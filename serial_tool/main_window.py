# -*- coding: utf-8 -*-
"""
serial_tool/main_window.py
主窗口：
- 串口数量选择（1~4），动态等分布局
  1 个 -> 整窗；2 个 -> 左右平分；3 个 -> 三等分；4 个 -> 固定 2×2
- 全部打开 / 全部关闭 / 刷新串口 / 清空全部
- 窗口保持居中、自适应大小、一键最大化
"""

import ctypes
import math
import sys

from PyQt5.QtCore import (
    Qt,
    QTimer,
    QSettings,
    QEvent,
    QPoint,
    QRect,
    QPointF,
    QSize,
    QEasingCurve,
    QVariantAnimation,
)
from PyQt5.QtGui import QFont, QPainter, QPainterPath, QPixmap, QTransform, QIcon
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QCheckBox,
    QToolBar,
    QToolButton,
    QMessageBox,
    QDialog,
    QApplication,
)
from PyQt5 import sip

from serial_tool.terminal_panel import TerminalPanel
from serial_tool.resources import asset_path

# Windows 无边框窗口所需常量（仅 Windows 生效）
if sys.platform.startswith("win"):
    import ctypes.wintypes

    WM_NCHITTEST = 0x0084
    WM_GETMINMAXINFO = 0x0024
    WM_EXITSIZEMOVE = 0x0232
    HTCLIENT = 1
    HTCAPTION = 2
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOM = 15
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17
    RESIZE_MARGIN = 6

    class _WinPoint(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class _MinMaxInfo(ctypes.Structure):
        _fields_ = [
            ("ptReserved", _WinPoint),
            ("ptMaxSize", _WinPoint),
            ("ptMaxPosition", _WinPoint),
            ("ptMinTrackSize", _WinPoint),
            ("ptMaxTrackSize", _WinPoint),
        ]


MAX_PANELS = 4

# 每个串口数量对应的建议窗口尺寸（宽, 高）
WINDOW_SIZES = {
    1: (650, 880),  # 单个串口默认小窗
    2: (1150, 880),
    3: (1700, 880),
    4: (1400, 912),  # 4 个时工具栏在左侧，给 2×2 网格更多高度
}


class _ThemeRevealOverlay(QWidget):
    """主题切换的圆形扩散过渡层：新主题从圆心向外扩展示出。"""

    def __init__(self, window, old_pix, new_pix, center):
        super().__init__(window)
        self._old = old_pix
        self._new = new_pix
        self._center = center
        self._progress = 0.0
        w, h = window.width(), window.height()
        self._max_r = math.hypot(
            max(center.x(), w - center.x()), max(center.y(), h - center.y())
        )
        self.setGeometry(0, 0, w, h)
        self.raise_()
        self.show()

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(600)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.valueChanged.connect(self._on_progress)
        self._anim.finished.connect(self._on_finished)

    def start_animation(self):
        self._anim.start()

    def _on_progress(self, value):
        self._progress = float(value)
        self.update()

    def _on_finished(self):
        self.hide()
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self._old)
        path = QPainterPath()
        r = self._progress * self._max_r
        path.addEllipse(QPointF(self._center), r, r)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, self._new)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("串口调试助手")
        self.setMinimumSize(640, 480)
        # 无边框：使用自定义标题栏与窗口控制按钮
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 圆角窗口：透明背景 + QSS border-radius（最大化时由 changeEvent 取消圆角）
        self.setObjectName("mainWindow")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.panels = [TerminalPanel(i) for i in range(MAX_PANELS)]
        for p in self.panels:
            p.state_changed.connect(self._update_status)

        self._port_count = 1
        self._dark_mode = True

        self._build_ui()
        self._load_settings()

    def _load_settings(self):
        """恢复上次保存的串口数量、主题与各面板参数。"""
        s = QSettings("SerialTool", "SerialDebugAssistant")
        count = min(max(int(s.value("port_count", 1, int)), 1), MAX_PANELS)
        self._port_count = count
        self._dark_mode = bool(s.value("dark_mode", True, bool))

        # 静默恢复下拉框，避免触发多次重建
        self.combo_count.blockSignals(True)
        self.combo_count.setCurrentIndex(count - 1)
        self.combo_count.blockSignals(False)

        for p in self.panels:
            p.load_settings(s)

        self._apply_settings()

        self._apply_theme()
        self._apply_toolbar_area()
        self._rebuild_layout()
        self._adjust_window_size()

    def closeEvent(self, event):
        """退出前保存当前配置，下次启动自动恢复。"""
        s = QSettings("SerialTool", "SerialDebugAssistant")
        s.setValue("port_count", self._port_count)
        s.setValue("dark_mode", self._dark_mode)
        # 关键词高亮 / 行过滤配置
        s.setValue("highlight_enabled", self._highlight_enabled)
        s.setValue(
            "highlight_keywords",
            [f"{kw}|{color}" for kw, color in self._highlight_keywords],
        )
        s.setValue("filter_enabled", self._filter_enabled)
        s.setValue("filter_keywords", self._filter_keywords)
        for p in self.panels:
            p.save_settings(s)
        s.sync()
        super().closeEvent(event)

    # ------------------------------------------------------------- UI 构建
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 自定义标题栏（独占整行、按钮靠最右）
        self._build_title_bar()
        root.addWidget(self.title_bar)

        # 主体：工具栏 + 中央网格（按串口数量切换摆放）
        self._body = QWidget()
        root.addWidget(self._body, 1)

        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self._toolbar = tb

        tb.addWidget(QLabel("串口数量 "))
        self.combo_count = QComboBox()
        self.combo_count.addItems([str(i) for i in range(1, MAX_PANELS + 1)])
        self.combo_count.setCurrentIndex(0)
        self.combo_count.currentTextChanged.connect(self._on_count_changed)
        tb.addWidget(self.combo_count)
        tb.addSeparator()

        self.btn_refresh_all = QPushButton("刷新")
        self.btn_refresh_all.setToolTip("刷新串口列表")
        self.btn_refresh_all.clicked.connect(self._refresh_all)
        tb.addWidget(self.btn_refresh_all)

        self.btn_toggle_all = QPushButton("打开")
        self.btn_toggle_all.setObjectName("btnOpen")
        self.btn_toggle_all.setToolTip("同时打开所有串口")
        self.btn_toggle_all.clicked.connect(self._toggle_all)
        tb.addWidget(self.btn_toggle_all)

        self.btn_clear_all = QPushButton("清空")
        self.btn_clear_all.setToolTip("清空所有串口的接收区")
        self.btn_clear_all.clicked.connect(self._clear_all)
        tb.addWidget(self.btn_clear_all)

        self.btn_settings = QPushButton("设置")
        self.btn_settings.setToolTip("日志关键词高亮等设置")
        self.btn_settings.clicked.connect(self._open_settings)
        tb.addWidget(self.btn_settings)

        self.btn_check_update = QPushButton("检查更新")
        self.btn_check_update.setToolTip("检查是否有新版本")
        self.btn_check_update.clicked.connect(self._check_update)
        tb.addWidget(self.btn_check_update)
        tb.addSeparator()

        self.check_center = QCheckBox("窗口居中")
        self.check_center.setChecked(True)
        self.check_center.setToolTip("开启后窗口始终保持居中")
        tb.addWidget(self.check_center)

        self.check_auto_size = QCheckBox("自适应窗口")
        self.check_auto_size.setChecked(True)
        self.check_auto_size.setToolTip("布局变化时自动调整窗口大小")
        tb.addWidget(self.check_auto_size)

        # 中央网格
        self._central = QWidget()
        self._grid = QGridLayout(self._central)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setSpacing(8)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusBar")
        self.status_label.setContentsMargins(8, 3, 8, 3)
        root.addWidget(self.status_label)

        self._apply_toolbar_area()

    # ----------------------------------------------------- 自定义标题栏
    def _build_title_bar(self):
        """无边框窗口的自定义标题栏（标题 + 主题/最小化/最大化/关闭按钮）。"""
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(34)
        bar.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 6, 0)
        lay.setSpacing(2)

        self.title_label = QLabel("串口调试助手")
        self.title_label.setObjectName("titleLabel")
        # 左上角 logo
        self.title_logo = QLabel()
        self.title_logo.setFixedSize(20, 20)
        self.title_logo.setPixmap(QIcon(asset_path("logo.ico")).pixmap(20, 20))
        self.title_logo.setToolTip("串口调试助手")
        lay.addWidget(self.title_logo)
        lay.addWidget(self.title_label)
        lay.addStretch(1)  # 把按钮可靠推到最右

        self._title_buttons = []
        self._title_bar_layout = lay
        # 顺序：图钉(置顶) → 主题切换 → 最小化 → 最大化 → 关闭（靠最右）
        self.btn_title_pin = self._make_title_button("", self._toggle_pin)
        self.btn_title_pin.setCheckable(True)
        self.btn_title_pin.setFixedSize(36, 26)
        self.btn_title_pin.setToolTip("窗口置顶（固定在最前）")
        self.btn_title_pin.setIcon(QIcon(self._make_pin_icon(45)))  # 初始：不固定，横着
        self.btn_title_pin.setIconSize(QSize(18, 18))
        self.btn_title_theme = self._make_title_button("☀", self._toggle_theme)
        self.btn_title_theme.setFont(QFont("Segoe UI Emoji", 12))
        self.btn_title_theme.setFixedSize(44, 26)
        self.btn_title_theme.setToolTip("切换 白天 / 夜间 模式")
        self.btn_title_min = self._make_title_button("─", self.showMinimized)
        self.btn_title_max = self._make_title_button("□", self._toggle_maximize)
        self.btn_title_close = self._make_title_button("✕", self.close, close=True)

        self.title_bar = bar

    def _make_title_button(self, text, slot, close=False):
        btn = QToolButton()
        btn.setText(text)
        btn.setObjectName("titleBtnClose" if close else "titleBtn")
        btn.setFixedSize(40, 26)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(slot)
        self._title_bar_layout.addWidget(btn)
        self._title_buttons.append(btn)
        return btn

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _toggle_pin(self, checked):
        """图钉按钮：勾选时窗口始终置顶（最前），取消时恢复正常。
        不固定时图钉横着放平（旋转45°），固定时呈斜向（📌 天然斜态）。"""
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.show()  # 切换窗口标志后重新显示，使其立即生效
        self.btn_title_pin.setIcon(QIcon(self._make_pin_icon(0 if checked else 45)))
        self.btn_title_pin.setToolTip(
            "取消窗口置顶" if checked else "窗口置顶（固定在最前）"
        )

    def _make_pin_icon(self, angle):
        """把斜向图钉 � 渲染成图标，可按角度旋转（固定时旋转成竖直）。"""
        size = 24
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(QFont("Segoe UI Emoji", 14))
        painter.drawText(pm.rect(), Qt.AlignCenter, "📌")
        painter.end()
        if angle:
            pm = pm.transformed(QTransform().rotate(angle), Qt.SmoothTransformation)
        return pm

    # ----------------------------------------------------------- 主题切换
    def _toggle_theme(self):
        """点击主题图标：切换主题，并以图标为中心圆形扩散过渡。

        关键：切换主题后不做 processEvents，屏幕仍显示旧主题；
        直接抓取新主题截图并盖上过渡层，避免新主题先闪现。
        切换完成后立即刷新各面板接收缓冲，日志不因抓图耗时而滞后。
        """
        btn = self.btn_title_theme
        center = btn.mapTo(self, QPoint(btn.width() // 2, btn.height() // 2))
        old_pix = self.grab()
        self._dark_mode = not self._dark_mode
        self._apply_theme()
        new_pix = self.grab()
        overlay = _ThemeRevealOverlay(self, old_pix, new_pix, center)
        overlay.start_animation()
        self._flush_all_panels()

    def _flush_all_panels(self):
        """立即刷新所有可见面板的接收缓冲。"""
        for p in self.panels[: self._port_count]:
            p.flush_now()

    def _apply_theme(self):
        from serial_tool.theme import QSS, LIGHT_QSS

        app = QApplication.instance()
        app.setStyleSheet(QSS if self._dark_mode else LIGHT_QSS)
        self.btn_title_theme.setText("☀" if self._dark_mode else "🌙")
        for w in QApplication.allWidgets():
            w.style().unpolish(w)
            w.style().polish(w)

    # ------------------------------------------- 无边框窗口（Windows）
    def nativeEvent(self, eventType, message):
        """Windows 无边框：边缘缩放 + 标题栏拖动 + 最大化不遮任务栏。"""
        if not sys.platform.startswith("win"):
            return super().nativeEvent(eventType, message)
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_NCHITTEST:
                return True, self._nchittest(msg)
            if msg.message == WM_GETMINMAXINFO:
                self._getminmaxinfo(msg)
                return True, 0
            if msg.message == WM_EXITSIZEMOVE:
                # 拖动/缩放结束：立即刷新所有面板接收缓冲，日志不因拖动而滞后
                self._flush_all_panels()
        return super().nativeEvent(eventType, message)

    def _nchittest(self, msg):
        pos = self.mapFromGlobal(QPoint(msg.pt.x, msg.pt.y))
        m = RESIZE_MARGIN
        w, h = self.width(), self.height()
        if not self.isMaximized():
            left = pos.x() <= m
            right = pos.x() >= w - m
            top = pos.y() <= m
            bottom = pos.y() >= h - m
            if top and left:
                return HTTOPLEFT
            if top and right:
                return HTTOPRIGHT
            if bottom and left:
                return HTBOTTOMLEFT
            if bottom and right:
                return HTBOTTOMRIGHT
            if left:
                return HTLEFT
            if right:
                return HTRIGHT
            if top:
                return HTTOP
            if bottom:
                return HTBOTTOM
        tb = self.title_bar.geometry()
        if tb.contains(pos):
            for btn in self._title_buttons:
                r = QRect(tb.topLeft() + btn.geometry().topLeft(), btn.size())
                if r.contains(pos):
                    return HTCLIENT
            return HTCAPTION
        return HTCLIENT

    def _getminmaxinfo(self, msg):
        mmi = ctypes.cast(msg.lParam, ctypes.POINTER(_MinMaxInfo)).contents
        work = QApplication.primaryScreen().availableGeometry()
        mmi.ptMaxSize.x = work.width()
        mmi.ptMaxSize.y = work.height()
        mmi.ptMaxPosition.x = work.x()
        mmi.ptMaxPosition.y = work.y()
        mmi.ptMaxTrackSize.x = work.width()
        mmi.ptMaxTrackSize.y = work.height()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            maximized = self.isMaximized()
            self.btn_title_max.setText("❐" if maximized else "□")
            # 最大化时取消圆角（铺满工作区），还原时恢复圆角。
            # 注意：属性名不能用 "maximized"（本环境 PyQt5 无法写入该保留名），
            # 且 setProperty 返回值恒为 False（ABI 兼容问题），实际已写入。
            val = "true" if maximized else "false"
            for w in (self, self.title_bar, self.status_label):
                w.setProperty("winMaximized", val)
                w.style().unpolish(w)
                w.style().polish(w)
        super().changeEvent(event)

    # ------------------------------------------------------------- 布局
    def _rows_cols(self):
        """根据串口数量计算网格行列数（固定水平等分）。"""
        n = self._port_count
        if n == 1:
            return 1, 1
        if n == MAX_PANELS:
            return 2, 2  # 4 个固定 2×2
        return 1, n  # 2/3 个串口左右平分

    def _rebuild_layout(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
        # 重置所有行列拉伸，避免上次布局（如 2×2）残留的空行列分走空间
        for r in range(MAX_PANELS):
            self._grid.setRowStretch(r, 0)
        for c in range(MAX_PANELS):
            self._grid.setColumnStretch(c, 0)
        rows, cols = self._rows_cols()
        for i in range(self._port_count):
            r, c = divmod(i, cols)
            self._grid.addWidget(self.panels[i], r, c)
        for r in range(rows):
            self._grid.setRowStretch(r, 1)
        for c in range(cols):
            self._grid.setColumnStretch(c, 1)
        for i in range(self._port_count):
            self.panels[i].show()
        self._update_status()

    def _on_count_changed(self, text):
        self._port_count = int(text)
        self._apply_toolbar_area()
        self._rebuild_layout()
        self._adjust_window_size()

    def _apply_toolbar_area(self):
        """摆放主工具栏：4 个串口时在左侧（竖排），其余在顶部。"""
        self._toolbar.setOrientation(
            Qt.Vertical if self._port_count == MAX_PANELS else Qt.Horizontal
        )
        # 先卸载并删除旧布局，再安装新布局。
        # 注意：setParent(None) 不会从控件上真正卸载布局，会让旧布局指针悬空，
        # 再次 setLayout 时触发 C++ 双重释放导致崩溃；必须用 sip.delete。
        old = self._body.layout()
        if old is not None:
            old.removeWidget(self._toolbar)
            old.removeWidget(self._central)
            sip.delete(old)
        lay = QHBoxLayout() if self._port_count == MAX_PANELS else QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._toolbar)
        lay.addWidget(self._central, 1)
        self._body.setLayout(lay)
        self._body_layout = lay

    # ------------------------------------------------------------- 批量操作
    def _refresh_all(self):
        for p in self.panels[: self._port_count]:
            p.refresh_ports()

    def _toggle_all(self):
        """单个开关按钮：有串口已打开则全部关闭，否则全部打开。"""
        if any(p.is_open for p in self.panels[: self._port_count]):
            self._close_all()
        else:
            self._open_all()

    def _open_all(self):
        errors = []
        for p in self.panels[: self._port_count]:
            ok, msg = p.open_port(silent=True)
            if not ok:
                errors.append(msg)
        if errors:
            QMessageBox.warning(
                self, "全部打开", "以下串口打开失败：\n" + "\n".join(errors)
            )

    def _close_all(self):
        for p in self.panels[: self._port_count]:
            p.close_port()

    def _clear_all(self):
        for p in self.panels[: self._port_count]:
            p.clear_receive()

    # ------------------------------------------------------------- 设置
    def _open_settings(self):
        """打开设置对话框（日志关键词高亮、行过滤等）。"""
        from serial_tool.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self._apply_settings()

    # ------------------------------------------------------------- 检查更新
    def _check_update(self):
        """检查更新：拉取版本清单，发现新版本则提示下载安装。"""
        from serial_tool import __version__
        from serial_tool.updater import (
            STATE_ERROR,
            STATE_FOUND,
            STATE_LATEST,
            STATE_NO_ASSET,
            Updater,
        )

        btn = self.btn_check_update
        btn.setEnabled(False)
        btn.setText("检查中…")
        updater = Updater(self)
        self._updater = updater  # 持有引用，防止被回收

        def on_result(state, new_version, info):
            btn.setEnabled(True)
            btn.setText("检查更新")
            if state == STATE_ERROR:
                QMessageBox.warning(
                    self,
                    "检查更新",
                    "无法连接更新服务器，请检查网络后重试。\n"
                    "（更新地址：GitHub Releases，大陆网络访问可能需要代理）",
                )
                return
            if state == STATE_NO_ASSET:
                QMessageBox.information(
                    self,
                    "检查更新",
                    "更新服务器已连接，但 Release 中未找到安装包\n"
                    "（缺少 SerialTool-Setup-*.exe 附件），请联系开发者。",
                )
                return
            if state == STATE_LATEST:
                QMessageBox.information(
                    self,
                    "检查更新",
                    f"当前已是最新版本 v{__version__}。",
                )
                return
            # STATE_FOUND：发现新版本
            ret = QMessageBox.question(
                self,
                "发现新版本",
                f"发现新版本 v{new_version}（当前 v{__version__}）。\n是否下载并安装？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ret == QMessageBox.Yes:
                updater.download_and_launch(self, info)

        updater.check(on_result)

    def _apply_settings(self):
        """从 QSettings 读取高亮/行过滤配置并应用到所有串口面板。

        高亮与过滤使用两套独立的关键词列表。
        """
        s = QSettings("SerialTool", "SerialDebugAssistant")
        # 高亮关键词：带颜色
        keywords = []
        for entry in s.value("highlight_keywords", [], list):
            if "|" in entry:
                kw, color = entry.split("|", 1)
                if kw:
                    keywords.append((kw, color))
        # 过滤关键词：独立列表
        filter_kws = [
            kw for kw in s.value("filter_keywords", [], list) if kw and kw.strip()
        ]
        # 记录当前配置，供 closeEvent 统一保存
        self._highlight_enabled = bool(s.value("highlight_enabled", False, bool))
        self._highlight_keywords = keywords
        self._filter_enabled = bool(s.value("filter_enabled", False, bool))
        self._filter_keywords = filter_kws
        rules = keywords if self._highlight_enabled else []
        for p in self.panels:
            p.set_highlight_rules(rules)
            p.set_filter(self._filter_enabled, filter_kws)

    # ------------------------------------------------------------- 窗口管理
    def _update_status(self, *args):
        n = self._port_count
        opened = sum(1 for p in self.panels[:n] if p.is_open)
        rows, cols = self._rows_cols()
        # 单个开关按钮：根据打开状态切换文案/配色/提示
        any_open = opened > 0
        self.btn_toggle_all.setText("关闭" if any_open else "打开")
        self.btn_toggle_all.setObjectName("btnClose" if any_open else "btnOpen")
        self.btn_toggle_all.setToolTip(
            "同时关闭所有串口" if any_open else "同时打开所有串口"
        )
        self.btn_toggle_all.style().unpolish(self.btn_toggle_all)
        self.btn_toggle_all.style().polish(self.btn_toggle_all)
        self.status_label.setText(
            f"布局：水平等分 {rows}×{cols} ｜ 串口数量：{n} ｜ 已打开：{opened}/{n}"
        )

    def _center_window(self):
        """将窗口移动到主屏幕中央。"""
        if not self.check_center.isChecked() or self.isMaximized():
            return
        frame = self.frameGeometry()
        screen = QApplication.primaryScreen().availableGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def _adjust_window_size(self):
        """按串口数量使用固定适中尺寸；屏幕放不下时最大化。

        切换数量时直接切换到对应尺寸（1 个口为 720×640 小窗）。
        """
        if not self.check_auto_size.isChecked():
            return
        screen = QApplication.primaryScreen().availableGeometry()
        sw, sh = screen.width(), screen.height()
        w, h = WINDOW_SIZES[self._port_count]
        w = min(w, sw)
        h = min(h, sh)
        if w >= sw - 1 or h >= sh - 1:
            self.showMaximized()
            return
        if self.isMaximized():
            self.showNormal()
        self.resize(w, h)
        self._center_window()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._deferred_center)

    def _deferred_center(self):
        """仅在首次显示时居中一次，避免用户拖动缩放时窗口被拽回中央。"""
        if (
            self.check_center.isChecked()
            and not self.isMaximized()
            and self.isVisible()
        ):
            self._center_window()

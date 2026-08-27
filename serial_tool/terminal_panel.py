# -*- coding: utf-8 -*-
"""
serial_tool/terminal_panel.py
单个串口终端面板：
- 连接参数：串口 / 波特率 / 格式 / 流控
- 打开 / 关闭（面板独立控制）
- 接收显示：自动滚屏（关闭后视图停留在关闭那一刻，接收不中断、可鼠标滑动）、
  HEX 显示、时间戳、显示发送回显、清空、保存日志、收发字节统计
- 发送：HEX 发送、追加 CRLF、定时发送、回车即发送
"""

import re
from collections import deque

from PyQt5.QtCore import Qt, QTimer, QDateTime, QIODevice, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QPlainTextEdit,
    QCheckBox,
    QGroupBox,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QFrame,
    QSizePolicy,
    QMenu,
    QApplication,
)

from serial_tool.log_highlighter import KeywordHighlighter

BAUD_RATES = [
    "300",
    "600",
    "1200",
    "2400",
    "4800",
    "9600",
    "19200",
    "38400",
    "57600",
    "115200",
    "128000",
    "230400",
    "256000",
    "460800",
    "500000",
    "576000",
    "921600",
    "1000000",
    "1152000",
    "1500000",
    "2000000",
]

DATA_BITS = {
    "5": QSerialPort.Data5,
    "6": QSerialPort.Data6,
    "7": QSerialPort.Data7,
    "8": QSerialPort.Data8,
}
PARITY_CHARS = {
    "N": QSerialPort.NoParity,
    "E": QSerialPort.EvenParity,
    "O": QSerialPort.OddParity,
    "M": QSerialPort.MarkParity,
    "S": QSerialPort.SpaceParity,
}
STOP_BITS = {
    "1": QSerialPort.OneStop,
    "1.5": QSerialPort.OneAndHalfStop,
    "2": QSerialPort.TwoStop,
}
FLOW_CTRL = {
    "无": QSerialPort.NoFlowControl,
    "RTS/CTS": QSerialPort.HardwareControl,
    "XON/XOFF": QSerialPort.SoftwareControl,
}

# 数据位/校验位/停止位合并的格式选项（如 8N1）
FORMATS = [
    "8N1",
    "8N2",
    "8E1",
    "8O1",
    "8M1",
    "8S1",
    "8E2",
    "8O2",
    "8N1.5",
    "8E1.5",
    "8O1.5",
    "7N1",
    "7E1",
    "7O1",
    "7N2",
    "6N1",
    "5N1",
]


def _parse_format(fmt):
    """把 "8N1" / "8N1.5" 解析为 (数据位枚举, 校验枚举, 停止位枚举)。"""
    stop_key = "1.5" if fmt.endswith("1.5") else fmt[2]
    return DATA_BITS[fmt[0]], PARITY_CHARS[fmt[1]], STOP_BITS[stop_key]


# 发送时追加的换行方式
LINE_ENDS = {
    "无": b"",
    "CR": b"\r",
    "LF": b"\n",
    "CRLF": b"\r\n",
}

_ESCAPE_RE = re.compile(r"\\(?:x([0-9a-fA-F]{2})|u([0-9a-fA-F]{4})|(.))", re.DOTALL)
_ESCAPE_MAP = {
    "r": "\r",
    "n": "\n",
    "t": "\t",
    "0": "\0",
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "v": "\v",
    "\\": "\\",
    "'": "'",
    '"': '"',
}


def _decode_escapes(text):
    """把 \\r \\n \\t \\xHH \\uHHHH 等转义序列解析为真实字符。

    未知转义（如 \\q）原样保留。
    """

    def repl(m):
        if m.group(1):
            return chr(int(m.group(1), 16))
        if m.group(2):
            return chr(int(m.group(2), 16))
        ch = m.group(3)
        return _ESCAPE_MAP.get(ch, "\\" + ch)

    return _ESCAPE_RE.sub(repl, text)


def _natural_key(name):
    """COM2 < COM10 的自然排序键。"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


class SendEdit(QPlainTextEdit):
    """发送输入框：回车即发送，Shift+回车换行。"""

    sendRequested = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
            event.modifiers() & Qt.ShiftModifier
        ):
            self.sendRequested.emit()
            return
        super().keyPressEvent(event)


class LogView(QPlainTextEdit):
    """接收日志区：只读 + 中文右键菜单（复制/复制所选/全选/清空/保存日志）。"""

    clearRequested = pyqtSignal()
    saveRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        has_sel = self.textCursor().hasSelection()
        act_copy = menu.addAction("复制")
        act_copy.triggered.connect(self._copy)
        act_copy_sel = menu.addAction("复制所选内容")
        act_copy_sel.setEnabled(has_sel)
        act_copy_sel.triggered.connect(self.copy)
        menu.addSeparator()
        act_select = menu.addAction("全选")
        act_select.triggered.connect(self.selectAll)
        menu.addSeparator()
        act_clear = menu.addAction("清空")
        act_clear.triggered.connect(self.clearRequested.emit)
        act_save = menu.addAction("保存日志")
        act_save.triggered.connect(self.saveRequested.emit)
        menu.exec_(event.globalPos())

    def _copy(self):
        """复制：有选区复制选区，否则复制最后一行。"""
        if self.textCursor().hasSelection():
            self.copy()
        else:
            last = self.document().lastBlock().text()
            if last:
                QApplication.clipboard().setText(last)


class TerminalPanel(QFrame):
    """单个串口终端面板。"""

    state_changed = pyqtSignal(int, bool)  # (index, is_open)

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setObjectName("terminalPanel")
        # 窗口放大/最大化时面板同步撑满
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.serial = QSerialPort(self)
        self._rx_buffer = bytearray()
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._is_open = False
        self._filter_enabled = False
        self._filter_keywords = []  # 小写关键词列表

        self._build_ui()
        self.refresh_ports()

        # 接收数据分批刷新的定时器，避免高速数据卡界面
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(60)
        self._flush_timer.timeout.connect(self._flush_rx)
        self._flush_timer.start()

        self._send_timer = QTimer(self)
        self._send_timer.timeout.connect(self.send_data)

        self.serial.readyRead.connect(self._on_ready_read)
        self.serial.errorOccurred.connect(self._on_error)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(4)

        # 标题栏
        head = QHBoxLayout()
        head.setSpacing(6)
        self.title_label = QLabel(f"串口 {self.index + 1}")
        self.title_label.setObjectName("panelTitle")
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDotClosed")
        self.status_dot.setToolTip("串口未打开")
        head.addWidget(self.title_label)
        head.addWidget(self.status_dot)
        head.addStretch(1)
        root.addLayout(head)

        root.addWidget(self._build_config_group())
        root.addWidget(self._build_rx_group(), 1)
        root.addWidget(self._build_tx_group())

    def _build_config_group(self):
        group = QGroupBox("连接参数")
        gl = QGridLayout(group)
        gl.setContentsMargins(6, 12, 6, 6)
        gl.setHorizontalSpacing(4)
        gl.setVerticalSpacing(4)

        # 第一行：所有连接参数（只占一行）；刷新串口由顶部工具栏统一处理
        gl.addWidget(QLabel("串口"), 0, 0)
        self.combo_port = QComboBox()
        self.combo_port.setMinimumWidth(60)
        gl.addWidget(self.combo_port, 0, 1)

        gl.addWidget(QLabel("波特率"), 0, 2)
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(BAUD_RATES)
        self.combo_baud.setCurrentText("115200")
        self.combo_baud.setMinimumWidth(64)
        gl.addWidget(self.combo_baud, 0, 3)

        gl.addWidget(QLabel("格式"), 0, 4)
        self.combo_format = QComboBox()
        self.combo_format.addItems(FORMATS)
        self.combo_format.setCurrentText("8N1")
        self.combo_format.setMinimumWidth(56)
        self.combo_format.setToolTip("数据位/校验位/停止位，如 8N1")
        gl.addWidget(self.combo_format, 0, 5)

        gl.addWidget(QLabel("流控"), 0, 6)
        self.combo_flow = QComboBox()
        self.combo_flow.addItems(list(FLOW_CTRL.keys()))
        self.combo_flow.setCurrentText("无")
        self.combo_flow.setMinimumWidth(48)
        gl.addWidget(self.combo_flow, 0, 7)

        for col in (1, 3, 5, 7):
            gl.setColumnStretch(col, 1)
        return group

    def _build_rx_group(self):
        group = QGroupBox("接收")
        v = QVBoxLayout(group)
        v.setContentsMargins(8, 14, 8, 6)
        v.setSpacing(4)

        # 完整日志缓冲：始终保留全部接收内容（过滤只是显示开关）。
        # 注意：QPlainTextEdit.setDocument 在本环境 PyQt5 下不生效（ABI 问题），
        # 因此用 Python deque 保存完整日志，视图按过滤状态重建。
        self._log_lines = deque(maxlen=200000)

        self.receive_view = LogView()
        self.receive_view.setPlaceholderText("接收数据将显示在这里…")
        self.receive_view.setMaximumBlockCount(200000)
        self.receive_view.clearRequested.connect(self.clear_receive)
        self.receive_view.saveRequested.connect(self.save_log)
        v.addWidget(self.receive_view, 1)
        # 日志关键词高亮（由顶部工具栏「设置」配置）
        self._highlighter = KeywordHighlighter(self.receive_view.document())

        tools = QHBoxLayout()
        tools.setSpacing(5)
        self.check_autoscroll = QCheckBox("自动滚屏")
        self.check_autoscroll.setChecked(True)
        self.check_hex_display = QCheckBox("HEX显示")
        self.check_timestamp = QCheckBox("时间戳")
        self.check_echo = QCheckBox("显示发送")
        for w in (
            self.check_autoscroll,
            self.check_hex_display,
            self.check_timestamp,
            self.check_echo,
        ):
            tools.addWidget(w)
        tools.addStretch(1)

        self.btn_clear_rx = QPushButton("清空")
        self.btn_clear_rx.clicked.connect(self.clear_receive)
        self.btn_save = QPushButton("保存")
        self.btn_save.setToolTip("保存接收日志到文件")
        self.btn_save.clicked.connect(self.save_log)
        tools.addWidget(self.btn_clear_rx)
        tools.addWidget(self.btn_save)
        v.addLayout(tools)

        self.rx_stats = QLabel("接收: 0 B | 发送: 0 B")
        self.rx_stats.setObjectName("statusText")
        v.addWidget(self.rx_stats)
        return group

    def _build_tx_group(self):
        group = QGroupBox("发送")
        v = QVBoxLayout(group)
        v.setContentsMargins(8, 14, 8, 6)
        v.setSpacing(4)

        self.send_edit = SendEdit()
        self.send_edit.setPlaceholderText(
            "输入要发送的数据（回车发送；转义解析可用 \\r \\n \\t \\xHH）…"
        )
        self.send_edit.setFixedHeight(56)
        self.send_edit.sendRequested.connect(self.send_data)
        v.addWidget(self.send_edit)

        tools = QHBoxLayout()
        tools.setSpacing(4)
        self.check_hex_send = QCheckBox("HEX发送")
        tools.addWidget(self.check_hex_send)

        self.check_escape = QCheckBox("转义解析")
        self.check_escape.setToolTip(
            "解析 \\r \\n \\t \\xHH \\uHHHH 等转义字符为实际字节"
        )
        tools.addWidget(self.check_escape)

        line_end_label = QLabel("换行")
        line_end_label.setFixedWidth(28)
        tools.addWidget(line_end_label)
        self.combo_line_end = QComboBox()
        self.combo_line_end.addItems(list(LINE_ENDS.keys()))
        self.combo_line_end.setCurrentText("CRLF")
        self.combo_line_end.setFixedWidth(60)
        self.combo_line_end.setToolTip("发送时自动追加的换行")
        tools.addWidget(self.combo_line_end)

        self.check_timer_send = QCheckBox("定时发送")
        self.check_timer_send.toggled.connect(self._on_timer_send_toggled)
        self.spin_timer = QSpinBox()
        self.spin_timer.setRange(10, 600000)
        self.spin_timer.setValue(1000)
        self.spin_timer.setSuffix(" ms")
        self.spin_timer.setFixedWidth(88)  # 保证时间显示完整
        self.spin_timer.valueChanged.connect(self._on_timer_interval_changed)
        tools.addWidget(self.check_timer_send)
        tools.addWidget(self.spin_timer)
        tools.addStretch(1)

        self.btn_clear_tx = QPushButton("清空")
        self.btn_clear_tx.setFixedWidth(48)
        self.btn_clear_tx.setToolTip("清空发送内容")
        self.btn_clear_tx.clicked.connect(self.send_edit.clear)
        self.btn_send = QPushButton("发送")
        self.btn_send.setObjectName("btnSend")
        self.btn_send.setFixedWidth(52)
        self.btn_send.clicked.connect(self.send_data)
        tools.addWidget(self.btn_clear_tx)
        tools.addWidget(self.btn_send)
        v.addLayout(tools)
        return group

    # -------------------------------------------------------------- 串口控制
    @property
    def is_open(self):
        return self._is_open

    def refresh_ports(self):
        current = self.combo_port.currentText()
        self.combo_port.clear()
        ports = sorted(
            (p.portName() for p in QSerialPortInfo.availablePorts()),
            key=_natural_key,
        )
        self.combo_port.addItems(ports)
        if current in ports:
            self.combo_port.setCurrentText(current)

    # ------------------------------------------------------------ 配置记忆
    def save_settings(self, s):
        """把本面板当前参数写入 QSettings，供下次启动恢复。"""
        prefix = f"panel{self.index}/"
        s.setValue(prefix + "port", self.combo_port.currentText())
        s.setValue(prefix + "baud", self.combo_baud.currentText())
        s.setValue(prefix + "format", self.combo_format.currentText())
        s.setValue(prefix + "flow", self.combo_flow.currentText())
        s.setValue(prefix + "hex_send", self.check_hex_send.isChecked())
        s.setValue(prefix + "escape", self.check_escape.isChecked())
        s.setValue(prefix + "line_end", self.combo_line_end.currentText())
        s.setValue(prefix + "timer_interval", self.spin_timer.value())
        s.setValue(prefix + "hex_display", self.check_hex_display.isChecked())
        s.setValue(prefix + "timestamp", self.check_timestamp.isChecked())
        s.setValue(prefix + "echo", self.check_echo.isChecked())
        s.setValue(prefix + "autoscroll", self.check_autoscroll.isChecked())
        s.setValue(prefix + "send_text", self.send_edit.toPlainText())

    def load_settings(self, s):
        """从 QSettings 恢复上次保存的参数。"""
        prefix = f"panel{self.index}/"
        self.combo_port.setCurrentText(s.value(prefix + "port", "", str))
        self.combo_baud.setCurrentText(s.value(prefix + "baud", "115200", str))
        self.combo_format.setCurrentText(s.value(prefix + "format", "8N1", str))
        self.combo_flow.setCurrentText(s.value(prefix + "flow", "无", str))
        self.check_hex_send.setChecked(s.value(prefix + "hex_send", False, bool))
        self.check_escape.setChecked(s.value(prefix + "escape", False, bool))
        le = s.value(prefix + "line_end", "CRLF", str)
        if le in LINE_ENDS:
            self.combo_line_end.setCurrentText(le)
        self.spin_timer.setValue(int(s.value(prefix + "timer_interval", 1000, int)))
        self.check_hex_display.setChecked(s.value(prefix + "hex_display", False, bool))
        self.check_timestamp.setChecked(s.value(prefix + "timestamp", False, bool))
        self.check_echo.setChecked(s.value(prefix + "echo", False, bool))
        self.check_autoscroll.setChecked(s.value(prefix + "autoscroll", True, bool))
        self.send_edit.setPlainText(s.value(prefix + "send_text", "", str))

    def open_port(self, silent=False):
        """打开串口。返回 (成功?, 错误信息)。"""
        if self.serial.isOpen():
            return True, None
        port = self.combo_port.currentText()
        if not port:
            msg = f"串口 {self.index + 1}：未选择端口"
            if not silent:
                QMessageBox.warning(self, "打开串口", msg)
            return False, msg
        self.serial.setPortName(port)
        self.serial.setBaudRate(int(self.combo_baud.currentText()))
        data_bits, parity, stop_bits = _parse_format(self.combo_format.currentText())
        self.serial.setDataBits(data_bits)
        self.serial.setParity(parity)
        self.serial.setStopBits(stop_bits)
        self.serial.setFlowControl(FLOW_CTRL[self.combo_flow.currentText()])
        if self.serial.open(QIODevice.ReadWrite):
            self._set_open_state(True)
            return True, None
        msg = f"串口 {port} 打开失败：{self.serial.errorString()}"
        if not silent:
            QMessageBox.warning(self, "打开串口", msg)
        return False, msg

    def close_port(self):
        if self.serial.isOpen():
            self.serial.close()
        self._send_timer.stop()
        self.check_timer_send.setChecked(False)
        self._set_open_state(False)

    def _set_open_state(self, is_open):
        self._is_open = is_open
        self.status_dot.setObjectName("statusDotOpen" if is_open else "statusDotClosed")
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        self.status_dot.setToolTip("串口已打开" if is_open else "串口未打开")
        for w in (
            self.combo_port,
            self.combo_baud,
            self.combo_format,
            self.combo_flow,
        ):
            w.setEnabled(not is_open)
        self.state_changed.emit(self.index, is_open)

    def _on_error(self, error):
        if error == QSerialPort.NoError:
            return
        if error == QSerialPort.ResourceError:
            QMessageBox.warning(
                self,
                "串口错误",
                f"串口 {self.serial.portName()} 连接丢失：{self.serial.errorString()}",
            )
            self.close_port()

    # -------------------------------------------------------------- 接收显示
    def _on_ready_read(self):
        data = self.serial.readAll()
        self._rx_buffer.extend(bytes(data))

    def _flush_rx(self):
        if not self._rx_buffer:
            return
        data = bytes(self._rx_buffer)
        self._rx_buffer.clear()
        self._rx_bytes += len(data)
        self._append_received(data)
        self._update_stats()

    def flush_now(self):
        """立即刷新接收缓冲（窗口拖动/主题切换等事件结束后调用，
        确保日志及时显示；期间未刷新的数据不会丢失）。"""
        self._flush_rx()

    def _insert_text(self, text):
        """新数据始终写入完整日志缓冲；按过滤状态决定是否显示。"""
        if not text:
            return
        self._log_lines.extend(text.split("\n"))
        view = self.receive_view
        cursor = view.textCursor()
        cursor.movePosition(QTextCursor.End)
        if self._filter_enabled and self._filter_keywords:
            kws = self._filter_keywords
            shown = [ln for ln in text.split("\n") if any(k in ln.lower() for k in kws)]
            if shown:
                cursor.insertText("\n".join(shown))
        else:
            cursor.insertText(text)
        if self.check_autoscroll.isChecked():
            bar = view.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _append_received(self, data):
        if self.check_hex_display.isChecked():
            text = self._to_hex(data)
        else:
            text = data.decode("utf-8", errors="replace")
        if self.check_timestamp.isChecked():
            ts = QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
            text = f"\n[{ts}] {text}"
        self._insert_text(text)

    @staticmethod
    def _to_hex(data):
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            lines.append(" ".join(f"{b:02X}" for b in chunk))
        return "\n".join(lines) + "\n"

    def clear_receive(self):
        """清空接收区与完整日志缓冲，并清零接收/发送字节统计。"""
        self._log_lines.clear()
        self.receive_view.clear()
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._update_stats()

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存接收日志",
            f"串口{self.index + 1}_接收日志.txt",
            "文本文件 (*.txt);;所有文件 (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.receive_view.toPlainText())
        except OSError as exc:
            QMessageBox.warning(self, "保存日志", f"保存失败：{exc}")

    def set_highlight_rules(self, rules):
        """设置日志关键词高亮规则；rules: [(关键词, 颜色十六进制), ...]。"""
        self._highlighter.set_rules(rules)

    # -------------------------------------------------------------- 行过滤
    def set_filter(self, enabled, keywords):
        """设置行过滤：启用后视图只显示包含关键词的行，
        完整日志仍保留在 _log_lines 缓冲，关闭过滤即可查看之前被隐藏的内容。"""
        self._filter_enabled = bool(enabled)
        self._filter_keywords = [k.lower().strip() for k in keywords if k and k.strip()]
        self._apply_filter_view()

    def _apply_filter_view(self):
        """按当前过滤状态重建视图（完整日志仍在缓冲中）。"""
        view = self.receive_view
        view.clear()
        if self._filter_enabled and self._filter_keywords:
            kws = self._filter_keywords
            shown = [ln for ln in self._log_lines if any(k in ln.lower() for k in kws)]
        else:
            shown = list(self._log_lines)
        if shown:
            view.setPlainText("\n".join(shown))
        if self.check_autoscroll.isChecked():
            bar = view.verticalScrollBar()
            bar.setValue(bar.maximum())

    # -------------------------------------------------------------- 发送
    def send_data(self):
        if not self._is_open:
            QMessageBox.warning(
                self, "发送", f"串口 {self.index + 1} 未打开，请先打开串口"
            )
            return
        text = self.send_edit.toPlainText()
        if not text:
            return
        try:
            if self.check_escape.isChecked():
                text = _decode_escapes(text)
            if self.check_hex_send.isChecked():
                payload = self._parse_hex(text)
            else:
                payload = text.encode("utf-8")
            payload += LINE_ENDS[self.combo_line_end.currentText()]
        except ValueError as exc:
            QMessageBox.warning(self, "发送", str(exc))
            return
        self.serial.write(payload)
        self.serial.flush()
        self._tx_bytes += len(payload)
        self._update_stats()
        if self.check_echo.isChecked():
            if self.check_hex_send.isChecked():
                shown = " ".join(f"{b:02X}" for b in payload)
            else:
                shown = payload.decode("utf-8", errors="replace")
            self._insert_text(f"\n[TX] {shown}")

    @staticmethod
    def _parse_hex(text):
        cleaned = re.sub(r"[^0-9a-fA-F]", "", text)
        if len(cleaned) % 2 != 0:
            raise ValueError(
                "HEX 发送数据长度必须为偶数（每两个十六进制字符表示一个字节）"
            )
        return bytes.fromhex(cleaned)

    def _on_timer_send_toggled(self, checked):
        if checked:
            if not self._is_open:
                self.check_timer_send.setChecked(False)
                QMessageBox.warning(
                    self, "定时发送", f"串口 {self.index + 1} 未打开，请先打开串口"
                )
                return
            self._send_timer.start(self.spin_timer.value())
        else:
            self._send_timer.stop()

    def _on_timer_interval_changed(self, value):
        if self._send_timer.isActive():
            self._send_timer.start(value)

    def _update_stats(self):
        self.rx_stats.setText(
            f"接收: {self._rx_bytes:,} B | 发送: {self._tx_bytes:,} B"
        )

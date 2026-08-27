# -*- coding: utf-8 -*-
"""设置对话框：日志关键词高亮配置，保存到 QSettings。"""

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QTableWidget,
    QHeaderView,
    QPushButton,
    QLineEdit,
    QDialogButtonBox,
    QColorDialog,
)

# QSettings 键
ENABLED_KEY = "highlight_enabled"
KEYWORDS_KEY = "highlight_keywords"
FILTER_KEY = "filter_enabled"
FILTER_KEYWORDS_KEY = "filter_keywords"

# 默认高亮颜色（浅黄，深浅主题下都清晰）
DEFAULT_COLOR = "#FFE082"


class SettingsDialog(QDialog):
    """设置对话框：日志关键词高亮 与 行过滤（两套独立关键词）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(440)
        self._build_ui()
        self._load()

    def _build_ui(self):
        v = QVBoxLayout(self)

        # ---------- 1) 日志关键词高亮（字体颜色高亮） ----------
        group = QGroupBox("日志关键词高亮")
        gv = QVBoxLayout(group)
        self.check_enable = QCheckBox(
            "启用关键词高亮（在接收区以字体颜色高亮匹配的关键词）"
        )
        gv.addWidget(self.check_enable)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["关键词", "字体颜色"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        gv.addWidget(self.table)

        row = QHBoxLayout()
        self.btn_add = QPushButton("添加")
        self.btn_add.clicked.connect(lambda: self._add_row())
        self.btn_remove = QPushButton("删除选中")
        self.btn_remove.clicked.connect(self._remove_selected)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_remove)
        row.addStretch(1)
        gv.addLayout(row)
        v.addWidget(group)

        # ---------- 2) 日志行过滤（独立关键词） ----------
        group2 = QGroupBox("日志行过滤")
        g2 = QVBoxLayout(group2)
        self.check_filter = QCheckBox("启用行过滤（只显示包含过滤关键词的行）")
        g2.addWidget(self.check_filter)

        self.filter_table = QTableWidget(0, 1)
        self.filter_table.setHorizontalHeaderLabels(["过滤关键词"])
        self.filter_table.verticalHeader().setVisible(False)
        self.filter_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        g2.addWidget(self.filter_table)

        row2 = QHBoxLayout()
        self.btn_filter_add = QPushButton("添加")
        self.btn_filter_add.clicked.connect(lambda: self._add_filter_row())
        self.btn_filter_remove = QPushButton("删除选中")
        self.btn_filter_remove.clicked.connect(self._remove_filter_selected)
        row2.addWidget(self.btn_filter_add)
        row2.addWidget(self.btn_filter_remove)
        row2.addStretch(1)
        g2.addLayout(row2)
        v.addWidget(group2)

        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.button(QDialogButtonBox.Ok).setText("确定")
        box.button(QDialogButtonBox.Cancel).setText("取消")
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        v.addWidget(box)

    def _load(self):
        s = QSettings("SerialTool", "SerialDebugAssistant")
        self.check_enable.setChecked(s.value(ENABLED_KEY, False, bool))
        for entry in s.value(KEYWORDS_KEY, [], list):
            if "|" in entry:
                kw, color = entry.split("|", 1)
                self._add_row(kw, color)
        if self.table.rowCount() == 0:
            self._add_row("", DEFAULT_COLOR)
        # 过滤关键词（独立于高亮关键词）
        self.check_filter.setChecked(s.value(FILTER_KEY, False, bool))
        for kw in s.value(FILTER_KEYWORDS_KEY, [], list):
            self._add_filter_row(kw)
        if self.filter_table.rowCount() == 0:
            self._add_filter_row("")

    def _add_row(self, keyword="", color=DEFAULT_COLOR):
        r = self.table.rowCount()
        self.table.insertRow(r)
        edit = QLineEdit(keyword)
        edit.setPlaceholderText("输入关键词")
        self.table.setCellWidget(r, 0, edit)
        btn = QPushButton(color)
        btn.setToolTip("点击选择颜色")
        btn.setStyleSheet(
            f"background: {color}; color: #111111; border-radius: 3px; border: 1px solid #888;"
        )
        btn.clicked.connect(lambda _, row=r: self._pick_color(row))
        self.table.setCellWidget(r, 1, btn)

    def _pick_color(self, row):
        btn = self.table.cellWidget(row, 1)
        color = QColorDialog.getColor(QColor(btn.text()), self, "选择字体颜色")
        if color.isValid():
            hex_ = color.name().upper()
            btn.setText(hex_)
            btn.setStyleSheet(
                f"background: {hex_}; color: #111111; border-radius: 3px; border: 1px solid #888;"
            )

    def _remove_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    # ---------------------------------------------------------- 过滤关键词
    def _add_filter_row(self, keyword=""):
        r = self.filter_table.rowCount()
        self.filter_table.insertRow(r)
        edit = QLineEdit(keyword)
        edit.setPlaceholderText("输入过滤关键词")
        self.filter_table.setCellWidget(r, 0, edit)

    def _remove_filter_selected(self):
        row = self.filter_table.currentRow()
        if row >= 0:
            self.filter_table.removeRow(row)

    def rules(self):
        """高亮表格里的 [(关键词, 颜色), ...]，空关键词已过滤。"""
        out = []
        for r in range(self.table.rowCount()):
            edit = self.table.cellWidget(r, 0)
            btn = self.table.cellWidget(r, 1)
            kw = edit.text().strip() if edit else ""
            color = btn.text() if btn else DEFAULT_COLOR
            if kw:
                out.append((kw, color))
        return out

    def filter_keywords(self):
        """过滤表格里的关键词列表（仅非空）。"""
        out = []
        for r in range(self.filter_table.rowCount()):
            edit = self.filter_table.cellWidget(r, 0)
            kw = edit.text().strip() if edit else ""
            if kw:
                out.append(kw)
        return out

    def accept(self):
        s = QSettings("SerialTool", "SerialDebugAssistant")
        s.setValue(ENABLED_KEY, self.check_enable.isChecked())
        s.setValue(KEYWORDS_KEY, [f"{kw}|{color}" for kw, color in self.rules()])
        s.setValue(FILTER_KEY, self.check_filter.isChecked())
        s.setValue(FILTER_KEYWORDS_KEY, self.filter_keywords())
        s.sync()
        super().accept()

# -*- coding: utf-8 -*-
"""全局深色主题样式表。"""

QSS = """
QMainWindow, QWidget {
    background-color: #1e222a;
    color: #d4d8e0;
    font-size: 12px;
}

/* 无边框主窗口：圆角 + 透明背景（最大化时取消圆角） */
#mainWindow {
    border-radius: 10px;
    background-color: #1e222a;
}
#mainWindow[winMaximized="true"] {
    border-radius: 0px;
}

QToolBar {
    background-color: #232833;
    border: none;
    border-bottom: 1px solid #343a47;
    padding: 4px;
    spacing: 8px;
}

QToolButton {
    background: transparent;
    border: 1px solid #3a4150;
    border-radius: 4px;
    padding: 4px 12px;
    color: #d4d8e0;
}
QToolButton:hover { background: #2f3542; }
QToolButton:pressed { background: #22262f; }
QToolButton:checked {
    background: #2d6fdb;
    border-color: #4a8bef;
    color: #ffffff;
}

QStatusBar {
    background: #232833;
    color: #9aa3b2;
}
QStatusBar::item { border: none; }
#statusBar {
    background: #232833;
    color: #9aa3b2;
    border-top: 1px solid #343a47;
    padding: 3px 8px;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}
#statusBar[winMaximized="true"] {
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}

QMenuBar {
    background: #232833;
    color: #d4d8e0;
}

QGroupBox {
    border: 1px solid #343a47;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 4px;
    font-weight: bold;
    color: #c3c9d4;
    background: #20242d;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #8fd0ff;
}

QLabel { background: transparent; }

QComboBox, QSpinBox {
    background: #14171d;
    border: 1px solid #343a47;
    border-radius: 4px;
    padding: 3px 8px;
    min-height: 18px;
}
QComboBox:disabled, QSpinBox:disabled {
    color: #5a6170;
    background: #20242d;
}
QComboBox QAbstractItemView {
    background: #1a1e26;
    border: 1px solid #343a47;
    selection-background-color: #2d6fdb;
    selection-color: #ffffff;
}

QLineEdit, QPlainTextEdit {
    background: #14171d;
    border: 1px solid #343a47;
    border-radius: 4px;
    color: #e6e9ef;
    selection-background-color: #2d6fdb;
    selection-color: #ffffff;
}
QPlainTextEdit {
    font-family: Consolas, "Courier New", "Microsoft YaHei Mono", monospace;
    font-size: 12px;
}

QPushButton {
    background: #2a303b;
    border: 1px solid #3a4150;
    border-radius: 4px;
    padding: 4px 12px;
    color: #d4d8e0;
}
QPushButton:hover { background: #333a48; }
QPushButton:pressed { background: #22262f; }
QPushButton:disabled { color: #5a6170; background: #232833; }

QPushButton#btnOpen {
    background: #1c6b3f;
    border-color: #2a9d5f;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btnOpen:hover { background: #238553; }

QPushButton#btnClose {
    background: #b3453f;
    border-color: #d65a53;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btnClose:hover { background: #c95049; }

QPushButton#btnSend {
    background: #1c5fa8;
    border-color: #3a86d8;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btnSend:hover { background: #2372c4; }

QCheckBox { spacing: 5px; background: transparent; }
QCheckBox::indicator { width: 14px; height: 14px; }

QScrollBar:vertical {
    background: #1a1e26;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a4150;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #4a5264; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #1a1e26;
    height: 10px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #3a4150;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #4a5264; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

#terminalPanel {
    border: 1px solid #343a47;
    border-radius: 6px;
    background: #1e222a;
}
#panelTitle { font-size: 13px; font-weight: bold; color: #e6e9ef; }
#statusDotOpen { color: #3ddc84; font-size: 14px; font-weight: bold; }
#statusDotClosed { color: #7a8291; font-size: 14px; }
#statusText { color: #9aa3b2; }

#titleBar {
    background-color: #232833;
    border: none;
    border-bottom: 1px solid #343a47;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
#titleBar[winMaximized="true"] {
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
}
#titleLabel { color: #e6e9ef; font-weight: bold; font-size: 13px; padding-left: 6px; }
#titleBtn {
    background: transparent;
    border: none;
    color: #b8bfcc;
    font-size: 15px;
    border-radius: 0;
    padding: 0;
}
#titleBtn:hover { background: #343a49; color: #ffffff; }
#titleBtnClose:hover { background: #d64545; color: #ffffff; }
"""


LIGHT_QSS = """
QMainWindow, QWidget {
    background-color: #f3f5f9;
    color: #2b3038;
    font-size: 12px;
}

/* 无边框主窗口：圆角 + 透明背景（最大化时取消圆角） */
#mainWindow {
    border-radius: 10px;
    background-color: #f3f5f9;
}
#mainWindow[winMaximized="true"] {
    border-radius: 0px;
}

QToolBar {
    background-color: #e9edf3;
    border: none;
    border-bottom: 1px solid #ccd3de;
    padding: 4px;
    spacing: 8px;
}

QToolButton {
    background: transparent;
    border: 1px solid #bcc5d1;
    border-radius: 4px;
    padding: 4px 12px;
    color: #2b3038;
}
QToolButton:hover { background: #dde3ec; }
QToolButton:pressed { background: #cfd7e2; }
QToolButton:checked {
    background: #3d7ee8;
    border-color: #5a95f0;
    color: #ffffff;
}

QStatusBar {
    background: #e9edf3;
    color: #6a7280;
}
QStatusBar::item { border: none; }
#statusBar {
    background: #e9edf3;
    color: #6a7280;
    border-top: 1px solid #ccd3de;
    padding: 3px 8px;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}
#statusBar[winMaximized="true"] {
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}

QMenuBar {
    background: #e9edf3;
    color: #2b3038;
}

QGroupBox {
    border: 1px solid #ccd3de;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 4px;
    font-weight: bold;
    color: #3a414d;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #1f6dc4;
}

QLabel { background: transparent; }

QComboBox, QSpinBox {
    background: #ffffff;
    border: 1px solid #c3cbd6;
    border-radius: 4px;
    padding: 3px 8px;
    min-height: 18px;
}
QComboBox:disabled, QSpinBox:disabled {
    color: #9aa2ae;
    background: #eef1f5;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #c3cbd6;
    selection-background-color: #3d7ee8;
    selection-color: #ffffff;
}

QLineEdit, QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #c3cbd6;
    border-radius: 4px;
    color: #1c2129;
    selection-background-color: #3d7ee8;
    selection-color: #ffffff;
}
QPlainTextEdit {
    font-family: Consolas, "Courier New", "Microsoft YaHei Mono", monospace;
    font-size: 12px;
}

QPushButton {
    background: #e4e9f0;
    border: 1px solid #c3cbd6;
    border-radius: 4px;
    padding: 4px 12px;
    color: #2b3038;
}
QPushButton:hover { background: #d7dee8; }
QPushButton:pressed { background: #c8d1dd; }
QPushButton:disabled { color: #9aa2ae; background: #eef1f5; }

QPushButton#btnOpen {
    background: #1f8a4d;
    border-color: #2aa862;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btnOpen:hover { background: #249f59; }

QPushButton#btnClose {
    background: #c0443d;
    border-color: #d65a53;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btnClose:hover { background: #d14d46; }

QPushButton#btnSend {
    background: #2d6fc8;
    border-color: #4b8ade;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btnSend:hover { background: #3a7ed6; }

QCheckBox { spacing: 5px; background: transparent; }
QCheckBox::indicator { width: 14px; height: 14px; }

QScrollBar:vertical { background: #eef1f5; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #b9c2cf; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #a4afbf; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #eef1f5; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #b9c2cf; border-radius: 5px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: #a4afbf; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

#terminalPanel {
    border: 1px solid #ccd3de;
    border-radius: 6px;
    background: #ffffff;
}
#panelTitle { font-size: 13px; font-weight: bold; color: #1c2129; }
#statusDotOpen { color: #1fa35a; font-size: 14px; font-weight: bold; }
#statusDotClosed { color: #a6aebc; font-size: 14px; }
#statusText { color: #6a7280; }

#titleBar {
    background-color: #e9edf3;
    border: none;
    border-bottom: 1px solid #ccd3de;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
#titleBar[winMaximized="true"] {
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
}
#titleLabel { color: #2b3038; font-weight: bold; font-size: 13px; padding-left: 6px; }
#titleBtn {
    background: transparent;
    border: none;
    color: #5a6270;
    font-size: 15px;
    border-radius: 0;
    padding: 0;
}
#titleBtn:hover { background: #d5dce6; color: #111111; }
#titleBtnClose:hover { background: #d64545; color: #ffffff; }
"""

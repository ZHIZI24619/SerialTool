# -*- coding: utf-8 -*-
"""
串口调试助手 · 多窗口

运行方式（任一）：
    python main.py
    python -m serial_tool
"""

import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from serial_tool.main_window import MainWindow
from serial_tool.resources import asset_path
from serial_tool.theme import QSS

ICON_PATH = asset_path("logo.ico")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("串口调试助手")
    app.setOrganizationName("SerialTool")
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    app.setWindowIcon(QIcon(ICON_PATH))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

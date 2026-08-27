# -*- coding: utf-8 -*-
"""
串口调试助手 · 多窗口

运行方式（任一）：
    python main.py
    python -m serial_tool
"""

import sys

from PyQt5.QtWidgets import QApplication

from serial_tool.main_window import MainWindow
from serial_tool.resources import make_rounded_logo_icon
from serial_tool.theme import QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("串口调试助手")
    app.setOrganizationName("SerialTool")
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    # 多尺寸圆角 logo 作为窗口/任务栏图标（每个尺寸独立圆角裁剪，无白点）
    app.setWindowIcon(make_rounded_logo_icon())
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

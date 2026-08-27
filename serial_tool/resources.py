# -*- coding: utf-8 -*-
"""资源文件路径助手：兼容源码运行与 PyInstaller 打包（--add-data "assets;assets"）。"""

import os
import sys


def asset_path(name):
    """返回 assets 目录下资源文件的绝对路径。"""
    if getattr(sys, "_MEIPASS", None):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", name)


def make_rounded_logo(size):
    """加载 logo.ico 并裁剪为圆角矩形，去掉四角白色背景。

    原 logo.ico 是白底方形图标，在暗色主题（夜间模式）下会露出白色边框。
    这里用 QPainter 圆角裁剪，保留蓝色主体，四角透明，适配深浅两种主题。
    返回 QPixmap。
    """
    from PyQt5.QtCore import QRectF, Qt
    from PyQt5.QtGui import QIcon, QPainter, QPainterPath, QPixmap

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    radius = size * 0.22
    clip.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(clip)
    painter.drawPixmap(0, 0, size, size, QIcon(asset_path("logo.ico")).pixmap(size, size))
    painter.end()
    return pm

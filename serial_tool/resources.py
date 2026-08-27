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


def make_rounded_logo_icon():
    """生成多尺寸圆角 logo 的 QIcon（基于 .ico 文件）。

    Windows 任务栏对 QIcon 动态生成的透明 pixmap 支持不佳（会显示方形+白点）。
    这里用 PIL 生成一个真正的多尺寸圆角 .ico 文件再加载，Windows 对其透明圆角
    的渲染是标准支持（与大多数圆角应用图标一致）。返回 QIcon。
    """
    from PyQt5.QtGui import QIcon

    return QIcon(_rounded_ico_path())


def _rounded_ico_path():
    """用 PIL 生成多尺寸圆角 logo 的 .ico 并返回路径。"""
    from PIL import Image, ImageDraw
    import tempfile

    ico_path = os.path.join(tempfile.gettempdir(), "SerialTool_rounded.ico")
    src = Image.open(asset_path("logo.ico")).convert("RGBA")
    src = src.resize((256, 256), Image.LANCZOS)
    mask = Image.new("L", (256, 256), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, 255, 255), radius=56, fill=255)
    result = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    result = Image.composite(src, result, mask)
    result.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    return ico_path

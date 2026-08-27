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

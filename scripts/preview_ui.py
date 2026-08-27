# -*- coding: utf-8 -*-
"""
离屏渲染各布局截图，用于 UI 预览与验证（不弹窗口）。
运行：python scripts/preview_ui.py
输出：串口工具/preview/layout_<数量>_<方向>.png
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication  # noqa: E402

from serial_tool.main_window import MainWindow  # noqa: E402
from serial_tool.theme import QSS  # noqa: E402

SAMPLE = (
    "HELLO - 串口调试助手多窗口演示\n"
    "line 1\nline 2\nline 3\n"
    "baud=115200 data=8 parity=N stop=1\n"
    "OK, command received.\r\n"
).encode("utf-8")


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)

    win = MainWindow()
    win.check_auto_size.setChecked(False)
    win.check_center.setChecked(False)
    win.show()
    app.processEvents()

    out = os.path.join(ROOT, "preview")
    os.makedirs(out, exist_ok=True)

    for count in (1, 2, 3, 4):
        for orient in ("horizontal", "vertical"):
            win.combo_count.setCurrentText(str(count))
            win.btn_layout.setChecked(orient == "vertical")
            app.processEvents()
            for p in win.panels[:count]:
                p._append_received(SAMPLE)
            win.resize(1000, 760)
            app.processEvents()
            pix = win.grab()
            path = os.path.join(out, f"layout_{count}_{orient}.png")
            pix.save(path)
            print("saved:", path)
            for p in win.panels[:count]:
                p.receive_view.clear()


if __name__ == "__main__":
    main()

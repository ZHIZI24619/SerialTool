# -*- coding: utf-8 -*-
"""在线更新模块：从 GitHub Releases 检查新版本、下载新版安装程序并启动。

无需单独上传 version.json，直接调 GitHub 公开 API 获取最新 Release：
    https://api.github.com/repos/{用户名}/{仓库名}/releases/latest
每次发版只需：打 tag（如 v0.2.0）+ 上传安装包 SerialTool-Setup-0.2.0.exe 到 Release 附件。
"""

import hashlib
import json
import os
import re
import tempfile
import time

from PyQt5.QtCore import Qt, QObject, QTimer, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog

from serial_tool import __version__

# GitHub 仓库（用户名/仓库名）
GITHUB_REPO = "ZHIZI24619/SerialTool"

# 安装包文件名前缀（在 Release 附件中据此挑出安装程序）
SETUP_PREFIX = "SerialTool-Setup-"

LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _log(msg):
    """把更新流程日志写到临时目录，便于排查下载/安装问题。"""
    try:
        log_path = os.path.join(tempfile.gettempdir(), "SerialTool_update.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except OSError:
        pass

# 检查结果状态（on_result 的第一个参数）
STATE_ERROR = "error"        # 网络/API/解析失败
STATE_NO_ASSET = "no_asset"  # Release 存在但缺少安装包附件
STATE_LATEST = "latest"      # 已是最新版本
STATE_FOUND = "found"        # 发现新版本


def _parse_version(v):
    """把版本号字符串解析为可比较的数字列表，如 '1.2.3' -> [1,2,3]。"""
    return [int(x) for x in re.split(r"[._\-]", str(v)) if x.isdigit()] or [0]


def is_newer(remote, current):
    """remote 版本是否比 current 新。"""
    return _parse_version(remote) > _parse_version(current)


class Updater(QObject):
    """异步检查更新 + 下载新版安装程序。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)

    # ---------------------------------------------------------- 检查更新
    def check(self, on_result):
        """异步检查更新。on_result(state, new_version, info)
        state 为 STATE_*；发现新版本时 new_version 为最新版本号，
        info 为 dict(version/url/sha256)。"""
        req = QNetworkRequest(QUrl(LATEST_RELEASE_URL))
        req.setTransferTimeout(15000)
        reply = self._nam.get(req)
        reply.finished.connect(lambda: self._on_check_finished(reply, on_result))

    def _on_check_finished(self, reply, on_result):
        try:
            if reply.error() != QNetworkReply.NoError:
                on_result(STATE_ERROR, None, None)
                return
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            # tag_name 形如 "v0.2.0"，去掉前导 v 得到版本号
            new_ver = str(data.get("tag_name", "")).lstrip("vV")
            url, sha = "", ""
            for asset in data.get("assets", []) or []:
                name = asset.get("name", "")
                if name.startswith(SETUP_PREFIX) and name.lower().endswith(".exe"):
                    url = asset.get("browser_download_url", "")
                    digest = asset.get("digest", "") or ""
                    if digest.startswith("sha256:"):
                        sha = digest[len("sha256:") :]
                    break
            if not new_ver or not url:
                on_result(STATE_NO_ASSET, None, None)
                return
            info = {"version": new_ver, "url": url, "sha256": sha}
            if is_newer(new_ver, __version__):
                on_result(STATE_FOUND, new_ver, info)
            else:
                on_result(STATE_LATEST, new_ver, info)
        except Exception:
            on_result(STATE_ERROR, None, None)
        finally:
            reply.deleteLater()

    # ------------------------------------------------------ 下载并安装
    def download_and_launch(self, parent, info):
        """下载新版安装程序（带进度），校验后启动安装。"""
        url = info.get("url", "")
        sha = str(info.get("sha256", "") or "")
        _log(f"开始下载更新: {url}")
        if not url:
            QMessageBox.warning(parent, "更新", "更新清单缺少下载地址")
            return

        fname = os.path.basename(QUrl(url).path()) or "SerialTool-update.exe"
        dest = os.path.join(tempfile.gettempdir(), fname)
        _log(f"目标文件: {dest}")

        # 无取消按钮：QProgressDialog 在 Windows 上会误触发 canceled 信号
        # （进度条完成/窗口处理时也被当成"取消"），导致下载被中断。
        prog = QProgressDialog("正在下载更新…", "", 0, 100, parent)
        prog.setWindowTitle("软件更新")
        prog.setWindowModality(Qt.WindowModal)
        prog.setAutoClose(False)
        prog.setAutoReset(False)
        prog.setMinimumDuration(0)
        prog.show()

        req = QNetworkRequest(QUrl(url))
        # 40MB 安装包，放宽超时到 5 分钟，避免慢网络下超时中断
        req.setTransferTimeout(300000)
        # 显式跟随下载链接重定向（GitHub release 下载会 302 到资产 CDN）
        req.setAttribute(
            QNetworkRequest.RedirectPolicyAttribute,
            QNetworkRequest.NoLessSafeRedirectPolicy,
        )
        reply = self._nam.get(req)

        def on_progress(received, total):
            prog.setMaximum(max(1, total))
            prog.setValue(received)

        def on_finished():
            error = reply.error()
            # finished 时一次性读取全部数据（比 readyRead 收集更可靠）
            payload = bytes(reply.readAll())
            reply.deleteLater()
            if error != QNetworkReply.NoError:
                prog.close()
                msg = f"下载更新失败：{reply.errorString()}（错误码 {int(error)}）"
                _log(msg)
                QMessageBox.warning(parent, "更新", msg + "\n请检查网络后重试。")
                return
            _log(f"下载完成：{len(payload)} 字节")
            try:
                if sha and hashlib.sha256(payload).hexdigest().lower() != sha.lower():
                    _log("sha256 校验失败")
                    prog.close()
                    QMessageBox.warning(parent, "更新", "下载文件校验失败，已中止更新")
                    return
                if len(payload) < 1024:
                    _log(f"下载内容异常：仅 {len(payload)} 字节")
                    prog.close()
                    QMessageBox.warning(
                        parent,
                        "更新",
                        f"下载内容异常（仅 {len(payload)} 字节），已中止更新",
                    )
                    return
                with open(dest, "wb") as f:
                    f.write(payload)
            except OSError as exc:
                _log(f"保存更新文件失败: {exc}")
                prog.close()
                QMessageBox.warning(parent, "更新", f"保存更新文件失败：{exc}")
                return
            _log(f"已保存：{dest}（{os.path.getsize(dest)} 字节）")
            # 下载成功：进度条窗口保持显示，提示即将启动安装程序（不突然消失）
            prog.setMaximum(100)
            prog.setValue(100)
            prog.setLabelText("下载完成，正在启动安装程序…")
            try:
                os.startfile(dest)
                _log("已启动安装程序")
            except OSError as exc:
                _log(f"启动安装程序失败: {exc}")
                prog.close()
                QMessageBox.warning(
                    parent,
                    "更新",
                    f"启动安装程序失败：{exc}\n请手动运行：\n{dest}",
                )
                return
            # 保持窗口显示片刻，然后自动退出本程序（安装程序接管；5 秒兜底强退）
            QTimer.singleShot(1500, QApplication.instance().quit)
            QTimer.singleShot(5000, lambda: os._exit(0))
            _log("更新流程完成，即将退出本程序")

        reply.downloadProgress.connect(on_progress)
        reply.finished.connect(on_finished)

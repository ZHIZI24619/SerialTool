# -*- coding: utf-8 -*-
"""创建 GitHub Release 并上传安装包。

用法（在你自己终端设置 token，不要粘贴给任何人）：
    $env:GITHUB_TOKEN = "ghp_你的token"
    python scripts/create_release.py

会自动：1) 创建/更新 Release v0.1.1  2) 上传 installer\SerialTool-Setup-0.1.1.exe
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "ZHIZI24619/SerialTool"
TAG = "v0.1.3"
NAME = "v0.1.3"
BODY = (
    "## v0.1.3 更新\n\n"
    "- 修复标题栏太阳/月亮图标黑色边框问题（改为自绘无描边图标）\n"
    "- 修复更新下载失败无提示、放宽超时并跟随重定向（v0.1.2）\n"
)
API = "https://api.github.com"
UPLOAD_API = "https://uploads.github.com"
ASSET = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "installer",
    "SerialTool-Setup-0.1.3.exe",
)


def _headers():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("错误：未设置 GITHUB_TOKEN 环境变量")
        sys.exit(1)
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "release-script",
    }


def _request(method, url, payload=None, headers=None, raw=False):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    h = dict(_headers())
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            if raw:
                return resp.status, body
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        print(f"API 错误 {e.code}: {e.read().decode('utf-8', errors='replace')[:800]}")
        sys.exit(1)


def main():
    if not os.path.exists(ASSET):
        print(f"找不到安装包: {ASSET}")
        sys.exit(1)

    # 0) 校验 token
    status, me = _request("GET", f"{API}/user")
    if status == 200:
        print(f"token 有效，账号：{me.get('login')}")
    else:
        print("token 无效（401）——请重新生成并勾选 repo 权限后再试")
        sys.exit(1)

    # 1) 创建或复用 Release
    status, existing = _request("GET", f"{API}/repos/{REPO}/releases/tags/{TAG}")
    if status == 200:
        print(f"Release {TAG} 已存在，复用")
        release_id = existing["id"]
    else:
        payload = {
            "tag_name": TAG,
            "target_commitish": "main",
            "name": NAME,
            "body": BODY,
            "draft": False,
            "prerelease": False,
        }
        _, rel = _request("POST", f"{API}/repos/{REPO}/releases", payload)
        print(f"Release 已创建: {rel.get('html_url')}")
        release_id = rel["id"]

    # 2) 上传安装包
    fname = os.path.basename(ASSET)
    with open(ASSET, "rb") as f:
        content = f.read()
    url = f"{UPLOAD_API}/repos/{REPO}/releases/{release_id}/assets?name={urllib.parse.quote(fname)}"
    _, resp = _request(
        "POST",
        url,
        payload=content,
        headers={"Content-Type": "application/octet-stream"},
    )
    print(f"安装包上传成功: {resp.get('browser_download_url')}")
    print("发布完成 ✅")


if __name__ == "__main__":
    main()

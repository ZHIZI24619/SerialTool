# -*- coding: utf-8 -*-
"""通过 GitHub Git Data API 推送本地代码到仓库（绕开被拦截的 git.exe）。

用法：
    1. 在自己的终端设置 token（不要粘贴给任何人）：
       $env:GITHUB_TOKEN = "ghp_你的token"
    2. 运行本脚本：
       python scripts/push_to_github.py
仅推送到 ZHIZI24619/SerialTool，内容为 串口工具/ 目录（忽略构建产物）。
"""

import base64
import json
import mimetypes
import os
import sys
import urllib.request

REPO = "ZHIZI24619/SerialTool"
BRANCH = "main"
API = "https://api.github.com"
# 项目根（脚本位于 串口工具/scripts/ 下）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 需要忽略的目录/文件（与 .gitignore 一致）
IGNORE_DIRS = {
    ".git",
    "build",
    "dist",
    "__pycache__",
    ".vscode",
    "preview",
    "installer",
}
IGNORE_FILES = {".gitignore", "*.spec"}


def _headers():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("错误：未设置 GITHUB_TOKEN 环境变量")
        sys.exit(1)
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "push-script",
    }


def _request(method, url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API 错误 {e.code}: {body[:500]}")
        sys.exit(1)


def _collect_files():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            if name == "SerialTool.spec":
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT).replace("\\", "/")
            files.append(rel)
    return sorted(files)


def main():
    print(f"推送 {ROOT} -> {REPO} 分支 {BRANCH}")
    # 0) 先校验 token 有效性，给出明确提示
    status, me = _request("GET", f"{API}/user")
    if status == 200:
        print(f"token 有效，账号：{me.get('login')}")
    else:
        print("token 无效（401）——请重新生成并勾选 repo 权限后再试")
        sys.exit(1)

    files = _collect_files()
    print(f"共 {len(files)} 个文件")

    # 1) 获取当前分支最新提交（仓库可能为空）
    status, ref = _request("GET", f"{API}/repos/{REPO}/branches/{BRANCH}")
    base_sha = ref.get("commit", {}).get("sha", "") if status == 200 else ""

    # 2) 创建 blobs
    tree = []
    for rel in files:
        path = os.path.join(ROOT, rel)
        with open(path, "rb") as f:
            content = f.read()
        if rel.endswith(".ico") or rel.endswith(".png") or rel.endswith(".exe"):
            enc = base64.b64encode(content).decode("ascii")
            _, resp = _request(
                "POST",
                f"{API}/repos/{REPO}/git/blobs",
                {"content": enc, "encoding": "base64"},
            )
            tree.append(
                {"path": rel, "mode": "100644", "type": "blob", "sha": resp["sha"]}
            )
        else:
            text = content.decode("utf-8", errors="replace")
            _, resp = _request(
                "POST",
                f"{API}/repos/{REPO}/git/blobs",
                {"content": text, "encoding": "utf-8"},
            )
            tree.append(
                {"path": rel, "mode": "100644", "type": "blob", "sha": resp["sha"]}
            )
        print(f"  blob: {rel}")

    # 3) 创建 tree（含父提交）
    tree_payload = {"tree": tree}
    if base_sha:
        tree_payload["base_tree"] = base_sha
    _, tree_resp = _request("POST", f"{API}/repos/{REPO}/git/trees", tree_payload)
    tree_sha = tree_resp["sha"]

    # 4) 创建 commit
    commit_payload = {
        "message": "串口调试助手：多窗口串口工具（含检查更新与安装脚本）",
        "tree": tree_sha,
    }
    if base_sha:
        commit_payload["parents"] = [base_sha]
    _, commit_resp = _request("POST", f"{API}/repos/{REPO}/git/commits", commit_payload)
    commit_sha = commit_resp["sha"]

    # 5) 更新分支引用（空仓库用 create ref）
    try:
        _, ref_resp = _request(
            "PATCH",
            f"{API}/repos/{REPO}/git/refs/heads/{BRANCH}",
            {"sha": commit_sha, "force": True},
        )
        print("分支已更新 ->", ref_resp.get("object", {}).get("sha"))
    except SystemExit:
        # 空仓库：创建引用
        _, ref_resp = _request(
            "POST",
            f"{API}/repos/{REPO}/git/refs",
            {"ref": f"refs/heads/{BRANCH}", "sha": commit_sha},
        )
        print("分支已创建 ->", ref_resp.get("object", {}).get("sha"))

    print("推送完成！")


if __name__ == "__main__":
    main()

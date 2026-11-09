#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeViewCam Linux/Ubuntu 发布包一键打包脚本
精确定制打包内容，严格排除历史归档、缓存、虚拟环境及 Windows 库文件，
并将打包结果同步部署到工作区根目录与子目录。
"""

import os
import sys
import shutil
import tarfile

VERSION = "0.1.5"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OPEN_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

OUTPUT_PKG_NAME = f"weviewcam_ubuntu_v{VERSION}.tar.gz"
LATEST_PKG_NAME = "weviewcam_ubuntu.tar.gz"

EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode",
    "logs", "dist", "build", "HCNetSDKV6.1.11.30", "win64"
}

EXCLUDE_EXTENSIONS = {
    ".tar.gz", ".zip", ".tgz", ".7z", ".bat", ".exe", ".dll", ".pyc"
}

INCLUDED_TOP_ITEMS = [
    "core", "adapters", "ui", "config_template", "sdk", "tests",
    "main.py", "requirements.txt", "install.sh", "run.sh", "icon.png", "README.md"
]


def tar_filter(tarinfo: tarfile.TarInfo):
    name = tarinfo.name
    base = os.path.basename(name)
    parts = name.replace("\\", "/").split("/")

    # 排除特定目录
    for p in parts:
        if p in EXCLUDE_DIRS:
            return None
        if "win64" in p.lower():
            return None

    # 排除特定文件后缀或历史归档
    for ext in EXCLUDE_EXTENSIONS:
        if base.endswith(ext):
            return None

    if "weviewcam_ubuntu" in base.lower():
        return None

    # 替换敏感的 config/devices.json 为模板空列表
    if name == "config/devices.json":
        return None

    # 设置 Linux 执行权限 (run.sh, install.sh)
    if base.endswith(".sh"):
        tarinfo.mode = 0o755
    else:
        if tarinfo.isdir():
            tarinfo.mode = 0o755
        else:
            tarinfo.mode = 0o644

    tarinfo.uname = "root"
    tarinfo.gname = "root"
    return tarinfo


def main():
    print(f"=== 开始打包 WeViewCam Ubuntu 发布包 v{VERSION} ===")
    os.chdir(SCRIPT_DIR)

    temp_pkg = os.path.join(SCRIPT_DIR, OUTPUT_PKG_NAME)
    if os.path.exists(temp_pkg):
        os.remove(temp_pkg)

    with tarfile.open(temp_pkg, "w:gz") as tar:
        for item in INCLUDED_TOP_ITEMS:
            full_path = os.path.join(SCRIPT_DIR, item)
            if not os.path.exists(full_path):
                print(f"[跳过] 不存在的顶层项: {item}")
                continue
            print(f"[打包中] 添加: {item}")
            tar.add(full_path, arcname=item, filter=tar_filter)

        # 写入默认空 config/devices.json
        dev_json_template = os.path.join(SCRIPT_DIR, "config_template", "devices.json")
        if os.path.exists(dev_json_template):
            tar.add(dev_json_template, arcname="config/devices.json")
        else:
            import io
            dummy_data = b"[]\n"
            ti = tarfile.TarInfo("config/devices.json")
            ti.size = len(dummy_data)
            ti.mode = 0o644
            tar.addfile(ti, io.BytesIO(dummy_data))

    pkg_size_mb = os.path.getsize(temp_pkg) / (1024 * 1024)
    print(f"=== 打包成功: {OUTPUT_PKG_NAME} ({pkg_size_mb:.2f} MB) ===")

    # 复制到各目标位置
    target_locations = [
        (SCRIPT_DIR, OUTPUT_PKG_NAME),
        (SCRIPT_DIR, LATEST_PKG_NAME),
        (OPEN_DIR, OUTPUT_PKG_NAME),
        (OPEN_DIR, LATEST_PKG_NAME),
        (PROJECT_ROOT, OUTPUT_PKG_NAME),
        (PROJECT_ROOT, LATEST_PKG_NAME),
    ]

    for dir_path, f_name in target_locations:
        dest_file = os.path.join(dir_path, f_name)
        if dest_file != temp_pkg:
            shutil.copy2(temp_pkg, dest_file)
        print(f"[部署] -> {dest_file}")

    print("=== 全流程发布包同步完成 ===")


if __name__ == "__main__":
    main()

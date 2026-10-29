#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeViewCam Windows Standalone Release Packaging Script.
Builds and packages WeViewCam.exe with PyQt5 and Hikvision Win64 SDK into a clean distribution.
Strictly ensures user's private device configuration is NOT included in the release package.
"""

import os
import sys
import shutil
import zipfile
import subprocess

VERSION = "0.1.3"

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)

    out_name = f"weviewcam_windows_v{VERSION}.zip"
    latest_name = "weviewcam_windows.zip"
    out_path = os.path.join(base_dir, out_name)
    latest_path = os.path.join(base_dir, latest_name)
    workspace_out = os.path.join(root_dir, out_name)

    dist_dir = os.path.join(base_dir, "dist", "WeViewCam")
    spec_file = os.path.join(base_dir, "WeViewCam.spec")

    # Clean legacy version zips
    legacy_zips = [
        os.path.join(base_dir, "weviewcam_windows_v0.1.2.zip"),
        os.path.join(root_dir, "weviewcam_windows_v0.1.2.zip"),
        out_path,
        latest_path
    ]
    for p in legacy_zips:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    # Ensure config_template/devices.json exists with []
    template_dir = os.path.join(base_dir, "config_template")
    os.makedirs(template_dir, exist_ok=True)
    with open(os.path.join(template_dir, "devices.json"), "w", encoding="utf-8") as f:
        f.write("[]\n")

    # Step 1: Execute PyInstaller compilation using WeViewCam.spec
    print(f"正在执行 PyInstaller 编译 v{VERSION} ...")
    subprocess.check_call(["pyinstaller", "--noconfirm", spec_file], cwd=base_dir)

    # Step 2: Ensure convenient root files exist in dist/WeViewCam
    sdk_src = os.path.join(base_dir, "sdk")
    sdk_dst = os.path.join(dist_dir, "sdk")
    if os.path.exists(sdk_src) and not os.path.exists(sdk_dst):
        shutil.copytree(sdk_src, sdk_dst, dirs_exist_ok=True)

    for f in ["icon.ico", "icon.png", "README.md"]:
        src_f = os.path.join(base_dir, f)
        dst_f = os.path.join(dist_dir, f)
        if os.path.exists(src_f):
            shutil.copy2(src_f, dst_f)

    # Step 3: STRICT PRIVACY SANITIZATION
    # Overwrite any devices.json in dist with clean empty array []
    dist_cfg = os.path.join(dist_dir, "config", "devices.json")
    os.makedirs(os.path.dirname(dist_cfg), exist_ok=True)
    with open(dist_cfg, "w", encoding="utf-8") as f:
        f.write("[]\n")
    print("  -> 已重置发布包中 config/devices.json 为纯净空模板 [] (避免打包本地用户设备)")

    internal_cfg = os.path.join(dist_dir, "_internal", "config", "devices.json")
    if os.path.exists(os.path.dirname(internal_cfg)):
        with open(internal_cfg, "w", encoding="utf-8") as f:
            f.write("[]\n")

    print(f"正在打包 WeViewCam Windows 独立可执行程序发布包: {out_name} ...")

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(dist_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
            for f in files:
                if f.endswith(".pyc"):
                    continue
                full_f = os.path.join(root, f)
                rel_f = os.path.relpath(full_f, os.path.dirname(dist_dir))
                zf.write(full_f, arcname=rel_f)

    # Copy to latest and workspace root
    shutil.copy2(out_path, latest_path)
    shutil.copy2(out_path, workspace_out)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\n========================================================")
    print(f"Windows EXE 打包成功 (v{VERSION})!")
    print(f"发布压缩包: {out_path} ({size_mb:.2f} MB)")
    print(f"工作区副本: {workspace_out}")
    print(f"隐私安全核查: 已完全剔除任何用户私有设备配置")
    print(f"========================================================")

if __name__ == "__main__":
    main()

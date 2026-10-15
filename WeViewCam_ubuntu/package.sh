#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 一键打包脚本 (Linux / Ubuntu)
# 排除无关的 Demo 示例、虚拟环境和缓存文件，生成精简发布包
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="0.1.1"
OUTPUT_NAME="weviewcam_ubuntu.tar.gz"
VERSIONED_NAME="weviewcam_ubuntu_v${VERSION}.tar.gz"

echo "正在打包工程到 $VERSIONED_NAME 与 $OUTPUT_NAME ..."
tar -czvf "$OUTPUT_NAME" \
    --exclude="*.zip" \
    --exclude="HCNetSDKV6.1.11.30*" \
    --exclude="*.tar.gz" \
    --exclude="__pycache__" \
    --exclude=".pytest_cache" \
    --exclude=".venv" \
    --exclude="logs" \
    core adapters ui config sdk tests main.py scan_rtsp.py requirements.txt setup_env.sh install.sh run.sh install_desktop_shortcut.sh weviewcam.desktop icon.png README.md

cp "$OUTPUT_NAME" "$VERSIONED_NAME"
cp "$OUTPUT_NAME" "../$VERSIONED_NAME" 2>/dev/null || true

echo "打包完成: $VERSIONED_NAME 与 $OUTPUT_NAME (大小: $(du -sh $OUTPUT_NAME | cut -f1))"

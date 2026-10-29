#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 一键打包脚本 (Linux / Ubuntu)
# 排除无关的 Demo 示例、虚拟环境和缓存文件，生成精简发布包
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="0.1.3"
OUTPUT_NAME="weviewcam_ubuntu.tar.gz"
VERSIONED_NAME="weviewcam_ubuntu_v${VERSION}.tar.gz"

echo "正在打包工程到 $VERSIONED_NAME 与 $OUTPUT_NAME ..."

# 确保打包中的 config 使用空配置模板
TMP_DIR=$(mktemp -d)
mkdir -p "$TMP_DIR/config"
cp config_template/devices.json "$TMP_DIR/config/devices.json" 2>/dev/null || echo "[]" > "$TMP_DIR/config/devices.json"

tar -czvf "$OUTPUT_NAME" \
    --exclude="*.zip" \
    --exclude="HCNetSDKV6.1.11.30*" \
    --exclude="*.tar.gz" \
    --exclude="__pycache__" \
    --exclude=".pytest_cache" \
    --exclude=".venv" \
    --exclude="venv" \
    --exclude="logs" \
    --exclude="sdk/hikvision/win64" \
    --exclude="sdk/hikvision/lib/*.dll" \
    --exclude="*.bat" \
    --exclude="*.exe" \
    --exclude="WeViewCam.spec" \
    --exclude="config/devices.json" \
    core adapters ui config_template sdk tests main.py requirements.txt install.sh run.sh icon.png README.md

# 将脱敏的 config/devices.json 打入包内
tar -rf "$OUTPUT_NAME" -C "$TMP_DIR" config/devices.json 2>/dev/null || true
rm -rf "$TMP_DIR"

cp "$OUTPUT_NAME" "$VERSIONED_NAME"
cp "$OUTPUT_NAME" "../$VERSIONED_NAME" 2>/dev/null || true

echo "打包完成: $VERSIONED_NAME 与 $OUTPUT_NAME"

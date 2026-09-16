#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 桌面快捷方式一键生成与安装脚本 (Ubuntu Linux)
# 支持一键在用户桌面及应用菜单创建图标，双击即可无缝启动监控客户端
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "正在为 WeViewCam 创建桌面启动图标..."
echo "=========================================================="

# 1. 确保核心运行脚本有可执行权限
chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true
if [ -f "$SCRIPT_DIR/setup_env.sh" ]; then
    chmod +x "$SCRIPT_DIR/setup_env.sh" 2>/dev/null || true
fi

# 2. 检查图标文件
ICON_FILE="$SCRIPT_DIR/icon.png"
if [ ! -f "$ICON_FILE" ]; then
    if [ -f "$SCRIPT_DIR/图标.jpg" ]; then
        ICON_FILE="$SCRIPT_DIR/图标.jpg"
    fi
fi

# 3. 动态获取用户桌面路径 (兼容中文'桌面'与英文'Desktop'系统)
DESKTOP_DIR=""
if command -v xdg-user-dir &> /dev/null; then
    DESKTOP_DIR=$(xdg-user-dir DESKTOP)
fi

if [ -z "$DESKTOP_DIR" ] || [ ! -d "$DESKTOP_DIR" ]; then
    if [ -d "$HOME/桌面" ]; then
        DESKTOP_DIR="$HOME/桌面"
    elif [ -d "$HOME/Desktop" ]; then
        DESKTOP_DIR="$HOME/Desktop"
    else
        DESKTOP_DIR="$HOME/Desktop"
        mkdir -p "$DESKTOP_DIR"
    fi
fi

# 4. 生成标准 .desktop 文件内容
TEMP_DESKTOP="/tmp/weviewcam.desktop"
cat <<EOF > "$TEMP_DESKTOP"
[Desktop Entry]
Version=1.0
Type=Application
Name=WeViewCam 监控系统
GenericName=视频监控与回放客户端
Comment=实时视频监控、云台控制与历史录像回放平台
Exec=/bin/bash -c "cd '$SCRIPT_DIR' && bash run.sh"
Icon=$ICON_FILE
Terminal=false
Categories=AudioVideo;Video;Surveillance;
StartupNotify=true
StartupWMClass=WeViewCam
EOF

# 5. 安装到桌面
TARGET_DESKTOP="$DESKTOP_DIR/weviewcam.desktop"
cp "$TEMP_DESKTOP" "$TARGET_DESKTOP"
chmod +x "$TARGET_DESKTOP"

# 解决 Ubuntu GNOME 桌面环境的“允许启动 (Allow Launching)”信任限制
if command -v gio &> /dev/null; then
    gio set "$TARGET_DESKTOP" metadata::trusted true 2>/dev/null || true
fi

# 6. 同时安装到系统应用程序列表 (可从 Ubuntu 九宫格/Dash 搜索启动并常驻 Dock 栏)
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_DIR"
TARGET_APP="$APP_DIR/weviewcam.desktop"
cp "$TEMP_DESKTOP" "$TARGET_APP"
chmod +x "$TARGET_APP"

# 更新桌面数据库缓存 (如果有的话)
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

rm -f "$TEMP_DESKTOP"

echo "=========================================================="
echo "🎉 桌面快捷方式创建成功！"
echo "  - 桌面图标位置: $TARGET_DESKTOP"
echo "  - 应用菜单位置: $TARGET_APP"
echo ""
echo "💡 使用提示:"
echo "  现在您可以直接回到 Ubuntu 桌面，双击【WeViewCam 监控系统】彩色图标启动！"
echo "  (如果个别 Ubuntu 版本初次双击弹出确认，右键选择'允许启动 / Allow Launching'即可)"
echo "=========================================================="

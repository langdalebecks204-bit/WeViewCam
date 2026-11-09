#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 视频监控平台 Ubuntu / Linux 一键安装与配置脚本 (v0.1.5)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "🚀 开始一键安装与配置 WeViewCam Linux 运行环境..."
echo "=========================================================="

# 1. 安装系统依赖 (支持 Debian / Ubuntu 体系)
if command -v apt-get &> /dev/null; then
    echo "[INFO] 检测到 Debian/Ubuntu 体系，正在通过 apt 安装系统核心运行库与硬件播放引擎..."
    sudo apt-get update || true
    sudo apt-get install -y python3 python3-pip python3-pyqt5 python3-opencv ffmpeg \
        libvlc-dev vlc python3-vlc \
        libgl1 libglib2.0-0 fonts-wqy-zenhei libxcb-xinerama0 libxcb-icccm4 \
        libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
        libva2 libva-drm2 libva-x11-2 || {
            echo "[WARN] 部分 apt 包安装跳过，继续安装 Python 依赖..."
        }
elif command -v dnf &> /dev/null; then
    echo "[INFO] 检测到 Fedora/RHEL/openEuler 体系..."
    sudo dnf install -y python3 python3-pip python3-qt5 vlc-devel vlc mesa-libGL glib2 libX11 libxcb || true
elif command -v yum &> /dev/null; then
    echo "[INFO] 检测到 CentOS 体系..."
    sudo yum install -y python3 python3-pip vlc mesa-libGL glib2 libX11 libxcb || true
fi

# 2. 安装 Python 依赖
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo "[INFO] 正在安装 Python 依赖库..."
    pip3 install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages 2>/dev/null || \
    pip3 install -r "$SCRIPT_DIR/requirements.txt" || \
    pip install -r "$SCRIPT_DIR/requirements.txt" || {
        echo "[WARN] 部分 pip 依赖安装提示，如果系统已具备 PyQt5 和 requests，可直接启动。"
    }
fi

# 3. 赋予脚本执行权限
chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/main.py" 2>/dev/null || true

# 4. 生成桌面快捷方式与系统菜单项
DESKTOP_FILE="$HOME/Desktop/WeViewCam.desktop"
if [ ! -d "$HOME/Desktop" ] && [ -d "$HOME/桌面" ]; then
    DESKTOP_FILE="$HOME/桌面/WeViewCam.desktop"
fi

ICON_PATH="$SCRIPT_DIR/icon.png"
if [ ! -f "$ICON_PATH" ]; then
    ICON_PATH="$SCRIPT_DIR/图标.jpg"
fi

cat > "$SCRIPT_DIR/WeViewCam.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WeViewCam 视频监控
GenericName=Video Surveillance System
Comment=Multi-Protocol Video Surveillance Application (Hikvision, Dahua, ONVIF)
Exec=bash "$SCRIPT_DIR/run.sh"
Icon=$ICON_PATH
Path=$SCRIPT_DIR
Terminal=false
Categories=AudioVideo;Video;Player;Network;
StartupNotify=true
EOF

chmod +x "$SCRIPT_DIR/WeViewCam.desktop"

# 复制到用户桌面和系统应用列表
if [ -d "$(dirname "$DESKTOP_FILE")" ]; then
    cp "$SCRIPT_DIR/WeViewCam.desktop" "$DESKTOP_FILE"
    chmod +x "$DESKTOP_FILE"
fi

mkdir -p "$HOME/.local/share/applications" 2>/dev/null || true
cp "$SCRIPT_DIR/WeViewCam.desktop" "$HOME/.local/share/applications/" 2>/dev/null || true

echo "=========================================================="
echo "🎉 WeViewCam 安装与配置完成！"
echo "  - 启动方式 1: 在终端中执行: cd $SCRIPT_DIR && ./run.sh"
echo "  - 启动方式 2: 双击桌面上的【WeViewCam 视频监控】图标"
echo "=========================================================="

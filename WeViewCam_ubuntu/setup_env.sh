#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 视频监控软件 Ubuntu 环境自动化初始化与 Python 虚拟环境配置脚本
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "正在检查系统运行环境..."
echo "========================================================"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先运行: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "检测到 $PYTHON_VERSION"

# 创建或校验虚拟环境
VENV_DIR="$SCRIPT_DIR/.venv"
VENV_ACTIVATE="$VENV_DIR/bin/activate"

# 如果不存在 activate 脚本，说明未创建或此前创建损坏，先清理再重建
if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "正在创建 Python 虚拟环境: $VENV_DIR ..."
    rm -rf "$VENV_DIR"

    # 执行创建并捕获异常
    if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
        echo ""
        echo "========================================================"
        echo "❌ 虚拟环境创建失败！"
        echo "Debian/Ubuntu 系统默认未自带 venv 工具包，请在终端执行以下命令安装："
        echo ""
        echo "  sudo apt update && sudo apt install -y python3-venv python3-pip libgl1-mesa-glx libx11-xcb1 ibus-gtk ibus-gtk3 libibus-1.0-5 libvlc-dev vlc"
        echo ""
        echo "安装完成后，重新运行: bash setup_env.sh"
        echo "========================================================"
        exit 1
    fi
    echo "虚拟环境创建完成。"
else
    echo "虚拟环境已存在且有效: $VENV_DIR"
fi

# 激活虚拟环境
echo "正在激活虚拟环境并安装项目依赖..."
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"

# 升级 pip
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple || pip install --upgrade pip

# 安装依赖
echo "正在安装 requirements.txt ..."
pip install -r "$SCRIPT_DIR/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple || pip install -r "$SCRIPT_DIR/requirements.txt"

# 自动配置与修复 Linux/Ubuntu 中文输入法支持 (IBus / Fcitx)
echo "正在检查并配置 Qt5 中文输入法插件支持..."
VENV_INPUT_DIR=$(find "$VENV_DIR" -type d -path "*/PyQt5/Qt5/plugins/platforminputcontexts" 2>/dev/null | head -n 1)
if [ -n "$VENV_INPUT_DIR" ]; then
    SYS_INPUT_PATHS=(
        "/usr/lib/x86_64-linux-gnu/qt5/plugins/platforminputcontexts"
        "/usr/lib/qt5/plugins/platforminputcontexts"
    )
    LINK_COUNT=0
    for sys_dir in "${SYS_INPUT_PATHS[@]}"; do
        if [ -d "$sys_dir" ]; then
            for plugin_so in "$sys_dir"/lib*platforminputcontextplugin.so; do
                if [ -f "$plugin_so" ]; then
                    fname=$(basename "$plugin_so")
                    if [ ! -f "$VENV_INPUT_DIR/$fname" ]; then
                        ln -sf "$plugin_so" "$VENV_INPUT_DIR/$fname" 2>/dev/null || cp "$plugin_so" "$VENV_INPUT_DIR/$fname" 2>/dev/null || true
                        LINK_COUNT=$((LINK_COUNT + 1))
                    fi
                fi
            done
        fi
    done
    if [ "$LINK_COUNT" -gt 0 ]; then
        echo "已成功将 $LINK_COUNT 个系统输入法插件集成至虚拟环境中。"
    else
        echo "输入法插件状态良好。"
    fi
fi

echo "========================================================"
echo "环境配置成功！"
# 检查视频解码引擎状态
if ldconfig -p 2>/dev/null | grep -q "libvlc.so"; then
    echo "💡 视频引擎: 已检测到 LibVLC 原生硬件加速库。"
else
    echo "💡 视频引擎: 已启用内置 OpenCV 解码引擎 (无需系统级 VLC，零依赖即开即用)。"
fi
echo "========================================================"

# 自动为用户生成桌面与应用中心启动图标
if [ -f "$SCRIPT_DIR/install_desktop_shortcut.sh" ]; then
    bash "$SCRIPT_DIR/install_desktop_shortcut.sh"
else
    echo "您可以通过运行以下命令启动监控软件:"
    echo "  bash run.sh"
fi

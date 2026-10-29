#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 视频监控平台 Ubuntu 一键安装与配置脚本 (v0.1.2)
# 自动化完成：系统依赖检测、Python 虚拟环境搭建、pip 依赖安装、
# Qt5 中文输入法适配、桌面启动图标创建与系统应用列表集成
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "🚀 开始一键安装与配置 WeViewCam Ubuntu 客户端 (v0.1.2)..."
echo "=========================================================="

# 1. 确保核心运行脚本具有可执行权限
chmod +x "$SCRIPT_DIR/setup_env.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/install_desktop_shortcut.sh" 2>/dev/null || true

# 2. 执行环境初始化与 Python 依赖安装
bash "$SCRIPT_DIR/setup_env.sh"

# 3. 创建桌面快捷方式与系统应用菜单项
if [ -f "$SCRIPT_DIR/install_desktop_shortcut.sh" ]; then
    bash "$SCRIPT_DIR/install_desktop_shortcut.sh"
fi

echo "=========================================================="
echo "🎉 WeViewCam Ubuntu 客户端安装完成！"
echo "  - 启动方式 1: 直接双击 Ubuntu 桌面上的【WeViewCam 监控系统】彩色图标"
echo "  - 启动方式 2: 在终端运行: cd $SCRIPT_DIR && bash run.sh"
echo "=========================================================="

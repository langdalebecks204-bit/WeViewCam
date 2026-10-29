#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 视频监控软件启动脚本 (Ubuntu x86_64)
# 自动配置海康 SDK 动态库搜索路径 (LD_LIBRARY_PATH) 并启动程序
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 自动搜寻海康威视 Linux 64位 SDK 库文件目录
SDK_LIB_DIR=""
POSSIBLE_PATHS=(
    "$SCRIPT_DIR/HCNetSDKV6.1.11.30_build20260805_linux64_20260812103926/HCNetSDKV6.1.11.30_build20260805_linux64/库文件"
    "$SCRIPT_DIR/sdk/hikvision/lib"
    "$SCRIPT_DIR/lib"
)

for p in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$p" ] && [ -f "$p/libhcnetsdk.so" ]; then
        SDK_LIB_DIR="$p"
        break
    fi
done

if [ -z "$SDK_LIB_DIR" ]; then
    # 递归搜索包含 libhcnetsdk.so 的目录
    FOUND=$(find "$SCRIPT_DIR" -name "libhcnetsdk.so" 2>/dev/null | head -n 1)
    if [ -n "$FOUND" ]; then
        SDK_LIB_DIR="$(dirname "$FOUND")"
    fi
fi

if [ -n "$SDK_LIB_DIR" ]; then
    echo "[Info] 发现海康威视 SDK 动态库路径: $SDK_LIB_DIR"
    export LD_LIBRARY_PATH="$SDK_LIB_DIR:$SDK_LIB_DIR/HCNetSDKCom:${LD_LIBRARY_PATH}"
    export HIK_SDK_PATH="$SDK_LIB_DIR"
else
    echo "[Warning] 未在当前目录下检测到 libhcnetsdk.so，海康设备功能可能受限。"
fi

# 确保视频播放基于 X11 窗口句柄渲染 (兼容 Ubuntu Wayland/X11 桌面)
if [ -z "$QT_QPA_PLATFORM" ]; then
    export QT_QPA_PLATFORM=xcb
fi

# 关键修复：清除外部 QT_PLUGIN_PATH，防止加载系统不兼容的 libqxcb.so 导致崩溃
unset QT_PLUGIN_PATH

# ==============================================================================
# 中文输入法智能检测 (IBus / Fcitx) - 使用 POSIX 兼容写法
# ==============================================================================
if [ -z "$QT_IM_MODULE" ]; then
    if pgrep -x "fcitx" >/dev/null 2>&1 || pgrep -x "fcitx5" >/dev/null 2>&1; then
        export QT_IM_MODULE=fcitx
        export GTK_IM_MODULE=fcitx
        export XMODIFIERS="@im=fcitx"
    elif pgrep -x "ibus-daemon" >/dev/null 2>&1; then
        export QT_IM_MODULE=ibus
        export GTK_IM_MODULE=ibus
        export XMODIFIERS="@im=ibus"
    elif [ -n "$XMODIFIERS" ]; then
        case "$XMODIFIERS" in
            *fcitx*)
                export QT_IM_MODULE=fcitx
                export GTK_IM_MODULE=fcitx
                ;;
            *ibus*)
                export QT_IM_MODULE=ibus
                export GTK_IM_MODULE=ibus
                ;;
        esac
    fi
fi

# 确保日志目录存在
mkdir -p "$SCRIPT_DIR/logs"

# 动态为虚拟环境补齐输入法插件 (仅链接输入法单文件，绝不污染 platforms 平台插件)
VENV_INPUT_DIR=$(find "$SCRIPT_DIR/.venv" -type d -path "*/PyQt5/Qt5/plugins/platforminputcontexts" 2>/dev/null | head -n 1)
if [ -n "$VENV_INPUT_DIR" ]; then
    for sys_so in /usr/lib/x86_64-linux-gnu/qt5/plugins/platforminputcontexts/*.so; do
        if [ -f "$sys_so" ]; then
            so_name=$(basename "$sys_so")
            if [ ! -f "$VENV_INPUT_DIR/$so_name" ]; then
                ln -sf "$sys_so" "$VENV_INPUT_DIR/$so_name" 2>/dev/null || cp "$sys_so" "$VENV_INPUT_DIR/$so_name" 2>/dev/null || true
            fi
        fi
    done
fi

# 检查并激活虚拟环境
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [ -f "$VENV_PYTHON" ]; then
    echo "[Info] 正在使用虚拟环境: $SCRIPT_DIR/.venv"
    source "$SCRIPT_DIR/.venv/bin/activate"
    python3 "$SCRIPT_DIR/main.py" "$@" 2>&1 | tee -a "$SCRIPT_DIR/logs/startup.log"
else
    echo "[Warning] 未找到 .venv 虚拟环境，使用系统默认 python3 启动..."
    echo "[Tip] 建议先执行 bash setup_env.sh 自动配置独立运行环境。"
    python3 "$SCRIPT_DIR/main.py" "$@" 2>&1 | tee -a "$SCRIPT_DIR/logs/startup.log"
fi

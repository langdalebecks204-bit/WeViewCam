#!/usr/bin/env bash
# ==============================================================================
# WeViewCam 视频监控软件启动脚本 (Ubuntu / Linux x86_64)
# 自动配置海康 SDK 与大华 SDK 动态库搜索路径 (LD_LIBRARY_PATH) 并启动程序
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. 搜寻并配置海康威视 Linux 64位 SDK 库文件目录
HIK_SDK_DIR=""
POSSIBLE_HIK_PATHS=(
    "$SCRIPT_DIR/sdk/hikvision/linux64"
    "$SCRIPT_DIR/HCNetSDKV6.1.11.30_build20260805_linux64_20260812103926/HCNetSDKV6.1.11.30_build20260805_linux64/库文件"
    "$SCRIPT_DIR/sdk/hikvision/lib"
    "$SCRIPT_DIR/lib"
)

for p in "${POSSIBLE_HIK_PATHS[@]}"; do
    if [ -d "$p" ] && [ -f "$p/libhcnetsdk.so" ]; then
        HIK_SDK_DIR="$p"
        break
    fi
done

if [ -z "$HIK_SDK_DIR" ]; then
    FOUND_HIK=$(find "$SCRIPT_DIR" -name "libhcnetsdk.so" 2>/dev/null | head -n 1)
    if [ -n "$FOUND_HIK" ]; then
        HIK_SDK_DIR="$(dirname "$FOUND_HIK")"
    fi
fi

# 2. 搜寻并配置大华 NetSDK Linux 64位库文件目录
DAHUA_SDK_DIR=""
POSSIBLE_DAHUA_PATHS=(
    "$SCRIPT_DIR/sdk/dahua/linux64"
    "$SCRIPT_DIR/adapters/dahua/NetSDK/Libs/linux64"
)

for p in "${POSSIBLE_DAHUA_PATHS[@]}"; do
    if [ -d "$p" ] && [ -f "$p/libdhnetsdk.so" ]; then
        DAHUA_SDK_DIR="$p"
        break
    fi
done

if [ -z "$DAHUA_SDK_DIR" ]; then
    FOUND_DH=$(find "$SCRIPT_DIR" -name "libdhnetsdk.so" 2>/dev/null | head -n 1)
    if [ -n "$FOUND_DH" ]; then
        DAHUA_SDK_DIR="$(dirname "$FOUND_DH")"
    fi
fi

# 3. 组装 LD_LIBRARY_PATH
NEW_LD_PATH=""

if [ -n "$HIK_SDK_DIR" ]; then
    echo "[Info] 发现海康威视 SDK 动态库路径: $HIK_SDK_DIR"
    export HIK_SDK_PATH="$HIK_SDK_DIR"
    NEW_LD_PATH="$HIK_SDK_DIR:$HIK_SDK_DIR/HCNetSDKCom"
else
    echo "[Warning] 未检测到海康 libhcnetsdk.so，海康设备功能可能受限。"
fi

if [ -n "$DAHUA_SDK_DIR" ]; then
    echo "[Info] 发现大华 NetSDK 动态库路径: $DAHUA_SDK_DIR"
    export DAHUA_SDK_PATH="$DAHUA_SDK_DIR"
    if [ -n "$NEW_LD_PATH" ]; then
        NEW_LD_PATH="$DAHUA_SDK_DIR:$NEW_LD_PATH"
    else
        NEW_LD_PATH="$DAHUA_SDK_DIR"
    fi
else
    echo "[Warning] 未检测到大华 libdhnetsdk.so，大华设备功能可能受限。"
fi

if [ -n "$NEW_LD_PATH" ]; then
    export LD_LIBRARY_PATH="$NEW_LD_PATH:${LD_LIBRARY_PATH}"
fi

# 确保视频播放基于 X11 窗口句柄渲染 (兼容 Ubuntu Wayland/X11 桌面)
if [ -z "$QT_QPA_PLATFORM" ]; then
    export QT_QPA_PLATFORM=xcb
fi

# 清除外部 QT_PLUGIN_PATH，防止加载系统不兼容的 libqxcb.so 导致崩溃
unset QT_PLUGIN_PATH

# 强制 Python 标准输出和错误输出无缓冲，防止崩溃时日志丢失
export PYTHONUNBUFFERED=1

# 确保日志目录存在
mkdir -p "$SCRIPT_DIR/logs"

# 检查并激活虚拟环境 (优先使用 Python3)
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [ -f "$VENV_PYTHON" ]; then
    echo "[Info] 正在使用虚拟环境: $SCRIPT_DIR/.venv"
    source "$SCRIPT_DIR/.venv/bin/activate"
    python3 -u "$SCRIPT_DIR/main.py" "$@" 2>&1 | tee -a "$SCRIPT_DIR/logs/startup.log"
else
    echo "[Info] 使用系统默认 python3 启动..."
    python3 -u "$SCRIPT_DIR/main.py" "$@" 2>&1 | tee -a "$SCRIPT_DIR/logs/startup.log"
fi

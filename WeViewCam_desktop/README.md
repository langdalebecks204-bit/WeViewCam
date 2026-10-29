<div align="center">
  <img src="icon.png" width="120" height="120" alt="WeViewCam Logo">
  <h1>WeViewCam Desktop (Windows & Linux)</h1>
  <p><strong>A Unified Cross-Platform Video Surveillance & VMS Client for Windows 10/11 & Linux (Ubuntu)</strong></p>
  <p><strong>专为 Windows 10/11 与 Linux (Ubuntu) 打造的统一跨平台现代化视频监控综合管理平台</strong></p>

  <p>
    <a href="#english">English</a> •
    <a href="#中文说明">中文说明</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20%7C%20Ubuntu%20Linux-0078D6?logo=linux" alt="Platform">
    <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python" alt="Python Version">
    <img src="https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52?logo=qt" alt="GUI">
    <img src="https://img.shields.io/badge/Video-SDK%20Direct%20Render%20%7C%20OpenCV-FF5722" alt="Video Engines">
    <img src="https://img.shields.io/badge/SDK-Hikvision%20(Win64%20%26%20Linux64)%20%2B%20ONVIF-brightgreen" alt="Supported SDKs">
    <img src="https://img.shields.io/badge/Release-v0.1.3-orange" alt="Release">
  </p>
</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

**WeViewCam Desktop** is a unified, high-performance, and lightweight Video Management System (VMS) client engineered to run seamlessly across **Windows 10 / 11 (64-bit)** and **Linux (Ubuntu 20.04 / 22.04 / 24.04 x86_64)** with a single codebase.

- **Unified Native SDK Driver**: Automatically detects host OS (`sys.platform`) and binds official Hikvision SDK (`.dll` on Windows, `.so` on Linux) with zero manual configuration.
- **Ultra-Low Latency Direct Rendering**: Direct hardware window embedding (`HWND` on Windows, X11 Window ID on Linux) for smooth 25/30 FPS playback with minimal CPU usage.
- **International Standard ONVIF & RTSP**: Auto-discovery of ONVIF profiles, PTZ controls, and OpenCV fallback rendering.
- **Cross-Platform Sync**: 100% interoperable backup and restore protocol matching the Android mobile edition.

### Quick Start

#### On Windows:
```cmd
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run
python main.py
# Or double click run.bat

# 3. Build standalone .exe
python pack.py
```

#### On Ubuntu / Linux:
```bash
# 1. Install dependencies and system libs
chmod +x install.sh && ./install.sh

# 2. Run
./run.sh
# Or python3 main.py

# 3. Build release tarball
chmod +x package.sh && ./package.sh
```

---

<a name="中文说明"></a>
## 🇨🇳 中文说明

### 项目概述

**WeViewCam 桌面端 (WeViewCam Desktop)** 是针对 **Windows 10 / 11 (64位)** 与 **Linux (Ubuntu 20.04 / 22.04 / 24.04 x86_64)** 双平台统一打造的高性能视频监控综合管理平台。

通过统一抽象层与动态系统检测，双平台共享 100% 的业务逻辑、UI 界面、设备数据与测试套件。

### 核心特性

1. **双平台海康 SDK 原生直驱**：
   - 自动识别操作系统：Windows 下动态加载 Win64 官方 DLL，Linux 下动态加载 Linux64 官方 SO 动态库。
   - 采用原生窗口句柄（Windows HWND / Linux X11 WinID）直接渲染，超低延迟、CPU 占用极低。
2. **多协议兼容**：
   - 海康威视（私有 SDK 直驱）
   - ONVIF 国际标准（自动探测、全向云台控制）
   - 大华与标准 RTSP 流媒体（支持 OpenCV 软件兜底解码渲染）
3. **多画面实时预览与主辅码流切换**：
   - 支持 1 / 4 / 9 / 16 分屏动态切换。
   - 支持主码流（高清）与子码流（流畅）一键即时平滑切换。
   - 双击任意分屏快速全屏放大，支持单路即时截图与本地录像。
4. **24 小时精准时间轴回放**：
   - 交互式 24 小时时间刻度轴，直观显示录像分段。
   - 拖拽快进、暂停、快放（2x/4x/8x/16x）、慢放与逐帧单步播放。
5. **通道管理与全平台互通备份**：
   - 支持自定义通道名称、通道启用/禁用过滤。
   - 支持按设备选择性备份导出，与 Android 移动端 100% 格式无缝互通。

### 快速启动

#### Windows 平台：
```cmd
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动运行
python main.py
# 或直接双击 run.bat

# 3. 编译打包独立免安装绿色版
python pack.py
```

#### Ubuntu / Linux 平台：
```bash
# 1. 一键安装依赖与系统库
chmod +x install.sh && ./install.sh

# 2. 启动运行
./run.sh
# 或 python3 main.py

# 3. 生成发布安装包
chmod +x package.sh && ./package.sh
```

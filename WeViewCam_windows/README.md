<div align="center">
  <img src="icon.png" width="120" height="120" alt="WeViewCam Logo">
  <h1>WeViewCam (Windows Edition)</h1>
  <p><strong>A Modern Video Surveillance & VMS Client for Windows 10 / 11 (x86_64)</strong></p>
  <p><strong>专为 Windows 10 / 11 打造的现代化视频监控综合管理平台</strong></p>

  <p>
    <a href="#english">English</a> •
    <a href="#中文说明">中文说明</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(64--bit)-0078D6?logo=windows" alt="Platform">
    <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python" alt="Python Version">
    <img src="https://img.shields.io/badge/GUI-PyQt5-41CD52?logo=qt" alt="PyQt5">
    <img src="https://img.shields.io/badge/Video-SDK%20Direct%20Render%20%7C%20OpenCV-FF5722" alt="Video Engines">
    <img src="https://img.shields.io/badge/SDK-Hikvision%20Win64%20%26%20ONVIF-brightgreen" alt="Supported SDKs">
    <img src="https://img.shields.io/badge/Release-v0.1.3-orange" alt="Release">
  </p>
</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

**WeViewCam (Windows Edition)** is a modern, lightweight, and high-performance Video Management System (VMS) client specifically engineered for **Windows 10 and Windows 11 (64-bit)**. It provides complete feature parity and visual consistency with the Ubuntu version, featuring multi-camera live surveillance (1/4/9/16 split views), PTZ pan-tilt-zoom controls, historical recording search, and 24-hour timeline playback.

The system features:
- **Hikvision Official Win64 SDK Integration**: Native ctypes bindings to official Windows 64-bit SDK (`HCNetSDK.dll`, `PlayCtrl.dll`, `HCNetSDKCom/`), enabling direct HWND window rendering with ultra-low latency and negligible CPU usage.
- **ONVIF International Standard**: Integrated with `onvif-zeep`, supporting automatic device profile discovery, multi-stream channel resolution, RTSP URL retrieval, and 8-direction PTZ / continuous zoom control.
- **Dual-Engine Video Architecture**: Native SDK Direct HWND rendering and graceful fallback to OpenCV RTSP decoding.
- **Windows Integration**: Native High-DPI scaling, Windows taskbar AppUserModelID icon grouping, and one-click `run.bat` launcher.

---

### Key Features

1. **Multi-Vendor Architecture**:
   - Standardized `BaseDeviceAdapter` interface abstracting manufacturer protocols.
   - Built-in Hikvision adapter, ONVIF/RTSP standard adapter, and pre-configured Dahua slots.
2. **Multi-Split Live View**:
   - Dynamic 1x1, 2x2, 3x3, and 4x4 viewport grid layouts.
   - Low-latency native Windows window embedding (`HWND` via `widget.winId()`).
   - Double-click any viewport to toggle full-screen zoom.
   - Live snapshot (JPEG) and local MP4 recording.
   - Full PTZ control panel: 8-direction navigation, Zoom (+/-), Focus (+/-), Iris (+/-), and 1-7 speed presets.
3. **24-Hour Timeline Playback**:
   - Precise search for NVR / SD card historical recordings by device, channel, and date.
   - Custom high-precision 24-hour interactive timeline with visual recording segments.
   - Draggable playhead and comprehensive playback controls: Play, Pause, Fast-forward (2x/4x/8x/16x), Slow-motion (1/2x, 1/4x), and single-frame stepping.
4. **Device & Channel Management**:
   - Custom channel names and in-place renaming via right-click or dedicated dialog.
   - Selective channel enable/disable switch (disabled channels hidden from tree and live views).
   - Dedicated Channel Management Dialog with batch enable/disable and manual channel addition.
   - Full JSON backup export/import preserving custom channel names and enabled states, with 100% mutual compatibility with the Android and Ubuntu clients.

---

### Quick Start (Windows)

#### 1. Requirements
Ensure Python 3.8+ (64-bit) is installed on your Windows system.
Install dependencies:
```cmd
pip install -r requirements.txt
```

#### 2. Run Application
Simply double-click `run.bat` or run in terminal:
```cmd
python main.py
```

#### 3. One-Click Packaging
To create a clean release zip:
```powershell
powershell -ExecutionPolicy Bypass -File pack.ps1
```
To compile into a standalone `.exe`:
```cmd
build_exe.bat
```

---

<a name="中文说明"></a>
## 🇨🇳 中文说明

### 项目简介

**WeViewCam (Windows 版)** 是专为 **Windows 10 / 11 (64位)** 打造的现代化、轻量级、高性能综合视频监控管理客户端（VMS）。**界面设计与业务功能与 Ubuntu 版 100% 保持一致**，支持多画面分屏预览（1/4/9/16 分屏）、8方向 PTZ 云台控制、历史录像检索以及 24 小时高精度时间轴回放。

---

### 核心特性

1. **多品牌协议融合**:
   - 抽象统一的设备驱动层，支持海康威视（Hikvision HCNetSDK）、ONVIF 标准协议和大华（Dahua）设备。
2. **海康威视 Windows 64位 原生 SDK 驱动**:
   - 深度集成海康 Win64 官方动态库（`HCNetSDK.dll`、`PlayCtrl.dll` 及 `HCNetSDKCom/` 插件库），通过原生窗口句柄（`HWND`）直通硬解渲染，极低延迟，极低 CPU 占用。
3. **现代化多画面预览**:
   - 自由切换 1x1、2x2、3x3、4x4 分屏；
   - 双击单视口切换最大化/还原；
   - 实时抓图（JPEG）与本地录像；
   - 完整云台控制（上/下/左/右/左上/右上/左下/右下、焦距、聚焦、光圈、1-7级转速）。
4. **24 小时精细时间轴录像回放**:
   - 按设备、通道、日期精准检索 NVR / 摄像头存储卡历史录像；
   - 录像片段多色彩条带渲染，支持拖拽时间轴指针精准定位；
   - 正常播放、暂停、2x/4x/8x/16x 快进、1/2x与1/4x 慢放、单帧逐帧步进。
5. **通道管理与多端互通**:
   - 支持通道自定义重命名与右键就地编辑；
   - 支持通道按需启用/禁用（停用通道自动在设备树和预览中隐藏）；
   - 设备配置以 JSON 格式持久化，配置导入导出与 Android 版、Ubuntu 版完全通用兼容。

---

### 快速开始

#### 1. 环境准备
确保已安装 Python 3.8+ 64位环境，并在命令行中安装依赖：
```cmd
pip install -r requirements.txt
```

#### 2. 启动客户端
直接双击运行目录下的 `run.bat`，或在命令行运行：
```cmd
python main.py
```

#### 3. 一键打包发布
- **打包为绿色发布压缩包**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File pack.ps1
  ```
- **编译为独立单文件 EXE 应用程序**:
  双击运行 `build_exe.bat` 即可调用 PyInstaller 构建生成 `dist\WeViewCam\WeViewCam.exe`。

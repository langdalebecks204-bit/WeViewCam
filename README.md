<div align="center">
  <img src="WeViewCam_ubuntu/icon.png" width="120" height="120" alt="WeViewCam Logo">
  <h1>WeViewCam</h1>
  <p><strong>A Modern, Unified Video Surveillance & VMS Client Suite for Ubuntu Linux & Android</strong></p>
  <p><strong>专为 Ubuntu Linux 桌面与 Android 移动终端打造的现代化视频监控综合管理平台</strong></p>

  <p>
    <a href="#english">English</a> •
    <a href="#中文说明">中文说明</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Platform-Ubuntu%20Linux%20%7C%20Android-E95420?logo=linux" alt="Platform">
    <img src="https://img.shields.io/badge/Ubuntu-PyQt5%20%7C%20Python3-41CD52?logo=qt" alt="Ubuntu Tech">
    <img src="https://img.shields.io/badge/Android-Java%20%7C%20SurfaceView-3DDC84?logo=android" alt="Android Tech">
    <img src="https://img.shields.io/badge/SDK-Hikvision%20%26%20ONVIF-brightgreen" alt="Supported SDKs">
    <img src="https://img.shields.io/badge/Release-v0.1.0-orange" alt="Release">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  </p>
</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

**WeViewCam** is an open-source, multi-platform Video Management System (VMS) designed for unified, low-latency surveillance camera monitoring, high-precision PTZ control, and 24-hour timeline video playback. 

The repository provides two production-ready solutions sharing a standardized architecture:
1. **[WeViewCam_ubuntu](./WeViewCam_ubuntu/)**: Modern desktop VMS client engineered for **Ubuntu Linux (x86_64)** with PyQt5, LibVLC/OpenCV dual-engine, and official Hikvision Linux 64-bit SDK bindings.
2. **[WeViewCam_android](./WeViewCam_android/)**: Native mobile VMS client engineered for **Android phones and tablets**, powered by official Hikvision Android SDK (HCNetSDK / PlayerSDK) with hardware-accelerated `SurfaceView` rendering.

---

### Project Structure

```text
WeViewCam/
├── WeViewCam_ubuntu/           # Ubuntu Linux Desktop Client (Python 3 + PyQt5)
│   ├── adapters/               # Hikvision Ctypes driver & ONVIF/RTSP adapters
│   ├── core/                   # Device management, base adapter & player controller
│   ├── ui/                     # Multi-split live view, PTZ panel & 24h timeline
│   ├── sdk/hikvision/lib/      # Official Hikvision Linux 64-bit native libraries
│   ├── package.sh              # Standalone package creation script
│   └── README.md               # Detailed Ubuntu documentation
├── WeViewCam_android/          # Android Mobile Client (Java + Native SDK)
│   ├── app/                    # Native Android application module
│   │   ├── libs/               # Hikvision Android Java SDK (HCNetSDK.jar, jna.jar)
│   │   └── src/main/jniLibs/   # Hikvision native .so libraries (arm64-v8a, armeabi-v7a)
│   ├── gradlew / gradlew.bat   # Gradle build tools
│   ├── weviewcam_android_v0.1.0.apk # Pre-built release APK
│   └── README.md               # Detailed Android documentation
└── README.md                   # Repository overview
```

---

### Feature Matrix

| Feature | Ubuntu Desktop Client | Android Mobile Client |
| :--- | :---: | :---: |
| **Language & Framework** | Python 3.8+ / PyQt5 | Java 8+ / Android SDK 34 |
| **Video Rendering** | X11 Native Embedding / LibVLC / OpenCV | Hardware SurfaceView / SurfaceHolder |
| **Hikvision SDK** | Linux 64-bit (`libhcnetsdk.so`) | Android Native (`arm64-v8a`, `armeabi-v7a`) |
| **Live View Layouts** | 1x1, 2x2, 3x3, 4x4 (1-16 Screens) | Single View (1x1), Quad View (2x2) |
| **Channel Status** | Online / Offline Indicators | Dropdown & Viewport OSD `[在线]` / `[离线]` |
| **PTZ Controls** | 8-Direction Compass, Zoom, Focus, Iris, Speed 1-7 | 8-Direction Touchpad, Zoom, Focus, Iris, Speed 1-7 |
| **Stream Switch** | Main Stream / Sub Stream | Main Stream / Sub Stream |
| **Local Capture** | Snapshot (JPEG) & Local Recording (MP4) | Snapshot (JPEG to Gallery) & Local MP4 |
| **Timeline Playback** | 24-Hour Custom Canvas Timeline (24h/12h/4h/1h Zoom) | Custom `TimelineBarView` (24h/12h/4h/1h Zoom) |
| **Playback Control** | Play/Pause, Stop, Fast (2x-16x), Slow, Frame Step | Play/Pause, Stop, Fast, Slow, Frame Step |
| **Device Config** | Local `config/devices.json` & Connection Test | SQLite/JSON persistent `devices.json` & Connection Test |

---

<a name="中文说明"></a>
## 🇨🇳 中文说明

### 项目简介

**WeViewCam** 是一个面向现代化视频监控场景的跨平台综合管理平台（VMS Client）。项目采用统一的架构设计与模块分层模式，分别针对 **Ubuntu Linux 桌面端** 与 **Android 移动终端** 进行了全功能深度移植与原生适配，全面支持海康威视（Hikvision）私有 SDK 协议以及 ONVIF / RTSP 国际通用协议。

### 目录说明

1. **[WeViewCam_ubuntu](./WeViewCam_ubuntu/)**：
   - 专为 **Ubuntu Linux (x86_64)** 打造的桌面客户端；
   - 基于 Python 3 + PyQt5 架构，采用现代化深色监控 UI 风格；
   - 原生封装海康 Linux 64 位官方 SDK（`libhcnetsdk.so`、`libPlayCtrl.so`），配合 LibVLC 与 OpenCV 双引擎实现极低延迟拉流；
   - 支持 1 / 4 / 9 / 16 多分屏切换、8 方向 PTZ 遥控、24 小时录像检索及交互式时间轴回放。

2. **[WeViewCam_android](./WeViewCam_android/)**：
   - 专为 **Android 手机与平板设备** 打造的原生移动端应用；
   - 原生集成海康威视最新版 Android SDK 与 JNA 动态库，支持 `arm64-v8a` 与 `armeabi-v7a` 架构；
   - 基于 Android 原生 `SurfaceView` 实现硬件加速直传渲染，CPU 与功耗占用极低；
   - 支持单画面与四分屏切换、云台触控操作、通道在线状态检测、异步历史录像检索与高精度时间轴回放；
   - 包含已构建好的发布版本安装包：[`weviewcam_android_v0.1.0.apk`](./WeViewCam_android/weviewcam_android_v0.1.0.apk)。

---

### 快速开始

#### 1. Ubuntu 桌面版本
```bash
cd WeViewCam_ubuntu

# 初始化虚拟环境并安装依赖
bash setup_env.sh

# 启动客户端
bash run.sh
```

#### 2. Android 移动版本
- **直接安装**：将 [`WeViewCam_android/weviewcam_android_v0.1.0.apk`](./WeViewCam_android/weviewcam_android_v0.1.0.apk) 传输至 Android 设备即可一键安装使用。
- **源码编译**：
  ```bash
  cd WeViewCam_android
  # 使用 Gradle 构建 Debug APK
  ./gradlew assembleDebug
  ```

---

### 开源许可

本项目遵循 [MIT License](./LICENSE) 开源协议。

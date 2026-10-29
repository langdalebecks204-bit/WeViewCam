<div align="center">
  <img src="WeViewCam_desktop/icon.png" width="120" height="120" alt="WeViewCam Logo">
  <h1>WeViewCam</h1>
  <p><strong>A Modern, Unified Video Surveillance & VMS Client Suite for Windows, Linux & Android</strong></p>
  <p><strong>专为 Windows、Linux 桌面与 Android 移动终端打造的现代化视频监控综合管理平台</strong></p>

  <p>
    <a href="#english">English</a> •
    <a href="#中文说明">中文说明</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Android-0078D6?logo=linux" alt="Platform">
    <img src="https://img.shields.io/badge/Desktop-PySide6%20%2F%20Qt6-41CD52?logo=qt" alt="Desktop Tech">
    <img src="https://img.shields.io/badge/Android-Java%20%7C%20SurfaceView-3DDC84?logo=android" alt="Android Tech">
    <img src="https://img.shields.io/badge/SDK-Hikvision%20%26%20ONVIF-brightgreen" alt="Supported SDKs">
    <img src="https://img.shields.io/badge/Release-v0.1.3-orange" alt="Release">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  </p>
</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

**WeViewCam** is an open-source, multi-platform Video Management System (VMS) designed for unified, low-latency surveillance camera monitoring, high-precision PTZ control, and 24-hour timeline video playback. 

The repository provides two unified solutions:
1. **[WeViewCam_desktop](./WeViewCam_desktop/)**: Unified Cross-Platform Desktop Client for **Windows 10 / 11 (64-bit)** and **Linux (Ubuntu 20.04 / 22.04 / 24.04 x86_64)**. Shares 100% of the UI, business logic, and test suites with auto-detection for native Hikvision SDKs (Win64 DLL / Linux64 SO).
2. **[WeViewCam_android](./WeViewCam_android/)**: Native mobile VMS client for **Android phones and tablets**, powered by official Hikvision Android SDK with hardware-accelerated `SurfaceView` rendering.

---

### Project Structure

```text
WeViewCam/
├── WeViewCam_desktop/          # Unified Desktop Client (Windows & Linux)
│   ├── adapters/               # Hikvision (Win64/Linux64), Dahua & ONVIF/RTSP adapters
│   ├── core/                   # Device management, base adapter & player controller
│   ├── ui/                     # Multi-split live view, PTZ panel & 24h timeline
│   ├── sdk/hikvision/
│   │   ├── win64/              # Official Hikvision Windows 64-bit DLLs
│   │   └── linux64/            # Official Hikvision Linux 64-bit SOs
│   ├── config_template/        # Clean empty configuration template
│   ├── run.bat / run.sh        # One-click execution runners (Windows / Linux)
│   ├── pack.py                 # Windows Standalone EXE packager (PyInstaller)
│   ├── package.sh              # Linux release tarball packager
│   └── README.md               # Detailed Desktop documentation
└── WeViewCam_android/          # Android Native Client (Java)
    ├── app/                    # Android Studio application module
    ├── app/build.gradle        # Build script with auto-extraction task
    └── README.md               # Detailed Android documentation
```

---

<a name="中文说明"></a>
## 🇨🇳 中文说明

### 项目概述

**WeViewCam** 是一款现代化、高性能、多平台视频监控与安防管理客户端套件。支持海康威视官方私有 SDK 原生硬解码直驱渲染、ONVIF 国际标准协议自动发现与大华/RTSP 流媒体拉流。

仓库采用极简的双端统一架构：
1. **[WeViewCam_desktop](./WeViewCam_desktop/)**：**Windows 与 Linux (Ubuntu) 统一桌面客户端**。代码 100% 共享，根据运行操作系统自动加载 Win64 DLL 或 Linux64 SO 原生海康 SDK，提供 Windows 便携版 (`WeViewCam.exe`) 与 Linux 源码运行/安装包。
2. **[WeViewCam_android](./WeViewCam_android/)**：**Android 移动客户端**。基于 Java 与官方 Android SDK，支持硬件加速多通道分屏与触控云台交互。

### 核心特性

- **双端跨平台配置同步**：Android 与桌面端配置文件及备份格式 100% 互通，支持按需指定设备勾选导出备份。
- **超低延迟硬件直驱渲染**：桌面端支持 HWND / X11 窗口句柄直传海康 SDK 原生渲染；Android 端采用 `SurfaceView`。
- **主辅码流无缝切换**：实时预览支持高清主码流与流畅子码流一键平滑重载切换。
- **通道状态巡检**：启动自动探测设备重连与通道状态，支持后台定时心跳检测。

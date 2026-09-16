<div align="center">
  <img src="icon.png" width="120" height="120" alt="WeViewCam Logo">
  <h1>WeViewCam</h1>
  <p><strong>A Modern Video Surveillance & VMS Client for Ubuntu Linux (x86_64)</strong></p>
  <p><strong>专为 Ubuntu Linux 打造的现代化视频监控综合管理平台</strong></p>

  <p>
    <a href="#english">English</a> •
    <a href="#中文说明">中文说明</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Platform-Ubuntu%2020.04%20%7C%2022.04%20%7C%2024.04%20LTS-E95420?logo=ubuntu" alt="Platform">
    <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python" alt="Python Version">
    <img src="https://img.shields.io/badge/GUI-PyQt5-41CD52?logo=qt" alt="PyQt5">
    <img src="https://img.shields.io/badge/Video-LibVLC%20%7C%20OpenCV-FF5722" alt="Video Engines">
    <img src="https://img.shields.io/badge/SDK-Hikvision%20%26%20ONVIF-brightgreen" alt="Supported SDKs">
    <img src="https://img.shields.io/badge/Release-v0.1.0-orange" alt="Release">
  </p>
</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

**WeViewCam** is a modern, lightweight, and high-performance Video Management System (VMS) client specifically engineered for **Ubuntu Linux (x86_64)**. It provides unified multi-camera live surveillance (1/4/9/16 split views), PTZ pan-tilt-zoom controls, historical recording search, and 24-hour timeline playback.

The system adopts a decoupled, modular architecture:
- **Hikvision Official SDK Integration**: Native ctypes bindings to official Linux 64-bit SDK (`libhcnetsdk.so`, `libPlayCtrl.so`, `HCNetSDKCom`), enabling native hardware acceleration with negligible CPU usage.
- **ONVIF International Standard**: Integrated with `onvif-zeep`, supporting automatic device profile discovery, multi-stream channel resolution, RTSP URL retrieval, and 8-direction PTZ / continuous zoom control.
- **Dual-Engine Video Architecture**: High-speed LibVLC rendering (`python-vlc`) with hardware acceleration and automatic graceful fallback to OpenCV, ensuring zero-dependency out-of-the-box streaming.
- **Ubuntu Desktop Integration**: Automated virtual environment setup and one-click `.desktop` application entry creation.

---

### Key Features

1. **Multi-Vendor Architecture**:
   - Standardized `BaseDeviceAdapter` interface abstracting manufacturer protocols.
   - Built-in Hikvision adapter, ONVIF/RTSP standard adapter, and pre-configured Dahua slots.
2. **Multi-Split Live View**:
   - Dynamic 1x1, 2x2, 3x3, and 4x4 viewport grid layouts.
   - Low-latency X11 window embedding (`winId` / `set_xwindow`).
   - Double-click any viewport to toggle full-screen zoom.
   - Live snapshot (JPEG) and local MP4 recording.
   - Full PTZ control panel: 8-direction navigation, Zoom (+/-), Focus (+/-), Iris (+/-), and 1-7 speed presets.
3. **24-Hour Timeline Playback**:
   - Precise search for NVR / SD card historical recordings by device, channel, and date.
   - Custom high-precision 24-hour interactive timeline with visual recording segments.
   - Mouse wheel zoom (24h -> 12h -> 4h -> 1h scale) and draggable playhead.
   - Comprehensive playback controls: Play, Pause, Fast-forward (2x/4x/8x/16x), Slow-motion (1/2x, 1/4x), and single-frame stepping.
4. **Device Management**:
   - Add, edit, remove devices with local persistent storage in `config/devices.json`.
   - One-click "Test Connection" with automatic channel count detection.
5. **Ubuntu Desktop Experience**:
   - Ready-to-use standalone release tarball (`weviewcam_ubuntu_v0.1.0.tar.gz`).
   - Auto-configures Python virtual environments and resolves Linux Chinese input method (IBus / Fcitx) integration.

---

### Project Structure

```text
WeViewCam/
├── core/                                # Core business layer
│   ├── base_adapter.py                  # Abstract device interface & data models
│   ├── device_manager.py                # Device configuration & persistence
│   ├── player_controller.py             # Viewport dispatcher & player manager
│   └── logger.py                        # Unified logging utility
├── adapters/                            # Device protocol adapters
│   ├── factory.py                       # Adapter factory
│   ├── hikvision/                       # Hikvision SDK implementation
│   │   ├── adapter.py                   # HikvisionAdapter
│   │   ├── driver.py                    # Ctypes SDK loader & API bindings
│   │   ├── structures.py                # C struct definitions & constants
│   │   └── PlayCtrl.py                  # Player SDK definitions
│   ├── onvif/                           # ONVIF & RTSP implementation
│   │   ├── adapter.py                   # OnvifAdapter
│   │   └── player.py                    # Dual-engine RTSP player (VLC / OpenCV)
│   └── dahua/                           # Dahua adapter (reserved extension)
├── ui/                                  # Presentation layer (PyQt5)
│   ├── main_window.py                   # Main window & navigation
│   ├── live_view_widget.py              # Multi-screen live view & PTZ panel
│   ├── video_widget.py                  # Video viewport unit
│   ├── playback_widget.py               # Recording retrieval & playback view
│   ├── timeline_bar.py                  # Interactive 24-hour timeline bar
│   ├── device_tree_widget.py            # Device & channel tree view
│   ├── device_dialog.py                 # Device add/edit dialog
│   └── styles.py                        # Dark theme surveillance QSS stylesheet
├── config/
│   └── devices.json                     # Persistent device config
├── sdk/
│   └── hikvision/lib/                   # Pre-bundled Hikvision Linux 64-bit libraries
├── tests/                               # Automated unit test suite
│   ├── test_adapters.py
│   ├── test_device_manager.py
│   ├── test_onvif.py
│   └── test_timeline.py
├── weviewcam_ubuntu_v0.1.0.tar.gz       # Standalone Ubuntu release package
├── requirements.txt                     # Python dependencies
├── setup_env.sh                         # One-click environment initialization
├── install_desktop_shortcut.sh          # Desktop shortcut installer
├── run.sh                               # Startup script with library path exports
├── package.sh / pack.ps1                # Packaging scripts
└── main.py                              # Application entry point
```

---

### Getting Started (Ubuntu Linux)

#### Option A: Quick Run with Release Package

1. Download or locate `weviewcam_ubuntu_v0.1.0.tar.gz`.
2. Extract the archive:
   ```bash
   tar -xzvf weviewcam_ubuntu_v0.1.0.tar.gz
   cd WeViewCam
   ```
3. Run the automated installer:
   ```bash
   bash setup_env.sh
   ```
4. Launch the application:
   - Double-click the **WeViewCam** icon generated on your Desktop, or
   - Launch from the terminal:
     ```bash
     bash run.sh
     ```

#### Option B: Clone from Source

1. **Install system prerequisites**:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip libgl1-mesa-glx libx11-xcb1
   ```
   *(Optional for LibVLC hardware acceleration)*:
   ```bash
   sudo apt install -y libvlc-dev vlc
   ```

2. **Initialize environment**:
   ```bash
   bash setup_env.sh
   ```

3. **Start WeViewCam**:
   ```bash
   bash run.sh
   ```

---

### Running Automated Tests

Run the test suite using pytest:
```bash
python3 -m pytest tests/ -v
```

---

<a name="中文说明"></a>
## 🇨🇳 中文说明

### 项目概述

**WeViewCam** 是一套专为 **Ubuntu Linux (x86_64)** 环境打造的现代视频监控综合管理平台（VMS Client），当前版本 **v0.1.0**。提供多分屏实时视频监控、8方向云台与变倍控制、历史录像精准检索及 24 小时高精度时间轴回放等核心功能。

系统采用高内聚、低耦合的分层架构设计：
- **深度接入海康威视官方 SDK**：原生封装 Linux 64 位底层动态库（`libhcnetsdk.so`、`libPlayCtrl.so`、`HCNetSDKCom` 等），基于 X11 窗口句柄直传（`winId`）硬件加速，CPU 占用极低。
- **国际标准 ONVIF 协议支持**：深度集成 `onvif-zeep` 协议栈，自动探测 Profile、多码流通道解析、RTSP 流地址获取及 8 方向连续 PTZ 云台/变焦控制。
- **双引擎 RTSP 播放架构**：优先采用 LibVLC 原生硬件加速嵌入渲染，并内置轻量级 OpenCV 软解引擎作为无缝自动降级备选，实现零系统依赖即开即用。
- **完善的 Ubuntu 桌面整合**：一键生成桌面图标与系统应用菜单项，自动适配并修复 Ubuntu 中文输入法（IBus / Fcitx）。

---

### 核心功能

1. **多厂商统一设备架构**：
   - 统一抽象 `BaseDeviceAdapter` 接口，屏蔽各厂商底层差异；
   - 包含海康威视（Hikvision）专有适配器、ONVIF/RTSP 国际标准适配器，并预留大华（Dahua）扩展插槽。
2. **多分屏实时预览 (Live View)**：
   - 支持 **1 画面 (1x1)**、**4 画面 (2x2)**、**9 画面 (3x3)**、**16 画面 (4x4)** 动态网格分屏；
   - 双击任意视频视口全屏放大，再次双击还原；
   - 支持通道实时画面抓图（JPEG）与本地 MP4 录像；
   - **PTZ 云台控制面板**：8 方向移动控制、变焦 (Zoom)、聚焦 (Focus)、光圈 (Iris) 及 1-7 级速度调节。
3. **录像检索与 24 小时时间轴回放 (Playback)**：
   - 按设备、通道、日期精确检索 NVR / SD 卡历史录像；
   - 自绘高精度 **24 小时交互式时间轴**：绿色高亮录像区间、滚轮无级缩放（24h/12h/4h/1h）、拖拽红色指针精确定位；
   - 完整播控支持：播放、暂停、快进 (2x/4x/8x/16x)、慢放 (1/2x, 1/4x)、单帧步进、截图保存。
4. **设备管理中心**：
   - 设备增删改查，配置持久化保存在 `config/devices.json`；
   - 一键“测试连接”，验证网络连通并自动探测通道总数。
5. **开箱即用的安装包与自动化脚本**：
   - 附带精简独立的 Ubuntu 预编译安装包 `weviewcam_ubuntu_v0.1.0.tar.gz`；
   - 提供 `setup_env.sh` 与 `run.sh` 脚本，全自动配置依赖并生成桌面图标。

---

### 在 Ubuntu 系统上的安装与使用

#### 方式一：使用发布安装包直接部署 (推荐)

1. 获取发布安装包 `weviewcam_ubuntu_v0.1.0.tar.gz`。
2. 解压安装包：
   ```bash
   tar -xzvf weviewcam_ubuntu_v0.1.0.tar.gz
   cd WeViewCam
   ```
3. 执行一键环境初始化：
   ```bash
   bash setup_env.sh
   ```
   > 提示：脚本会自动创建隔离的 Python 虚拟环境，安装所需依赖，并在桌面与应用程序菜单中自动生成【WeViewCam 监控系统】快捷方式。
4. 启动程序：
   - 直接在 Ubuntu 桌面上**双击【WeViewCam 监控系统】图标**启动；
   - 或在终端执行：
     ```bash
     bash run.sh
     ```

#### 方式二：从源码仓库运行

1. **安装系统前置库**（Ubuntu 20.04/22.04/24.04）：
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip libgl1-mesa-glx libx11-xcb1
   ```
   *(可选：安装 LibVLC 硬件加速库)*：
   ```bash
   sudo apt install -y libvlc-dev vlc
   ```

2. **初始化虚拟环境**：
   ```bash
   bash setup_env.sh
   ```

3. **运行程序**：
   ```bash
   bash run.sh
   ```

---

### 操作说明

1. **添加设备**：
   - 点击左侧设备面板的 `+` 按钮；
   - 输入设备名称，选择设备协议（海康威视 / ONVIF）；
   - 填写 IP 地址、端口（海康默认 8000，ONVIF 通常为 80 或 8899）、用户名与密码；
   - 点击“测试连接”确认通信正常后保存。
2. **实时预览**：
   - 顶部工具栏自由切换 1 / 4 / 9 / 16 分屏；
   - 在左侧设备树中**双击任意通道**即可在选中视口出图播放；
   - 选中视口后通过右侧控制面板操控云台方向与变焦。
3. **录像回放**：
   - 顶部导航切换至“录像回放”；
   - 选择设备、通道与日期，点击“检索历史录像”；
   - 点击时间轴或双击录像列表即可跳转播放。

---

### 运行单元测试

```bash
python3 -m pytest tests/ -v
```
覆盖适配器生命周期、设备管理 CRUD、ONVIF PTZ 映射与时间轴数学坐标运算等 12 项测试。

---

### 许可证 / License

本项目采用 [MIT License](LICENSE) 开源许可（第三方厂商 SDK 库版权归对应厂商所有）。

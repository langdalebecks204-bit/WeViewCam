# WeViewCam-Open 版本更新日志 (Changelog)

所有关于 **WeViewCam-Open** 开源版本的重大更新、新增功能、系统适配与缺陷修复记录均归档于此。

---

## [v0.1.5] - 2026-11-09

本次更新重点聚焦于 **Ubuntu (Linux x86_64) 原生适配的全面稳定** 以及 **大华 (Dahua) 原生 SDK 驱动与硬件解码管线的双端对齐**，彻底解决了 Python 3.12 环境下的段错误崩溃、录像切片切换异常与视口直驱渲染等核心痛点。

---

### 🐧 Ubuntu 平台 (Linux x86_64 / Ubuntu 20.04 / 22.04 / 24.04)

#### 🌟 新增特性 (New Features)
1. **大华 (Dahua) 原生 SDK Linux 驱动集成**：
   - 适配大华 Linux 64 位原生 NetSDK (`libnetsdk.so`, `libdhnetsdk.so`, `libdhconfigsdk.so`)；
   - 支持大华 NVR / IPC 原生 SDK 实时双码流（主码流/子码流）毫秒级低延迟直驱预览；
   - 支持录像段检索 (`CLIENT_FindFileEx`) 与时间范围回放 (`CLIENT_PlayBackByTimeEx2`)。
2. **PlaySDK 硬件加速灌流管线**：
   - 集成大华官方 `libdhplay.so` 解码核心，构建原生流式回放链路（`GetFreePort` + `OpenStream` + `Play(port, winId)` + `InputData`），消除软解高 CPU 占用，实现流畅 25/30 FPS 渲染。

#### 🐛 核心缺陷修复 (Bug Fixes)
1. **根治 Python 3.12.3 + PyQt5 表格段错误 (SIGSEGV 退出码 139)**：
   - **问题现象**：在 Ubuntu 24.04 (Python 3.12.3) 下，录像切片列表或通道列表连续点击 3 次即触发底层崩溃；
   - **根因**：PyQt5 `QTableWidget` 内部的 `QItemSelectionModel` 在 Python 3.12 垃圾回收机制下触发 C++ 底层悬挂指针；
   - **修复**：全面将回放录像列表 (`playback_widget.py`) 与通道管理对话框 (`channel_management_dialog.py`) 重构为 `QTreeWidget(setRootIsDecorated=False)` 扁平多列架构，生命周期由 Qt 树节点安全托管，彻底杜绝闪退。
2. **修复录像连续切片切换时的 `AttributeError` 阻断**：
   - **问题现象**：双击录像列表切换不同切片时，报 `AttributeError: type object 'datetime.time' has no attribute 'sleep'`；
   - **根因**：文件头部 `from datetime import time` 别名覆盖了 Python 标准库 `time` 模块；
   - **修复**：规范重构导入为 `import time as py_time` 与 `from datetime import time as dt_time`，确保底层 150ms 硬件复位平滑延时正常执行。
3. **修复 X11 视口黑屏遮挡问题**：
   - 移除了视口控件的 `Qt.WA_PaintOnScreen` 与 QSS 纯黑样式背景覆盖，确保 X11 原生底层视频帧直出无遮盖渲染。
4. **消除 `LD_LIBRARY_PATH` 环境变量全局污染**：
   - 优化 `run.sh` 脚本的动态链接隔离机制，避免厂商 SDK 库污染系统 Nautilus 文件管理器与外部浏览器。

#### ⚡ 稳定性与跨语言优化 (Stability)
- **多切片平滑切换时序缓冲**：在大华 SDK 停止旧回放与发起新回放之间引入 150ms 硬件时序防抖，杜绝底层网络 socket 与解码器线程对 X11 `winId` 句柄的争抢碰撞。
- **动态链接与软链接自动装配**：在发布包内构建完善的 `libhcnetsdk.so`、`libplayercore.so` 及大华依赖软链接链条，开箱即用。

---

### 🪟 Windows 平台 (Windows 10 / 11 64-bit)

#### 🌟 新增特性 (New Features)
1. **大华 (Dahua) 原生 Win64 SDK 集成**：
   - 全面支持大华 64 位 NetSDK (`dhnetsdk.dll`) 与 PlaySDK (`dhplay.dll`)；
   - 支持 HWND 窗口句柄直传硬件加速解码与秒开播放；
   - 完整支持大华 NVR / IPC 录像检索、时间轴标尺映射与精准回放。
2. **海康威视 (Hikvision) Win64 原生渲染完善**：
   - 适配最新海康 Win64 SDK，支持实时双码流一键无缝重载切换；
   - 支持 8 向高精度 PTZ 云台控制与预置点调用。

#### 🐛 体验与稳定性优化 (Improvements & Fixes)
1. **统一列表组件稳定性架构**：
   - Windows 端同步对齐 `QTreeWidget` 表格渲染架构，消除频繁刷新列表时的界面卡顿与重绘闪烁。
2. **回放时间轴与切片切换顺畅度优化**：
   - 优化回放状态机防重入逻辑，多录像段连续双击快速切换不卡死、不假死。
3. **跨端设备配置 100% 互通**：
   - 支持导出/导入通用标准加密与 JSON 配置备份，与 Android 移动端备份文件完全无缝兼容。

#### 📦 打包与分发更新 (Packaging & Distribution)
- 优化 PyInstaller 单目录便携打包脚本，内置完整的海康威视与大华 Win64 原生 SDK 运行库环境；
- 生成独立运行绿色包 `weviewcam_windows_v0.1.5.zip`，解压即用，无需配置外部依赖。

---

### 🧪 测试与质量验证 (Testing & Verification)

- **单元测试覆盖**：`pytest tests/` 26 项核心单元测试（跨平台适配器、设备管理器、ONVIF 协议解析、时间轴计算、跨端备份恢复）**100% 通过**；
- **真机实测**：
  - Windows 11 64-bit 实测通过：海康、大华实时多屏预览、PTZ 云台控制、24小时回放；
  - Ubuntu 24.04 LTS (Python 3.12.3) 实测通过：大华/海康实时流直出、录像回放多段快速双击切换无崩溃、列表点击 100% 稳定。

---

### 📁 发布构件 (Artifacts)
- **Ubuntu 发布包**：`weviewcam_ubuntu_v0.1.5.tar.gz` (71.7 MB)
- **Windows 便携包**：`weviewcam_windows_v0.1.5.zip` (230.9 MB)

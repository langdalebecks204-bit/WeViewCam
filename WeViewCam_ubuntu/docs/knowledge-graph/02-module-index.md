# 模块 / 类 / 方法索引

> 本文件由 `tools/build_graph.py` 自动生成，请勿手工编辑。
> 生成日期：2026-09-30　数据源：`knowledge-graph.json`

行号均指向文件中的定义起始行（`def` / `class` / 赋值语句所在行）。

## 目录

- [adapters/__init__.py](#adapters__init__py)
- [adapters/dahua/__init__.py](#adaptersdahua__init__py)
- [adapters/dahua/adapter.py](#adaptersdahuaadapterpy)
- [adapters/factory.py](#adaptersfactorypy)
- [adapters/hikvision/PlayCtrl.py](#adaptershikvisionplayctrlpy)
- [adapters/hikvision/__init__.py](#adaptershikvision__init__py)
- [adapters/hikvision/adapter.py](#adaptershikvisionadapterpy)
- [adapters/hikvision/driver.py](#adaptershikvisiondriverpy)
- [adapters/hikvision/structures.py](#adaptershikvisionstructurespy)
- [adapters/onvif/__init__.py](#adaptersonvif__init__py)
- [adapters/onvif/adapter.py](#adaptersonvifadapterpy)
- [adapters/onvif/player.py](#adaptersonvifplayerpy)
- [core/__init__.py](#core__init__py)
- [core/base_adapter.py](#corebase_adapterpy)
- [core/device_manager.py](#coredevice_managerpy)
- [core/logger.py](#coreloggerpy)
- [core/player_controller.py](#coreplayer_controllerpy)
- [main.py](#mainpy)
- [scan_rtsp.py](#scan_rtsppy)
- [tests/__init__.py](#tests__init__py)
- [tests/test_adapters.py](#teststest_adapterspy)
- [tests/test_device_manager.py](#teststest_device_managerpy)
- [tests/test_onvif.py](#teststest_onvifpy)
- [tests/test_timeline.py](#teststest_timelinepy)
- [ui/__init__.py](#ui__init__py)
- [ui/device_dialog.py](#uidevice_dialogpy)
- [ui/device_tree_widget.py](#uidevice_tree_widgetpy)
- [ui/live_view_widget.py](#uilive_view_widgetpy)
- [ui/main_window.py](#uimain_windowpy)
- [ui/playback_widget.py](#uiplayback_widgetpy)
- [ui/styles.py](#uistylespy)
- [ui/timeline_bar.py](#uitimeline_barpy)
- [ui/video_widget.py](#uivideo_widgetpy)

## adapters/__init__.py

- **分层**：设备适配层
- **行数**：1
- **职责**：适配器包标识。

## adapters/dahua/__init__.py

- **分层**：设备适配层
- **行数**：4
- **职责**：大华适配器包标识。

## adapters/dahua/adapter.py

- **分层**：设备适配层
- **行数**：109
- **职责**：大华 NetSDK 适配器骨架：返回固定模拟通道与句柄，等待接入 libdhnetsdk.so。

### 类

#### `DahuaAdapter` :23　(基类: BaseDeviceAdapter)

大华适配器骨架（模拟实现）：固定返回 2 个通道与 5100/5200 系句柄，标注了 CLIENT_Init/CLIENT_LoginEx2 接入位置。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 26 | method |  |
| `login()` | 30 | method |  |
| `logout()` | 38 | method |  |
| `get_channels()` | 45 | method |  |
| `start_real_play()` | 51 | method |  |
| `stop_real_play()` | 55 | method |  |
| `capture_picture()` | 59 | method |  |
| `start_record()` | 63 | method |  |
| `stop_record()` | 67 | method |  |
| `ptz_control()` | 71 | method |  |
| `find_records()` | 75 | method |  |
| `start_playback_by_time()` | 87 | method |  |
| `playback_control()` | 91 | method |  |
| `get_playback_pos()` | 95 | method |  |
| `stop_playback()` | 98 | method |  |
| `download_record_by_time()` | 102 | method |  |
| `get_download_pos()` | 105 | method |  |
| `stop_download()` | 108 | method |  |

## adapters/factory.py

- **分层**：设备适配层
- **行数**：28
- **职责**：适配器工厂：按 ProtocolType 分派厂商实现，未知协议回落海康并告警。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `create_device_adapter()` | 16 | 按协议创建适配器实例的策略函数；未知协议回落 HikvisionAdapter 并记录告警。 |

## adapters/hikvision/PlayCtrl.py

- **分层**：设备适配层
- **行数**：54
- **职责**：播放库 FRAME_INFO/DISPLAY_INFO_YUV 与回调类型定义；当前无任何模块引用。
- **折叠节点**：`grp:adapters/hikvision/PlayCtrl.py`，含 2 个定义，明细见 graph.html 与 JSON

## adapters/hikvision/__init__.py

- **分层**：设备适配层
- **行数**：4
- **职责**：海康适配器包标识。

## adapters/hikvision/adapter.py

- **分层**：设备适配层
- **行数**：210
- **职责**：海康适配器：把统一接口映射到 HikvisionNativeDriver，并在未登录时自动补登录。

### 类

#### `HikvisionAdapter` :23　(基类: BaseDeviceAdapter)

海康适配器实现：持有 HikvisionNativeDriver，所有需要登录的操作前自动 login()，并额外提供 start_playback_by_name。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 26 | method |  |
| `login()` | 32 | method |  |
| `logout()` | 54 | method |  |
| `get_channels()` | 63 | method |  |
| `start_real_play()` | 73 | method |  |
| `stop_real_play()` | 90 | method |  |
| `capture_picture()` | 93 | method |  |
| `start_record()` | 96 | method |  |
| `stop_record()` | 99 | method |  |
| `ptz_control()` | 102 | method |  |
| `find_records()` | 123 | method |  |
| `start_playback_by_time()` | 140 | method |  |
| `start_playback_by_name()` | 159 | method |  |
| `playback_control()` | 174 | method |  |
| `get_playback_pos()` | 182 | method |  |
| `stop_playback()` | 185 | method |  |
| `download_record_by_time()` | 188 | method |  |
| `get_download_pos()` | 198 | method |  |
| `stop_download()` | 201 | method |  |
| `refresh_play()` | 204 | method |  |
| `refresh_playback()` | 207 | method |  |

## adapters/hikvision/driver.py

- **分层**：设备适配层
- **行数**：1019
- **职责**：HCNetSDK 原生驱动：.so 动态发现与预加载、登录、通道枚举、实时预览、PTZ 四级降级、录像检索（V50→V30）、回放与窗口分辨率刷新。

### 类

#### `HCNetSDKLibrary` :57　(基类: —)

SDK 单例：按 HIK_SDK_PATH → 内置 HCNetSDK 目录 → sdk/hikvision/lib → lib 顺序查找 libhcnetsdk.so，预加载 crypto/ssl/hpr/HCCore，设置 HCNetSDKCom 路径并 NET_DVR_Init；非 Linux 直接进入模拟模式。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `get_instance()` | 63 | classmethod |  |
| `__init__()` | 68 | method |  |
| `_find_and_load_library()` | 76 | method | Locate and load Hikvision Linux 64-bit SDK .so files. |
| `cleanup()` | 170 | method | Clean up SDK on exit. |
| `get_last_error()` | 180 | method |  |

#### `HikvisionNativeDriver` :186　(基类: —)

原生 API 封装：数字通道状态与工作状态双路探测在线、IPPARACFG_V40 展开数字通道、PTZ 四级降级（Other带速度→Other→句柄带速度→句柄）、录像 V50→V30 回退检索、回放句柄与 PlayM4 窗口分辨率刷新。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 189 | method |  |
| `is_available()` | 193 | method |  |
| `login()` | 196 | method |  |
| `logout()` | 222 | method |  |
| `get_channels()` | 236 | method |  |
| `start_real_play()` | 359 | method |  |
| `stop_real_play()` | 391 | method |  |
| `capture_picture()` | 405 | method |  |
| `start_record()` | 419 | method |  |
| `stop_record()` | 433 | method |  |
| `ptz_control()` | 445 | method |  |
| `find_records()` | 560 | method |  |
| `start_playback_by_time()` | 780 | method |  |
| `start_playback_by_name()` | 831 | method |  |
| `playback_control()` | 860 | method |  |
| `get_playback_pos()` | 904 | method |  |
| `stop_playback()` | 919 | method |  |
| `refresh_play()` | 926 | method | Notify Hikvision SDK to adapt to new window geometry after resize or maximize. |
| `refresh_playback()` | 965 | method | Notify Hikvision playback to adapt to new window geometry. |

## adapters/hikvision/structures.py

- **分层**：设备适配层
- **行数**：1214
- **职责**：海康 SDK C 结构体与常量定义（非官方生成的 ctypes 绑定，含重复定义）。
- **折叠节点**：`grp:adapters/hikvision/structures.py`，含 60 个定义，明细见 graph.html 与 JSON

## adapters/onvif/__init__.py

- **分层**：设备适配层
- **行数**：4
- **职责**：ONVIF 适配器包标识。

## adapters/onvif/adapter.py

- **分层**：设备适配层
- **行数**：519
- **职责**：ONVIF 适配器：多端口握手、Profile 归并为单通道、GetStreamUri 与多厂商 RTSP 路径候选库、RTSP URL 归一化、8 方向 ContinuousMove 云台。

### 类

#### `OnvifAdapter` :35　(基类: BaseDeviceAdapter)

ONVIF 适配器实现：端口列表逐个尝试 ONVIFCamera，GetProfiles 后按分辨率归并出 main/sub 两个 Profile，无 SDK 或握手失败均降级为模拟模式并返回 True。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 38 | method |  |
| `login()` | 51 | method | Connect and authenticate with the ONVIF device. |
| `logout()` | 101 | method | Disconnect and stop all streams for this device. |
| `_parse_channel_profiles()` | 111 | method | Group profiles into logical channels (1 channel per physical camera sensor). |
| `get_channels()` | 138 | method | Return camera channels. |
| `start_real_play()` | 163 | method | Acquire RTSP Stream URI from ONVIF or intelligent multi-vendor candidate list, |
| `stop_real_play()` | 185 | method | Stop real-time stream playback. |
| `capture_picture()` | 193 | method | Capture screenshot of the live stream. |
| `start_record()` | 197 | method | Record live stream to local MP4 file. |
| `stop_record()` | 201 | method | Stop local stream recording. |
| `ptz_control()` | 205 | method | Send standard ONVIF PTZ ContinuousMove or Stop command. |
| `find_records()` | 240 | method | Search recordings (Profile G compliant or simulated for testing). |
| `start_playback_by_time()` | 253 | method | Start recording playback via RTSP or simulated stream. |
| `playback_control()` | 258 | method |  |
| `get_playback_pos()` | 261 | method |  |
| `stop_playback()` | 264 | method |  |
| `download_record_by_time()` | 267 | method |  |
| `get_download_pos()` | 270 | method |  |
| `stop_download()` | 273 | method |  |
| `get_stream_uri_candidates()` | 279 | method | Generate prioritized candidate RTSP URLs across all major camera manufacturers |
| `_get_stream_uri()` | 404 | method | Fetch actual RTSP stream URI from ONVIF with host normalization and safe URL encoding. |
| `_normalize_rtsp_url()` | 452 | method | Correct common ONVIF GetStreamUri flaws: |
| `_construct_fallback_rtsp()` | 484 | method | Generate vendor-compatible RTSP URL patterns when GetStreamUri is unsupported. |
| `_command_to_velocity()` | 496 | staticmethod | Map generic PTZCommand to ONVIF ContinuousMove (pan, tilt, zoom) float vector. |

## adapters/onvif/player.py

- **分层**：播放引擎层
- **行数**：443
- **职责**：RTSP 播放引擎：LibVLC 硬解嵌入 → OpenCV 软解线程 → 模拟模式三级降级；管理会话句柄、抓图、录像与 URL 脱敏。

### 类

#### `OpencvRtspWorker` :37　(基类: threading.Thread)

OpenCV/FFmpeg 拉流线程：强制 TCP 与超时参数、候选路径轮询协商、BGR→QImage 回调、按锁写出 MP4 录制，首次成功路径回写回调。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 43 | method |  |
| `run()` | 57 | method |  |
| `stop()` | 143 | method |  |
| `capture()` | 146 | method |  |
| `start_record()` | 170 | method |  |
| `stop_record()` | 186 | method |  |

#### `RtspSession` :195　(基类: —)

播放会话记录：句柄、URL、目标窗口、是否播放/录制、引擎类型（vlc/opencv/mock）与引擎对象。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 198 | method |  |

#### `RtspPlayerManager` :215　(基类: —)

RTSP 播放单例管理器：句柄自增（起 6100）、窗口表面回调注册表、LibVLC→OpenCV→模拟三级启动策略、抓图/录像/停止与 URL 口令脱敏。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `register_window_surface()` | 223 | classmethod | Register a video surface QImage update callback for software rendering. |
| `unregister_window_surface()` | 229 | classmethod |  |
| `get_instance()` | 234 | classmethod |  |
| `__init__()` | 240 | method |  |
| `has_vlc()` | 265 | method |  |
| `has_cv2()` | 269 | method |  |
| `start_play()` | 272 | method | Start playing an RTSP stream onto the designated X11 / Win32 window. |
| `_on_vlc_error()` | 347 | method |  |
| `_on_vlc_playing()` | 350 | method |  |
| `stop_play()` | 353 | method | Stop playback for the given handle and free resources. |
| `capture_picture()` | 374 | method | Capture current frame to a snapshot file. |
| `start_record()` | 394 | method | Start recording RTSP stream to a local file. |
| `stop_record()` | 406 | method | Stop local stream recording. |
| `stop_all()` | 417 | method | Stop all active sessions on shutdown. |
| `_mask_url()` | 432 | staticmethod | Mask password in rtsp://user:pass@ip:port/ stream URI for logging safety. |

## core/__init__.py

- **分层**：核心域层
- **行数**：3
- **职责**：核心包标识，暴露 __version__ = 0.1.0（全应用版本号唯一来源）。

## core/base_adapter.py

- **分层**：核心域层
- **行数**：238
- **职责**：领域契约层：协议/PTZ/回放枚举、ChannelInfo/DeviceInfo/RecordSegment 数据模型与 BaseDeviceAdapter 抽象接口（20 个抽象方法）。

### 类

#### `ProtocolType` :14　(基类: str, Enum)

设备协议枚举：hikvision / dahua / onvif / custom_rtsp；str 混入使 JSON 序列化直观。

#### `PTZCommand` :21　(基类: Enum)

与厂商无关的云台指令枚举：8 方向 + 变焦/聚焦/光圈共 14 项。

#### `PlaybackCommand` :38　(基类: Enum)

与厂商无关的回放控制枚举：开始/暂停/恢复/快放/慢放/常速/单帧/读进度/设进度。

#### `ChannelInfo` :51　(基类: —)

通道模型：通道号、名称、在线、是否支持云台、所属设备与扩展字段。

#### `DeviceInfo` :61　(基类: —)

设备模型（聚合根）：唯一 ID、名称、IP、管理端口、凭据、协议、RTSP 端口、通道列表、连接态与 extra（含 custom_rtsp_url）。

#### `RecordSegment` :76　(基类: —)

录像片段模型：通道、起止时间、文件名、字节大小、录像类型。

#### `BaseDeviceAdapter` :85　(基类: ABC)

厂商适配器抽象基类：登录/通道/实时预览/抓图/录像/PTZ/检索/回放/下载 + 窗口刷新钩子，是全部厂商差异的唯一收敛点。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 91 | method |  |
| `is_connected()` | 96 | method |  |
| `is_logged_in()` | 100 | method |  |
| `login()` | 104 | method | Connect and authenticate with the device/NVR. |
| `logout()` | 109 | method | Disconnect and release session resources. |
| `get_channels()` | 114 | method | Enumerate active camera channels from NVR or IPC. |
| `start_real_play()` | 119 | method | Start live video preview. |
| `stop_real_play()` | 135 | method | Stop real-time preview session. |
| `capture_picture()` | 140 | method | Capture current video frame to image file (BMP/JPEG). |
| `start_record()` | 145 | method | Start saving live stream to a local video file (MP4). |
| `stop_record()` | 150 | method | Stop local video recording. |
| `ptz_control()` | 155 | method | Control Pan-Tilt-Zoom. |
| `find_records()` | 167 | method | Search for historical recordings on the device/NVR storage. |
| `start_playback_by_time()` | 177 | method | Start recording playback by time range. |
| `playback_control()` | 191 | method | Control playback state: Pause, Resume, Fast, Slow, Step, Seek. |
| `get_playback_pos()` | 201 | method | Get playback progress from 0 to 100%. |
| `stop_playback()` | 206 | method | Stop playback session. |
| `download_record_by_time()` | 211 | method | Start downloading recording segment to local file. |
| `get_download_pos()` | 222 | method | Get download progress percentage (0-100). |
| `stop_download()` | 227 | method | Stop and cancel downloading. |
| `refresh_play()` | 231 | method | Notify video renderer to adapt to new window resolution upon resize. |
| `refresh_playback()` | 235 | method | Notify playback renderer to adapt to new window resolution upon resize. |

## core/device_manager.py

- **分层**：核心域层
- **行数**：244
- **职责**：设备注册中心：设备增删改查、适配器生命周期、通道目录、连接测试与 devices.json 持久化。

### 类

#### `DeviceManager` :23　(基类: —)

设备注册中心实现：内存字典 + JSON 文件双写，按需延迟创建适配器，test_connection 使用临时适配器不落盘。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 26 | method |  |
| `create_adapter()` | 32 | method | Factory method to instantiate the correct vendor adapter. |
| `add_device()` | 37 | method | Add a new device and optionally connect. |
| `update_device()` | 65 | method | Update existing device credentials or network parameters. |
| `remove_device()` | 82 | method | Disconnect and remove device. |
| `get_device()` | 98 | method |  |
| `get_adapter()` | 101 | method |  |
| `list_devices()` | 106 | method |  |
| `connect_device()` | 109 | method | Explicitly connect / login to a device and fetch its channels. |
| `disconnect_device()` | 135 | method | Disconnect a device. |
| `test_connection()` | 148 | method | Test temporary connection parameters without saving. |
| `save_devices()` | 163 | method | Serialize devices to JSON config file. |
| `load_devices()` | 199 | method | Load devices from JSON config file. |

## core/logger.py

- **分层**：核心域层
- **行数**：57
- **职责**：统一日志设施：根 logger VMS，控制台 + 按日期切分文件输出，模块级子 logger。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `setup_logger()` | 14 | 幂等初始化 VMS 根 logger（控制台 + logs/vms_YYYY-MM-DD.log）。 |
| `get_logger()` | 51 | 返回 VMS.<模块名> 子 logger，未初始化时自动初始化。 |

## core/player_controller.py

- **分层**：核心域层
- **行数**：409
- **职责**：视口调度器：SlotState 槽位状态机，把界面窗口句柄映射到实时预览/回放/录像句柄，并负责窗口尺寸变化后的重开流。

### 类

#### `SlotState` :23　(基类: —)

单个视口的状态快照：窗口句柄、设备/通道、直播/回放/录像标志、播放与回放句柄、录像路径、码流类型与时间范围。

#### `PlayerController` :40　(基类: —)

视口调度服务：start_live_play / start_playback / stop_slot / capture_slot / toggle_record_slot / ptz_control / refresh_slot / reopen_* / stop_all；同时是 UI 与适配器之间的唯一通道。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 43 | method |  |
| `get_slot_state()` | 47 | method |  |
| `set_slot_window()` | 52 | method |  |
| `start_live_play()` | 56 | method | Start live view in the specified slot. |
| `start_playback()` | 107 | method | Start recording playback in the specified slot. |
| `control_playback()` | 158 | method | Issue playback controls to active playback slot. |
| `get_playback_pos()` | 170 | method | Query 0-100% progress for active playback slot. |
| `stop_slot()` | 182 | method | Stop video stream on the given slot. |
| `capture_slot()` | 216 | method | Capture screenshot from video stream in slot. |
| `toggle_record_slot()` | 229 | method | Toggle local MP4 recording. |
| `ptz_control()` | 253 | method | Send PTZ command for currently active channel in slot. |
| `refresh_slot()` | 277 | method | Notify active stream in slot that display window dimensions changed. |
| `reopen_live_play()` | 296 | method | Seamlessly reinitialize live preview stream on slot. |
| `reopen_playback()` | 357 | method | Seamlessly restart playback on slot at new resolution from current position. |
| `stop_all()` | 403 | method | Stop all playing slots on application exit. |

## main.py

- **分层**：入口与运维工具
- **行数**：60
- **职责**：应用入口：初始化日志与高 DPI、创建 QApplication、加载图标、启动 MainWindow 事件循环。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `main()` | 22 | 进程主函数：打印启动横幅、检查 DISPLAY、设置高 DPI、创建 QApplication 与 MainWindow 并进入事件循环。 |

## scan_rtsp.py

- **分层**：入口与运维工具
- **行数**：278
- **职责**：独立 RTSP/ONVIF 流地址探测 CLI：端口扫描 + 全品牌路径特征库 DESCRIBE 探测 + OpenCV 真实拉流验证。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `check_tcp_port()` | 105 | 单端口 TCP 握手探测（默认 1s 超时）。 |
| `probe_rtsp_describe()` | 117 | 发送 RTSP DESCRIBE 并解析状态码（200/401 视为路径有效）。 |
| `probe_with_opencv()` | 150 | 用 OpenCV 实际拉取一帧以确认流可用。 |
| `probe_onvif_ports()` | 163 | 遍历常见 ONVIF 端口并用 GetStreamUri 取原生流地址。 |
| `run_diagnostics()` | 191 | 四阶段诊断编排：端口扫描 → ONVIF 发现 → 特征库 DESCRIBE 遍历 → 结果汇总与人工排查建议。 |

## tests/__init__.py

- **分层**：测试层
- **行数**：1
- **职责**：测试包标识。

## tests/test_adapters.py

- **分层**：测试层
- **行数**：165
- **职责**：适配器工厂分派、海康适配器全生命周期（模拟模式）、大华/ONVIF 冒烟、PlayerController 重开流回归。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `test_factory_creation()` | 19 |  |
| `test_hikvision_adapter_lifecycle()` | 48 |  |
| `test_dahua_and_onvif_adapters()` | 103 |  |
| `test_player_controller_reopen()` | 119 |  |

## tests/test_device_manager.py

- **分层**：测试层
- **行数**：102
- **职责**：设备管理 CRUD 与磁盘持久化、连接测试的消息格式、设备对话框常用名称填充（需 PyQt5）。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `test_device_manager_crud()` | 12 |  |
| `test_device_manager_test_connection()` | 60 |  |
| `test_device_dialog_quick_names()` | 81 |  |

## tests/test_onvif.py

- **分层**：测试层
- **行数**：164
- **职责**：ONVIF 生命周期、RTSP URL 归一化、PTZ 速度向量映射、RTSP 引擎句柄与 URL 脱敏、候选路径库与自定义 RTSP 优先级。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `test_onvif_adapter_lifecycle()` | 13 |  |
| `test_onvif_ptz_velocity_mapping()` | 77 |  |
| `test_rtsp_player_manager()` | 103 |  |
| `test_stream_uri_candidates_and_negotiation()` | 116 |  |

## tests/test_timeline.py

- **分层**：测试层
- **行数**：38
- **职责**：时间轴坐标与秒偏移的纯数学校验（无 GUI）。

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `test_timeline_math()` | 10 |  |

## ui/__init__.py

- **分层**：界面层
- **行数**：1
- **职责**：界面包标识。

## ui/device_dialog.py

- **分层**：界面层
- **行数**：228
- **职责**：设备新增/编辑对话框：协议选择联动默认端口、常用中文名快捷填充、自定义 RTSP 路径、连接测试。

### 类

#### `DeviceDialog` :16　(基类: QDialog)

模态对话框：协议切换联动端口（8000/37777/80/554）、常用名称下拉、extra.custom_rtsp_url 读写、测试连接复用 DeviceManager.test_connection。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 19 | method |  |
| `_init_ui()` | 33 | method |  |
| `_on_quick_name_selected()` | 134 | method |  |
| `_on_protocol_changed()` | 140 | method |  |
| `_load_existing_device()` | 151 | method |  |
| `_get_form_device_info()` | 164 | method |  |
| `_test_connection()` | 187 | method |  |
| `_save_device()` | 207 | method |  |

## ui/device_tree_widget.py

- **分层**：界面层
- **行数**：267
- **职责**：设备资源树：设备/通道两级展示、在线状态圆点图标、双击播放与右键连接/刷新/编辑/删除。

### 类

#### `DeviceTreeWidget` :58　(基类: QWidget)

设备树：按协议显示中文厂商前缀与在线通道统计，双击通道请求播放，右键提供连接/断开、刷新通道、编辑、删除（带确认框）。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 66 | method |  |
| `_init_ui()` | 71 | method |  |
| `refresh_devices()` | 113 | method | Populate tree with current devices and channels. |
| `_on_item_double_clicked()` | 173 | method |  |
| `_show_context_menu()` | 192 | method |  |
| `_refresh_device_channels()` | 237 | method |  |
| `_toggle_connect()` | 249 | method |  |
| `_confirm_delete()` | 256 | method |  |

### 顶层函数

| 函数 | 行 | 说明 |
| --- | --- | --- |
| `get_status_icon()` | 20 | 生成并缓存圆形状态图标（高 DPI 抗锯齿）。 |
| `icon_online()` | 46 | 绿色在线图标（#2ea043）。 |
| `icon_offline()` | 50 | 红色离线图标（#da3633）。 |
| `icon_disconnected()` | 54 | 灰色未连接图标（#8b949e）。 |

## ui/live_view_widget.py

- **分层**：界面层
- **行数**：440
- **职责**：实时监控页：16 个视频视口的 1/4/9/16 分屏布局、双击最大化、PTZ 面板与速度滑块、抓图/本地录像委托。

### 类

#### `LiveViewWidget` :25　(基类: QWidget)

实时监控页：预建 16 个 VideoWidget，switch_layout 重排网格，QTimer 延迟 60/80ms 通知 SDK 刷新或重开流，PTZ 面板按下发送/抬起停止。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 28 | method |  |
| `_init_ui()` | 41 | method |  |
| `_create_ptz_panel()` | 147 | method |  |
| `_create_ptz_btn()` | 241 | method |  |
| `_send_ptz_command()` | 251 | method |  |
| `_toggle_ptz_panel()` | 269 | method |  |
| `switch_layout()` | 272 | method | Switch grid layout: 1, 4, 9, or 16 screens. |
| `select_slot()` | 317 | method | Highlight specified slot. |
| `toggle_fullscreen()` | 323 | method | Toggle fullscreen mode for currently active slot. |
| `_reopen_slot_if_playing()` | 327 | method | Reopen playing stream on slot to force SDK hardware decoder to re-bind to new dimensions. |
| `play_channel_in_slot()` | 334 | method | Start playing channel in the active or specified slot. |
| `_on_slot_clicked()` | 355 | method |  |
| `_on_slot_double_clicked()` | 358 | method | Double click to toggle between single-slot maximized and multi-split layout. |
| `_on_slot_resized()` | 386 | method | Called when a video slot changes size. |
| `_refresh_active_slots()` | 391 | method | Notify SDK for all currently visible active slots. |
| `_on_slot_close_requested()` | 397 | method |  |
| `_on_slot_capture()` | 401 | method |  |
| `_on_slot_record_toggle()` | 408 | method |  |
| `_on_snapshot_clicked()` | 426 | method |  |
| `_on_record_clicked()` | 434 | method |  |
| `stop_all_slots()` | 437 | method |  |

## ui/main_window.py

- **分层**：界面层
- **行数**：249
- **职责**：主窗口外壳：顶部导航、实时/回放页堆栈、SDK 状态与时钟、设备增删改对话框编排、退出清理。

### 类

#### `MainWindow` :31　(基类: QMainWindow)

应用外壳：组装 DeviceManager 与 PlayerController，管理实时/回放两个页面、设备对话框结果回流、F11/Esc 全屏与窗口状态变化后的重开流、closeEvent 释放流与 SDK。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 34 | method |  |
| `_init_ui()` | 55 | method |  |
| `_init_clock_timer()` | 161 | method |  |
| `_update_clock()` | 168 | method |  |
| `switch_view()` | 172 | method | Switch between Live View (0) and Playback View (1). |
| `_on_channel_double_clicked()` | 182 | method | Play channel in active slot. |
| `_show_add_device_dialog()` | 188 | method |  |
| `_show_edit_device_dialog()` | 195 | method |  |
| `_on_delete_device()` | 205 | method |  |
| `keyPressEvent()` | 211 | method |  |
| `changeEvent()` | 226 | method |  |
| `_on_window_state_changed()` | 231 | method | Called when main window is maximized, restored or set to full screen. |
| `closeEvent()` | 242 | method | Clean up on window close. |

## ui/playback_widget.py

- **分层**：界面层
- **行数**：430
- **职责**：回放页：设备/通道/日期检索、录像片段列表、24 小时时间轴联动、播放/暂停/倍速/单帧/拖拽定位与截图。

### 类

#### `PlaybackWidget` :23　(基类: QWidget)

回放页：专用 slot_id=99，检索结果同时填充表格与时间轴，1 秒定时器推进指针并按倍速前进，调用 control_playback 下发暂停/倍速/单帧/定位。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 26 | method |  |
| `_init_ui()` | 40 | method |  |
| `_init_timer()` | 210 | method | Timer to tick playback time and update slider. |
| `refresh_devices_combo()` | 216 | method | Update device dropdown from DeviceManager. |
| `_on_device_changed()` | 224 | method |  |
| `search_records()` | 246 | method | Execute record search for selected channel and date. |
| `_on_table_row_double_clicked()` | 288 | method |  |
| `_on_timeline_time_selected()` | 294 | method |  |
| `start_playback_at()` | 298 | method | Start playback at specific time. |
| `_toggle_play_pause()` | 330 | method |  |
| `stop_playback()` | 351 | method |  |
| `_speed_up()` | 361 | method |  |
| `_slow_down()` | 368 | method |  |
| `_normal_speed()` | 375 | method |  |
| `_step_frame()` | 382 | method |  |
| `_on_slider_moved()` | 387 | method |  |
| `_on_timer_tick()` | 391 | method |  |
| `_snapshot()` | 403 | method |  |
| `_toggle_fullscreen_playback()` | 414 | method | Toggle fullscreen mode for playback video slot. |

## ui/styles.py

- **分层**：界面层
- **行数**：263
- **职责**：深色监控主题 QSS 字符串 DARK_THEME_QSS，由 MainWindow 全局应用。

## ui/timeline_bar.py

- **分层**：界面层
- **行数**：239
- **职责**：自绘 24 小时交互时间轴：录像区间着色、自适应刻度、滚轮以鼠标为中心缩放、拖拽定位指针。

### 类

#### `TimelineBar` :22　(基类: QWidget)

自定义控件：秒↔像素双向换算、按缩放级别自适应主/次刻度、录像区间矩形、红色指针与拖拽 seek，向外发出 time_selected(datetime)。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 28 | method |  |
| `set_date()` | 57 | method | Switch timeline day and reset zoom to full 24 hours. |
| `set_records()` | 65 | method | Load recording segments for display. |
| `set_current_time()` | 70 | method | Update active playback needle time. |
| `set_zoom_duration()` | 75 | method | Set visible zoom duration in hours (e.g. 24, 12, 4, 1). |
| `_sec_to_x()` | 84 | method | Convert second offset from day start to pixel X. |
| `_x_to_sec()` | 89 | method | Convert pixel X to second offset from day start. |
| `paintEvent()` | 94 | method |  |
| `mousePressEvent()` | 195 | method |  |
| `mouseMoveEvent()` | 200 | method |  |
| `mouseReleaseEvent()` | 214 | method |  |
| `wheelEvent()` | 218 | method | Zoom in / zoom out centered on cursor position. |
| `_seek_to_mouse()` | 234 | method |  |

## ui/video_widget.py

- **分层**：界面层
- **行数**：271
- **职责**：单个视频视口：VideoSurface 提供原生 X11 句柄给 SDK 硬解，并支持 OpenCV 帧的 QImage 软渲染、OSD 叠层与右键菜单。

### 类

#### `VideoSurface` :17　(基类: QWidget)

纯渲染面：WA_NativeWindow 暴露 X11 句柄供 SDK 直绘；软解时按等比缩放绘制 QImage；空闲时绘制“视口 N (空闲)”占位并清屏。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 23 | method |  |
| `update_frame()` | 45 | method | Called by software/OpenCV RTSP decoding thread to present new video frame. |
| `set_playing()` | 50 | method |  |
| `paintEvent()` | 58 | method |  |

#### `VideoWidget` :94　(基类: QFrame)

视口容器：顶部 REC/标题/关闭 OSD、中间 VideoSurface、底部状态与帧率；对外发出 clicked/double_clicked/close_requested/capture_requested/record_toggle_requested/resized 信号与右键菜单。

| 方法 | 行 | 类型 | 说明 |
| --- | --- | --- | --- |
| `__init__()` | 105 | method |  |
| `_init_ui()` | 122 | method |  |
| `get_win_id()` | 182 | method | Returns the native X11 window id of the inner video surface. |
| `set_selected()` | 192 | method | Set visual highlight border. |
| `set_stream_info()` | 204 | method |  |
| `set_recording()` | 212 | method |  |
| `clear_stream()` | 216 | method |  |
| `refresh_idle_surface()` | 228 | method | Force clean repaint of idle surface on layout switch or window resize. |
| `mousePressEvent()` | 233 | method |  |
| `resizeEvent()` | 238 | method |  |
| `mouseDoubleClickEvent()` | 246 | method |  |
| `contextMenuEvent()` | 252 | method |  |

## 折叠节点明细

### `adapters/hikvision/PlayCtrl.py` — PlayCtrl 解码回调定义（未被引用）

共 2 个定义：

- `FRAME_INFO` :13　`DISPLAY_INFO_YUV` :26

### `adapters/hikvision/structures.py` — ctypes 结构体集合（自动生成）

共 60 个定义：

- `NET_DVR_DEVICEINFO_V30` :94　`NET_DVR_DEVICEINFO_V40` :178　`NET_DVR_IPADDR` :211　`NET_DVR_ADDRESS` :221
- `NET_DVR_USER_LOGIN_INFO` :236　`NET_DVR_LOCAL_SDK_PATH` :260　`NET_DVR_PREVIEWINFO` :272　`NET_DVR_JPEGPARA` :300
- `NET_DVR_SHOWSTRINGINFO` :312　`NET_DVR_SHOWSTRING_V30` :327　`NET_DVR_XML_CONFIG_OUTPUT` :339　`NET_DVR_XML_CONFIG_INPUT` :356
- `NET_DVR_ALARMER` :375　`NET_DVR_SETUPALARM_PARAM` :401　`NET_DVR_ALARMINFO_V30` :429　`NET_DVR_SETUPALARM_PARAM` :444
- `NET_DVR_TIME` :472　`NET_DVR_IPADDR` :486　`NET_DVR_ACS_EVENT_INFO` :496　`NET_DVR_ACS_ALARM_INFO` :537
- `NET_VCA_POINT` :565　`NET_DVR_ID_CARD_INFO_EXTEND` :573　`NET_DVR_DATE` :592　`NET_DVR_ID_CARD_INFO` :601
- `NET_DVR_TIME` :619　`NET_DVR_TIME_V30` :631　`NET_DVR_IPADDR` :647　`NET_DVR_ID_CARD_INFO_ALARM` :654
- `NET_DVR_ALARM_ISAPI_PICDATA` :688　`NET_DVR_ALARM_ISAPI_INFO` :701　`NET_DVR_LOCAL_GENERAL_CFG` :716　`NET_DVR_STREAM_INFO` :736
- `NET_DVR_VOD_PARA` :745　`NET_DVR_TIME_SEARCH_COND` :768　`NET_DVR_TIME_SEARCH` :786　`NET_DVR_ATMFINDINFO` :803
- `NET_DVR_SPECIAL_FINDINFO_UNION` :815　`NET_DVR_FILECOND_V50` :822　`NET_DVR_TIME` :848　`NET_DVR_FILECOND` :862
- `NET_DVR_FINDDATA_V30` :877　`NET_DVR_FINDDATA_V50` :894　`NET_DVR_IPDEVINFO_V31` :920　`NET_DVR_IPCHANINFO` :939
- `NET_DVR_IPSERVER_STREAM` :955　`NET_DVR_STREAM_MEDIA_SERVER_CFG` :974　`NET_DVR_DEV_CHAN_INFO` :986　`NET_DVR_PU_STREAM_CFG` :1006
- `NET_DVR_DDNS_STREAM_CFG` :1015　`NET_DVR_PU_STREAM_URL` :1045　`NET_DVR_HKDDNS_STREAM` :1057　`NET_DVR_IPCHANINFO_V40` :1076
- `NET_DVR_GET_STREAM_UNION` :1090　`NET_DVR_STREAM_MODE` :1102　`NET_DVR_IPPARACFG_V40` :1115　`NET_DVR_PLAYCOND` :1129
- `NET_DVR_DIGITAL_CHANNEL_STATE` :1161　`NET_DVR_DISKSTATE` :1176　`NET_DVR_CHANNELSTATE_V30` :1184　`NET_DVR_WORKSTATE_V30` :1201

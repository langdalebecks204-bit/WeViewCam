# 四、关键运行时流程

图谱 `flows` 字段固化了 5 条主链路。下面给出时序细节与代码定位；括号内为 `文件:行号`，可用 [02-module-index.md](02-module-index.md) 交叉核对。

---

## 4.1 FLOW-BOOT · 应用启动

```mermaid
sequenceDiagram
    autonumber
    participant OS as 操作系统
    participant M as main.py
    participant LG as core.logger
    participant SDK as HCNetSDKLibrary
    participant MW as MainWindow
    participant DM as DeviceManager
    participant PC as PlayerController
    participant UI as 各页面控件

    OS->>M: python main.py
    M->>LG: setup_logger() 幂等初始化
    M->>M: 检查 DISPLAY 环境变量并告警
    M->>M: 设置高 DPI 属性 AA_EnableHighDpiScaling
    M->>M: 创建 QApplication 并加载 icon.png 或 图标.jpg
    M->>MW: MainWindow()
    MW->>SDK: get_instance() 触发 _find_and_load_library()
    Note over SDK: 顺序尝试 HIK_SDK_PATH → 内置 HCNetSDK 目录 → sdk/hikvision/lib → lib
    SDK-->>MW: is_loaded 决定状态栏徽标为“已就绪”或“模拟/未加载”
    MW->>DM: DeviceManager() → load_devices()
    DM-->>MW: 设备与通道目录
    MW->>PC: PlayerController(device_manager)
    MW->>UI: 构建 DeviceTree / LiveView / Playback / 状态栏 / 时钟定时器
    M->>OS: app.exec_() 进入事件循环
```

**要点**

- SDK 加载发生在 `MainWindow.__init__` 里（`ui/main_window.py:103`），**不是**在首次连接设备时；因此启动横幅一出，SDK 的成败就已确定。
- `main.py` 对 `ui.main_window` 采用函数内导入（`main.py:51`），把 Qt 全量加载推迟到 `QApplication` 建立之后。
- 启动期唯一可能抛错而不被吞掉的是 `DeviceManager.load_devices()` 之外的部分；配置解析异常被 `try/except` 捕获并仅记录日志（`core/device_manager.py:243`）。

---

## 4.2 FLOW-LIVE · 双击通道开启实时预览

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant DT as DeviceTreeWidget
    participant MW as MainWindow
    participant LV as LiveViewWidget
    participant VW as VideoWidget
    participant PC as PlayerController
    participant DM as DeviceManager
    participant FA as factory
    participant A as BaseDeviceAdapter
    participant ENG as 播放引擎

    U->>DT: 双击通道节点
    DT->>MW: channel_double_clicked(device_id, channel_no, name)
    MW->>MW: switch_view(0) 切到实时监控页
    MW->>LV: play_channel_in_slot(...)
    LV->>VW: get_win_id() 取 X11 winId 并注册帧回调
    LV->>PC: start_live_play(slot_id, device, ch, win_id, stream_type)
    PC->>PC: 槽位已在播放则先 stop_slot()
    PC->>DM: get_adapter(device_id)
    alt 适配器尚未创建
        DM->>FA: create_device_adapter(device_info)
        FA-->>DM: HikvisionAdapter / DahuaAdapter / OnvifAdapter
    end
    alt 设备未连接
        PC->>DM: connect_device(device_id)
        DM->>A: login()
        DM->>A: get_channels()
    end
    PC->>A: start_real_play(channel_no, win_id, stream_type)
    A->>ENG: HCNetSDK RealPlay_V40 或 RtspPlayerManager.start_play
    ENG-->>A: play_handle
    A-->>PC: play_handle
    PC->>PC: 写回 SlotState 并置 is_live
    LV->>VW: set_stream_info(名称, 状态文案)
```

**要点**

- 播放前有两道自动补全：**适配器懒创建**（`core/device_manager.py:101-104`）与**登录懒补**（`core/player_controller.py:80-83`），因此用户不必先点"连接设备"。
- 切换槽位内容时先 `stop_slot()` 释放旧句柄（`core/player_controller.py:69-70`），避免句柄泄漏。
- `win_id` 由 `VideoWidget.get_win_id()` 提供，取的是内层 `VideoSurface` 的原生窗口，而不是外层 `QFrame`——这决定了硬解画面是否被 OSD 遮挡。

---

## 4.3 FLOW-ONVIF · ONVIF 取流协商（本项目最复杂的一条链路）

```mermaid
sequenceDiagram
    autonumber
    participant OA as OnvifAdapter
    participant Z as onvif-zeep
    participant RPM as RtspPlayerManager
    participant W as OpencvRtspWorker
    participant VS as VideoSurface

    OA->>Z: ONVIFCamera(ip, port) 逐端口尝试 默认端口 + 8080/80/8899/8000/5000/8090
    alt 握手成功
        Z-->>OA: GetProfiles()
        OA->>OA: _parse_channel_profiles 按分辨率归并为 main/sub
        OA->>Z: GetStreamUri RTP-Unicast 失败则 RTP_Unicast 再试 Media2
        Z-->>OA: 原始 Uri
        OA->>OA: _normalize_rtsp_url 替换内网 IP 并编码凭据
    else 全部端口失败或无 onvif-zeep
        OA->>OA: 置 _is_logged_in=True 并返回 True 进入模拟模式
    end
    OA->>OA: get_stream_uri_candidates 自定义 URL > 已缓存可用 URL > ONVIF Uri > 40+ 品牌路径
    OA->>RPM: start_play(primary_url, win_id, candidates, url_matched_callback)
    alt VLC 可用且 win_id 大于 0
        RPM->>RPM: libvlc set_xwindow 硬解直绘 首帧最快
    else cv2 可用
        RPM->>W: OpencvRtspWorker.start() 后台线程
        W->>W: 按候选列表轮询 DESCRIBE 未命中则换下一条
        W->>W: 命中后回写 rtsp_url 并触发 url_matched_callback 缓存
        W->>VS: frame_callback(QImage) 经 _WIN_SURFACE_REGISTRY 每帧推送
        VS->>VS: paintEvent 按 KeepAspectRatio 绘制
    else 两者皆无
        RPM->>RPM: mock 模式 直接返回句柄
    end
```

**要点**

- **路径候选是核心设计**：很多国产道闸/车牌一体机不响应标准 ONVIF，`get_stream_uri_candidates()`（`adapters/onvif/adapter.py:279-402`）把臻识/华夏智信/芊熠/大华/海康/雄迈/宇视/天地伟业等 40 余条路径按优先级排好，首次命中后写入 `_cached_working_urls`，后续直接复用（这是 [RISK-12](06-issues-and-roadmap.md) 的优化点：候选多且串行尝试）。
- **软渲染回调是唯一旁路**：`VideoSurface.__init__` 即注册（`ui/video_widget.py:39-43`），`get_win_id()` 时再注册一次；解码线程通过 `_WIN_SURFACE_REGISTRY` 回调把 `QImage` 送进 Qt。注册从未注销，见 [BUG-03](06-issues-and-roadmap.md)。
- **日志脱敏**：URL 中的口令统一经 `RtspPlayerManager._mask_url()` 处理后再落日志（`adapters/onvif/player.py:431-443`），但真实 URL 仍以明文存在于内存与 SDK 调用中。

---

## 4.4 FLOW-PLAYBACK · 录像检索与 24 小时时间轴回放

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant PB as PlaybackWidget
    participant A as BaseDeviceAdapter
    participant HD as HikvisionNativeDriver
    participant SDK as HCNetSDK
    participant TL as TimelineBar
    participant PC as PlayerController

    U->>PB: 选择设备/通道/日期 点击检索
    PB->>A: find_records(channel_no, 00:00:00, 23:59:59) 同步阻塞 UI 线程
    A->>HD: find_records(...)
    HD->>SDK: NET_DVR_FindFile_V50 并按 0.05s 轮询 FindNextFile_V50
    alt V50 结果为空
        HD->>SDK: NET_DVR_FindFile_V30 回退检索
    end
    HD-->>PB: List of RecordSegment
    PB->>TL: set_date(target_date) 与 set_records(records)
    PB->>PB: 填充录像片段表格
    U->>TL: 点击或拖拽时间轴指针
    TL->>PB: time_selected(datetime)
    PB->>PC: start_playback(slot=99, device, ch, start, 当日23:59:59, win_id)
    PC->>A: start_playback_by_time(...)
    A-->>PC: playback_handle
    PB->>PB: 启动 1 秒 QTimer
    loop 每秒
        PB->>TL: set_current_time(前进 1 秒 × 倍速)
        PB->>PC: get_playback_pos(slot) 回读进度并同步滑块
    end
    U->>PB: 暂停/快放/慢放/单帧/拖动滑块
    PB->>PC: control_playback(slot, PlaybackCommand.*, param)
```

**要点**

- 回放使用**专用槽位 `slot_id = 99`**（`ui/playback_widget.py:31`），与实时监控的 0–15 号槽位完全隔离，二者可同时播放。
- 检索是**同步调用且在 UI 线程**（`ui/playback_widget.py:265`），驱动层最长会轮询 100×0.05s；弱网设备上界面会卡住（[RISK-07](06-issues-and-roadmap.md)）。
- 进度采用**双源**：UI 定时器自行按倍速推进指针（保证画面流畅），同时每秒向 SDK 回读真实进度覆盖滑块（保证最终一致）。
- 时间轴缩放窗口化 24h → 12h → 4h → 1h（`set_zoom_duration`），滚轮缩放以鼠标位置为锚点。

---

## 4.5 FLOW-RESIZE · 窗口缩放 / 最大化后的重开流

这是本项目特有的补偿机制：X11 硬解窗口在父控件尺寸剧变后不会自动重排，需要显式通知甚至重建流。

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant MW as MainWindow
    participant LV as LiveViewWidget
    participant PC as PlayerController
    participant A as 适配器
    participant T as QTimer

    U->>MW: 最大化 / 还原 / 全屏 / 双击视口 / 切换分屏
    alt 主窗口状态变化
        MW->>MW: changeEvent 捕获 WindowStateChange
        T-->>MW: 延迟 120ms 待布局稳定
        MW->>LV: _refresh_active_slots(count)
        MW->>LV: _reopen_slot_if_playing(active_slot)
    else 视口双击最大化或还原
        LV->>LV: 重排网格并 select_slot
        T-->>LV: 延迟 60ms 后刷新全部可见槽位
        T-->>LV: 延迟 80ms 后重开当前视口流
    else 单个视口尺寸变化
        LV->>LV: VideoWidget.resized 信号
        T-->>PC: 延迟 80ms refresh_slot(slot, win_id)
    end
    LV->>PC: refresh_slot 或 reopen_live_play
    alt 仅刷新
        PC->>A: refresh_play / refresh_playback SDK 内部适配新尺寸
    else 重建流
        PC->>A: stop_record 与 stop_real_play 释放旧句柄
        PC->>A: start_real_play(新 win_id) 重新绑定窗口
        PC->>A: 若原在录像则 start_record 恢复录像
    end
```

**要点**

- 三级延迟（60 / 80 / 120 ms）是刻意的时间预算：先等 Qt 完成布局，再通知 SDK 刷新，最后才对需要重建的视口重开流。
- `reopen_live_play()`（`core/player_controller.py:296-355`）会**自动恢复原本进行中的本地录像**，这是它在实现上最容易被忽略的部分。
- `reopen_playback()`（`core/player_controller.py:357-401`）存在**实参顺序缺陷**（[BUG-01](06-issues-and-roadmap.md)），该分支下的重开流在真实 SDK 上不可用；模拟模式下因为句柄是编造的所以测试看不出来。
- 视口销毁时软渲染回调未注销（[BUG-03](06-issues-and-roadmap.md)），长时间反复切换分屏会累积注册表条目。

---

## 4.6 五条流程在图谱中的位置

| 流程 id | 入口节点 | 涉及节点数 | 关键风险 |
| --- | --- | --- | --- |
| `FLOW-BOOT` | `fn:main.py#main` | 9 | RISK-11（Windows 下静默降级为模拟） |
| `FLOW-LIVE` | `cls:ui/device_tree_widget.py#DeviceTreeWidget` | 8 | BUG-02（PTZ 回退分支抛异常） |
| `FLOW-ONVIF` | `cls:adapters/onvif/adapter.py#OnvifAdapter` | 4 | RISK-04（失败仍报成功）、RISK-12（候选串行） |
| `FLOW-PLAYBACK` | `cls:ui/playback_widget.py#PlaybackWidget` | 5 | RISK-03（ONVIF 回放是假的）、RISK-07（UI 阻塞） |
| `FLOW-RESIZE` | `cls:ui/main_window.py#MainWindow` | 4 | BUG-01（回放重开流实参错位） |

在 `graph.html` 中直接搜索 `PlayerController` 或 `RtspPlayerManager`，可看到这些流程节点的高密度连边。

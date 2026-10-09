# 六、缺陷、风险与改进路线

图谱里的 `issues` 数组固化了 17 项发现（6 个 BUG + 11 个 RISK），每项都带定位、影响范围（`affects` 边指向具体模块/类）与修复建议。本文按严重级别排序并给出可执行的验证方式。

**统计**：高危 5 · 中危 8 · 低危 4。仓库自带测试当前 **12 passed**，`verify_graph.py` **409 项断言通过**——即下列问题都是"测试覆盖不到"的盲区，不是已回归的缺陷。

> **复核说明**：本清单经过一轮独立的对抗式复核（逐条比对源码）。复核推翻了一条我最初写入的错误结论（曾误称 `LICENSE`、`weviewcam.desktop`、发布包不在仓库中——实际三者均存在于根目录），并纠正了 BUG-04 的影响描述、下调了 RISK-05 的严重级别、补充了 BUG-05/BUG-06 两项新发现。详见 §6.7。

---

## 6.1 总览

| 编号 | 级别 | 标题 | 定位 | 影响面 |
| --- | --- | --- | --- | --- |
| [BUG-01](#bug-01) | 🔴 高 | `reopen_playback` 实参顺序与接口签名不一致 | `core/player_controller.py:391` | `PlayerController`、`BaseDeviceAdapter` |
| [BUG-02](#bug-02) | 🔴 高 | 访问不存在的 `PlayerController.slots` 属性 | `ui/live_view_widget.py:257` | `LiveViewWidget`、`PlayerController` |
| [BUG-03](#bug-03) | 🟡 中 | 窗口表面回调注册后从不注销 | `ui/video_widget.py:41,187` | `VideoSurface`、`RtspPlayerManager` |
| [BUG-04](#bug-04) | 🟡 中 | 重开流失败后 `is_recording` 残留为 `True` | `core/player_controller.py:318-355` | `PlayerController`、`SlotState` |
| [BUG-05](#bug-05) | 🟡 中 | 停止录像的提示对话框永远显示空路径 | `ui/live_view_widget.py:412-415` | `LiveViewWidget`、`PlayerController` |
| [BUG-06](#bug-06) | 🟡 中 | OpenCV 引擎首帧前启动录像会静默无产出 | `adapters/onvif/player.py:170-184` | `OpencvRtspWorker`、`RtspPlayerManager` |
| [RISK-01](#risk-01) | 🔴 高 | 设备口令明文落盘 | `core/device_manager.py:174` | `DeviceManager`、`devices.json` |
| [RISK-02](#risk-02) | 🟡 中 | `save_devices` 对无目录路径会失败 | `core/device_manager.py:165` | `DeviceManager` |
| [RISK-03](#risk-03) | 🔴 高 | ONVIF 回放/检索/下载为模拟实现 | `adapters/onvif/adapter.py:240-274` | `OnvifAdapter` |
| [RISK-04](#risk-04) | 🔴 高 | 登录失败仍返回成功，无法感知降级 | `adapters/onvif/adapter.py:97-99` | `OnvifAdapter`、`DeviceManager` |
| [RISK-05](#risk-05) | ⚪ 低 | 重复结构体定义造成静默遮蔽 | `adapters/hikvision/structures.py` | 全部海康调用（当前无害） |
| [RISK-06](#risk-06) | ⚪ 低 | `PlayCtrl.py` 为未接线的死代码 | `adapters/hikvision/PlayCtrl.py` | — |
| [RISK-07](#risk-07) | 🟡 中 | UI 线程内同步执行 SDK 检索与登录 | `ui/playback_widget.py:265` | `PlaybackWidget`、`DeviceManager`、驱动 |
| [RISK-08](#risk-08) | 🟡 中 | 测试对真实 QApplication 有隐含依赖 | `tests/test_device_manager.py:81` | 测试套件 |
| [RISK-10](#risk-10) | ⚪ 低 | 诊断工具硬编码内网默认 IP | `scan_rtsp.py:275` | `scan_rtsp.py` |
| [RISK-11](#risk-11) | 🟡 中 | Windows 开发环境下海康链路静默降级 | `adapters/hikvision/driver.py:113` | `HCNetSDKLibrary` |
| [RISK-12](#risk-12) | ⚪ 低 | RTSP 候选路径缺少总超时与并发上限 | `adapters/onvif/adapter.py:279` | `OnvifAdapter` |

---

## 6.2 高危问题

### BUG-01

**`reopen_playback` 实参顺序与接口签名不一致** · 🔴 高 · `core/player_controller.py:391`

```python
# 接口签名（core/base_adapter.py:176）
def start_playback_by_time(self, channel_no, win_id, start_time, end_time) -> int: ...

# 实际调用（core/player_controller.py:391）—— 位置参数错位
new_handle = adapter.start_playback_by_time(channel_no, start_t, end_t, w_id)
```

`win_id` 收到 `datetime`，`start_time` 收到 `end_time`，`end_time` 收到窗口句柄。因为位置参数不报错，模拟模式（`is_available=False` 时直接 `return 3000 + channel_no`）让回归测试照样通过，掩盖了问题。

**触发路径**：回放中最大化/全屏/还原 → `MainWindow._on_window_state_changed`（`ui/main_window.py:240`）或 `PlaybackWidget._toggle_fullscreen_playback`（`ui/playback_widget.py:425`）→ `reopen_playback`。

**修复**：

```python
new_handle = adapter.start_playback_by_time(
    channel_no=channel_no, win_id=w_id, start_time=start_t, end_time=end_t
)
```

**验证**：真实设备上回放中切换全屏，检查画面是否从当前时刻恢复；或加单测断言 `HikvisionNativeDriver.start_playback_by_time` 收到的关键字参数。

### BUG-02

**访问不存在的 `PlayerController.slots` 属性** · 🔴 高 · `ui/live_view_widget.py:257`

```python
for s_id, st in self.player_controller.slots.items():   # 实际属性名是 _slots
```

`PlayerController.__init__` 只定义了 `self._slots`（`core/player_controller.py:45`），全文件没有任何 `@property`。当"当前选中视口不是直播"时进入该回退分支，必然抛 `AttributeError`——也就是说**只要用户先点一个空闲视口再按云台方向键，PTZ 就整条失效**（异常在 Qt 槽内被打印，界面无提示）。

**修复**：在 `PlayerController` 暴露只读属性，并让调用方走公开 API：

```python
@property
def slots(self) -> Dict[int, SlotState]:
    return self._slots
```

**验证**：选中空视口后按住 PTZ 方向键，观察控制台无 `AttributeError`，且另一路正在直播的通道能正常转动。

### RISK-01

**设备口令明文落盘** · 🔴 高 · `core/device_manager.py:174`

`save_devices()` 直接写入 `password` 字段。`config/devices.json` 会被 `package.sh` / `pack.ps1` 白名单收录进发布包，且 `_mask_url` 只对**日志**脱敏，配置与内存中始终是明文。

**修复建议**（按成本递增）：

1. 最低成本：落盘前去敏 + 首启提示；文件权限收紧到 `0600`（`os.chmod`）；
2. 推荐：口令交 `keyring`/系统密钥环，配置只存引用；
3. 完整：本地密钥加密（如 `cryptography.Fernet` + 用户主密钥）。

**验证**：修复后 `grep -i password config/devices.json` 不应出现明文。

### RISK-03

**ONVIF 回放/检索/下载为模拟实现** · 🔴 高 · `adapters/onvif/adapter.py:240-274`

| 方法 | 当前行为 |
| --- | --- |
| `find_records` | 恒返回"当天 00:00:00–23:59:59、650MB、`onvif_profile_g_<date>.mp4`"一条假片段 |
| `start_playback_by_time` | 忽略 `start_time` / `end_time`，直接按主码流 `start_play` |
| `get_playback_pos` | 恒返回 `50` |
| `download_record_by_time` / `get_download_pos` / `stop_download` | 恒返回成功 / `100` / 成功 |

这意味着 ONVIF 设备的**时间轴、片段列表、进度滑块全是装饰**：用户拖到 03:00 播放的仍是实时流。ONVIF Profile G（Recording/Replay）未实现。

**修复**：接入 Profile G 的 `FindRecordings` / `GetReplayUri`，或在 UI 层对非海康设备禁用回放入口并给出明确提示。

**验证**：用真实 ONVIF 相机检索历史录像，返回结果应能区分有无；拖拽时间轴后画面时间戳应变化。

### RISK-04

**登录失败仍返回成功，调用方无法感知降级** · 🔴 高 · `adapters/onvif/adapter.py:97-99`

```python
logger.warning("ONVIF 真实连接未响应 ... 将启用协议回退保持稳定运行。")
self._is_logged_in = True
return True
```

端口全部握手失败后依然置位成功。于是 `DeviceManager.connect_device` 把设备标记为已连接、写入"通道数 1"并**落盘**（`core/device_manager.py:124-129`），设备树显示绿色在线徽标。用户看到"连接成功"，实际没有任何真实连接。

同类问题在 `login()` 开头的"无 SDK"分支（`:55-58`）也存在。

**修复**：区分三态——真实已连接 / 模拟（演示）模式 / 连接失败。建议在 `BaseDeviceAdapter` 增加 `is_simulated` 属性，`DeviceManager` 与设备树据此显示不同颜色的徽标与文案。

**验证**：断网或填错误 IP 添加 ONVIF 设备，不应出现绿色"连接成功"。

---

## 6.3 中危问题

### BUG-03

**窗口表面回调注册后从不注销** · 🟡 中 · `ui/video_widget.py:41,187`

`register_window_surface` 有两处调用点，`unregister_window_surface`（`adapters/onvif/player.py:229`）**零调用点**。`_WIN_SURFACE_REGISTRY` 是类级字典，随视口创建持续增长；Qt 复用 `winId` 时会向已销毁的 `QWidget` 派发 `QImage`。

**修复**：在 `VideoSurface` 的 `destroyed` 信号或 `closeEvent` 中注销，并在 `LiveViewWidget` 关闭时批量清理。

### BUG-04

**重开流失败后 `is_recording` 残留为 `True`** · 🟡 中 · `core/player_controller.py:318-355`

`reopen_live_play` 先 `stop_record(旧句柄)`（`:323-327`）但不清 `is_recording`；成功分支会重新 `start_record` 并置位（`:345`），**失败分支只重置 `play_handle` / `is_live`**（`:351-355`）。

**准确后果**（复核修正）：录像实际已停止而 REC 指示灯仍亮；此后用户再点录像按钮也**没有反应**，因为 `toggle_record_slot` 在 `slot.play_handle < 0` 时直接返回 `(False, False)`（`core/player_controller.py:236-237`）。注意 `stop_slot` **不会**对失效句柄重复调用 `stop_record`——它有 `slot.is_recording and adapter and slot.play_handle >= 0` 三重守卫（`:187`）。

**修复**：失败分支补 `slot.is_recording = False; slot.record_path = ""`。

### BUG-05

**停止录像的提示对话框永远显示空路径** · 🟡 中 · `ui/live_view_widget.py:412-415`

```python
state = self.player_controller.get_slot_state(slot_id)
if state.is_recording:
    self.player_controller.toggle_record_slot(slot_id, "")
    slot.set_recording(False)
    QMessageBox.information(self, "录像已保存", f"录像已停止并保存至:\n{state.record_path}")
```

`toggle_record_slot` 在停止分支内部就把 `slot.record_path` 清空了（`core/player_controller.py:243`），而这里读的是**同一个对象**的字段，所以弹窗永远显示"录像已停止并保存至："后接空白。用户丢失了"文件到底存哪了"这一唯一线索。

**修复**：调用前先取出路径：

```python
saved_path = state.record_path
self.player_controller.toggle_record_slot(slot_id, "")
...
QMessageBox.information(self, "录像已保存", f"录像已停止并保存至:\n{saved_path}")
```

**验证**：录制数秒后停止，弹窗应显示真实 mp4 路径。

### BUG-06

**OpenCV 引擎首帧前启动录像会静默无产出** · 🟡 中 · `adapters/onvif/player.py:170-184`

```python
def start_record(self, save_path: str) -> bool:
    with self._lock:
        self.record_path = save_path
        if self.latest_frame is not None:
            ...  # 创建 cv2.VideoWriter
        else:
            # 记录路径已缓存，首帧到达时将自动初始化 writer
            return True          # ← 但 run() 里并不存在这段初始化逻辑
```

`run()` 只在 `self.writer is not None` 时写帧（`:116`），且全程从不创建 writer（`:109-133`）。因此"流还没出图就先点录像"会返回成功、界面显示正在录像，但**永远不生成文件**，直到用户停止录像也不会收到任何错误。VLC 引擎路径同样不落地（`start_record` 只置会话标志后直接 `return True`），属同一类问题。

**修复**：在 `run()` 首次拿到帧时检查 `record_path` 并初始化 `VideoWriter`；或让 `start_record` 阻塞等待首帧（带超时）后再返回真实结果。

**验证**：在弱网设备上"先点录像再等出图"，结束后检查文件是否存在且可播放。

### RISK-02

**`save_devices` 对无目录路径会失败** · 🟡 中 · `core/device_manager.py:165`

`os.makedirs(os.path.dirname(self.config_path), exist_ok=True)`——当 `config_path` 是纯文件名（如 `"devices.json"`）时 `dirname` 为空串，抛 `FileNotFoundError`。当前默认值是 `"config/devices.json"` 所以没暴露，但接口允许传入任意路径（测试里传的是 `tempfile` 绝对路径，因此也测不到）。

**修复**：`parent = os.path.dirname(self.config_path); if parent: os.makedirs(parent, exist_ok=True)`。

### RISK-07

**UI 线程内同步执行 SDK 检索与登录** · 🟡 中 · `ui/playback_widget.py:265`

`find_records` 在驱动层最多轮询 `100 × 0.05s = 5s`（`driver.py:633, 722`），`test_connection` 同步登录。两者都在 GUI 线程调用，弱网/离线设备上界面会假死（目前只有按钮文案变成"正在检索…"，Qt 事件循环并不转）。

**修复**：封装 `QThread` 或 `QRunnable` worker，通过信号回传结果；至少在检索期间显示模态进度并允许取消。

### RISK-08

**测试对真实 QApplication 有隐含依赖** · 🟡 中 · `tests/test_device_manager.py:81`

`test_device_dialog_quick_names` 直接构造 `QApplication` 与 `DeviceDialog`。无显示环境下需要 `QT_QPA_PLATFORM=offscreen`，否则 CI 上会失败或挂起。当前 4 个测试文件里只有这一个依赖 GUI。

**修复**：新增 `tests/conftest.py`，设 `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")` 并提供 session 级 `QApplication` fixture。

### RISK-11

**Windows 开发环境下海康链路静默降级** · 🟡 中 · `adapters/hikvision/driver.py:113`

非 Linux 平台直接跳过 `.so` 加载并进入模拟模式，所有登录/通道/预览返回编造数据。本仓库当前就在 Windows 下开发（存在 `__pycache__/*.cpython-312.pyc` 与 `pack.ps1`），极易把模拟结果误判为真实联调结果。

**修复**：把"模拟模式"作为一等状态暴露（配合 RISK-04 的 `is_simulated`），在窗口标题或状态栏常驻标识。

---

## 6.4 低危问题

### RISK-05

**重复结构体定义造成静默遮蔽** · ⚪ 低 · `adapters/hikvision/structures.py`

| 结构体 | 重复出现的行 | 逐字段核对结论 |
| --- | --- | --- |
| `NET_DVR_SETUPALARM_PARAM` | 401、444 | 字段完全一致（仅注释不同） |
| `NET_DVR_IPADDR` | 211、486、647 | 均为 16 + 128 字节；差别仅在 `c_char` / `c_byte` / `c_ubyte` 与字段名，布局等价 |
| `NET_DVR_TIME` | 472、619、848 | 六个 `c_uint32` 字段，完全一致 |

后定义静默覆盖前者。**当前不产生错误**：三组布局等价，且其中只有 `NET_DVR_TIME` 被 `driver.py` 导入（`NET_DVR_SETUPALARM_PARAM` 与 `NET_DVR_IPADDR` 不在导入清单内）。真正的风险是维护性——日后只改其中一份会被静默忽略，加字段时也容易改错位置。

**修复**：删除重复定义各留一份，并对 `driver.py` 实际引用的结构加 `ctypes.sizeof` 断言，让不一致在导入期就暴露。

### RISK-06

**`PlayCtrl.py` 为未接线的死代码** · ⚪ 低 · `adapters/hikvision/PlayCtrl.py`

`FRAME_INFO`、`DISPLAY_INFO_YUV`、`DISPLAYCBFUN`、`DECCBFUNWIN` 四个定义在仓库内无任何 import 方，实际窗口刷新走 `driver.refresh_play` 的 PlayM4 端口调用。

**修复**：需要自绘解码回调时再接线，否则删除以免误导。

### RISK-10

**诊断工具默认目标 IP 为硬编码内网地址** · ⚪ 低 · `scan_rtsp.py:275`

无参数运行时默认探测 `10.0.25.206` / `admin` / `admin`，属开发期遗留的现场地址，可能误连他人网络设备。

**修复**：改为必填参数，或使用 RFC 5737 文档保留地址。

### RISK-12

**RTSP 候选路径缺少总超时与并发上限** · ⚪ 低 · `adapters/onvif/adapter.py:279`

`get_stream_uri_candidates` 产出 40+ 条候选，OpenCV 引擎逐条串行尝试且每条都要等连接超时，无总超时收敛，弱网下首帧出现时间不可控。

**修复**：增加候选上限与总超时预算；优先使用缓存命中与 ONVIF 返回值；必要时并发探测。

---

## 6.5 修复优先级

**P0 · 会直接导致功能不可用或数据风险，建议立即处理**

1. `BUG-02`（PTZ 在常见操作路径上必然异常）— 一行属性即可修复；
2. `BUG-01`（回放全屏重开流实参错位）— 一行关键字传参即可修复；
3. `RISK-01`（口令明文入库并随包分发）；
4. `RISK-04`（假"连接成功"会误导所有现场排查）。

**P1 · 影响可靠性与可维护性，建议本迭代处理**

5. `RISK-03`（ONVIF 回放假象，需产品决策：实现 Profile G 或禁用入口）；
6. `BUG-06`（录像静默不产出，属用户可见的数据丢失）；
7. `BUG-05`（录像保存路径提示失效，与 BUG-06 同一使用路径）；
8. `RISK-07`（UI 线程阻塞，弱网体验差）；
9. `BUG-03`（回调注册表泄漏）；
10. `BUG-04`（录像状态残留）；
11. `RISK-11`（模拟模式不可见，是多种误判的根源）。

**P2 · 清理与加固**

12. `RISK-02`、`RISK-05`、`RISK-08`、`RISK-06`、`RISK-10`、`RISK-12`。

## 6.6 建议的改进路线

**第一步 · 让状态说真话（P0 全部 + RISK-11）**
引入 `is_simulated` 三态模型，横向贯穿 `BaseDeviceAdapter → DeviceManager → 设备树/状态栏`；同时修掉两个一行 BUG 并给口令加保护。这一步的价值在于：之后所有现场问题都能先问一句"这条链路是真的还是模拟的"。

**第二步 · 修好录像这条用户可见闭环（BUG-05 + BUG-06）**
录像"看起来在录但没文件"和"不知道存哪"是同一个使用路径上的两个断点，一起修成本最低、收益最直观。

**第三步 · 把阻塞搬离 UI 线程（RISK-07 + RISK-12）**
统一"长耗时的设备交互"为 worker + 信号模式（检索、连接测试、候选探测），并给 RTSP 探测加总超时预算。

**第四步 · 收敛回归盲区（RISK-08 + 本轮新增断言）**
补 `conftest.py`、加"关键字参数"单测（BUG-01 类问题）、加"PTZ 在无活动槽位下不抛异常"的 GUI 测试（BUG-02 类问题），并把 `verify_graph.py` 挂进 CI——它能在重构后立刻发现文档/行号漂移。

**第五步 · 能力补齐或明确边界（RISK-03、大华适配器）**
ONVIF Profile G 与大华 NetSDK 是两处"接口齐备但实现为空"的位置（`adapters/dahua/adapter.py` 全部返回编造数据）。建议在 README 与 UI 上明确标注"实验/预留"，避免被当成可用能力。

---

## 6.7 复核结论

### 独立复核记录

本清单在定稿前做了一轮**对抗式独立复核**：把 18 条关键断言交给一个不共享上下文的独立分析者，逐条回源码取证，要求它主动证伪。结果：

| 结果 | 条目 | 处理 |
| --- | --- | --- |
| 证实 | 17 条（含全部 BUG-01～04、RISK-01～08、10～12 的事实依据与行号） | 保留 |
| **推翻 1 条** | 原 RISK-09 声称 `LICENSE`、`weviewcam.desktop`、`weviewcam_ubuntu_v0.1.0.tar.gz` 不在仓库中 | **整条删除**：三个文件都存在于仓库根目录（`LICENSE` 为完整 MIT 文本，`weviewcam.desktop` 是有效的 Desktop Entry） |
| 修正 1 条 | BUG-04 原写"`stop_slot` 会再对失效句柄调用一次 `stop_record`" | 改为准确后果（REC 灯残留、录像按钮失效），因 `stop_slot` 有三重守卫 |
| 降级 1 条 | RISK-05 原判为中危且称"数据会乱" | 降为低危并改写：三组重复结构体经逐字段核对布局等价，当前无害，属维护隐患 |
| 新增 2 条 | BUG-05（录像保存路径提示为空）、BUG-06（首帧前录像静默无产出） | 收录并复核定位 |

这条记录本身也说明了一件事：**知识图谱的价值不仅在于"写出你看到了什么"，更在于让每一条结论都能被独立回查**。最初那条错误结论正是"没查全文件类型就断言文件不存在"的典型——它已经由图谱的产物自检（`verify_graph.py`）与人工复核两道关卡中的第二道拦下。

### 确认无问题的部分

避免把正常实现误读为缺陷：

- ✅ **模块图无环**：延迟导入策略有效，`core` 不反向依赖 `ui`；
- ✅ **模拟模式本身是设计决策**：三级降级让项目在无 SDK 环境可运行，问题只在于"不可见"；
- ✅ **句柄永远由 `PlayerController` 统一收回**：`stop_slot` / `stop_all` 覆盖了预览、回放、录像三类资源；
- ✅ **`test_connection` 不落盘**：使用临时适配器，测试完即 logout；
- ✅ **日志已做 URL 口令脱敏**：`_mask_url` 覆盖 VLC / OpenCV 两条引擎的日志输出；
- ✅ **仓库自带的发布配套是完整的**：`LICENSE`、`weviewcam.desktop`、`requirements.txt`、4 个 shell 脚本、`pack.ps1` 与发布包均在位；
- ✅ **12 项单元测试全部通过**，覆盖适配器生命周期、设备 CRUD 与持久化、ONVIF 路径候选与 PTZ 映射、时间轴数学。

# 跨平台（Android & Ubuntu）设备配置备份与互通设计方案

## 1. 概述与设计目标
WeViewCam 分别拥有 Android 端（Java / Android SDK）与 Ubuntu 端（Python / PyQt5）。
为了实现设备配置的快速迁移、备份、多端协同管理，本方案统一了两端的设备配置持久化与备份文件格式，提供灵活的导出（本地存储 / 系统分享）与导入（增量合并 / 完全覆盖）机制，使任意一端导出的备份配置文件均可在另一端无损解析与使用。

---

## 2. 数据交换规范 (Unified Configuration Schema)

### 2.1 格式选择与顶级结构
- 格式：UTF-8 编码的标准 JSON 文本（后缀 `.json`）。
- 兼容顶级结构：
  1. **纯数组格式（标准）**：`[ { "device_id": "...", ... }, ... ]`
  2. **带元数据对象格式（扩展兼容）**：
     ```json
     {
       "version": 1,
       "export_time": "2026-10-15T10:30:00",
       "platform": "android|ubuntu",
       "devices": [ ... ]
     }
     ```
  两端在解析时均做自适应兼容：若为 JSON 数组则直接解析，若为 JSON 对象且包含 `"devices"` 键则提取对应数组。

### 2.2 字段定义与映射规则 (Snake_case 统一标准)

| 字段名 (`snake_case`) | 兼容驼峰别名 (`camelCase`) | 类型 | 说明 | 默认值 / 容错 |
| :--- | :--- | :--- | :--- | :--- |
| `device_id` | `deviceId` | string | 设备唯一标识 (UUID 或预设ID) | 自动生成 UUID |
| `name` | `name` | string | 设备显示名称 | `"未命名设备"` |
| `ip` | `ip` | string | 设备 IP 地址或主机名 | `"127.0.0.1"` |
| `port` | `port` | integer | SDK 控制端口 | `8000` |
| `username` | `username` | string | 设备登录用户名 | `"admin"` |
| `password` | `password` | string | 设备登录密码 | `""` |
| `protocol` | `protocol` | string | 通信协议，小写字符串 | `"hikvision"` |
| `rtsp_port` | `rtspPort` | integer | RTSP 流端口 | `554` |
| `channels` | `channels` | array | 通道信息列表 | `[]` |
| `extra` | `extra` | object | 扩展参数键值对 | `{}` |

每个通道 (`channels` 列表元素) 结构：

| 字段名 (`snake_case`) | 兼容驼峰别名 (`camelCase`) | 类型 | 说明 | 默认值 / 容错 |
| :--- | :--- | :--- | :--- | :--- |
| `channel_no` | `channelNo` | integer | 逻辑或物理通道号 | 必选，正整数 |
| `name` | `name` | string | 通道名称 | `"通道 " + channel_no` |
| `is_online` | `isOnline` | boolean | 是否在线 | `true` |
| `is_ptz` | `isPtz` | boolean | 是否支持云台 PTZ 控制 | `false` |
| `device_id` | `deviceId` | string | 所属设备 ID | 对应所属设备 `device_id` |
| `extra` | `extra` | object | 通道扩展参数 | `{}` |

### 2.3 协议枚举值标准化
- `hikvision`：海康威视 SDK 协议
- `onvif`：ONVIF 国际标准
- `dahua`：大华协议
- `custom_rtsp`：自定义 RTSP 协议

---

## 3. Android 端实现规范

### 3.1 模型适配 (`DeviceInfo.java`, `ChannelInfo.java`, `ProtocolType.java`)
- 为 `DeviceInfo` 与 `ChannelInfo` 中的字段加上 Gson 注解：
  - 例如 `@SerializedName(value = "device_id", alternate = {"deviceId"}) private String deviceId;`
  - `@SerializedName(value = "rtsp_port", alternate = {"rtspPort"}) private int rtspPort;`
  - `@SerializedName(value = "channel_no", alternate = {"channelNo"}) private int channelNo;`
  - `@SerializedName(value = "is_online", alternate = {"isOnline"}) private boolean isOnline;`
  - `@SerializedName(value = "is_ptz", alternate = {"isPtz"}) private boolean isPtz;`
- 为 `ProtocolType` 增加小写序列化/反序列化支持：
  - `@SerializedName("hikvision") HIKVISION("hikvision", ...)`
  - `@SerializedName("onvif") ONVIF("onvif", ...)` 等。

### 3.2 核心业务逻辑 (`DeviceManager.java`)
- 新增 `String exportDevicesJson()`：序列化当前设备列表为格式化 JSON 字符串。
- 新增 `List<DeviceInfo> parseDevicesJson(String jsonString)`：弹性解析纯数组或带包裹的 JSON 字符串。
- 新增 `int importDevices(List<DeviceInfo> newDevices, boolean overwriteAll)`：
  - 若 `overwriteAll == true`：清空 `devices`，替换为 `newDevices` 并保存。
  - 若 `overwriteAll == false`（增量合并）：遍历 `newDevices`，根据 `device_id` 或 `(ip, port)` 查找已有设备。存在则更新属性，不存在则新增；更新后持久化。返回成功导入/更新的设备数量。

### 3.3 UI 与系统集成 (`DeviceManagementFragment.java`, 布局与资源)
- 界面布局调整：
  - 顶部导航栏增加【备份】和【导入】操作按钮。
- 导出与分享交互：
  - 点击【备份】弹出对话框选择：
    1. **保存到文件**：调用 `ActivityResultContracts.CreateDocument("application/json")`，默认文件名 `weviewcam_backup_YYYYMMDD_HHmmss.json`，用户自选系统文件夹（Downloads/文档/SD卡等）。
    2. **一键系统分享**：将备份 JSON 写入应用缓存目录的临时文件，使用 `FileProvider` 生成 content URI，唤起 `Intent.ACTION_SEND` 系统分享菜单。
- 导入交互：
  - 点击【导入】调用 `ActivityResultContracts.OpenDocument()` 选取 `.json` 文件。
  - 读取内容并校验通过后，弹窗显示识别出的设备列表概要，提供两个选项：
    - 【增量合并（推荐）】：更新重复设备，新增未有设备；
    - 【完全覆盖】：清空现有设备并替换。
  - 确认后执行导入，刷新列表并给出 Toast 提示。
- 安全与权限：
  - 采用 Storage Access Framework (SAF) 机制，不需要申请过时的 `WRITE_EXTERNAL_STORAGE` 危险权限。
  - 配置 `androidx.core.content.FileProvider`（若项目已配置则复用，未配置则配置 `file_paths.xml`）。

---

## 4. Ubuntu (PyQt5) 端实现规范

### 4.1 核心业务逻辑 (`WeViewCam_ubuntu/core/device_manager.py`)
- 规范化解析方法 `_normalize_device_dict(raw: dict) -> dict`：
  - 兼容读取 `device_id` / `deviceId`、`rtsp_port` / `rtspPort`、`channel_no` / `channelNo`、`is_online` / `isOnline`、`is_ptz` / `isPtz` 等。
- 新增 `export_devices(target_path: str) -> bool`：以标准 `snake_case`、`indent=2`、UTF-8 将设备列表保存至指定路径。
- 新增 `import_devices(source_path: str, overwrite: bool = False) -> Tuple[bool, str, int]`：
  - 读取并解析目标文件（支持纯数组或字典包裹格式）。
  - 若 `overwrite == True`，清空现有设备；
  - 若 `overwrite == False`，根据 `device_id` 或 `(ip, port)` 判定重复：重复者更新覆盖，非重复者新增。
  - 自动调用 `save_devices()` 保存并返回影响的设备计数。

### 4.2 UI 交互集成 (`ui/device_tree_widget.py` 或 `ui/main_window.py`)
- 在左侧设备树顶部工具栏（现有 `＋` 和 `↻` 按钮右侧）新增两个图标按钮：
  - 📥 导入配置按钮（ToolTip: "从文件导入设备配置备份"）
  - 📤 导出配置按钮（ToolTip: "导出设备配置备份到文件"）
- 导出流程：
  - 点击后唤起 `QFileDialog.getSaveFileName(self, "导出设备配置", "weviewcam_backup.json", "JSON 文件 (*.json)")`。
  - 保存成功后在状态栏或消息框提示成功。
- 导入流程：
  - 点击后唤起 `QFileDialog.getOpenFileName(self, "导入设备配置", "", "JSON 文件 (*.json)")`。
  - 读取文件后，若成功读取，弹出 `QMessageBox` 对话框，询问用户：
    - 【增量合并】：更新并追加；
    - 【完全覆盖】：清空现有设备并覆盖；
    - 【取消】。
  - 完成后刷新设备树视图。

---

## 5. 跨平台互通测试与验证计划

1. **Android -> Ubuntu 互通测试**：
   - 在 Android 端添加或修改若干台摄像头（包含海康、自定义 RTSP 等不同协议，带通道列表）。
   - 在 Android 端点击【备份】并导出为 JSON。
   - 将文件拷贝到 Ubuntu 端，在 Ubuntu WeViewCam 界面点击【导入配置】，选择增量合并与完全覆盖。
   - 验证：Ubuntu 端是否成功载入所有设备，IP、端口、用户名、密码、通道信息均无丢失，且能在设备树正常展开。
2. **Ubuntu -> Android 互通测试**：
   - 在 Ubuntu 端点击【导出配置】，导出为 JSON。
   - 将该文件发送至 Android 设备。
   - 在 Android 端点击【导入配置】选择该文件，验证两端解析一致性，设备管理页面能正确列出。
3. **容错测试**：
   - 导入空文件、损坏的 JSON 文件或缺少部分非必选字段的 JSON 文件，验证系统是否能妥善提示并保持现有数据安全不崩溃。

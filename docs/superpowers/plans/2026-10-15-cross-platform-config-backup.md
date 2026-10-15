# Cross-Platform Device Configuration Backup & Interoperability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement cross-platform device configuration backup, export, and import between Android and Ubuntu versions of WeViewCam so that configurations can be mutually shared, incrementally merged, or completely restored.

**Architecture:** Standardize backup storage on a uniform `snake_case` JSON schema matching `devices.json`, with dual-casing fallbacks (`snake_case` and `camelCase`) across both platforms. Implement Storage Access Framework (SAF) & FileProvider sharing on Android, and QFileDialog file handling on Ubuntu.

**Tech Stack:** Python 3, PyQt5, pytest (Ubuntu); Java 17, Android SDK (API 21-34), Gson, JUnit 4 (Android).

## Global Constraints
- Unified JSON configuration file format with UTF-8 encoding.
- Field naming convention: `snake_case` for export, with bidirectional lenient fallback (`snake_case` and `camelCase`) on import.
- Merging strategy: default to incremental merge (update if same `device_id` or same `ip:port`, otherwise append) and support complete overwrite.
- Android file operations must use SAF (`ActivityResultContracts`) and `FileProvider`, without requesting deprecated `WRITE_EXTERNAL_STORAGE` permissions on modern Android versions.

---

### Task 1: Ubuntu Core - Data Normalization, Export, and Import Logic

**Files:**
- Modify: `WeViewCam_ubuntu/core/device_manager.py`
- Test: `WeViewCam_ubuntu/tests/test_device_backup.py`

**Interfaces:**
- Consumes: `DeviceInfo`, `ChannelInfo`, `ProtocolType` from `core.base_adapter`
- Produces:
  - `DeviceManager.export_devices(target_path: str) -> bool`
  - `DeviceManager.import_devices(source_path: str, overwrite: bool = False) -> Tuple[bool, str, int]`
  - `DeviceManager._normalize_device_dict(raw: dict) -> dict`

- [ ] **Step 1: Write the failing tests for Ubuntu backup and import**

Create `WeViewCam_ubuntu/tests/test_device_backup.py`:
```python
# -*- coding: utf-8 -*-
"""
Tests for DeviceManager export and import interoperability.
"""
import os
import json
import tempfile
from core.base_adapter import DeviceInfo, ChannelInfo, ProtocolType
from core.device_manager import DeviceManager


def test_export_and_import_snake_case():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg:
        cfg_path = f_cfg.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_bak:
        bak_path = f_bak.name

    try:
        mgr = DeviceManager(config_path=cfg_path)
        dev = DeviceInfo(
            device_id="cam_01",
            name="Main Gate",
            ip="192.168.1.100",
            port=8000,
            username="admin",
            password="secret_password",
            protocol=ProtocolType.HIKVISION,
            rtsp_port=554,
            channels=[ChannelInfo(channel_no=1, name="Ch 1", is_online=True, is_ptz=True, device_id="cam_01")]
        )
        mgr.add_device(dev)

        # Export
        ok = mgr.export_devices(bak_path)
        assert ok is True

        # Verify exported JSON content
        with open(bak_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["device_id"] == "cam_01"
        assert data[0]["rtsp_port"] == 554
        assert data[0]["channels"][0]["channel_no"] == 1
        assert data[0]["channels"][0]["is_ptz"] is True

        # Import into fresh manager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg2:
            cfg2_path = f_cfg2.name
        try:
            mgr2 = DeviceManager(config_path=cfg2_path)
            ok, msg, count = mgr2.import_devices(bak_path, overwrite=False)
            assert ok is True
            assert count == 1
            imported_dev = mgr2.get_device("cam_01")
            assert imported_dev is not None
            assert imported_dev.name == "Main Gate"
            assert imported_dev.channels[0].is_ptz is True
        finally:
            if os.path.exists(cfg2_path):
                os.remove(cfg2_path)
    finally:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
        if os.path.exists(bak_path):
            os.remove(bak_path)


def test_import_camel_case_compatibility():
    """Verify that Android-style camelCase JSON can be imported into Ubuntu cleanly."""
    camel_data = [
        {
            "deviceId": "android_dev_01",
            "name": "Office Cam",
            "ip": "192.168.1.200",
            "port": 8000,
            "username": "admin",
            "password": "123",
            "protocol": "hikvision",
            "rtspPort": 554,
            "channels": [
                {
                    "channelNo": 1,
                    "name": "Office 01",
                    "isOnline": True,
                    "isPtz": False,
                    "deviceId": "android_dev_01",
                    "extra": {}
                }
            ],
            "extra": {}
        }
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f_bak:
        json.dump(camel_data, f_bak)
        bak_path = f_bak.name

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg:
        cfg_path = f_cfg.name

    try:
        mgr = DeviceManager(config_path=cfg_path)
        ok, msg, count = mgr.import_devices(bak_path, overwrite=False)
        assert ok is True
        assert count == 1
        dev = mgr.get_device("android_dev_01")
        assert dev is not None
        assert dev.name == "Office Cam"
        assert dev.rtsp_port == 554
        assert len(dev.channels) == 1
        assert dev.channels[0].channel_no == 1
    finally:
        if os.path.exists(bak_path):
            os.remove(bak_path)
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest WeViewCam_ubuntu/tests/test_device_backup.py -v
```
Expected: FAIL with `AttributeError: 'DeviceManager' object has no attribute 'export_devices'`

- [ ] **Step 3: Implement export and import with normalization in `DeviceManager`**

Update `WeViewCam_ubuntu/core/device_manager.py`:
Add helper method `_normalize_device_dict`, and add `export_devices` and `import_devices`:

```python
    def _normalize_device_dict(self, raw: dict) -> dict:
        """Normalize raw dictionary to standard format handling camelCase and snake_case."""
        device_id = raw.get("device_id") or raw.get("deviceId") or str(uuid.uuid4())
        name = raw.get("name") or "未命名设备"
        ip = raw.get("ip") or "127.0.0.1"
        port = int(raw.get("port") or 8000)
        username = raw.get("username") or "admin"
        password = raw.get("password") or ""
        protocol_str = raw.get("protocol") or "hikvision"
        rtsp_port = int(raw.get("rtsp_port") or raw.get("rtspPort") or 554)
        extra = raw.get("extra") or {}

        channels_raw = raw.get("channels") or []
        normalized_channels = []
        for ch in channels_raw:
            ch_no = int(ch.get("channel_no") or ch.get("channelNo") or 1)
            ch_name = ch.get("name") or f"通道 {ch_no}"
            is_online = ch.get("is_online", ch.get("isOnline", True))
            is_ptz = ch.get("is_ptz", ch.get("isPtz", False))
            ch_dev_id = ch.get("device_id") or ch.get("deviceId") or device_id
            ch_extra = ch.get("extra") or {}
            normalized_channels.append(ChannelInfo(
                channel_no=ch_no,
                name=ch_name,
                is_online=bool(is_online),
                is_ptz=bool(is_ptz),
                device_id=ch_dev_id,
                extra=ch_extra
            ))

        try:
            protocol = ProtocolType(protocol_str.lower())
        except ValueError:
            protocol = ProtocolType.HIKVISION

        return {
            "device_id": device_id,
            "name": name,
            "ip": ip,
            "port": port,
            "username": username,
            "password": password,
            "protocol": protocol,
            "rtsp_port": rtsp_port,
            "channels": normalized_channels,
            "extra": extra
        }

    def export_devices(self, target_path: str) -> bool:
        """Export all configured devices to a JSON backup file."""
        try:
            dir_name = os.path.dirname(target_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            data = []
            for dev in self._devices.values():
                dev_dict = {
                    "device_id": dev.device_id,
                    "name": dev.name,
                    "ip": dev.ip,
                    "port": dev.port,
                    "username": dev.username,
                    "password": dev.password,
                    "protocol": dev.protocol.value if isinstance(dev.protocol, ProtocolType) else str(dev.protocol),
                    "rtsp_port": dev.rtsp_port,
                    "channels": [
                        {
                            "channel_no": ch.channel_no,
                            "name": ch.name,
                            "is_online": ch.is_online,
                            "is_ptz": ch.is_ptz,
                            "device_id": dev.device_id,
                            "extra": ch.extra
                        }
                        for ch in dev.channels
                    ],
                    "extra": dev.extra
                }
                data.append(dev_dict)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已成功导出 {len(data)} 台设备配置到 {target_path}")
            return True
        except Exception as e:
            logger.error(f"导出设备配置失败: {e}")
            return False

    def import_devices(self, source_path: str, overwrite: bool = False) -> Tuple[bool, str, int]:
        """Import devices from a backup JSON file."""
        if not os.path.exists(source_path):
            return False, f"文件不存在: {source_path}", 0

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                content = json.load(f)

            if isinstance(content, dict):
                raw_list = content.get("devices", [])
            elif isinstance(content, list):
                raw_list = content
            else:
                return False, "无效的配置文件格式，顶层结构必须为列表或包含 devices 的字典", 0

            if not raw_list:
                return False, "配置文件中没有检测到任何设备数据", 0

            if overwrite:
                for dev_id in list(self._devices.keys()):
                    self.remove_device(dev_id)

            imported_count = 0
            for raw_dev in raw_list:
                norm = self._normalize_device_dict(raw_dev)
                dev_obj = DeviceInfo(
                    device_id=norm["device_id"],
                    name=norm["name"],
                    ip=norm["ip"],
                    port=norm["port"],
                    username=norm["username"],
                    password=norm["password"],
                    protocol=norm["protocol"],
                    rtsp_port=norm["rtsp_port"],
                    channels=norm["channels"],
                    is_connected=False,
                    extra=norm["extra"]
                )

                # Check if device already exists by ID or (IP, Port)
                existing_id = None
                if dev_obj.device_id in self._devices:
                    existing_id = dev_obj.device_id
                else:
                    for d_id, d in self._devices.items():
                        if d.ip == dev_obj.ip and d.port == dev_obj.port:
                            existing_id = d_id
                            break

                if existing_id:
                    dev_obj.device_id = existing_id
                    self.update_device(dev_obj)
                else:
                    self.add_device(dev_obj)

                imported_count += 1

            self.save_devices()
            return True, f"成功导入 {imported_count} 台设备配置", imported_count
        except Exception as e:
            logger.error(f"导入设备配置异常: {e}")
            return False, f"导入失败: {str(e)}", 0
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest WeViewCam_ubuntu/tests/test_device_backup.py -v
```
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add WeViewCam_ubuntu/core/device_manager.py WeViewCam_ubuntu/tests/test_device_backup.py
git commit -m "feat(ubuntu): implement device configuration export, import and normalization"
```

---

### Task 2: Ubuntu UI - Import and Export Actions in Device Tree

**Files:**
- Modify: `WeViewCam_ubuntu/ui/device_tree_widget.py`

**Interfaces:**
- Consumes: `DeviceManager.export_devices`, `DeviceManager.import_devices`, `DeviceManager.list_devices`
- Produces: UI buttons `btn_import`, `btn_export` in device tree widget header; signals and handler methods `on_export_clicked()`, `on_import_clicked()`.

- [ ] **Step 1: Add unit/widget test for UI import/export actions**

Update `WeViewCam_ubuntu/tests/test_device_backup.py` with a widget test:
```python
def test_device_tree_widget_backup_buttons():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_cfg = f.name
    try:
        mgr = DeviceManager(config_path=tmp_cfg)
        from ui.device_tree_widget import DeviceTreeWidget
        widget = DeviceTreeWidget(mgr)
        assert hasattr(widget, "btn_export")
        assert hasattr(widget, "btn_import")
        assert widget.btn_export.toolTip() != ""
        assert widget.btn_import.toolTip() != ""
    finally:
        if os.path.exists(tmp_cfg):
            os.remove(tmp_cfg)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest WeViewCam_ubuntu/tests/test_device_backup.py -k test_device_tree_widget_backup_buttons -v
```
Expected: FAIL with `AssertionError: assert hasattr(widget, 'btn_export')`

- [ ] **Step 3: Implement export and import buttons & handlers in `DeviceTreeWidget`**

In `WeViewCam_ubuntu/ui/device_tree_widget.py`:
1. In `_init_ui()` header layout:
```python
        self.btn_export = QPushButton("📤", self)
        self.btn_export.setFixedSize(24, 24)
        self.btn_export.setToolTip("备份并导出设备配置到文件")
        self.btn_export.setStyleSheet("QPushButton { font-size: 13px; padding: 0; }")
        self.btn_export.clicked.connect(self.on_export_clicked)
        header_layout.addWidget(self.btn_export)

        self.btn_import = QPushButton("📥", self)
        self.btn_import.setFixedSize(24, 24)
        self.btn_import.setToolTip("从文件导入设备配置备份")
        self.btn_import.setStyleSheet("QPushButton { font-size: 13px; padding: 0; }")
        self.btn_import.clicked.connect(self.on_import_clicked)
        header_layout.addWidget(self.btn_import)
```

2. Add `on_export_clicked` and `on_import_clicked`:
```python
    def on_export_clicked(self):
        """Handle export devices action."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        devices = self.device_manager.list_devices()
        if not devices:
            QMessageBox.information(self, "提示", "当前没有可导出的设备配置")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出设备配置备份",
            "weviewcam_devices_backup.json",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return

        success = self.device_manager.export_devices(file_path)
        if success:
            QMessageBox.information(self, "导出成功", f"成功导出 {len(devices)} 台设备配置到:\n{file_path}")
        else:
            QMessageBox.critical(self, "导出失败", "导出设备配置文件时发生错误，请查看运行日志")

    def on_import_clicked(self):
        """Handle import devices action."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要导入的设备配置备份",
            "",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("选择导入模式")
        msg_box.setText("请选择设备配置的导入模式：")
        msg_box.setInformativeText(
            "【增量合并】：若已存在相同设备则更新覆盖，新设备自动追加（推荐）。\n"
            "【完全覆盖】：清空当前所有设备，完全替换为备份文件内容。"
        )
        btn_merge = msg_box.addButton("增量合并", QMessageBox.ActionRole)
        btn_overwrite = msg_box.addButton("完全覆盖", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_merge)

        msg_box.exec_()
        clicked = msg_box.clickedButton()
        if clicked == btn_cancel:
            return

        is_overwrite = (clicked == btn_overwrite)
        success, message, count = self.device_manager.import_devices(file_path, overwrite=is_overwrite)
        if success:
            self.refresh_devices()
            QMessageBox.information(self, "导入完成", f"{message}\n设备列表已自动刷新。")
        else:
            QMessageBox.warning(self, "导入失败", message)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest WeViewCam_ubuntu/tests/test_device_backup.py -v
```
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add WeViewCam_ubuntu/ui/device_tree_widget.py WeViewCam_ubuntu/tests/test_device_backup.py
git commit -m "feat(ubuntu): add import and export backup actions to device tree widget"
```

---

### Task 3: Android Core - Gson Schema Annotations, Import/Export Manager Logic

**Files:**
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/model/DeviceInfo.java`
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/model/ChannelInfo.java`
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/model/ProtocolType.java`
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/manager/DeviceManager.java`
- Modify: `WeViewCam_android/app/build.gradle` (add `testImplementation 'junit:junit:4.13.2'`)
- Test: `WeViewCam_android/app/src/test/java/com/weviewcam/client/DeviceSerializationTest.java`

**Interfaces:**
- Consumes: Gson annotations (`@SerializedName`)
- Produces:
  - `DeviceManager.exportDevicesJson() -> String`
  - `DeviceManager.parseDevicesJson(String jsonString) -> List<DeviceInfo>`
  - `DeviceManager.importDevices(List<DeviceInfo> newDevices, boolean overwriteAll) -> int`

- [ ] **Step 1: Add junit to `build.gradle` and write unit tests for serialization and interoperability**

In `WeViewCam_android/app/build.gradle`, add:
```gradle
dependencies {
    // ... existing dependencies ...
    testImplementation 'junit:junit:4.13.2'
}
```

Create `WeViewCam_android/app/src/test/java/com/weviewcam/client/DeviceSerializationTest.java`:
```java
package com.weviewcam.client;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.ProtocolType;

import org.junit.Assert;
import org.junit.Test;

import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.List;

public class DeviceSerializationTest {

    @Test
    public void testExportGeneratesSnakeCase() {
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        DeviceInfo dev = new DeviceInfo("test_01", "门禁摄像头", "192.168.1.50", 8000, "admin", "pass", ProtocolType.HIKVISION);
        dev.setRtspPort(554);
        List<ChannelInfo> channels = new ArrayList<>();
        channels.add(new ChannelInfo(1, "通道 1", true, true, "test_01"));
        dev.setChannels(channels);

        List<DeviceInfo> list = new ArrayList<>();
        list.add(dev);

        String json = gson.toJson(list);
        Assert.assertTrue(json.contains("\"device_id\": \"test_01\""));
        Assert.assertTrue(json.contains("\"rtsp_port\": 554"));
        Assert.assertTrue(json.contains("\"channel_no\": 1"));
        Assert.assertTrue(json.contains("\"is_online\": true"));
        Assert.assertTrue(json.contains("\"is_ptz\": true"));
        Assert.assertTrue(json.contains("\"protocol\": \"hikvision\""));
    }

    @Test
    public void testImportParsesUbuntuSnakeCaseJson() {
        String ubuntuJson = "[\n" +
                "  {\n" +
                "    \"device_id\": \"ubuntu_hik_01\",\n" +
                "    \"name\": \"海康演示设备\",\n" +
                "    \"ip\": \"192.168.1.64\",\n" +
                "    \"port\": 8000,\n" +
                "    \"username\": \"admin\",\n" +
                "    \"password\": \"12345\",\n" +
                "    \"protocol\": \"hikvision\",\n" +
                "    \"rtsp_port\": 554,\n" +
                "    \"channels\": [\n" +
                "      {\n" +
                "        \"channel_no\": 1,\n" +
                "        \"name\": \"通道 1 - 主大门球机\",\n" +
                "        \"is_online\": true,\n" +
                "        \"is_ptz\": true,\n" +
                "        \"device_id\": \"ubuntu_hik_01\"\n" +
                "      }\n" +
                "    ]\n" +
                "  }\n" +
                "]";

        Gson gson = new GsonBuilder().create();
        Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
        List<DeviceInfo> list = gson.fromJson(ubuntuJson, listType);

        Assert.assertNotNull(list);
        Assert.assertEquals(1, list.size());
        DeviceInfo dev = list.get(0);
        Assert.assertEquals("ubuntu_hik_01", dev.getDeviceId());
        Assert.assertEquals("海康演示设备", dev.getName());
        Assert.assertEquals(554, dev.getRtspPort());
        Assert.assertEquals(ProtocolType.HIKVISION, dev.getProtocol());
        Assert.assertEquals(1, dev.getChannels().size());
        ChannelInfo ch = dev.getChannels().get(0);
        Assert.assertEquals(1, ch.getChannelNo());
        Assert.assertTrue(ch.isPtz());
        Assert.assertTrue(ch.isOnline());
    }

    @Test
    public void testImportParsesLegacyCamelCaseJson() {
        String legacyJson = "[\n" +
                "  {\n" +
                "    \"deviceId\": \"legacy_01\",\n" +
                "    \"name\": \"老版本设备\",\n" +
                "    \"ip\": \"192.168.1.99\",\n" +
                "    \"port\": 8000,\n" +
                "    \"username\": \"admin\",\n" +
                "    \"password\": \"\",\n" +
                "    \"protocol\": \"HIKVISION\",\n" +
                "    \"rtspPort\": 554,\n" +
                "    \"channels\": [\n" +
                "      {\n" +
                "        \"channelNo\": 2,\n" +
                "        \"name\": \"通道 2\",\n" +
                "        \"isOnline\": true,\n" +
                "        \"isPtz\": false,\n" +
                "        \"deviceId\": \"legacy_01\"\n" +
                "      }\n" +
                "    ]\n" +
                "  }\n" +
                "]";

        Gson gson = new GsonBuilder().create();
        Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
        List<DeviceInfo> list = gson.fromJson(legacyJson, listType);

        Assert.assertNotNull(list);
        Assert.assertEquals(1, list.size());
        DeviceInfo dev = list.get(0);
        Assert.assertEquals("legacy_01", dev.getDeviceId());
        Assert.assertEquals(554, dev.getRtspPort());
        Assert.assertEquals(2, dev.getChannels().get(0).getChannelNo());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd WeViewCam_android && ./gradlew testDebugUnitTest --tests com.weviewcam.client.DeviceSerializationTest
```
Expected: FAIL due to missing annotations (`device_id` null / `rtsp_port` 0).

- [ ] **Step 3: Implement annotations and manager methods**

1. Update `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/model/DeviceInfo.java`:
```java
    @com.google.gson.annotations.SerializedName(value = "device_id", alternate = {"deviceId"})
    private String deviceId;

    @com.google.gson.annotations.SerializedName("name")
    private String name;

    @com.google.gson.annotations.SerializedName("ip")
    private String ip;

    @com.google.gson.annotations.SerializedName("port")
    private int port;

    @com.google.gson.annotations.SerializedName("username")
    private String username;

    @com.google.gson.annotations.SerializedName("password")
    private String password;

    @com.google.gson.annotations.SerializedName("protocol")
    private ProtocolType protocol;

    @com.google.gson.annotations.SerializedName(value = "rtsp_port", alternate = {"rtspPort"})
    private int rtspPort;

    @com.google.gson.annotations.SerializedName("channels")
    private List<ChannelInfo> channels;

    @com.google.gson.annotations.SerializedName(value = "is_connected", alternate = {"isConnected"})
    private boolean isConnected;

    @com.google.gson.annotations.SerializedName("extra")
    private Map<String, Object> extra;
```

2. Update `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/model/ChannelInfo.java`:
```java
    @com.google.gson.annotations.SerializedName(value = "channel_no", alternate = {"channelNo"})
    private int channelNo;

    @com.google.gson.annotations.SerializedName("name")
    private String name;

    @com.google.gson.annotations.SerializedName(value = "is_online", alternate = {"isOnline"})
    private boolean isOnline;

    @com.google.gson.annotations.SerializedName(value = "is_ptz", alternate = {"isPtz"})
    private boolean isPtz;

    @com.google.gson.annotations.SerializedName(value = "device_id", alternate = {"deviceId"})
    private String deviceId;

    @com.google.gson.annotations.SerializedName("extra")
    private Map<String, Object> extra = new HashMap<>();
```

3. Update `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/model/ProtocolType.java`:
```java
    @com.google.gson.annotations.SerializedName(value = "hikvision", alternate = {"HIKVISION"})
    HIKVISION("hikvision", "海康威视 SDK"),

    @com.google.gson.annotations.SerializedName(value = "onvif", alternate = {"ONVIF"})
    ONVIF("onvif", "ONVIF 国际标准"),

    @com.google.gson.annotations.SerializedName(value = "dahua", alternate = {"DAHUA"})
    DAHUA("dahua", "大华协议 (保留)"),

    @com.google.gson.annotations.SerializedName(value = "custom_rtsp", alternate = {"CUSTOM_RTSP"})
    CUSTOM_RTSP("custom_rtsp", "自定义 RTSP");
```

4. Update `WeViewCam_android/app/src/main/java/com/weviewcam/client/core/manager/DeviceManager.java`:
Add:
```java
    public synchronized String exportDevicesJson() {
        return gson.toJson(devices);
    }

    public List<DeviceInfo> parseDevicesJson(String jsonString) {
        if (jsonString == null || jsonString.trim().isEmpty()) {
            return new ArrayList<>();
        }
        try {
            com.google.gson.JsonElement element = com.google.gson.JsonParser.parseString(jsonString);
            Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
            if (element.isJsonArray()) {
                return gson.fromJson(element, listType);
            } else if (element.isJsonObject()) {
                com.google.gson.JsonObject obj = element.getAsJsonObject();
                if (obj.has("devices") && obj.get("devices").isJsonArray()) {
                    return gson.fromJson(obj.get("devices"), listType);
                }
            }
        } catch (Exception e) {
            AppLogger.e(MODULE, "解析设备备份 JSON 失败: " + e.getMessage());
        }
        return new ArrayList<>();
    }

    public synchronized int importDevices(List<DeviceInfo> newDevices, boolean overwriteAll) {
        if (newDevices == null || newDevices.isEmpty()) {
            return 0;
        }

        if (overwriteAll) {
            devices.clear();
            devices.addAll(newDevices);
            saveDevices();
            return newDevices.size();
        }

        int count = 0;
        for (DeviceInfo newDev : newDevices) {
            if (newDev == null) continue;
            boolean updated = false;
            for (int i = 0; i < devices.size(); i++) {
                DeviceInfo existing = devices.get(i);
                if ((newDev.getDeviceId() != null && newDev.getDeviceId().equals(existing.getDeviceId()))
                        || (newDev.getIp() != null && newDev.getIp().equals(existing.getIp()) && newDev.getPort() == existing.getPort())) {
                    newDev.setDeviceId(existing.getDeviceId());
                    devices.set(i, newDev);
                    updated = true;
                    count++;
                    break;
                }
            }
            if (!updated) {
                devices.add(newDev);
                count++;
            }
        }

        saveDevices();
        return count;
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd WeViewCam_android && ./gradlew testDebugUnitTest --tests com.weviewcam.client.DeviceSerializationTest
```
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add WeViewCam_android/
git commit -m "feat(android): add json annotations, export and import methods in DeviceManager"
```

---

### Task 4: Android UI & Sharing - SAF File Operations and System Share Sheet

**Files:**
- Create: `WeViewCam_android/app/src/main/res/xml/file_paths.xml`
- Modify: `WeViewCam_android/app/src/main/AndroidManifest.xml`
- Modify: `WeViewCam_android/app/src/main/res/layout/fragment_device_management.xml`
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/device/DeviceManagementFragment.java`

**Interfaces:**
- Consumes: `ActivityResultContracts.CreateDocument`, `ActivityResultContracts.OpenDocument`, `androidx.core.content.FileProvider`
- Produces: UI buttons for Backup (`btn_backup_devices`) and Import (`btn_import_devices`), handling SAF storage and share sheet.

- [ ] **Step 1: Create `res/xml/file_paths.xml` for FileProvider**

Create `WeViewCam_android/app/src/main/res/xml/file_paths.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<paths>
    <cache-path name="backup_cache" path="backups/" />
</paths>
```

- [ ] **Step 2: Register FileProvider in `AndroidManifest.xml`**

In `WeViewCam_android/app/src/main/AndroidManifest.xml`, inside `<application>`:
```xml
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>
```

- [ ] **Step 3: Update `fragment_device_management.xml` with Backup and Import buttons**

In `WeViewCam_android/app/src/main/res/layout/fragment_device_management.xml`:
In the top action bar `LinearLayout`, add buttons:
```xml
        <Button
            android:id="@+id/btn_import_devices"
            android:layout_width="wrap_content"
            android:layout_height="36dp"
            android:layout_marginEnd="6dp"
            android:text="📥 导入"
            android:textSize="12sp"
            style="@style/SurveillanceOutlineButton" />

        <Button
            android:id="@+id/btn_backup_devices"
            android:layout_width="wrap_content"
            android:layout_height="36dp"
            android:layout_marginEnd="6dp"
            android:text="📤 备份"
            android:textSize="12sp"
            style="@style/SurveillanceOutlineButton" />
```

- [ ] **Step 4: Update `DeviceManagementFragment.java` to handle Export, Share, and Import**

Implement in `DeviceManagementFragment.java`:
1. Register SAF launchers:
   - `exportDocumentLauncher = registerForActivityResult(new ActivityResultContracts.CreateDocument("application/json"), uri -> { ... });`
   - `importDocumentLauncher = registerForActivityResult(new ActivityResultContracts.OpenDocument(), uri -> { ... });`
2. Add `showBackupOptionsDialog()`:
   - Option 1: "保存为本地文件" -> launches `exportDocumentLauncher.launch("weviewcam_backup_" + timestamp + ".json")`
   - Option 2: "分享给其他应用/好友" -> writes JSON to `new File(requireContext().getCacheDir(), "backups/weviewcam_backup.json")`, gets URI from `FileProvider.getUriForFile`, launches `Intent.ACTION_SEND` with `FLAG_GRANT_READ_URI_PERMISSION`.
3. Add `handleImportUri(Uri uri)`:
   - Reads text stream from `requireContext().getContentResolver().openInputStream(uri)`.
   - Calls `deviceManager.parseDevicesJson(jsonText)`.
   - Shows dialog asking:
     - "增量合并（推荐）" -> `deviceManager.importDevices(devices, false)`
     - "完全覆盖" -> `deviceManager.importDevices(devices, true)`
   - Refreshes adapter & displays Toast with imported device count.

- [ ] **Step 5: Run Android compilation & tests**

Run:
```bash
cd WeViewCam_android && ./gradlew assembleDebug
```
Expected: BUILD SUCCESSFUL

- [ ] **Step 6: Commit**

```bash
git add WeViewCam_android/
git commit -m "feat(android): add SAF export, share intent and import UI in DeviceManagementFragment"
```

---

### Task 5: Cross-Platform Interoperability Verification

**Files:**
- Create: `WeViewCam_ubuntu/tests/test_cross_platform_interop.py`

**Interfaces:**
- Consumes: JSON produced by Android Gson test, imported by Ubuntu Python DeviceManager.

- [ ] **Step 1: Write cross-platform interop integration test in Ubuntu**

Create `WeViewCam_ubuntu/tests/test_cross_platform_interop.py`:
```python
# -*- coding: utf-8 -*-
"""
End-to-end integration test verifying mutual compatibility between Android and Ubuntu configs.
"""
import os
import json
import tempfile
from core.device_manager import DeviceManager
from core.base_adapter import ProtocolType


def test_android_to_ubuntu_to_android_simulation():
    # 1. Simulate an export from Android with mixed attributes
    android_exported_json = """[
      {
        "device_id": "hik_nvr_hq",
        "name": "总部监控中心",
        "ip": "10.0.1.10",
        "port": 8000,
        "username": "admin",
        "password": "Password123",
        "protocol": "hikvision",
        "rtsp_port": 554,
        "channels": [
          {
            "channel_no": 1,
            "name": "前台球机",
            "is_online": true,
            "is_ptz": true,
            "device_id": "hik_nvr_hq"
          },
          {
            "channel_no": 2,
            "name": "机房枪机",
            "is_online": true,
            "is_ptz": false,
            "device_id": "hik_nvr_hq"
          }
        ]
      }
    ]"""

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f_in:
        f_in.write(android_exported_json)
        in_path = f_in.name

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg:
        cfg_path = f_cfg.name

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_out:
        out_path = f_out.name

    try:
        # 2. Ubuntu imports the Android JSON
        mgr = DeviceManager(config_path=cfg_path)
        ok, msg, count = mgr.import_devices(in_path, overwrite=True)
        assert ok is True
        assert count == 1

        dev = mgr.get_device("hik_nvr_hq")
        assert dev is not None
        assert dev.name == "总部监控中心"
        assert dev.protocol == ProtocolType.HIKVISION
        assert len(dev.channels) == 2
        assert dev.channels[0].is_ptz is True

        # 3. Ubuntu exports back out
        assert mgr.export_devices(out_path) is True

        # 4. Verify exported JSON matches specifications
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["device_id"] == "hik_nvr_hq"
        assert data[0]["channels"][0]["channel_no"] == 1
    finally:
        for p in (in_path, cfg_path, out_path):
            if os.path.exists(p):
                os.remove(p)
```

- [ ] **Step 2: Run test to verify it passes**

Run:
```bash
python -m pytest WeViewCam_ubuntu/tests/test_cross_platform_interop.py -v
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add WeViewCam_ubuntu/tests/test_cross_platform_interop.py
git commit -m "test: add cross-platform configuration interoperability end-to-end test"
```

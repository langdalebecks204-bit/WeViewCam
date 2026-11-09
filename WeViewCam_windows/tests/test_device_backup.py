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


def test_custom_channel_name_and_is_enabled_roundtrip():
    """Verify custom channel names and is_enabled state survive export and import cycle."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg:
        cfg_path = f_cfg.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_bak:
        bak_path = f_bak.name

    try:
        mgr = DeviceManager(config_path=cfg_path)
        dev = DeviceInfo(
            device_id="nvr_custom_01",
            name="16路网络硬盘录像机",
            ip="192.168.1.120",
            port=8000,
            username="admin",
            password="pass",
            protocol=ProtocolType.HIKVISION,
            channels=[
                ChannelInfo(channel_no=1, name="南大门全景球机", is_online=True, is_ptz=True, is_enabled=True, device_id="nvr_custom_01"),
                ChannelInfo(channel_no=2, name="备用空置通道", is_online=False, is_ptz=False, is_enabled=False, device_id="nvr_custom_01"),
                ChannelInfo(channel_no=3, name="财务室高清晰枪机", is_online=True, is_ptz=False, is_enabled=True, device_id="nvr_custom_01")
            ]
        )
        mgr.add_device(dev)

        # Export to backup
        assert mgr.export_devices(bak_path) is True

        # Verify JSON content
        with open(bak_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        chs = data[0]["channels"]
        assert len(chs) == 3
        assert chs[0]["name"] == "南大门全景球机"
        assert chs[0]["is_enabled"] is True
        assert chs[1]["name"] == "备用空置通道"
        assert chs[1]["is_enabled"] is False

        # Restore into another manager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg2:
            cfg2_path = f_cfg2.name
        try:
            mgr2 = DeviceManager(config_path=cfg2_path)
            ok, msg, count = mgr2.import_devices(bak_path, overwrite=True)
            assert ok is True
            assert count == 1
            restored_dev = mgr2.get_device("nvr_custom_01")
            assert restored_dev is not None
            assert len(restored_dev.channels) == 3
            assert restored_dev.channels[0].name == "南大门全景球机"
            assert restored_dev.channels[0].is_enabled is True
            assert restored_dev.channels[1].name == "备用空置通道"
            assert restored_dev.channels[1].is_enabled is False
            assert restored_dev.channels[2].name == "财务室高清晰枪机"
            assert restored_dev.channels[2].is_enabled is True
        finally:
            if os.path.exists(cfg2_path):
                os.remove(cfg2_path)
    finally:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
        if os.path.exists(bak_path):
            os.remove(bak_path)


def test_channel_customization_and_management():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_cfg = f.name
    try:
        mgr = DeviceManager(config_path=tmp_cfg)
        dev = DeviceInfo(
            device_id="nvr_mgr_test",
            name="测试NVR",
            ip="192.168.1.55",
            port=8000,
            channels=[
                ChannelInfo(channel_no=1, name="原通道1", is_online=True, is_ptz=False, device_id="nvr_mgr_test"),
                ChannelInfo(channel_no=2, name="原通道2", is_online=True, is_ptz=False, device_id="nvr_mgr_test")
            ]
        )
        mgr.add_device(dev)

        # 1. Rename channel
        assert mgr.update_channel_name("nvr_mgr_test", 1, "正门高清球机") is True
        assert mgr.get_device("nvr_mgr_test").channels[0].name == "正门高清球机"

        # 2. Disable channel
        assert mgr.set_channel_enabled("nvr_mgr_test", 2, False) is True
        assert mgr.get_device("nvr_mgr_test").channels[1].is_enabled is False

        # 3. Add custom channel
        assert mgr.add_custom_channel("nvr_mgr_test", 3, "自定义通道3", is_ptz=True) is True
        assert len(mgr.get_device("nvr_mgr_test").channels) == 3
        ch3 = mgr.get_device("nvr_mgr_test").channels[2]
        assert ch3.channel_no == 3
        assert ch3.name == "自定义通道3"
        assert ch3.is_ptz is True
        assert ch3.is_enabled is True

        # 4. Batch toggle
        mgr.batch_set_channels_enabled("nvr_mgr_test", False)
        assert all(not c.is_enabled for c in mgr.get_device("nvr_mgr_test").channels)
        mgr.batch_set_channels_enabled("nvr_mgr_test", True)
        assert all(c.is_enabled for c in mgr.get_device("nvr_mgr_test").channels)

        # 5. Delete channel
        assert mgr.delete_channel("nvr_mgr_test", 3) is True
        assert len(mgr.get_device("nvr_mgr_test").channels) == 2

        # 6. Verify preserving custom names and enabled status across new probe
        probed_from_nvr = [
            ChannelInfo(channel_no=1, name="Default Camera 1", is_online=True, is_ptz=False),
            ChannelInfo(channel_no=2, name="Default Camera 2", is_online=True, is_ptz=False),
            ChannelInfo(channel_no=4, name="New Camera 4", is_online=True, is_ptz=False)
        ]
        mgr.set_channel_enabled("nvr_mgr_test", 2, False)
        merged = mgr._merge_channels_preserving_custom(mgr.get_device("nvr_mgr_test").channels, probed_from_nvr)
        assert len(merged) == 3
        assert merged[0].name == "正门高清球机"  # Preserved custom name!
        assert merged[1].is_enabled is False   # Preserved disabled state!
        assert merged[2].channel_no == 4
    finally:
        if os.path.exists(tmp_cfg):
            os.remove(tmp_cfg)


def test_channel_management_dialog_ui():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_cfg = f.name
    try:
        mgr = DeviceManager(config_path=tmp_cfg)
        dev = DeviceInfo(
            device_id="ui_test_dev",
            name="UI测试设备",
            ip="192.168.1.66",
            channels=[
                ChannelInfo(channel_no=1, name="大门", is_online=True, device_id="ui_test_dev"),
                ChannelInfo(channel_no=2, name="后院", is_online=False, device_id="ui_test_dev")
            ]
        )
        mgr.add_device(dev)

        from ui.channel_management_dialog import ChannelManagementDialog
        dlg = ChannelManagementDialog(mgr, "ui_test_dev")
        assert dlg.table.rowCount() == 2
        assert hasattr(dlg, "btn_add")
        assert hasattr(dlg, "btn_enable_all")
        assert hasattr(dlg, "btn_disable_all")
    finally:
        if os.path.exists(tmp_cfg):
            os.remove(tmp_cfg)


def test_import_robustness_bom_and_empty_files():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_cfg = f.name
    try:
        mgr = DeviceManager(config_path=tmp_cfg)

        # 1. Test 0-byte file (reproducing the user's issue)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_zero:
            zero_path = f_zero.name
        try:
            ok, msg, count = mgr.import_devices(zero_path)
            assert ok is False
            assert "0 字节" in msg
            assert "微信" in msg
        finally:
            if os.path.exists(zero_path):
                os.remove(zero_path)

        # 2. Test UTF-8 with BOM file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="wb") as f_bom:
            bom_content = b"\xef\xbb\xbf" + '[{"device_id":"bom_dev","name":"BOM设备","ip":"192.168.1.99","port":8000}]'.encode("utf-8")
            f_bom.write(bom_content)
            bom_path = f_bom.name
        try:
            ok, msg, count = mgr.import_devices(bom_path)
            assert ok is True
            assert count == 1
            assert mgr.get_device("bom_dev") is not None
            assert mgr.get_device("bom_dev").name == "BOM设备"
        finally:
            if os.path.exists(bom_path):
                os.remove(bom_path)

        # 3. Test text import directly (clipboard support)
        text_data = '[{"device_id":"clip_dev","name":"剪贴板设备","ip":"192.168.1.101","port":8000}]'
        ok, msg, count = mgr.import_devices_from_text(text_data)
        assert ok is True
        assert count == 1
        assert mgr.get_device("clip_dev") is not None
    finally:
        if os.path.exists(tmp_cfg):
            os.remove(tmp_cfg)


def test_selective_device_export():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg:
        cfg_path = f_cfg.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_bak:
        bak_path = f_bak.name

    try:
        mgr = DeviceManager(config_path=cfg_path)
        dev1 = DeviceInfo(
            device_id="dev_01",
            name="Office 1",
            ip="192.168.1.101",
            port=8000,
            username="admin",
            password="123",
            protocol=ProtocolType.HIKVISION,
            rtsp_port=554,
            channels=[]
        )
        dev2 = DeviceInfo(
            device_id="dev_02",
            name="Office 2",
            ip="192.168.1.102",
            port=8000,
            username="admin",
            password="123",
            protocol=ProtocolType.HIKVISION,
            rtsp_port=554,
            channels=[]
        )
        mgr.add_device(dev1)
        mgr.add_device(dev2)

        # Export only dev_01
        data1 = mgr.get_devices_export_data(device_ids=["dev_01"])
        assert len(data1) == 1
        assert data1[0]["device_id"] == "dev_01"

        # Export file for only dev_02
        ok = mgr.export_devices(bak_path, device_ids=["dev_02"])
        assert ok is True
        with open(bak_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        assert len(file_data) == 1
        assert file_data[0]["device_id"] == "dev_02"
    finally:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
        if os.path.exists(bak_path):
            os.remove(bak_path)





# -*- coding: utf-8 -*-
"""
Unit tests for Device Manager.
"""

import os
import tempfile
from core.base_adapter import DeviceInfo, ProtocolType
from core.device_manager import DeviceManager


def test_device_manager_crud():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_cfg = f.name

    try:
        mgr = DeviceManager(config_path=tmp_cfg)
        assert len(mgr.list_devices()) == 0

        # Add
        dev = DeviceInfo(
            device_id="dev_01",
            name="Main Gate NVR",
            ip="192.168.1.100",
            port=8000,
            username="admin",
            password="pwd",
            protocol=ProtocolType.HIKVISION
        )
        ok, dev_id = mgr.add_device(dev, auto_connect=True)
        assert ok is True
        assert dev_id == "dev_01"
        assert len(mgr.list_devices()) == 1

        # Check persistence by reloading from disk
        mgr2 = DeviceManager(config_path=tmp_cfg)
        loaded = mgr2.get_device("dev_01")
        assert loaded is not None
        assert loaded.name == "Main Gate NVR"
        assert loaded.ip == "192.168.1.100"
        assert loaded.protocol == ProtocolType.HIKVISION

        # Update
        loaded.name = "Renamed Gate NVR"
        mgr2.update_device(loaded)

        mgr3 = DeviceManager(config_path=tmp_cfg)
        assert mgr3.get_device("dev_01").name == "Renamed Gate NVR"

        # Remove
        assert mgr3.remove_device("dev_01") is True
        assert len(mgr3.list_devices()) == 0
        assert mgr3.get_device("dev_01") is None

    finally:
        if os.path.exists(tmp_cfg):
            os.remove(tmp_cfg)


def test_device_manager_test_connection():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_cfg = f.name
    try:
        mgr = DeviceManager(config_path=tmp_cfg)
        dev = DeviceInfo(
            device_id="test_conn_dev",
            name="Test NVR",
            ip="192.168.1.101",
            protocol=ProtocolType.HIKVISION
        )
        ok, msg, channels = mgr.test_connection(dev)
        assert ok is True
        assert "通道" in msg
        assert len(channels) > 0
        assert any(c.is_online for c in channels)
    finally:
        if os.path.exists(tmp_cfg):
            os.remove(tmp_cfg)


def test_device_dialog_quick_names():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_cfg = f.name

    try:
        mgr = DeviceManager(config_path=tmp_cfg)
        from ui.device_dialog import DeviceDialog
        dlg = DeviceDialog(mgr)

        assert dlg.combo_quick_name.count() > 1
        # 选择第一个常用名称
        dlg.combo_quick_name.setCurrentIndex(1)
        # 验证 edit_name 自动填充了中文
        assert dlg.edit_name.text() == "1号主大门"
    finally:
        if os.path.exists(tmp_cfg):
            os.remove(tmp_cfg)

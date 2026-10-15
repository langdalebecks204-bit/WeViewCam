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

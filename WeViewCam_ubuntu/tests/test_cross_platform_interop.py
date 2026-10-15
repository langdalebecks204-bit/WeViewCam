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


def test_envelope_metadata_json_import():
    """Verify that backup files wrapped in envelope metadata can also be imported."""
    envelope_json = {
        "version": 1,
        "platform": "android",
        "export_time": "2026-10-15T10:00:00",
        "devices": [
            {
                "device_id": "onvif_cam_01",
                "name": "ONVIF走廊摄像头",
                "ip": "192.168.1.188",
                "port": 80,
                "username": "admin",
                "password": "adminpassword",
                "protocol": "onvif",
                "rtsp_port": 554,
                "channels": [
                    {
                        "channel_no": 1,
                        "name": "走廊主码流",
                        "is_online": True,
                        "is_ptz": False,
                        "device_id": "onvif_cam_01"
                    }
                ]
            }
        ]
    }

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f_in:
        json.dump(envelope_json, f_in)
        in_path = f_in.name

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_cfg:
        cfg_path = f_cfg.name

    try:
        mgr = DeviceManager(config_path=cfg_path)
        ok, msg, count = mgr.import_devices(in_path, overwrite=False)
        assert ok is True
        assert count == 1
        dev = mgr.get_device("onvif_cam_01")
        assert dev is not None
        assert dev.name == "ONVIF走廊摄像头"
        assert dev.protocol == ProtocolType.ONVIF
        assert dev.port == 80
        assert len(dev.channels) == 1
    finally:
        for p in (in_path, cfg_path):
            if os.path.exists(p):
                os.remove(p)

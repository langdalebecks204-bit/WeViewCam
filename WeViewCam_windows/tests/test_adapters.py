# -*- coding: utf-8 -*-
"""
Unit tests for Device Adapters and Factory.
"""

from datetime import datetime
from core.base_adapter import (
    DeviceInfo,
    ProtocolType,
    PTZCommand,
    PlaybackCommand
)
from adapters.factory import create_device_adapter
from adapters.hikvision.adapter import HikvisionAdapter
from adapters.dahua.adapter import DahuaAdapter
from adapters.onvif.adapter import OnvifAdapter


def test_factory_creation():
    hik_info = DeviceInfo(
        device_id="hik_1",
        name="Hik Test",
        ip="192.168.1.64",
        protocol=ProtocolType.HIKVISION
    )
    adapter = create_device_adapter(hik_info)
    assert isinstance(adapter, HikvisionAdapter)

    dh_info = DeviceInfo(
        device_id="dh_1",
        name="Dahua Test",
        ip="192.168.1.65",
        protocol=ProtocolType.DAHUA
    )
    adapter = create_device_adapter(dh_info)
    assert isinstance(adapter, DahuaAdapter)

    onvif_info = DeviceInfo(
        device_id="onvif_1",
        name="ONVIF Test",
        ip="192.168.1.66",
        protocol=ProtocolType.ONVIF
    )
    adapter = create_device_adapter(onvif_info)
    assert isinstance(adapter, OnvifAdapter)


def test_hikvision_adapter_lifecycle():
    info = DeviceInfo(
        device_id="hik_test",
        name="Hik Device",
        ip="10.0.0.1",
        port=8000,
        username="admin",
        password="password123",
        protocol=ProtocolType.HIKVISION
    )
    adapter = HikvisionAdapter(info)

    # Login (in mock/local environment)
    assert adapter.login() is True
    assert adapter.is_connected is True

    # Get channels
    channels = adapter.get_channels()
    assert len(channels) > 0
    assert channels[0].channel_no >= 1

    # Real play
    play_handle = adapter.start_real_play(channel_no=1, win_id=0, stream_type=0)
    assert play_handle > 0
    assert adapter.stop_real_play(play_handle) is True

    # PTZ
    assert adapter.ptz_control(channel_no=1, command=PTZCommand.UP, stop=False, speed=5) is True
    assert adapter.ptz_control(channel_no=1, command=PTZCommand.UP, stop=True, speed=5) is True
    assert adapter.ptz_control(channel_no=36, command=PTZCommand.LEFT, stop=False, speed=4, play_handle=play_handle) is True
    assert adapter.ptz_control(channel_no=36, command=PTZCommand.ZOOM_IN, stop=False, speed=4) is True

    # Records search
    s_time = datetime(2026, 9, 15, 0, 0, 0)
    e_time = datetime(2026, 9, 15, 23, 59, 59)
    records = adapter.find_records(channel_no=1, start_time=s_time, end_time=e_time)
    assert isinstance(records, list)

    # Playback
    pb_handle = adapter.start_playback_by_time(1, 0, s_time, e_time)
    assert pb_handle > 0
    assert adapter.playback_control(pb_handle, PlaybackCommand.PAUSE) is True
    assert adapter.playback_control(pb_handle, PlaybackCommand.RESTART) is True
    assert adapter.stop_playback(pb_handle) is True

    # Playback by name
    pb_name_handle = adapter.start_playback_by_name("test_file.mp4", 0)
    assert pb_name_handle > 0
    assert adapter.stop_playback(pb_name_handle) is True

    # Logout
    assert adapter.logout() is True
    assert adapter.is_connected is False


def test_dahua_adapter_lifecycle():
    dh_info = DeviceInfo(
        device_id="dh_test_lifecycle",
        name="Dahua Test Device",
        ip="192.168.1.100",
        port=37777,
        username="admin",
        password="password123",
        protocol=ProtocolType.DAHUA
    )
    dh_adapter = DahuaAdapter(dh_info)
    assert dh_adapter.login() is True
    assert dh_adapter.is_connected is True

    # Channels
    channels = dh_adapter.get_channels()
    assert len(channels) > 0
    assert channels[0].device_id == "dh_test_lifecycle"

    # Real play
    play_h = dh_adapter.start_real_play(channel_no=1, win_id=1001)
    assert play_h > 0
    assert dh_adapter.stop_real_play(play_h) is True

    # PTZ
    assert dh_adapter.ptz_control(channel_no=1, command=PTZCommand.UP, speed=4) is True
    assert dh_adapter.ptz_control(channel_no=1, command=PTZCommand.ZOOM_IN, speed=4) is True

    # Snapshot & Record
    assert dh_adapter.capture_picture(play_handle=play_h, save_path="test_snap.jpg") is True
    assert dh_adapter.start_record(play_handle=play_h, save_path="test_rec.mp4") is True
    assert dh_adapter.stop_record(play_handle=play_h) is True

    # Playback
    s_time = datetime(2026, 9, 15, 0, 0, 0)
    e_time = datetime(2026, 9, 15, 23, 59, 59)
    records = dh_adapter.find_records(channel_no=1, start_time=s_time, end_time=e_time)
    assert len(records) > 0
    pb_h = dh_adapter.start_playback_by_time(1, 0, s_time, e_time)
    assert pb_h > 0
    assert dh_adapter.playback_control(pb_h, PlaybackCommand.PAUSE) is True
    assert dh_adapter.playback_control(pb_h, PlaybackCommand.RESTART) is True
    assert dh_adapter.stop_playback(pb_h) is True

    # Logout
    assert dh_adapter.logout() is True
    assert dh_adapter.is_connected is False


def test_onvif_adapter():
    onvif_info = DeviceInfo(device_id="onvif_test", name="ONVIF", ip="10.0.0.3", protocol=ProtocolType.ONVIF)
    onvif_adapter = OnvifAdapter(onvif_info)
    assert onvif_adapter.login() is True
    assert len(onvif_adapter.get_channels()) > 0
    assert onvif_adapter.logout() is True


def test_player_controller_reopen():
    from core.device_manager import DeviceManager
    from core.player_controller import PlayerController

    dm = DeviceManager(config_path="tests/test_devices_reopen.json")
    dev_info = DeviceInfo(
        device_id="test_reopen_dev",
        name="Test Reopen Dev",
        ip="192.168.1.100",
        protocol=ProtocolType.HIKVISION
    )
    dm.add_device(dev_info)

    pc = PlayerController(dm)
    # Start live play
    ok = pc.start_live_play(slot_id=0, device_id="test_reopen_dev", channel_no=1, win_id=12345)
    assert ok is True
    assert pc.get_slot_state(0).is_live is True

    # Reopen live play with new win_id (simulating maximize)
    reopen_ok = pc.reopen_live_play(slot_id=0, win_id=67890)
    assert reopen_ok is True
    assert pc.get_slot_state(0).is_live is True
    assert pc.get_slot_state(0).win_id == 67890

    # Stop live play
    pc.stop_slot(0)
    assert pc.get_slot_state(0).is_live is False

    # Start playback
    s_time = datetime(2026, 9, 15, 10, 0, 0)
    e_time = datetime(2026, 9, 15, 12, 0, 0)
    pb_ok = pc.start_playback(slot_id=1, device_id="test_reopen_dev", channel_no=1, start_time=s_time, end_time=e_time, win_id=11111)
    assert pb_ok is True
    assert pc.get_slot_state(1).is_playback is True

    # Reopen playback
    reopen_pb = pc.reopen_playback(slot_id=1, current_time=datetime(2026, 9, 15, 10, 30, 0), win_id=22222)
    assert reopen_pb is True
    assert pc.get_slot_state(1).win_id == 22222
    assert pc.get_slot_state(1).is_playback is True

    pc.stop_all()
    import os
    if os.path.exists("tests/test_devices_reopen.json"):
        os.remove("tests/test_devices_reopen.json")


def test_hikvision_cvr_multi_group_channels():
    """
    Test channel discovery on high-density CVR storage devices (e.g., DS-A71048)
    with 128+ channels across multiple groups to prevent ctypes 'invalid index' errors.
    """
    import ctypes
    from unittest.mock import MagicMock
    from adapters.hikvision.driver import HikvisionNativeDriver
    from adapters.hikvision.structures import (
        NET_DVR_IPPARACFG_V40,
        NET_DVR_STREAM_MODE,
        NET_DVR_DEVICEINFO_V30
    )

    driver = HikvisionNativeDriver()
    # Save original state
    orig_sdk = driver.sdk_lib

    try:
        mock_sdk = MagicMock()
        mock_sdk.is_loaded = True
        mock_sdk_hcnetsdk = MagicMock()
        mock_sdk.hcnetsdk = mock_sdk_hcnetsdk
        driver.sdk_lib = mock_sdk

        # Mock NET_DVR_GetDVRConfig to simulate a 128-channel CVR with 2 groups
        def mock_get_dvr_config(user_id, command, group_idx, out_ptr, out_size, ret_ptr):
            if command == 1062:  # NET_DVR_GET_IPPARACFG_V40
                cfg = getattr(out_ptr, "_obj", out_ptr)
                cfg.dwSize = ctypes.sizeof(NET_DVR_IPPARACFG_V40)
                cfg.dwGroupNum = 2
                cfg.dwDChanNum = 128
                cfg.dwStartDChan = 33
                # Populate slots in this group
                for i in range(64):
                    cfg.struStreamMode[i].byGetStreamType = 0
                    cfg.struStreamMode[i].uGetStream.struChanInfo.byIPID = (i % 2)  # 50% attached
                return 1
            return 0

        mock_sdk_hcnetsdk.NET_DVR_GetDVRConfig.side_effect = mock_get_dvr_config

        dev_info = NET_DVR_DEVICEINFO_V30()
        dev_info.byChanNum = 0
        dev_info.byStartChan = 1

        # Must not raise IndexError: invalid index!
        channels = driver.get_channels(user_id=1, device_info=dev_info)

        assert len(channels) == 128
        assert channels[0].channel_no == 33
        assert channels[127].channel_no == 160
        # Channels 0, 2, 4... should be unattached, 1, 3, 5... attached
        attached_count = sum(1 for c in channels if not c.extra.get("unattached", False))
        assert attached_count == 64
        # All channels must have is_enabled=True so they are rendered in UI device tree
        assert all(c.is_enabled for c in channels)
    finally:
        driver.sdk_lib = orig_sdk




def test_hikvision_cvr_legacy_fallback():
    """Test fallback to device_info when NET_DVR_GET_IPPARACFG_V40 is unsupported by legacy CVR."""
    from unittest.mock import MagicMock
    from adapters.hikvision.driver import HikvisionNativeDriver
    from adapters.hikvision.structures import NET_DVR_DEVICEINFO_V30

    driver = HikvisionNativeDriver()
    orig_sdk = driver.sdk_lib

    try:
        mock_sdk = MagicMock()
        mock_sdk.is_loaded = True
        mock_sdk_hcnetsdk = MagicMock()
        mock_sdk.hcnetsdk = mock_sdk_hcnetsdk
        driver.sdk_lib = mock_sdk

        # Simulate V40 unsupported (returns 0)
        mock_sdk_hcnetsdk.NET_DVR_GetDVRConfig.return_value = 0

        dev_info = NET_DVR_DEVICEINFO_V30()
        dev_info.byChanNum = 0
        dev_info.byStartChan = 1
        dev_info.byIPChanNum = 48  # 48 IP channels
        dev_info.byHighDChanNum = 0
        dev_info.byStartDChan = 33

        channels = driver.get_channels(user_id=1, device_info=dev_info)
        assert len(channels) == 48
        assert channels[0].channel_no == 33
        assert channels[47].channel_no == 80
    finally:
        driver.sdk_lib = orig_sdk


def test_main_window_startup():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.main_window import MainWindow
    win = MainWindow()
    assert win is not None
    assert "WeViewCam" in win.windowTitle()
    assert not hasattr(win, "btn_nav_inspection")
    assert not hasattr(win, "open_inspection_module")

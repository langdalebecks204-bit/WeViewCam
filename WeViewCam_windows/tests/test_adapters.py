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


def test_dahua_and_onvif_adapters():
    # Dahua
    dh_info = DeviceInfo(device_id="dh_test", name="DH", ip="10.0.0.2", protocol=ProtocolType.DAHUA)
    dh_adapter = DahuaAdapter(dh_info)
    assert dh_adapter.login() is True
    assert len(dh_adapter.get_channels()) > 0
    assert dh_adapter.logout() is True

    # ONVIF
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


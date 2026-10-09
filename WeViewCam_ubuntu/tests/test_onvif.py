# -*- coding: utf-8 -*-
"""
Unit tests for ONVIF protocol adapter and RTSP player engine.
"""

import os
import tempfile
from core.base_adapter import DeviceInfo, ProtocolType, PTZCommand
from adapters.onvif.adapter import OnvifAdapter
from adapters.onvif.player import RtspPlayerManager


def test_onvif_adapter_lifecycle():
    dev = DeviceInfo(
        device_id="onvif_cam_01",
        name="ONVIF Outdoor Cam",
        ip="192.168.1.188",
        port=80,
        username="admin",
        password="password123",
        protocol=ProtocolType.ONVIF
    )

    adapter = OnvifAdapter(dev)

    # 1. Login
    assert adapter.login() is True
    assert adapter.is_logged_in is True

    # 2. Channels (1 physical camera = 1 channel)
    channels = adapter.get_channels()
    assert len(channels) == 1
    ch1 = channels[0]
    assert ch1.channel_no == 1
    assert ch1.is_online is True

    # Test RTSP URL normalization & IP correction
    raw_faulty_url = "rtsp://192.168.1.64:554/Streaming/Channels/101?transportmode=unicast"
    fixed_url = adapter._normalize_rtsp_url(raw_faulty_url)
    assert "192.168.1.188" in fixed_url  # Target reachable IP replaced
    assert "192.168.1.64" not in fixed_url
    assert "admin:password123@" in fixed_url

    # 3. Start Live Play (win_id=9999)
    play_handle = adapter.start_real_play(channel_no=1, win_id=9999)
    assert play_handle > 0

    # 4. Snapshot
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        tmp_snap = f.name
    try:
        ok = adapter.capture_picture(play_handle, tmp_snap)
        assert ok is True
        assert os.path.exists(tmp_snap)
    finally:
        if os.path.exists(tmp_snap):
            os.remove(tmp_snap)

    # 5. Record
    record_path = "test_onvif_rec.mp4"
    assert adapter.start_record(play_handle, record_path) is True
    assert adapter.stop_record(play_handle) is True

    # 6. PTZ commands
    assert adapter.ptz_control(channel_no=1, command=PTZCommand.LEFT, stop=False, speed=4) is True
    assert adapter.ptz_control(channel_no=1, command=PTZCommand.LEFT, stop=True) is True
    assert adapter.ptz_control(channel_no=1, command=PTZCommand.ZOOM_IN, stop=False, speed=6) is True

    # 7. Stop Play
    assert adapter.stop_real_play(play_handle) is True

    # 8. Logout
    assert adapter.logout() is True
    assert adapter.is_logged_in is False


def test_onvif_ptz_velocity_mapping():
    # Tilt Up
    p, t, z = OnvifAdapter._command_to_velocity(PTZCommand.UP, 0.5)
    assert p == 0.0 and t == 0.5 and z == 0.0

    # Tilt Down
    p, t, z = OnvifAdapter._command_to_velocity(PTZCommand.DOWN, 0.5)
    assert p == 0.0 and t == -0.5 and z == 0.0

    # Pan Left / Right
    p, t, z = OnvifAdapter._command_to_velocity(PTZCommand.LEFT, 0.8)
    assert p == -0.8 and t == 0.0 and z == 0.0
    p, t, z = OnvifAdapter._command_to_velocity(PTZCommand.RIGHT, 0.8)
    assert p == 0.8 and t == 0.0 and z == 0.0

    # Diagonal Up-Right
    p, t, z = OnvifAdapter._command_to_velocity(PTZCommand.UP_RIGHT, 1.0)
    assert p > 0.7 and t > 0.7

    # Zoom In / Out
    p, t, z = OnvifAdapter._command_to_velocity(PTZCommand.ZOOM_IN, 0.6)
    assert p == 0.0 and t == 0.0 and z == 0.6
    p, t, z = OnvifAdapter._command_to_velocity(PTZCommand.ZOOM_OUT, 0.6)
    assert p == 0.0 and t == 0.0 and z == -0.6


def test_rtsp_player_manager():
    mgr = RtspPlayerManager.get_instance()
    # Test URL masking
    masked = mgr._mask_url("rtsp://admin:superSecretPass@192.168.1.100:554/live")
    assert "superSecretPass" not in masked
    assert "admin:***@192.168.1.100:554/live" in masked

    # Start and stop playback handle
    handle = mgr.start_play("rtsp://test:pwd@127.0.0.1/stream", win_id=12345)
    assert handle >= 6100
    assert mgr.stop_play(handle) is True


def test_stream_uri_candidates_and_negotiation():
    dev = DeviceInfo(
        device_id="cam_gate_02",
        name="2号道闸入口",
        ip="10.0.25.206",
        port=80,
        username="admin",
        password="admin_password",
        protocol=ProtocolType.ONVIF
    )
    adapter = OnvifAdapter(dev)

    # 1. Main stream candidates
    main_cands = adapter.get_stream_uri_candidates(channel_no=1, stream_type=0)
    assert len(main_cands) >= 5
    # Must contain Hikvision, Dahua, Zhenshi, TP-Link, Xiongmai patterns
    assert any("/Streaming/Channels/101" in u for u in main_cands)
    assert any("/cam/realmonitor?channel=1&subtype=0" in u for u in main_cands)
    assert any("/live/ch0" in u for u in main_cands)
    assert any("/stream1" in u for u in main_cands)
    assert any("10.0.25.206" in u for u in main_cands)

    # 2. Sub stream candidates
    sub_cands = adapter.get_stream_uri_candidates(channel_no=1, stream_type=1)
    assert len(sub_cands) >= 5
    assert any("/Streaming/Channels/102" in u for u in sub_cands)
    assert any("/cam/realmonitor?channel=1&subtype=1" in u for u in sub_cands)
    assert any("/live/sub" in u or "/live/ch1" in u for u in sub_cands)
    assert any("/stream2" in u for u in sub_cands)

    # 3. Cached verified URL priority
    matched_test_url = "rtsp://admin:admin_password@10.0.25.206:554/live/ch0"
    adapter._cached_working_urls[(1, 0)] = matched_test_url
    updated_cands = adapter.get_stream_uri_candidates(channel_no=1, stream_type=0)
    # The verified working URL must now be at index 0!
    assert updated_cands[0] == matched_test_url

    # 4. Custom RTSP override
    dev_custom = DeviceInfo(
        device_id="custom_cam",
        name="Custom Camera",
        ip="10.0.25.206",
        port=554,
        protocol=ProtocolType.CUSTOM_RTSP,
        extra={"custom_rtsp_url": "/h264"}
    )
    custom_adapter = OnvifAdapter(dev_custom)
    c_cands = custom_adapter.get_stream_uri_candidates(channel_no=1, stream_type=0)
    assert c_cands[0] == "rtsp://admin:@10.0.25.206:554/h264"

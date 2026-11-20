# -*- coding: utf-8 -*-
"""Tests for stream stats (FPS and bitrate) tracking and OSD formatting."""

import time
import pytest
from PyQt5.QtWidgets import QApplication

from core.base_adapter import StreamStatsTracker
from core.device_manager import DeviceManager
from core.player_controller import PlayerController
from ui.video_widget import VideoWidget


def test_stream_stats_tracker_bytes_and_frames():
    tracker = StreamStatsTracker()
    # Initially None before sampling interval elapses
    assert tracker.sample_bitrate_kbps() is None
    assert tracker.sample_fps_from_total_frames(100) is None

    # Record 256 KB over ~0.5s -> ~4096 kbps
    tracker.record_bytes(256 * 1024)
    time.sleep(0.5)
    kbps = tracker.sample_bitrate_kbps()
    assert kbps is not None
    assert 2000.0 < kbps < 6000.0

    # Cumulative frames delta: 100 -> 115 over ~0.5s -> ~30 fps
    fps = tracker.sample_fps_from_total_frames(115)
    assert fps is not None
    assert 15.0 < fps < 45.0


def test_stream_stats_tracker_total_bytes():
    tracker = StreamStatsTracker()
    assert tracker.sample_bitrate_from_total_bytes(1000) is None
    time.sleep(0.5)
    kbps = tracker.sample_bitrate_from_total_bytes(1000 + 125 * 1024)
    assert kbps is not None
    assert 1000.0 < kbps < 3500.0


def test_video_widget_set_stream_stats_osd():
    app = QApplication.instance() or QApplication([])
    w = VideoWidget(slot_id=0)

    w.set_stream_stats(25.0, 512.0)
    assert w.fps_label.text() == "25 fps | 512 kbps"

    w.set_stream_stats(29.8, 2048.0)
    assert w.fps_label.text() == "30 fps | 2.00 Mbps"

    w.set_stream_stats(None, 768.0)
    assert w.fps_label.text() == "768 kbps"

    w.set_stream_stats(None, None)
    assert w.fps_label.text() == ""

    w.clear_stream()
    assert w.fps_label.text() == ""


def test_player_controller_get_slot_stats_idle(tmp_path):
    dm = DeviceManager(config_path=str(tmp_path / "devices.json"))
    pc = PlayerController(dm)
    assert pc.get_slot_stats(0) == (None, None)


def test_dahua_get_stream_stats_handles_c_long_port(monkeypatch):
    import ctypes
    from adapters.dahua.driver import DahuaNativeDriver

    drv = DahuaNativeDriver()
    drv.sdk_lib.is_loaded = True

    class FakePlaySDK:
        def PLAY_GetPlayedFrames(self, port):
            assert isinstance(port, ctypes.c_int)
            return 100

        def PLAY_GetCurrentFrameRate(self, port):
            assert isinstance(port, ctypes.c_int)
            return 25

    class FakeNetClient:
        play_sdk = FakePlaySDK()

    drv.sdk_lib.net_client = FakeNetClient()
    drv._live_sessions[123] = (ctypes.c_long(101), None, True)

    fps, _ = drv.get_stream_stats(123, is_playback=False)
    assert fps == 25.0


def test_merge_channels_updates_online_status_on_reconnect():
    from core.base_adapter import ChannelInfo

    existing = [
        ChannelInfo(channel_no=33, name="大门口", is_online=False, is_enabled=True),
        ChannelInfo(channel_no=34, name="通道 2", is_online=False, is_enabled=True),
    ]
    probed = [
        ChannelInfo(channel_no=33, name="IP通道 1", is_online=True, is_enabled=True),
        ChannelInfo(channel_no=34, name="IP通道 2", is_online=False, is_enabled=True),
    ]
    merged = DeviceManager._merge_channel_lists(existing, probed)
    by_no = {c.channel_no: c for c in merged}
    assert by_no[33].name == "大门口"
    assert by_no[33].is_online is True
    assert by_no[34].is_online is False


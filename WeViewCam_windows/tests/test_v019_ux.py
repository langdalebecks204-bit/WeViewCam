# -*- coding: utf-8 -*-
"""Tests for v0.1.9 Open UX improvements, drag-to-play, and NVR channel auto-enable."""

import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest
from PyQt5.QtCore import Qt, QPoint, QMimeData
from PyQt5.QtGui import QDropEvent
from PyQt5.QtWidgets import QApplication
from core.base_adapter import ChannelInfo, DeviceInfo, ProtocolType
from core.device_manager import DeviceManager
from core.player_controller import PlayerController
from ui.live_view_widget import LiveViewWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication([])
    return app


def test_live_view_defaults_single_screen_and_collapsed_ptz(qapp, tmp_path):
    dm = DeviceManager(config_path=str(tmp_path / "devices.json"))
    pc = PlayerController(dm)
    lv = LiveViewWidget(pc)

    assert lv.current_layout_count == 1
    assert lv.saved_layout_count == 1
    assert len(lv.video_slots) >= 1
    assert lv.btn_ptz_toggle.isChecked() is False
    assert lv.ptz_panel.isVisible() is False


def test_merge_auto_enables_newly_attached_nvr_channel():
    existing = [
        ChannelInfo(channel_no=33, name="CH33", is_online=True, is_enabled=False, extra={"unattached": False}),
        ChannelInfo(channel_no=34, name="CH34", is_online=False, is_enabled=False, extra={"unattached": True}),
    ]
    incoming = [
        ChannelInfo(channel_no=33, name="CH33", is_online=True, is_enabled=True, extra={"unattached": False}),
        ChannelInfo(channel_no=34, name="东门新枪机", is_online=True, is_enabled=True, extra={"unattached": False}),
        ChannelInfo(channel_no=35, name="新增通道35", is_online=True, is_enabled=True, extra={"unattached": False}),
    ]
    merged = DeviceManager._merge_channel_lists(existing, incoming)
    by_no = {c.channel_no: c for c in merged}
    assert by_no[33].is_enabled is False
    assert by_no[34].is_enabled is True
    assert by_no[35].is_enabled is True


def test_move_or_swap_live_slots_between_windows(qapp, tmp_path):
    dm = DeviceManager(config_path=str(tmp_path / "devices.json"))
    pc = PlayerController(dm)
    lv = LiveViewWidget(pc)
    lv.switch_layout(4)

    class FakeAdapter:
        is_connected = True
        _next_h = 100

        def start_real_play(self, channel_no, win_id, stream_type=0):
            self._next_h += 1
            return self._next_h

        def stop_real_play(self, handle):
            return True

    dm._adapters["dev1"] = FakeAdapter()

    # Start stream on slot 0 (window 1), drag slot 0 -> idle slot 2 (window 3)
    assert pc.start_live_play(0, "dev1", 1, win_id=lv.video_slots[0].get_win_id(), channel_name="通道1")
    lv.video_slots[0].set_stream_info("通道1", "实时预览中")
    lv._on_slot_swap_requested(0, 2)
    assert pc.get_slot_state(0).is_live is False
    assert lv.video_slots[0].is_playing is False
    assert pc.get_slot_state(2).is_live is True
    assert pc.get_slot_state(2).channel_no == 1
    assert lv.video_slots[2].is_playing is True

    # Start stream on slot 1 (window 2), then drag slot 2 -> slot 1 to swap
    assert pc.start_live_play(1, "dev1", 2, win_id=lv.video_slots[1].get_win_id(), channel_name="通道2")
    lv.video_slots[1].set_stream_info("通道2", "实时预览中")
    lv._on_slot_swap_requested(2, 1)
    assert pc.get_slot_state(1).channel_no == 1
    assert pc.get_slot_state(2).channel_no == 2


def test_drop_channel_from_tree_plays_in_target_slot(qapp, tmp_path):
    dm = DeviceManager(config_path=str(tmp_path / "devices.json"))
    pc = PlayerController(dm)
    lv = LiveViewWidget(pc)
    lv.switch_layout(4)

    class FakeAdapter:
        is_connected = True

        def start_real_play(self, channel_no, win_id, stream_type=0):
            return 77

        def stop_real_play(self, handle):
            return True

    dm._adapters["dev1"] = FakeAdapter()

    mime = QMimeData()
    mime.setData(
        "application/x-weviewcam-channel",
        json.dumps({"device_id": "dev1", "channel_no": 34, "channel_name": "东门枪机"}).encode("utf-8"),
    )
    target_slot = lv.video_slots[2]
    ev = QDropEvent(QPoint(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    target_slot.dropEvent(ev)

    assert ev.isAccepted()
    st = pc.get_slot_state(2)
    assert st.is_live is True
    assert st.channel_no == 34
    assert st.channel_name == "东门枪机"
    assert target_slot.is_playing is True


def test_disconnect_or_reconnect_stops_active_slots_before_logout(qapp, tmp_path):
    dm = DeviceManager(config_path=str(tmp_path / "devices.json"))
    pc = PlayerController(dm)
    lv = LiveViewWidget(pc)

    events = []

    class TrackingAdapter:
        is_connected = True

        def login(self):
            events.append("login")
            self.is_connected = True
            return True

        def logout(self):
            events.append("logout")
            self.is_connected = False
            return True

        def get_channels(self):
            return [ChannelInfo(channel_no=1, name="CH1", is_online=True, is_enabled=True)]

        def start_real_play(self, channel_no, win_id, stream_type=0):
            events.append(f"start:{channel_no}")
            return 42

        def stop_real_play(self, handle):
            events.append(f"stop:{handle}")
            return True

    dev = DeviceInfo(
        device_id="dev_rc",
        name="NVR",
        ip="127.0.0.1",
        port=8000,
        username="admin",
        password="",
        protocol=ProtocolType.HIKVISION,
        is_connected=True,
    )
    dm._devices["dev_rc"] = dev
    dm._adapters["dev_rc"] = TrackingAdapter()

    def _on_before_disc(did):
        for sid in pc.stop_device_slots(did):
            if 0 <= sid < len(lv.video_slots):
                lv.video_slots[sid].clear_stream()

    dm.register_before_disconnect_callback(_on_before_disc)

    assert pc.start_live_play(0, "dev_rc", 1, win_id=lv.video_slots[0].get_win_id(), channel_name="CH1")
    lv.video_slots[0].set_stream_info("CH1", "实时预览中")

    assert dm.connect_device("dev_rc", force_refresh=True) is True
    assert events.index("stop:42") < events.index("logout") < events.index("login")
    assert pc.get_slot_state(0).is_live is False
    assert lv.video_slots[0].is_playing is False

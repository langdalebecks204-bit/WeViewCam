# -*- coding: utf-8 -*-
"""Unit tests for v0.1.8 desktop UX improvements (fullscreen, batch device load, auto-advance focus)."""

import os
import sys
from unittest.mock import MagicMock

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_adapter import ChannelInfo, DeviceInfo, ProtocolType
from ui.device_tree_widget import DeviceTreeWidget
from ui.live_view_widget import LiveViewWidget
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication([])
    return app


def _make_device(device_id="dev1", connected=True, num_channels=6, disabled_nos=None):
    disabled_nos = set(disabled_nos or [])
    channels = [
        ChannelInfo(
            channel_no=i,
            name=f"CAM-{i}",
            is_online=True,
            is_enabled=(i not in disabled_nos),
        )
        for i in range(1, num_channels + 1)
    ]
    return DeviceInfo(
        device_id=device_id,
        name="NVR-01",
        ip="192.168.1.100",
        port=8000,
        username="admin",
        password="123",
        protocol=ProtocolType.HIKVISION,
        is_connected=connected,
        channels=channels,
    )


def test_auto_advance_slot_focus_on_play(qapp):
    pc = MagicMock()
    pc.get_slot_state.return_value = None
    pc.start_live_play.return_value = True

    lv = LiveViewWidget(pc)
    assert lv.current_layout_count == 1
    lv.switch_layout(4)
    assert lv.current_layout_count == 4
    assert lv.active_slot_id == 0

    for expected_next in (1, 2, 3, 0):
        lv.play_channel_in_slot("dev1", 1, "CAM-1")
        assert lv.active_slot_id == expected_next
        assert lv.video_slots[expected_next]._is_selected

    # Failed play should not advance focus
    pc.start_live_play.return_value = False
    lv.play_channel_in_slot("dev1", 2, "CAM-2")
    assert lv.active_slot_id == 0

    # 1-split keeps focus on slot 0
    pc.start_live_play.return_value = True
    lv.switch_layout(1)
    lv.play_channel_in_slot("dev1", 1, "CAM-1")
    assert lv.active_slot_id == 0
    lv.close()


def test_double_click_device_batch_loads_enabled_channels(qapp):
    dev = _make_device(connected=False, num_channels=6, disabled_nos={2})
    dm = MagicMock()
    dm.list_devices.return_value = [dev]
    dm.get_device.return_value = dev

    def fake_connect(device_id):
        dev.is_connected = True
        return True

    dm.connect_device.side_effect = fake_connect

    tree = DeviceTreeWidget(dm, defer_load=False)
    emitted = []
    tree.device_double_clicked.connect(emitted.append)

    dev_item = tree.tree.topLevelItem(0)
    tree._on_item_double_clicked(dev_item, 0)

    dm.connect_device.assert_called_once_with("dev1")
    assert emitted == ["dev1"]

    pc = MagicMock()
    pc.get_slot_state.return_value = None
    pc.start_live_play.return_value = True
    lv = LiveViewWidget(pc)
    lv.switch_layout(4)

    loaded = lv.play_device_channels("dev1", dev.channels)
    assert loaded == 4
    called_channels = [call.kwargs["channel_no"] for call in pc.start_live_play.call_args_list]
    # Channel 2 is disabled, so first 4 enabled channels are 1, 3, 4, 5
    assert called_channels == [1, 3, 4, 5]
    assert lv.active_slot_id == 0
    tree.close()
    lv.close()


def test_true_video_fullscreen_toggles_chrome_and_window_state(qapp):
    win = MainWindow()
    win.show()
    qapp.processEvents()

    assert not win.isFullScreen()
    assert win.top_bar.isVisible()
    assert win.status_bar.isVisible()
    assert win.device_tree.isVisible()
    assert win.live_view.top_bar.isVisible()

    win.live_view.toggle_fullscreen()
    qapp.processEvents()

    assert win._is_video_fullscreen is True
    assert win.isFullScreen()
    assert not win.top_bar.isVisible()
    assert not win.status_bar.isVisible()
    assert not win.device_tree.isVisible()
    assert not win.live_view.top_bar.isVisible()
    assert not win.live_view.ptz_panel.isVisible()

    win.exit_video_fullscreen()
    qapp.processEvents()

    assert win._is_video_fullscreen is False
    assert not win.isFullScreen()
    assert win.top_bar.isVisible()
    assert win.status_bar.isVisible()
    assert win.device_tree.isVisible()
    assert win.live_view.top_bar.isVisible()
    assert win.live_view.ptz_panel.isVisible() == win.live_view.btn_ptz_toggle.isChecked()
    win.close()

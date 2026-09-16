# -*- coding: utf-8 -*-
"""
Main Application Window.
Surveillance Operations Center Shell: Top Navigation, Central Multi-View Stack, Status Bar.
"""

import os
import sys
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QSplitter, QStatusBar, QMessageBox
)
from core import __version__
from core.device_manager import DeviceManager
from core.player_controller import PlayerController
from adapters.hikvision.driver import HCNetSDKLibrary
from ui.device_tree_widget import DeviceTreeWidget
from ui.device_dialog import DeviceDialog
from ui.live_view_widget import LiveViewWidget
from ui.playback_widget import PlaybackWidget
from ui.styles import DARK_THEME_QSS
from core.logger import get_logger

logger = get_logger("MainWindow")


class MainWindow(QMainWindow):
    """Main Surveillance Operations Center Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"WeViewCam - 智能视频监控平台 v{__version__} (Ubuntu x86_64)")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)

        # Set Window Icon
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._icon_path = os.path.join(base_dir, "icon.png")
        if not os.path.exists(self._icon_path):
            self._icon_path = os.path.join(base_dir, "图标.jpg")
        if os.path.exists(self._icon_path):
            self.setWindowIcon(QIcon(self._icon_path))

        # Core controllers
        self.device_manager = DeviceManager()
        self.player_controller = PlayerController(self.device_manager)

        self._init_ui()
        self._init_clock_timer()

    def _init_ui(self):
        # Apply dark theme
        self.setStyleSheet(DARK_THEME_QSS)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Navigation Bar
        top_bar = QFrame(self)
        top_bar.setObjectName("topNavBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 0, 16, 0)
        top_layout.setSpacing(10)

        # Logo Icon & Title
        if hasattr(self, "_icon_path") and os.path.exists(self._icon_path):
            icon_label = QLabel(top_bar)
            pix = QPixmap(self._icon_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
            top_layout.addWidget(icon_label)

        logo = QLabel(f"WeViewCam v{__version__}", top_bar)
        logo.setObjectName("appLogo")
        top_layout.addWidget(logo)

        top_layout.addSpacing(24)

        # Nav Switcher Buttons
        self.btn_nav_live = QPushButton("📹 实时监控", top_bar)
        self.btn_nav_live.setProperty("class", "navBtn")
        self.btn_nav_live.setCheckable(True)
        self.btn_nav_live.setChecked(True)
        self.btn_nav_live.clicked.connect(lambda: self.switch_view(0))
        top_layout.addWidget(self.btn_nav_live)

        self.btn_nav_playback = QPushButton("⏪ 录像回放", top_bar)
        self.btn_nav_playback.setProperty("class", "navBtn")
        self.btn_nav_playback.setCheckable(True)
        self.btn_nav_playback.clicked.connect(lambda: self.switch_view(1))
        top_layout.addWidget(self.btn_nav_playback)

        top_layout.addStretch()

        # SDK Status indicator
        sdk_lib = HCNetSDKLibrary.get_instance()
        sdk_status_str = "海康SDK: 已就绪 (Linux 64)" if sdk_lib.is_loaded else "海康SDK: 模拟/未加载"
        self.lbl_sdk_status = QLabel(sdk_status_str, top_bar)
        sdk_color = "#3fb950" if sdk_lib.is_loaded else "#e3b341"
        self.lbl_sdk_status.setStyleSheet(f"color: {sdk_color}; font-size: 12px; font-weight: 500;")
        top_layout.addWidget(self.lbl_sdk_status)

        top_layout.addSpacing(16)

        # Clock
        self.lbl_clock = QLabel("", top_bar)
        self.lbl_clock.setStyleSheet("color: #8b949e; font-size: 13px; font-family: monospace;")
        top_layout.addWidget(self.lbl_clock)

        root_layout.addWidget(top_bar)

        # 2. Main Stacked Pages
        self.stacked_widget = QStackedWidget(self)

        # Page 0: Live View (Left Device Tree + Right Multi-screen Grid)
        page_live = QWidget(self.stacked_widget)
        page_live_layout = QHBoxLayout(page_live)
        page_live_layout.setContentsMargins(0, 0, 0, 0)
        page_live_layout.setSpacing(0)

        live_splitter = QSplitter(Qt.Horizontal, page_live)

        # Left Tree
        self.device_tree = DeviceTreeWidget(self.device_manager, live_splitter)
        self.device_tree.setMinimumWidth(220)
        self.device_tree.setMaximumWidth(320)
        self.device_tree.channel_double_clicked.connect(self._on_channel_double_clicked)
        self.device_tree.add_device_requested.connect(self._show_add_device_dialog)
        self.device_tree.edit_device_requested.connect(self._show_edit_device_dialog)
        self.device_tree.delete_device_requested.connect(self._on_delete_device)
        live_splitter.addWidget(self.device_tree)

        # Right Live View
        self.live_view = LiveViewWidget(self.player_controller, live_splitter)
        live_splitter.addWidget(self.live_view)

        live_splitter.setStretchFactor(0, 0)
        live_splitter.setStretchFactor(1, 1)
        page_live_layout.addWidget(live_splitter)

        self.stacked_widget.addWidget(page_live)

        # Page 1: Playback
        self.playback_view = PlaybackWidget(self.player_controller, self.device_manager, self.stacked_widget)
        self.stacked_widget.addWidget(self.playback_view)

        root_layout.addWidget(self.stacked_widget, 1)

        # 3. Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 | 支持海康威视、大华、ONVIF 多厂商监控对接")

    def _init_clock_timer(self):
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start()
        self._update_clock()

    def _update_clock(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.setText(now_str)

    def switch_view(self, index: int):
        """Switch between Live View (0) and Playback View (1)."""
        self.stacked_widget.setCurrentIndex(index)
        self.btn_nav_live.setChecked(index == 0)
        self.btn_nav_playback.setChecked(index == 1)

        if index == 1:
            # Refresh device dropdown in playback page
            self.playback_view.refresh_devices_combo()

    def _on_channel_double_clicked(self, device_id: str, channel_no: int, channel_name: str):
        """Play channel in active slot."""
        self.switch_view(0)
        self.live_view.play_channel_in_slot(device_id, channel_no, channel_name)
        self.status_bar.showMessage(f"已请求播放: {channel_name} (通道 {channel_no})", 3000)

    def _show_add_device_dialog(self):
        dlg = DeviceDialog(self.device_manager, parent=self)
        if dlg.exec_():
            self.device_tree.refresh_devices()
            self.playback_view.refresh_devices_combo()
            self.status_bar.showMessage("成功添加新监控设备", 3000)

    def _show_edit_device_dialog(self, device_id: str):
        dev = self.device_manager.get_device(device_id)
        if not dev:
            return
        dlg = DeviceDialog(self.device_manager, device_info=dev, parent=self)
        if dlg.exec_():
            self.device_tree.refresh_devices()
            self.playback_view.refresh_devices_combo()
            self.status_bar.showMessage(f"已更新设备 [{dev.name}]", 3000)

    def _on_delete_device(self, device_id: str):
        self.device_manager.remove_device(device_id)
        self.device_tree.refresh_devices()
        self.playback_view.refresh_devices_combo()
        self.status_bar.showMessage("已删除设备", 3000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
            event.accept()
            return
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
                event.accept()
                return
        super().keyPressEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.WindowStateChange:
            QTimer.singleShot(120, self._on_window_state_changed)

    def _on_window_state_changed(self):
        """Called when main window is maximized, restored or set to full screen."""
        if hasattr(self, "live_view"):
            self.live_view._refresh_active_slots(self.live_view.current_layout_count)
            if self.live_view.is_single_maximized:
                self.live_view._reopen_slot_if_playing(self.live_view.active_slot_id)
        if hasattr(self, "playback_view") and self.playback_view.is_playing:
            cur_t = self.playback_view.timeline._current_time
            w_id = self.playback_view.video_slot.get_win_id()
            self.player_controller.reopen_playback(self.playback_view.playback_slot_id, current_time=cur_t, win_id=w_id)

    def closeEvent(self, event):
        """Clean up on window close."""
        logger.info("应用程序正在退出，清理流资源...")
        self.player_controller.stop_all()
        sdk_lib = HCNetSDKLibrary.get_instance()
        sdk_lib.cleanup()
        event.accept()


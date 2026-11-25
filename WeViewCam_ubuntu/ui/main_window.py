# -*- coding: utf-8 -*-
"""
Main Application Window.
Surveillance Operations Center Shell: Top Navigation, Central Multi-View Stack, Status Bar.
"""

import os
import sys
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QSplitter, QStatusBar, QMessageBox, QShortcut, QApplication
)
from core import __version__
from core.device_manager import DeviceManager
from core.player_controller import PlayerController
from ui.device_tree_widget import DeviceTreeWidget
from ui.device_dialog import DeviceDialog
from ui.live_view_widget import LiveViewWidget
from ui.styles import DARK_THEME_QSS
from core.logger import get_logger

logger = get_logger("MainWindow")


class MainWindow(QMainWindow):
    """Main Surveillance Operations Center Window."""

    def __init__(self):
        super().__init__()
        platform_name = "Windows x64" if sys.platform.startswith("win") else "Linux x86_64"
        self.setWindowTitle(f"WeViewCam - 智能视频监控平台 v{__version__} ({platform_name})")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)

        # Set Window Icon
        search_dirs = []
        if getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                search_dirs.append(sys._MEIPASS)
            search_dirs.append(os.path.dirname(sys.executable))
        search_dirs.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self._icon_path = None
        for d in search_dirs:
            for fname in ["icon.png", "icon.ico", "图标.jpg"]:
                cand = os.path.join(d, fname)
                if os.path.exists(cand):
                    self._icon_path = cand
                    break
            if self._icon_path:
                break

        if self._icon_path and os.path.exists(self._icon_path):
            self.setWindowIcon(QIcon(self._icon_path))

        # Core controllers (defer device loading until after main window is visible)
        self.device_manager = DeviceManager(auto_load=False)
        self.player_controller = PlayerController(self.device_manager)

        self._pre_fullscreen_maximized = False
        self._is_video_fullscreen = False
        self._init_ui()
        self._init_fullscreen_overlay_and_shortcuts()
        self._init_clock_timer()
        QTimer.singleShot(30, self._post_show_init)

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
        self.top_bar = top_bar
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

        # Left Tree (defer rendering until after window is shown)
        self.device_tree = DeviceTreeWidget(self.device_manager, live_splitter, defer_load=True)
        self.device_tree.setMinimumWidth(220)
        self.device_tree.setMaximumWidth(320)
        self.device_tree.channel_double_clicked.connect(self._on_channel_double_clicked)
        self.device_tree.device_double_clicked.connect(self._on_device_double_clicked)
        self.device_tree.add_device_requested.connect(self._show_add_device_dialog)
        self.device_tree.edit_device_requested.connect(self._show_edit_device_dialog)
        self.device_tree.delete_device_requested.connect(self._on_delete_device)
        live_splitter.addWidget(self.device_tree)

        # Right Live View
        self.live_view = LiveViewWidget(self.player_controller, live_splitter)
        self.live_view.fullscreen_requested.connect(self.toggle_video_fullscreen)
        live_splitter.addWidget(self.live_view)

        live_splitter.setStretchFactor(0, 0)
        live_splitter.setStretchFactor(1, 1)
        page_live_layout.addWidget(live_splitter)

        self.stacked_widget.addWidget(page_live)

        # Page 1: Playback (created lazily on switch_view(1) or post-show init)
        self.playback_placeholder = QWidget(self.stacked_widget)
        self.playback_view = None
        self.stacked_widget.addWidget(self.playback_placeholder)

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

    def _post_show_init(self):
        """Load devices and render device tree after the main window is visible."""
        try:
            self.device_manager.load_devices()
            self.device_tree.refresh_devices()
            QTimer.singleShot(400, self.device_tree.start_async_refresh)
        except Exception as e:
            logger.error(f"延迟加载设备列表失败: {e}")
        QTimer.singleShot(100, self._ensure_playback_view)

    def _ensure_playback_view(self):
        """Lazily construct PlaybackWidget after first paint."""
        if getattr(self, "playback_view", None) is None:
            from ui.playback_widget import PlaybackWidget
            self.playback_view = PlaybackWidget(self.player_controller, self.device_manager, self.stacked_widget)
            idx = self.stacked_widget.indexOf(self.playback_placeholder)
            if idx >= 0:
                self.stacked_widget.removeWidget(self.playback_placeholder)
                self.playback_placeholder.deleteLater()
                self.stacked_widget.insertWidget(idx, self.playback_view)

    def _update_clock(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.setText(now_str)

    def switch_view(self, index: int):
        """Switch between Live View (0) and Playback View (1)."""
        if index == 1:
            self._ensure_playback_view()
        self.stacked_widget.setCurrentIndex(index)
        self.btn_nav_live.setChecked(index == 0)
        self.btn_nav_playback.setChecked(index == 1)

        if index == 1 and self.playback_view is not None:
            self.playback_view.refresh_devices_combo()

    def _on_channel_double_clicked(self, device_id: str, channel_no: int, channel_name: str):
        """Play channel in active slot."""
        self.switch_view(0)
        self.live_view.play_channel_in_slot(device_id, channel_no, channel_name)
        self.status_bar.showMessage(f"已请求播放: {channel_name} (通道 {channel_no})", 3000)

    def _on_device_double_clicked(self, device_id: str):
        """Batch-load enabled channels of the double-clicked device up to current split count."""
        self.switch_view(0)
        dev = self.device_manager.get_device(device_id)
        if not dev:
            return
        if not dev.channels:
            self.status_bar.showMessage(f"设备 [{dev.name}] 暂无可用通道或连接失败", 3000)
            return
        loaded = self.live_view.play_device_channels(device_id, dev.channels)
        if loaded > 0:
            self.status_bar.showMessage(
                f"已为设备 [{dev.name}] 批量加载 {loaded} 路通道到 {self.live_view.current_layout_count} 分屏",
                4000,
            )
        else:
            self.status_bar.showMessage(f"设备 [{dev.name}] 没有已启用的通道", 3000)

    def _show_add_device_dialog(self):
        dlg = DeviceDialog(self.device_manager, parent=self)
        if dlg.exec_():
            self.device_tree.refresh_devices()
            if getattr(self, "playback_view", None) is not None:
                self.playback_view.refresh_devices_combo()
            self.status_bar.showMessage("成功添加新监控设备", 3000)

    def _show_edit_device_dialog(self, device_id: str):
        dev = self.device_manager.get_device(device_id)
        if not dev:
            return
        dlg = DeviceDialog(self.device_manager, device_info=dev, parent=self)
        if dlg.exec_():
            self.device_tree.refresh_devices()
            if getattr(self, "playback_view", None) is not None:
                self.playback_view.refresh_devices_combo()
            self.status_bar.showMessage(f"已更新设备 [{dev.name}]", 3000)

    def _on_delete_device(self, device_id: str):
        self.device_manager.remove_device(device_id)
        self.device_tree.refresh_devices()
        if getattr(self, "playback_view", None) is not None:
            self.playback_view.refresh_devices_combo()
        self.status_bar.showMessage("已删除设备", 3000)

    def _init_fullscreen_overlay_and_shortcuts(self):
        """Initialize global F11/Esc shortcuts and floating exit-fullscreen button."""
        self._shortcut_f11 = QShortcut(QKeySequence(Qt.Key_F11), self)
        self._shortcut_f11.setContext(Qt.WindowShortcut)
        self._shortcut_f11.activated.connect(self.toggle_video_fullscreen)

        self._shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._shortcut_esc.setContext(Qt.WindowShortcut)
        self._shortcut_esc.activated.connect(self.exit_video_fullscreen)

        self._exit_fs_btn = QPushButton("✕ 退出全屏 (Esc)")
        self._exit_fs_btn.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        )
        self._exit_fs_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 210);
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(220, 38, 38, 230);
                border-color: #f87171;
            }
        """)
        self._exit_fs_btn.adjustSize()
        self._exit_fs_btn.clicked.connect(self.exit_video_fullscreen)
        self._exit_fs_btn.hide()

    def _position_exit_fs_button(self):
        if not hasattr(self, "_exit_fs_btn"):
            return
        screen = self.screen() if hasattr(self, "screen") and self.screen() else QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self._exit_fs_btn.adjustSize()
            x = geo.right() - self._exit_fs_btn.width() - 20
            y = geo.top() + 16
            self._exit_fs_btn.move(x, y)

    def toggle_video_fullscreen(self):
        """Toggle true OS fullscreen mode for the video surveillance viewport."""
        self.set_video_fullscreen(not self._is_video_fullscreen)

    def exit_video_fullscreen(self):
        """Exit true OS fullscreen mode if currently active."""
        if self._is_video_fullscreen or self.isFullScreen():
            self.set_video_fullscreen(False)

    def set_video_fullscreen(self, enabled: bool):
        """Enter or exit true OS fullscreen mode, hiding/restoring all chrome."""
        if enabled == self._is_video_fullscreen and self.isFullScreen() == enabled:
            return

        if enabled:
            self._pre_fullscreen_maximized = self.isMaximized()
            self._is_video_fullscreen = True
            self.top_bar.setVisible(False)
            self.status_bar.setVisible(False)
            self.device_tree.setVisible(False)
            self.live_view.set_fullscreen_mode(True)
            if getattr(self, "playback_view", None) is not None and hasattr(self.playback_view, "left_panel"):
                self.playback_view.left_panel.setVisible(False)
            self.showFullScreen()
            QTimer.singleShot(50, self._show_exit_fs_btn)
        else:
            self._is_video_fullscreen = False
            if hasattr(self, "_exit_fs_btn"):
                self._exit_fs_btn.hide()
            self.top_bar.setVisible(True)
            self.status_bar.setVisible(True)
            self.device_tree.setVisible(True)
            self.live_view.set_fullscreen_mode(False)
            if getattr(self, "playback_view", None) is not None and hasattr(self.playback_view, "left_panel"):
                self.playback_view.left_panel.setVisible(not getattr(self.playback_view, "is_fullscreen", False))
            if self._pre_fullscreen_maximized:
                self.showMaximized()
            else:
                self.showNormal()

    def _show_exit_fs_btn(self):
        if self._is_video_fullscreen and hasattr(self, "_exit_fs_btn"):
            self._position_exit_fs_button()
            self._exit_fs_btn.show()
            self._exit_fs_btn.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.toggle_video_fullscreen()
            event.accept()
            return
        elif event.key() == Qt.Key_Escape:
            if self._is_video_fullscreen or self.isFullScreen():
                self.exit_video_fullscreen()
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

    def closeEvent(self, event):
        """Clean up on window close."""
        if hasattr(self, "_exit_fs_btn"):
            self._exit_fs_btn.hide()
            self._exit_fs_btn.close()
        logger.info("应用程序正在退出，清理流资源...")
        self.player_controller.stop_all()
        try:
            from adapters.hikvision.driver import HCNetSDKLibrary
            HCNetSDKLibrary.get_instance().cleanup()
        except Exception:
            pass
        try:
            from adapters.dahua.driver import DahuaSDKLibrary
            DahuaSDKLibrary.get_instance().cleanup()
        except Exception:
            pass
        event.accept()

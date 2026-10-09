# -*- coding: utf-8 -*-
"""
Live View Video Surveillance Widget.
Features:
- Dynamic multi-screen grid layout (1, 4, 9, 16 splits).
- Direct X11 window embedding for zero-overhead decoding.
- Double-click to maximize/restore viewport.
- PTZ control panel (8 directions, zoom, focus, iris, speed).
"""

import os
from datetime import datetime
from typing import List, Optional
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QComboBox, QSlider, QLabel, QGroupBox,
    QFileDialog, QMessageBox, QSplitter, QFrame
)
from ui.video_widget import VideoWidget
from core.player_controller import PlayerController
from core.base_adapter import PTZCommand


class LiveViewWidget(QWidget):
    """Real-time multi-channel video monitoring view."""

    def __init__(self, player_controller: PlayerController, parent=None):
        super().__init__(parent)
        self.player_controller = player_controller

        self.max_slots = 16
        self.video_slots: List[VideoWidget] = []
        self.active_slot_id = 0
        self.current_layout_count = 4  # Default 4-split (2x2)
        self.saved_layout_count = 4
        self.is_single_maximized = False

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # 1. Top Control Bar
        top_bar = QFrame(self)
        top_bar.setStyleSheet("background-color: #1f232c; border-radius: 4px; padding: 2px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 4, 6, 4)
        top_layout.setSpacing(8)

        # Split screen buttons
        lbl_split = QLabel("分屏模式:", top_bar)
        lbl_split.setStyleSheet("color: #a0aab8; font-weight: 500;")
        top_layout.addWidget(lbl_split)

        self.btn_1_split = QPushButton("1 画面", top_bar)
        self.btn_1_split.clicked.connect(lambda: self.switch_layout(1))
        top_layout.addWidget(self.btn_1_split)

        self.btn_4_split = QPushButton("4 画面", top_bar)
        self.btn_4_split.clicked.connect(lambda: self.switch_layout(4))
        top_layout.addWidget(self.btn_4_split)

        self.btn_9_split = QPushButton("9 画面", top_bar)
        self.btn_9_split.clicked.connect(lambda: self.switch_layout(9))
        top_layout.addWidget(self.btn_9_split)

        self.btn_16_split = QPushButton("16 画面", top_bar)
        self.btn_16_split.clicked.connect(lambda: self.switch_layout(16))
        top_layout.addWidget(self.btn_16_split)

        top_layout.addSpacing(16)

        # Stream type selector
        lbl_stream = QLabel("码流:", top_bar)
        lbl_stream.setStyleSheet("color: #a0aab8;")
        top_layout.addWidget(lbl_stream)

        self.combo_stream = QComboBox(top_bar)
        self.combo_stream.addItem("主码流 (高清)", 0)
        self.combo_stream.addItem("子码流 (流畅)", 1)
        top_layout.addWidget(self.combo_stream)

        top_layout.addStretch()

        # Action shortcuts
        self.btn_snap = QPushButton("📸 截图", top_bar)
        self.btn_snap.clicked.connect(self._on_snapshot_clicked)
        top_layout.addWidget(self.btn_snap)

        self.btn_record = QPushButton("⏺ 本地录像", top_bar)
        self.btn_record.clicked.connect(self._on_record_clicked)
        top_layout.addWidget(self.btn_record)

        self.btn_stop_all = QPushButton("⏹ 全部停止", top_bar)
        self.btn_stop_all.clicked.connect(self.stop_all_slots)
        top_layout.addWidget(self.btn_stop_all)

        self.btn_fullscreen = QPushButton("⛶ 全屏显示", top_bar)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        top_layout.addWidget(self.btn_fullscreen)

        self.btn_ptz_toggle = QPushButton("🎮 云台面板", top_bar)
        self.btn_ptz_toggle.setCheckable(True)
        self.btn_ptz_toggle.setChecked(True)
        self.btn_ptz_toggle.toggled.connect(self._toggle_ptz_panel)
        top_layout.addWidget(self.btn_ptz_toggle)

        main_layout.addWidget(top_bar)

        # 2. Main Content (Center Split-Screen Grid + Right PTZ Panel)
        content_splitter = QSplitter(Qt.Horizontal, self)

        # Center Grid Container
        self.grid_container = QWidget(content_splitter)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(2)

        # Pre-create 16 video slot widgets
        for i in range(self.max_slots):
            slot = VideoWidget(slot_id=i, parent=self.grid_container)
            slot.clicked.connect(self._on_slot_clicked)
            slot.double_clicked.connect(self._on_slot_double_clicked)
            slot.close_requested.connect(self._on_slot_close_requested)
            slot.capture_requested.connect(self._on_slot_capture)
            slot.record_toggle_requested.connect(self._on_slot_record_toggle)
            slot.resized.connect(self._on_slot_resized)
            self.video_slots.append(slot)

        content_splitter.addWidget(self.grid_container)

        # Right PTZ Control Panel
        self.ptz_panel = self._create_ptz_panel(content_splitter)
        content_splitter.addWidget(self.ptz_panel)

        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 0)
        main_layout.addWidget(content_splitter, 1)

        # Apply initial 4-screen layout
        self.switch_layout(4)
        self.select_slot(0)

    def _create_ptz_panel(self, parent) -> QWidget:
        panel = QWidget(parent)
        panel.setMaximumWidth(220)
        panel.setMinimumWidth(180)
        panel.setStyleSheet("background-color: #1e222a; border-left: 1px solid #2d3340;")
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(10, 10, 10, 10)
        p_layout.setSpacing(12)

        # Title
        title = QLabel("云台方位控制 (PTZ)", panel)
        title.setStyleSheet("color: #3894ff; font-weight: bold; font-size: 13px;")
        p_layout.addWidget(title)

        # Direction Pad Grid
        dir_group = QGroupBox("方向操控", panel)
        dir_layout = QGridLayout(dir_group)
        dir_layout.setContentsMargins(6, 12, 6, 8)
        dir_layout.setSpacing(4)

        # 8-direction buttons
        btn_ul = self._create_ptz_btn("↖", PTZCommand.UP_LEFT)
        btn_u  = self._create_ptz_btn("↑", PTZCommand.UP)
        btn_ur = self._create_ptz_btn("↗", PTZCommand.UP_RIGHT)
        btn_l  = self._create_ptz_btn("←", PTZCommand.LEFT)
        btn_c  = QPushButton("●", dir_group)
        btn_c.setEnabled(False)
        btn_c.setProperty("class", "ptzBtn")
        btn_r  = self._create_ptz_btn("→", PTZCommand.RIGHT)
        btn_dl = self._create_ptz_btn("↙", PTZCommand.DOWN_LEFT)
        btn_d  = self._create_ptz_btn("↓", PTZCommand.DOWN)
        btn_dr = self._create_ptz_btn("↘", PTZCommand.DOWN_RIGHT)

        dir_layout.addWidget(btn_ul, 0, 0)
        dir_layout.addWidget(btn_u,  0, 1)
        dir_layout.addWidget(btn_ur, 0, 2)
        dir_layout.addWidget(btn_l,  1, 0)
        dir_layout.addWidget(btn_c,  1, 1)
        dir_layout.addWidget(btn_r,  1, 2)
        dir_layout.addWidget(btn_dl, 2, 0)
        dir_layout.addWidget(btn_d,  2, 1)
        dir_layout.addWidget(btn_dr, 2, 2)

        p_layout.addWidget(dir_group)

        # Optics (Zoom, Focus, Iris)
        opt_group = QGroupBox("镜头参数微调", panel)
        opt_layout = QGridLayout(opt_group)
        opt_layout.setContentsMargins(6, 12, 6, 8)
        opt_layout.setSpacing(6)

        btn_zin  = self._create_ptz_btn("放大 +", PTZCommand.ZOOM_IN)
        btn_zout = self._create_ptz_btn("缩小 -", PTZCommand.ZOOM_OUT)
        btn_fnear = self._create_ptz_btn("聚焦 +", PTZCommand.FOCUS_NEAR)
        btn_ffar  = self._create_ptz_btn("聚焦 -", PTZCommand.FOCUS_FAR)
        btn_iopen = self._create_ptz_btn("光圈 +", PTZCommand.IRIS_OPEN)
        btn_iclose = self._create_ptz_btn("光圈 -", PTZCommand.IRIS_CLOSE)

        opt_layout.addWidget(QLabel("变焦:"), 0, 0)
        opt_layout.addWidget(btn_zin, 0, 1)
        opt_layout.addWidget(btn_zout, 0, 2)

        opt_layout.addWidget(QLabel("聚焦:"), 1, 0)
        opt_layout.addWidget(btn_fnear, 1, 1)
        opt_layout.addWidget(btn_ffar, 1, 2)

        opt_layout.addWidget(QLabel("光圈:"), 2, 0)
        opt_layout.addWidget(btn_iopen, 2, 1)
        opt_layout.addWidget(btn_iclose, 2, 2)

        p_layout.addWidget(opt_group)

        # PTZ Speed Slider
        speed_group = QGroupBox("转动速度 (1-7)", panel)
        speed_layout = QVBoxLayout(speed_group)
        speed_layout.setContentsMargins(8, 12, 8, 8)

        self.speed_slider = QSlider(Qt.Horizontal, speed_group)
        self.speed_slider.setRange(1, 7)
        self.speed_slider.setValue(4)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)

        self.lbl_speed_val = QLabel("当前速度: 4", speed_group)
        self.lbl_speed_val.setAlignment(Qt.AlignCenter)
        self.speed_slider.valueChanged.connect(lambda v: self.lbl_speed_val.setText(f"当前速度: {v}"))

        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.lbl_speed_val)
        p_layout.addWidget(speed_group)

        p_layout.addStretch()
        return panel

    def _create_ptz_btn(self, text: str, command: PTZCommand) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "ptzBtn")
        btn.setStyleSheet("QPushButton { font-weight: bold; min-height: 28px; }")

        # Press to start moving, release to stop moving
        btn.pressed.connect(lambda: self._send_ptz_command(command, stop=False))
        btn.released.connect(lambda: self._send_ptz_command(command, stop=True))
        return btn

    def _send_ptz_command(self, command: PTZCommand, stop: bool):
        speed = self.speed_slider.value() if hasattr(self, "speed_slider") else 4
        slot_id = self.active_slot_id
        slot_state = self.player_controller.get_slot_state(slot_id)
        if not (slot_state and slot_state.is_live and slot_state.channel_no > 0):
            # If current active slot is not live, check if any slot is playing live
            for s_id, st in self.player_controller.slots.items():
                if st.is_live and st.channel_no > 0:
                    slot_id = s_id
                    break

        self.player_controller.ptz_control(
            slot_id=slot_id,
            command=command,
            stop=stop,
            speed=speed
        )

    def _toggle_ptz_panel(self, checked: bool):
        self.ptz_panel.setVisible(checked)

    def switch_layout(self, count: int):
        """Switch grid layout: 1, 4, 9, or 16 screens."""
        self.current_layout_count = count
        self.is_single_maximized = False

        # Remove all slots from grid layout without detaching their parent
        for slot in self.video_slots:
            self.grid_layout.removeWidget(slot)
            slot.setVisible(False)

        if count == 1:
            rows, cols = 1, 1
        elif count == 4:
            rows, cols = 2, 2
        elif count == 9:
            rows, cols = 3, 3
        else:
            rows, cols = 4, 4

        for i in range(count):
            r = i // cols
            c = i % cols
            slot = self.video_slots[i]
            self.grid_layout.addWidget(slot, r, c)
            slot.setVisible(True)

        # Ensure active slot is within range
        if self.active_slot_id >= count:
            self.select_slot(0)
        else:
            self.select_slot(self.active_slot_id)

        # Refresh idle slots to clean away any leftover screen artifacts
        for i in range(count):
            slot = self.video_slots[i]
            if not getattr(slot, "is_playing", False):
                slot.refresh_idle_surface()

        # Notify SDK after layout finishes resizing X11 surfaces
        QTimer.singleShot(60, lambda: self._refresh_active_slots(count))
        # If switching to 1-screen, seamlessly reopen slot 0 so it immediately adapts to full-window resolution
        if count == 1:
            QTimer.singleShot(80, lambda: self._reopen_slot_if_playing(0))


    def select_slot(self, slot_id: int):
        """Highlight specified slot."""
        self.active_slot_id = slot_id
        for slot in self.video_slots:
            slot.set_selected(slot.slot_id == slot_id)

    def toggle_fullscreen(self):
        """Toggle fullscreen mode for currently active slot."""
        self._on_slot_double_clicked(self.active_slot_id)

    def _reopen_slot_if_playing(self, slot_id: int):
        """Reopen playing stream on slot to force SDK hardware decoder to re-bind to new dimensions."""
        slot = self.player_controller.get_slot_state(slot_id)
        if slot and slot.is_live:
            w_id = self.video_slots[slot_id].get_win_id()
            self.player_controller.reopen_live_play(slot_id, win_id=w_id)

    def play_channel_in_slot(self, device_id: str, channel_no: int, channel_name: str, slot_id: Optional[int] = None):
        """Start playing channel in the active or specified slot."""
        target_slot_id = slot_id if slot_id is not None else self.active_slot_id
        slot_widget = self.video_slots[target_slot_id]
        win_id = slot_widget.get_win_id()
        stream_type = self.combo_stream.currentData() or 0

        ok = self.player_controller.start_live_play(
            slot_id=target_slot_id,
            device_id=device_id,
            channel_no=channel_no,
            win_id=win_id,
            stream_type=stream_type,
            channel_name=channel_name
        )

        if ok:
            slot_widget.set_stream_info(channel_name, "实时预览中 (主码流)" if stream_type == 0 else "实时预览中 (子码流)")
        else:
            slot_widget.set_stream_info(channel_name, "预览连接失败")

    def _on_slot_clicked(self, slot_id: int):
        self.select_slot(slot_id)

    def _on_slot_double_clicked(self, slot_id: int):
        """Double click to toggle between single-slot maximized and multi-split layout."""
        if self.is_single_maximized:
            # Restore saved layout
            self.switch_layout(self.saved_layout_count)
            self.select_slot(slot_id)
            # Re-open stream at restored geometry
            QTimer.singleShot(80, lambda: self._reopen_slot_if_playing(slot_id))
        else:
            # Maximize this single slot
            self.saved_layout_count = self.current_layout_count
            self.is_single_maximized = True

            for slot in self.video_slots:
                self.grid_layout.removeWidget(slot)
                slot.setVisible(False)

            slot = self.video_slots[slot_id]
            self.grid_layout.addWidget(slot, 0, 0)
            slot.setVisible(True)

            self.select_slot(slot_id)
            # Re-open stream at maximized geometry so decoder scales 100%
            QTimer.singleShot(80, lambda: self._reopen_slot_if_playing(slot_id))

        # Notify SDK that slot dimensions changed (maximize or restore)
        QTimer.singleShot(60, lambda: self._refresh_active_slots(1 if self.is_single_maximized else self.saved_layout_count))

    def _on_slot_resized(self, slot_id: int):
        """Called when a video slot changes size."""
        win_id = self.video_slots[slot_id].get_win_id()
        QTimer.singleShot(80, lambda: self.player_controller.refresh_slot(slot_id, win_id=win_id))

    def _refresh_active_slots(self, count: int):
        """Notify SDK for all currently visible active slots."""
        for i in range(count):
            win_id = self.video_slots[i].get_win_id()
            self.player_controller.refresh_slot(i, win_id=win_id)

    def _on_slot_close_requested(self, slot_id: int):
        self.player_controller.stop_slot(slot_id)
        self.video_slots[slot_id].clear_stream()

    def _on_slot_capture(self, slot_id: int, save_path: str):
        ok = self.player_controller.capture_slot(slot_id, save_path)
        if ok:
            QMessageBox.information(self, "截图成功", f"画面截图已保存至:\n{save_path}")
        else:
            QMessageBox.warning(self, "截图失败", "截图保存失败，请检查通道是否处于活动状态。")

    def _on_slot_record_toggle(self, slot_id: int):
        slot = self.video_slots[slot_id]
        state = self.player_controller.get_slot_state(slot_id)

        if state.is_recording:
            self.player_controller.toggle_record_slot(slot_id, "")
            slot.set_recording(False)
            QMessageBox.information(self, "录像已保存", f"录像已停止并保存至:\n{state.record_path}")
        else:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"record_slot{slot_id + 1}_{now_str}.mp4"
            save_path, _ = QFileDialog.getSaveFileName(self, "保存录像文件", default_name, "MP4 Video (*.mp4)")
            if save_path:
                ok, is_rec = self.player_controller.toggle_record_slot(slot_id, save_path)
                slot.set_recording(is_rec)
                if not ok:
                    QMessageBox.warning(self, "录像失败", "启动本地录像失败。")

    def _on_snapshot_clicked(self):
        slot = self.video_slots[self.active_slot_id]
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"snapshot_slot{self.active_slot_id + 1}_{now_str}.jpg"
        save_path, _ = QFileDialog.getSaveFileName(self, "保存截图", default_name, "JPEG Images (*.jpg)")
        if save_path:
            self._on_slot_capture(self.active_slot_id, save_path)

    def _on_record_clicked(self):
        self._on_slot_record_toggle(self.active_slot_id)

    def stop_all_slots(self):
        for i in range(self.max_slots):
            self.player_controller.stop_slot(i)
            self.video_slots[i].clear_stream()

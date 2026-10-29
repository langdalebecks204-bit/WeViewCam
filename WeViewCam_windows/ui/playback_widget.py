# -*- coding: utf-8 -*-
"""
Recording Playback Widget.
Provides search by device/channel/date, recorded file list, interactive 24h timeline and playback control.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Optional
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QSlider, QFrame, QMessageBox, QFileDialog
)
from ui.video_widget import VideoWidget
from ui.timeline_bar import TimelineBar
from core.player_controller import PlayerController
from core.device_manager import DeviceManager
from core.base_adapter import RecordSegment, PlaybackCommand
from ui.device_tree_widget import icon_online, icon_offline, icon_disconnected


class PlaybackWidget(QWidget):
    """Historical video playback view with date search, list and 24h timeline scrubbing."""

    def __init__(self, player_controller: PlayerController, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.player_controller = player_controller
        self.device_manager = device_manager

        self.playback_slot_id = 99  # Dedicated slot id for playback session
        self.current_records: List[RecordSegment] = []
        self.is_playing = False
        self.is_paused = False
        self.current_speed_mult = 1.0

        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Main horizontal splitter: Left query panel + Right video & timeline
        splitter = QSplitter(Qt.Horizontal, self)

        self.splitter = splitter

        # 1. Left Query & File List Panel
        self.left_panel = QFrame(splitter)
        left_panel = self.left_panel
        self.left_panel.setMinimumWidth(260)
        self.left_panel.setMaximumWidth(320)
        self.left_panel.setStyleSheet("background-color: #1e222a; border-right: 1px solid #2d3340;")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        left_title = QLabel("录像条件检索", left_panel)
        left_title.setStyleSheet("color: #3894ff; font-weight: bold; font-size: 14px;")
        left_layout.addWidget(left_title)

        # Device selector
        left_layout.addWidget(QLabel("选择监控设备:", left_panel))
        self.combo_device = QComboBox(left_panel)
        self.combo_device.currentIndexChanged.connect(self._on_device_changed)
        left_layout.addWidget(self.combo_device)

        # Channel selector
        left_layout.addWidget(QLabel("选择监控通道:", left_panel))
        self.combo_channel = QComboBox(left_panel)
        left_layout.addWidget(self.combo_channel)

        # Date picker
        left_layout.addWidget(QLabel("检索日期:", left_panel))
        self.date_picker = QDateEdit(left_panel)
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(date.today())
        left_layout.addWidget(self.date_picker)

        # Search button
        self.btn_search = QPushButton("🔍 检索历史录像", left_panel)
        self.btn_search.setProperty("class", "primaryBtn")
        self.btn_search.setStyleSheet("background-color: #0e78ff; color: white; font-weight: bold; min-height: 28px;")
        self.btn_search.clicked.connect(self.search_records)
        left_layout.addWidget(self.btn_search)

        left_layout.addSpacing(6)
        left_layout.addWidget(QLabel("录像片段列表 (双击播放):", left_panel))

        # Records Table
        self.record_table = QTableWidget(left_panel)
        self.record_table.setColumnCount(3)
        self.record_table.setHorizontalHeaderLabels(["开始时间", "结束时间", "大小(MB)"])
        self.record_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.record_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.record_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.record_table.itemDoubleClicked.connect(self._on_table_row_double_clicked)
        left_layout.addWidget(self.record_table, 1)

        splitter.addWidget(left_panel)

        # 2. Right Video & Timeline Area
        right_panel = QWidget(splitter)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        # Video Viewport
        self.video_slot = VideoWidget(slot_id=self.playback_slot_id, parent=right_panel)
        self.video_slot.title_label.setText("录像回放窗口")
        self.video_slot.status_label.setText("未开始回放")
        self.video_slot.double_clicked.connect(self._toggle_fullscreen_playback)
        self.video_slot.resized.connect(
            lambda sid: QTimer.singleShot(80, lambda: self.player_controller.refresh_slot(sid, win_id=self.video_slot.get_win_id()))
        )
        right_layout.addWidget(self.video_slot, 1)

        # Timeline Zoom Bar
        zoom_bar = QHBoxLayout()
        zoom_bar.setContentsMargins(6, 0, 6, 0)
        lbl_zoom = QLabel("时间轴精度:", right_panel)
        lbl_zoom.setStyleSheet("color: #8b949e; font-size: 12px;")
        zoom_bar.addWidget(lbl_zoom)

        for text, hours in [("24小时", 24.0), ("12小时", 12.0), ("4小时", 4.0), ("1小时", 1.0)]:
            btn = QPushButton(text, right_panel)
            btn.setFixedSize(60, 22)
            btn.setStyleSheet("font-size: 11px; padding: 0;")
            btn.clicked.connect(lambda _, h=hours: self.timeline.set_zoom_duration(h))
            zoom_bar.addWidget(btn)

        zoom_bar.addStretch()
        self.lbl_time_display = QLabel("当前时间: 00:00:00", right_panel)
        self.lbl_time_display.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 13px;")
        zoom_bar.addWidget(self.lbl_time_display)

        right_layout.addLayout(zoom_bar)

        # 24-hour interactive timeline
        self.timeline = TimelineBar(right_panel)
        self.timeline.time_selected.connect(self._on_timeline_time_selected)
        right_layout.addWidget(self.timeline)

        # Playback Control Bar
        ctrl_bar = QFrame(right_panel)
        ctrl_bar.setStyleSheet("background-color: #1f232c; border-radius: 4px; padding: 4px;")
        ctrl_layout = QHBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)
        ctrl_layout.setSpacing(10)

        self.btn_play = QPushButton("▶ 播放", ctrl_bar)
        self.btn_play.setMinimumWidth(70)
        self.btn_play.setStyleSheet("background-color: #238636; color: white; font-weight: bold;")
        self.btn_play.clicked.connect(self._toggle_play_pause)
        ctrl_layout.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹ 停止", ctrl_bar)
        self.btn_stop.clicked.connect(self.stop_playback)
        ctrl_layout.addWidget(self.btn_stop)

        self.btn_slow = QPushButton("◀◀ 慢放", ctrl_bar)
        self.btn_slow.clicked.connect(self._slow_down)
        ctrl_layout.addWidget(self.btn_slow)

        self.btn_normal = QPushButton("1x 正常", ctrl_bar)
        self.btn_normal.clicked.connect(self._normal_speed)
        ctrl_layout.addWidget(self.btn_normal)

        self.btn_fast = QPushButton("▶▶ 快放", ctrl_bar)
        self.btn_fast.clicked.connect(self._speed_up)
        ctrl_layout.addWidget(self.btn_fast)

        self.btn_step = QPushButton("⏯ 单帧", ctrl_bar)
        self.btn_step.clicked.connect(self._step_frame)
        ctrl_layout.addWidget(self.btn_step)

        ctrl_layout.addSpacing(12)

        # Progress slider
        self.slider_pos = QSlider(Qt.Horizontal, ctrl_bar)
        self.slider_pos.setRange(0, 100)
        self.slider_pos.sliderMoved.connect(self._on_slider_moved)
        ctrl_layout.addWidget(self.slider_pos, 1)

        self.lbl_speed = QLabel("倍速: 1x", ctrl_bar)
        self.lbl_speed.setStyleSheet("color: #3894ff; font-weight: bold;")
        ctrl_layout.addWidget(self.lbl_speed)

        # Snapshot & download
        self.btn_snap = QPushButton("📸 截取画面", ctrl_bar)
        self.btn_snap.clicked.connect(self._snapshot)
        ctrl_layout.addWidget(self.btn_snap)

        # Fullscreen toggle button
        self.btn_fullscreen = QPushButton("⛶ 全屏", ctrl_bar)
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen_playback)
        ctrl_layout.addWidget(self.btn_fullscreen)

        right_layout.addWidget(ctrl_bar)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

        self.refresh_devices_combo()

    def _init_timer(self):
        """Timer to tick playback time and update slider."""
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(1000)
        self.play_timer.timeout.connect(self._on_timer_tick)

    def refresh_devices_combo(self):
        """Update device dropdown from DeviceManager."""
        self.combo_device.clear()
        devices = self.device_manager.list_devices()
        for dev in devices:
            icon = icon_online() if dev.is_connected else icon_disconnected()
            self.combo_device.addItem(icon, f"{dev.name} ({dev.ip})", dev.device_id)

    def _on_device_changed(self, index: int):
        self.combo_channel.clear()
        dev_id = self.combo_device.currentData()
        if not dev_id:
            return

        dev = self.device_manager.get_device(dev_id)
        if not dev:
            return

        channels = dev.channels
        if not channels:
            adapter = self.device_manager.get_adapter(dev_id)
            if adapter:
                channels = adapter.get_channels()
                dev.channels = channels

        for ch in channels:
            icon = icon_online() if ch.is_online else icon_offline()
            st_suffix = "" if ch.is_online else " [离线]"
            self.combo_channel.addItem(icon, f"{ch.name} (CH{ch.channel_no}){st_suffix}", ch.channel_no)

    def search_records(self):
        """Execute record search for selected channel and date."""
        dev_id = self.combo_device.currentData()
        ch_no = self.combo_channel.currentData()
        if not dev_id or ch_no is None:
            QMessageBox.warning(self, "提示", "请先选择设备和监控通道！")
            return

        target_date = self.date_picker.date().toPyDate()
        start_time = datetime.combine(target_date, time(0, 0, 0))
        end_time = datetime.combine(target_date, time(23, 59, 59))

        adapter = self.device_manager.get_adapter(dev_id)
        if not adapter:
            return

        self.btn_search.setEnabled(False)
        self.btn_search.setText("正在检索...")

        records = adapter.find_records(ch_no, start_time, end_time)

        self.btn_search.setEnabled(True)
        self.btn_search.setText("🔍 检索历史录像")

        self.current_records = records
        self.timeline.set_date(target_date)
        self.timeline.set_records(records)

        # Fill table
        self.record_table.setRowCount(len(records))
        for row, r in enumerate(records):
            s_str = r.start_time.strftime("%H:%M:%S")
            e_str = r.end_time.strftime("%H:%M:%S")
            size_mb = f"{r.file_size / (1024 * 1024):.1f}"

            self.record_table.setItem(row, 0, QTableWidgetItem(s_str))
            self.record_table.setItem(row, 1, QTableWidgetItem(e_str))
            self.record_table.setItem(row, 2, QTableWidgetItem(size_mb))

        if not records:
            QMessageBox.information(self, "提示", f"未检索到 {target_date} 的录像数据。")

    def _on_table_row_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        if 0 <= row < len(self.current_records):
            seg = self.current_records[row]
            self.start_playback_at(seg.start_time)

    def _on_timeline_time_selected(self, target_dt: datetime):
        self.lbl_time_display.setText(f"当前时间: {target_dt.strftime('%H:%M:%S')}")
        self.start_playback_at(target_dt)

    def start_playback_at(self, target_time: datetime):
        """Start playback at specific time."""
        dev_id = self.combo_device.currentData()
        ch_no = self.combo_channel.currentData()
        ch_name = self.combo_channel.currentText()
        if not dev_id or ch_no is None:
            return

        end_time = datetime.combine(target_time.date(), time(23, 59, 59))
        win_id = self.video_slot.get_win_id()

        ok = self.player_controller.start_playback(
            slot_id=self.playback_slot_id,
            device_id=dev_id,
            channel_no=ch_no,
            start_time=target_time,
            end_time=end_time,
            win_id=win_id,
            channel_name=ch_name
        )

        if ok:
            self.is_playing = True
            self.is_paused = False
            self.btn_play.setText("⏸ 暂停")
            self.btn_play.setStyleSheet("background-color: #d29922; color: white; font-weight: bold;")
            self.video_slot.set_stream_info(ch_name, f"回放中 ({target_time.strftime('%H:%M:%S')})")
            self.timeline.set_current_time(target_time)
            self.play_timer.start()
        else:
            self.video_slot.set_stream_info(ch_name, "回放开启失败")

    def _toggle_play_pause(self):
        if not self.is_playing:
            # Try start from timeline current time
            self.start_playback_at(self.timeline._current_time)
            return

        if self.is_paused:
            # Resume
            self.player_controller.control_playback(self.playback_slot_id, PlaybackCommand.RESTART)
            self.is_paused = False
            self.btn_play.setText("⏸ 暂停")
            self.btn_play.setStyleSheet("background-color: #d29922; color: white; font-weight: bold;")
            self.play_timer.start()
        else:
            # Pause
            self.player_controller.control_playback(self.playback_slot_id, PlaybackCommand.PAUSE)
            self.is_paused = True
            self.btn_play.setText("▶ 继续")
            self.btn_play.setStyleSheet("background-color: #238636; color: white; font-weight: bold;")
            self.play_timer.stop()

    def stop_playback(self):
        self.player_controller.stop_slot(self.playback_slot_id)
        self.video_slot.clear_stream()
        self.is_playing = False
        self.is_paused = False
        self.btn_play.setText("▶ 播放")
        self.btn_play.setStyleSheet("background-color: #238636; color: white; font-weight: bold;")
        self.play_timer.stop()
        self.slider_pos.setValue(0)

    def _speed_up(self):
        if not self.is_playing:
            return
        self.player_controller.control_playback(self.playback_slot_id, PlaybackCommand.FAST)
        self.current_speed_mult = min(16.0, self.current_speed_mult * 2)
        self.lbl_speed.setText(f"倍速: {self.current_speed_mult:g}x")

    def _slow_down(self):
        if not self.is_playing:
            return
        self.player_controller.control_playback(self.playback_slot_id, PlaybackCommand.SLOW)
        self.current_speed_mult = max(0.125, self.current_speed_mult / 2)
        self.lbl_speed.setText(f"倍速: {self.current_speed_mult:g}x")

    def _normal_speed(self):
        if not self.is_playing:
            return
        self.player_controller.control_playback(self.playback_slot_id, PlaybackCommand.NORMAL)
        self.current_speed_mult = 1.0
        self.lbl_speed.setText("倍速: 1x")

    def _step_frame(self):
        if not self.is_playing:
            return
        self.player_controller.control_playback(self.playback_slot_id, PlaybackCommand.STEP_FRAME)

    def _on_slider_moved(self, pos: int):
        if self.is_playing:
            self.player_controller.control_playback(self.playback_slot_id, PlaybackCommand.SET_POS, pos)

    def _on_timer_tick(self):
        if self.is_playing and not self.is_paused:
            # Advance playback needle by current speed
            next_time = self.timeline._current_time + timedelta(seconds=1 * self.current_speed_mult)
            self.timeline.set_current_time(next_time)
            self.lbl_time_display.setText(f"当前时间: {next_time.strftime('%H:%M:%S')}")

            # Query real pos from SDK
            pos = self.player_controller.get_playback_pos(self.playback_slot_id)
            if pos > 0:
                self.slider_pos.setValue(pos)

    def _snapshot(self):
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"playback_snap_{now_str}.jpg"
        save_path, _ = QFileDialog.getSaveFileName(self, "保存截图", default_name, "JPEG Images (*.jpg)")
        if save_path:
            ok = self.player_controller.capture_slot(self.playback_slot_id, save_path)
            if ok:
                QMessageBox.information(self, "截图成功", f"画面已保存至:\n{save_path}")
            else:
                QMessageBox.warning(self, "截图失败", "截图保存失败。")

    def _toggle_fullscreen_playback(self):
        """Toggle fullscreen mode for playback video slot."""
        self.is_fullscreen = not getattr(self, "is_fullscreen", False)
        self.left_panel.setVisible(not self.is_fullscreen)
        if hasattr(self, "btn_fullscreen"):
            self.btn_fullscreen.setText("⛶ 还原" if self.is_fullscreen else "⛶ 全屏")

        def _reopen_or_refresh():
            w_id = self.video_slot.get_win_id()
            if self.is_playing:
                cur_t = self.timeline._current_time
                self.player_controller.reopen_playback(self.playback_slot_id, current_time=cur_t, win_id=w_id)
            else:
                self.player_controller.refresh_slot(self.playback_slot_id, win_id=w_id)

        QTimer.singleShot(80, _reopen_or_refresh)


# -*- coding: utf-8 -*-
"""
Single Video Tile Widget.
Hosts native X11 window surface for direct hardware rendering, OSD overlay, and user interaction.
"""

import os
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMenu, QWidget, QSizePolicy, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QMouseEvent, QColor, QPalette, QPainter, QFont, QImage


class VideoSurface(QWidget):
    """
    Dedicated video rendering surface widget.
    Hosts native X11 window (winId) for SDK direct hardware rendering.
    Also supports direct QImage frame rendering for OpenCV/pure-Python fallback decoding.
    """
    def __init__(self, slot_id: int, parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self._is_playing = False
        self._current_frame = None

        # Native X11 window for SDK direct hardware rendering
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAutoFillBackground(True)

        p = self.palette()
        p.setColor(QPalette.Window, QColor(10, 12, 16))
        self.setPalette(p)
        self.setStyleSheet("background-color: #0a0c10;")

        # Auto register to RtspPlayerManager for software/OpenCV rendering fallback
        try:
            from adapters.onvif.player import RtspPlayerManager
            RtspPlayerManager.register_window_surface(int(self.winId()), self.update_frame)
        except Exception:
            pass

    def update_frame(self, q_img: QImage):
        """Called by software/OpenCV RTSP decoding thread to present new video frame."""
        self._current_frame = q_img
        self.update()

    def set_playing(self, playing: bool):
        self._is_playing = playing
        self.setAttribute(Qt.WA_OpaquePaintEvent, playing)
        if not playing:
            self._current_frame = None
            self.update()
            self.repaint()

    def paintEvent(self, event):
        # 1. If we have active software/OpenCV decoded frames, paint frame keeping aspect ratio
        if self._current_frame is not None and self._is_playing:
            painter = QPainter(self)
            rect = self.rect()
            painter.fillRect(rect, QColor(10, 12, 16))
            scaled_img = self._current_frame.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (rect.width() - scaled_img.width()) // 2
            y = (rect.height() - scaled_img.height()) // 2
            painter.drawImage(x, y, scaled_img)
            painter.end()
            return

        # 2. If idle, draw placeholder
        if not self._is_playing:
            painter = QPainter(self)
            rect = self.rect()
            # Clean dark background to erase any previous artifacts completely
            painter.fillRect(rect, QColor(10, 12, 16))

            # Draw subtle placeholder for idle slot
            w, h = rect.width(), rect.height()
            if w > 70 and h > 50:
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setPen(QColor(80, 88, 102, 140))
                font = painter.font()
                font.setPointSize(10)
                font.setWeight(QFont.Medium)
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, f"视口 {self.slot_id + 1}\n(空闲)")
            painter.end()
        else:
            # 3. For hardware rendering (VLC / Hikvision C SDK direct X11 output), leave window unpainted
            event.accept()


class VideoWidget(QFrame):
    """Interactive video slot supporting native SDK HW rendering and OSD overlay."""

    clicked = pyqtSignal(int)           # Emits slot_id
    double_clicked = pyqtSignal(int)    # Emits slot_id for maximize/restore
    close_requested = pyqtSignal(int)   # Emits slot_id to close stream
    capture_requested = pyqtSignal(int, str)  # slot_id, save_path
    record_toggle_requested = pyqtSignal(int) # slot_id
    resized = pyqtSignal(int)                 # Emits slot_id when resized


    def __init__(self, slot_id: int, parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.is_playing = False
        self._is_selected = False
        self._is_recording = False
        self._channel_name = ""
        self._status_text = "空闲"

        self.setObjectName("videoSlot")
        self.setProperty("class", "videoSlot")
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(160, 120)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        # 1. Top OSD Bar
        self.top_osd = QFrame(self)
        self.top_osd.setStyleSheet("background-color: rgba(15, 18, 24, 0.75); min-height: 24px;")
        top_layout = QHBoxLayout(self.top_osd)
        top_layout.setContentsMargins(6, 2, 6, 2)
        top_layout.setSpacing(6)

        # Recording dot
        self.rec_dot = QLabel("● REC", self.top_osd)
        self.rec_dot.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 11px;")
        self.rec_dot.setVisible(False)
        top_layout.addWidget(self.rec_dot)

        # Channel name
        self.title_label = QLabel(f"窗口 {self.slot_id + 1}", self.top_osd)
        self.title_label.setStyleSheet("color: #e6edf3; font-weight: 500; font-size: 12px;")
        top_layout.addWidget(self.title_label)

        top_layout.addStretch()

        # Slot close button
        self.btn_close = QPushButton("✕", self.top_osd)
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setStyleSheet(
            "QPushButton { background: transparent; color: #8b949e; border: none; font-size: 11px; } "
            "QPushButton:hover { color: #f85149; background: rgba(255,255,255,0.1); border-radius: 2px; }"
        )
        self.btn_close.clicked.connect(lambda: self.close_requested.emit(self.slot_id))
        top_layout.addWidget(self.btn_close)

        main_layout.addWidget(self.top_osd)

        # 2. Native Video Surface (Hosts X11 winId for SDK HW acceleration, clean auto-erase)
        self.surface = VideoSurface(slot_id=self.slot_id, parent=self)
        self.surface.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.surface, 1)

        # 3. Bottom Status Bar (OSD)
        self.bottom_osd = QFrame(self)
        self.bottom_osd.setStyleSheet("background-color: rgba(15, 18, 24, 0.75); min-height: 20px;")
        bottom_layout = QHBoxLayout(self.bottom_osd)
        bottom_layout.setContentsMargins(6, 1, 6, 1)

        self.status_label = QLabel("无信号", self.bottom_osd)
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        bottom_layout.addWidget(self.status_label)

        bottom_layout.addStretch()

        self.fps_label = QLabel("", self.bottom_osd)
        self.fps_label.setStyleSheet("color: #58a6ff; font-size: 11px;")
        bottom_layout.addWidget(self.fps_label)

        main_layout.addWidget(self.bottom_osd)

    def get_win_id(self) -> int:
        """Returns the native X11 window id of the inner video surface."""
        w_id = int(self.surface.winId())
        try:
            from adapters.onvif.player import RtspPlayerManager
            RtspPlayerManager.register_window_surface(w_id, self.surface.update_frame)
        except Exception:
            pass
        return w_id

    def set_selected(self, selected: bool):
        """Set visual highlight border."""
        self._is_selected = selected
        if selected:
            self.setStyleSheet(
                "QFrame#videoSlot { border: 2px solid #3894ff; background-color: #0d1117; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#videoSlot { border: 1px solid #232731; background-color: #0b0c0e; }"
            )

    def set_stream_info(self, channel_name: str, status: str = "预览中"):
        self.is_playing = True
        self._channel_name = channel_name
        self.title_label.setText(channel_name if channel_name else f"窗口 {self.slot_id + 1}")
        self.status_label.setText(status)
        self.status_label.setStyleSheet("color: #3fb950; font-size: 11px;")
        self.surface.set_playing(True)

    def set_recording(self, is_recording: bool):
        self._is_recording = is_recording
        self.rec_dot.setVisible(is_recording)

    def clear_stream(self):
        self.is_playing = False
        self._channel_name = ""
        self._is_recording = False
        self.rec_dot.setVisible(False)
        self.title_label.setText(f"窗口 {self.slot_id + 1}")
        self.status_label.setText("空闲")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.fps_label.setText("")
        # Force surface redraw to clean dark background
        self.surface.set_playing(False)

    def refresh_idle_surface(self):
        """Force clean repaint of idle surface on layout switch or window resize."""
        if not self.is_playing:
            self.surface.set_playing(False)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot_id)
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.is_playing:
            self.surface.update()
            self.surface.repaint()
        self.resized.emit(self.slot_id)


    def mouseDoubleClickEvent(self, event: QMouseEvent):

        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.slot_id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; }")

        act_snap = menu.addAction("📸 单帧抓图")
        act_rec = menu.addAction("⏹ 停止录像" if self._is_recording else "⏺ 开始录像")
        menu.addSeparator()
        act_close = menu.addAction("✕ 关闭视口")

        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == act_snap:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"snapshot_slot{self.slot_id + 1}_{now_str}.jpg"
            save_path, _ = QFileDialog.getSaveFileName(self, "保存截图", default_name, "JPEG Images (*.jpg)")
            if save_path:
                self.capture_requested.emit(self.slot_id, save_path)
        elif action == act_rec:
            self.record_toggle_requested.emit(self.slot_id)
        elif action == act_close:
            self.close_requested.emit(self.slot_id)

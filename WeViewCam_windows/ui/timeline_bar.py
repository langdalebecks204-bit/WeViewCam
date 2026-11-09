# -*- coding: utf-8 -*-
"""
Interactive 24-Hour Surveillance Timeline Bar.
Features:
- Full day or zoomed time ruler with custom ticks.
- Color-coded recording segments (schedule, motion, alarm).
- Interactive scrubbing cursor (click & drag to seek).
- Mouse wheel zooming centered on hover time.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Optional
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPolygonF,
    QMouseEvent, QWheelEvent, QPaintEvent
)
from core.base_adapter import RecordSegment


class TimelineBar(QWidget):
    """Custom high-precision timeline widget for NVR recording playback."""

    # Emitted when user clicks or drags the time cursor
    time_selected = pyqtSignal(datetime)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(65)
        self.setMaximumHeight(80)
        self.setMouseTracking(True)

        # Selected calendar date
        self._target_date = date.today()
        # Viewport visible range (in seconds offset from 00:00:00 of the day)
        self._view_start_sec = 0.0          # 00:00:00
        self._view_duration_sec = 86400.0   # 24 hours = 86400 seconds

        # Current playback position
        self._current_time: datetime = datetime.combine(self._target_date, time(0, 0, 0))

        # Recorded segments
        self._segments: List[RecordSegment] = []

        # Mouse interaction state
        self._is_dragging = False

        # Colors
        self.bg_color = QColor("#161b22")
        self.ruler_bg = QColor("#21262d")
        self.tick_color = QColor("#8b949e")
        self.text_color = QColor("#c9d1d9")
        self.record_color = QColor(46, 160, 67, 210)  # Green with alpha
        self.needle_color = QColor("#ff4d4f")

    def set_date(self, target_date: date):
        """Switch timeline day and reset zoom to full 24 hours."""
        self._target_date = target_date
        self._view_start_sec = 0.0
        self._view_duration_sec = 86400.0
        self._current_time = datetime.combine(self._target_date, time(0, 0, 0))
        self.update()

    def set_records(self, segments: List[RecordSegment]):
        """Load recording segments for display."""
        self._segments = segments
        self.update()

    def set_current_time(self, dt: datetime):
        """Update active playback needle time."""
        self._current_time = dt
        self.update()

    def set_zoom_duration(self, hours: float):
        """Set visible zoom duration in hours (e.g. 24, 12, 4, 1)."""
        duration = hours * 3600.0
        # Center zoom around current playback time
        current_offset = (self._current_time - datetime.combine(self._target_date, time(0, 0))).total_seconds()
        self._view_duration_sec = max(600.0, min(86400.0, duration))
        self._view_start_sec = max(0.0, min(86400.0 - self._view_duration_sec, current_offset - self._view_duration_sec / 2.0))
        self.update()

    def _sec_to_x(self, sec_offset: float, width: float) -> float:
        """Convert second offset from day start to pixel X."""
        fraction = (sec_offset - self._view_start_sec) / self._view_duration_sec
        return fraction * width

    def _x_to_sec(self, x: float, width: float) -> float:
        """Convert pixel X to second offset from day start."""
        fraction = max(0.0, min(1.0, x / width))
        return self._view_start_sec + fraction * self._view_duration_sec

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        ruler_h = 24
        track_h = h - ruler_h

        # 1. Backgrounds
        painter.fillRect(0, 0, w, ruler_h, self.ruler_bg)
        painter.fillRect(0, ruler_h, w, track_h, self.bg_color)

        # 2. Draw Recorded Segments
        base_day_dt = datetime.combine(self._target_date, time(0, 0))
        for seg in self._segments:
            seg_start_sec = max(0.0, (seg.start_time - base_day_dt).total_seconds())
            seg_end_sec = min(86400.0, (seg.end_time - base_day_dt).total_seconds())

            if seg_end_sec < self._view_start_sec or seg_start_sec > (self._view_start_sec + self._view_duration_sec):
                continue

            x1 = self._sec_to_x(seg_start_sec, w)
            x2 = self._sec_to_x(seg_end_sec, w)
            seg_w = max(2.0, x2 - x1)

            rect = QRectF(x1, ruler_h + 4, seg_w, track_h - 8)
            painter.fillRect(rect, self.record_color)
            painter.setPen(QPen(QColor("#3fb950"), 1))
            painter.drawRect(rect)

        # 3. Draw Time Scale / Ruler
        painter.setPen(QPen(self.tick_color, 1))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        # Determine tick step based on zoom duration
        if self._view_duration_sec > 43200:   # > 12h
            major_step = 3600 * 2  # 2 hours
            minor_step = 3600      # 1 hour
        elif self._view_duration_sec > 14400: # > 4h
            major_step = 3600      # 1 hour
            minor_step = 1800      # 30 min
        elif self._view_duration_sec > 3600:  # > 1h
            major_step = 1800      # 30 min
            minor_step = 600       # 10 min
        else:
            major_step = 600       # 10 min
            minor_step = 60        # 1 min

        start_sec_aligned = int(self._view_start_sec // minor_step) * minor_step
        end_sec = self._view_start_sec + self._view_duration_sec

        current_sec = start_sec_aligned
        while current_sec <= end_sec:
            if current_sec >= self._view_start_sec:
                x = self._sec_to_x(current_sec, w)
                is_major = (current_sec % major_step == 0)

                if is_major:
                    painter.setPen(QPen(self.tick_color, 1.2))
                    painter.drawLine(QPointF(x, ruler_h - 10), QPointF(x, ruler_h))
                    
                    # Format time label HH:MM
                    hh = int(current_sec // 3600) % 24
                    mm = int((current_sec % 3600) // 60)
                    time_str = f"{hh:02d}:{mm:02d}"
                    painter.setPen(self.text_color)
                    painter.drawText(QRectF(x - 25, 2, 50, 14), Qt.AlignCenter, time_str)
                else:
                    painter.setPen(QPen(QColor("#484f58"), 1))
                    painter.drawLine(QPointF(x, ruler_h - 5), QPointF(x, ruler_h))

            current_sec += minor_step

        # Separator line between ruler and track
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.drawLine(0, ruler_h, w, ruler_h)

        # 4. Playback Needle (Cursor)
        curr_offset = (self._current_time - base_day_dt).total_seconds()
        if self._view_start_sec <= curr_offset <= (self._view_start_sec + self._view_duration_sec):
            needle_x = self._sec_to_x(curr_offset, w)

            # Red vertical line
            painter.setPen(QPen(self.needle_color, 1.5))
            painter.drawLine(QPointF(needle_x, 0), QPointF(needle_x, h))

            # Inverted red triangle indicator at top
            painter.setBrush(QBrush(self.needle_color))
            triangle = QPolygonF([
                QPointF(needle_x - 5, 0),
                QPointF(needle_x + 5, 0),
                QPointF(needle_x, 7)
            ])
            painter.drawPolygon(triangle)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._seek_to_mouse(event.x())

    def mouseMoveEvent(self, event: QMouseEvent):
        sec = self._x_to_sec(event.x(), self.width())
        hover_dt = datetime.combine(self._target_date, time(0, 0)) + timedelta(seconds=sec)
        
        # Tooltip display
        QToolTip.showText(
            self.mapToGlobal(event.pos()),
            hover_dt.strftime("%H:%M:%S"),
            self
        )

        if self._is_dragging:
            self._seek_to_mouse(event.x())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False

    def wheelEvent(self, event: QWheelEvent):
        """Zoom in / zoom out centered on cursor position."""
        angle = event.angleDelta().y()
        zoom_factor = 0.8 if angle > 0 else 1.25

        cursor_sec = self._x_to_sec(event.x(), self.width())
        new_duration = max(600.0, min(86400.0, self._view_duration_sec * zoom_factor))

        fraction = event.x() / max(1.0, float(self.width()))
        new_start = cursor_sec - fraction * new_duration
        new_start = max(0.0, min(86400.0 - new_duration, new_start))

        self._view_duration_sec = new_duration
        self._view_start_sec = new_start
        self.update()

    def _seek_to_mouse(self, x: float):
        sec = self._x_to_sec(x, self.width())
        target_dt = datetime.combine(self._target_date, time(0, 0)) + timedelta(seconds=sec)
        self._current_time = target_dt
        self.update()
        self.time_selected.emit(target_dt)

# -*- coding: utf-8 -*-
"""
Device & Channel Navigation Tree.
Lists configured devices and their camera channels with quick double-click-to-play support.
"""

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMenu, QMessageBox
)
from PyQt5.QtGui import QIcon, QColor, QBrush, QPixmap, QPainter, QPen
from core.base_adapter import DeviceInfo, ChannelInfo, ProtocolType
from core.device_manager import DeviceManager


_STATUS_ICONS = {}


def get_status_icon(color_hex: str, size: int = 14) -> QIcon:
    """Create or return cached high-DPI crisp circular status badge icon."""
    key = (color_hex, size)
    if key in _STATUS_ICONS:
        return _STATUS_ICONS[key]

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Outer border
    pen = QPen(QColor(color_hex).darker(115))
    pen.setWidthF(1.2)
    painter.setPen(pen)

    # Circle fill
    painter.setBrush(QBrush(QColor(color_hex)))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()

    icon = QIcon(pixmap)
    _STATUS_ICONS[key] = icon
    return icon


def icon_online() -> QIcon:
    return get_status_icon("#2ea043", 14)       # 鲜艳绿色


def icon_offline() -> QIcon:
    return get_status_icon("#da3633", 14)      # 鲜艳红色


def icon_disconnected() -> QIcon:
    return get_status_icon("#8b949e", 14) # 灰色


class DeviceTreeWidget(QWidget):
    """Sidebar tree view of surveillance devices and camera channels."""

    channel_double_clicked = pyqtSignal(str, int, str)  # device_id, channel_no, channel_name
    add_device_requested = pyqtSignal()
    edit_device_requested = pyqtSignal(str)              # device_id
    delete_device_requested = pyqtSignal(str)            # device_id

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 6, 8, 4)

        title = QLabel("设备资源列表", self)
        title.setStyleSheet("font-weight: bold; color: #a0aab8; font-size: 13px;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_add = QPushButton("＋", self)
        btn_add.setFixedSize(24, 24)
        btn_add.setToolTip("添加新设备")
        btn_add.setStyleSheet("QPushButton { font-weight: bold; font-size: 14px; padding: 0; }")
        btn_add.clicked.connect(self.add_device_requested.emit)
        header_layout.addWidget(btn_add)

        btn_refresh = QPushButton("↻", self)
        btn_refresh.setFixedSize(24, 24)
        btn_refresh.setToolTip("刷新设备列表与状态")
        btn_refresh.setStyleSheet("QPushButton { font-size: 14px; padding: 0; }")
        btn_refresh.clicked.connect(self.refresh_devices)
        header_layout.addWidget(btn_refresh)

        layout.addLayout(header_layout)

        # Tree Widget
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIconSize(QSize(14, 14))
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        self.refresh_devices()

    def refresh_devices(self):
        """Populate tree with current devices and channels."""
        self.tree.clear()
        devices = self.device_manager.list_devices()

        for dev in devices:
            # Device root item
            dev_item = QTreeWidgetItem(self.tree)
            proto_name = {
                ProtocolType.HIKVISION: "海康",
                ProtocolType.DAHUA: "大华",
                ProtocolType.ONVIF: "ONVIF",
                ProtocolType.CUSTOM_RTSP: "RTSP"
            }.get(dev.protocol, "海康")

            dev_item.setIcon(0, icon_online() if dev.is_connected else icon_disconnected())
            ch_summary = ""
            if dev.channels:
                online_cnt = sum(1 for c in dev.channels if c.is_online)
                ch_summary = f" [{online_cnt}/{len(dev.channels)} 在线]"
            dev_item.setText(0, f"[{proto_name}] {dev.name} ({dev.ip}){ch_summary}")
            dev_item.setData(0, Qt.UserRole, {"type": "device", "device_id": dev.device_id})
            dev_item.setExpanded(True)

            # Channels
            channels = dev.channels
            if not channels and dev.is_connected:
                # If connected but no channels cached, try query
                adapter = self.device_manager.get_adapter(dev.device_id)
                if adapter:
                    channels = adapter.get_channels()
                    dev.channels = channels

            if channels:
                for ch in channels:
                    ch_item = QTreeWidgetItem(dev_item)
                    if ch.is_online:
                        ch_item.setIcon(0, icon_online())
                        st_suffix = ""
                        ch_item.setForeground(0, QBrush(QColor("#e6edf3")))
                    else:
                        ch_item.setIcon(0, icon_offline())
                        st_suffix = " [离线]"
                        ch_item.setForeground(0, QBrush(QColor("#8b949e")))

                    ch_item.setText(0, f"{ch.name} (CH{ch.channel_no}){st_suffix}")
                    ch_item.setData(0, Qt.UserRole, {
                        "type": "channel",
                        "device_id": dev.device_id,
                        "channel_no": ch.channel_no,
                        "channel_name": ch.name,
                        "is_online": ch.is_online
                    })
            else:
                empty_item = QTreeWidgetItem(dev_item)
                empty_item.setIcon(0, icon_disconnected())
                empty_item.setText(0, "(双击设备连接获取通道)")
                empty_item.setForeground(0, QBrush(QColor("#7d8590")))
                empty_item.setData(0, Qt.UserRole, {"type": "hint", "device_id": dev.device_id})

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data.get("type")
        if item_type == "channel":
            self.channel_double_clicked.emit(
                data["device_id"],
                data["channel_no"],
                data["channel_name"]
            )
        elif item_type in ("device", "hint"):
            # Connect device and expand
            dev_id = data["device_id"]
            if not self.device_manager.get_device(dev_id).is_connected:
                self.device_manager.connect_device(dev_id)
                self.refresh_devices()

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data.get("type")
        device_id = data.get("device_id")

        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; }")

        if item_type == "device":
            dev = self.device_manager.get_device(device_id)
            if dev and dev.is_connected:
                act_conn = menu.addAction("🔌 断开连接")
                act_conn.triggered.connect(lambda: self._toggle_connect(device_id, False))
            else:
                act_conn = menu.addAction("⚡ 连接设备")
                act_conn.triggered.connect(lambda: self._toggle_connect(device_id, True))

            menu.addSeparator()
            act_refresh = menu.addAction("🔄 刷新通道状态")
            act_refresh.triggered.connect(lambda: self._refresh_device_channels(device_id))

            menu.addSeparator()
            act_edit = menu.addAction("✏️ 编辑设备")
            act_edit.triggered.connect(lambda: self.edit_device_requested.emit(device_id))

            act_del = menu.addAction("🗑️ 删除设备")
            act_del.triggered.connect(lambda: self._confirm_delete(device_id))

        elif item_type == "channel":
            act_play = menu.addAction("▶️ 在当前选定窗口播放")
            act_play.triggered.connect(lambda: self.channel_double_clicked.emit(
                data["device_id"],
                data["channel_no"],
                data["channel_name"]
            ))

        menu.exec_(self.tree.mapToGlobal(pos))

    def _refresh_device_channels(self, device_id: str):
        dev = self.device_manager.get_device(device_id)
        if not dev:
            return
        if not dev.is_connected:
            self.device_manager.connect_device(device_id)
        else:
            adapter = self.device_manager.get_adapter(device_id)
            if adapter:
                dev.channels = adapter.get_channels()
        self.refresh_devices()

    def _toggle_connect(self, device_id: str, connect: bool):
        if connect:
            self.device_manager.connect_device(device_id)
        else:
            self.device_manager.disconnect_device(device_id)
        self.refresh_devices()

    def _confirm_delete(self, device_id: str):
        dev = self.device_manager.get_device(device_id)
        name = dev.name if dev else device_id
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除设备 '{name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_device_requested.emit(device_id)
            self.refresh_devices()

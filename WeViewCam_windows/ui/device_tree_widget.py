# -*- coding: utf-8 -*-
"""
Device & Channel Navigation Tree.
Lists configured devices and their camera channels with quick double-click-to-play support.
"""

from typing import Optional, List, Set

from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread, QSettings
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMenu, QMessageBox, QDialog, QListWidget,
    QListWidgetItem, QFileDialog, QApplication
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


class DeviceExportDialog(QDialog):
    """Dialog allowing users to selectively choose which devices to export."""

    def __init__(self, devices: List[DeviceInfo], preselected_ids: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.devices = devices
        self.preselected_ids = set(preselected_ids) if preselected_ids is not None else None
        self.export_action: Optional[str] = None  # "file" or "clipboard"

        self.setWindowTitle("备份导出监控设备配置")
        self.resize(540, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #161b22;
                color: #c9d1d9;
            }
            QLabel {
                color: #c9d1d9;
            }
            QListWidget {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px;
                color: #c9d1d9;
            }
            QListWidget::item {
                padding: 8px 6px;
                border-bottom: 1px solid #21262d;
            }
            QListWidget::item:hover {
                background-color: #21262d;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
            }
            QPushButton#btn_primary {
                background-color: #238636;
                border-color: #2ea043;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton#btn_primary:hover {
                background-color: #2ea043;
            }
            QPushButton#btn_accent {
                background-color: #1f6feb;
                border-color: #388bfd;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton#btn_accent:hover {
                background-color: #388bfd;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        lbl_title = QLabel("选择要导出的设备")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #58a6ff;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel("请勾选需要备份导出的设备。支持单独选择指定设备，也可多选或全选：")
        lbl_desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(lbl_desc)

        # Quick actions row
        tools_layout = QHBoxLayout()
        btn_all = QPushButton("全选")
        btn_all.setFixedHeight(28)
        btn_all.clicked.connect(self._select_all)
        tools_layout.addWidget(btn_all)

        btn_none = QPushButton("清空")
        btn_none.setFixedHeight(28)
        btn_none.clicked.connect(self._select_none)
        tools_layout.addWidget(btn_none)

        btn_invert = QPushButton("反选")
        btn_invert.setFixedHeight(28)
        btn_invert.clicked.connect(self._invert_selection)
        tools_layout.addWidget(btn_invert)

        tools_layout.addStretch()

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold;")
        tools_layout.addWidget(self.lbl_count)
        layout.addLayout(tools_layout)

        # Device list
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        for dev in self.devices:
            proto_name = dev.protocol.value if hasattr(dev.protocol, "value") else str(dev.protocol)
            item_text = f"📹  {dev.name}   ({dev.ip}:{dev.port} | {proto_name} | {len(dev.channels)} 个通道)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, dev.device_id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            # Check state
            if self.preselected_ids is not None:
                is_checked = dev.device_id in self.preselected_ids
            else:
                is_checked = True
            item.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
            self.list_widget.addItem(item)

        self.list_widget.itemChanged.connect(self._update_count)
        self._update_count()

        # Action buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        btn_file = QPushButton("📁 保存为本地 JSON 文件")
        btn_file.setObjectName("btn_primary")
        btn_file.setFixedHeight(34)
        btn_file.clicked.connect(self._on_export_file)
        bottom_layout.addWidget(btn_file)

        btn_clip = QPushButton("📋 复制配置到剪贴板")
        btn_clip.setObjectName("btn_accent")
        btn_clip.setFixedHeight(34)
        btn_clip.clicked.connect(self._on_export_clipboard)
        bottom_layout.addWidget(btn_clip)

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(btn_cancel)

        layout.addLayout(bottom_layout)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)
        self._update_count()

    def _select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)
        self._update_count()

    def _invert_selection(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
        self._update_count()

    def _update_count(self):
        total = self.list_widget.count()
        selected = len(self.get_selected_device_ids())
        self.lbl_count.setText(f"已选择 {selected} / {total} 台设备")

    def get_selected_device_ids(self) -> List[str]:
        ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        return ids

    def _on_export_file(self):
        if not self.get_selected_device_ids():
            QMessageBox.warning(self, "提示", "请至少勾选一台需要导出的设备！")
            return
        self.export_action = "file"
        self.accept()

    def _on_export_clipboard(self):
        if not self.get_selected_device_ids():
            QMessageBox.warning(self, "提示", "请至少勾选一台需要导出的设备！")
            return
        self.export_action = "clipboard"
        self.accept()


class RefreshWorker(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager

    def run(self):
        try:
            results = self.device_manager.refresh_all_devices_status()
            self.finished_signal.emit(results)
        except Exception:
            self.finished_signal.emit({})


class DeviceTreeWidget(QWidget):
    """Sidebar tree view of surveillance devices and camera channels."""

    channel_double_clicked = pyqtSignal(str, int, str)  # device_id, channel_no, channel_name
    add_device_requested = pyqtSignal()
    edit_device_requested = pyqtSignal(str)              # device_id
    delete_device_requested = pyqtSignal(str)            # device_id

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._refresh_worker: Optional[RefreshWorker] = None
        self._init_ui()
        self._init_timer()
        # 启动时后台自动重新连接设备探测最新通道在线状态
        QTimer.singleShot(600, self.start_async_refresh)

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

        self.btn_auto_refresh = QPushButton("⏱️", self)
        self.btn_auto_refresh.setFixedSize(24, 24)
        self.btn_auto_refresh.setStyleSheet("QPushButton { font-size: 13px; padding: 0; }")
        self.btn_auto_refresh.clicked.connect(self._show_auto_refresh_menu)
        header_layout.addWidget(self.btn_auto_refresh)

        self.btn_export = QPushButton("📤", self)
        self.btn_export.setFixedSize(24, 24)
        self.btn_export.setToolTip("备份并导出设备配置到文件")
        self.btn_export.setStyleSheet("QPushButton { font-size: 13px; padding: 0; }")
        self.btn_export.clicked.connect(self.on_export_clicked)
        header_layout.addWidget(self.btn_export)

        self.btn_import = QPushButton("📥", self)
        self.btn_import.setFixedSize(24, 24)
        self.btn_import.setToolTip("从文件导入设备配置备份")
        self.btn_import.setStyleSheet("QPushButton { font-size: 13px; padding: 0; }")
        self.btn_import.clicked.connect(self.on_import_clicked)
        header_layout.addWidget(self.btn_import)

        btn_refresh = QPushButton("↻", self)
        btn_refresh.setFixedSize(24, 24)
        btn_refresh.setToolTip("刷新设备列表与通道在线状态")
        btn_refresh.setStyleSheet("QPushButton { font-size: 14px; padding: 0; }")
        btn_refresh.clicked.connect(self.start_async_refresh)
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

    def _init_timer(self):
        settings = QSettings("WeViewCam", "Client")
        self.auto_refresh_sec = int(settings.value("channel_refresh_interval_sec", 60))
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self.start_async_refresh)
        self._apply_timer_interval()

    def _apply_timer_interval(self):
        if self.auto_refresh_sec > 0:
            self._auto_refresh_timer.start(self.auto_refresh_sec * 1000)
            tip = f"定时更新通道状态 (当前: 每 {self.auto_refresh_sec} 秒)"
        else:
            self._auto_refresh_timer.stop()
            tip = "定时更新通道状态 (已关闭/仅手动)"
        self.btn_auto_refresh.setToolTip(tip)

    def set_auto_refresh_interval(self, sec: int):
        self.auto_refresh_sec = sec
        settings = QSettings("WeViewCam", "Client")
        settings.setValue("channel_refresh_interval_sec", sec)
        self._apply_timer_interval()

    def start_async_refresh(self):
        if self._refresh_worker and self._refresh_worker.isRunning():
            return
        self.btn_auto_refresh.setText("⏳")
        self._refresh_worker = RefreshWorker(self.device_manager)
        self._refresh_worker.finished_signal.connect(self._on_async_refresh_finished)
        self._refresh_worker.start()

    def _on_async_refresh_finished(self, results):
        self.btn_auto_refresh.setText("⏱️")
        self.refresh_devices(keep_expanded=True)

    def _show_auto_refresh_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; }")

        intervals = [
            (0, "🔴 禁用 (仅手动刷新)"),
            (30, "⚡ 每 30 秒自动刷新"),
            (60, "⏱️ 每 60 秒自动刷新 (默认)"),
            (120, "⏱️ 每 2 分钟自动刷新"),
            (300, "⏱️ 每 5 分钟自动刷新"),
        ]
        for sec, text in intervals:
            prefix = "● " if self.auto_refresh_sec == sec else "○ "
            act = menu.addAction(prefix + text)
            act.triggered.connect(lambda checked=False, s=sec: self.set_auto_refresh_interval(s))

        menu.addSeparator()
        act_now = menu.addAction("🔄 立即全网探测并更新状态")
        act_now.triggered.connect(self.start_async_refresh)

        menu.exec_(self.btn_auto_refresh.mapToGlobal(self.btn_auto_refresh.rect().bottomLeft()))

    def refresh_devices(self, expanded_device_id: Optional[str] = None, keep_expanded: bool = False):
        """Populate tree with current devices and channels (collapsed by default)."""
        expanded_ids = set()
        if keep_expanded:
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                data = item.data(0, Qt.UserRole)
                if data and item.isExpanded():
                    expanded_ids.add(data.get("device_id"))
        if expanded_device_id:
            expanded_ids.add(expanded_device_id)

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
                enabled_chs = [c for c in dev.channels if getattr(c, "is_enabled", True)]
                online_cnt = sum(1 for c in enabled_chs if c.is_online)
                ch_summary = f" [{online_cnt}/{len(enabled_chs)} 在线]"
            dev_item.setText(0, f"[{proto_name}] {dev.name} ({dev.ip}){ch_summary}")
            dev_item.setData(0, Qt.UserRole, {"type": "device", "device_id": dev.device_id})
            # 默认全部折叠，仅在明确指定或保持状态时展开
            dev_item.setExpanded(dev.device_id in expanded_ids)

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
                    if not getattr(ch, "is_enabled", True):
                        continue
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
            dev = self.device_manager.get_device(dev_id)
            if dev and not dev.is_connected:
                self.device_manager.connect_device(dev_id)
                self.refresh_devices(expanded_device_id=dev_id)

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            menu = QMenu(self)
            menu.setStyleSheet("QMenu { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; }")
            act_add = menu.addAction("＋ 添加新设备")
            act_add.triggered.connect(self.add_device_requested.emit)
            menu.addSeparator()
            act_import = menu.addAction("📥 导入设备配置")
            act_import.triggered.connect(self.on_import_clicked)
            act_export = menu.addAction("📤 导出设备配置")
            act_export.triggered.connect(self.on_export_clicked)
            menu.addSeparator()
            act_refresh = menu.addAction("🔄 刷新设备与通道在线状态")
            act_refresh.triggered.connect(self.start_async_refresh)
            menu.addSeparator()
            act_timer = menu.addAction("⏱️ 定时更新通道在线状态设置...")
            act_timer.triggered.connect(self._show_auto_refresh_menu)
            menu.exec_(self.tree.mapToGlobal(pos))
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
            act_channels = menu.addAction("📑 通道管理")
            act_channels.triggered.connect(lambda: self._open_channel_management(device_id))

            act_export_dev = menu.addAction("📤 备份导出此设备")
            act_export_dev.triggered.connect(lambda: self.on_export_clicked(device_id=device_id))

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

            menu.addSeparator()
            act_rename = menu.addAction("✏️ 重命名此通道")
            act_rename.triggered.connect(lambda: self._rename_channel_prompt(
                data["device_id"],
                data["channel_no"],
                data["channel_name"]
            ))

            act_disable = menu.addAction("👁️ 停用此通道")
            act_disable.triggered.connect(lambda: self._disable_channel(
                data["device_id"],
                data["channel_no"],
                data["channel_name"]
            ))

            menu.addSeparator()
            act_manage = menu.addAction("📑 打开通道管理")
            act_manage.triggered.connect(lambda: self._open_channel_management(data["device_id"]))

        menu.exec_(self.tree.mapToGlobal(pos))

    def _open_channel_management(self, device_id: str):
        from ui.channel_management_dialog import ChannelManagementDialog
        dlg = ChannelManagementDialog(self.device_manager, device_id, self)
        dlg.exec_()
        self.refresh_devices()

    def _rename_channel_prompt(self, device_id: str, channel_no: int, current_name: str):
        from PyQt5.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self,
            "重命名通道",
            f"请输入通道 {channel_no} 的自定义显示名称:",
            text=current_name
        )
        if ok and new_name.strip():
            self.device_manager.update_channel_name(device_id, channel_no, new_name.strip())
            self.refresh_devices()

    def _disable_channel(self, device_id: str, channel_no: int, channel_name: str):
        reply = QMessageBox.question(
            self,
            "停用通道确认",
            f"确定要停用通道 [{channel_name}] (CH {channel_no}) 吗？\n\n停用后该通道在资源树和预览分屏中将不再显示。\n可随时在【通道管理】中重新启用。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.device_manager.set_channel_enabled(device_id, channel_no, False)
            self.refresh_devices()

    def _refresh_device_channels(self, device_id: str):
        dev = self.device_manager.get_device(device_id)
        if not dev:
            return
        if not dev.is_connected:
            self.device_manager.connect_device(device_id)
        else:
            adapter = self.device_manager.get_adapter(device_id)
            if adapter:
                probed = adapter.get_channels()
                dev.channels = self.device_manager._merge_channels_preserving_custom(dev.channels, probed)
                self.device_manager.save_devices()
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

    def on_export_clicked(self, device_id: Optional[str] = None):
        """Handle export devices action, supporting selective device export."""
        devices = self.device_manager.list_devices()
        if not devices:
            QMessageBox.information(self, "提示", "当前没有可导出的设备配置")
            return

        preselected = [device_id] if device_id else None
        dlg = DeviceExportDialog(devices, preselected_ids=preselected, parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.export_action:
            return

        selected_ids = dlg.get_selected_device_ids()
        if not selected_ids:
            return

        if dlg.export_action == "clipboard":
            import json
            data = self.device_manager.get_devices_export_data(selected_ids)
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            QApplication.clipboard().setText(json_str)
            QMessageBox.information(
                self,
                "复制成功",
                f"已成功将选定的 {len(selected_ids)} 台设备配置复制到剪贴板！\n可直接粘贴到微信/邮件/文本文件，或发送至 Android 客户端。"
            )
            return

        # Export to file
        default_name = "weviewcam_devices_backup.json"
        if len(selected_ids) == 1:
            dev = self.device_manager.get_device(selected_ids[0])
            if dev and dev.name:
                safe_name = "".join(c for c in dev.name if c.isalnum() or c in ("-", "_", " ")).strip()
                if safe_name:
                    default_name = f"weviewcam_backup_{safe_name}.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出设备配置备份",
            default_name,
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return

        success = self.device_manager.export_devices(file_path, device_ids=selected_ids)
        if success:
            QMessageBox.information(
                self,
                "导出成功",
                f"成功导出选定的 {len(selected_ids)} 台设备配置到:\n{file_path}"
            )
        else:
            QMessageBox.critical(self, "导出失败", "导出设备配置文件时发生错误，请查看运行日志")

    def on_import_clicked(self):
        """Handle import devices action."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox, QMenu
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; }")
        act_file = menu.addAction("📁 选择本地备份文件 (.json)")
        act_clip = menu.addAction("📋 从剪贴板粘贴配置导入")
        chosen = menu.exec_(self.btn_import.mapToGlobal(self.btn_import.rect().bottomLeft()))
        if not chosen:
            return

        if chosen == act_clip:
            self.on_paste_import_clicked()
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要导入的设备配置备份",
            "",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("选择导入模式")
        msg_box.setText("请选择设备配置的导入模式：")
        msg_box.setInformativeText(
            "【增量合并】：若已存在相同设备则更新覆盖，新设备自动追加（推荐）。\n"
            "【完全覆盖】：清空当前所有设备，完全替换为备份文件内容。"
        )
        btn_merge = msg_box.addButton("增量合并", QMessageBox.ActionRole)
        btn_overwrite = msg_box.addButton("完全覆盖", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_merge)

        msg_box.exec_()
        clicked = msg_box.clickedButton()
        if clicked == btn_cancel:
            return

        is_overwrite = (clicked == btn_overwrite)
        success, message, count = self.device_manager.import_devices(file_path, overwrite=is_overwrite)
        if success:
            self.refresh_devices()
            QMessageBox.information(self, "导入完成", f"{message}\n设备列表已自动刷新。")
        else:
            QMessageBox.warning(self, "导入提示", message)

    def on_paste_import_clicked(self):
        """Import configuration directly from clipboard."""
        from PyQt5.QtWidgets import QApplication, QMessageBox, QInputDialog
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            text, ok = QInputDialog.getMultiLineText(
                self,
                "从剪贴板粘贴配置",
                "剪贴板为空，请将 JSON 备份配置直接粘贴到下方输入框中:",
                ""
            )
            if not ok or not text.strip():
                return
            text = text.strip()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("选择导入模式")
        msg_box.setText("已读取到配置文本，请选择导入模式：")
        msg_box.setInformativeText(
            "【增量合并】：若已存在相同设备则更新覆盖，新设备自动追加（推荐）。\n"
            "【完全覆盖】：清空当前所有设备，完全替换为配置内容。"
        )
        btn_merge = msg_box.addButton("增量合并", QMessageBox.ActionRole)
        btn_overwrite = msg_box.addButton("完全覆盖", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_merge)

        msg_box.exec_()
        clicked = msg_box.clickedButton()
        if clicked == btn_cancel:
            return

        is_overwrite = (clicked == btn_overwrite)
        success, message, count = self.device_manager.import_devices_from_text(text, overwrite=is_overwrite)
        if success:
            self.refresh_devices()
            QMessageBox.information(self, "导入完成", f"{message}\n设备列表已自动刷新。")
        else:
            QMessageBox.warning(self, "导入提示", message)


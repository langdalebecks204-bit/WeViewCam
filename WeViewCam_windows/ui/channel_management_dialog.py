# -*- coding: utf-8 -*-
"""
Channel Management Modal Dialog for Ubuntu VMS.
Supports custom channel naming, individual channel enabling/disabling, adding custom channels, and batch operations.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QInputDialog,
    QMessageBox, QSpinBox, QLineEdit, QFormLayout
)
from PyQt5.QtGui import QColor, QFont
from core.base_adapter import DeviceInfo, ChannelInfo
from core.device_manager import DeviceManager


class AddChannelDialog(QDialog):
    """Sub-dialog for manually adding a channel to NVR / DVR / RTSP device."""

    def __init__(self, device_id: str, default_channel_no: int, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.setWindowTitle("添加监控通道")
        self.setFixedSize(380, 220)
        self.setModal(True)
        self._init_ui(default_channel_no)

    def _init_ui(self, default_no: int):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.spin_no = QSpinBox(self)
        self.spin_no.setRange(1, 256)
        self.spin_no.setValue(default_no)
        form.addRow("通道编号 (CH):", self.spin_no)

        self.edit_name = QLineEdit(self)
        self.edit_name.setPlaceholderText("例如: 西侧仓库高空球机")
        self.edit_name.setText(f"通道 {default_no}")
        form.addRow("通道名称:", self.edit_name)

        self.check_ptz = QCheckBox("支持云台控制 (PTZ 球机)", self)
        form.addRow("", self.check_ptz)

        layout.addLayout(form)
        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("取消", self)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_ok = QPushButton("确定添加", self)
        btn_ok.setStyleSheet("background-color: #0e78ff; color: white; font-weight: bold;")
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)

        layout.addLayout(btn_box)

    def get_result(self):
        return self.spin_no.value(), self.edit_name.text().strip(), self.check_ptz.isChecked()


class ChannelManagementDialog(QDialog):
    """Modal dialog for managing camera channels of a surveillance device."""

    def __init__(self, device_manager: DeviceManager, device_id: str, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.device_id = device_id
        self.dev = self.device_manager.get_device(device_id)

        title = f"通道管理 - {self.dev.name if self.dev else device_id}"
        self.setWindowTitle(title)
        self.setMinimumSize(680, 480)
        self.resize(720, 520)
        self.setModal(True)

        self._init_ui()
        self._load_channels()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header bar
        header_box = QHBoxLayout()
        self.lbl_title = QLabel(f"设备通道列表 ({self.dev.ip}:{self.dev.port})" if self.dev else "", self)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        header_box.addWidget(self.lbl_title)

        header_box.addStretch()

        self.lbl_summary = QLabel("", self)
        self.lbl_summary.setStyleSheet("color: #8b949e; font-size: 13px;")
        header_box.addWidget(self.lbl_summary)

        layout.addLayout(header_box)

        # Action bar
        act_box = QHBoxLayout()
        act_box.setSpacing(8)

        self.btn_add = QPushButton("＋ 添加通道", self)
        self.btn_add.setStyleSheet("background-color: #238636; color: white; font-weight: bold;")
        self.btn_add.clicked.connect(self._on_add_channel)
        act_box.addWidget(self.btn_add)

        self.btn_enable_all = QPushButton("✓ 全部启用", self)
        self.btn_enable_all.clicked.connect(lambda: self._on_batch_toggle(True))
        act_box.addWidget(self.btn_enable_all)

        self.btn_disable_all = QPushButton("✕ 全部停用", self)
        self.btn_disable_all.clicked.connect(lambda: self._on_batch_toggle(False))
        act_box.addWidget(self.btn_disable_all)

        act_box.addStretch()

        layout.addLayout(act_box)

        # Channels Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["通道编号", "自定义通道名称", "在线状态", "PTZ", "启用状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #161b22; alternate-background-color: #0d1117; "
            "gridline-color: #30363d; border: 1px solid #30363d; border-radius: 6px; } "
            "QHeaderView::section { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 6px; font-weight: bold; }"
        )
        layout.addWidget(self.table)

        # Footer
        footer_box = QHBoxLayout()
        tip_lbl = QLabel("提示: 停用的通道在监控预览展开通道时不显示；双击名称或点击重命名可修改通道名称", self)
        tip_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        footer_box.addWidget(tip_lbl)
        footer_box.addStretch()

        btn_close = QPushButton("完成并关闭", self)
        btn_close.setProperty("class", "primaryBtn")
        btn_close.setStyleSheet("background-color: #1f6feb; color: white; font-weight: bold; min-width: 100px;")
        btn_close.clicked.connect(self.accept)
        footer_box.addWidget(btn_close)

        layout.addLayout(footer_box)

    def _load_channels(self):
        """Populate the channels table with current device channels."""
        self.dev = self.device_manager.get_device(self.device_id)
        if not self.dev:
            return

        channels = list(self.dev.channels)
        channels.sort(key=lambda c: c.channel_no)

        enabled_cnt = sum(1 for c in channels if getattr(c, "is_enabled", True))
        self.lbl_summary.setText(f"共 {len(channels)} 个通道 (已启用 {enabled_cnt} 个)")

        self.table.setRowCount(len(channels))
        for row, ch in enumerate(channels):
            # 0. Channel No
            item_no = QTableWidgetItem(f"CH {ch.channel_no}")
            item_no.setTextAlignment(Qt.AlignCenter)
            item_no.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, item_no)

            # 1. Custom Name
            item_name = QTableWidgetItem(ch.name)
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 1, item_name)

            # 2. Online status
            is_online = getattr(ch, "is_online", True)
            item_status = QTableWidgetItem("在线" if is_online else "离线")
            item_status.setTextAlignment(Qt.AlignCenter)
            item_status.setForeground(QColor("#3fb950" if is_online else "#8b949e"))
            item_status.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, item_status)

            # 3. PTZ
            is_ptz = getattr(ch, "is_ptz", False)
            item_ptz = QTableWidgetItem("云台" if is_ptz else "枪机")
            item_ptz.setTextAlignment(Qt.AlignCenter)
            item_ptz.setForeground(QColor("#58a6ff" if is_ptz else "#c9d1d9"))
            item_ptz.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 3, item_ptz)

            # 4. Enabled checkbox
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(6, 0, 6, 0)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk = QCheckBox(chk_widget)
            is_en = getattr(ch, "is_enabled", True)
            chk.setChecked(is_en)
            chk.setToolTip("开启或停用此通道显示")
            chk.toggled.connect(lambda checked, c_no=ch.channel_no: self._on_toggle_enabled(c_no, checked))
            chk_layout.addWidget(chk)
            self.table.setCellWidget(row, 4, chk_widget)

            # 5. Operations
            op_widget = QWidget()
            op_layout = QHBoxLayout(op_widget)
            op_layout.setContentsMargins(4, 2, 4, 2)
            op_layout.setSpacing(6)

            btn_rename = QPushButton("✏️ 重命名", op_widget)
            btn_rename.setStyleSheet("font-size: 11px; padding: 2px 8px;")
            btn_rename.clicked.connect(lambda _, c_no=ch.channel_no, old_n=ch.name: self._on_rename_channel(c_no, old_n))
            op_layout.addWidget(btn_rename)

            btn_del = QPushButton("🗑️ 删除", op_widget)
            btn_del.setStyleSheet("font-size: 11px; padding: 2px 6px; color: #f85149;")
            btn_del.clicked.connect(lambda _, c_no=ch.channel_no, c_name=ch.name: self._on_delete_channel(c_no, c_name))
            op_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 5, op_widget)

    def _on_rename_channel(self, channel_no: int, old_name: str):
        new_name, ok = QInputDialog.getText(
            self,
            "重命名通道",
            f"请输入通道 {channel_no} 的自定义显示名称:",
            text=old_name
        )
        if ok and new_name.strip():
            self.device_manager.update_channel_name(self.device_id, channel_no, new_name.strip())
            self._load_channels()

    def _on_toggle_enabled(self, channel_no: int, enabled: bool):
        self.device_manager.set_channel_enabled(self.device_id, channel_no, enabled)
        # Refresh summary counter
        dev = self.device_manager.get_device(self.device_id)
        if dev:
            enabled_cnt = sum(1 for c in dev.channels if getattr(c, "is_enabled", True))
            self.lbl_summary.setText(f"共 {len(dev.channels)} 个通道 (已启用 {enabled_cnt} 个)")

    def _on_batch_toggle(self, enabled: bool):
        self.device_manager.batch_set_channels_enabled(self.device_id, enabled)
        self._load_channels()

    def _on_add_channel(self):
        next_no = 1
        if self.dev and self.dev.channels:
            next_no = max(c.channel_no for c in self.dev.channels) + 1

        dlg = AddChannelDialog(self.device_id, next_no, self)
        if dlg.exec_() == QDialog.Accepted:
            c_no, c_name, is_ptz = dlg.get_result()
            self.device_manager.add_custom_channel(self.device_id, c_no, c_name, is_ptz=is_ptz)
            self._load_channels()

    def _on_delete_channel(self, channel_no: int, channel_name: str):
        reply = QMessageBox.question(
            self,
            "删除通道确认",
            f"确定要删除通道 [{channel_name}] (CH {channel_no}) 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.device_manager.delete_channel(self.device_id, channel_no)
            self._load_channels()

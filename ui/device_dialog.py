# -*- coding: utf-8 -*-
"""
Add / Edit Device Modal Dialog.
Supports configuring network parameters, protocol selection, and connection testing.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QComboBox, QCheckBox, QPushButton, QLabel, QMessageBox
)
from core.base_adapter import DeviceInfo, ProtocolType
from core.device_manager import DeviceManager


class DeviceDialog(QDialog):
    """Modal dialog for adding or editing surveillance devices."""

    def __init__(self, device_manager: DeviceManager, device_info: DeviceInfo = None, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.device_info = device_info
        self.is_edit = device_info is not None

        self.setWindowTitle("编辑监控设备" if self.is_edit else "添加监控设备")
        self.setFixedSize(480, 420)
        self.setModal(True)

        self._init_ui()
        if self.is_edit:
            self._load_existing_device()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        # 1. Device Name (带常用中文名快捷填充)
        name_container = QWidget(self)
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(6)

        self.edit_name = QLineEdit(name_container)
        self.edit_name.setPlaceholderText("例如: 1号主大门监控")
        name_layout.addWidget(self.edit_name, 1)

        self.combo_quick_name = QComboBox(name_container)
        self.combo_quick_name.setToolTip("快捷选择常用中文名称，方便免打字")
        self.combo_quick_name.addItem("常用名称...")
        for qn in ["1号主大门", "南大门入口", "地下停车场", "办公楼大厅", "周界防范", "仓储库房", "厂区主干道", "园区东门"]:
            self.combo_quick_name.addItem(qn)
        self.combo_quick_name.currentIndexChanged.connect(self._on_quick_name_selected)
        name_layout.addWidget(self.combo_quick_name)

        form.addRow("设备名称:", name_container)

        # 2. Protocol Type
        self.combo_proto = QComboBox(self)
        self.combo_proto.addItem("海康威视 (HCNetSDK)", ProtocolType.HIKVISION)
        self.combo_proto.addItem("大华 (NetSDK - 预留)", ProtocolType.DAHUA)
        self.combo_proto.addItem("ONVIF / RTSP (国际标准)", ProtocolType.ONVIF)
        self.combo_proto.addItem("自定义 RTSP / 车牌抓拍一体机", ProtocolType.CUSTOM_RTSP)
        self.combo_proto.currentIndexChanged.connect(self._on_protocol_changed)
        form.addRow("设备协议:", self.combo_proto)

        # 3. IP Address
        self.edit_ip = QLineEdit(self)
        self.edit_ip.setPlaceholderText("例如: 192.168.1.64 或 10.0.25.206")
        form.addRow("IP 地址:", self.edit_ip)

        # 4. Port
        self.spin_port = QSpinBox(self)
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(8000)
        form.addRow("端口:", self.spin_port)

        # 5. Username
        self.edit_user = QLineEdit(self)
        self.edit_user.setText("admin")
        form.addRow("登录用户名:", self.edit_user)

        # 6. Password
        self.edit_pwd = QLineEdit(self)
        self.edit_pwd.setEchoMode(QLineEdit.Password)
        self.edit_pwd.setPlaceholderText("设备管理密码")
        form.addRow("登录密码:", self.edit_pwd)

        # 7. Custom RTSP Path / URL
        self.edit_custom_rtsp = QLineEdit(self)
        self.edit_custom_rtsp.setPlaceholderText("选填，留空自动探测；或填如 /h264、/video 等")
        self.edit_custom_rtsp.setToolTip("小厂车牌一体机若已在 NVR 或 Web 后台查到取流路径，可在此直接填入")
        form.addRow("RTSP 流路径:", self.edit_custom_rtsp)

        # 8. Auto Connect
        self.check_auto_conn = QCheckBox("保存后立即连接并获取通道", self)
        self.check_auto_conn.setChecked(True)
        form.addRow("", self.check_auto_conn)

        layout.addLayout(form)

        # Test Status Label
        self.lbl_status = QLabel("", self)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #a0aab8; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.btn_test = QPushButton("🔍 测试连接", self)
        self.btn_test.clicked.connect(self._test_connection)
        btn_layout.addWidget(self.btn_test)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消", self)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("确定保存", self)
        self.btn_save.setProperty("class", "primaryBtn")
        self.btn_save.setStyleSheet("background-color: #0e78ff; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self._save_device)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _on_quick_name_selected(self, index: int):
        if index > 0:
            chosen = self.combo_quick_name.currentText()
            self.edit_name.setText(chosen)
            self.combo_quick_name.setCurrentIndex(0)

    def _on_protocol_changed(self, index: int):
        proto = self.combo_proto.currentData()
        if proto == ProtocolType.HIKVISION:
            self.spin_port.setValue(8000)
        elif proto == ProtocolType.DAHUA:
            self.spin_port.setValue(37777)
        elif proto == ProtocolType.ONVIF:
            self.spin_port.setValue(80)
        elif proto == ProtocolType.CUSTOM_RTSP:
            self.spin_port.setValue(554)

    def _load_existing_device(self):
        dev = self.device_info
        self.edit_name.setText(dev.name)
        self.edit_ip.setText(dev.ip)
        self.spin_port.setValue(dev.port)
        self.edit_user.setText(dev.username)
        self.edit_pwd.setText(dev.password)
        self.edit_custom_rtsp.setText(dev.extra.get("custom_rtsp_url", ""))

        index = self.combo_proto.findData(dev.protocol)
        if index >= 0:
            self.combo_proto.setCurrentIndex(index)

    def _get_form_device_info(self) -> DeviceInfo:
        name = self.edit_name.text().strip() or self.edit_ip.text().strip()
        proto = self.combo_proto.currentData() or ProtocolType.HIKVISION
        dev_id = self.device_info.device_id if self.is_edit else ""

        extra = dict(self.device_info.extra) if (self.is_edit and self.device_info) else {}
        custom_url = self.edit_custom_rtsp.text().strip()
        if custom_url:
            extra["custom_rtsp_url"] = custom_url
        elif "custom_rtsp_url" in extra:
            del extra["custom_rtsp_url"]

        return DeviceInfo(
            device_id=dev_id,
            name=name,
            ip=self.edit_ip.text().strip(),
            port=self.spin_port.value(),
            username=self.edit_user.text().strip(),
            password=self.edit_pwd.text().strip(),
            protocol=proto,
            extra=extra
        )

    def _test_connection(self):
        temp_dev = self._get_form_device_info()
        if not temp_dev.ip:
            QMessageBox.warning(self, "警告", "请先输入设备 IP 地址！")
            return

        self.lbl_status.setText("正在测试连接，请稍候...")
        self.lbl_status.setStyleSheet("color: #3894ff;")
        self.btn_test.setEnabled(False)

        ok, msg, channels = self.device_manager.test_connection(temp_dev)
        self.btn_test.setEnabled(True)

        if ok:
            self.lbl_status.setText(f"✓ {msg}")
            self.lbl_status.setStyleSheet("color: #3fb950; font-weight: bold;")
        else:
            self.lbl_status.setText(f"✕ {msg}")
            self.lbl_status.setStyleSheet("color: #ff4d4f;")

    def _save_device(self):
        temp_dev = self._get_form_device_info()
        if not temp_dev.ip:
            QMessageBox.warning(self, "警告", "请填写设备 IP 地址！")
            return

        if not temp_dev.name:
            temp_dev.name = f"设备_{temp_dev.ip}"

        auto_conn = self.check_auto_conn.isChecked()

        if self.is_edit:
            self.device_manager.update_device(temp_dev)
            if auto_conn:
                self.device_manager.connect_device(temp_dev.device_id)
        else:
            ok, res = self.device_manager.add_device(temp_dev, auto_connect=auto_conn)
            if not ok:
                QMessageBox.critical(self, "保存失败", res)
                return

        self.accept()

# -*- coding: utf-8 -*-
"""
WeViewCam Professional Extension Promotion & Activation Dialog.
Displays feature highlights, machine fingerprint, contact card, and license activation entry.
"""

import json
import os
try:
    from PyQt5.QtCore import Qt, QSize
    from PyQt5.QtGui import QIcon, QFont, QGuiApplication
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QFileDialog, QMessageBox, QWidget, QScrollArea
    )
except ImportError:
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtGui import QIcon, QFont, QGuiApplication
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QFileDialog, QMessageBox, QWidget, QScrollArea
    )

from core.license_manager import LicenseManager


class ProLicenseDialog(QDialog):
    """Dialog for PRO module introduction, machine code display, and license activation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WeViewCam 智能巡检与存储健康日报 [专业版扩展]")
        self.setFixedSize(680, 720)
        self.setStyleSheet("""
            QDialog {
                background-color: #12141a;
                color: #e2e8f0;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QLabel {
                color: #cbd5e1;
            }
            QFrame.card {
                background-color: #1a1e27;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton.primary-btn {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
            }
            QPushButton.primary-btn:hover {
                background-color: #1d4ed8;
            }
            QPushButton.secondary-btn {
                background-color: #2d3748;
                color: #cbd5e1;
                border: 1px solid #4a5568;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton.secondary-btn:hover {
                background-color: #3b4556;
                color: #ffffff;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 1. Header Banner
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #0f172a); border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        
        title = QLabel("🛡️ WeViewCam 智能巡检与存储健康日报 [PRO]")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setStyleSheet("color: #38bdf8;")
        h_layout.addWidget(title)

        desc = QLabel("专为安防监控工程商、物业弱电维保与工业园区打造的全自动视频与存储智能巡检系统。")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        desc.setWordWrap(True)
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # 2. Features Grid
        feat_card = QFrame()
        feat_card.setProperty("class", "card")
        feat_card.setStyleSheet("background-color: #1a1e27; border: 1px solid #2d3748; border-radius: 8px; padding: 12px;")
        feat_layout = QVBoxLayout(feat_card)
        feat_layout.setSpacing(10)

        f_title = QLabel("🌟 专业版核心商业特性")
        f_title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        f_title.setStyleSheet("color: #f8fafc;")
        feat_layout.addWidget(f_title)

        features = [
            ("📸 每日全网全自动轮巡抓拍", "毫秒级提取海康/RTSP原画帧，保存带时间水印高清存证，防漏拍、防视角偏位。"),
            ("⚠️ 离线故障与失联自动追溯", "全天候侦测设备与通道离线，自动登记故障起始时间与持续时长，形成台账。"),
            ("💽 NVR 硬盘状态与 S.M.A.R.T. 预警", "直接与硬件时钟和存储芯片通信，监控总容量、剩余可用量与坏道/SMART故障预警。"),
            ("📊 自动化 HTML / PDF 运维日报", "一键生成管理层汇报看板，带九宫格缩略图墙与在线率指标，支持一键发送微信/钉钉。")
        ]

        for head_text, sub_text in features:
            item_box = QVBoxLayout()
            h_lbl = QLabel(head_text)
            h_lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
            s_lbl = QLabel(sub_text)
            s_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; margin-left: 18px;")
            s_lbl.setWordWrap(True)
            item_box.addWidget(h_lbl)
            item_box.addWidget(s_lbl)
            feat_layout.addLayout(item_box)

        layout.addWidget(feat_card)

        # 3. Machine Code Box
        mc_card = QFrame()
        mc_card.setStyleSheet("background-color: #1a1e27; border: 1px solid #2d3748; border-radius: 8px; padding: 12px;")
        mc_layout = QVBoxLayout(mc_card)

        mc_header = QLabel("💻 本机设备专属机器码 (Machine ID)")
        mc_header.setStyleSheet("color: #f8fafc; font-weight: bold;")
        mc_layout.addWidget(mc_header)

        mc_row = QHBoxLayout()
        self.mc_code = LicenseManager.get_machine_code()
        self.mc_label = QLabel(self.mc_code)
        self.mc_label.setStyleSheet("""
            background-color: #0f172a;
            color: #38bdf8;
            font-family: Consolas, monospace;
            font-size: 14px;
            font-weight: bold;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px dashed #38bdf8;
        """)
        mc_row.addWidget(self.mc_label, stretch=1)

        copy_btn = QPushButton("📋 一键复制")
        copy_btn.setProperty("class", "secondary-btn")
        copy_btn.setStyleSheet("background-color: #2d3748; color: #fff; padding: 8px 14px; border-radius: 4px;")
        copy_btn.clicked.connect(self.copy_machine_code)
        mc_row.addWidget(copy_btn)
        mc_layout.addLayout(mc_row)
        layout.addWidget(mc_card)

        # 4. Contact & Activation Card
        act_card = QFrame()
        act_card.setStyleSheet("background-color: #1a1e27; border: 1px solid #2d3748; border-radius: 8px; padding: 12px;")
        act_layout = QVBoxLayout(act_card)

        c_title = QLabel("📲 获取授权 / 商业咨询")
        c_title.setStyleSheet("color: #f8fafc; font-weight: bold;")
        act_layout.addWidget(c_title)

        contact_info = QLabel("请复制上方机器码联系作者，获取对应设备的专属激活授权文件 (license.lic)。\n商务咨询 / 微信: 请联系作者获取")
        contact_info.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        act_layout.addWidget(contact_info)

        act_row = QHBoxLayout()
        is_act, status_msg, _ = LicenseManager.is_activated("daily_inspection")
        self.status_lbl = QLabel(f"当前授权状态: {status_msg}")
        status_color = "#4ade80" if is_act else "#f87171"
        self.status_lbl.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        act_row.addWidget(self.status_lbl, stretch=1)

        import_btn = QPushButton("🔑 导入授权文件 (.lic)")
        import_btn.setProperty("class", "primary-btn")
        import_btn.setStyleSheet("background-color: #059669; color: #fff; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        import_btn.clicked.connect(self.import_license)
        act_row.addWidget(import_btn)

        act_layout.addLayout(act_row)
        layout.addWidget(act_card)

        # 5. Bottom Close
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("background-color: #334155; color: #fff; padding: 6px 20px; border-radius: 4px;")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

    def copy_machine_code(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.mc_code)
        QMessageBox.information(self, "复制成功", "机器码已成功复制到剪贴板！\n请将机器码发送给作者获取专属授权。")

    def import_license(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择授权文件", "", "License Files (*.lic *.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or "machine_code" not in data:
                QMessageBox.critical(self, "授权失败", "授权文件格式无效，未找到有效的机器码信息。")
                return

            # Save license
            success = LicenseManager.save_license(data)
            if not success:
                QMessageBox.critical(self, "授权失败", "无法保存授权文件到本地配置目录。")
                return

            # Re-verify
            is_act, status_msg, _ = LicenseManager.is_activated("daily_inspection")
            if is_act:
                self.status_lbl.setText(f"当前授权状态: {status_msg}")
                self.status_lbl.setStyleSheet("color: #4ade80; font-weight: bold;")
                QMessageBox.information(self, "激活成功", f"🎉 专业版功能已成功激活！\n{status_msg}")
            else:
                self.status_lbl.setText(f"当前授权状态: {status_msg}")
                self.status_lbl.setStyleSheet("color: #f87171; font-weight: bold;")
                QMessageBox.warning(self, "激活未生效", f"授权文件已导入，但验证未通过:\n{status_msg}")

        except Exception as e:
            QMessageBox.critical(self, "导入异常", f"读取授权文件异常: {str(e)}")

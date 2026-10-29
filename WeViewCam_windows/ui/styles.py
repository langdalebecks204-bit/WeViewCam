# -*- coding: utf-8 -*-
"""
Modern Dark VMS Theme (QSS Stylesheet).
Designed for surveillance operations centers: eye-friendly dark palette, clear contrasts.
"""

DARK_THEME_QSS = """
/* Global Application Styles */
QWidget {
    background-color: #1a1d24;
    color: #e1e4ea;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    selection-background-color: #0e78ff;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #14161b;
}

/* Top Navigation Bar */
QFrame#topNavBar {
    background-color: #1f232c;
    border-bottom: 1px solid #2d3340;
    min-height: 52px;
    max-height: 52px;
}

QLabel#appLogo {
    font-size: 16px;
    font-weight: bold;
    color: #3894ff;
    padding-left: 12px;
}

QPushButton.navBtn {
    background-color: transparent;
    color: #b0b7c3;
    border: none;
    border-bottom: 3px solid transparent;
    font-size: 14px;
    font-weight: 500;
    padding: 0 18px;
    min-height: 49px;
}

QPushButton.navBtn:hover {
    color: #ffffff;
    background-color: rgba(255, 255, 255, 0.04);
}

QPushButton.navBtn:checked {
    color: #3894ff;
    border-bottom: 3px solid #3894ff;
    font-weight: bold;
}

/* Sidebar & Panels */
QFrame.sidePanel {
    background-color: #1e222a;
    border-right: 1px solid #2c3240;
}

QGroupBox {
    border: 1px solid #323948;
    border-radius: 4px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: bold;
    color: #a0aab8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #3894ff;
}

/* Push Buttons */
QPushButton {
    background-color: #2a303d;
    color: #e1e4ea;
    border: 1px solid #3d4556;
    border-radius: 4px;
    padding: 5px 12px;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #343c4c;
    border-color: #4f5a70;
}

QPushButton:pressed {
    background-color: #202530;
}

QPushButton:disabled {
    background-color: #1c1f26;
    color: #586070;
    border-color: #272c36;
}

/* Primary Action Buttons */
QPushButton.primaryBtn {
    background-color: #0e78ff;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton.primaryBtn:hover {
    background-color: #2788ff;
}

QPushButton.primaryBtn:pressed {
    background-color: #0066e6;
}

/* Danger Buttons */
QPushButton.dangerBtn {
    background-color: #dc3545;
    color: #ffffff;
    border: none;
}

QPushButton.dangerBtn:hover {
    background-color: #e44d5c;
}

/* Tree & List Views */
QTreeView, QListView, QTableView {
    background-color: #181b22;
    alternate-background-color: #1d212a;
    border: 1px solid #2d3340;
    border-radius: 4px;
    color: #d8dde6;
    show-decoration-selected: 1;
}

QTreeView::item, QListView::item {
    padding: 5px;
    border-radius: 2px;
}

QTreeView::item:hover, QListView::item:hover {
    background-color: #262c38;
}

QTreeView::item:selected, QListView::item:selected {
    background-color: #1a4273;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #222630;
    color: #a0aab8;
    padding: 5px;
    border: none;
    border-bottom: 1px solid #333a4a;
    font-weight: 600;
}

/* Inputs & Combos */
QLineEdit, QSpinBox, QDateTimeEdit, QComboBox {
    background-color: #171920;
    border: 1px solid #353c4d;
    border-radius: 4px;
    padding: 4px 8px;
    color: #f0f2f5;
    min-height: 22px;
}

QLineEdit:focus, QSpinBox:focus, QDateTimeEdit:focus, QComboBox:focus {
    border: 1px solid #3894ff;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #171a21;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #343c4c;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #47536a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #171a21;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #343c4c;
    min-width: 20px;
    border-radius: 4px;
}

/* Video Tile Widget */
QFrame.videoSlot {
    background-color: #0b0c0e;
    border: 1px solid #232731;
    border-radius: 2px;
}

QFrame.videoSlot[selected="true"] {
    border: 2px solid #3894ff;
}

/* PTZ Circular Dial buttons */
QPushButton.ptzBtn {
    background-color: #262b36;
    border: 1px solid #394254;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    min-width: 36px;
    min-height: 36px;
}

QPushButton.ptzBtn:hover {
    background-color: #374154;
    border-color: #556480;
    color: #3894ff;
}

QPushButton.ptzBtn:pressed {
    background-color: #195299;
    color: #ffffff;
}

/* Status Bar */
QStatusBar {
    background-color: #171920;
    color: #8c96a5;
    border-top: 1px solid #262b36;
    font-size: 12px;
}

QStatusBar::item {
    border: none;
}
"""

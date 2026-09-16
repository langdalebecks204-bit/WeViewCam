#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Surveillance and Recording Playback Application.
Supports Hikvision, Dahua, and ONVIF with Linux hardware rendering.
"""

import os
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from core import __version__
from core.logger import setup_logger, get_logger

# Initialize structured logging
setup_logger()
logger = get_logger("Main")


def main():
    logger.info("==================================================")
    logger.info(f"正在启动 WeViewCam 视频监控平台 v{__version__}...")
    logger.info(f"Python 版本: {sys.version.split()[0]} ({sys.platform})")
    logger.info("==================================================")

    # Check X11 DISPLAY on Linux desktop
    if "linux" in sys.platform.lower():
        display = os.environ.get("DISPLAY")
        if not display:
            logger.warning("未检测到 DISPLAY 环境变量。如果您在无桌面图形终端中运行，请确保 X11 或 VNC 转发已开启。")

    # High DPI settings
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("WeViewCam")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("WeViewCam")

    # Set application icon
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "icon.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_dir, "图标.jpg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from ui.main_window import MainWindow

    main_win = MainWindow()
    main_win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

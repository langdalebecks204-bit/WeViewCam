#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeViewCam Video Surveillance and Recording Playback Application (Windows Edition).
Supports Hikvision, Dahua, and ONVIF with native hardware rendering and RTSP fallback.
"""

import os
import sys
import ctypes

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from core import __version__
from core.logger import setup_logger, get_logger

# Initialize structured logging
setup_logger()
logger = get_logger("Main")


def set_windows_app_id():
    """Set Windows AppUserModelID so the taskbar groups and displays the correct icon."""
    if sys.platform.startswith("win"):
        try:
            myappid = "WeViewCam.VideoSurveillance.VMS.Desktop"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            logger.debug(f"SetCurrentProcessExplicitAppUserModelID failed: {e}")


def main():
    logger.info("==================================================")
    logger.info(f"正在启动 WeViewCam 视频监控平台 (Windows 版) v{__version__}...")
    logger.info(f"Python 版本: {sys.version.split()[0]} ({sys.platform})")
    logger.info("==================================================")

    # Set Windows Taskbar App ID
    set_windows_app_id()

    # High DPI settings for crisp rendering on modern Windows monitors
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("WeViewCam")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("WeViewCam")

    # Set application icon
    search_dirs = []
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            search_dirs.append(sys._MEIPASS)
        search_dirs.append(os.path.dirname(sys.executable))
    search_dirs.append(os.path.dirname(os.path.abspath(__file__)))

    icon_candidates = []
    for d in search_dirs:
        icon_candidates.extend([
            os.path.join(d, "icon.ico"),
            os.path.join(d, "icon.png"),
            os.path.join(d, "图标.jpg")
        ])

    for ic in icon_candidates:
        if os.path.exists(ic):
            app.setWindowIcon(QIcon(ic))
            break

    from ui.main_window import MainWindow

    main_win = MainWindow()
    main_win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

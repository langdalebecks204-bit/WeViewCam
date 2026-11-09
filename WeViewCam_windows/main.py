#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeViewCam Video Surveillance and Recording Playback Application (Ubuntu / Linux Edition).
Supports Hikvision, Dahua, and ONVIF with native hardware rendering and RTSP fallback.
"""

import os
import sys
import ctypes
import faulthandler

# Enable C-level crash trace capture for SIGSEGV, SIGABRT, SIGFPE, SIGILL
try:
    faulthandler.enable(all_threads=True)
except Exception:
    pass

# 1. Linux X11 initialization MUST happen before importing Qt / SDKs
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    try:
        libx11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        libx11.XInitThreads()
    except Exception:
        pass

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
    plat_desc = "Windows 版" if sys.platform.startswith("win") else "Ubuntu / Linux 版"
    logger.info("==================================================")
    logger.info(f"正在启动 WeViewCam 视频监控平台 ({plat_desc}) v{__version__}...")
    logger.info(f"Python 版本: {sys.version.split()[0]} ({sys.platform})")
    try:
        from adapters.onvif.player import RtspPlayerManager
        mgr = RtspPlayerManager.get_instance()
        if mgr.has_vlc:
            logger.info("✓ 硬件加速播放引擎: VLC 就绪 (原生 X11 / DirectDraw 直出)")
        else:
            logger.error("❌ 硬件加速播放引擎: libvlc 未就绪！请运行 bash install.sh 安装 libvlc-dev 和 vlc")
    except Exception as ve:
        logger.error(f"检查 VLC 状态异常: {ve}")
    logger.info("==================================================")

    # Set Windows Taskbar App ID
    set_windows_app_id()

    # Enable X11 multi-thread safety and High DPI settings
    if hasattr(Qt, "AA_X11InitThreads"):
        QApplication.setAttribute(Qt.AA_X11InitThreads, True)
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

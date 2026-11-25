#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeViewCam Video Surveillance and Recording Playback Application (Windows Edition).
Supports Hikvision, Dahua, and ONVIF with native hardware rendering and RTSP fallback.
"""

import os
import sys
import ctypes
import faulthandler

# 0. Windows PyInstaller frozen safety: guard stdout/stderr when None (noconsole mode)
class NullWriter:
    def write(self, *args, **kwargs):
        pass
    def flush(self, *args, **kwargs):
        pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

# Configure Windows DLL search directories before importing SDKs
if sys.platform.startswith("win"):
    base_dir = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, "frozen", False) else os.path.dirname(sys.executable)
    dahua_win64 = os.path.join(base_dir, "sdk", "dahua", "win64")
    hik_win64 = os.path.join(base_dir, "sdk", "hikvision", "win64")
    for d in [dahua_win64, hik_win64]:
        if os.path.isdir(d):
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
            if d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + d

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

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtWidgets import QApplication, QSplashScreen

from core import __version__
from core.logger import setup_logger, get_logger

# Initialize structured logging
setup_logger()
logger = get_logger("Main")


def global_excepthook(exctype, value, tb):
    logger.error("Unhandled Python exception:", exc_info=(exctype, value, tb))


sys.excepthook = global_excepthook


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

    chosen_icon = None
    for ic in icon_candidates:
        if os.path.exists(ic):
            app.setWindowIcon(QIcon(ic))
            chosen_icon = ic
            break

    # Show lightweight dark splash immediately so user gets instant visual feedback
    splash_pix = QPixmap(380, 150)
    splash_pix.fill(QColor("#0d1117"))
    painter = QPainter(splash_pix)
    painter.setPen(QColor("#30363d"))
    painter.drawRect(0, 0, 379, 149)
    if chosen_icon:
        icon_pix = QPixmap(chosen_icon).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(28, 51, icon_pix)
    painter.setPen(QColor("#f0f6fc"))
    painter.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
    painter.drawText(92, 66, "WeViewCam")
    painter.setPen(QColor("#8b949e"))
    painter.setFont(QFont("Microsoft YaHei", 9))
    painter.drawText(92, 94, f"v{__version__} · 正在初始化监控工作台...")
    painter.end()

    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.show()
    app.processEvents()

    from ui.main_window import MainWindow

    main_win = MainWindow()
    main_win.show()
    splash.finish(main_win)

    # Warm up VLC in background only after main window is visible
    def _warmup_vlc():
        try:
            from adapters.onvif.player import RtspPlayerManager
            RtspPlayerManager.get_instance()
        except Exception:
            pass

    QTimer.singleShot(50, _warmup_vlc)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Logger utility module.
Provides consistent logging formatting for the surveillance system with instant flushing.
"""

import os
import sys
import logging
from datetime import datetime

_LOGGER_INITIALIZED = False


class FlushStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes immediately after every write."""
    def emit(self, record):
        try:
            super().emit(record)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            pass


class FlushFileHandler(logging.FileHandler):
    """FileHandler that flushes and syncs to disk immediately after every write."""
    def emit(self, record):
        try:
            super().emit(record)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            pass


def setup_logger(log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """Initialize root logger with console and rotating file output."""
    global _LOGGER_INITIALIZED
    logger = logging.getLogger("VMS")
    
    if _LOGGER_INITIALIZED:
        return logger

    logger.setLevel(log_level)
    logger.propagate = False

    # Create log directory if not exists
    if not os.path.isabs(log_dir):
        if getattr(sys, "frozen", False):
            base_app = os.path.dirname(sys.executable)
        else:
            base_app = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_app, log_dir)

    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"vms_{today_str}.log")

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-5s] [%(name)s:%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (auto flush)
    if sys.stdout is not None:
        try:
            console_handler = FlushStreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        except Exception:
            pass

    # File handler (auto flush)
    try:
        file_handler = FlushFileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        if sys.stderr is not None:
            try:
                print(f"[Warning] Failed to initialize file logger: {e}", file=sys.stderr)
            except Exception:
                pass

    _LOGGER_INITIALIZED = True
    return logger


def get_logger(module_name: str = "") -> logging.Logger:
    """Get a named logger child of the main VMS logger."""
    if not _LOGGER_INITIALIZED:
        setup_logger()
    if module_name:
        return logging.getLogger(f"VMS.{module_name}")
    return logging.getLogger("VMS")

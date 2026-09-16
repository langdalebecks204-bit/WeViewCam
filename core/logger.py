# -*- coding: utf-8 -*-
"""
Logger utility module.
Provides consistent logging formatting for the surveillance system.
"""

import os
import sys
import logging
from datetime import datetime

_LOGGER_INITIALIZED = False

def setup_logger(log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """Initialize root logger with console and rotating file output."""
    global _LOGGER_INITIALIZED
    logger = logging.getLogger("VMS")
    
    if _LOGGER_INITIALIZED:
        return logger

    logger.setLevel(log_level)
    logger.propagate = False

    # Create log directory if not exists
    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"vms_{today_str}.log")

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-5s] [%(name)s:%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[Warning] Failed to initialize file logger: {e}", file=sys.stderr)

    _LOGGER_INITIALIZED = True
    return logger

def get_logger(module_name: str = "") -> logging.Logger:
    """Get a named logger child of the main VMS logger."""
    if not _LOGGER_INITIALIZED:
        setup_logger()
    if module_name:
        return logging.getLogger(f"VMS.{module_name}")
    return logging.getLogger("VMS")

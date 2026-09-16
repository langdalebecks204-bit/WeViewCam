# -*- coding: utf-8 -*-
"""
Base device adapter interface.
Defines abstract contracts for multi-vendor surveillance devices (Hikvision, Dahua, ONVIF).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional, Dict, Any


class ProtocolType(str, Enum):
    HIKVISION = "hikvision"
    DAHUA = "dahua"
    ONVIF = "onvif"
    CUSTOM_RTSP = "custom_rtsp"


class PTZCommand(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    UP_LEFT = auto()
    UP_RIGHT = auto()
    DOWN_LEFT = auto()
    DOWN_RIGHT = auto()
    ZOOM_IN = auto()
    ZOOM_OUT = auto()
    FOCUS_NEAR = auto()
    FOCUS_FAR = auto()
    IRIS_OPEN = auto()
    IRIS_CLOSE = auto()


class PlaybackCommand(Enum):
    START = auto()
    PAUSE = auto()
    RESTART = auto()
    FAST = auto()      # Speed up (2x, 4x, 8x, 16x)
    SLOW = auto()      # Slow down (1/2, 1/4, 1/8)
    NORMAL = auto()    # Restore normal 1x speed
    STEP_FRAME = auto() # Step forward single frame
    GET_POS = auto()   # Get playback progress (0-100)
    SET_POS = auto()   # Seek to progress percentage (0-100)


@dataclass
class ChannelInfo:
    channel_no: int                 # Physical or logical channel number
    name: str                       # e.g. "Camera 01" / "D1"
    is_online: bool = True
    is_ptz: bool = False
    device_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceInfo:
    device_id: str                  # Unique identifier (UUID or host:port)
    name: str                       # Display name
    ip: str                         # IP address or hostname
    port: int = 8000                # Management / SDK port
    username: str = "admin"
    password: str = ""
    protocol: ProtocolType = ProtocolType.HIKVISION
    rtsp_port: int = 554
    channels: List[ChannelInfo] = field(default_factory=list)
    is_connected: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordSegment:
    channel_no: int
    start_time: datetime
    end_time: datetime
    file_name: str = ""
    file_size: int = 0              # Bytes
    record_type: str = "schedule"   # schedule / alarm / manual / motion


class BaseDeviceAdapter(ABC):
    """
    Abstract interface for surveillance hardware adapters.
    Each camera/NVR manufacturer implements this contract.
    """

    def __init__(self, device_info: DeviceInfo):
        self.device_info = device_info
        self._is_logged_in = False

    @property
    def is_connected(self) -> bool:
        return self._is_logged_in

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    @abstractmethod
    def login(self) -> bool:
        """Connect and authenticate with the device/NVR."""
        pass

    @abstractmethod
    def logout(self) -> bool:
        """Disconnect and release session resources."""
        pass

    @abstractmethod
    def get_channels(self) -> List[ChannelInfo]:
        """Enumerate active camera channels from NVR or IPC."""
        pass

    @abstractmethod
    def start_real_play(
        self,
        channel_no: int,
        win_id: int,
        stream_type: int = 0
    ) -> int:
        """
        Start live video preview.
        :param channel_no: Channel number.
        :param win_id: Native X11 window handle (winId) for direct rendering, or 0.
        :param stream_type: 0 for Main stream (high-res), 1 for Sub stream (low-res).
        :return: RealPlay handle or positive session id, -1 if failed.
        """
        pass

    @abstractmethod
    def stop_real_play(self, play_handle: int) -> bool:
        """Stop real-time preview session."""
        pass

    @abstractmethod
    def capture_picture(self, play_handle: int, save_path: str) -> bool:
        """Capture current video frame to image file (BMP/JPEG)."""
        pass

    @abstractmethod
    def start_record(self, play_handle: int, save_path: str) -> bool:
        """Start saving live stream to a local video file (MP4)."""
        pass

    @abstractmethod
    def stop_record(self, play_handle: int) -> bool:
        """Stop local video recording."""
        pass

    @abstractmethod
    def ptz_control(
        self,
        channel_no: int,
        command: PTZCommand,
        stop: bool = False,
        speed: int = 4,
        play_handle: int = -1
    ) -> bool:
        """Control Pan-Tilt-Zoom."""
        pass

    @abstractmethod
    def find_records(
        self,
        channel_no: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[RecordSegment]:
        """Search for historical recordings on the device/NVR storage."""
        pass

    @abstractmethod
    def start_playback_by_time(
        self,
        channel_no: int,
        win_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """
        Start recording playback by time range.
        :return: Playback handle or positive session id, -1 if failed.
        """
        pass

    @abstractmethod
    def playback_control(
        self,
        playback_handle: int,
        command: PlaybackCommand,
        param: int = 0
    ) -> bool:
        """Control playback state: Pause, Resume, Fast, Slow, Step, Seek."""
        pass

    @abstractmethod
    def get_playback_pos(self, playback_handle: int) -> int:
        """Get playback progress from 0 to 100%."""
        pass

    @abstractmethod
    def stop_playback(self, playback_handle: int) -> bool:
        """Stop playback session."""
        pass

    @abstractmethod
    def download_record_by_time(
        self,
        channel_no: int,
        start_time: datetime,
        end_time: datetime,
        save_path: str
    ) -> int:
        """Start downloading recording segment to local file."""
        pass

    @abstractmethod
    def get_download_pos(self, download_handle: int) -> int:
        """Get download progress percentage (0-100)."""
        pass

    @abstractmethod
    def stop_download(self, download_handle: int) -> bool:
        """Stop and cancel downloading."""
        pass

    def refresh_play(self, play_handle: int, win_id: int = 0) -> bool:
        """Notify video renderer to adapt to new window resolution upon resize."""
        return True

    def refresh_playback(self, playback_handle: int, win_id: int = 0) -> bool:
        """Notify playback renderer to adapt to new window resolution upon resize."""
        return True


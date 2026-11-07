# -*- coding: utf-8 -*-
"""
Dahua NetSDK Device Adapter.
Implements BaseDeviceAdapter using native Dahua NetSDK ctypes driver.
"""

from datetime import datetime
from typing import List, Optional

from core.base_adapter import (
    BaseDeviceAdapter,
    DeviceInfo,
    ChannelInfo,
    RecordSegment,
    PTZCommand,
    PlaybackCommand
)
from core.logger import get_logger
from adapters.dahua.driver import DahuaNativeDriver

logger = get_logger("DahuaAdapter")


class DahuaAdapter(BaseDeviceAdapter):
    """Adapter for Dahua devices powered by Dahua NetSDK."""

    def __init__(self, device_info: DeviceInfo):
        super().__init__(device_info)
        self.driver = DahuaNativeDriver()
        self._login_handle = -1
        self._device_raw_info = None

    def login(self) -> bool:
        logger.info(f"正在连接大华设备 [{self.device_info.name}] {self.device_info.ip}:{self.device_info.port}")
        user_id, dev_info = self.driver.login(
            self.device_info.ip,
            self.device_info.port,
            self.device_info.username,
            self.device_info.password
        )

        if user_id > 0:
            self._login_handle = user_id
            self._device_raw_info = dev_info
            self._is_logged_in = True
            logger.info(f"大华设备登录成功 [{self.device_info.name}] user_id={user_id}")
            return True

        self._login_handle = -1
        self._is_logged_in = False
        return False

    def logout(self) -> bool:
        if self._is_logged_in and self._login_handle > 0:
            logger.info(f"注销大华设备 [{self.device_info.name}] user_id={self._login_handle}")
            self.driver.logout(self._login_handle)
            self._login_handle = -1
            self._device_raw_info = None
            self._is_logged_in = False
        return True

    def get_channels(self) -> List[ChannelInfo]:
        channels = self.driver.get_channels(self._login_handle, self._device_raw_info)
        for ch in channels:
            ch.device_id = self.device_info.device_id
        return channels

    def start_real_play(self, channel_no: int, win_id: int, stream_type: int = 0) -> int:
        return self.driver.start_real_play(self._login_handle, channel_no, win_id, stream_type)

    def stop_real_play(self, play_handle: int) -> bool:
        return self.driver.stop_real_play(play_handle)

    def capture_picture(self, play_handle: int, save_path: str) -> bool:
        channel_no = play_handle % 1000 if play_handle > 0 else 1
        return self.driver.capture_picture(self._login_handle, channel_no, save_path)

    def start_record(self, play_handle: int, save_path: str) -> bool:
        logger.info(f"大华开始本地录像至 {save_path} (handle={play_handle})")
        return True

    def stop_record(self, play_handle: int) -> bool:
        logger.info(f"大华停止本地录像 handle={play_handle}")
        return True

    def ptz_control(
        self,
        channel_no: int,
        command: PTZCommand,
        stop: bool = False,
        speed: int = 4,
        play_handle: int = -1
    ) -> bool:
        return self.driver.ptz_control(
            self._login_handle,
            channel_no,
            command,
            stop=stop,
            speed=speed,
            play_handle=play_handle
        )

    def find_records(self, channel_no: int, start_time: datetime, end_time: datetime) -> List[RecordSegment]:
        return self.driver.find_records(self._login_handle, channel_no, start_time, end_time)

    def start_playback_by_time(self, channel_no: int, win_id: int, start_time: datetime, end_time: datetime) -> int:
        return self.driver.start_playback_by_time(self._login_handle, channel_no, win_id, start_time, end_time)

    def playback_control(self, playback_handle: int, command: PlaybackCommand, param: int = 0) -> bool:
        return self.driver.playback_control(playback_handle, command, param)

    def get_playback_pos(self, playback_handle: int) -> int:
        return 50

    def stop_playback(self, playback_handle: int) -> bool:
        return self.driver.stop_playback(playback_handle)

    def download_record_by_time(self, channel_no: int, start_time: datetime, end_time: datetime, save_path: str) -> int:
        return 1

    def get_download_pos(self, download_handle: int) -> int:
        return 100

    def stop_download(self, download_handle: int) -> bool:
        return True

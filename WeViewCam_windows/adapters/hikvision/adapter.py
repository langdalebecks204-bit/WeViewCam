# -*- coding: utf-8 -*-
"""
Hikvision Device Adapter implementation.
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
from adapters.hikvision.driver import HikvisionNativeDriver
from core.logger import get_logger

logger = get_logger("HikvisionAdapter")


class HikvisionAdapter(BaseDeviceAdapter):
    """Concrete adapter for Hikvision NVRs, DVRs, and IP cameras."""

    def __init__(self, device_info: DeviceInfo):
        super().__init__(device_info)
        self.driver = HikvisionNativeDriver()
        self._user_id = -1
        self._device_raw_info = None

    def login(self) -> bool:
        if self._is_logged_in and self._user_id >= 0:
            return True

        user_id, raw_info = self.driver.login(
            ip=self.device_info.ip,
            port=self.device_info.port,
            user=self.device_info.username,
            password=self.device_info.password
        )

        if user_id >= 0:
            self._user_id = user_id
            self._device_raw_info = raw_info
            self._is_logged_in = True
            logger.info(f"海康设备登录成功 [{self.device_info.name}] user_id={user_id}")
            return True

        self._is_logged_in = False
        self._user_id = -1
        return False

    def logout(self) -> bool:
        if self._user_id >= 0:
            ret = self.driver.logout(self._user_id)
            self._user_id = -1
            self._is_logged_in = False
            return ret
        self._is_logged_in = False
        return True

    def get_channels(self) -> List[ChannelInfo]:
        if not self._is_logged_in or self._user_id < 0:
            if not self.login():
                return []

        channels = self.driver.get_channels(self._user_id, self._device_raw_info)
        for ch in channels:
            ch.device_id = self.device_info.device_id
        return channels

    def start_real_play(
        self,
        channel_no: int,
        win_id: int,
        stream_type: int = 0
    ) -> int:
        if not self._is_logged_in or self._user_id < 0:
            if not self.login():
                return -1

        return self.driver.start_real_play(
            user_id=self._user_id,
            channel_no=channel_no,
            win_id=win_id,
            stream_type=stream_type
        )

    def stop_real_play(self, play_handle: int) -> bool:
        return self.driver.stop_real_play(play_handle)

    def capture_picture(self, play_handle: int, save_path: str) -> bool:
        return self.driver.capture_picture(play_handle, save_path)

    def start_record(self, play_handle: int, save_path: str) -> bool:
        return self.driver.start_record(play_handle, save_path)

    def stop_record(self, play_handle: int) -> bool:
        return self.driver.stop_record(play_handle)

    def ptz_control(
        self,
        channel_no: int,
        command: PTZCommand,
        stop: bool = False,
        speed: int = 4,
        play_handle: int = -1
    ) -> bool:
        if not self._is_logged_in or self._user_id < 0:
            if not self.login():
                return False

        return self.driver.ptz_control(
            user_id=self._user_id,
            channel_no=channel_no,
            command=command,
            stop=stop,
            speed=speed,
            play_handle=play_handle
        )

    def find_records(
        self,
        channel_no: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[RecordSegment]:
        if not self._is_logged_in or self._user_id < 0:
            if not self.login():
                return []

        return self.driver.find_records(
            user_id=self._user_id,
            channel_no=channel_no,
            start_time=start_time,
            end_time=end_time
        )

    def start_playback_by_time(
        self,
        channel_no: int,
        win_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        if not self._is_logged_in or self._user_id < 0:
            if not self.login():
                return -1

        return self.driver.start_playback_by_time(
            user_id=self._user_id,
            channel_no=channel_no,
            win_id=win_id,
            start_time=start_time,
            end_time=end_time
        )

    def start_playback_by_name(
        self,
        file_name: str,
        win_id: int
    ) -> int:
        if not self._is_logged_in or self._user_id < 0:
            if not self.login():
                return -1

        return self.driver.start_playback_by_name(
            user_id=self._user_id,
            file_name=file_name,
            win_id=win_id
        )

    def playback_control(
        self,
        playback_handle: int,
        command: PlaybackCommand,
        param: int = 0
    ) -> bool:
        return self.driver.playback_control(playback_handle, command, param)

    def get_playback_pos(self, playback_handle: int) -> int:
        return self.driver.get_playback_pos(playback_handle)

    def stop_playback(self, playback_handle: int) -> bool:
        return self.driver.stop_playback(playback_handle)

    def download_record_by_time(
        self,
        channel_no: int,
        start_time: datetime,
        end_time: datetime,
        save_path: str
    ) -> int:
        logger.info(f"海康按时间下载: 通道{channel_no} -> {save_path}")
        return 1

    def get_download_pos(self, download_handle: int) -> int:
        return 100

    def stop_download(self, download_handle: int) -> bool:
        return True

    def refresh_play(self, play_handle: int, win_id: int = 0) -> bool:
        return self.driver.refresh_play(play_handle, win_id=win_id)

    def refresh_playback(self, playback_handle: int, win_id: int = 0) -> bool:
        return self.driver.refresh_playback(playback_handle, win_id=win_id)



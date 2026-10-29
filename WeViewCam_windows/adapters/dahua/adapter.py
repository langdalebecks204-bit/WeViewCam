# -*- coding: utf-8 -*-
"""
Dahua NetSDK Device Adapter (Stub/Extension skeleton).
Ready for plugging in libdhnetsdk.so when required.
"""

from datetime import datetime
from typing import List

from core.base_adapter import (
    BaseDeviceAdapter,
    DeviceInfo,
    ChannelInfo,
    RecordSegment,
    PTZCommand,
    PlaybackCommand
)
from core.logger import get_logger

logger = get_logger("DahuaAdapter")


class DahuaAdapter(BaseDeviceAdapter):
    """Adapter for Dahua devices (Pre-configured extension point)."""

    def __init__(self, device_info: DeviceInfo):
        super().__init__(device_info)
        self._login_handle = -1

    def login(self) -> bool:
        logger.info(f"正在连接大华设备 [{self.device_info.name}] {self.device_info.ip}:{self.device_info.port}")
        # When Dahua NetSDK .so is integrated:
        # CLIENT_Init / CLIENT_LoginEx2
        self._login_handle = 5001
        self._is_logged_in = True
        return True

    def logout(self) -> bool:
        if self._is_logged_in:
            logger.info(f"注销大华设备 [{self.device_info.name}]")
            self._login_handle = -1
            self._is_logged_in = False
        return True

    def get_channels(self) -> List[ChannelInfo]:
        return [
            ChannelInfo(channel_no=1, name="大华通道 1", is_online=True, is_ptz=True, device_id=self.device_info.device_id),
            ChannelInfo(channel_no=2, name="大华通道 2", is_online=True, is_ptz=False, device_id=self.device_info.device_id),
        ]

    def start_real_play(self, channel_no: int, win_id: int, stream_type: int = 0) -> int:
        logger.info(f"大华开启实时预览 通道 {channel_no} (winId: {win_id})")
        return 5100 + channel_no

    def stop_real_play(self, play_handle: int) -> bool:
        logger.info(f"大华停止实时预览 handle={play_handle}")
        return True

    def capture_picture(self, play_handle: int, save_path: str) -> bool:
        logger.info(f"大华抓图保存至 {save_path}")
        return True

    def start_record(self, play_handle: int, save_path: str) -> bool:
        logger.info(f"大华开始录像至 {save_path}")
        return True

    def stop_record(self, play_handle: int) -> bool:
        logger.info(f"大华停止录像 handle={play_handle}")
        return True

    def ptz_control(self, channel_no: int, command: PTZCommand, stop: bool = False, speed: int = 4, play_handle: int = -1) -> bool:
        logger.debug(f"大华云台控制: {command.name}, stop={stop}, speed={speed}, handle={play_handle}")
        return True

    def find_records(self, channel_no: int, start_time: datetime, end_time: datetime) -> List[RecordSegment]:
        day_str = start_time.strftime("%Y-%m-%d")
        return [
            RecordSegment(
                channel_no=channel_no,
                start_time=datetime.strptime(f"{day_str} 08:00:00", "%Y-%m-%d %H:%M:%S"),
                end_time=datetime.strptime(f"{day_str} 18:00:00", "%Y-%m-%d %H:%M:%S"),
                file_name=f"dahua_ch{channel_no}_{day_str}.mp4",
                file_size=1024 * 1024 * 500
            )
        ]

    def start_playback_by_time(self, channel_no: int, win_id: int, start_time: datetime, end_time: datetime) -> int:
        logger.info(f"大华开始按时间回放 通道 {channel_no}: {start_time} - {end_time}")
        return 5200 + channel_no

    def playback_control(self, playback_handle: int, command: PlaybackCommand, param: int = 0) -> bool:
        logger.debug(f"大华回放控制: {command.name}")
        return True

    def get_playback_pos(self, playback_handle: int) -> int:
        return 50

    def stop_playback(self, playback_handle: int) -> bool:
        logger.info(f"大华停止回放 handle={playback_handle}")
        return True

    def download_record_by_time(self, channel_no: int, start_time: datetime, end_time: datetime, save_path: str) -> int:
        return 1

    def get_download_pos(self, download_handle: int) -> int:
        return 100

    def stop_download(self, download_handle: int) -> bool:
        return True

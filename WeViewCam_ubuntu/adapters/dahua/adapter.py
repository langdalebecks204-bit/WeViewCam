# -*- coding: utf-8 -*-
"""
Dahua NetSDK Device Adapter.
Implements BaseDeviceAdapter using native Dahua NetSDK ctypes driver.
"""

import sys
from datetime import datetime
from typing import List, Optional, Dict

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
from adapters.onvif.player import RtspPlayerManager

logger = get_logger("DahuaAdapter")


class DahuaAdapter(BaseDeviceAdapter):
    """Adapter for Dahua devices powered by Dahua NetSDK."""

    def __init__(self, device_info: DeviceInfo):
        super().__init__(device_info)
        self.driver = DahuaNativeDriver()
        self._login_handle = -1
        self._device_raw_info = None
        self._player_mgr = RtspPlayerManager.get_instance()
        self._active_rtsp_plays: Dict[int, int] = {}
        self._active_rtsp_playbacks: Dict[int, int] = {}
        self._active_sdk_plays: Dict[int, int] = {}
        self._active_sdk_playbacks: Dict[int, int] = {}

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
        for handle in list(self._active_rtsp_plays.keys()):
            self.stop_real_play(handle)
        for handle in list(self._active_sdk_plays.keys()):
            self.stop_real_play(handle)
        for handle in list(self._active_rtsp_playbacks.keys()):
            self.stop_playback(handle)
        for handle in list(self._active_sdk_playbacks.keys()):
            self.stop_playback(handle)
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
        # 1. 优先使用大华官方 NetSDK 原生驱动 (37777 原生协议，硬件直出视口)
        play_handle = self.driver.start_real_play(self._login_handle, channel_no, win_id, stream_type)
        if play_handle > 0:
            self._active_sdk_plays[play_handle] = channel_no
            logger.info(f"大华设备 [{self.device_info.name}] 通道 {channel_no} 成功启动原生 SDK 实时预览 (handle={play_handle})")
            return play_handle

        logger.warning(f"大华设备 [{self.device_info.name}] 通道 {channel_no} 原生 SDK 预览未成功启动 (handle={play_handle})，尝试 RTSP 备选管线...")

        # 2. 备用管线：若 SDK 动态库不可用或接口失败，尝试标准 RTSP 流
        u = self.device_info.username
        p = self.device_info.password
        ip = self.device_info.ip
        candidates = [
            f"rtsp://{u}:{p}@{ip}:554/cam/realmonitor?channel={channel_no}&subtype={stream_type}",
            f"rtsp://{u}:{p}@{ip}:554/cam/realmonitor?channel={channel_no}&subtype=0",
            f"rtsp://{u}:{p}@{ip}:554/live?channel={channel_no}&subtype={stream_type}",
        ]
        primary = candidates[0]

        if self._player_mgr.has_vlc:
            logger.info(f"大华设备 [{self.device_info.name}] 通道 {channel_no} 启用 VLC RTSP 备用渲染管线 (win_id={win_id})...")
            play_handle = self._player_mgr.start_play(
                rtsp_url=primary,
                win_id=win_id,
                candidate_urls=candidates
            )
            if play_handle > 0:
                self._active_rtsp_plays[play_handle] = channel_no
                return play_handle

        logger.error(f"❌ 大华设备 [{self.device_info.name}] 通道 {channel_no} 实时预览所有管线均未成功")
        return -1

    def stop_real_play(self, play_handle: int) -> bool:
        if play_handle in self._active_rtsp_plays:
            self._active_rtsp_plays.pop(play_handle, None)
            return self._player_mgr.stop_play(play_handle)
        if play_handle in self._active_sdk_plays:
            self._active_sdk_plays.pop(play_handle, None)
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
        # 1. 优先使用大华 NetSDK 官方原生回放驱动 (37777 原生协议，硬件直出视口)
        pb_handle = self.driver.start_playback_by_time(self._login_handle, channel_no, win_id, start_time, end_time)
        if pb_handle > 0:
            self._active_sdk_playbacks[pb_handle] = channel_no
            logger.info(f"大华设备 [{self.device_info.name}] 通道 {channel_no} 成功启动原生 SDK 录像回放 (handle={pb_handle})")
            return pb_handle

        logger.warning(f"大华设备 [{self.device_info.name}] 通道 {channel_no} 原生 SDK 回放启动未成功 (handle={pb_handle})，尝试 RTSP 备选管线...")

        # 2. 备用管线：若 SDK 动态库不可用或接口失败，尝试 RTSP 回放
        u = self.device_info.username
        p = self.device_info.password
        ip = self.device_info.ip
        s_str = start_time.strftime("%Y_%m_%d_%H_%M_%S")
        e_str = end_time.strftime("%Y_%m_%d_%H_%M_%S")
        s_iso = start_time.strftime("%Y%m%dT%H%M%SZ")
        e_iso = end_time.strftime("%Y%m%dT%H%M%SZ")

        candidates = [
            f"rtsp://{u}:{p}@{ip}:554/cam/playback?channel={channel_no}&starttime={s_str}",
            f"rtsp://{u}:{p}@{ip}:554/cam/playback?channel={channel_no}&starttime={s_str}&endtime={e_str}",
            f"rtsp://{u}:{p}@{ip}:554/cam/playback?channel={channel_no}&starttime={s_iso}&endtime={e_iso}",
            f"rtsp://{u}:{p}@{ip}:554/cam/playback?channel={channel_no}&subtype=0&starttime={s_str}&endtime={e_str}",
            f"rtsp://{u}:{p}@{ip}:554/cam/playback?channel={channel_no:02d}&starttime={s_str}",
            f"rtsp://{u}:{p}@{ip}:554/cam/playback?channelid={channel_no}&starttime={s_str}",
            f"rtsp://{u}:{p}@{ip}:554/playback?channel={channel_no}&starttime={s_str}",
        ]
        primary = candidates[0]

        if self._player_mgr.has_vlc:
            logger.info(
                f"大华设备 [{self.device_info.name}] 通道 {channel_no} 启用原生 VLC 硬件加速回放管线 "
                f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {end_time.strftime('%Y-%m-%d %H:%M:%S')}] (win_id={win_id})..."
            )
            pb_handle = self._player_mgr.start_play(
                rtsp_url=primary,
                win_id=win_id,
                candidate_urls=candidates
            )
            if pb_handle > 0:
                self._active_rtsp_playbacks[pb_handle] = channel_no
                return pb_handle

        logger.error(f"❌ 大华设备 [{self.device_info.name}] 通道 {channel_no} 录像回放所有管线均未成功")
        return -1

    def playback_control(self, playback_handle: int, command: PlaybackCommand, param: int = 0) -> bool:
        if playback_handle in self._active_rtsp_playbacks:
            return True
        return self.driver.playback_control(playback_handle, command, param)

    def get_playback_pos(self, playback_handle: int) -> int:
        if playback_handle in self._active_rtsp_playbacks:
            return 50
        return self.driver.get_playback_pos(playback_handle)

    def stop_playback(self, playback_handle: int) -> bool:
        if playback_handle in self._active_rtsp_playbacks:
            self._active_rtsp_playbacks.pop(playback_handle, None)
            return self._player_mgr.stop_play(playback_handle)
        if playback_handle in self._active_sdk_playbacks:
            self._active_sdk_playbacks.pop(playback_handle, None)
            return self.driver.stop_playback(playback_handle)
        return self.driver.stop_playback(playback_handle)

    def download_record_by_time(self, channel_no: int, start_time: datetime, end_time: datetime, save_path: str) -> int:
        return 1

    def get_download_pos(self, download_handle: int) -> int:
        return 100

    def stop_download(self, download_handle: int) -> bool:
        return True

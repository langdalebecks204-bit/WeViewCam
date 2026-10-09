# -*- coding: utf-8 -*-
"""
Player Controller.
Orchestrates multiple video viewing slots, mapping display windows to active stream handles.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from core.base_adapter import (
    BaseDeviceAdapter,
    PlaybackCommand,
    PTZCommand
)
from core.device_manager import DeviceManager
from core.logger import get_logger

logger = get_logger("PlayerController")


@dataclass
class SlotState:
    slot_id: int
    win_id: int = 0
    device_id: str = ""
    channel_no: int = 0
    channel_name: str = ""
    is_live: bool = False
    is_playback: bool = False
    is_recording: bool = False
    play_handle: int = -1
    playback_handle: int = -1
    record_path: str = ""
    stream_type: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class PlayerController:
    """Manages multi-screen viewports, streams, playback sessions and captures."""

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self._slots: Dict[int, SlotState] = {}

    def get_slot_state(self, slot_id: int) -> SlotState:
        if slot_id not in self._slots:
            self._slots[slot_id] = SlotState(slot_id=slot_id)
        return self._slots[slot_id]

    def set_slot_window(self, slot_id: int, win_id: int):
        slot = self.get_slot_state(slot_id)
        slot.win_id = win_id

    def start_live_play(
        self,
        slot_id: int,
        device_id: str,
        channel_no: int,
        win_id: int = 0,
        stream_type: int = 0,
        channel_name: str = ""
    ) -> bool:
        """Start live view in the specified slot."""
        slot = self.get_slot_state(slot_id)
        
        # If slot is already playing something, stop it first
        if slot.is_live or slot.is_playback:
            self.stop_slot(slot_id)

        target_win_id = win_id if win_id != 0 else slot.win_id

        # Ensure device is connected
        adapter = self.device_manager.get_adapter(device_id)
        if not adapter:
            logger.error(f"无法获取设备 {device_id} 的适配器")
            return False

        if not adapter.is_connected:
            if not self.device_manager.connect_device(device_id):
                logger.error(f"设备 {device_id} 连接失败，无法播放")
                return False

        play_handle = adapter.start_real_play(
            channel_no=channel_no,
            win_id=target_win_id,
            stream_type=stream_type
        )

        if play_handle < 0:
            logger.error(f"槽位 {slot_id} 通道 {channel_no} 开启实时预览失败")
            return False

        slot.device_id = device_id
        slot.channel_no = channel_no
        slot.channel_name = channel_name or f"Ch {channel_no}"
        slot.win_id = target_win_id
        slot.stream_type = stream_type
        slot.play_handle = play_handle
        slot.is_live = True
        slot.is_playback = False

        logger.info(f"槽位 [{slot_id}] 开始实时预览: {slot.channel_name} (句柄: {play_handle})")
        return True

    def start_playback(
        self,
        slot_id: int,
        device_id: str,
        channel_no: int,
        start_time: datetime,
        end_time: datetime,
        win_id: int = 0,
        channel_name: str = ""
    ) -> bool:
        """Start recording playback in the specified slot."""
        slot = self.get_slot_state(slot_id)
        if slot.is_live or slot.is_playback:
            self.stop_slot(slot_id)

        target_win_id = win_id if win_id != 0 else slot.win_id

        adapter = self.device_manager.get_adapter(device_id)
        if not adapter:
            logger.error(f"无法获取设备 {device_id} 的适配器")
            return False

        if not adapter.is_connected:
            if not self.device_manager.connect_device(device_id):
                logger.error(f"设备 {device_id} 连接失败，无法回放")
                return False

        pb_handle = adapter.start_playback_by_time(
            channel_no=channel_no,
            win_id=target_win_id,
            start_time=start_time,
            end_time=end_time
        )

        if pb_handle < 0:
            logger.error(f"槽位 {slot_id} 通道 {channel_no} 按时间回放开启失败")
            return False

        slot.device_id = device_id
        slot.channel_no = channel_no
        slot.channel_name = channel_name or f"Ch {channel_no}"
        slot.win_id = target_win_id
        slot.start_time = start_time
        slot.end_time = end_time
        slot.playback_handle = pb_handle
        slot.is_live = False
        slot.is_playback = True

        logger.info(f"槽位 [{slot_id}] 开启录像回放: {slot.channel_name} (句柄: {pb_handle})")
        return True

    def control_playback(self, slot_id: int, command: PlaybackCommand, param: int = 0) -> bool:
        """Issue playback controls to active playback slot."""
        slot = self.get_slot_state(slot_id)
        if not slot.is_playback or slot.playback_handle < 0:
            return False

        adapter = self.device_manager.get_adapter(slot.device_id)
        if not adapter:
            return False

        return adapter.playback_control(slot.playback_handle, command, param)

    def get_playback_pos(self, slot_id: int) -> int:
        """Query 0-100% progress for active playback slot."""
        slot = self.get_slot_state(slot_id)
        if not slot.is_playback or slot.playback_handle < 0:
            return 0

        adapter = self.device_manager.get_adapter(slot.device_id)
        if not adapter:
            return 0

        return adapter.get_playback_pos(slot.playback_handle)

    def stop_slot(self, slot_id: int) -> bool:
        """Stop video stream on the given slot."""
        slot = self.get_slot_state(slot_id)
        adapter = self.device_manager.get_adapter(slot.device_id) if slot.device_id else None

        if slot.is_recording and adapter and slot.play_handle >= 0:
            try:
                adapter.stop_record(slot.play_handle)
            except Exception as e:
                logger.warning(f"停止录像异常: {e}")
            slot.is_recording = False

        if slot.is_live and adapter and slot.play_handle >= 0:
            try:
                adapter.stop_real_play(slot.play_handle)
            except Exception as e:
                logger.warning(f"停止预览异常: {e}")

        if slot.is_playback and adapter and slot.playback_handle >= 0:
            try:
                adapter.stop_playback(slot.playback_handle)
            except Exception as e:
                logger.warning(f"停止回放异常: {e}")

        slot.is_live = False
        slot.is_playback = False
        slot.is_recording = False
        slot.play_handle = -1
        slot.playback_handle = -1
        slot.device_id = ""
        slot.channel_no = 0
        slot.channel_name = ""
        return True

    def capture_slot(self, slot_id: int, save_path: str) -> bool:
        """Capture screenshot from video stream in slot."""
        slot = self.get_slot_state(slot_id)
        adapter = self.device_manager.get_adapter(slot.device_id)
        if not adapter:
            return False

        handle = slot.play_handle if slot.is_live else slot.playback_handle
        if handle < 0:
            return False

        return adapter.capture_picture(handle, save_path)

    def toggle_record_slot(self, slot_id: int, save_path: str) -> Tuple[bool, bool]:
        """
        Toggle local MP4 recording.
        Returns: (success, is_recording_now)
        """
        slot = self.get_slot_state(slot_id)
        adapter = self.device_manager.get_adapter(slot.device_id)
        if not adapter or slot.play_handle < 0:
            return False, False

        if slot.is_recording:
            # Stop recording
            ret = adapter.stop_record(slot.play_handle)
            slot.is_recording = False
            slot.record_path = ""
            return ret, False
        else:
            # Start recording
            ret = adapter.start_record(slot.play_handle, save_path)
            if ret:
                slot.is_recording = True
                slot.record_path = save_path
            return ret, slot.is_recording

    def ptz_control(
        self,
        slot_id: int,
        command: PTZCommand,
        stop: bool = False,
        speed: int = 4
    ) -> bool:
        """Send PTZ command for currently active channel in slot."""
        slot = self.get_slot_state(slot_id)
        if not slot.is_live or slot.channel_no <= 0:
            return False

        adapter = self.device_manager.get_adapter(slot.device_id)
        if not adapter:
            return False

        return adapter.ptz_control(
            slot.channel_no,
            command,
            stop=stop,
            speed=speed,
            play_handle=slot.play_handle
        )

    def refresh_slot(self, slot_id: int, win_id: Optional[int] = None):
        """Notify active stream in slot that display window dimensions changed."""
        slot = self.get_slot_state(slot_id)
        if not slot or not slot.device_id:
            return

        w_id = win_id if win_id is not None and win_id > 0 else slot.win_id
        if win_id and win_id > 0:
            slot.win_id = win_id

        adapter = self.device_manager.get_adapter(slot.device_id)
        if not adapter:
            return

        if slot.is_live and slot.play_handle >= 0:
            adapter.refresh_play(slot.play_handle, win_id=w_id)
        elif slot.is_playback and slot.playback_handle >= 0:
            adapter.refresh_playback(slot.playback_handle, win_id=w_id)

    def reopen_live_play(self, slot_id: int, win_id: Optional[int] = None) -> bool:
        """
        Seamlessly reinitialize live preview stream on slot.
        Used when window geometry changes significantly (maximize/restore/layout switch)
        to guarantee that the SDK hardware decoder adapts 100% to the new window dimensions.
        """
        slot = self.get_slot_state(slot_id)
        if not slot.is_live or not slot.device_id or slot.channel_no <= 0:
            return False

        device_id = slot.device_id
        channel_no = slot.channel_no
        channel_name = slot.channel_name
        stream_type = slot.stream_type
        w_id = win_id if win_id is not None and win_id > 0 else slot.win_id
        if win_id and win_id > 0:
            slot.win_id = win_id

        adapter = self.device_manager.get_adapter(device_id)
        if not adapter:
            return False

        was_recording = slot.is_recording
        rec_path = slot.record_path

        # 1. Stop old handle
        old_handle = slot.play_handle
        if was_recording and old_handle >= 0:
            try:
                adapter.stop_record(old_handle)
            except Exception:
                pass

        if old_handle >= 0:
            try:
                adapter.stop_real_play(old_handle)
            except Exception as e:
                logger.warning(f"视口 {slot_id + 1} 停止原流异常: {e}")

        # 2. Restart real play with the new X11 window geometry
        new_handle = adapter.start_real_play(channel_no, w_id, stream_type)
        if new_handle >= 0:
            slot.play_handle = new_handle
            slot.is_live = True

            # Resume local recording if it was active
            if was_recording and rec_path:
                try:
                    adapter.start_record(new_handle, rec_path)
                    slot.is_recording = True
                except Exception as e:
                    logger.warning(f"视口 {slot_id + 1} 恢复录像异常: {e}")

            logger.info(f"视口 {slot_id + 1} 已无缝重开流适配新窗口分辨率: handle={new_handle}")
            return True
        else:
            slot.play_handle = -1
            slot.is_live = False
            logger.warning(f"视口 {slot_id + 1} 重开流失败")
            return False

    def reopen_playback(
        self,
        slot_id: int,
        current_time: Optional[datetime] = None,
        win_id: Optional[int] = None
    ) -> bool:
        """
        Seamlessly restart playback on slot at new resolution from current position.
        """
        slot = self.get_slot_state(slot_id)
        if not slot.is_playback or not slot.device_id or slot.channel_no <= 0:
            return False

        device_id = slot.device_id
        channel_no = slot.channel_no
        channel_name = slot.channel_name
        w_id = win_id if win_id is not None and win_id > 0 else slot.win_id
        if win_id and win_id > 0:
            slot.win_id = win_id

        start_t = current_time or slot.start_time
        end_t = slot.end_time

        adapter = self.device_manager.get_adapter(device_id)
        if not adapter:
            return False

        old_handle = slot.playback_handle
        if old_handle >= 0:
            try:
                adapter.stop_playback(old_handle)
            except Exception as e:
                logger.warning(f"停止回放原流异常: {e}")

        new_handle = adapter.start_playback_by_time(channel_no, start_t, end_t, w_id)
        if new_handle >= 0:
            slot.playback_handle = new_handle
            slot.is_playback = True
            slot.start_time = start_t
            logger.info(f"回放视口 {slot_id} 已无缝重开流适配新分辨率: handle={new_handle}")
            return True
        else:
            slot.playback_handle = -1
            slot.is_playback = False
            return False

    def stop_all(self):
        """Stop all playing slots on application exit."""
        for slot_id in list(self._slots.keys()):
            self.stop_slot(slot_id)
        logger.info("已停止所有视口播放会话")



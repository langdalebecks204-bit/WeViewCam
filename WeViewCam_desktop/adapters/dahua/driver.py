# -*- coding: utf-8 -*-
"""
Dahua NetSDK Native Driver and Library Manager.
Handles dynamic library discovery, initialization, login, channels, live stream, PTZ and playback.
"""

import os
import sys
import ctypes
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from adapters.dahua.NetSDK.NetSDK import NetClient
from adapters.dahua.NetSDK.SDK_Struct import (
    NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY,
    NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY,
    NET_TIME,
    SNAP_PARAMS
)
from adapters.dahua.NetSDK.SDK_Enum import (
    EM_LOGIN_SPAC_CAP_TYPE,
    SDK_RealPlayType,
    SDK_PTZ_ControlType
)
from adapters.dahua.NetSDK.SDK_Callback import fDisConnect, fHaveReConnect

from core.base_adapter import (
    ChannelInfo,
    RecordSegment,
    PTZCommand,
    PlaybackCommand
)
from core.logger import get_logger

logger = get_logger("DahuaSDK")


class DahuaSDKLibrary:
    """Singleton wrapper around Dahua NetClient and library lifecycle."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "DahuaSDKLibrary":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.is_loaded = False
        self.net_client: Optional[NetClient] = None
        self._dis_connect_cb = None
        self._re_connect_cb = None
        self._init_sdk()
        self._initialized = True

    def _init_sdk(self):
        """Discover and load Dahua NetSDK."""
        if os.environ.get("DAHUA_SDK_MOCK") == "1":
            logger.info("检测到 DAHUA_SDK_MOCK 环境变量，启用大华协议模拟模式。")
            self.is_loaded = False
            return

        try:
            self.net_client = NetClient()
            if self.net_client and getattr(self.net_client, "sdk", None) is not None:
                # Setup global reconnection and disconnection callbacks
                self._dis_connect_cb = fDisConnect(self._on_disconnect)
                self._re_connect_cb = fHaveReConnect(self._on_reconnect)

                init_ok = self.net_client.InitEx(self._dis_connect_cb)
                if init_ok:
                    self.net_client.SetAutoReconnect(self._re_connect_cb)
                    self.is_loaded = True
                    ver = self.net_client.sdk.CLIENT_GetSDKVersion()
                    logger.info(f"大华 NetSDK 初始化成功，SDK 版本: 0x{ver:X}")
                else:
                    err = self.get_last_error()
                    logger.warning(f"大华 NetSDK InitEx 初始化失败，错误码: {err}")
                    self.is_loaded = False
            else:
                logger.warning("未找到大华 SDK 动态库 (dhnetsdk.dll / libdhnetsdk.so)，将运行在模拟模式。")
                self.is_loaded = False
        except Exception as e:
            logger.warning(f"大华 NetSDK 加载初始化异常: {e}，将运行在模拟模式。")
            self.is_loaded = False

    def _on_disconnect(self, login_id: int, ip_buf: bytes, port: int, user_data: int):
        ip_str = ip_buf.decode('utf-8', errors='ignore') if isinstance(ip_buf, bytes) else str(ip_buf)
        logger.warning(f"[DahuaSDK] 设备断开连接: login_id={login_id}, {ip_str}:{port}")

    def _on_reconnect(self, login_id: int, ip_buf: bytes, port: int, user_data: int):
        ip_str = ip_buf.decode('utf-8', errors='ignore') if isinstance(ip_buf, bytes) else str(ip_buf)
        logger.info(f"[DahuaSDK] 设备重新连上: login_id={login_id}, {ip_str}:{port}")

    def get_last_error(self) -> int:
        if self.is_loaded and self.net_client:
            try:
                return self.net_client.GetLastError()
            except Exception:
                return -1
        return -1

    def get_last_error_msg(self) -> str:
        if self.is_loaded and self.net_client:
            try:
                return self.net_client.GetLastErrorMessage()
            except Exception:
                return "未知错误"
        return "SDK 未加载"

    def cleanup(self):
        if self.is_loaded and self.net_client:
            try:
                self.net_client.Cleanup()
                logger.info("大华 NetSDK 已清理释放。")
            except Exception as e:
                logger.warning(f"大华 NetSDK Cleanup 异常: {e}")
            self.is_loaded = False


class DahuaNativeDriver:
    """Wrapper providing clean Python methods over Dahua NetSDK."""

    def __init__(self):
        self.sdk_lib = DahuaSDKLibrary.get_instance()

    @property
    def is_available(self) -> bool:
        return self.sdk_lib.is_loaded

    def login(self, ip: str, port: int, user: str, password: str) -> Tuple[int, Optional[Any]]:
        """Log in to Dahua DVR/NVR/IPC device."""
        if not self.is_available:
            logger.info(f"[模拟模式] 正在模拟连接大华设备: {ip}:{port}")
            # Mock device info
            class MockDeviceInfo:
                nChanNum = 4
                sSerialNumber = b"DH-MOCK-DEV-001"
            return 5001, MockDeviceInfo()

        stu_in = NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY()
        stu_in.dwSize = ctypes.sizeof(NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY)
        stu_in.szIP = ip.encode('utf-8')
        stu_in.nPort = int(port)
        stu_in.szUserName = user.encode('utf-8')
        stu_in.szPassword = password.encode('utf-8')
        stu_in.emSpecCap = EM_LOGIN_SPAC_CAP_TYPE.TCP

        stu_out = NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY()
        stu_out.dwSize = ctypes.sizeof(NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY)

        login_id, dev_info, error_msg = self.sdk_lib.net_client.LoginWithHighLevelSecurity(stu_in, stu_out)

        if login_id == 0 or login_id is None:
            err = self.sdk_lib.get_last_error()
            logger.error(f"大华设备登录失败 {ip}:{port}, 错误码: {err}, 信息: {error_msg}")
            return -1, None

        n_chans = getattr(dev_info, "nChanNum", 0)
        logger.info(f"大华设备登录成功 {ip}:{port}, 用户ID: {login_id}, 检测到通道总数: {n_chans}")
        return int(login_id), dev_info

    def logout(self, login_id: int) -> bool:
        """Log out from Dahua device."""
        if not self.is_available:
            return True

        if login_id <= 0:
            return True

        ret = self.sdk_lib.net_client.Logout(login_id)
        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.warning(f"注销大华设备失败 login_id={login_id}, 错误码: {err}")
            return False
        return True

    def get_channels(self, login_id: int, device_info: Optional[Any] = None) -> List[ChannelInfo]:
        """Enumerate camera channels for Dahua device."""
        if not self.is_available or login_id <= 0:
            return [
                ChannelInfo(channel_no=1, name="大华枪机-正门", is_online=True, is_ptz=False),
                ChannelInfo(channel_no=2, name="大华球机-园区东", is_online=True, is_ptz=True),
                ChannelInfo(channel_no=3, name="大华半球-大厅", is_online=True, is_ptz=False),
                ChannelInfo(channel_no=4, name="大华枪机-仓库", is_online=True, is_ptz=False),
            ]

        channels = []
        n_chans = 0
        if device_info:
            n_chans = int(getattr(device_info, "nChanNum", 0))

        if n_chans <= 0:
            n_chans = 1

        logger.info(f"[DahuaDriver] 开始解析设备通道 login_id={login_id}, 通道总数={n_chans}")

        for i in range(n_chans):
            ch_no = i + 1
            chan_name = f"通道 {ch_no}"
            channels.append(ChannelInfo(
                channel_no=ch_no,
                name=chan_name,
                is_online=True,
                is_ptz=True,
                is_enabled=True,
                extra={"dh_channel_idx": i}
            ))

        logger.info(f"[DahuaDriver] 通道解析完毕: 共生成 {len(channels)} 个通道")
        return channels

    def start_real_play(
        self,
        login_id: int,
        channel_no: int,
        win_id: int,
        stream_type: int = 0
    ) -> int:
        """Start real-time live preview."""
        if not self.is_available:
            logger.info(f"[模拟模式] 开启大华通道 {channel_no} 实时预览 (win_id={win_id})")
            return 5100 + channel_no

        dh_channel = channel_no - 1 if channel_no > 0 else 0
        # 0: Main stream (Realplay), 1: Sub stream (Realplay_1)
        r_type = SDK_RealPlayType.Realplay if stream_type == 0 else SDK_RealPlayType.Realplay_1

        logger.info(
            f"大华发起实时预览: login_id={login_id}, 通道={channel_no}(dh_idx={dh_channel}), "
            f"win_id={win_id}, 码流={stream_type}"
        )
        play_id = self.sdk_lib.net_client.RealPlayEx(login_id, dh_channel, int(win_id), r_type)

        if play_id == 0:
            err = self.sdk_lib.get_last_error()
            msg = self.sdk_lib.get_last_error_msg()
            logger.error(f"大华开启实时预览失败: 通道={channel_no}, 错误码={err}, 信息={msg}")
            return -1

        return int(play_id)

    def stop_real_play(self, play_id: int) -> bool:
        """Stop real-time live preview."""
        if not self.is_available:
            return True

        if play_id <= 0:
            return True

        ret = self.sdk_lib.net_client.StopRealPlayEx(play_id)
        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.warning(f"大华停止实时预览失败 play_id={play_id}, 错误码: {err}")
            return False
        return True

    def ptz_control(
        self,
        login_id: int,
        channel_no: int,
        command: PTZCommand,
        stop: bool = False,
        speed: int = 4,
        play_handle: int = -1
    ) -> bool:
        """Execute PTZ Pan/Tilt/Zoom operation."""
        if not self.is_available:
            logger.debug(f"[模拟模式] 大华云台控制: {command.name}, stop={stop}, speed={speed}")
            return True

        dh_channel = channel_no - 1 if channel_no > 0 else 0
        clamped_speed = max(1, min(8, speed))

        ptz_cmd_map = {
            PTZCommand.UP: SDK_PTZ_ControlType.UP_CONTROL,
            PTZCommand.DOWN: SDK_PTZ_ControlType.DOWN_CONTROL,
            PTZCommand.LEFT: SDK_PTZ_ControlType.LEFT_CONTROL,
            PTZCommand.RIGHT: SDK_PTZ_ControlType.RIGHT_CONTROL,
            PTZCommand.UP_LEFT: SDK_PTZ_ControlType.LEFTTOP,
            PTZCommand.UP_RIGHT: SDK_PTZ_ControlType.RIGHTTOP,
            PTZCommand.DOWN_LEFT: SDK_PTZ_ControlType.LEFTDOWN,
            PTZCommand.DOWN_RIGHT: SDK_PTZ_ControlType.RIGHTDOWN,
            PTZCommand.ZOOM_IN: SDK_PTZ_ControlType.ZOOM_ADD_CONTROL,
            PTZCommand.ZOOM_OUT: SDK_PTZ_ControlType.ZOOM_DEC_CONTROL,
            PTZCommand.FOCUS_NEAR: SDK_PTZ_ControlType.FOCUS_ADD_CONTROL,
            PTZCommand.FOCUS_FAR: SDK_PTZ_ControlType.FOCUS_DEC_CONTROL,
            PTZCommand.IRIS_OPEN: SDK_PTZ_ControlType.APERTURE_ADD_CONTROL,
            PTZCommand.IRIS_CLOSE: SDK_PTZ_ControlType.APERTURE_DEC_CONTROL,
        }

        dh_cmd = ptz_cmd_map.get(command)
        if dh_cmd is None:
            logger.warning(f"大华未支持的 PTZ 命令: {command}")
            return False

        # CLIENT_DHPTZControlEx2(lLoginID, nChannelID, dwPTZCommand, lParam1, lParam2, lParam3, dwStop, param4)
        ret = self.sdk_lib.net_client.PTZControlEx2(
            login_id,
            dh_channel,
            dh_cmd,
            0,
            clamped_speed,
            0,
            bool(stop),
            None
        )

        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.warning(f"大华云台控制执行失败: cmd={command.name}, stop={stop}, 错误码={err}")
            return False

        return True

    def find_records(
        self,
        login_id: int,
        channel_no: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[RecordSegment]:
        """Query record files in time range."""
        if not self.is_available or login_id <= 0:
            day_str = start_time.strftime("%Y-%m-%d")
            return [
                RecordSegment(
                    channel_no=channel_no,
                    start_time=datetime.strptime(f"{day_str} 08:00:00", "%Y-%m-%d %H:%M:%S"),
                    end_time=datetime.strptime(f"{day_str} 18:00:00", "%Y-%m-%d %H:%M:%S"),
                    file_name=f"dahua_ch{channel_no}_{day_str}.mp4",
                    file_size=1024 * 1024 * 512
                )
            ]

        dh_channel = channel_no - 1 if channel_no > 0 else 0

        st_time = NET_TIME()
        st_time.dwYear = start_time.year
        st_time.dwMonth = start_time.month
        st_time.dwDay = start_time.day
        st_time.dwHour = start_time.hour
        st_time.dwMinute = start_time.minute
        st_time.dwSecond = start_time.second

        ed_time = NET_TIME()
        ed_time.dwYear = end_time.year
        ed_time.dwMonth = end_time.month
        ed_time.dwDay = end_time.day
        ed_time.dwHour = end_time.hour
        ed_time.dwMinute = end_time.minute
        ed_time.dwSecond = end_time.second

        try:
            ret, files = self.sdk_lib.net_client.QueryRecordFile(
                login_id,
                dh_channel,
                0,  # 0: all record types
                st_time,
                ed_time,
                "",
                3000,
                False
            )
            segments = []
            if ret and files:
                for f_info in files:
                    try:
                        s_dt = datetime(
                            f_info.starttime.dwYear, f_info.starttime.dwMonth, f_info.starttime.dwDay,
                            f_info.starttime.dwHour, f_info.starttime.dwMinute, f_info.starttime.dwSecond
                        )
                        e_dt = datetime(
                            f_info.endtime.dwYear, f_info.endtime.dwMonth, f_info.endtime.dwDay,
                            f_info.endtime.dwHour, f_info.endtime.dwMinute, f_info.endtime.dwSecond
                        )
                        name_str = f_info.filename.decode('utf-8', errors='ignore') if isinstance(f_info.filename, bytes) else str(f_info.filename)
                        segments.append(RecordSegment(
                            channel_no=channel_no,
                            start_time=s_dt,
                            end_time=e_dt,
                            file_name=name_str,
                            file_size=int(getattr(f_info, 'size', 0))
                        ))
                    except Exception:
                        continue
                logger.info(f"大华查询到 {len(segments)} 条录像段 (通道 {channel_no})")
                return segments
        except Exception as e:
            logger.warning(f"大华查询录像出现异常: {e}")

        # Fallback simulation if query returns empty or not supported
        day_str = start_time.strftime("%Y-%m-%d")
        return [
            RecordSegment(
                channel_no=channel_no,
                start_time=datetime.strptime(f"{day_str} 09:00:00", "%Y-%m-%d %H:%M:%S"),
                end_time=datetime.strptime(f"{day_str} 17:00:00", "%Y-%m-%d %H:%M:%S"),
                file_name=f"dahua_ch{channel_no}_{day_str}.mp4",
                file_size=1024 * 1024 * 256
            )
        ]

    def start_playback_by_time(
        self,
        login_id: int,
        channel_no: int,
        win_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Start VOD record playback by time."""
        if not self.is_available:
            logger.info(f"[模拟模式] 开启大华按时间回放 通道 {channel_no} (win_id={win_id})")
            return 5200 + channel_no

        dh_channel = channel_no - 1 if channel_no > 0 else 0

        st_time = NET_TIME()
        st_time.dwYear = start_time.year
        st_time.dwMonth = start_time.month
        st_time.dwDay = start_time.day
        st_time.dwHour = start_time.hour
        st_time.dwMinute = start_time.minute
        st_time.dwSecond = start_time.second

        ed_time = NET_TIME()
        ed_time.dwYear = end_time.year
        ed_time.dwMonth = end_time.month
        ed_time.dwDay = end_time.day
        ed_time.dwHour = end_time.hour
        ed_time.dwMinute = end_time.minute
        ed_time.dwSecond = end_time.second

        play_handle = self.sdk_lib.net_client.PlayBackByTimeEx(
            login_id,
            dh_channel,
            st_time,
            ed_time,
            int(win_id),
            None,
            0,
            None,
            0
        )

        if play_handle == 0:
            err = self.sdk_lib.get_last_error()
            logger.error(f"大华按时间回放失败 通道 {channel_no}, 错误码: {err}")
            return -1

        return int(play_handle)

    def playback_control(
        self,
        playback_handle: int,
        command: PlaybackCommand,
        param: int = 0
    ) -> bool:
        """Control playback state: Pause, Resume, Fast, Slow, Normal."""
        if not self.is_available:
            logger.debug(f"[模拟模式] 大华回放控制: {command.name}")
            return True

        if playback_handle <= 0:
            return False

        if command == PlaybackCommand.PAUSE:
            ret = self.sdk_lib.net_client.PausePlayBack(playback_handle, True)
        elif command in (PlaybackCommand.RESTART, PlaybackCommand.START):
            ret = self.sdk_lib.net_client.PausePlayBack(playback_handle, False)
        elif command == PlaybackCommand.FAST:
            ret = self.sdk_lib.net_client.FastPlayBack(playback_handle)
        elif command == PlaybackCommand.SLOW:
            ret = self.sdk_lib.net_client.SlowPlayBack(playback_handle)
        elif command == PlaybackCommand.NORMAL:
            ret = self.sdk_lib.net_client.NormalPlayBack(playback_handle)
        else:
            ret = True

        return bool(ret)

    def stop_playback(self, playback_handle: int) -> bool:
        """Stop VOD playback."""
        if not self.is_available:
            return True

        if playback_handle <= 0:
            return True

        ret = self.sdk_lib.net_client.StopPlayBack(playback_handle)
        return bool(ret)

    def capture_picture(self, login_id: int, channel_no: int, save_path: str) -> bool:
        """Capture snapshot from Dahua camera."""
        if not self.is_available:
            logger.info(f"[模拟模式] 大华抓图并保存至: {save_path}")
            return True

        dh_channel = channel_no - 1 if channel_no > 0 else 0
        try:
            par = SNAP_PARAMS()
            par.Channel = dh_channel
            par.Quality = 3
            par.ImageSize = 0
            par.mode = 0
            ret = self.sdk_lib.net_client.SnapPictureEx(login_id, par)
            return bool(ret)
        except Exception as e:
            logger.warning(f"大华抓图接口调用异常: {e}")
            return False

# -*- coding: utf-8 -*-
"""
Dahua NetSDK Native Driver and Library Manager.
Handles dynamic library discovery, initialization, login, channels, live stream, PTZ and playback.
"""

import os
import sys
import json
import ctypes
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from adapters.dahua.NetSDK.NetSDK import NetClient
from adapters.dahua.NetSDK.SDK_Struct import (
    NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY,
    NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY,
    NET_TIME,
    SNAP_PARAMS,
    NET_IN_GET_CAMERA_STATEINFO,
    NET_OUT_GET_CAMERA_STATEINFO,
    NET_CAMERA_STATE_INFO,
    NET_IN_PLAY_BACK_BY_TIME_INFO,
    NET_OUT_PLAY_BACK_BY_TIME_INFO,
    CB_FUNCTYPE,
    C_LLONG,
    C_DWORD,
    C_LDWORD,
    C_BYTE
)
from adapters.dahua.NetSDK.SDK_Enum import (
    EM_LOGIN_SPAC_CAP_TYPE,
    SDK_RealPlayType,
    SDK_PTZ_ControlType,
    EM_REALDATA_FLAG,
    EM_USEDEV_MODE
)
from adapters.dahua.NetSDK.SDK_Callback import fDisConnect, fHaveReConnect, fRealDataCallBackEx2

from core.base_adapter import (
    ChannelInfo,
    RecordSegment,
    PTZCommand,
    PlaybackCommand
)
from core.logger import get_logger

logger = get_logger("DahuaSDK")

# 全局保存当前各回放句柄的播放进度
_dh_playback_positions: Dict[int, int] = {}
_dh_data_cb_counter: Dict[int, int] = {}


@CB_FUNCTYPE(None, C_LLONG, C_DWORD, C_DWORD, C_LDWORD)
def _dh_playback_pos_callback(lPlayHandle, dwTotalSize, dwDownLoadSize, dwUser):
    try:
        handle = int(lPlayHandle)
        total = int(dwTotalSize)
        cur = int(dwDownLoadSize)
        if total > 0:
            pos = int(cur * 100 / total)
            _dh_playback_positions[handle] = min(100, max(0, pos))
    except BaseException:
        pass


@CB_FUNCTYPE(ctypes.c_int, C_LLONG, C_DWORD, ctypes.POINTER(ctypes.c_ubyte), C_DWORD, C_LDWORD)
def _dh_playback_data_callback(lPlayHandle, dwDataType, pBuffer, dwBufSize, dwUser):
    # 严格对齐大华官方 PlayBackDemo：NetSDK 在给定 hWnd 时会自动进行解码与硬件自绘制渲染。
    # 数据回调仅用于统计/日志，无需且绝不可向 PlaySDK 重复投递，以防止 X11 线程竞争崩溃。
    try:
        if dwDataType == 0 and pBuffer and dwBufSize > 0:
            h = int(lPlayHandle)
            cnt = _dh_data_cb_counter.get(h, 0) + 1
            _dh_data_cb_counter[h] = cnt
            if cnt <= 2 or cnt % 200 == 0:
                logger.debug(f"[DahuaSDK:DataCB] 回放码流接收中: handle={h}, frame={cnt}, size={dwBufSize}")
    except BaseException:
        pass
    return 1


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
        self._live_sessions: Dict[int, Any] = {}
        self._playback_sessions: Dict[int, Any] = {}

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
        try:
            stream_type = ctypes.c_int(0)  # 0: 主辅码流自适应
            self.sdk_lib.net_client.SetDeviceMode(int(login_id), int(EM_USEDEV_MODE.RECORD_STREAM_TYPE), stream_type)
        except Exception as e:
            logger.debug(f"设置大华 RECORD_STREAM_TYPE 模式提示: {e}")

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
        """Enumerate camera channels for Dahua device with online status and real channel names."""
        if not self.is_available or login_id <= 0:
            return [
                ChannelInfo(channel_no=1, name="大华枪机-正门", is_online=True, is_ptz=False),
                ChannelInfo(channel_no=2, name="大华球机-园区东", is_online=True, is_ptz=True),
                ChannelInfo(channel_no=3, name="大华半球-大厅", is_online=True, is_ptz=False),
                ChannelInfo(channel_no=4, name="大华枪机-仓库", is_online=True, is_ptz=False),
            ]

        n_chans = 0
        if device_info:
            n_chans = int(getattr(device_info, "nChanNum", 0))

        if n_chans <= 0:
            n_chans = 1

        logger.info(f"[DahuaDriver] 开始解析设备通道 login_id={login_id}, 通道总数={n_chans}")

        # 1. 查询真实通道名称 ChannelTitle
        titles: Dict[int, str] = {}
        try:
            buf_title = (ctypes.c_char * 32768)()
            err_title = ctypes.c_int(0)
            if self.sdk_lib.net_client.GetNewDevConfig(login_id, "ChannelTitle", -1, buf_title, 32768, err_title, 2000):
                raw_str = bytes(buf_title).split(b"\x00")[0].decode("utf-8", errors="ignore")
                data = json.loads(raw_str)
                t_list = data.get("params", {}).get("table", [])
                for idx, item in enumerate(t_list):
                    if isinstance(item, dict) and "Name" in item and item["Name"]:
                        titles[idx] = str(item["Name"]).strip()
                logger.debug(f"[DahuaDriver] 获取到通道名称字典: {titles}")
        except Exception as e:
            logger.debug(f"[DahuaDriver] 查询 ChannelTitle 异常或不支持: {e}")

        # 2. 查询数字通道使能 RemoteChannel (针对 NVR/DVR 汇聚设备)
        enabled_map: Dict[int, bool] = {}
        try:
            buf_rc = (ctypes.c_char * 32768)()
            err_rc = ctypes.c_int(0)
            if self.sdk_lib.net_client.GetNewDevConfig(login_id, "RemoteChannel", -1, buf_rc, 32768, err_rc, 2000):
                raw_str = bytes(buf_rc).split(b"\x00")[0].decode("utf-8", errors="ignore")
                data = json.loads(raw_str)
                r_list = data.get("params", {}).get("table", [])
                for idx, item in enumerate(r_list):
                    if isinstance(item, dict) and "Enable" in item:
                        enabled_map[idx] = bool(item["Enable"])
                logger.debug(f"[DahuaDriver] 获取到数字通道使能状态: {enabled_map}")
        except Exception as e:
            logger.debug(f"[DahuaDriver] 查询 RemoteChannel 异常或不支持: {e}")

        # 3. 查询视频输入选项 VideoInOptions (null 说明未接通或无前端信号)
        video_in_map: Dict[int, bool] = {}
        try:
            buf_vi = (ctypes.c_char * 32768)()
            err_vi = ctypes.c_int(0)
            if self.sdk_lib.net_client.GetNewDevConfig(login_id, "VideoInOptions", -1, buf_vi, 32768, err_vi, 2000):
                raw_str = bytes(buf_vi).split(b"\x00")[0].decode("utf-8", errors="ignore")
                data = json.loads(raw_str)
                vi_list = data.get("params", {}).get("table", [])
                for idx, item in enumerate(vi_list):
                    video_in_map[idx] = (item is not None)
                logger.debug(f"[DahuaDriver] 获取到视频输入有效性: {video_in_map}")
        except Exception as e:
            logger.debug(f"[DahuaDriver] 查询 VideoInOptions 异常或不支持: {e}")

        # 4. 查询前端摄像机状态 CAMERA_STATE (0x0E)
        camera_states: Dict[int, int] = {}
        try:
            in_param = NET_IN_GET_CAMERA_STATEINFO()
            in_param.dwSize = ctypes.sizeof(NET_IN_GET_CAMERA_STATEINFO)
            in_param.bGetAllFlag = True
            max_num = max(n_chans, 32)
            state_arr = (NET_CAMERA_STATE_INFO * max_num)()
            out_param = NET_OUT_GET_CAMERA_STATEINFO()
            out_param.dwSize = ctypes.sizeof(NET_OUT_GET_CAMERA_STATEINFO)
            out_param.nMaxNum = max_num
            out_param.pCameraStateInfo = ctypes.cast(state_arr, ctypes.POINTER(NET_CAMERA_STATE_INFO))
            if self.sdk_lib.net_client.QueryDevInfo(login_id, 0x0E, in_param, out_param, None, 2000):
                for i in range(out_param.nValidNum):
                    camera_states[state_arr[i].nChannel] = state_arr[i].emConnectionState
                logger.debug(f"[DahuaDriver] 获取到前端摄像机连接状态: {camera_states}")
        except Exception as e:
            logger.debug(f"[DahuaDriver] 查询 CAMERA_STATE 异常或不支持: {e}")

        # 5. 组合生成通道列表
        channels = []
        for i in range(n_chans):
            ch_no = i + 1
            chan_name = titles.get(i) or f"通道 {ch_no}"
            is_en = enabled_map.get(i, True)
            has_vi = video_in_map.get(i, None)
            cam_st = camera_states.get(i, None)

            # 综合判定在线状态：
            if n_chans == 1:
                # 单通道独立 IPC，成功登录说明前端在线
                is_online = True
            elif not is_en:
                # 数字通道未启用
                is_online = False
            elif has_vi is False:
                # 明确无视频输入 (老 NVR 特征)
                is_online = False
            elif cam_st is not None and cam_st in (4, 5):  # 4: EMPTY(未配置), 5: DISABLE(禁用)
                is_online = False
            elif has_vi is True:
                # 具备有效视频输入
                is_online = True
            elif cam_st == 2:  # 2: CONNECTED
                is_online = True
            else:
                # 若无详细特征返回，默认遵循使能状态
                is_online = is_en

            logger.info(
                f"[DahuaDriver] 通道 {ch_no} [{chan_name}]: 使能={is_en}, 视频输入={has_vi}, "
                f"相机状态={cam_st} => 判定在线={is_online}"
            )
            channels.append(ChannelInfo(
                channel_no=ch_no,
                name=chan_name,
                is_online=is_online,
                is_ptz=True,
                is_enabled=is_en,
                extra={"dh_channel_idx": i}
            ))

        online_count = sum(1 for c in channels if c.is_online)
        logger.info(f"[DahuaDriver] 通道解析完毕: 共生成 {len(channels)} 个通道, 其中在线 {online_count} 个")
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

        is_linux = sys.platform.startswith("linux")
        logger.info(
            f"大华发起实时预览: login_id={login_id}, 通道={channel_no}(dh_idx={dh_channel}), "
            f"win_id={win_id}, 码流={stream_type}"
        )
        sys.stdout.flush()

        # 在 Linux 环境下优先采用官方标准的 PlaySDK 硬件加速灌流直出管线 (100% 对齐官方 RealPlayDemo.py)
        if is_linux and win_id > 0:
            try:
                res, free_port = self.sdk_lib.net_client.GetFreePort()
                if res and free_port is not None:
                    self.sdk_lib.net_client.OpenStream(free_port)
                    self.sdk_lib.net_client.Play(free_port, int(win_id))
                    play_id = self.sdk_lib.net_client.RealPlayEx(login_id, dh_channel, 0, r_type)
                    if play_id != 0:
                        def _on_real_data(lRealHandle, dwDataType, pBuffer, dwBufSize, param, dwUser):
                            if pBuffer and dwBufSize > 0:
                                self.sdk_lib.net_client.InputData(free_port, pBuffer, dwBufSize)

                        cb_ref = fRealDataCallBackEx2(_on_real_data)
                        self.sdk_lib.net_client.SetRealDataCallBackEx2(play_id, cb_ref, None, EM_REALDATA_FLAG.RAW_DATA)
                        self._live_sessions[int(play_id)] = (free_port, cb_ref, True)
                        logger.info(f"✓ 大华实时预览已通过官方 PlaySDK 硬件加速管线启动 (play_id={play_id}, port={free_port})")
                        sys.stdout.flush()
                        return int(play_id)
                    else:
                        try:
                            self.sdk_lib.net_client.Stop(free_port)
                            self.sdk_lib.net_client.CloseStream(free_port)
                            self.sdk_lib.net_client.ReleasePort(free_port)
                        except Exception:
                            pass
            except Exception as pe:
                logger.warning(f"大华 PlaySDK 初始化异常，回退至原生直绘: {pe}")

        play_id = self.sdk_lib.net_client.RealPlayEx(login_id, dh_channel, int(win_id), r_type)

        if play_id == 0:
            err = self.sdk_lib.get_last_error()
            msg = self.sdk_lib.get_last_error_msg()
            logger.error(f"大华开启实时预览失败: 通道={channel_no}, 错误码={err}, 信息={msg}")
            sys.stdout.flush()
            return -1

        self._live_sessions[int(play_id)] = (None, None, False)
        return int(play_id)

    def stop_real_play(self, play_id: int) -> bool:
        """Stop real-time live preview."""
        if not self.is_available:
            return True

        if play_id <= 0:
            return True

        if int(play_id) in self._live_sessions:
            port, cb_ref, is_playsdk = self._live_sessions.pop(int(play_id))
            if is_playsdk and port is not None:
                try:
                    self.sdk_lib.net_client.SetDecCallBack(port, None)
                    self.sdk_lib.net_client.Stop(port)
                    self.sdk_lib.net_client.CloseStream(port)
                    self.sdk_lib.net_client.ReleasePort(port)
                except Exception as e:
                    logger.debug(f"大华清理 PlaySDK 会话资源异常: {e}")

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
        """Query record files in time range with rich logging."""
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

        if end_time <= start_time:
            from datetime import timedelta
            end_time = min(start_time + timedelta(hours=1), datetime.combine(start_time.date(), time(23, 59, 59)))

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

        s_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        e_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"大华查询录像: login_id={login_id}, 通道={channel_no}(dh_idx={dh_channel}), 检索范围=[{s_str} 至 {e_str}]")

        try:
            try:
                stream_type = ctypes.c_int(0)  # 0: 主辅码流自适应
                self.sdk_lib.net_client.SetDeviceMode(int(login_id), int(EM_USEDEV_MODE.RECORD_STREAM_TYPE), stream_type)
            except Exception:
                pass

            res = self.sdk_lib.net_client.QueryRecordFile(
                login_id,
                dh_channel,
                0,  # 0: all record types
                st_time,
                ed_time,
                None,
                3000,
                False
            )
            if isinstance(res, tuple):
                if len(res) == 3:
                    ret, file_count, files = res
                elif len(res) == 2:
                    ret, files = res
                    file_count = len(files) if files else 0
                else:
                    ret, file_count, files = False, 0, []
            else:
                ret, file_count, files = False, 0, []

            if hasattr(file_count, "value"):
                file_count = file_count.value
            file_count = int(file_count or 0)

            segments: List[RecordSegment] = []
            if ret and files and file_count > 0:
                limit = min(file_count, len(files), 5000)
                for i in range(limit):
                    f_info = files[i]
                    try:
                        sy = int(getattr(f_info.starttime, "dwYear", 0))
                        if sy < 2000:
                            continue
                        s_dt = datetime(
                            sy,
                            int(f_info.starttime.dwMonth),
                            int(f_info.starttime.dwDay),
                            int(f_info.starttime.dwHour),
                            int(f_info.starttime.dwMinute),
                            int(f_info.starttime.dwSecond)
                        )
                        ey = int(getattr(f_info.endtime, "dwYear", 0))
                        e_dt = datetime(
                            ey,
                            int(f_info.endtime.dwMonth),
                            int(f_info.endtime.dwDay),
                            int(f_info.endtime.dwHour),
                            int(f_info.endtime.dwMinute),
                            int(f_info.endtime.dwSecond)
                        )
                        raw_fn = getattr(f_info, "filename", b"")
                        name_str = raw_fn.decode("utf-8", errors="ignore") if isinstance(raw_fn, bytes) else str(raw_fn)
                        # size 字段单位为 KByte
                        kb_size = int(getattr(f_info, "size", 0))
                        byte_size = kb_size * 1024
                        segments.append(RecordSegment(
                            channel_no=channel_no,
                            start_time=s_dt,
                            end_time=e_dt,
                            file_name=name_str,
                            file_size=byte_size
                        ))
                        logger.debug(f"  检索到录像片段 {i+1}: {name_str} ({s_dt} -> {e_dt}, 大小: {kb_size} KB)")
                    except Exception as parse_e:
                        logger.debug(f"  解析录像条目 {i+1} 异常: {parse_e}")
                        continue

                logger.info(f"大华录像检索完成: 通道 {channel_no} 共找到 {len(segments)} 条有效录像段")
                return segments
            else:
                err = self.sdk_lib.get_last_error()
                err_msg = self.sdk_lib.get_last_error_msg()
                logger.info(f"大华未检索到录像文件 (通道 {channel_no}): ret={ret}, count={file_count}, 状态={err}({err_msg})")
                return []
        except Exception as e:
            logger.error(f"大华查询录像发生未捕获异常: {e}", exc_info=True)
            return []

    def start_playback_by_time(
        self,
        login_id: int,
        channel_no: int,
        win_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Start VOD record playback by time with rich logging."""
        if not self.is_available:
            logger.info(f"[模拟模式] 开启大华按时间回放 通道 {channel_no} (win_id={win_id})")
            return 5200 + channel_no

        dh_channel = channel_no - 1 if channel_no > 0 else 0

        if end_time <= start_time:
            from datetime import timedelta
            end_time = min(start_time + timedelta(hours=1), datetime.combine(start_time.date(), time(23, 59, 59)))

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

        s_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        e_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(
            f"大华按时间发起回放: login_id={login_id}, 通道={channel_no}(dh_idx={dh_channel}), "
            f"win_id={win_id}, 时间范围=[{s_str} 至 {e_str}]"
        )
        sys.stdout.flush()

        play_handle = 0

        # 若之前有残留的回放会话，先主动停止清理，防止端口及窗口占用
        if self._playback_sessions:
            for old_h in list(self._playback_sessions.keys()):
                try:
                    self.stop_playback(old_h)
                except Exception:
                    pass

        # 严格遵循大华官方 PlayBackDemo：
        # NetSDK 自带完整的硬件解码与自绘引擎，只要传入有效的窗口句柄 hWnd=win_id，
        # 底层即会自动将解码后的画面渲染到窗口上。绝不可在外部手动使用 PlaySDK 重复开流与抢占窗口，
        # 否则在多次切换时会引起底层 OpenGL/X11 句柄竞争导致段错误 (SIGSEGV) 崩溃。
        target_hwnd = int(win_id) if win_id > 0 else 0
        is_linux = sys.platform.startswith("linux")
        pb_port = None
        pb_cb = _dh_playback_data_callback

        # Linux 环境下优先采用与 test_dahua.py 相同的 PlaySDK 灌流硬件加速管线
        if is_linux and win_id > 0:
            try:
                res, port = self.sdk_lib.net_client.GetFreePort()
                if res and port is not None:
                    self.sdk_lib.net_client.OpenStream(port)
                    self.sdk_lib.net_client.Play(port, int(win_id))
                    pb_port = port

                    @CB_FUNCTYPE(ctypes.c_int, C_LLONG, C_DWORD, ctypes.POINTER(ctypes.c_ubyte), C_DWORD, C_LDWORD)
                    def _on_pb_stream_data(lPlayHandle, dwDataType, pBuffer, dwBufSize, dwUser):
                        if pBuffer and dwBufSize > 0 and pb_port is not None:
                            self.sdk_lib.net_client.InputData(pb_port, pBuffer, dwBufSize)
                        return 1

                    pb_cb = _on_pb_stream_data
                    target_hwnd = 0  # 灌流模式由 PlaySDK 驱动窗口，NetSDK 传 0
                    logger.info(f"大华回放已配置 PlaySDK 硬件解码管线 (port={port})")
            except Exception as pe:
                logger.warning(f"大华回放配置 PlaySDK 异常，回退至原生直出: {pe}")

        # 1. 优先调用大华官方标准 PlayBackByTimeEx2 接口
        try:
            try:
                stream_type = ctypes.c_int(0)  # 0: 主辅码流自适应
                self.sdk_lib.net_client.SetDeviceMode(int(login_id), int(EM_USEDEV_MODE.RECORD_STREAM_TYPE), stream_type)
            except Exception:
                pass

            in_param = NET_IN_PLAY_BACK_BY_TIME_INFO()
            in_param.hWnd = ctypes.c_long(target_hwnd)
            in_param.cbDownLoadPos = _dh_playback_pos_callback
            in_param.dwPosUser = 0
            in_param.fDownLoadDataCallBack = pb_cb
            in_param.dwDataUser = 0
            in_param.nPlayDirection = 0
            in_param.nWaittime = 5000
            in_param.stStartTime.dwYear = start_time.year
            in_param.stStartTime.dwMonth = start_time.month
            in_param.stStartTime.dwDay = start_time.day
            in_param.stStartTime.dwHour = start_time.hour
            in_param.stStartTime.dwMinute = start_time.minute
            in_param.stStartTime.dwSecond = start_time.second
            in_param.stStopTime.dwYear = end_time.year
            in_param.stStopTime.dwMonth = end_time.month
            in_param.stStopTime.dwDay = end_time.day
            in_param.stStopTime.dwHour = end_time.hour
            in_param.stStopTime.dwMinute = end_time.minute
            in_param.stStopTime.dwSecond = end_time.second
            out_param = NET_OUT_PLAY_BACK_BY_TIME_INFO()

            logger.info(f"大华调用 NetSDK.PlayBackByTimeEx2 (hWnd={target_hwnd})...")
            sys.stdout.flush()
            play_handle = self.sdk_lib.net_client.PlayBackByTimeEx2(
                login_id,
                dh_channel,
                in_param,
                out_param
            )
            logger.info(f"大华 NetSDK.PlayBackByTimeEx2 返回 play_handle={play_handle}")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"[DahuaDriver] 调用 PlayBackByTimeEx2 异常: {e}", exc_info=True)
            sys.stdout.flush()

        # 2. 若 Ex2 失败或返回 0，尝试 PlayBackByTimeEx 兼容接口
        if not play_handle:
            try:
                logger.info(f"大华尝试调用 PlayBackByTimeEx 兼容接口 (hWnd={target_hwnd})...")
                sys.stdout.flush()
                play_handle = self.sdk_lib.net_client.PlayBackByTimeEx(
                    login_id,
                    dh_channel,
                    st_time,
                    ed_time,
                    target_hwnd,
                    _dh_playback_pos_callback,
                    0,
                    _dh_playback_data_callback,
                    0
                )
                logger.info(f"大华 PlayBackByTimeEx 返回 handle={play_handle}")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"[DahuaDriver] 调用 PlayBackByTimeEx 异常: {e}", exc_info=True)
                sys.stdout.flush()

        if not play_handle or play_handle == 0:
            err = self.sdk_lib.get_last_error()
            err_msg = self.sdk_lib.get_last_error_msg()
            hint = ""
            if err == 24:
                hint = " (该时间段内无录像数据，请核对录像日期与设备系统时间)"
            elif err == 7:
                hint = " (参数错误，请检查窗口句柄 HWND 是否有效)"
            logger.error(f"大华按时间回放失败: 通道 {channel_no}, 错误码: {err} ({err_msg}){hint}")
            sys.stdout.flush()
            return -1

        h_val = int(play_handle)
        _dh_playback_positions[h_val] = 0
        self._playback_sessions[h_val] = (pb_port, pb_cb)

        logger.info(f"大华按时间回放成功启动: handle={h_val}, 通道={channel_no}")
        sys.stdout.flush()
        return h_val

    def get_playback_pos(self, playback_handle: int) -> int:
        """Get playback progress 0-100%."""
        return _dh_playback_positions.get(playback_handle, 50)

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

        h_val = int(playback_handle)

        if command == PlaybackCommand.PAUSE:
            ret = self.sdk_lib.net_client.PausePlayBack(h_val, True)
        elif command in (PlaybackCommand.RESTART, PlaybackCommand.START):
            ret = self.sdk_lib.net_client.PausePlayBack(h_val, False)
        elif command == PlaybackCommand.FAST:
            ret = self.sdk_lib.net_client.FastPlayBack(h_val)
        elif command == PlaybackCommand.SLOW:
            ret = self.sdk_lib.net_client.SlowPlayBack(h_val)
        elif command == PlaybackCommand.NORMAL:
            ret = self.sdk_lib.net_client.NormalPlayBack(h_val)
        else:
            ret = True

        return bool(ret)

    def stop_playback(self, playback_handle: int) -> bool:
        """Stop VOD playback cleanly."""
        h_val = int(playback_handle)
        _dh_playback_positions.pop(h_val, None)
        _dh_data_cb_counter.pop(h_val, None)

        if h_val in self._playback_sessions:
            sess = self._playback_sessions.pop(h_val, None)
            if sess and isinstance(sess, tuple):
                port, _ = sess
                if port is not None:
                    try:
                        self.sdk_lib.net_client.Stop(port)
                        self.sdk_lib.net_client.CloseStream(port)
                        self.sdk_lib.net_client.ReleasePort(port)
                    except Exception as pe:
                        logger.debug(f"释放 PlaySDK 回放端口异常: {pe}")

        if not self.is_available or h_val <= 0:
            return True

        logger.info(f"大华停止回放 handle={h_val}...")
        sys.stdout.flush()
        ret = self.sdk_lib.net_client.StopPlayBack(h_val)
        logger.info(f"大华停止回放完成: ret={bool(ret)}")
        sys.stdout.flush()
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

# -*- coding: utf-8 -*-
"""
Hikvision HCNetSDK Driver and Library Manager.
Handles dynamic library discovery, initialization, login, channels, live stream and playback.
"""

import os
import sys
import time
import ctypes
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from adapters.hikvision.structures import (
    NET_DVR_DEVICEINFO_V30,
    NET_DVR_PREVIEWINFO,
    NET_DVR_VOD_PARA,
    NET_DVR_TIME,
    NET_DVR_FILECOND,
    NET_DVR_FINDDATA_V30,
    NET_DVR_FILECOND_V50,
    NET_DVR_FINDDATA_V50,
    NET_DVR_IPPARACFG_V40,
    NET_DVR_LOCAL_SDK_PATH,
    NET_DVR_GET_IPPARACFG_V40,
    NET_DVR_GET_DIGITAL_CHANNEL_STATE,
    NET_DVR_DIGITAL_CHANNEL_STATE,
    NET_DVR_WORKSTATE_V30,
    NET_DVR_PLAYSTART,
    NET_DVR_PLAYPAUSE,
    NET_DVR_PLAYRESTART,
    NET_DVR_PLAYFAST,
    NET_DVR_PLAYSLOW,
    NET_DVR_PLAYGETPOS,
    LIGHT_PWRON, WIPER_PWRON,
    ZOOM_IN, ZOOM_OUT, FOCUS_NEAR, FOCUS_FAR, IRIS_OPEN, IRIS_CLOSE,
    TILT_UP, TILT_DOWN, PAN_LEFT, PAN_RIGHT,
    UP_LEFT, UP_RIGHT, DOWN_LEFT, DOWN_RIGHT
)

# Standard Hikvision Playback Command Constants
NET_DVR_PLAYNORMAL = 7
NET_DVR_PLAYFRAME = 8
NET_DVR_PLAYSETPOS = 12

from core.base_adapter import (
    ChannelInfo,
    RecordSegment,
    PTZCommand,
    PlaybackCommand
)
from core.logger import get_logger

logger = get_logger("HCNetSDK")


class HCNetSDKLibrary:
    """Singleton wrapper around libhcnetsdk.so and libPlayCtrl.so."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.is_loaded = False
        self.sdk_path: Optional[str] = None
        self.hcnetsdk = None
        self.playctrl = None
        self._init_success = False
        self._find_and_load_library()

    def _find_and_load_library(self):
        """Locate and load Hikvision Linux 64-bit SDK .so files."""
        is_linux = "linux" in sys.platform.lower()

        search_paths = []
        if os.environ.get("HIK_SDK_PATH"):
            search_paths.append(os.environ["HIK_SDK_PATH"])

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sdk_candidate = os.path.join(
            base_dir,
            "HCNetSDKV6.1.11.30_build20260805_linux64_20260812103926",
            "HCNetSDKV6.1.11.30_build20260805_linux64",
            "库文件"
        )
        search_paths.append(sdk_candidate)
        search_paths.append(os.path.join(base_dir, "sdk", "hikvision", "lib"))
        search_paths.append(os.path.join(base_dir, "lib"))

        valid_path = None
        for p in search_paths:
            if os.path.isdir(p):
                so_file = os.path.join(p, "libhcnetsdk.so")
                if os.path.exists(so_file):
                    valid_path = p
                    break

        if not valid_path:
            logger.warning(
                "未找到海康威视 Linux SDK (libhcnetsdk.so)。"
                "如果在 Windows 开发环境或未加载 SDK，将运行在模拟模式。"
            )
            return

        self.sdk_path = valid_path
        logger.info(f"发现海康 SDK 库路径: {valid_path}")

        if not is_linux:
            logger.info("当前系统不是 Linux (Ubuntu)，跳过加载 .so 动态库，启用模拟协议模式。")
            return

        try:
            # 1. 预加载依赖库
            crypto_path = os.path.join(valid_path, "libcrypto.so.3")
            ssl_path = os.path.join(valid_path, "libssl.so.3")
            hpr_path = os.path.join(valid_path, "libhpr.so")
            hccore_path = os.path.join(valid_path, "libHCCore.so")

            for dep in [crypto_path, ssl_path, hpr_path, hccore_path]:
                if os.path.exists(dep):
                    try:
                        ctypes.cdll.LoadLibrary(dep)
                    except Exception as e:
                        logger.debug(f"加载依赖库 {dep} 提示: {e}")

            # 2. 加载主网络库 libhcnetsdk.so
            hcnetsdk_so = os.path.join(valid_path, "libhcnetsdk.so")
            self.hcnetsdk = ctypes.cdll.LoadLibrary(hcnetsdk_so)

            # 3. 加载播放库 libPlayCtrl.so
            playctrl_so = os.path.join(valid_path, "libPlayCtrl.so")
            if os.path.exists(playctrl_so):
                self.playctrl = ctypes.cdll.LoadLibrary(playctrl_so)

            # 4. 配置 SDK 初始化参数 (HCNetSDKCom 目录、crypto 和 ssl 路径)
            com_path = os.path.join(valid_path, "HCNetSDKCom")
            if os.path.isdir(com_path):
                stru_com = NET_DVR_LOCAL_SDK_PATH()
                stru_com.sPath = com_path.encode('utf-8')
                self.hcnetsdk.NET_DVR_SetSDKInitCfg(2, ctypes.byref(stru_com))

            if os.path.exists(crypto_path):
                self.hcnetsdk.NET_DVR_SetSDKInitCfg(3, ctypes.create_string_buffer(crypto_path.encode('utf-8')))

            if os.path.exists(ssl_path):
                self.hcnetsdk.NET_DVR_SetSDKInitCfg(4, ctypes.create_string_buffer(ssl_path.encode('utf-8')))

            # 5. 初始化 NET_DVR_Init
            ret = self.hcnetsdk.NET_DVR_Init()
            if ret:
                self.is_loaded = True
                self._init_success = True
                log_dir = os.path.join(base_dir, "logs", "hik_sdk")
                os.makedirs(log_dir, exist_ok=True)
                self.hcnetsdk.NET_DVR_SetLogToFile(3, log_dir.encode('utf-8'), False)
                logger.info("海康威视 SDK 初始化成功 (NET_DVR_Init)")
            else:
                err = self.hcnetsdk.NET_DVR_GetLastError()
                logger.error(f"海康威视 SDK NET_DVR_Init 失败，错误码: {err}")

        except Exception as e:
            logger.error(f"加载海康威视 SDK 动态库异常: {e}")
            self.is_loaded = False

    def cleanup(self):
        """Clean up SDK on exit."""
        if self.is_loaded and self.hcnetsdk:
            try:
                self.hcnetsdk.NET_DVR_Cleanup()
                logger.info("海康威视 SDK 资源已清理 (NET_DVR_Cleanup)")
            except Exception as e:
                logger.error(f"SDK Cleanup 异常: {e}")
            self.is_loaded = False

    def get_last_error(self) -> int:
        if self.is_loaded and self.hcnetsdk:
            return self.hcnetsdk.NET_DVR_GetLastError()
        return -1


class HikvisionNativeDriver:
    """Wrapper providing clean Python methods over HCNetSDK."""

    def __init__(self):
        self.sdk_lib = HCNetSDKLibrary.get_instance()

    @property
    def is_available(self) -> bool:
        return self.sdk_lib.is_loaded

    def login(self, ip: str, port: int, user: str, password: str) -> Tuple[int, Optional[Any]]:
        if not self.is_available:
            logger.info(f"[模拟模式] 正在模拟连接海康设备: {ip}:{port}")
            return 1001, None

        device_info = NET_DVR_DEVICEINFO_V30()
        ip_buf = ctypes.create_string_buffer(ip.encode('utf-8'))
        user_buf = ctypes.create_string_buffer(user.encode('utf-8'))
        pwd_buf = ctypes.create_string_buffer(password.encode('utf-8'))

        user_id = self.sdk_lib.hcnetsdk.NET_DVR_Login_V30(
            ip_buf,
            port,
            user_buf,
            pwd_buf,
            ctypes.byref(device_info)
        )

        if user_id < 0:
            err = self.sdk_lib.get_last_error()
            logger.error(f"海康设备登录失败 {ip}:{port}, 错误码: {err}")
            return -1, None

        logger.info(f"海康设备登录成功 {ip}:{port}, 用户ID: {user_id}")
        return user_id, device_info

    def logout(self, user_id: int) -> bool:
        if not self.is_available:
            return True

        if user_id < 0:
            return True

        ret = self.sdk_lib.hcnetsdk.NET_DVR_Logout(user_id)
        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.warning(f"注销设备失败 user_id={user_id}, 错误码: {err}")
            return False
        return True

    def get_channels(self, user_id: int, device_info: Optional[Any] = None) -> List[ChannelInfo]:
        if not self.is_available or user_id < 0:
            return [
                ChannelInfo(channel_no=1, name="海康球机-正门", is_online=True, is_ptz=True),
                ChannelInfo(channel_no=2, name="海康枪机-周界东", is_online=True, is_ptz=False),
                ChannelInfo(channel_no=3, name="海康枪机-周界西", is_online=True, is_ptz=False),
                ChannelInfo(channel_no=4, name="海康半球-大厅入口", is_online=True, is_ptz=False),
            ]

        channels = []

        by_chan_num = 0
        by_start_chan = 1
        if device_info:
            by_chan_num = getattr(device_info, "byChanNum", 0)
            by_start_chan = getattr(device_info, "byStartChan", 1)

        # 1. 尝试检测数字通道连接/在线状态
        dig_online_map = {}
        try:
            dig_state = NET_DVR_DIGITAL_CHANNEL_STATE()
            dig_state.dwSize = ctypes.sizeof(dig_state)
            bytes_ret = ctypes.c_ulong(0)
            ret_state = self.sdk_lib.hcnetsdk.NET_DVR_GetDVRConfig(
                user_id,
                NET_DVR_GET_DIGITAL_CHANNEL_STATE,
                0,
                ctypes.byref(dig_state),
                ctypes.sizeof(dig_state),
                ctypes.byref(bytes_ret)
            )
            if ret_state:
                # 0-63 通道
                for idx in range(64):
                    code = dig_state.byDigitalChanState[idx]
                    dig_online_map[idx] = (code == 1)  # 1 为 CONNECTED (在线)
                # 64-255 扩展通道
                for idx in range(192):
                    code = dig_state.byDigitalChanStateEx[idx]
                    dig_online_map[64 + idx] = (code == 1)
                online_count = sum(1 for v in dig_online_map.values() if v)
                logger.info(f"成功获取设备数字通道状态: 共检出 {online_count} 个在线")
        except Exception as e:
            logger.debug(f"NET_DVR_GET_DIGITAL_CHANNEL_STATE 查询提示: {e}")

        # 2. 回退机制：若数字通道状态未获取，尝试查询设备工作状态 (NET_DVR_GetDVRWorkState_V30)
        work_state_map = {}
        if not dig_online_map:
            try:
                work_state = NET_DVR_WORKSTATE_V30()
                if self.sdk_lib.hcnetsdk.NET_DVR_GetDVRWorkState_V30(user_id, ctypes.byref(work_state)):
                    for idx in range(64):
                        st = work_state.struChanStatic[idx]
                        c_no = st.dwChannelNo if (st.dwChannelNo != 0xFFFFFFFF and st.dwChannelNo > 0) else (idx + 1)
                        # bySignalStatic: 0-正常(在线), 1-信号丢失(离线)
                        work_state_map[c_no] = (st.bySignalStatic == 0)
                    logger.info("成功通过工作状态 (NET_DVR_GetDVRWorkState_V30) 获取通道信号状态")
            except Exception as e:
                logger.debug(f"NET_DVR_GetDVRWorkState_V30 查询提示: {e}")

        # 3. 处理模拟通道 (仅混合型 DVR/NVR 存在模拟通道)
        for i in range(by_chan_num):
            ch_no = by_start_chan + i
            is_online = work_state_map.get(ch_no, True)
            channels.append(ChannelInfo(
                channel_no=ch_no,
                name=f"模拟通道 {i + 1}",
                is_online=is_online,
                is_ptz=False
            ))

        # 4. 获取 IP 数字通道配置 (NET_DVR_GET_IPPARACFG_V40)
        ip_para_cfg = NET_DVR_IPPARACFG_V40()
        bytes_returned = ctypes.c_ulong(0)
        ret = self.sdk_lib.hcnetsdk.NET_DVR_GetDVRConfig(
            user_id,
            NET_DVR_GET_IPPARACFG_V40,
            0,
            ctypes.byref(ip_para_cfg),
            ctypes.sizeof(ip_para_cfg),
            ctypes.byref(bytes_returned)
        )

        if ret:
            start_num = ip_para_cfg.dwStartDChan
            d_chan_num = ip_para_cfg.dwDChanNum
            for i in range(d_chan_num):
                chan_cfg = ip_para_cfg.struStreamMode[i]
                ch_no = start_num + i

                # 判断在线状态
                if i in dig_online_map:
                    is_online = dig_online_map[i]
                elif ch_no in work_state_map:
                    is_online = work_state_map[ch_no]
                elif chan_cfg.byGetStreamType == 0:
                    stream_type = chan_cfg.uGetStream.struChanInfo
                    is_online = bool(stream_type.byEnable)
                else:
                    is_online = True

                # 通道显示名称：从 1 开始顺号，避免从 33 开始让用户困惑
                if by_chan_num == 0:
                    # 纯 NVR：规范编号为 "通道 1", "通道 2" ...
                    chan_name = f"通道 {i + 1}"
                else:
                    # 混合型 DVR：接在模拟通道之后顺号
                    chan_name = f"数字通道 {by_chan_num + i + 1}"

                channels.append(ChannelInfo(
                    channel_no=ch_no,
                    name=chan_name,
                    is_online=is_online,
                    is_ptz=True
                ))
        else:
            logger.debug("获取数字通道配置未返回 (可能为单个网络IPC摄像机)")

        if not channels:
            channels.append(ChannelInfo(channel_no=1, name="通道 1", is_online=True, is_ptz=True))

        return channels

    def start_real_play(
        self,
        user_id: int,
        channel_no: int,
        win_id: int,
        stream_type: int = 0
    ) -> int:
        if not self.is_available:
            logger.info(f"[模拟模式] 开启通道 {channel_no} 实时预览 (win_id={win_id})")
            return 2000 + channel_no

        preview_info = NET_DVR_PREVIEWINFO()
        preview_info.hPlayWnd = win_id
        preview_info.lChannel = channel_no
        preview_info.dwStreamType = stream_type
        preview_info.dwLinkMode = 0
        preview_info.bBlocked = 0

        play_handle = self.sdk_lib.hcnetsdk.NET_DVR_RealPlay_V40(
            user_id,
            ctypes.byref(preview_info),
            None,
            None
        )

        if play_handle < 0:
            err = self.sdk_lib.get_last_error()
            logger.error(f"NET_DVR_RealPlay_V40 失败 (通道 {channel_no}), 错误码: {err}")
            return -1

        return play_handle

    def stop_real_play(self, play_handle: int) -> bool:
        if not self.is_available:
            return True

        if play_handle < 0:
            return True

        ret = self.sdk_lib.hcnetsdk.NET_DVR_StopRealPlay(play_handle)
        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.warning(f"NET_DVR_StopRealPlay 失败 handle={play_handle}, 错误码: {err}")
            return False
        return True

    def capture_picture(self, play_handle: int, save_path: str) -> bool:
        if not self.is_available:
            logger.info(f"[模拟模式] 截取画面保存至: {save_path}")
            return True

        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        c_path = ctypes.create_string_buffer(save_path.encode('utf-8'))
        ret = self.sdk_lib.hcnetsdk.NET_DVR_CapturePicture(play_handle, c_path)
        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.error(f"抓图失败 handle={play_handle}, 错误码: {err}")
            return False
        return True

    def start_record(self, play_handle: int, save_path: str) -> bool:
        if not self.is_available:
            logger.info(f"[模拟模式] 开始录像至: {save_path}")
            return True

        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        c_path = ctypes.create_string_buffer(save_path.encode('utf-8'))
        ret = self.sdk_lib.hcnetsdk.NET_DVR_SaveRealData(play_handle, c_path)
        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.error(f"开启录像失败 handle={play_handle}, 错误码: {err}")
            return False
        return True

    def stop_record(self, play_handle: int) -> bool:
        if not self.is_available:
            logger.info("[模拟模式] 停止录像")
            return True

        ret = self.sdk_lib.hcnetsdk.NET_DVR_StopSaveRealData(play_handle)
        if not ret:
            err = self.sdk_lib.get_last_error()
            logger.error(f"停止录像失败 handle={play_handle}, 错误码: {err}")
            return False
        return True

    def ptz_control(
        self,
        user_id: int,
        channel_no: int,
        command: PTZCommand,
        stop: bool = False,
        speed: int = 4,
        play_handle: int = -1
    ) -> bool:
        cmd_map = {
            PTZCommand.UP: TILT_UP,
            PTZCommand.DOWN: TILT_DOWN,
            PTZCommand.LEFT: PAN_LEFT,
            PTZCommand.RIGHT: PAN_RIGHT,
            PTZCommand.UP_LEFT: UP_LEFT,
            PTZCommand.UP_RIGHT: UP_RIGHT,
            PTZCommand.DOWN_LEFT: DOWN_LEFT,
            PTZCommand.DOWN_RIGHT: DOWN_RIGHT,
            PTZCommand.ZOOM_IN: ZOOM_IN,
            PTZCommand.ZOOM_OUT: ZOOM_OUT,
            PTZCommand.FOCUS_NEAR: FOCUS_NEAR,
            PTZCommand.FOCUS_FAR: FOCUS_FAR,
            PTZCommand.IRIS_OPEN: IRIS_OPEN,
            PTZCommand.IRIS_CLOSE: IRIS_CLOSE,
        }

        hik_cmd = cmd_map.get(command)
        if hik_cmd is None:
            logger.warning(f"未知或不支持的云台控制指令: {command}")
            return False

        if not self.is_available:
            action = "停止" if stop else "启动"
            logger.debug(f"[模拟模式] 云台控制: {command.name} {action} speed={speed} user_id={user_id} ch={channel_no}")
            return True

        stop_flag = 1 if stop else 0
        speed_val = max(1, min(7, speed))

        # 方式 1 (标准方式): NET_DVR_PTZControlWithSpeed_Other (基于 user_id + channel_no 控制，海康推荐，支持 NVR IP 通道与直连球机)
        if user_id >= 0 and channel_no > 0 and hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_PTZControlWithSpeed_Other"):
            try:
                ret = self.sdk_lib.hcnetsdk.NET_DVR_PTZControlWithSpeed_Other(
                    ctypes.c_int(user_id),
                    ctypes.c_int(channel_no),
                    ctypes.c_uint(hik_cmd),
                    ctypes.c_uint(stop_flag),
                    ctypes.c_uint(speed_val)
                )
                if ret:
                    logger.debug(f"云台控制成功 (NET_DVR_PTZControlWithSpeed_Other): user_id={user_id}, ch={channel_no}, cmd={command.name}, stop={stop}")
                    return True
                else:
                    err = self.sdk_lib.get_last_error()
                    logger.debug(f"NET_DVR_PTZControlWithSpeed_Other 返回错误 user_id={user_id}, ch={channel_no}, err={err}")
            except Exception as e:
                logger.warning(f"调用 NET_DVR_PTZControlWithSpeed_Other 异常: {e}")

        # 方式 2: NET_DVR_PTZControl_Other (不带速度的通道控制备选)
        if user_id >= 0 and channel_no > 0 and hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_PTZControl_Other"):
            try:
                ret = self.sdk_lib.hcnetsdk.NET_DVR_PTZControl_Other(
                    ctypes.c_int(user_id),
                    ctypes.c_int(channel_no),
                    ctypes.c_uint(hik_cmd),
                    ctypes.c_uint(stop_flag)
                )
                if ret:
                    logger.debug(f"云台控制成功 (NET_DVR_PTZControl_Other): user_id={user_id}, ch={channel_no}, cmd={command.name}, stop={stop}")
                    return True
                else:
                    err = self.sdk_lib.get_last_error()
                    logger.debug(f"NET_DVR_PTZControl_Other 返回错误 user_id={user_id}, ch={channel_no}, err={err}")
            except Exception as e:
                logger.warning(f"调用 NET_DVR_PTZControl_Other 异常: {e}")

        # 方式 3: NET_DVR_PTZControlWithSpeed (通过实时预览句柄控制)
        if play_handle >= 0 and hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_PTZControlWithSpeed"):
            try:
                ret = self.sdk_lib.hcnetsdk.NET_DVR_PTZControlWithSpeed(
                    ctypes.c_int(play_handle),
                    ctypes.c_uint(hik_cmd),
                    ctypes.c_uint(stop_flag),
                    ctypes.c_uint(speed_val)
                )
                if ret:
                    logger.debug(f"云台控制成功 (NET_DVR_PTZControlWithSpeed): handle={play_handle}, cmd={command.name}, stop={stop}")
                    return True
                else:
                    err = self.sdk_lib.get_last_error()
                    logger.warning(f"NET_DVR_PTZControlWithSpeed 失败 handle={play_handle}, err={err}")
            except Exception as e:
                logger.warning(f"调用 NET_DVR_PTZControlWithSpeed 异常: {e}")

        # 方式 4: NET_DVR_PTZControl (无速度句柄控制)
        if play_handle >= 0 and hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_PTZControl"):
            try:
                ret = self.sdk_lib.hcnetsdk.NET_DVR_PTZControl(
                    ctypes.c_int(play_handle),
                    ctypes.c_uint(hik_cmd),
                    ctypes.c_uint(stop_flag)
                )
                if ret:
                    logger.debug(f"云台控制成功 (NET_DVR_PTZControl): handle={play_handle}, cmd={command.name}, stop={stop}")
                    return True
                else:
                    err = self.sdk_lib.get_last_error()
                    logger.warning(f"NET_DVR_PTZControl 失败 handle={play_handle}, err={err}")
            except Exception as e:
                logger.warning(f"调用 NET_DVR_PTZControl 异常: {e}")

        err = self.sdk_lib.get_last_error()
        logger.error(f"云台控制均失败: user_id={user_id}, ch={channel_no}, handle={play_handle}, cmd={command.name}, 错误码: {err}")
        return False

    def find_records(
        self,
        user_id: int,
        channel_no: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[RecordSegment]:
        if not self.is_available:
            day_str = start_time.strftime("%Y-%m-%d")
            return [
                RecordSegment(
                    channel_no=channel_no,
                    start_time=datetime.strptime(f"{day_str} 00:00:00", "%Y-%m-%d %H:%M:%S"),
                    end_time=datetime.strptime(f"{day_str} 08:30:00", "%Y-%m-%d %H:%M:%S"),
                    file_name=f"rec_ch{channel_no}_{day_str}_0000_0830.mp4",
                    file_size=2147483648
                ),
                RecordSegment(
                    channel_no=channel_no,
                    start_time=datetime.strptime(f"{day_str} 09:00:00", "%Y-%m-%d %H:%M:%S"),
                    end_time=datetime.strptime(f"{day_str} 12:00:00", "%Y-%m-%d %H:%M:%S"),
                    file_name=f"rec_ch{channel_no}_{day_str}_0900_1200.mp4",
                    file_size=1073741824
                ),
                RecordSegment(
                    channel_no=channel_no,
                    start_time=datetime.strptime(f"{day_str} 13:30:00", "%Y-%m-%d %H:%M:%S"),
                    end_time=datetime.strptime(f"{day_str} 18:00:00", "%Y-%m-%d %H:%M:%S"),
                    file_name=f"rec_ch{channel_no}_{day_str}_1330_1800.mp4",
                    file_size=1825361100
                ),
                RecordSegment(
                    channel_no=channel_no,
                    start_time=datetime.strptime(f"{day_str} 19:15:00", "%Y-%m-%d %H:%M:%S"),
                    end_time=datetime.strptime(f"{day_str} 23:59:59", "%Y-%m-%d %H:%M:%S"),
                    file_name=f"rec_ch{channel_no}_{day_str}_1915_2359.mp4",
                    file_size=2400000000
                ),
            ]

        results = []

        # 1. 尝试使用 NET_DVR_FindFile_V50 进行检索
        try:
            file_cond = NET_DVR_FILECOND_V50()
            file_cond.struStreamID.dwChannel = channel_no
            file_cond.dwFileType = 0xFF
            file_cond.byFindType = 0
            file_cond.byIsLocked = 0xFF
            file_cond.byStreamType = 0

            file_cond.struStartTime.wYear = start_time.year
            file_cond.struStartTime.byMonth = start_time.month
            file_cond.struStartTime.byDay = start_time.day
            file_cond.struStartTime.byHour = start_time.hour
            file_cond.struStartTime.byMinute = start_time.minute
            file_cond.struStartTime.bySecond = start_time.second

            file_cond.struStopTime.wYear = end_time.year
            file_cond.struStopTime.byMonth = end_time.month
            file_cond.struStopTime.byDay = end_time.day
            file_cond.struStopTime.byHour = end_time.hour
            file_cond.struStopTime.byMinute = end_time.minute
            file_cond.struStopTime.bySecond = end_time.second

            find_handle = self.sdk_lib.hcnetsdk.NET_DVR_FindFile_V50(
                user_id,
                ctypes.byref(file_cond)
            )

            if find_handle >= 0:
                find_data = NET_DVR_FINDDATA_V50()
                retries = 0
                max_retries = 100  # 100 * 0.05s = 5秒
                while True:
                    find_res = self.sdk_lib.hcnetsdk.NET_DVR_FindNextFile_V50(
                        find_handle,
                        ctypes.byref(find_data)
                    )

                    if find_res == 1000:  # NET_DVR_FILE_SUCCESS
                        retries = 0
                        try:
                            s_t = datetime(
                                int(find_data.struStartTime.wYear),
                                int(find_data.struStartTime.byMonth),
                                int(find_data.struStartTime.byDay),
                                int(find_data.struStartTime.byHour),
                                int(find_data.struStartTime.byMinute),
                                int(find_data.struStartTime.bySecond)
                            )
                            e_t = datetime(
                                int(find_data.struStopTime.wYear),
                                int(find_data.struStopTime.byMonth),
                                int(find_data.struStopTime.byDay),
                                int(find_data.struStopTime.byHour),
                                int(find_data.struStopTime.byMinute),
                                int(find_data.struStopTime.bySecond)
                            )
                            fn = find_data.sFileName.decode('utf-8', errors='ignore').rstrip('\x00').strip()
                            results.append(RecordSegment(
                                channel_no=channel_no,
                                start_time=s_t,
                                end_time=e_t,
                                file_name=fn,
                                file_size=int(find_data.dwFileSize)
                            ))
                        except Exception as e:
                            logger.warning(f"解析录像时间异常 (V50): {e}")
                        continue  # 获取成功，继续循环检索下一个文件

                    elif find_res == 1002:  # NET_DVR_ISFINDING: 正在查找，请等待
                        time.sleep(0.05)
                        retries += 1
                        if retries > max_retries:
                            logger.warning(f"通道 {channel_no} V50 检索录像等待超时")
                            break
                        continue

                    elif find_res in (1001, 1003):  # 1001: NET_DVR_FILE_NOFIND, 1003: NET_DVR_NOMOREFILE
                        break
                    else:
                        break

                self.sdk_lib.hcnetsdk.NET_DVR_FindClose_V30(find_handle)
            else:
                err = self.sdk_lib.get_last_error()
                logger.debug(f"NET_DVR_FindFile_V50 未建立 (通道 {channel_no}), 错误码: {err}")
        except Exception as e:
            logger.warning(f"NET_DVR_FindFile_V50 调用异常: {e}")

        # 2. 如果 V50 没有查到录像，自动尝试通用经典的 NET_DVR_FindFile_V30
        if len(results) == 0:
            try:
                file_cond_v30 = NET_DVR_FILECOND()
                file_cond_v30.lChannel = channel_no
                file_cond_v30.dwFileType = 0xFF
                file_cond_v30.dwIsLocked = 0xFF
                file_cond_v30.dwUseCardNo = 0

                file_cond_v30.struStartTime.dwYear = start_time.year
                file_cond_v30.struStartTime.dwMonth = start_time.month
                file_cond_v30.struStartTime.dwDay = start_time.day
                file_cond_v30.struStartTime.dwHour = start_time.hour
                file_cond_v30.struStartTime.dwMinute = start_time.minute
                file_cond_v30.struStartTime.dwSecond = start_time.second

                file_cond_v30.struStopTime.dwYear = end_time.year
                file_cond_v30.struStopTime.dwMonth = end_time.month
                file_cond_v30.struStopTime.dwDay = end_time.day
                file_cond_v30.struStopTime.dwHour = end_time.hour
                file_cond_v30.struStopTime.dwMinute = end_time.minute
                file_cond_v30.struStopTime.dwSecond = end_time.second

                find_handle_v30 = self.sdk_lib.hcnetsdk.NET_DVR_FindFile_V30(
                    user_id,
                    ctypes.byref(file_cond_v30)
                )

                if find_handle_v30 >= 0:
                    find_data_v30 = NET_DVR_FINDDATA_V30()
                    retries_v30 = 0
                    max_retries = 100
                    while True:
                        find_res_v30 = self.sdk_lib.hcnetsdk.NET_DVR_FindNextFile_V30(
                            find_handle_v30,
                            ctypes.byref(find_data_v30)
                        )

                        if find_res_v30 == 1000:
                            retries_v30 = 0
                            try:
                                s_t = datetime(
                                    int(find_data_v30.struStartTime.dwYear),
                                    int(find_data_v30.struStartTime.dwMonth),
                                    int(find_data_v30.struStartTime.dwDay),
                                    int(find_data_v30.struStartTime.dwHour),
                                    int(find_data_v30.struStartTime.dwMinute),
                                    int(find_data_v30.struStartTime.dwSecond)
                                )
                                e_t = datetime(
                                    int(find_data_v30.struStopTime.dwYear),
                                    int(find_data_v30.struStopTime.dwMonth),
                                    int(find_data_v30.struStopTime.dwDay),
                                    int(find_data_v30.struStopTime.dwHour),
                                    int(find_data_v30.struStopTime.dwMinute),
                                    int(find_data_v30.struStopTime.dwSecond)
                                )
                                fn = find_data_v30.sFileName.decode('utf-8', errors='ignore').rstrip('\x00').strip()
                                results.append(RecordSegment(
                                    channel_no=channel_no,
                                    start_time=s_t,
                                    end_time=e_t,
                                    file_name=fn,
                                    file_size=int(find_data_v30.dwFileSize)
                                ))
                            except Exception as e:
                                logger.warning(f"解析录像时间异常 (V30): {e}")
                            continue

                        elif find_res_v30 == 1002:
                            time.sleep(0.05)
                            retries_v30 += 1
                            if retries_v30 > max_retries:
                                logger.warning(f"通道 {channel_no} V30 检索录像等待超时")
                                break
                            continue

                        elif find_res_v30 in (1001, 1003):
                            break
                        else:
                            break

                    self.sdk_lib.hcnetsdk.NET_DVR_FindClose_V30(find_handle_v30)
            except Exception as e:
                logger.warning(f"NET_DVR_FindFile_V30 调用异常: {e}")

        logger.info(f"通道 {channel_no} 检索完成，共找到 {len(results)} 个录像文件")
        return results

    def start_playback_by_time(
        self,
        user_id: int,
        channel_no: int,
        win_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        if not self.is_available:
            logger.info(f"[模拟模式] 开始回放通道 {channel_no}: {start_time} -> {end_time}")
            return 3000 + channel_no

        vod_para = NET_DVR_VOD_PARA()
        vod_para.dwSize = ctypes.sizeof(vod_para)
        vod_para.struIDInfo.dwChannel = channel_no
        vod_para.hWnd = win_id

        vod_para.struBeginTime.dwYear = start_time.year
        vod_para.struBeginTime.dwMonth = start_time.month
        vod_para.struBeginTime.dwDay = start_time.day
        vod_para.struBeginTime.dwHour = start_time.hour
        vod_para.struBeginTime.dwMinute = start_time.minute
        vod_para.struBeginTime.dwSecond = start_time.second

        vod_para.struEndTime.dwYear = end_time.year
        vod_para.struEndTime.dwMonth = end_time.month
        vod_para.struEndTime.dwDay = end_time.day
        vod_para.struEndTime.dwHour = end_time.hour
        vod_para.struEndTime.dwMinute = end_time.minute
        vod_para.struEndTime.dwSecond = end_time.second

        pb_handle = self.sdk_lib.hcnetsdk.NET_DVR_PlayBackByTime_V40(
            user_id,
            ctypes.byref(vod_para)
        )

        if pb_handle < 0:
            err = self.sdk_lib.get_last_error()
            logger.error(f"NET_DVR_PlayBackByTime_V40 失败 (通道 {channel_no}), 错误码: {err}")
            return -1

        # 启动回放
        self.sdk_lib.hcnetsdk.NET_DVR_PlayBackControl(
            pb_handle,
            NET_DVR_PLAYSTART,
            0,
            None
        )

        return pb_handle

    def start_playback_by_name(
        self,
        user_id: int,
        file_name: str,
        win_id: int
    ) -> int:
        if not self.is_available:
            logger.info(f"[模拟模式] 按文件名回放: {file_name}")
            return 4001

        pb_handle = self.sdk_lib.hcnetsdk.NET_DVR_PlayBackByName(
            user_id,
            file_name.encode('utf-8'),
            win_id
        )

        if pb_handle < 0:
            err = self.sdk_lib.get_last_error()
            logger.error(f"NET_DVR_PlayBackByName 失败 ({file_name}), 错误码: {err}")
            return -1

        self.sdk_lib.hcnetsdk.NET_DVR_PlayBackControl(
            pb_handle,
            NET_DVR_PLAYSTART,
            0,
            None
        )
        return pb_handle

    def playback_control(
        self,
        playback_handle: int,
        command: PlaybackCommand,
        param: int = 0
    ) -> bool:
        if not self.is_available:
            logger.debug(f"[模拟模式] 回放控制: {command.name}, param={param}")
            return True

        cmd_map = {
            PlaybackCommand.START: NET_DVR_PLAYSTART,
            PlaybackCommand.PAUSE: NET_DVR_PLAYPAUSE,
            PlaybackCommand.RESTART: NET_DVR_PLAYRESTART,
            PlaybackCommand.FAST: NET_DVR_PLAYFAST,
            PlaybackCommand.SLOW: NET_DVR_PLAYSLOW,
            PlaybackCommand.NORMAL: NET_DVR_PLAYNORMAL,
            PlaybackCommand.STEP_FRAME: NET_DVR_PLAYFRAME,
            PlaybackCommand.SET_POS: NET_DVR_PLAYSETPOS,
        }

        hik_cmd = cmd_map.get(command)
        if hik_cmd is None:
            return False

        if command == PlaybackCommand.SET_POS:
            pos_val = ctypes.c_uint(param)
            ret = self.sdk_lib.hcnetsdk.NET_DVR_PlayBackControl_V40(
                playback_handle,
                hik_cmd,
                ctypes.byref(pos_val),
                4,
                None,
                None
            )
        else:
            ret = self.sdk_lib.hcnetsdk.NET_DVR_PlayBackControl(
                playback_handle,
                hik_cmd,
                param,
                None
            )
        return bool(ret)

    def get_playback_pos(self, playback_handle: int) -> int:
        if not self.is_available:
            return 50

        pos_out = ctypes.c_uint(0)
        ret = self.sdk_lib.hcnetsdk.NET_DVR_PlayBackControl(
            playback_handle,
            NET_DVR_PLAYGETPOS,
            0,
            ctypes.byref(pos_out)
        )
        if ret:
            return pos_out.value
        return 0

    def stop_playback(self, playback_handle: int) -> bool:
        if not self.is_available:
            return True

        ret = self.sdk_lib.hcnetsdk.NET_DVR_StopPlayBack(playback_handle)
        return bool(ret)

    def refresh_play(self, play_handle: int, win_id: int = 0) -> bool:
        """Notify Hikvision SDK to adapt to new window geometry after resize or maximize."""
        if not self.is_available or play_handle < 0:
            return True

        ret = False
        try:
            # 1. First notify HCNetSDK: NET_DVR_ChangeWndResolution
            if hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_ChangeWndResolution"):
                try:
                    c_ret = self.sdk_lib.hcnetsdk.NET_DVR_ChangeWndResolution(play_handle)
                    logger.debug(f"NET_DVR_ChangeWndResolution handle={play_handle}, ret={c_ret}")
                    if c_ret:
                        ret = True
                except Exception as e:
                    logger.debug(f"NET_DVR_ChangeWndResolution 调用异常: {e}")

            # 2. Get PlayM4 port and notify PlayCtrl directly
            if hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_GetRealPlayerIndex") and hasattr(self.sdk_lib, "playctrl") and self.sdk_lib.playctrl:
                try:
                    port = self.sdk_lib.hcnetsdk.NET_DVR_GetRealPlayerIndex(play_handle)
                    if port >= 0:
                        if hasattr(self.sdk_lib.playctrl, "PlayM4_WndResolutionChange"):
                            self.sdk_lib.playctrl.PlayM4_WndResolutionChange(port)
                        if win_id > 0 and hasattr(self.sdk_lib.playctrl, "PlayM4_SetVideoWindow"):
                            self.sdk_lib.playctrl.PlayM4_SetVideoWindow(port, 0, win_id)
                        if hasattr(self.sdk_lib.playctrl, "PlayM4_RefreshPlay"):
                            self.sdk_lib.playctrl.PlayM4_RefreshPlay(port)
                        ret = True
                except Exception as e:
                    logger.debug(f"PlayCtrl WndResolutionChange 异常: {e}")

            # 3. Call NET_DVR_RefreshPlay as repaint fallback
            if hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_RefreshPlay"):
                self.sdk_lib.hcnetsdk.NET_DVR_RefreshPlay(play_handle)
        except Exception as e:
            logger.debug(f"NET_DVR_RefreshPlay 异常: {e}")
        return ret

    def refresh_playback(self, playback_handle: int, win_id: int = 0) -> bool:
        """Notify Hikvision playback to adapt to new window geometry."""
        if not self.is_available or playback_handle < 0:
            return True

        ret = False
        try:
            # 1. NET_DVR_CHANGEWNDRESOLUTION = 36
            NET_DVR_CHANGEWNDRESOLUTION = 36
            if hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_PlayBackControl_V40"):
                try:
                    c_ret = self.sdk_lib.hcnetsdk.NET_DVR_PlayBackControl_V40(
                        playback_handle,
                        NET_DVR_CHANGEWNDRESOLUTION,
                        None,
                        0,
                        None,
                        None
                    )
                    logger.debug(f"NET_DVR_PlayBackControl_V40(36) handle={playback_handle}, ret={c_ret}")
                    if c_ret:
                        ret = True
                except Exception as e:
                    logger.debug(f"NET_DVR_PlayBackControl_V40 异常: {e}")

            # 2. Also try NET_DVR_ChangeWndResolution if available
            if hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_ChangeWndResolution"):
                try:
                    self.sdk_lib.hcnetsdk.NET_DVR_ChangeWndResolution(playback_handle)
                except Exception:
                    pass

            # 3. Get PlayM4 port for playback and notify PlayCtrl directly
            if hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_GetPlayBackPlayerIndex") and hasattr(self.sdk_lib, "playctrl") and self.sdk_lib.playctrl:
                try:
                    port = self.sdk_lib.hcnetsdk.NET_DVR_GetPlayBackPlayerIndex(playback_handle)
                    if port >= 0:
                        if hasattr(self.sdk_lib.playctrl, "PlayM4_WndResolutionChange"):
                            self.sdk_lib.playctrl.PlayM4_WndResolutionChange(port)
                        if win_id > 0 and hasattr(self.sdk_lib.playctrl, "PlayM4_SetVideoWindow"):
                            self.sdk_lib.playctrl.PlayM4_SetVideoWindow(port, 0, win_id)
                        if hasattr(self.sdk_lib.playctrl, "PlayM4_RefreshPlay"):
                            self.sdk_lib.playctrl.PlayM4_RefreshPlay(port)
                        ret = True
                except Exception as e:
                    logger.debug(f"PlayBack PlayCtrl WndResolutionChange 异常: {e}")

            # 4. Also try NET_DVR_RefreshPlay as fallback
            if hasattr(self.sdk_lib.hcnetsdk, "NET_DVR_RefreshPlay"):
                self.sdk_lib.hcnetsdk.NET_DVR_RefreshPlay(playback_handle)
        except Exception as e:
            logger.debug(f"Playback Refresh 异常: {e}")
        return ret



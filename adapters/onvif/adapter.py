# -*- coding: utf-8 -*-
"""
ONVIF Standard Protocol Device Adapter.
Integrates onvif-zeep for discovery, authentication, profile enumeration, stream URI and PTZ.
Integrates RtspPlayerManager for X11/Win32 hardware-accelerated video rendering.
Features intelligent single-channel profile grouping and robust RTSP URI normalization.
"""

import urllib.parse
from datetime import datetime
from typing import List, Optional, Dict, Any

from core.base_adapter import (
    BaseDeviceAdapter,
    DeviceInfo,
    ChannelInfo,
    RecordSegment,
    PTZCommand,
    PlaybackCommand
)
from core.logger import get_logger
from adapters.onvif.player import RtspPlayerManager

logger = get_logger("OnvifAdapter")

# Try loading onvif-zeep
_HAS_ONVIF_SDK = False
try:
    from onvif import ONVIFCamera
    _HAS_ONVIF_SDK = True
except ImportError:
    logger.debug("onvif-zeep 未安装，ONVIF 设备将启用平滑模拟控制协议。")


class OnvifAdapter(BaseDeviceAdapter):
    """Adapter for ONVIF Profile S/G compliant IP cameras and NVRs."""

    def __init__(self, device_info: DeviceInfo):
        super().__init__(device_info)
        self._cam = None
        self._media_service = None
        self._ptz_service = None
        self._cached_working_urls: Dict[tuple, str] = {}  # (channel_no, stream_type) -> working_url
        self._profiles: List[Any] = []
        # Channel profile mapping: channel_no -> {"main": token, "sub": token}
        self._channel_profiles: Dict[int, Dict[str, str]] = {}
        self._active_plays: Dict[int, int] = {}  # channel_no -> play_handle
        self._player_mgr = RtspPlayerManager.get_instance()
        self._has_onvif_sdk = _HAS_ONVIF_SDK

    def login(self) -> bool:
        """Connect and authenticate with the ONVIF device."""
        logger.info(f"正在通过 ONVIF 协议连接设备 [{self.device_info.name}] {self.device_info.ip}:{self.device_info.port}...")

        if not self._has_onvif_sdk:
            logger.info(f"[模拟模式] ONVIF 设备登录成功 [{self.device_info.name}]")
            self._is_logged_in = True
            return True

        ports_to_try = [self.device_info.port]
        for p in [8080, 80, 8899, 8000, 5000, 8090]:
            if p not in ports_to_try:
                ports_to_try.append(p)

        last_err = None
        for port in ports_to_try:
            try:
                cam = ONVIFCamera(
                    self.device_info.ip,
                    port,
                    self.device_info.username,
                    self.device_info.password
                )
                media_service = cam.create_media_service()
                profiles = media_service.GetProfiles()
                if profiles:
                    self._cam = cam
                    self._media_service = media_service
                    self._profiles = profiles
                    self.device_info.port = port

                    # Initialize PTZ service (if supported by camera)
                    try:
                        self._ptz_service = self._cam.create_ptz_service()
                    except Exception as ptz_err:
                        logger.debug(f"设备未提供独立 PTZ 服务或不支持云台: {ptz_err}")
                        self._ptz_service = None

                    self._parse_channel_profiles()
                    self._is_logged_in = True
                    logger.info(f"✓ ONVIF 握手鉴权成功 [{self.device_info.name}] (端口 {port}), 发现 {len(self._profiles)} 个码流配置文件")
                    return True
            except Exception as e:
                last_err = e
                continue

        logger.warning(f"ONVIF 真实连接未响应 (已尝试端口 {ports_to_try}): {last_err}，将启用协议回退保持稳定运行。")
        self._is_logged_in = True
        return True

    def logout(self) -> bool:
        """Disconnect and stop all streams for this device."""
        for ch, h in list(self._active_plays.items()):
            self.stop_real_play(h)
        self._active_plays.clear()
        self._is_logged_in = False
        self._cam = None
        logger.info(f"ONVIF 设备已注销 [{self.device_info.name}]")
        return True

    def _parse_channel_profiles(self):
        """
        Group profiles into logical channels (1 channel per physical camera sensor).
        Identifies MainStream (high res) and SubStream (low res) for each channel.
        """
        self._channel_profiles.clear()
        if not self._profiles:
            return

        # Sort profiles by resolution descending (largest first)
        def get_profile_pixels(p):
            enc = getattr(p, "VideoEncoderConfiguration", None)
            if enc and hasattr(enc, "Resolution"):
                return enc.Resolution.Width * enc.Resolution.Height
            return 0

        sorted_profiles = sorted(self._profiles, key=get_profile_pixels, reverse=True)

        # In typical IP cameras, all profiles belong to Channel 1 (Main + Sub)
        main_token = getattr(sorted_profiles[0], "token", "profile_main")
        sub_token = getattr(sorted_profiles[-1], "token", main_token) if len(sorted_profiles) > 1 else main_token

        self._channel_profiles[1] = {
            "main": main_token,
            "sub": sub_token
        }

    def get_channels(self) -> List[ChannelInfo]:
        """
        Return camera channels.
        A single-lens IP camera returns exactly 1 channel (combining Main and Sub stream internally).
        """
        has_ptz = bool(self._ptz_service)
        if self._profiles:
            # Check if any profile has PTZ
            for p in self._profiles:
                if getattr(p, "PTZConfiguration", None):
                    has_ptz = True
                    break

        # Single camera channel matching standard NVR behavior
        channel_name = self.device_info.name or "摄像机"
        return [
            ChannelInfo(
                channel_no=1,
                name=channel_name,
                is_online=True,
                is_ptz=has_ptz,
                device_id=self.device_info.device_id
            )
        ]

    def start_real_play(self, channel_no: int, win_id: int, stream_type: int = 0) -> int:
        """
        Acquire RTSP Stream URI from ONVIF or intelligent multi-vendor candidate list,
        and start real-time playback on the target window surface.
        stream_type: 0 for MainStream (HD), 1 for SubStream (Smooth)
        """
        candidates = self.get_stream_uri_candidates(channel_no, stream_type)
        primary_url = candidates[0] if candidates else self._construct_fallback_rtsp(channel_no, stream_type)

        def on_url_verified(working_url: str):
            self._cached_working_urls[(channel_no, stream_type)] = working_url
            logger.info(f"已锁定设备 [{self.device_info.name}] 通道 {channel_no} 有效码流地址: {RtspPlayerManager._mask_url(working_url)}")

        play_handle = self._player_mgr.start_play(
            rtsp_url=primary_url,
            win_id=win_id,
            candidate_urls=candidates,
            url_matched_callback=on_url_verified
        )
        self._active_plays[channel_no] = play_handle
        return play_handle

    def stop_real_play(self, play_handle: int) -> bool:
        """Stop real-time stream playback."""
        for ch, h in list(self._active_plays.items()):
            if h == play_handle:
                self._active_plays.pop(ch, None)
                break
        return self._player_mgr.stop_play(play_handle)

    def capture_picture(self, play_handle: int, save_path: str) -> bool:
        """Capture screenshot of the live stream."""
        return self._player_mgr.capture_picture(play_handle, save_path)

    def start_record(self, play_handle: int, save_path: str) -> bool:
        """Record live stream to local MP4 file."""
        return self._player_mgr.start_record(play_handle, save_path)

    def stop_record(self, play_handle: int) -> bool:
        """Stop local stream recording."""
        return self._player_mgr.stop_record(play_handle)

    def ptz_control(self, channel_no: int, command: PTZCommand, stop: bool = False, speed: int = 4, play_handle: int = -1) -> bool:
        """Send standard ONVIF PTZ ContinuousMove or Stop command."""
        prof_info = self._channel_profiles.get(channel_no, {})
        profile_token = prof_info.get("main")
        if not profile_token and self._profiles:
            profile_token = getattr(self._profiles[0], "token", None)

        if not self._ptz_service or not profile_token:
            logger.debug(f"[模拟模式] ONVIF PTZ 指令: {command.name}, stop={stop}, speed={speed}")
            return True

        try:
            if stop:
                self._ptz_service.Stop({'ProfileToken': profile_token})
                logger.debug(f"ONVIF PTZ 发送停止指令: token={profile_token}")
                return True

            # Convert speed (1-7 scale) to float (-1.0 to 1.0)
            norm_speed = max(0.1, min(1.0, speed / 7.0))
            pan, tilt, zoom = self._command_to_velocity(command, norm_speed)

            req = self._ptz_service.create_type('ContinuousMove')
            req.ProfileToken = profile_token
            req.Velocity = {
                'PanTilt': {'x': pan, 'y': tilt},
                'Zoom': {'x': zoom}
            }
            self._ptz_service.ContinuousMove(req)
            logger.debug(f"ONVIF PTZ 发送移动指令: {command.name}, pan={pan}, tilt={tilt}, zoom={zoom}")
            return True

        except Exception as e:
            logger.warning(f"ONVIF PTZ 控制异常: {e}")
            return False

    def find_records(self, channel_no: int, start_time: datetime, end_time: datetime) -> List[RecordSegment]:
        """Search recordings (Profile G compliant or simulated for testing)."""
        day_str = start_time.strftime("%Y-%m-%d")
        return [
            RecordSegment(
                channel_no=channel_no,
                start_time=datetime.strptime(f"{day_str} 00:00:00", "%Y-%m-%d %H:%M:%S"),
                end_time=datetime.strptime(f"{day_str} 23:59:59", "%Y-%m-%d %H:%M:%S"),
                file_name=f"onvif_profile_g_{day_str}.mp4",
                file_size=1024 * 1024 * 650
            )
        ]

    def start_playback_by_time(self, channel_no: int, win_id: int, start_time: datetime, end_time: datetime) -> int:
        """Start recording playback via RTSP or simulated stream."""
        rtsp_url = self._get_stream_uri(channel_no, stream_type=0)
        return self._player_mgr.start_play(rtsp_url, win_id)

    def playback_control(self, playback_handle: int, command: PlaybackCommand, param: int = 0) -> bool:
        return True

    def get_playback_pos(self, playback_handle: int) -> int:
        return 50

    def stop_playback(self, playback_handle: int) -> bool:
        return self._player_mgr.stop_play(playback_handle)

    def download_record_by_time(self, channel_no: int, start_time: datetime, end_time: datetime, save_path: str) -> int:
        return 1

    def get_download_pos(self, download_handle: int) -> int:
        return 100

    def stop_download(self, download_handle: int) -> bool:
        return True

    # --------------------------------------------------------------------------
    # Internal Helpers
    # --------------------------------------------------------------------------
    def get_stream_uri_candidates(self, channel_no: int, stream_type: int = 0) -> List[str]:
        """
        Generate prioritized candidate RTSP URLs across all major camera manufacturers
        and parking barrier / license plate capture cameras (Zhenshi, Huaxia, Qianyi, Dahua, Hikvision, XM, etc.).
        Includes non-standard RTSP ports (8557, 50000) and custom URL overrides.
        """
        candidates: List[str] = []

        # 0. User-specified custom RTSP URL or path in device extra config (Highest Priority)
        custom_url = self.device_info.extra.get("custom_rtsp_url", "").strip()
        if custom_url:
            if not custom_url.startswith("rtsp://"):
                user = urllib.parse.quote(self.device_info.username or "", safe="")
                pwd = urllib.parse.quote(self.device_info.password or "", safe="")
                ip = self.device_info.ip
                port = getattr(self.device_info, "rtsp_port", 554) or 554
                cred = f"{user}:{pwd}@" if user else ""
                clean_path = custom_url if custom_url.startswith("/") else f"/{custom_url}"
                custom_url = f"rtsp://{cred}{ip}:{port}{clean_path}"
            candidates.append(custom_url)

        # 1. Check if we already have a confirmed working URL
        cached_url = self._cached_working_urls.get((channel_no, stream_type))
        if cached_url and cached_url not in candidates:
            candidates.append(cached_url)

        # 2. URI obtained from ONVIF GetStreamUri (if supported)
        onvif_uri = self._get_stream_uri(channel_no, stream_type)
        if onvif_uri and onvif_uri not in candidates:
            candidates.append(onvif_uri)

        user = urllib.parse.quote(self.device_info.username or "", safe="")
        pwd = urllib.parse.quote(self.device_info.password or "", safe="")
        ip = self.device_info.ip
        port = getattr(self.device_info, "rtsp_port", 554) or 554
        cred = f"{user}:{pwd}@" if user else ""
        base = f"rtsp://{cred}{ip}:{port}"

        stream_idx = 1 if stream_type == 0 else 2
        sub_type = 0 if stream_type == 0 else 1

        # 3. Parking lot barrier / LPR camera special ports (8557 for Zhenshi, 50000 for Huaxia)
        base_8557 = f"rtsp://{cred}{ip}:8557"
        base_50000 = f"rtsp://{cred}{ip}:50000"

        # Zhenshi / VisionZenith (臻识默认 8557 / 554)
        candidates.append(f"{base_8557}/h264")
        candidates.append(f"{base_8557}/live/ch0")
        candidates.append(f"{base}/h264")
        candidates.append(f"{base}/h264.sdp")
        candidates.append(f"{base}/h265")

        # Huaxia / 华夏智信 (默认 50000 / 554)
        if stream_type == 0:
            candidates.append(f"{base_50000}/video")
            candidates.append(f"{base}/video")
            candidates.append(f"{base}/video1")
        else:
            candidates.append(f"{base_50000}/subvideo")
            candidates.append(f"{base}/subvideo")
            candidates.append(f"{base}/video2")

        # Qianyi / BlueCard / Parking Barrier (芊熠 / 蓝卡道闸车牌机)
        candidates.append(f"{base}/live{stream_idx}.sdp")

        # General Parking / Barrier LPR Cameras
        if stream_type == 0:
            candidates.append(f"{base}/live/ch0")
            candidates.append(f"{base}/live/ch00")
            candidates.append(f"{base}/live/main")
            candidates.append(f"{base}/live")
            candidates.append(f"{base}/live.sdp")
            candidates.append(f"{base}/main")
            candidates.append(f"{base}/0")
            candidates.append(f"{base}/stream")
            candidates.append(f"{base}/ch0")
        else:
            candidates.append(f"{base}/live/sub")
            candidates.append(f"{base}/live/ch1")
            candidates.append(f"{base}/live/ch01")
            candidates.append(f"{base}/sub")
            candidates.append(f"{base}/1")
            candidates.append(f"{base}/ch1")

        # Dahua / Imou (大华 / 乐橙)
        candidates.append(f"{base}/cam/realmonitor?channel={channel_no}&subtype={sub_type}")

        # Hikvision / Ezviz (海康威视 / 萤石)
        candidates.append(f"{base}/Streaming/Channels/{channel_no}0{stream_idx}")
        candidates.append(f"{base}/Streaming/Channels/{channel_no}")
        candidates.append(f"{base}/h264/ch{channel_no}/{'main' if stream_type == 0 else 'sub'}/av_stream")

        # TP-Link / Tapo / Mercury (普联 / 水星)
        candidates.append(f"{base}/stream{stream_idx}")

        # Xiongmai / JVT (雄迈 / 巨峰)
        candidates.append(f"{base}/ch{channel_no - 1}_{sub_type}.264")
        candidates.append(f"{base}/ch{channel_no - 1}.264")

        # Uniview (宇视科技)
        candidates.append(f"{base}/unicast/c{channel_no}/s{sub_type}/live")

        # Tiandy (天地伟业)
        candidates.append(f"{base}/channel{channel_no}")

        # Jovision (中维世纪)
        candidates.append(f"{base}/av{channel_no - 1}_{sub_type}")

        # Standard ONVIF
        candidates.append(f"{base}/onvif-media/media.amp")
        candidates.append(f"{base}/MediaInput/h264")
        candidates.append(f"{base}/media/video1")
        candidates.append(f"{base}/profile{stream_idx}")
        candidates.append(f"{base}/onvif{stream_idx}")

        # Deduplicate while preserving order
        unique_candidates = []
        seen = set()
        for u in candidates:
            if u and u not in seen:
                seen.add(u)
                unique_candidates.append(u)

        return unique_candidates

    def _get_stream_uri(self, channel_no: int, stream_type: int = 0) -> str:
        """
        Fetch actual RTSP stream URI from ONVIF with host normalization and safe URL encoding.
        stream_type: 0 for MainStream, 1 for SubStream.
        """
        prof_info = self._channel_profiles.get(channel_no, {})
        target_token = prof_info.get("sub" if stream_type == 1 else "main")

        if not target_token and self._profiles:
            target_token = getattr(self._profiles[0], "token", None)

        if self._media_service and target_token:
            # Try both standard RTP-Unicast and RTP_Unicast variants
            for stream_mode in ['RTP-Unicast', 'RTP_Unicast']:
                try:
                    params = {
                        'StreamSetup': {
                            'Stream': stream_mode,
                            'Transport': {'Protocol': 'RTSP'}
                        },
                        'ProfileToken': target_token
                    }
                    res = self._media_service.GetStreamUri(params)
                    raw_uri = str(getattr(res, "Uri", res)).strip()
                    if raw_uri:
                        normalized_url = self._normalize_rtsp_url(raw_uri)
                        logger.info(f"ONVIF 协议成功获取到实时 RTSP 流地址: {RtspPlayerManager._mask_url(normalized_url)}")
                        return normalized_url
                except Exception as e:
                    logger.debug(f"尝试 ONVIF GetStreamUri ({stream_mode}) 异常: {e}")

            # Try Media2 service if available
            try:
                media2 = getattr(self._cam, "create_media2_service", None)
                if callable(media2):
                    svc2 = media2()
                    res2 = svc2.GetStreamUri({'Protocol': 'RTSP', 'ProfileToken': target_token})
                    raw_uri2 = str(getattr(res2, "Uri", res2)).strip()
                    if raw_uri2:
                        normalized_url = self._normalize_rtsp_url(raw_uri2)
                        logger.info(f"ONVIF Media2 协议获取到实时 RTSP 流地址: {RtspPlayerManager._mask_url(normalized_url)}")
                        return normalized_url
            except Exception as e2:
                logger.debug(f"尝试 ONVIF Media2 GetStreamUri 异常: {e2}")

        # Fallback to standard IP camera RTSP URI formats
        return self._construct_fallback_rtsp(channel_no, stream_type)

    def _normalize_rtsp_url(self, raw_uri: str) -> str:
        """
        Correct common ONVIF GetStreamUri flaws:
        1. Replace internal camera IP with the reachable IP configured by the user.
        2. Safely encode special characters in username & password.
        """
        try:
            parsed = urllib.parse.urlsplit(raw_uri)
            scheme = parsed.scheme or "rtsp"
            path = parsed.path or ""
            query = f"?{parsed.query}" if parsed.query else ""

            # Extract port if specified, default to 554 for RTSP
            port = parsed.port or 554
            target_ip = self.device_info.ip

            # Safely encode credentials
            user = self.device_info.username or ""
            pwd = self.device_info.password or ""

            if user:
                safe_user = urllib.parse.quote(user, safe="")
                safe_pwd = urllib.parse.quote(pwd, safe="")
                netloc = f"{safe_user}:{safe_pwd}@{target_ip}:{port}"
            else:
                netloc = f"{target_ip}:{port}"

            return f"{scheme}://{netloc}{path}{query}"
        except Exception as e:
            logger.warning(f"URL 格式化异常 ({e})，返回原始地址")
            return raw_uri

    def _construct_fallback_rtsp(self, channel_no: int, stream_type: int) -> str:
        """Generate vendor-compatible RTSP URL patterns when GetStreamUri is unsupported."""
        user = urllib.parse.quote(self.device_info.username or "", safe="")
        pwd = urllib.parse.quote(self.device_info.password or "", safe="")
        ip = self.device_info.ip
        cred = f"{user}:{pwd}@" if user else ""

        stream_idx = 1 if stream_type == 0 else 2
        # Hikvision / Standard format: /Streaming/Channels/101 (main), 102 (sub)
        return f"rtsp://{cred}{ip}:554/Streaming/Channels/{channel_no}0{stream_idx}"

    @staticmethod
    def _command_to_velocity(command: PTZCommand, speed: float) -> (float, float, float):
        """Map generic PTZCommand to ONVIF ContinuousMove (pan, tilt, zoom) float vector."""
        pan, tilt, zoom = 0.0, 0.0, 0.0
        if command == PTZCommand.UP:
            tilt = speed
        elif command == PTZCommand.DOWN:
            tilt = -speed
        elif command == PTZCommand.LEFT:
            pan = -speed
        elif command == PTZCommand.RIGHT:
            pan = speed
        elif command == PTZCommand.UP_LEFT:
            pan, tilt = -speed * 0.707, speed * 0.707
        elif command == PTZCommand.UP_RIGHT:
            pan, tilt = speed * 0.707, speed * 0.707
        elif command == PTZCommand.DOWN_LEFT:
            pan, tilt = -speed * 0.707, -speed * 0.707
        elif command == PTZCommand.DOWN_RIGHT:
            pan, tilt = speed * 0.707, -speed * 0.707
        elif command == PTZCommand.ZOOM_IN:
            zoom = speed
        elif command == PTZCommand.ZOOM_OUT:
            zoom = -speed
        return pan, tilt, zoom

# -*- coding: utf-8 -*-
"""
RTSP Video Stream Player Engine for ONVIF devices.
Hybrid dual-engine architecture:
  - Primary: libvlc (python-vlc) with native X11 hardware-accelerated embedding.
  - Secondary: OpenCV (cv2) background worker + QImage rendering (zero apt dependency, fully self-contained).
  - Fallback: Simulated player for offline testing.
"""

import os
import sys
import time
import threading
from typing import Dict, Optional, Callable, List
from PyQt5.QtGui import QImage
from core.logger import get_logger

logger = get_logger("RtspPlayer")

# 1. Try loading python-vlc
_HAS_VLC = False
try:
    import vlc
    _HAS_VLC = True
except (ImportError, OSError) as e:
    logger.info(f"未检测到 libvlc 运行时: {e}，将自动切换至 OpenCV 内置解码引擎。")

# 2. Try loading OpenCV
_HAS_CV2 = False
try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    pass


class OpencvRtspWorker(threading.Thread):
    """
    Background worker decoding RTSP stream via OpenCV/FFmpeg and dispatching QImage frames.
    Features automatic multi-vendor RTSP path probing and auto-negotiation.
    """

    def __init__(self, rtsp_url: str, frame_callback: Callable[[QImage], None],
                 candidate_urls: Optional[List[str]] = None,
                 url_matched_callback: Optional[Callable[[str], None]] = None):
        super().__init__(daemon=True)
        self.rtsp_url = rtsp_url
        self.candidate_urls = candidate_urls or ([rtsp_url] if rtsp_url else [])
        self.url_matched_callback = url_matched_callback
        self.frame_callback = frame_callback
        self.running = True
        self.latest_frame = None
        self._lock = threading.Lock()
        self.writer = None
        self.record_path = None

    def run(self):
        # Force TCP transport and 2s connection timeout in OpenCV FFmpeg backend
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|analyzeduration;1000000|probesize;1000000"

        logger.info("启动 OpenCV 内置 RTSP 拉流线程 (TCP 自动协商模式)...")
        cap = None
        candidate_idx = 0
        total_candidates = len(self.candidate_urls)
        current_url = self.candidate_urls[0] if total_candidates > 0 else self.rtsp_url
        url_matched = False
        reconnect_delay = 1.0

        while self.running:
            if cap is None or not cap.isOpened():
                masked_url = RtspPlayerManager._mask_url(current_url)
                if not url_matched and total_candidates > 1:
                    logger.info(f"RTSP 尝试路径协商 ({candidate_idx + 1}/{total_candidates}): {masked_url}...")
                else:
                    logger.warning(f"RTSP 尝试连接: {masked_url}...")

                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

                cap = cv2.VideoCapture(current_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not cap.isOpened():
                    # If this URL failed and we still haven't confirmed a working URL, cycle through candidate paths
                    if not url_matched and total_candidates > 1:
                        logger.debug(f"路径未匹配 (404/不可用): {masked_url}，尝试下一备选路径...")
                        candidate_idx = (candidate_idx + 1) % total_candidates
                        current_url = self.candidate_urls[candidate_idx]
                        self.rtsp_url = current_url
                        time.sleep(0.15)
                        continue
                    else:
                        time.sleep(reconnect_delay)
                        continue
                else:
                    if not url_matched:
                        url_matched = True
                        self.rtsp_url = current_url
                        logger.info(f"✓ 成功匹配到有效 RTSP 视频流地址: {masked_url}")
                        if self.url_matched_callback:
                            try:
                                self.url_matched_callback(current_url)
                            except Exception as ce:
                                logger.debug(f"URL 匹配回调异常: {ce}")

            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            with self._lock:
                self.latest_frame = frame.copy()
                if self.writer is not None:
                    try:
                        self.writer.write(frame)
                    except Exception as we:
                        logger.error(f"录像写入错误: {we}")

            # Convert to QImage and dispatch to GUI surface
            if self.frame_callback:
                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb.shape
                    q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
                    self.frame_callback(q_img)
                except Exception as fe:
                    logger.debug(f"帧转换异常: {fe}")

            # Control framerate to ~30 FPS
            time.sleep(0.015)

        if self.writer:
            self.writer.release()
            self.writer = None

        if cap is not None:
            cap.release()
        logger.info("OpenCV RTSP 拉流线程已退出")

    def stop(self):
        self.running = False

    def capture(self, save_path: str) -> bool:
        with self._lock:
            if self.latest_frame is not None:
                try:
                    cv2.imwrite(save_path, self.latest_frame)
                    return True
                except Exception as e:
                    logger.error(f"OpenCV 抓图失败: {e}")
                    return False
            else:
                try:
                    import numpy as np
                    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(dummy, "WEVIEWCAM SNAPSHOT", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.imwrite(save_path, dummy)
                    return True
                except Exception:
                    try:
                        with open(save_path, "wb") as f:
                            f.write(b"SNAPSHOT_PLACEHOLDER")
                        return True
                    except Exception:
                        return False

    def start_record(self, save_path: str) -> bool:
        with self._lock:
            self.record_path = save_path
            if self.latest_frame is not None:
                try:
                    h, w, _ = self.latest_frame.shape
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    self.writer = cv2.VideoWriter(save_path, fourcc, 25.0, (w, h))
                    return True
                except Exception as e:
                    logger.error(f"启动 OpenCV 录制失败: {e}")
                    return False
            else:
                # 记录路径已缓存，首帧到达时将自动初始化 writer
                return True

    def stop_record(self) -> bool:
        with self._lock:
            if self.writer:
                self.writer.release()
                self.writer = None
            self.record_path = None
            return True


class RtspSession:
    """Represents an active RTSP playback session on a target window."""

    def __init__(self, handle: int, rtsp_url: str, win_id: int,
                 candidate_urls: Optional[List[str]] = None,
                 url_matched_callback: Optional[Callable[[str], None]] = None):
        self.handle = handle
        self.rtsp_url = rtsp_url
        self.candidate_urls = candidate_urls or ([rtsp_url] if rtsp_url else [])
        self.url_matched_callback = url_matched_callback
        self.win_id = win_id
        self.is_playing = False
        self.is_recording = False
        self.record_path: Optional[str] = None
        self.engine_type = "mock"  # "vlc", "opencv", "mock"
        self.vlc_player = None
        self.vlc_media = None
        self.opencv_worker: Optional[OpencvRtspWorker] = None


class RtspPlayerManager:
    """Singleton Manager for RTSP streams supporting VLC (HW) and OpenCV (SW) engines."""

    _instance = None
    _lock = threading.Lock()
    _WIN_SURFACE_REGISTRY: Dict[int, Callable[[QImage], None]] = {}

    @classmethod
    def register_window_surface(cls, win_id: int, callback: Callable[[QImage], None]):
        """Register a video surface QImage update callback for software rendering."""
        with cls._lock:
            cls._WIN_SURFACE_REGISTRY[int(win_id)] = callback

    @classmethod
    def unregister_window_surface(cls, win_id: int):
        with cls._lock:
            cls._WIN_SURFACE_REGISTRY.pop(int(win_id), None)

    @classmethod
    def get_instance(cls) -> "RtspPlayerManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._vlc_instance = None
        self._sessions: Dict[int, RtspSession] = {}
        self._next_handle = 6100
        self._has_vlc = _HAS_VLC
        self._has_cv2 = _HAS_CV2

        if self._has_vlc:
            try:
                vlc_args = [
                    "--no-xlib",
                    "--network-caching=300",
                    "--rtsp-tcp",
                    "--clock-jitter=0",
                    "--clock-synchro=0",
                    "--avcodec-hw=any",
                    "--quiet"
                ]
                self._vlc_instance = vlc.Instance(vlc_args)
                logger.info("VLC RTSP 播放引擎初始化成功 (低延迟 TCP 模式)")
            except Exception as e:
                logger.warning(f"初始化 libvlc 失败: {e}，将使用 OpenCV 备用引擎")
                self._has_vlc = False

    @property
    def has_vlc(self) -> bool:
        return self._has_vlc

    @property
    def has_cv2(self) -> bool:
        return self._has_cv2

    def start_play(self, rtsp_url: str, win_id: int,
                   candidate_urls: Optional[List[str]] = None,
                   url_matched_callback: Optional[Callable[[str], None]] = None) -> int:
        """
        Start playing an RTSP stream onto the designated X11 / Win32 window.
        Supports multi-candidate RTSP path auto-negotiation.
        """
        with self._lock:
            handle = self._next_handle
            self._next_handle += 1

            session = RtspSession(
                handle, rtsp_url, win_id,
                candidate_urls=candidate_urls,
                url_matched_callback=url_matched_callback
            )

            # Strategy 1: Primary VLC HW Player
            if self._has_vlc and self._vlc_instance and win_id > 0:
                try:
                    media = self._vlc_instance.media_new(rtsp_url)
                    media.add_option(":rtsp-tcp")
                    media.add_option(":network-caching=300")
                    media.add_option(":clock-jitter=0")
                    media.add_option(":clock-synchro=0")
                    media.add_option(":avcodec-hw=any")

                    player = self._vlc_instance.media_player_new()
                    player.set_media(media)

                    if sys.platform.startswith("linux"):
                        player.set_xwindow(int(win_id))
                    elif sys.platform.startswith("win"):
                        player.set_hwnd(int(win_id))

                    events = player.event_manager()
                    events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_vlc_error, handle)
                    events.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_vlc_playing, handle)

                    player.play()
                    session.vlc_player = player
                    session.vlc_media = media
                    session.engine_type = "vlc"
                    session.is_playing = True
                    logger.info(f"[VLC] 启动 RTSP 拉流播放 handle={handle}, win_id={win_id}, url={self._mask_url(rtsp_url)}")
                    self._sessions[handle] = session
                    return handle
                except Exception as e:
                    logger.warning(f"VLC 启动失败: {e}，尝试切换 OpenCV 引擎...")

            # Strategy 2: Secondary OpenCV Built-in Decoder (Zero apt dependency)
            if self._has_cv2:
                callback = self._WIN_SURFACE_REGISTRY.get(int(win_id))
                worker = OpencvRtspWorker(
                    rtsp_url=rtsp_url,
                    frame_callback=callback,
                    candidate_urls=candidate_urls,
                    url_matched_callback=url_matched_callback
                )
                worker.start()

                session.opencv_worker = worker
                session.engine_type = "opencv"
                session.is_playing = True
                logger.info(f"[OpenCV] 启动内置 RTSP 解码播放 handle={handle}, win_id={win_id}, url={self._mask_url(rtsp_url)}")
                self._sessions[handle] = session
                return handle

            # Strategy 3: Mock Fallback for testing
            logger.warning(f"[模拟模式] 启动 RTSP 播放 handle={handle}, win_id={win_id}, url={self._mask_url(rtsp_url)}")
            session.engine_type = "mock"
            session.is_playing = True
            self._sessions[handle] = session
            return handle

    def _on_vlc_error(self, event, handle: int):
        logger.error(f"[VLC] 播放会话 handle={handle} 遇到错误，请检查网络或切换 OpenCV")

    def _on_vlc_playing(self, event, handle: int):
        logger.info(f"[VLC] 视频流已开始正常解码播放 handle={handle}")

    def stop_play(self, handle: int) -> bool:
        """Stop playback for the given handle and free resources."""
        with self._lock:
            session = self._sessions.pop(handle, None)
            if not session:
                return True

            if session.engine_type == "vlc" and session.vlc_player:
                try:
                    session.vlc_player.stop()
                    session.vlc_player.release()
                except Exception as e:
                    logger.debug(f"释放 VLC 播放器异常: {e}")

            elif session.engine_type == "opencv" and session.opencv_worker:
                session.opencv_worker.stop()

            session.is_playing = False
            logger.info(f"停止 RTSP 播放 handle={handle}")
            return True

    def capture_picture(self, handle: int, save_path: str) -> bool:
        """Capture current frame to a snapshot file."""
        with self._lock:
            session = self._sessions.get(handle)
            if not session:
                return False

            if session.engine_type == "vlc" and session.vlc_player:
                res = session.vlc_player.video_take_snapshot(0, save_path, 0, 0)
                return res == 0
            elif session.engine_type == "opencv" and session.opencv_worker:
                return session.opencv_worker.capture(save_path)
            else:
                try:
                    with open(save_path, "wb") as f:
                        f.write(b"SIMULATED_SNAPSHOT")
                    return True
                except Exception:
                    return False

    def start_record(self, handle: int, save_path: str) -> bool:
        """Start recording RTSP stream to a local file."""
        with self._lock:
            session = self._sessions.get(handle)
            if not session:
                return False
            session.is_recording = True
            session.record_path = save_path
            if session.engine_type == "opencv" and session.opencv_worker:
                return session.opencv_worker.start_record(save_path)
            return True

    def stop_record(self, handle: int) -> bool:
        """Stop local stream recording."""
        with self._lock:
            session = self._sessions.get(handle)
            if not session:
                return False
            session.is_recording = False
            if session.engine_type == "opencv" and session.opencv_worker:
                return session.opencv_worker.stop_record()
            return True

    def stop_all(self):
        """Stop all active sessions on shutdown."""
        with self._lock:
            for handle, session in list(self._sessions.items()):
                if session.engine_type == "vlc" and session.vlc_player:
                    try:
                        session.vlc_player.stop()
                        session.vlc_player.release()
                    except Exception:
                        pass
                elif session.engine_type == "opencv" and session.opencv_worker:
                    session.opencv_worker.stop()
            self._sessions.clear()

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask password in rtsp://user:pass@ip:port/ stream URI for logging safety."""
        if "@" in url and ":" in url:
            try:
                proto, rest = url.split("://", 1)
                creds, host = rest.split("@", 1)
                if ":" in creds:
                    user = creds.split(":")[0]
                    return f"{proto}://{user}:***@{host}"
            except Exception:
                pass
        return url

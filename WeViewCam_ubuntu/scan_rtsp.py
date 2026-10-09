#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeViewCam RTSP / ONVIF 设备流地址深度探测与诊断工具.
专门针对小厂停车场道闸一体机、车牌抓拍相机以及无标准协议的 IP 设备。
通过多端口并发探测与全品牌特征库匹配，快速锁定设备的真实有效 RTSP 取流路径。
"""

import sys
import os
import socket
import time
import urllib.parse
from typing import List, Tuple, Optional

# 尝试载入 cv2
_HAS_CV2 = False
try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    pass


COMMON_RTSP_PORTS = [554, 8557, 50000, 8554, 10554, 5540]
COMMON_ONVIF_PORTS = [80, 8080, 8899, 8000, 5000, 8090, 8888]

# 车牌抓拍一体机与主流小厂 IPC 典型路径库
TYPICAL_PATHS = [
    # 臻识 (VisionZenith) / 车牌道闸一体机
    "/h264",
    "/h265",
    "/h264.sdp",
    "/live/ch0",
    "/live/ch00",
    "/live/main",
    "/live/sub",
    "/live/ch1",
    "/live",
    "/live.sdp",

    # 华夏智信 (Huaxia) 车牌相机
    "/video",
    "/subvideo",
    "/video1",
    "/video2",

    # 芊熠 (QianYi) / 蓝卡道闸车牌机
    "/live1.sdp",
    "/live2.sdp",

    # 文通 (Wintone) / 通用道闸抓拍机
    "/stream1",
    "/stream2",
    "/stream",

    # 大华 / 乐橙
    "/cam/realmonitor?channel=1&subtype=0",
    "/cam/realmonitor?channel=1&subtype=1",

    # 海康威视 / 萤石
    "/Streaming/Channels/101",
    "/Streaming/Channels/102",
    "/Streaming/Channels/1",
    "/Streaming/Channels/2",
    "/h264/ch1/main/av_stream",

    # 雄迈 / 巨峰 / 尚维 / 天视通
    "/ch0_0.264",
    "/ch0_1.264",
    "/ch0.264",
    "/ch0.sdp",
    "/ch0",
    "/ch1",

    # 简易/通用单通道路径
    "/main",
    "/sub",
    "/0",
    "/1",
    "/profile1",
    "/profile2",
    "/onvif1",
    "/onvif2",

    # 中维世纪 (Jovision)
    "/av0_0",
    "/av0_1",

    # 宇视 (Uniview)
    "/unicast/c1/s0/live",
    "/unicast/c1/s1/live",

    # 天地伟业 (Tiandy)
    "/channel1",
    "/channel2",

    # 标准 ONVIF
    "/onvif-media/media.amp",
    "/MediaInput/h264",
    "/media/video1",
]


def check_tcp_port(ip: str, port: int, timeout: float = 1.0) -> bool:
    """快速检测目标端口是否开放 (TCP 握手)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.close()
        return True
    except Exception:
        return False


def probe_rtsp_describe(ip: str, port: int, path: str, user: str = "", pwd: str = "", timeout: float = 1.5) -> Tuple[int, str]:
    """通过标准 RTSP DESCRIBE 命令直接探测流地址响应状态码."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        auth_header = ""
        if user:
            import base64
            token = base64.b64encode(f"{user}:{pwd}".encode('utf-8')).decode('utf-8')
            auth_header = f"Authorization: Basic {token}\r\n"

        req = (
            f"DESCRIBE rtsp://{ip}:{port}{path} RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"User-Agent: WeViewCam-Probe/1.0\r\n"
            f"{auth_header}"
            f"Accept: application/sdp\r\n\r\n"
        )
        s.sendall(req.encode('utf-8'))
        resp = s.recv(2048).decode('utf-8', errors='ignore')
        s.close()

        # 解析首行状态码
        if resp.startswith("RTSP/1.0") or resp.startswith("RTSP/"):
            parts = resp.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]), resp
        return 0, resp
    except Exception as e:
        return -1, str(e)


def probe_with_opencv(rtsp_url: str, timeout_sec: int = 2) -> bool:
    """使用 OpenCV 真实尝试拉流一帧以确认流是否完全可用."""
    if not _HAS_CV2:
        return False
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;tcp|stimeout;{timeout_sec * 1000000}|analyzeduration;1000000|probesize;1000000"
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return False
    ret, frame = cap.read()
    cap.release()
    return ret and frame is not None


def probe_onvif_ports(ip: str, user: str, pwd: str) -> Optional[str]:
    """探测 ONVIF 服务端口并尝试获取 StreamUri."""
    try:
        from onvif import ONVIFCamera
    except ImportError:
        return None

    for port in COMMON_ONVIF_PORTS:
        if not check_tcp_port(ip, port, timeout=0.8):
            continue
        try:
            cam = ONVIFCamera(ip, port, user, pwd)
            media = cam.create_media_service()
            profiles = media.GetProfiles()
            if profiles:
                token = profiles[0].token
                for mode in ['RTP-Unicast', 'RTP_Unicast']:
                    try:
                        res = media.GetStreamUri({'StreamSetup': {'Stream': mode, 'Transport': {'Protocol': 'RTSP'}}, 'ProfileToken': token})
                        if res and hasattr(res, 'Uri'):
                            return str(res.Uri)
                    except Exception:
                        pass
        except Exception:
            continue
    return None


def run_diagnostics(ip: str, user: str = "admin", pwd: str = "admin"):
    print("=" * 65)
    print(f"  WeViewCam 车牌抓拍一体机 / RTSP 流地址深度诊断工具")
    print(f"  目标设备 IP: {ip} | 登录账号: {user}")
    print("=" * 65)

    # 1. 扫描网络连通性与开放端口
    print("\n[阶段 1] 正在扫描常见网络端口...")
    open_rtsp_ports = []
    for p in COMMON_RTSP_PORTS:
        if check_tcp_port(ip, p):
            print(f"  ✓ RTSP 服务端口已开放: {p}")
            open_rtsp_ports.append(p)
        else:
            print(f"  · 端口 {p} 未响应")

    open_onvif_ports = []
    for p in COMMON_ONVIF_PORTS:
        if check_tcp_port(ip, p):
            print(f"  ✓ HTTP/ONVIF 端口已开放: {p}")
            open_onvif_ports.append(p)

    if not open_rtsp_ports and not open_onvif_ports:
        print(f"\n❌ 错误: 无法与目标设备 {ip} 的任何常见视频端口建立 TCP 连接！")
        print("请检查设备 IP 是否正确，网线及局域网通信是否正常。")
        return

    # 2. 尝试 ONVIF 自动发现
    print("\n[阶段 2] 正在尝试通过 ONVIF 协议自动发现媒体流...")
    onvif_url = probe_onvif_ports(ip, user, pwd)
    if onvif_url:
        print(f"  🎉 ONVIF 成功返回相机原生流地址: {onvif_url}")
        print(f"\n💡 建议在监控软件中直接使用此地址！")
        return

    # 3. 遍历特征库进行 RTSP DESCRIBE 探测
    print("\n[阶段 3] 正在对各端口遍历车牌抓拍机典型路径库...")
    ports_to_test = open_rtsp_ports if open_rtsp_ports else [554]
    found_urls = []

    safe_user = urllib.parse.quote(user, safe="")
    safe_pwd = urllib.parse.quote(pwd, safe="")
    cred = f"{safe_user}:{safe_pwd}@" if user else ""

    for port in ports_to_test:
        print(f"\n>> 正在测试端口 {port} ...")
        for path in TYPICAL_PATHS:
            test_url = f"rtsp://{cred}{ip}:{port}{path}"
            code, resp = probe_rtsp_describe(ip, port, path, user, pwd, timeout=1.0)

            # 200: 成功获取 SDP; 401: 路径存在但需要认证 (有效)
            if code in [200, 401]:
                print(f"  [发现疑似有效流] code={code} -> {test_url}")
                if _HAS_CV2:
                    if probe_with_opencv(test_url, timeout_sec=2):
                        print(f"    ⭐ [OpenCV 实际拉流成功！] 画面帧解析正常")
                        found_urls.append((test_url, True))
                    else:
                        print(f"    · OpenCV 尝试出图失败 (鉴权或格式差异)")
                        found_urls.append((test_url, False))
                else:
                    found_urls.append((test_url, False))
            elif code == 404:
                # 404 Stream Not Found
                continue
            elif code > 0:
                print(f"  · 路径 {path} 返回 HTTP/RTSP 状态码 {code}")

    print("\n" + "=" * 65)
    if found_urls:
        print("  🎉 诊断完成！共发现以下可用 RTSP 取流路径:")
        for idx, (u, verified) in enumerate(found_urls, 1):
            status = "【已验证可正常出图】" if verified else "【端口已响应】"
            print(f"  {idx}. {u}  {status}")
        print("\n请在 WeViewCam 设备的【自定义 RTSP 地址】中填入上述地址，或在软件中重新打开即可。")
    else:
        print("  ⚠️ 未能自动探测到匹配的流路径。")
        print("  请按以下步骤快速获取相机正确地址:")
        print("  1. 登录正常播放的 NVR 录像机管理后台 -> 进入【通道管理】查看该相机的取流配置与端口。")
        print(f"  2. 在浏览器直接打开 http://{ip} 登录该道闸相机的 Web 后台，在【视频设置】中查看 RTSP 路径。")
    print("=" * 65)


if __name__ == "__main__":
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.25.206"
    target_user = sys.argv[2] if len(sys.argv) > 2 else "admin"
    target_pwd = sys.argv[3] if len(sys.argv) > 3 else "admin"
    run_diagnostics(target_ip, target_user, target_pwd)

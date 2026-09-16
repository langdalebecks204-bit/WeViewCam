# -*- coding: utf-8 -*-
"""
Device Manager.
Handles device persistence, adapter lifecycle, and channel directory indexing.
"""

import json
import os
import uuid
from typing import Dict, List, Optional, Tuple, Any

from core.base_adapter import (
    BaseDeviceAdapter,
    DeviceInfo,
    ChannelInfo,
    ProtocolType
)
from core.logger import get_logger

logger = get_logger("DeviceManager")


class DeviceManager:
    """Central registry and controller for all registered surveillance devices."""

    def __init__(self, config_path: str = "config/devices.json"):
        self.config_path = config_path
        self._devices: Dict[str, DeviceInfo] = {}
        self._adapters: Dict[str, BaseDeviceAdapter] = {}
        self.load_devices()

    def create_adapter(self, device_info: DeviceInfo) -> BaseDeviceAdapter:
        """Factory method to instantiate the correct vendor adapter."""
        from adapters.factory import create_device_adapter
        return create_device_adapter(device_info)

    def add_device(self, device: DeviceInfo, auto_connect: bool = False) -> Tuple[bool, str]:
        """Add a new device and optionally connect."""
        if not device.device_id:
            device.device_id = str(uuid.uuid4())

        if device.device_id in self._devices:
            return False, f"设备 ID {device.device_id} 已存在"

        # Check for duplicate IP and Port
        for dev in self._devices.values():
            if dev.ip == device.ip and dev.port == device.port:
                logger.warning(f"设备 IP:端口 ({dev.ip}:{dev.port}) 与现有设备 '{dev.name}' 重复")

        self._devices[device.device_id] = device
        adapter = self.create_adapter(device)
        self._adapters[device.device_id] = adapter

        if auto_connect:
            if adapter.login():
                device.is_connected = True
                device.channels = adapter.get_channels()
                logger.info(f"设备 [{device.name}] 连接成功，检测到 {len(device.channels)} 个通道")
            else:
                logger.warning(f"设备 [{device.name}] 自动连接失败")

        self.save_devices()
        return True, device.device_id

    def update_device(self, device: DeviceInfo) -> bool:
        """Update existing device credentials or network parameters."""
        if device.device_id not in self._devices:
            return False

        # If already connected, logout first
        if device.device_id in self._adapters:
            try:
                self._adapters[device.device_id].logout()
            except Exception as e:
                logger.warning(f"更新设备前注销异常: {e}")

        self._devices[device.device_id] = device
        self._adapters[device.device_id] = self.create_adapter(device)
        self.save_devices()
        return True

    def remove_device(self, device_id: str) -> bool:
        """Disconnect and remove device."""
        if device_id in self._adapters:
            try:
                self._adapters[device_id].logout()
            except Exception as e:
                logger.warning(f"移除设备时注销异常: {e}")
            del self._adapters[device_id]

        if device_id in self._devices:
            del self._devices[device_id]
            self.save_devices()
            return True

        return False

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        return self._devices.get(device_id)

    def get_adapter(self, device_id: str) -> Optional[BaseDeviceAdapter]:
        if device_id not in self._adapters and device_id in self._devices:
            self._adapters[device_id] = self.create_adapter(self._devices[device_id])
        return self._adapters.get(device_id)

    def list_devices(self) -> List[DeviceInfo]:
        return list(self._devices.values())

    def connect_device(self, device_id: str) -> bool:
        """Explicitly connect / login to a device and fetch its channels."""
        dev = self._devices.get(device_id)
        if not dev:
            return False

        adapter = self.get_adapter(device_id)
        if not adapter:
            return False

        if adapter.is_connected:
            dev.is_connected = True
            return True

        success = adapter.login()
        if success:
            dev.is_connected = True
            dev.channels = adapter.get_channels()
            logger.info(f"设备 [{dev.name}] 连接成功，更新通道数: {len(dev.channels)}")
            self.save_devices()
            return True
        else:
            dev.is_connected = False
            logger.error(f"设备 [{dev.name}] 连接登录失败")
            return False

    def disconnect_device(self, device_id: str) -> bool:
        """Disconnect a device."""
        dev = self._devices.get(device_id)
        if not dev:
            return False

        adapter = self._adapters.get(device_id)
        if adapter:
            adapter.logout()

        dev.is_connected = False
        return True

    def test_connection(self, temp_device: DeviceInfo) -> Tuple[bool, str, List[ChannelInfo]]:
        """Test temporary connection parameters without saving."""
        adapter = self.create_adapter(temp_device)
        try:
            if adapter.login():
                channels = adapter.get_channels()
                adapter.logout()
                online_cnt = sum(1 for c in channels if c.is_online)
                offline_cnt = len(channels) - online_cnt
                return True, f"连接成功！获取到 {len(channels)} 个通道 ({online_cnt} 在线, {offline_cnt} 离线)", channels
            else:
                return False, "连接失败，请检查 IP、端口、用户名和密码", []
        except Exception as e:
            return False, f"连接发生异常: {str(e)}", []

    def save_devices(self):
        """Serialize devices to JSON config file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        data = []
        for dev in self._devices.values():
            dev_dict = {
                "device_id": dev.device_id,
                "name": dev.name,
                "ip": dev.ip,
                "port": dev.port,
                "username": dev.username,
                "password": dev.password,
                "protocol": dev.protocol.value if isinstance(dev.protocol, ProtocolType) else str(dev.protocol),
                "rtsp_port": dev.rtsp_port,
                "channels": [
                    {
                        "channel_no": ch.channel_no,
                        "name": ch.name,
                        "is_online": ch.is_online,
                        "is_ptz": ch.is_ptz,
                        "device_id": dev.device_id,
                        "extra": ch.extra
                    }
                    for ch in dev.channels
                ],
                "extra": dev.extra
            }
            data.append(dev_dict)

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存 {len(data)} 个设备配置到 {self.config_path}")
        except Exception as e:
            logger.error(f"保存设备配置失败: {e}")

    def load_devices(self):
        """Load devices from JSON config file."""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                channels = [
                    ChannelInfo(
                        channel_no=ch["channel_no"],
                        name=ch.get("name", f"Camera {ch['channel_no']}"),
                        is_online=ch.get("is_online", True),
                        is_ptz=ch.get("is_ptz", False),
                        device_id=item["device_id"],
                        extra=ch.get("extra", {})
                    )
                    for ch in item.get("channels", [])
                ]

                protocol_str = item.get("protocol", "hikvision")
                try:
                    protocol = ProtocolType(protocol_str)
                except ValueError:
                    protocol = ProtocolType.HIKVISION

                dev = DeviceInfo(
                    device_id=item["device_id"],
                    name=item.get("name", "Unnamed Device"),
                    ip=item.get("ip", "127.0.0.1"),
                    port=item.get("port", 8000),
                    username=item.get("username", "admin"),
                    password=item.get("password", ""),
                    protocol=protocol,
                    rtsp_port=item.get("rtsp_port", 554),
                    channels=channels,
                    is_connected=False,
                    extra=item.get("extra", {})
                )
                self._devices[dev.device_id] = dev

            logger.info(f"成功加载 {len(self._devices)} 个设备配置")
        except Exception as e:
            logger.error(f"加载设备配置失败: {e}")

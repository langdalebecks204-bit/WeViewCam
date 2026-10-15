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

    def _normalize_device_dict(self, raw: dict) -> dict:
        """Normalize raw dictionary to standard format handling camelCase and snake_case."""
        device_id = raw.get("device_id") or raw.get("deviceId") or str(uuid.uuid4())
        name = raw.get("name") or "未命名设备"
        ip = raw.get("ip") or "127.0.0.1"
        port = int(raw.get("port") or 8000)
        username = raw.get("username") or "admin"
        password = raw.get("password") or ""
        protocol_str = str(raw.get("protocol") or "hikvision")
        rtsp_port = int(raw.get("rtsp_port") or raw.get("rtspPort") or 554)
        extra = raw.get("extra") or {}

        channels_raw = raw.get("channels") or []
        normalized_channels = []
        for ch in channels_raw:
            ch_no = int(ch.get("channel_no") or ch.get("channelNo") or 1)
            ch_name = ch.get("name") or f"通道 {ch_no}"
            is_online = ch.get("is_online", ch.get("isOnline", True))
            is_ptz = ch.get("is_ptz", ch.get("isPtz", False))
            ch_dev_id = ch.get("device_id") or ch.get("deviceId") or device_id
            ch_extra = ch.get("extra") or {}
            normalized_channels.append(ChannelInfo(
                channel_no=ch_no,
                name=ch_name,
                is_online=bool(is_online),
                is_ptz=bool(is_ptz),
                device_id=ch_dev_id,
                extra=ch_extra
            ))

        try:
            protocol = ProtocolType(protocol_str.lower())
        except ValueError:
            protocol = ProtocolType.HIKVISION

        return {
            "device_id": device_id,
            "name": name,
            "ip": ip,
            "port": port,
            "username": username,
            "password": password,
            "protocol": protocol,
            "rtsp_port": rtsp_port,
            "channels": normalized_channels,
            "extra": extra
        }

    def export_devices(self, target_path: str) -> bool:
        """Export all configured devices to a JSON backup file."""
        try:
            dir_name = os.path.dirname(target_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
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
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已成功导出 {len(data)} 台设备配置到 {target_path}")
            return True
        except Exception as e:
            logger.error(f"导出设备配置失败: {e}")
            return False

    def import_devices(self, source_path: str, overwrite: bool = False) -> Tuple[bool, str, int]:
        """Import devices from a backup JSON file."""
        if not os.path.exists(source_path):
            return False, f"文件不存在: {source_path}", 0

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                content = json.load(f)

            if isinstance(content, dict):
                raw_list = content.get("devices", [])
            elif isinstance(content, list):
                raw_list = content
            else:
                return False, "无效的配置文件格式，顶层结构必须为列表或包含 devices 的字典", 0

            if not raw_list:
                return False, "配置文件中没有检测到任何设备数据", 0

            if overwrite:
                for dev_id in list(self._devices.keys()):
                    self.remove_device(dev_id)

            imported_count = 0
            for raw_dev in raw_list:
                norm = self._normalize_device_dict(raw_dev)
                dev_obj = DeviceInfo(
                    device_id=norm["device_id"],
                    name=norm["name"],
                    ip=norm["ip"],
                    port=norm["port"],
                    username=norm["username"],
                    password=norm["password"],
                    protocol=norm["protocol"],
                    rtsp_port=norm["rtsp_port"],
                    channels=norm["channels"],
                    is_connected=False,
                    extra=norm["extra"]
                )

                # Check if device already exists by ID or (IP, Port)
                existing_id = None
                if dev_obj.device_id in self._devices:
                    existing_id = dev_obj.device_id
                else:
                    for d_id, d in self._devices.items():
                        if d.ip == dev_obj.ip and d.port == dev_obj.port:
                            existing_id = d_id
                            break

                if existing_id:
                    dev_obj.device_id = existing_id
                    self.update_device(dev_obj)
                else:
                    self.add_device(dev_obj)

                imported_count += 1

            self.save_devices()
            return True, f"成功导入 {imported_count} 台设备配置", imported_count
        except Exception as e:
            logger.error(f"导入设备配置异常: {e}")
            return False, f"导入失败: {str(e)}", 0

    def load_devices(self):
        """Load devices from JSON config file."""
        if not os.path.exists(self.config_path) or os.path.getsize(self.config_path) == 0:
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                data = data.get("devices", [])
            elif not isinstance(data, list):
                data = []

            for item in data:
                norm = self._normalize_device_dict(item)
                dev = DeviceInfo(
                    device_id=norm["device_id"],
                    name=norm["name"],
                    ip=norm["ip"],
                    port=norm["port"],
                    username=norm["username"],
                    password=norm["password"],
                    protocol=norm["protocol"],
                    rtsp_port=norm["rtsp_port"],
                    channels=norm["channels"],
                    is_connected=False,
                    extra=norm["extra"]
                )
                self._devices[dev.device_id] = dev

            logger.info(f"成功加载 {len(self._devices)} 个设备配置")
        except Exception as e:
            logger.error(f"加载设备配置失败: {e}")

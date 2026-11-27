# -*- coding: utf-8 -*-
"""
Device Manager.
Handles device persistence, adapter lifecycle, and channel directory indexing.
"""

import json
import os
import sys
import uuid
from typing import Callable, Dict, List, Optional, Tuple, Any

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

    def __init__(self, config_path: str = "config/devices.json", auto_load: bool = True):
        if not os.path.isabs(config_path):
            if getattr(sys, "frozen", False):
                base_app = os.path.dirname(sys.executable)
            else:
                base_app = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_app, config_path)
        self.config_path = config_path
        self._devices: Dict[str, DeviceInfo] = {}
        self._adapters: Dict[str, BaseDeviceAdapter] = {}
        self._before_disconnect_callbacks: List[Callable[[str], None]] = []
        if auto_load:
            self.load_devices()

    def register_before_disconnect_callback(self, callback: Callable[[str], None]) -> None:
        """Register a hook invoked before a device adapter logs out (e.g. to stop active streams)."""
        if callback not in self._before_disconnect_callbacks:
            self._before_disconnect_callbacks.append(callback)

    def _notify_before_disconnect(self, device_id: str) -> None:
        for cb in list(self._before_disconnect_callbacks):
            try:
                cb(device_id)
            except Exception as e:
                logger.warning(f"before_disconnect 回调异常 ({device_id}): {e}")

    def create_adapter(self, device_info: DeviceInfo) -> BaseDeviceAdapter:
        """Factory method to instantiate the correct vendor adapter."""
        from adapters.factory import create_device_adapter
        return create_device_adapter(device_info)

    @staticmethod
    def _is_custom_name(name: Optional[str]) -> bool:
        """Return True if channel name is user-customized rather than default hardware placeholder."""
        if not name or not name.strip():
            return False
        nm = name.strip()
        default_prefixes = ("通道 ", "通道", "IP通道", "Camera", "Default Camera", "Ch ", "CH", "ch")
        for prefix in default_prefixes:
            if nm.startswith(prefix):
                rest = nm[len(prefix):].strip()
                if rest.isdigit() or rest.replace("0", "").isdigit() or not rest:
                    return False
        return True

    @classmethod
    def _deduplicate_channels(cls, channels: List[ChannelInfo]) -> List[ChannelInfo]:
        """
        Deduplicate channels within a device.
        Detects if both physical offset channels (e.g. 33..64) and sequential alias channels (1..32)
        exist concurrently due to past imports. Merges user custom names into physical channels and
        removes the redundant sequential alias channels.
        Also removes any duplicate channel_no entries (keeps the one with a customized name).
        """
        if not channels:
            return []

        # 1. First remove any identical channel_no duplicates
        by_no: Dict[int, ChannelInfo] = {}
        for ch in channels:
            if ch.channel_no not in by_no:
                by_no[ch.channel_no] = ch
            else:
                existing = by_no[ch.channel_no]
                # If the new one has a customized name, prioritize it
                if cls._is_custom_name(ch.name):
                    existing.name = ch.name
                existing.is_enabled = getattr(ch, "is_enabled", existing.is_enabled)
                existing.is_ptz = getattr(ch, "is_ptz", existing.is_ptz)

        unique_channels = list(by_no.values())

        # 2. Check if we have physical offset channels (>= 32) alongside sequential aliases (1..N)
        high_channels = [c for c in unique_channels if c.channel_no >= 32]
        low_channels = [c for c in unique_channels if c.channel_no < 32]

        if high_channels and low_channels:
            min_high = min(c.channel_no for c in high_channels)
            high_map = {c.channel_no: c for c in high_channels}
            cleaned_low = []
            for low_ch in low_channels:
                alias_physical_no = min_high + (low_ch.channel_no - 1)
                if alias_physical_no in high_map:
                    # It's an alias duplicate of an existing physical channel!
                    target_ch = high_map[alias_physical_no]
                    if cls._is_custom_name(low_ch.name):
                        target_ch.name = low_ch.name
                    target_ch.is_enabled = getattr(low_ch, "is_enabled", target_ch.is_enabled)
                    target_ch.is_ptz = getattr(low_ch, "is_ptz", target_ch.is_ptz)
                else:
                    cleaned_low.append(low_ch)
            unique_channels = high_channels + cleaned_low

        unique_channels.sort(key=lambda c: c.channel_no)
        return unique_channels

    @classmethod
    def _merge_channel_lists(
        cls,
        existing_channels: List[ChannelInfo],
        incoming_channels: List[ChannelInfo]
    ) -> List[ChannelInfo]:
        """
        Merge incoming channels into existing channels without duplicating.
        Handles:
        1. Exact channel_no matching (updates name, enabled, ptz).
        2. Offset alias matching (sequential 1..N vs physical 33..33+N-1).
        3. Truly new channels added.
        4. Cleans up any existing duplicate channels.
        """
        if not incoming_channels:
            return cls._deduplicate_channels(existing_channels)
        if not existing_channels:
            return cls._deduplicate_channels(incoming_channels)

        base_channels = cls._deduplicate_channels(existing_channels)
        inc_channels = cls._deduplicate_channels(incoming_channels)

        min_base = min(c.channel_no for c in base_channels)
        max_base = max(c.channel_no for c in base_channels)
        min_inc = min(c.channel_no for c in inc_channels)
        max_inc = max(c.channel_no for c in inc_channels)

        # Case A: Existing has physical channels (>=32), incoming has sequential (1..N)
        if min_base >= 32 and max_inc < min_base:
            base_map = {c.channel_no: c for c in base_channels}
            for inc_ch in inc_channels:
                mapped_no = min_base + (inc_ch.channel_no - 1)
                if mapped_no in base_map:
                    target = base_map[mapped_no]
                    if cls._is_custom_name(inc_ch.name):
                        target.name = inc_ch.name
                    elif not cls._is_custom_name(target.name) and inc_ch.name:
                        target.name = inc_ch.name
                    target.is_enabled = cls._merge_enabled_state(target, inc_ch)
                    target.is_ptz = getattr(inc_ch, "is_ptz", target.is_ptz)
                    target.is_online = getattr(inc_ch, "is_online", target.is_online)
                    if getattr(inc_ch, "extra", None):
                        target.extra.update(inc_ch.extra)
                else:
                    inc_ch.channel_no = mapped_no
                    base_map[mapped_no] = inc_ch
            result = list(base_map.values())

        # Case B: Incoming has physical channels (>=32), existing has sequential (1..N)
        elif min_inc >= 32 and max_base < min_inc:
            inc_map = {c.channel_no: c for c in inc_channels}
            for base_ch in base_channels:
                mapped_no = min_inc + (base_ch.channel_no - 1)
                if mapped_no in inc_map:
                    target = inc_map[mapped_no]
                    if cls._is_custom_name(base_ch.name):
                        target.name = base_ch.name
                    elif not cls._is_custom_name(target.name) and base_ch.name:
                        target.name = base_ch.name
                    target.is_enabled = cls._merge_enabled_state(base_ch, target)
                    target.is_ptz = getattr(base_ch, "is_ptz", target.is_ptz)
            result = list(inc_map.values())

        # Case C: Same numbering scheme (exact channel_no matching)
        else:
            base_map = {c.channel_no: c for c in base_channels}
            for inc_ch in inc_channels:
                if inc_ch.channel_no in base_map:
                    target = base_map[inc_ch.channel_no]
                    if cls._is_custom_name(inc_ch.name):
                        target.name = inc_ch.name
                    elif not cls._is_custom_name(target.name) and inc_ch.name:
                        target.name = inc_ch.name
                    target.is_enabled = cls._merge_enabled_state(target, inc_ch)
                    target.is_ptz = getattr(inc_ch, "is_ptz", target.is_ptz)
                    target.is_online = getattr(inc_ch, "is_online", target.is_online)
                    if getattr(inc_ch, "extra", None):
                        target.extra.update(inc_ch.extra)
                else:
                    base_map[inc_ch.channel_no] = inc_ch
            result = list(base_map.values())

        return cls._deduplicate_channels(result)

    @staticmethod
    def _merge_enabled_state(existing_ch: ChannelInfo, incoming_ch: ChannelInfo) -> bool:
        """Preserve user-disabled channels, but auto-enable newly attached/online NVR channels."""
        if getattr(existing_ch, "is_enabled", True):
            return getattr(incoming_ch, "is_enabled", True)
        was_inactive = (not getattr(existing_ch, "is_online", True)) or bool(
            (getattr(existing_ch, "extra", None) or {}).get("unattached", False)
        )
        now_active = (
            getattr(incoming_ch, "is_enabled", True)
            and getattr(incoming_ch, "is_online", True)
            and not bool((getattr(incoming_ch, "extra", None) or {}).get("unattached", False))
        )
        return True if (was_inactive and now_active) else False

    @classmethod
    def _merge_channels_preserving_custom(
        cls,
        existing_channels: List[ChannelInfo],
        probed_channels: List[ChannelInfo]
    ) -> List[ChannelInfo]:
        """Backward-compatible entry point for adapter probed channel merging."""
        return cls._merge_channel_lists(existing_channels, probed_channels)

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
                probed = adapter.get_channels()
                device.channels = self._merge_channels_preserving_custom(device.channels, probed)
                logger.info(f"设备 [{device.name}] 连接成功，检测到 {len(device.channels)} 个通道")
            else:
                logger.warning(f"设备 [{device.name}] 自动连接失败")

        self.save_devices()
        return True, device.device_id

    def update_device(self, device: DeviceInfo) -> bool:
        """Update existing device credentials or network parameters."""
        if device.device_id not in self._devices:
            return False

        # If already connected, stop active streams and logout first
        if device.device_id in self._adapters:
            self._notify_before_disconnect(device.device_id)
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
            self._notify_before_disconnect(device_id)
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

    def connect_device(self, device_id: str, force_refresh: bool = False) -> bool:
        """Explicitly connect / login to a device and fetch its channels."""
        dev = self._devices.get(device_id)
        if not dev:
            return False

        adapter = self.get_adapter(device_id)
        if not adapter:
            return False

        if adapter.is_connected and not force_refresh and dev.channels:
            dev.is_connected = True
            return True

        if force_refresh and adapter.is_connected:
            self._notify_before_disconnect(device_id)
            try:
                adapter.logout()
            except Exception as e:
                logger.warning(f"强制重连前注销异常 ({device_id}): {e}")

        if not adapter.is_connected:
            success = adapter.login()
        else:
            success = True

        if success:
            dev.is_connected = True
            probed = adapter.get_channels()
            dev.channels = self._merge_channels_preserving_custom(dev.channels, probed)
            logger.info(f"设备 [{dev.name}] 连接成功，更新通道数: {len(dev.channels)}")
            self.save_devices()
            return True
        else:
            dev.is_connected = False
            logger.error(f"设备 [{dev.name}] 连接登录失败")
            return False

    def refresh_device_status(self, device_id: str) -> bool:
        """Probe and refresh online status for a specific device and its channels."""
        dev = self._devices.get(device_id)
        if not dev:
            return False
        adapter = self.get_adapter(device_id)
        if not adapter:
            return False
        try:
            if not adapter.is_connected:
                login_ok = adapter.login()
                if login_ok:
                    dev.is_connected = True
                    probed = adapter.get_channels()
                    if probed:
                        dev.channels = self._merge_channels_preserving_custom(dev.channels, probed)
                    self.save_devices()
                    return True
                else:
                    dev.is_connected = False
                    for ch in dev.channels:
                        ch.is_online = False
                    self.save_devices()
                    return False
            else:
                probed = adapter.get_channels()
                if probed:
                    dev.channels = self._merge_channels_preserving_custom(dev.channels, probed)
                dev.is_connected = True
                self.save_devices()
                return True
        except Exception as e:
            logger.warning(f"刷新设备 [{dev.name}] 状态异常: {e}")
            dev.is_connected = False
            return False

    def refresh_all_devices_status(self, max_workers: int = 4) -> Dict[str, bool]:
        """Probe and refresh online status for all configured devices concurrently."""
        import concurrent.futures
        dev_ids = list(self._devices.keys())
        if not dev_ids:
            return {}
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(dev_ids))) as executor:
            future_to_id = {executor.submit(self.refresh_device_status, dev_id): dev_id for dev_id in dev_ids}
            for future in concurrent.futures.as_completed(future_to_id):
                d_id = future_to_id[future]
                try:
                    results[d_id] = future.result()
                except Exception as ex:
                    logger.warning(f"刷新设备 {d_id} 状态失败: {ex}")
                    results[d_id] = False
        return results

    def update_channel_name(self, device_id: str, channel_no: int, new_name: str) -> bool:
        """Update a specific channel's display name."""
        dev = self._devices.get(device_id)
        if not dev:
            return False
        for ch in dev.channels:
            if ch.channel_no == channel_no:
                ch.name = new_name.strip()
                self.save_devices()
                return True
        return False

    def set_channel_enabled(self, device_id: str, channel_no: int, enabled: bool) -> bool:
        """Toggle a specific channel's enabled state."""
        dev = self._devices.get(device_id)
        if not dev:
            return False
        for ch in dev.channels:
            if ch.channel_no == channel_no:
                ch.is_enabled = enabled
                self.save_devices()
                return True
        return False

    def batch_set_channels_enabled(self, device_id: str, enabled: bool) -> bool:
        """Batch set all channels of a device to enabled or disabled."""
        dev = self._devices.get(device_id)
        if not dev:
            return False
        for ch in dev.channels:
            ch.is_enabled = enabled
        self.save_devices()
        return True

    def add_custom_channel(self, device_id: str, channel_no: int, name: str, is_ptz: bool = False) -> bool:
        """Add or update a custom channel for a device."""
        dev = self._devices.get(device_id)
        if not dev:
            return False
        for ch in dev.channels:
            if ch.channel_no == channel_no:
                ch.name = name.strip() or f"通道 {channel_no}"
                ch.is_enabled = True
                ch.is_ptz = is_ptz
                self.save_devices()
                return True

        new_ch = ChannelInfo(
            channel_no=channel_no,
            name=name.strip() or f"通道 {channel_no}",
            is_online=True,
            is_ptz=is_ptz,
            device_id=device_id,
            is_enabled=True
        )
        dev.channels.append(new_ch)
        dev.channels.sort(key=lambda c: c.channel_no)
        self.save_devices()
        return True

    def delete_channel(self, device_id: str, channel_no: int) -> bool:
        """Delete a channel from device channels list."""
        dev = self._devices.get(device_id)
        if not dev:
            return False
        dev.channels = [c for c in dev.channels if c.channel_no != channel_no]
        self.save_devices()
        return True

    def disconnect_device(self, device_id: str) -> bool:
        """Disconnect a device."""
        dev = self._devices.get(device_id)
        if not dev:
            return False

        self._notify_before_disconnect(device_id)
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
                try:
                    channels = adapter.get_channels()
                except Exception as ce:
                    logger.exception(f"登录成功但获取通道列表时发生异常: {ce}")
                    channels = []
                finally:
                    adapter.logout()

                if channels:
                    online_cnt = sum(1 for c in channels if c.is_online)
                    offline_cnt = len(channels) - online_cnt
                    return True, f"连接成功！获取到 {len(channels)} 个通道 ({online_cnt} 在线, {offline_cnt} 离线)", channels
                else:
                    return True, "连接成功！但未能枚举到通道（可能为特殊存储设备或通道未就绪）", []
            else:
                return False, "连接失败，请检查 IP、端口、用户名和密码", []
        except Exception as e:
            logger.exception(f"测试连接时发生未预期异常: {e}")
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
                        "is_enabled": getattr(ch, "is_enabled", True),
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
            is_enabled = ch.get("is_enabled", ch.get("isEnabled", ch.get("enabled", True)))
            ch_dev_id = ch.get("device_id") or ch.get("deviceId") or device_id
            ch_extra = ch.get("extra") or {}
            normalized_channels.append(ChannelInfo(
                channel_no=ch_no,
                name=ch_name,
                is_online=bool(is_online),
                is_ptz=bool(is_ptz),
                device_id=ch_dev_id,
                is_enabled=bool(is_enabled),
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

    def get_devices_export_data(self, device_ids: Optional[List[str]] = None) -> List[dict]:
        """Convert specified (or all) devices into JSON-serializable backup dictionaries."""
        data = []
        target_ids = set(device_ids) if device_ids is not None else None
        for dev in self._devices.values():
            if target_ids is not None and dev.device_id not in target_ids:
                continue
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
                        "is_enabled": getattr(ch, "is_enabled", True),
                        "device_id": dev.device_id,
                        "extra": ch.extra
                    }
                    for ch in dev.channels
                ],
                "extra": dev.extra
            }
            data.append(dev_dict)
        return data

    def export_devices(self, target_path: str, device_ids: Optional[List[str]] = None) -> bool:
        """Export specified (or all) configured devices to JSON, CSV, or Excel file."""
        try:
            dir_name = os.path.dirname(target_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            data = self.get_devices_export_data(device_ids=device_ids)

            ext = os.path.splitext(target_path)[1].lower()
            if ext in (".xlsx", ".xlsm"):
                from core.device_excel_helper import DeviceExcelHelper
                ok = DeviceExcelHelper.export_devices_to_excel(target_path, data)
                if ok:
                    logger.info(f"已成功导出 {len(data)} 台设备配置到 Excel: {target_path}")
                return ok
            elif ext == ".csv":
                from core.device_excel_helper import DeviceExcelHelper
                ok = DeviceExcelHelper.export_devices_to_csv(target_path, data)
                if ok:
                    logger.info(f"已成功导出 {len(data)} 台设备配置到 CSV: {target_path}")
                return ok
            else:
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"已成功导出 {len(data)} 台设备配置到 JSON: {target_path}")
                return True
        except Exception as e:
            logger.error(f"导出设备配置失败: {e}")
            return False

    def import_devices(self, source_path: str, overwrite: bool = False) -> Tuple[bool, str, int]:
        """Import devices from a backup JSON, Excel (.xlsx), or CSV file with robust checks."""
        if not os.path.exists(source_path):
            return False, f"文件不存在: {source_path}", 0

        ext = os.path.splitext(source_path)[1].lower()
        if ext in (".xlsx", ".xlsm", ".csv"):
            try:
                from core.device_excel_helper import DeviceExcelHelper
                raw_list = DeviceExcelHelper.parse_table_file(source_path)
                return self.import_devices_from_list(raw_list, overwrite=overwrite)
            except Exception as e:
                logger.error(f"解析表格文件 ({source_path}) 失败: {e}")
                return False, f"解析表格失败: {str(e)}", 0

        try:
            file_size = os.path.getsize(source_path)
            if file_size == 0:
                return False, (
                    "选择的文件大小为 0 字节 (空文件)。\n\n"
                    "【排查提示】：\n"
                    "1. 若此文件通过微信/QQ等传输，请先在聊天窗口点击该文件完成【下载】或【另存为】到电脑（未下载时本地仅为 0 字节占位符）。\n"
                    "2. 若通过 USB 传输，请确认文件在电脑上已拷贝完整。\n"
                    "3. 您也可以在 Android 端选择【复制配置到剪贴板】，并在电脑端使用【从剪贴板导入】。"
                ), 0

            with open(source_path, "rb") as f:
                raw_bytes = f.read()

            return self.import_devices_from_bytes(raw_bytes, overwrite=overwrite)
        except Exception as e:
            logger.error(f"导入设备配置文件读取异常: {e}")
            return False, f"读取备份文件失败: {str(e)}", 0

    def import_devices_from_bytes(self, raw_bytes: bytes, overwrite: bool = False) -> Tuple[bool, str, int]:
        """Import devices from raw bytes with auto encoding detection (UTF-8, UTF-8-BOM, UTF-16)."""
        if not raw_bytes or not raw_bytes.strip():
            return False, "备份文件内容为空 (0 字节)，未读取到有效数据", 0

        # Auto-detect UTF-16 vs UTF-8 BOM vs UTF-8
        if raw_bytes.startswith(b"\xff\xfe") or raw_bytes.startswith(b"\xfe\xff"):
            text = raw_bytes.decode("utf-16", errors="replace")
        else:
            text = raw_bytes.decode("utf-8-sig", errors="replace")

        return self.import_devices_from_text(text, overwrite=overwrite)

    def import_devices_from_text(self, text: str, overwrite: bool = False) -> Tuple[bool, str, int]:
        """Import devices directly from JSON string."""
        if not text:
            return False, "传入的配置文本为空", 0

        clean_text = text.strip().lstrip("\ufeff\x00 \t\r\n")
        if not clean_text:
            return False, "配置文本去除空字符后为空", 0

        try:
            content = json.loads(clean_text)
        except json.JSONDecodeError as jde:
            preview = clean_text[:100] if len(clean_text) > 100 else clean_text
            logger.error(f"JSON 解析失败 ({jde.msg}, line {jde.lineno}, col {jde.colno}): {preview!r}")
            return False, (
                f"备份内容不是合法的 JSON 格式 ({jde.msg}，第{jde.lineno}行第{jde.colno}列)。\n\n"
                f"文本前缀: {preview!r}\n"
                f"请核对文件内容是否完整。"
            ), 0

        if isinstance(content, dict):
            raw_list = content.get("devices", [])
        elif isinstance(content, list):
            raw_list = content
        else:
            return False, "无效的配置文件格式，顶层结构必须为列表或包含 devices 的字典", 0

        return self.import_devices_from_list(raw_list, overwrite=overwrite)

    def import_devices_from_list(self, raw_list: List[Dict[str, Any]], overwrite: bool = False) -> Tuple[bool, str, int]:
        """Core worker to import devices from a standardized list of dicts."""
        if not raw_list:
            return False, "导入数据中没有检测到任何设备", 0

        try:
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
                    channels=self._deduplicate_channels(norm["channels"]),
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
                    existing_dev = self._devices[existing_id]
                    if not dev_obj.channels and existing_dev.channels:
                        dev_obj.channels = existing_dev.channels
                    elif dev_obj.channels and existing_dev.channels:
                        # Smart merge channels without duplicate sequential/physical aliases
                        dev_obj.channels = self._merge_channel_lists(existing_dev.channels, dev_obj.channels)
                    elif dev_obj.channels and not existing_dev.channels:
                        dev_obj.channels = self._deduplicate_channels(dev_obj.channels)
                    self.update_device(dev_obj)
                else:
                    dev_obj.channels = self._deduplicate_channels(dev_obj.channels)
                    self.add_device(dev_obj)

                imported_count += 1

            self.save_devices()
            return True, f"成功导入 {imported_count} 台设备配置", imported_count
        except Exception as e:
            logger.error(f"导入设备配置异常: {e}")
            return False, f"导入处理失败: {str(e)}", 0

    def load_devices(self):
        """Load devices from JSON config file."""
        if not os.path.exists(self.config_path) or os.path.getsize(self.config_path) == 0:
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                bundled_cfg = os.path.join(sys._MEIPASS, "config", "devices.json")
                if os.path.exists(bundled_cfg) and os.path.getsize(bundled_cfg) > 0:
                    try:
                        import shutil
                        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                        shutil.copy2(bundled_cfg, self.config_path)
                    except Exception as e:
                        logger.debug(f"复制打包内初始设备配置失败: {e}")

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
                    channels=self._deduplicate_channels(norm["channels"]),
                    is_connected=False,
                    extra=norm["extra"]
                )
                self._devices[dev.device_id] = dev

            logger.info(f"成功加载 {len(self._devices)} 个设备配置")
        except Exception as e:
            logger.error(f"加载设备配置失败: {e}")

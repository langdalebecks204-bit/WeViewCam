# -*- coding: utf-8 -*-
"""
Adapter Factory.
Creates vendor-specific device adapters according to device protocol configuration.
"""

from core.base_adapter import BaseDeviceAdapter, DeviceInfo, ProtocolType
from adapters.hikvision.adapter import HikvisionAdapter
from adapters.dahua.adapter import DahuaAdapter
from adapters.onvif.adapter import OnvifAdapter
from core.logger import get_logger

logger = get_logger("AdapterFactory")


def create_device_adapter(device_info: DeviceInfo) -> BaseDeviceAdapter:
    """Instantiate and return the appropriate adapter for a given device."""
    proto = device_info.protocol

    if proto == ProtocolType.HIKVISION or proto == "hikvision":
        return HikvisionAdapter(device_info)
    elif proto == ProtocolType.DAHUA or proto == "dahua":
        return DahuaAdapter(device_info)
    elif proto == ProtocolType.ONVIF or proto == "onvif" or proto == ProtocolType.CUSTOM_RTSP or proto == "custom_rtsp":
        return OnvifAdapter(device_info)
    else:
        logger.warning(f"未知或未指定协议 '{proto}', 默认使用海康威视适配器")
        return HikvisionAdapter(device_info)

package com.weviewcam.client.core.adapter;

import com.weviewcam.client.adapters.hikvision.HikvisionAdapter;
import com.weviewcam.client.adapters.mock.MockDeviceAdapter;
import com.weviewcam.client.adapters.onvif.OnvifAdapter;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.ProtocolType;

public class DeviceAdapterFactory {
    private static final String MODULE = "AdapterFactory";

    public static BaseDeviceAdapter createAdapter(DeviceInfo device) {
        if (device == null) {
            return new MockDeviceAdapter(new DeviceInfo());
        }

        ProtocolType proto = device.getProtocol();
        if (proto == null) proto = ProtocolType.HIKVISION;

        switch (proto) {
            case HIKVISION:
                try {
                    return new HikvisionAdapter(device);
                } catch (Throwable t) {
                    AppLogger.w(MODULE, "创建海康官方SDK适配器异常，降级启用仿真适配器: " + t.getMessage());
                    return new MockDeviceAdapter(device);
                }
            case ONVIF:
            case CUSTOM_RTSP:
                return new OnvifAdapter(device);
            case DAHUA:
            default:
                return new MockDeviceAdapter(device);
        }
    }
}

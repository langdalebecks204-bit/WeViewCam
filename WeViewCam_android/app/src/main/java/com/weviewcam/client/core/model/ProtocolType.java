package com.weviewcam.client.core.model;

public enum ProtocolType {
    HIKVISION("hikvision", "海康威视 SDK"),
    ONVIF("onvif", "ONVIF 国际标准"),
    DAHUA("dahua", "大华协议 (保留)"),
    CUSTOM_RTSP("custom_rtsp", "自定义 RTSP");

    private final String value;
    private final String displayName;

    ProtocolType(String value, String displayName) {
        this.value = value;
        this.displayName = displayName;
    }

    public String getValue() {
        return value;
    }

    public String getDisplayName() {
        return displayName;
    }

    public static ProtocolType fromString(String text) {
        for (ProtocolType b : ProtocolType.values()) {
            if (b.value.equalsIgnoreCase(text)) {
                return b;
            }
        }
        return HIKVISION;
    }
}

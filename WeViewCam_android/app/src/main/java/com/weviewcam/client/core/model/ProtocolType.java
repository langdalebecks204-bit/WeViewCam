package com.weviewcam.client.core.model;

import com.google.gson.annotations.SerializedName;

public enum ProtocolType {
    @SerializedName(value = "hikvision", alternate = {"HIKVISION"})
    HIKVISION("hikvision", "海康威视 SDK"),

    @SerializedName(value = "onvif", alternate = {"ONVIF"})
    ONVIF("onvif", "ONVIF 国际标准"),

    @SerializedName(value = "dahua", alternate = {"DAHUA"})
    DAHUA("dahua", "大华协议 (保留)"),

    @SerializedName(value = "custom_rtsp", alternate = {"CUSTOM_RTSP"})
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

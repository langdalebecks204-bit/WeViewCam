package com.weviewcam.client.core.model;

import com.google.gson.annotations.SerializedName;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

public class ChannelInfo implements Serializable {
    @SerializedName(value = "channel_no", alternate = {"channelNo"})
    private int channelNo;

    @SerializedName("name")
    private String name;

    @SerializedName(value = "is_online", alternate = {"isOnline"})
    private boolean isOnline;

    @SerializedName(value = "is_ptz", alternate = {"isPtz"})
    private boolean isPtz;

    @SerializedName(value = "device_id", alternate = {"deviceId"})
    private String deviceId;

    @SerializedName(value = "is_enabled", alternate = {"isEnabled", "enabled"})
    private boolean enabled = true;

    @SerializedName("extra")
    private Map<String, Object> extra = new HashMap<>();

    public ChannelInfo() {
        this.enabled = true;
    }

    public ChannelInfo(int channelNo, String name, boolean isOnline, boolean isPtz, String deviceId) {
        this(channelNo, name, isOnline, isPtz, deviceId, true);
    }

    public ChannelInfo(int channelNo, String name, boolean isOnline, boolean isPtz, String deviceId, boolean enabled) {
        this.channelNo = channelNo;
        this.name = name;
        this.isOnline = isOnline;
        this.isPtz = isPtz;
        this.deviceId = deviceId;
        this.enabled = enabled;
    }

    public int getChannelNo() {
        return channelNo;
    }

    public void setChannelNo(int channelNo) {
        this.channelNo = channelNo;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public boolean isOnline() {
        return isOnline;
    }

    public void setOnline(boolean online) {
        isOnline = online;
    }

    public boolean isPtz() {
        return isPtz;
    }

    public void setPtz(boolean ptz) {
        isPtz = ptz;
    }

    public String getDeviceId() {
        return deviceId;
    }

    public void setDeviceId(String deviceId) {
        this.deviceId = deviceId;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public Map<String, Object> getExtra() {
        return extra;
    }

    public void setExtra(Map<String, Object> extra) {
        this.extra = extra;
    }

    @Override
    public String toString() {
        return name != null ? name : ("Channel " + channelNo);
    }
}

package com.weviewcam.client.core.model;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

public class ChannelInfo implements Serializable {
    private int channelNo;
    private String name;
    private boolean isOnline;
    private boolean isPtz;
    private String deviceId;
    private Map<String, Object> extra = new HashMap<>();

    public ChannelInfo() {
    }

    public ChannelInfo(int channelNo, String name, boolean isOnline, boolean isPtz, String deviceId) {
        this.channelNo = channelNo;
        this.name = name;
        this.isOnline = isOnline;
        this.isPtz = isPtz;
        this.deviceId = deviceId;
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

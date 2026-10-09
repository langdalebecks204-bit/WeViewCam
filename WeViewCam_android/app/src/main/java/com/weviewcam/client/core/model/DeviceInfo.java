package com.weviewcam.client.core.model;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public class DeviceInfo implements Serializable {
    private String deviceId;
    private String name;
    private String ip;
    private int port;
    private String username;
    private String password;
    private ProtocolType protocol;
    private int rtspPort;
    private List<ChannelInfo> channels;
    private boolean isConnected;
    private Map<String, Object> extra;

    public DeviceInfo() {
        this.deviceId = UUID.randomUUID().toString();
        this.port = 8000;
        this.username = "admin";
        this.password = "";
        this.protocol = ProtocolType.HIKVISION;
        this.rtspPort = 554;
        this.channels = new ArrayList<>();
        this.isConnected = false;
        this.extra = new HashMap<>();
    }

    public DeviceInfo(String deviceId, String name, String ip, int port, String username, String password, ProtocolType protocol) {
        this.deviceId = deviceId != null ? deviceId : UUID.randomUUID().toString();
        this.name = name;
        this.ip = ip;
        this.port = port;
        this.username = username;
        this.password = password;
        this.protocol = protocol != null ? protocol : ProtocolType.HIKVISION;
        this.rtspPort = 554;
        this.channels = new ArrayList<>();
        this.isConnected = false;
        this.extra = new HashMap<>();
    }

    public String getDeviceId() {
        return deviceId;
    }

    public void setDeviceId(String deviceId) {
        this.deviceId = deviceId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getIp() {
        return ip;
    }

    public void setIp(String ip) {
        this.ip = ip;
    }

    public int getPort() {
        return port;
    }

    public void setPort(int port) {
        this.port = port;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public ProtocolType getProtocol() {
        return protocol;
    }

    public void setProtocol(ProtocolType protocol) {
        this.protocol = protocol;
    }

    public int getRtspPort() {
        return rtspPort;
    }

    public void setRtspPort(int rtspPort) {
        this.rtspPort = rtspPort;
    }

    public List<ChannelInfo> getChannels() {
        if (channels == null) {
            channels = new ArrayList<>();
        }
        return channels;
    }

    public void setChannels(List<ChannelInfo> channels) {
        this.channels = channels;
    }

    public boolean isConnected() {
        return isConnected;
    }

    public void setConnected(boolean connected) {
        isConnected = connected;
    }

    public Map<String, Object> getExtra() {
        if (extra == null) {
            extra = new HashMap<>();
        }
        return extra;
    }

    public void setExtra(Map<String, Object> extra) {
        this.extra = extra;
    }

    @Override
    public String toString() {
        return name != null ? name : (ip + ":" + port);
    }
}

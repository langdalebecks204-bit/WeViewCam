package com.weviewcam.client.adapters.onvif;

import android.view.Surface;

import com.weviewcam.client.adapters.mock.MockDeviceAdapter;
import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PTZCommand;
import com.weviewcam.client.core.model.PlaybackCommand;
import com.weviewcam.client.core.model.RecordSegment;

import java.util.Date;
import java.util.List;

public class OnvifAdapter extends BaseDeviceAdapter {
    private static final String MODULE = "OnvifAdapter";
    private final MockDeviceAdapter fallbackAdapter;

    public OnvifAdapter(DeviceInfo deviceInfo) {
        super(deviceInfo);
        this.fallbackAdapter = new MockDeviceAdapter(deviceInfo);
    }

    @Override
    public boolean login() {
        AppLogger.i(MODULE, "ONVIF 连接认证: " + deviceInfo.getIp() + ":" + deviceInfo.getPort());
        isLoggedIn = true;
        deviceInfo.setConnected(true);
        return fallbackAdapter.login();
    }

    @Override
    public boolean logout() {
        isLoggedIn = false;
        deviceInfo.setConnected(false);
        return fallbackAdapter.logout();
    }

    @Override
    public List<ChannelInfo> getChannels() {
        return fallbackAdapter.getChannels();
    }

    @Override
    public int startRealPlay(int channelNo, Surface surface, int streamType) {
        return fallbackAdapter.startRealPlay(channelNo, surface, streamType);
    }

    @Override
    public boolean stopRealPlay(int playHandle) {
        return fallbackAdapter.stopRealPlay(playHandle);
    }

    @Override
    public boolean capturePicture(int playHandle, String savePath) {
        return fallbackAdapter.capturePicture(playHandle, savePath);
    }

    @Override
    public boolean startRecord(int playHandle, String savePath) {
        return fallbackAdapter.startRecord(playHandle, savePath);
    }

    @Override
    public boolean stopRecord(int playHandle) {
        return fallbackAdapter.stopRecord(playHandle);
    }

    @Override
    public boolean ptzControl(int channelNo, PTZCommand command, boolean stop, int speed, int playHandle) {
        return fallbackAdapter.ptzControl(channelNo, command, stop, speed, playHandle);
    }

    @Override
    public List<RecordSegment> findRecords(int channelNo, Date startTime, Date endTime) {
        return fallbackAdapter.findRecords(channelNo, startTime, endTime);
    }

    @Override
    public int startPlaybackByTime(int channelNo, Surface surface, Date startTime, Date endTime) {
        return fallbackAdapter.startPlaybackByTime(channelNo, surface, startTime, endTime);
    }

    @Override
    public boolean playbackControl(int playbackHandle, PlaybackCommand command, int param) {
        return fallbackAdapter.playbackControl(playbackHandle, command, param);
    }

    @Override
    public int getPlaybackPos(int playbackHandle) {
        return fallbackAdapter.getPlaybackPos(playbackHandle);
    }

    @Override
    public boolean stopPlayback(int playbackHandle) {
        return fallbackAdapter.stopPlayback(playbackHandle);
    }
}

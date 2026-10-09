package com.weviewcam.client.core.adapter;

import android.view.Surface;
import android.view.SurfaceHolder;

import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PTZCommand;
import com.weviewcam.client.core.model.PlaybackCommand;
import com.weviewcam.client.core.model.RecordSegment;

import java.util.Date;
import java.util.List;

public abstract class BaseDeviceAdapter {
    protected DeviceInfo deviceInfo;
    protected boolean isLoggedIn = false;

    public BaseDeviceAdapter(DeviceInfo deviceInfo) {
        this.deviceInfo = deviceInfo;
    }

    public DeviceInfo getDeviceInfo() {
        return deviceInfo;
    }

    public boolean isLoggedIn() {
        return isLoggedIn;
    }

    public abstract boolean login();

    public abstract boolean logout();

    public abstract List<ChannelInfo> getChannels();

    /**
     * Start live video preview on given Android Surface.
     * @param channelNo Channel index (1-based or logical)
     * @param surface Android Surface for native rendering
     * @param streamType 0: Main stream (high-res), 1: Sub stream (low-res)
     * @return RealPlay handle or positive session id, -1 if failed
     */
    public abstract int startRealPlay(int channelNo, Surface surface, int streamType);

    /**
     * Start live video preview with SurfaceHolder (recommended for Hikvision Android SDK).
     */
    public int startRealPlay(int channelNo, SurfaceHolder surfaceHolder, int streamType) {
        return startRealPlay(channelNo, surfaceHolder != null ? surfaceHolder.getSurface() : null, streamType);
    }

    public abstract boolean stopRealPlay(int playHandle);

    public abstract boolean capturePicture(int playHandle, String savePath);

    public abstract boolean startRecord(int playHandle, String savePath);

    public abstract boolean stopRecord(int playHandle);

    /**
     * Control Pan-Tilt-Zoom.
     */
    public abstract boolean ptzControl(int channelNo, PTZCommand command, boolean stop, int speed, int playHandle);

    /**
     * Search for historical recordings on the device/NVR storage.
     */
    public abstract List<RecordSegment> findRecords(int channelNo, Date startTime, Date endTime);

    /**
     * Start recording playback by time range on given Android Surface.
     * @return Playback handle or positive session id, -1 if failed
     */
    public abstract int startPlaybackByTime(int channelNo, Surface surface, Date startTime, Date endTime);

    public abstract boolean playbackControl(int playbackHandle, PlaybackCommand command, int param);

    public abstract int getPlaybackPos(int playbackHandle);

    public abstract boolean stopPlayback(int playbackHandle);
}

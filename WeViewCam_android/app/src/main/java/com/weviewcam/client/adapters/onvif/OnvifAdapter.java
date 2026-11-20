package com.weviewcam.client.adapters.onvif;

import android.view.Surface;

import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PTZCommand;
import com.weviewcam.client.core.model.PlaybackCommand;
import com.weviewcam.client.core.model.RecordSegment;
import com.weviewcam.client.core.model.StreamStats;

import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Real ONVIF & Custom RTSP Adapter for Android.
 * Uses pure-Java OnvifSoapClient for WS-UsernameToken handshake & GetStreamUri,
 * and Media3 ExoPlayer RTSP (TCP interleaved + HW MediaCodec) for live video + FPS/bitrate stats.
 */
public class OnvifAdapter extends BaseDeviceAdapter {
    private static final String MODULE = "OnvifAdapter";

    private final RtspExoPlayerManager playerManager = RtspExoPlayerManager.getInstance();
    private final Map<Integer, Integer> activePlays = new ConcurrentHashMap<>();
    private final Map<Integer, String> cachedWorkingUrls = new ConcurrentHashMap<>();

    private OnvifSoapClient.DiscoveryResult discovery = new OnvifSoapClient.DiscoveryResult();

    public OnvifAdapter(DeviceInfo deviceInfo) {
        super(deviceInfo);
    }

    @Override
    public boolean login() {
        AppLogger.i(MODULE, "正在通过 ONVIF/RTSP 连接设备 [" + deviceInfo.getName() + "] "
                + deviceInfo.getIp() + ":" + deviceInfo.getPort());
        try {
            if (android.os.Looper.myLooper() == android.os.Looper.getMainLooper()) {
                java.util.concurrent.ExecutorService es = java.util.concurrent.Executors.newSingleThreadExecutor();
                try {
                    java.util.concurrent.Future<OnvifSoapClient.DiscoveryResult> fut = es.submit(() ->
                            OnvifSoapClient.discover(
                                    deviceInfo.getIp(),
                                    deviceInfo.getPort(),
                                    deviceInfo.getRtspPort(),
                                    deviceInfo.getUsername(),
                                    deviceInfo.getPassword()
                            ));
                    discovery = fut.get(3500, java.util.concurrent.TimeUnit.MILLISECONDS);
                } finally {
                    es.shutdownNow();
                }
            } else {
                discovery = OnvifSoapClient.discover(
                        deviceInfo.getIp(),
                        deviceInfo.getPort(),
                        deviceInfo.getRtspPort(),
                        deviceInfo.getUsername(),
                        deviceInfo.getPassword()
                );
            }
            if (discovery != null && discovery.connected) {
                deviceInfo.setPort(discovery.activePort);
            }
        } catch (Throwable t) {
            AppLogger.w(MODULE, "ONVIF 探测异常，将使用多厂商 RTSP 候选路径回退: " + t.getMessage());
        }
        isLoggedIn = true;
        deviceInfo.setConnected(true);
        return true;
    }

    @Override
    public boolean logout() {
        for (Integer handle : activePlays.values()) {
            playerManager.stopPlay(handle);
        }
        activePlays.clear();
        isLoggedIn = false;
        deviceInfo.setConnected(false);
        return true;
    }

    @Override
    public List<ChannelInfo> getChannels() {
        String name = (deviceInfo.getName() != null && !deviceInfo.getName().isEmpty())
                ? deviceInfo.getName()
                : "ONVIF 摄像机";
        return Collections.singletonList(
                new ChannelInfo(1, name, true, discovery.ptzSupported, deviceInfo.getDeviceId(), true)
        );
    }

    @Override
    public int startRealPlay(int channelNo, Surface surface, int streamType) {
        try {
            String onvifUri = (streamType == 0) ? discovery.mainStreamUri : discovery.subStreamUri;
            String cached = cachedWorkingUrls.get(streamType);
            List<String> candidates = OnvifSoapClient.buildCandidateRtspUrls(
                    deviceInfo.getIp(),
                    deviceInfo.getRtspPort(),
                    deviceInfo.getUsername(),
                    deviceInfo.getPassword(),
                    channelNo,
                    streamType,
                    (cached != null && !cached.isEmpty()) ? cached : onvifUri
            );

            String primary = candidates.isEmpty() ? "" : candidates.get(0);
            int handle = playerManager.startPlay(primary, surface, candidates,
                    workingUrl -> cachedWorkingUrls.put(streamType, workingUrl));
            if (handle > 0) {
                activePlays.put(channelNo, handle);
            }
            return handle;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "ONVIF startRealPlay 异常: " + t.getMessage(), t);
            return -1;
        }
    }

    @Override
    public boolean stopRealPlay(int playHandle) {
        activePlays.values().removeIf(h -> h == playHandle);
        return playerManager.stopPlay(playHandle);
    }

    @Override
    public boolean capturePicture(int playHandle, String savePath) {
        return false;
    }

    @Override
    public boolean startRecord(int playHandle, String savePath) {
        return false;
    }

    @Override
    public boolean stopRecord(int playHandle) {
        return false;
    }

    @Override
    public boolean ptzControl(int channelNo, PTZCommand command, boolean stop, int speed, int playHandle) {
        if (!discovery.connected || discovery.mainProfileToken.isEmpty()) {
            return false;
        }
        if (stop) {
            return OnvifSoapClient.ptzStop(deviceInfo.getIp(), deviceInfo.getPort(),
                    deviceInfo.getUsername(), deviceInfo.getPassword(), discovery.mainProfileToken);
        }
        float s = Math.max(0.1f, Math.min(1.0f, speed / 7.0f));
        float pan = 0f, tilt = 0f, zoom = 0f;
        switch (command) {
            case UP: tilt = s; break;
            case DOWN: tilt = -s; break;
            case LEFT: pan = -s; break;
            case RIGHT: pan = s; break;
            case UP_LEFT: pan = -s * 0.7f; tilt = s * 0.7f; break;
            case UP_RIGHT: pan = s * 0.7f; tilt = s * 0.7f; break;
            case DOWN_LEFT: pan = -s * 0.7f; tilt = -s * 0.7f; break;
            case DOWN_RIGHT: pan = s * 0.7f; tilt = -s * 0.7f; break;
            case ZOOM_IN: zoom = s; break;
            case ZOOM_OUT: zoom = -s; break;
            default: break;
        }
        return OnvifSoapClient.ptzContinuousMove(deviceInfo.getIp(), deviceInfo.getPort(),
                deviceInfo.getUsername(), deviceInfo.getPassword(), discovery.mainProfileToken, pan, tilt, zoom);
    }

    @Override
    public List<RecordSegment> findRecords(int channelNo, Date startTime, Date endTime) {
        // Most ONVIF cameras only implement Profile S (Live) and do not support Profile G playback
        AppLogger.w(MODULE, "ONVIF 设备 [" + deviceInfo.getName() + "] 暂不支持 Profile G 录像回放检索");
        return Collections.emptyList();
    }

    @Override
    public int startPlaybackByTime(int channelNo, Surface surface, Date startTime, Date endTime) {
        AppLogger.w(MODULE, "ONVIF 设备 [" + deviceInfo.getName() + "] 不支持录像回放，请使用厂商私有协议（海康/大华）");
        return -1;
    }

    @Override
    public boolean playbackControl(int playbackHandle, PlaybackCommand command, int param) {
        return false;
    }

    @Override
    public int getPlaybackPos(int playbackHandle) {
        return 0;
    }

    @Override
    public StreamStats getStreamStats(int playHandle, boolean isPlayback) {
        return playerManager.getStreamStats(playHandle);
    }

    @Override
    public boolean stopPlayback(int playbackHandle) {
        return playerManager.stopPlay(playbackHandle);
    }
}

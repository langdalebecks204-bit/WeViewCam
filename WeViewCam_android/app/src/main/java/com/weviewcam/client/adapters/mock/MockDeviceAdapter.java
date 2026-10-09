package com.weviewcam.client.adapters.mock;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.os.Handler;
import android.os.Looper;
import android.view.Surface;

import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PTZCommand;
import com.weviewcam.client.core.model.PlaybackCommand;
import com.weviewcam.client.core.model.RecordSegment;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

public class MockDeviceAdapter extends BaseDeviceAdapter {
    private static final String MODULE = "MockAdapter";
    private static final AtomicInteger HANDLE_GEN = new AtomicInteger(100);

    private final Map<Integer, RenderSession> activeSessions = new ConcurrentHashMap<>();
    private final Handler handler = new Handler(Looper.getMainLooper());

    private static class RenderSession {
        int handle;
        int channelNo;
        Surface surface;
        String title;
        boolean isPlayback;
        float ptzPan = 0f;
        float ptzTilt = 0f;
        float zoom = 1.0f;
        AtomicBoolean isRunning = new AtomicBoolean(true);
        Thread renderThread;
        Date simulatedTime = new Date();
        int progress = 0;
        boolean isPaused = false;
        float speed = 1.0f;
    }

    public MockDeviceAdapter(DeviceInfo deviceInfo) {
        super(deviceInfo);
    }

    @Override
    public boolean login() {
        isLoggedIn = true;
        deviceInfo.setConnected(true);
        AppLogger.i(MODULE, "已连接监控适配器 (仿真协议模式) [" + deviceInfo.getName() + "]");
        return true;
    }

    @Override
    public boolean logout() {
        for (RenderSession s : activeSessions.values()) {
            stopSession(s);
        }
        activeSessions.clear();
        isLoggedIn = false;
        deviceInfo.setConnected(false);
        return true;
    }

    @Override
    public List<ChannelInfo> getChannels() {
        if (deviceInfo.getChannels() != null && !deviceInfo.getChannels().isEmpty()) {
            return deviceInfo.getChannels();
        }
        List<ChannelInfo> list = new ArrayList<>();
        list.add(new ChannelInfo(1, "通道 1 - 主大门球机", true, true, deviceInfo.getDeviceId()));
        list.add(new ChannelInfo(2, "通道 2 - 停车场出入口", true, false, deviceInfo.getDeviceId()));
        list.add(new ChannelInfo(3, "通道 3 - 办公大楼大厅", true, false, deviceInfo.getDeviceId()));
        list.add(new ChannelInfo(4, "通道 4 - 园区周界围栏", true, false, deviceInfo.getDeviceId()));
        deviceInfo.setChannels(list);
        return list;
    }

    @Override
    public int startRealPlay(int channelNo, Surface surface, int streamType) {
        if (surface == null || !surface.isValid()) return -1;
        int handle = HANDLE_GEN.incrementAndGet();

        RenderSession session = new RenderSession();
        session.handle = handle;
        session.channelNo = channelNo;
        session.surface = surface;
        session.title = getChannelName(channelNo) + (streamType == 0 ? " [主码流]" : " [子码流]");
        session.isPlayback = false;

        startRendering(session);
        activeSessions.put(handle, session);
        return handle;
    }

    @Override
    public boolean stopRealPlay(int playHandle) {
        RenderSession session = activeSessions.remove(playHandle);
        if (session != null) {
            stopSession(session);
            return true;
        }
        return false;
    }

    @Override
    public boolean capturePicture(int playHandle, String savePath) {
        AppLogger.i(MODULE, "模拟抓图保存成功: " + savePath);
        return true;
    }

    @Override
    public boolean startRecord(int playHandle, String savePath) {
        AppLogger.i(MODULE, "模拟开启本地MP4录像: " + savePath);
        return true;
    }

    @Override
    public boolean stopRecord(int playHandle) {
        AppLogger.i(MODULE, "模拟停止本地MP4录像");
        return true;
    }

    @Override
    public boolean ptzControl(int channelNo, PTZCommand command, boolean stop, int speed, int playHandle) {
        RenderSession session = null;
        if (playHandle > 0) {
            session = activeSessions.get(playHandle);
        } else {
            for (RenderSession s : activeSessions.values()) {
                if (s.channelNo == channelNo) {
                    session = s;
                    break;
                }
            }
        }

        if (session != null && !stop) {
            float step = speed * 1.5f;
            switch (command) {
                case UP: session.ptzTilt -= step; break;
                case DOWN: session.ptzTilt += step; break;
                case LEFT: session.ptzPan -= step; break;
                case RIGHT: session.ptzPan += step; break;
                case UP_LEFT: session.ptzTilt -= step; session.ptzPan -= step; break;
                case UP_RIGHT: session.ptzTilt -= step; session.ptzPan += step; break;
                case DOWN_LEFT: session.ptzTilt += step; session.ptzPan -= step; break;
                case DOWN_RIGHT: session.ptzTilt += step; session.ptzPan += step; break;
                case ZOOM_IN: session.zoom = Math.min(4.0f, session.zoom + 0.2f); break;
                case ZOOM_OUT: session.zoom = Math.max(0.5f, session.zoom - 0.2f); break;
                default: break;
            }
        }
        return true;
    }

    @Override
    public List<RecordSegment> findRecords(int channelNo, Date startTime, Date endTime) {
        List<RecordSegment> list = new ArrayList<>();
        Calendar cal = Calendar.getInstance();
        cal.setTime(startTime);
        cal.set(Calendar.HOUR_OF_DAY, 0);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        Date dayStart = cal.getTime();

        // Generate realistic surveillance segments throughout the day
        int[][] intervals = {
                {0, 0, 4, 30},   // 00:00 - 04:30
                {5, 0, 8, 15},   // 05:00 - 08:15
                {8, 30, 12, 0},  // 08:30 - 12:00
                {13, 0, 18, 45}, // 13:00 - 18:45
                {19, 30, 23, 59} // 19:30 - 23:59
        };

        for (int[] iv : intervals) {
            cal.setTime(dayStart);
            cal.set(Calendar.HOUR_OF_DAY, iv[0]);
            cal.set(Calendar.MINUTE, iv[1]);
            Date segStart = cal.getTime();

            cal.set(Calendar.HOUR_OF_DAY, iv[2]);
            cal.set(Calendar.MINUTE, iv[3]);
            Date segEnd = cal.getTime();

            if (segEnd.after(startTime) && segStart.before(endTime)) {
                String name = String.format(Locale.getDefault(), "ch%02d_%02d%02d.mp4", channelNo, iv[0], iv[1]);
                list.add(new RecordSegment(channelNo, segStart, segEnd, name, 250 * 1024 * 1024L, "schedule"));
            }
        }

        // Add an alarm segment around 10:15 - 10:30
        cal.setTime(dayStart);
        cal.set(Calendar.HOUR_OF_DAY, 10);
        cal.set(Calendar.MINUTE, 15);
        Date alarmStart = cal.getTime();
        cal.set(Calendar.MINUTE, 30);
        Date alarmEnd = cal.getTime();
        list.add(new RecordSegment(channelNo, alarmStart, alarmEnd, "alarm_1015.mp4", 50 * 1024 * 1024L, "alarm"));

        return list;
    }

    @Override
    public int startPlaybackByTime(int channelNo, Surface surface, Date startTime, Date endTime) {
        if (surface == null || !surface.isValid()) return -1;
        int handle = HANDLE_GEN.incrementAndGet();

        RenderSession session = new RenderSession();
        session.handle = handle;
        session.channelNo = channelNo;
        session.surface = surface;
        session.title = getChannelName(channelNo) + " [录像回放]";
        session.isPlayback = true;
        session.simulatedTime = startTime != null ? startTime : new Date();

        startRendering(session);
        activeSessions.put(handle, session);
        return handle;
    }

    @Override
    public boolean playbackControl(int playbackHandle, PlaybackCommand command, int param) {
        RenderSession session = activeSessions.get(playbackHandle);
        if (session == null) return false;

        switch (command) {
            case START:
            case RESTART:
                session.isPaused = false;
                break;
            case PAUSE:
                session.isPaused = true;
                break;
            case FAST:
                session.speed = Math.min(16.0f, session.speed * 2.0f);
                break;
            case SLOW:
                session.speed = Math.max(0.25f, session.speed / 2.0f);
                break;
            case NORMAL:
                session.speed = 1.0f;
                session.isPaused = false;
                break;
            case SET_POS:
                session.progress = Math.max(0, Math.min(100, param));
                break;
            default:
                break;
        }
        return true;
    }

    @Override
    public int getPlaybackPos(int playbackHandle) {
        RenderSession session = activeSessions.get(playbackHandle);
        return session != null ? session.progress : 0;
    }

    @Override
    public boolean stopPlayback(int playbackHandle) {
        RenderSession session = activeSessions.remove(playbackHandle);
        if (session != null) {
            stopSession(session);
            return true;
        }
        return false;
    }

    private String getChannelName(int channelNo) {
        for (ChannelInfo ch : getChannels()) {
            if (ch.getChannelNo() == channelNo) {
                return ch.getName();
            }
        }
        return "监控通道 " + channelNo;
    }

    private void startRendering(RenderSession session) {
        session.renderThread = new Thread(() -> {
            Paint bgPaint = new Paint();
            bgPaint.setColor(Color.parseColor("#121820"));

            Paint gridPaint = new Paint();
            gridPaint.setColor(Color.parseColor("#1b2533"));
            gridPaint.setStrokeWidth(2f);

            Paint textPaint = new Paint();
            textPaint.setColor(Color.WHITE);
            textPaint.setTextSize(34f);
            textPaint.setAntiAlias(true);
            textPaint.setShadowLayer(4f, 2f, 2f, Color.BLACK);

            Paint badgePaint = new Paint();
            badgePaint.setColor(Color.parseColor("#238636"));
            badgePaint.setAntiAlias(true);

            Paint ptzIndicatorPaint = new Paint();
            ptzIndicatorPaint.setColor(Color.parseColor("#58a6ff"));
            ptzIndicatorPaint.setStyle(Paint.Style.STROKE);
            ptzIndicatorPaint.setStrokeWidth(3f);

            SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault());

            long lastUpdate = System.currentTimeMillis();

            while (session.isRunning.get()) {
                if (!session.surface.isValid()) {
                    try { Thread.sleep(100); } catch (InterruptedException ignored) {}
                    continue;
                }

                Canvas canvas = null;
                try {
                    canvas = session.surface.lockCanvas(null);
                    if (canvas != null) {
                        int w = canvas.getWidth();
                        int h = canvas.getHeight();

                        // 1. Clear background
                        canvas.drawRect(0, 0, w, h, bgPaint);

                        // 2. Draw surveillance perspective grid with PTZ offsets
                        float cx = w / 2f + session.ptzPan;
                        float cy = h / 2f + session.ptzTilt;
                        for (int i = -w; i < w * 2; i += 80 * session.zoom) {
                            canvas.drawLine(i + session.ptzPan, 0, i + session.ptzPan, h, gridPaint);
                        }
                        for (int j = -h; j < h * 2; j += 60 * session.zoom) {
                            canvas.drawLine(0, j + session.ptzTilt, w, j + session.ptzTilt, gridPaint);
                        }

                        // 3. Center crosshair
                        canvas.drawLine(cx - 20, cy, cx + 20, cy, ptzIndicatorPaint);
                        canvas.drawLine(cx, cy - 20, cx, cy + 20, ptzIndicatorPaint);

                        // 4. Update time
                        long now = System.currentTimeMillis();
                        if (!session.isPaused && (now - lastUpdate) >= 1000) {
                            session.simulatedTime = new Date(session.simulatedTime.getTime() + (long)(1000 * session.speed));
                            if (session.isPlayback) {
                                session.progress = (session.progress + 1) % 100;
                            }
                            lastUpdate = now;
                        }

                        // 5. Draw OSD Title & Time
                        String timeStr = sdf.format(session.simulatedTime);
                        canvas.drawText(session.title, 30, 50, textPaint);
                        canvas.drawText(timeStr, w - textPaint.measureText(timeStr) - 30, 50, textPaint);

                        // 6. Draw Status indicator (REC / LIVE)
                        if (session.isPlayback) {
                            canvas.drawText("回放倍速: " + session.speed + "x", 30, h - 30, textPaint);
                        } else {
                            canvas.drawCircle(40, 90, 10, badgePaint);
                            textPaint.setTextSize(26f);
                            canvas.drawText("LIVE", 60, 98, textPaint);
                            textPaint.setTextSize(34f);
                        }
                    }
                } catch (Exception e) {
                    AppLogger.w(MODULE, "渲染画面中断: " + e.getMessage());
                } finally {
                    if (canvas != null) {
                        try {
                            session.surface.unlockCanvasAndPost(canvas);
                        } catch (Exception ignored) {}
                    }
                }

                try {
                    Thread.sleep(60); // ~16 FPS simulated surveillance refresh
                } catch (InterruptedException e) {
                    break;
                }
            }
        });
        session.renderThread.start();
    }

    private void stopSession(RenderSession session) {
        session.isRunning.set(false);
        if (session.renderThread != null) {
            session.renderThread.interrupt();
        }
    }
}

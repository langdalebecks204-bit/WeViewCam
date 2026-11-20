package com.weviewcam.client.adapters.onvif;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.view.Surface;

import androidx.annotation.NonNull;
import androidx.annotation.OptIn;
import androidx.media3.common.Format;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.common.util.UnstableApi;
import androidx.media3.exoplayer.DecoderCounters;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.analytics.AnalyticsListener;
import androidx.media3.exoplayer.rtsp.RtspMediaSource;

import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.StreamStats;
import com.weviewcam.client.core.util.StreamStatsTracker;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Hardware-accelerated RTSP player manager powered by AndroidX Media3 ExoPlayer RTSP.
 * Supports RTSP over TCP, Digest auth, H.264/H.265, and real-time FPS/bitrate telemetry.
 */
@OptIn(markerClass = UnstableApi.class)
public class RtspExoPlayerManager {
    private static final String MODULE = "RtspExoPlayer";
    private static volatile Context appContext;
    private static final RtspExoPlayerManager INSTANCE = new RtspExoPlayerManager();

    private final AtomicInteger handleGen = new AtomicInteger(6100);
    private final Map<Integer, Session> sessions = new ConcurrentHashMap<>();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService probeExecutor = Executors.newCachedThreadPool();

    public interface UrlMatchedCallback {
        void onMatched(String workingUrl);
    }

    private static class Session {
        final int handle;
        volatile boolean active = true;
        volatile ExoPlayer player;
        volatile Surface surface;
        volatile String currentUrl;
        volatile LocalRtspProxy proxy;
        final StreamStatsTracker statsTracker = new StreamStatsTracker();
        volatile Double lastEstimatedBitrateKbps = null;

        Session(int handle, Surface surface, String url) {
            this.handle = handle;
            this.surface = surface;
            this.currentUrl = url;
        }
    }

    private RtspExoPlayerManager() {}

    public static void init(Context context) {
        if (context != null) {
            appContext = context.getApplicationContext();
        }
    }

    public static RtspExoPlayerManager getInstance() {
        return INSTANCE;
    }

    public int startPlay(String primaryUrl, Surface surface, List<String> candidates, UrlMatchedCallback cb) {
        if (appContext == null) {
            AppLogger.e(MODULE, "RtspExoPlayerManager 未初始化 Context");
            return -1;
        }
        if (surface == null || !surface.isValid()) {
            AppLogger.e(MODULE, "startPlay 失败: surface 无效");
            return -1;
        }

        final List<String> allUrls = new ArrayList<>();
        if (primaryUrl != null && !primaryUrl.isEmpty()) allUrls.add(primaryUrl);
        if (candidates != null) {
            for (String u : candidates) {
                if (u != null && !u.isEmpty() && !allUrls.contains(u)) {
                    allUrls.add(u);
                }
            }
        }
        if (allUrls.isEmpty()) return -1;

        final int handle = handleGen.incrementAndGet();
        final Session session = new Session(handle, surface, allUrls.get(0));
        sessions.put(handle, session);

        probeExecutor.execute(() -> {
            try {
                if (!session.active) return;

                String targetUrl = allUrls.get(0);
                if (allUrls.size() > 1) {
                    for (String cand : allUrls) {
                        if (!session.active) return;
                        if (OnvifSoapClient.probeRtspUrl(cand, 400)) {
                            targetUrl = cand;
                            if (cb != null) {
                                try {
                                    cb.onMatched(cand);
                                } catch (Throwable ignored) {}
                            }
                            break;
                        }
                    }
                }

                if (!session.active) return;
                session.currentUrl = targetUrl;

                String playUrl = targetUrl;
                try {
                    LocalRtspProxy proxy = new LocalRtspProxy(targetUrl, session.statsTracker);
                    session.proxy = proxy;
                    playUrl = proxy.getLocalRtspUrl();
                } catch (Throwable pe) {
                    AppLogger.w(MODULE, "LocalRtspProxy 启动失败，回退直连: " + pe.getMessage());
                }
                final String finalUrl = playUrl;

                mainHandler.post(() -> {
                    if (!session.active || session.surface == null || !session.surface.isValid()) {
                        return;
                    }
                    try {
                        RtspMediaSource.Factory rtspFactory = new RtspMediaSource.Factory()
                                .setForceUseRtpTcp(true)
                                .setTimeoutMs(5000);

                        ExoPlayer player = new ExoPlayer.Builder(appContext)
                                .setMediaSourceFactory(rtspFactory)
                                .build();

                        player.addListener(new Player.Listener() {
                            @Override
                            public void onPlayerError(@NonNull PlaybackException error) {
                                Throwable cause = error.getCause();
                                AppLogger.e(MODULE, "ExoPlayer RTSP 播放异常 handle=" + handle + ": "
                                        + error.getErrorCodeName() + " - " + error.getMessage()
                                        + (cause != null ? " | cause=" + cause.getClass().getSimpleName() + ": " + cause.getMessage() : ""));
                            }
                        });

                        player.addAnalyticsListener(new AnalyticsListener() {
                            @Override
                            public void onBandwidthEstimate(@NonNull EventTime eventTime, int totalLoadTimeMs,
                                                            long totalBytesLoaded, long bitrateEstimate) {
                                if (totalBytesLoaded > 0) {
                                    session.statsTracker.recordBytes((int) Math.min(totalBytesLoaded, Integer.MAX_VALUE));
                                }
                                if (bitrateEstimate > 0 && bitrateEstimate < 100_000_000L) {
                                    session.lastEstimatedBitrateKbps = bitrateEstimate / 1000.0;
                                }
                            }
                        });

                        player.setVideoSurface(session.surface);
                        player.setMediaItem(MediaItem.fromUri(finalUrl));
                        player.prepare();
                        player.setPlayWhenReady(true);
                        session.player = player;

                        AppLogger.i(MODULE, "✓ ExoPlayer RTSP 启动拉流 handle=" + handle + ", url=" + maskUrl(finalUrl));
                    } catch (Throwable t) {
                        AppLogger.e(MODULE, "创建 ExoPlayer 异常: " + t.getMessage(), t);
                    }
                });
            } catch (Throwable t) {
                AppLogger.e(MODULE, "RTSP 探测线程异常: " + t.getMessage(), t);
            }
        });

        return handle;
    }

    public boolean stopPlay(int handle) {
        Session session = sessions.remove(handle);
        if (session == null) return false;
        session.active = false;
        final LocalRtspProxy proxy = session.proxy;
        session.proxy = null;
        if (proxy != null) {
            proxy.close();
        }
        final ExoPlayer player = session.player;
        session.player = null;
        if (player != null) {
            Runnable releaseTask = () -> {
                try {
                    player.clearVideoSurface();
                    player.stop();
                    player.release();
                } catch (Throwable ignored) {}
            };
            if (Looper.myLooper() == Looper.getMainLooper()) {
                releaseTask.run();
            } else {
                mainHandler.post(releaseTask);
            }
        }
        return true;
    }

    public StreamStats getStreamStats(int handle) {
        final Session session = sessions.get(handle);
        if (session == null || !session.active || session.player == null) {
            return new StreamStats(null, null);
        }

        final Double[] res = new Double[2]; // [fps, bitrateKbps]
        if (Looper.myLooper() == Looper.getMainLooper()) {
            queryStatsOnMainThread(session, res);
        } else {
            final java.util.concurrent.CountDownLatch latch = new java.util.concurrent.CountDownLatch(1);
            mainHandler.post(() -> {
                try {
                    queryStatsOnMainThread(session, res);
                } finally {
                    latch.countDown();
                }
            });
            try {
                latch.await(100, java.util.concurrent.TimeUnit.MILLISECONDS);
            } catch (InterruptedException ignored) {}
        }
        return new StreamStats(res[0], res[1]);
    }

    private void queryStatsOnMainThread(Session session, Double[] out) {
        ExoPlayer p = session.player;
        if (p == null) return;
        try {
            DecoderCounters counters = p.getVideoDecoderCounters();
            if (counters != null && counters.renderedOutputBufferCount > 0) {
                out[0] = session.statsTracker.sampleFpsFromTotalFrames(counters.renderedOutputBufferCount);
            }
            if (out[0] == null || out[0] <= 0) {
                Format fmt = p.getVideoFormat();
                if (fmt != null && fmt.frameRate > 0 && fmt.frameRate <= 120) {
                    out[0] = (double) fmt.frameRate;
                }
            }
            Double sampledKbps = session.statsTracker.sampleBitrateKbps();
            out[1] = (sampledKbps != null && sampledKbps > 0) ? sampledKbps : session.lastEstimatedBitrateKbps;
        } catch (Throwable ignored) {}
    }

    private static String maskUrl(String url) {
        if (url == null) return "";
        return url.replaceAll("://([^:]+):([^@]+)@", "://$1:***@");
    }
}

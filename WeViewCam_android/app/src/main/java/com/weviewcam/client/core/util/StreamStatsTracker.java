package com.weviewcam.client.core.util;

/**
 * Thread-safe rolling calculator for stream bitrate (kbps) and frame rate (fps).
 */
public class StreamStatsTracker {
    private final Object lock = new Object();
    private long bytesAccum = 0;
    private long lastBitrateNs;
    private Double lastBitrateKbps = null;

    private long framesAccum = 0;
    private long lastTotalFrames = -1;
    private long lastFpsNs;
    private Double lastFps = null;

    public StreamStatsTracker() {
        long now = System.nanoTime();
        this.lastBitrateNs = now;
        this.lastFpsNs = now;
    }

    public void recordBytes(int numBytes) {
        if (numBytes <= 0) return;
        synchronized (lock) {
            bytesAccum += numBytes;
        }
    }

    public void recordFrames(int numFrames) {
        if (numFrames <= 0) return;
        synchronized (lock) {
            framesAccum += numFrames;
        }
    }

    public Double sampleBitrateKbps() {
        long now = System.nanoTime();
        synchronized (lock) {
            double dt = (now - lastBitrateNs) / 1_000_000_000.0;
            if (dt >= 0.4) {
                lastBitrateKbps = (bytesAccum * 8.0) / (dt * 1000.0);
                bytesAccum = 0;
                lastBitrateNs = now;
            }
            return lastBitrateKbps;
        }
    }

    public Double sampleFpsFromTotalFrames(long totalFrames) {
        if (totalFrames < 0) {
            synchronized (lock) {
                return lastFps;
            }
        }
        long now = System.nanoTime();
        synchronized (lock) {
            if (lastTotalFrames < 0 || totalFrames < lastTotalFrames) {
                lastTotalFrames = totalFrames;
                lastFpsNs = now;
                return lastFps;
            }
            double dt = (now - lastFpsNs) / 1_000_000_000.0;
            if (dt >= 0.4) {
                long delta = totalFrames - lastTotalFrames;
                lastTotalFrames = totalFrames;
                lastFpsNs = now;
                lastFps = delta / dt;
            }
            return lastFps;
        }
    }

    public Double sampleFpsFromRecordedFrames() {
        long now = System.nanoTime();
        synchronized (lock) {
            double dt = (now - lastFpsNs) / 1_000_000_000.0;
            if (dt >= 0.4) {
                if (framesAccum > 0) {
                    lastFps = framesAccum / dt;
                }
                framesAccum = 0;
                lastFpsNs = now;
            }
            return lastFps;
        }
    }

    /**
     * Count MPEG-PS pack headers (00 00 01 BA) in Hikvision stream chunks to estimate frame rate.
     */
    public static int countPsPackHeaders(byte[] buf, int len) {
        if (buf == null || len < 4) return 0;
        int limit = Math.min(buf.length, len) - 3;
        int count = 0;
        for (int i = 0; i < limit; i++) {
            if (buf[i] == 0x00 && buf[i + 1] == 0x00 && buf[i + 2] == 0x01 && (buf[i + 3] & 0xFF) == 0xBA) {
                count++;
                i += 3;
            }
        }
        return count;
    }
}

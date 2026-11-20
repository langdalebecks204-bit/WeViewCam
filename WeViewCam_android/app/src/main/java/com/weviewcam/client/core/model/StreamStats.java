package com.weviewcam.client.core.model;

/**
 * Immutable snapshot of real-time or playback stream statistics.
 */
public class StreamStats {
    public final Double fps;
    public final Double bitrateKbps;

    public StreamStats(Double fps, Double bitrateKbps) {
        this.fps = fps;
        this.bitrateKbps = bitrateKbps;
    }
}

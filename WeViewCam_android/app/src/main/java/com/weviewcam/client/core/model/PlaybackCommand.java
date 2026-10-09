package com.weviewcam.client.core.model;

public enum PlaybackCommand {
    START,
    PAUSE,
    RESTART,
    FAST,       // Speed up (2x, 4x, 8x, 16x)
    SLOW,       // Slow down (1/2, 1/4)
    NORMAL,     // Restore normal 1x speed
    STEP_FRAME, // Step forward single frame
    GET_POS,    // Get playback progress (0-100)
    SET_POS     // Seek to progress percentage (0-100)
}

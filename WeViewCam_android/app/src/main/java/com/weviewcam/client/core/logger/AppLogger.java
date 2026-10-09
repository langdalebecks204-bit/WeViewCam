package com.weviewcam.client.core.logger;

import android.util.Log;

public class AppLogger {
    private static final String TAG = "WeViewCam";

    public static void d(String module, String message) {
        Log.d(TAG, "[" + module + "] " + message);
    }

    public static void i(String module, String message) {
        Log.i(TAG, "[" + module + "] " + message);
    }

    public static void w(String module, String message) {
        Log.w(TAG, "[" + module + "] " + message);
    }

    public static void e(String module, String message) {
        Log.e(TAG, "[" + module + "] " + message);
    }

    public static void e(String module, String message, Throwable tr) {
        Log.e(TAG, "[" + module + "] " + message, tr);
    }
}

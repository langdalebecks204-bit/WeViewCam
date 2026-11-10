package com.weviewcam.client.core.logger;

import android.content.Context;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class AppLogger {
    private static final String TAG = "WeViewCam";
    private static File logFile = null;
    private static final Object FILE_LOCK = new Object();
    private static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.getDefault());

    public static void init(Context context) {
        if (context != null) {
            try {
                File dir = context.getExternalFilesDir(null);
                if (dir == null) {
                    dir = context.getFilesDir();
                }
                logFile = new File(dir, "app.log");
                // 限制日志文件大小超过 5MB 则滚动保留最近内容
                if (logFile.exists() && logFile.length() > 5 * 1024 * 1024) {
                    logFile.delete();
                }
                writeToFile("INFO", "AppLogger", "=== 应用日志记录器已启动 (同步强刷盘模式) ===");
            } catch (Throwable ignored) {}
        }
    }

    public static File getLogFile() {
        return logFile;
    }

    private static void writeToFile(String level, String module, String message) {
        if (logFile == null) return;
        final String time = DATE_FORMAT.format(new Date());
        final String line = String.format(Locale.getDefault(), "%s [%s] [%s] %s\n", time, level, module, message);
        synchronized (FILE_LOCK) {
            try {
                if (logFile != null) {
                    try (FileOutputStream fos = new FileOutputStream(logFile, true)) {
                        fos.write(line.getBytes(StandardCharsets.UTF_8));
                        fos.flush();
                        try {
                            fos.getFD().sync(); // 强行落盘，防止进程在下一行 Native 代码崩溃时缓存丢失
                        } catch (Throwable ignored) {}
                    }
                }
            } catch (Throwable ignored) {}
        }
    }

    public static String dumpSystemLogcat() {
        StringBuilder sb = new StringBuilder();
        try {
            Process process = Runtime.getRuntime().exec(new String[]{"logcat", "-d", "-v", "time"});
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                List<String> list = new ArrayList<>();
                while ((line = reader.readLine()) != null) {
                    list.add(line);
                }
                int start = Math.max(0, list.size() - 400);
                for (int i = start; i < list.size(); i++) {
                    sb.append(list.get(i)).append("\n");
                }
            }
        } catch (Throwable t) {
            sb.append("获取系统 Logcat 失败: ").append(t.getMessage());
        }
        return sb.toString();
    }

    public static void d(String module, String message) {
        Log.d(TAG, "[" + module + "] " + message);
        writeToFile("DEBUG", module, message);
    }

    public static void i(String module, String message) {
        Log.i(TAG, "[" + module + "] " + message);
        writeToFile("INFO", module, message);
    }

    public static void w(String module, String message) {
        Log.w(TAG, "[" + module + "] " + message);
        writeToFile("WARN", module, message);
    }

    public static void e(String module, String message) {
        Log.e(TAG, "[" + module + "] " + message);
        writeToFile("ERROR", module, message);
    }

    public static void e(String module, String message, Throwable tr) {
        Log.e(TAG, "[" + module + "] " + message, tr);
        String stack = tr != null ? "\n" + Log.getStackTraceString(tr) : "";
        writeToFile("ERROR", module, message + stack);
    }
}

package com.weviewcam.client.ui;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.Fragment;

import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.weviewcam.client.R;
import com.weviewcam.client.core.manager.DeviceManager;
import com.weviewcam.client.ui.device.DeviceManagementFragment;
import com.weviewcam.client.ui.live.LiveViewFragment;
import com.weviewcam.client.ui.playback.PlaybackFragment;

import android.content.res.Configuration;
import android.view.View;
import androidx.annotation.NonNull;

public class MainActivity extends AppCompatActivity {

    private LiveViewFragment liveViewFragment;
    private PlaybackFragment playbackFragment;
    private DeviceManagementFragment deviceManagementFragment;

    private View appHeader;
    private View headerDivider;
    private View bottomDivider;
    private BottomNavigationView bottomNav;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        com.weviewcam.client.core.logger.AppLogger.init(this);
        setContentView(R.layout.activity_main);

        appHeader = findViewById(R.id.app_header);
        headerDivider = findViewById(R.id.header_divider);
        bottomDivider = findViewById(R.id.bottom_divider);
        bottomNav = findViewById(R.id.bottom_navigation);

        android.widget.TextView tvVersion = findViewById(R.id.tv_app_version);
        if (tvVersion != null) {
            String verText = "v" + getAppVersionName(this);
            tvVersion.setText(verText);
            tvVersion.setOnClickListener(v -> showAboutAndLogDialog(verText));
        }

        // Pre-initialize DeviceManager
        DeviceManager.getInstance(this);

        checkPermissions();

        liveViewFragment = new LiveViewFragment();
        playbackFragment = new PlaybackFragment();
        deviceManagementFragment = new DeviceManagementFragment();

        // Default to Live View
        switchFragment(liveViewFragment);

        updateOrientationVisibility(getResources().getConfiguration().orientation);

        bottomNav.setOnItemSelectedListener(item -> {
            int id = item.getItemId();
            if (id == R.id.nav_live) {
                switchFragment(liveViewFragment);
                return true;
            } else if (id == R.id.nav_playback) {
                switchFragment(playbackFragment);
                return true;
            } else if (id == R.id.nav_device) {
                switchFragment(deviceManagementFragment);
                return true;
            }
            return false;
        });
    }

    private boolean isFullScreen = false;

    public interface FullScreenListener {
        void onFullScreenChanged(boolean isFullScreen);
    }

    public boolean isFullScreen() {
        return isFullScreen;
    }

    public void setFullScreen(boolean fullScreen) {
        this.isFullScreen = fullScreen;
        if (fullScreen) {
            setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
            enterImmersiveMode();
            updateOrientationVisibility(Configuration.ORIENTATION_LANDSCAPE);
        } else {
            setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
            exitImmersiveMode();
            updateOrientationVisibility(Configuration.ORIENTATION_PORTRAIT);
        }

        notifyFullScreenChanged(fullScreen);
    }

    public void toggleFullScreen() {
        setFullScreen(!isFullScreen);
    }

    private void notifyFullScreenChanged(boolean fullScreen) {
        Fragment current = getSupportFragmentManager().findFragmentById(R.id.fragment_container);
        if (current instanceof FullScreenListener) {
            ((FullScreenListener) current).onFullScreenChanged(fullScreen);
        }
    }

    private void enterImmersiveMode() {
        View decorView = getWindow().getDecorView();
        decorView.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }

    private void exitImmersiveMode() {
        View decorView = getWindow().getDecorView();
        decorView.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE);
    }

    @Override
    public void onBackPressed() {
        if (isFullScreen) {
            setFullScreen(false);
            return;
        }
        super.onBackPressed();
    }

    @Override
    public void onConfigurationChanged(@NonNull Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        if (isFullScreen) {
            enterImmersiveMode();
            updateOrientationVisibility(Configuration.ORIENTATION_LANDSCAPE);
            notifyFullScreenChanged(true);
        } else {
            updateOrientationVisibility(newConfig.orientation);
        }
    }

    private void updateOrientationVisibility(int orientation) {
        boolean isLandscape = (orientation == Configuration.ORIENTATION_LANDSCAPE);
        int visibility = (isLandscape || isFullScreen) ? View.GONE : View.VISIBLE;
        if (appHeader != null) appHeader.setVisibility(visibility);
        if (headerDivider != null) headerDivider.setVisibility(visibility);
        if (bottomDivider != null) bottomDivider.setVisibility(visibility);
        if (bottomNav != null) bottomNav.setVisibility(visibility);
    }

    private void switchFragment(Fragment fragment) {
        if (isFullScreen) {
            setFullScreen(false);
        }
        getSupportFragmentManager().beginTransaction()
                .replace(R.id.fragment_container, fragment)
                .commit();
    }

    private void checkPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            String[] permissions = new String[]{
                    Manifest.permission.INTERNET,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE,
                    Manifest.permission.READ_EXTERNAL_STORAGE
            };

            boolean hasAll = true;
            for (String p : permissions) {
                if (ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED) {
                    hasAll = false;
                    break;
                }
            }

            if (!hasAll) {
                ActivityCompat.requestPermissions(this, permissions, 100);
            }
        }
    }

    public static String getAppVersionName(android.content.Context context) {
        if (context == null) return "0.1.5";
        try {
            return context.getPackageManager().getPackageInfo(context.getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "0.1.5";
        }
    }

    private void showAboutAndLogDialog(String verText) {
        new androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("关于 WeViewCam")
                .setMessage("WeViewCam 移动监控平台客户端\n版本: " + verText +
                        "\n构建: Android Edition (arm64-v8a / armeabi-v7a)" +
                        "\n日志文件: Android/data/com.weviewcam.client/files/app.log" +
                        "\n支持: 多画面实时预览 / 远程录像回放 / 设备配置备份")
                .setPositiveButton("确定", null)
                .setNeutralButton("查看运行日志", (dialog, which) -> showLogViewerDialog())
                .show();
    }

    private void showLogViewerDialog() {
        java.io.File logFile = com.weviewcam.client.core.logger.AppLogger.getLogFile();
        StringBuilder logContent = new StringBuilder();
        if (logFile != null && logFile.exists()) {
            try (java.io.BufferedReader br = new java.io.BufferedReader(new java.io.InputStreamReader(new java.io.FileInputStream(logFile), java.nio.charset.StandardCharsets.UTF_8))) {
                java.util.List<String> lines = new java.util.ArrayList<>();
                String line;
                while ((line = br.readLine()) != null) {
                    lines.add(line);
                }
                int start = Math.max(0, lines.size() - 300);
                for (int i = start; i < lines.size(); i++) {
                    logContent.append(lines.get(i)).append("\n");
                }
            } catch (Exception e) {
                logContent.append("读取日志失败: ").append(e.getMessage());
            }
        } else {
            logContent.append("暂无本地运行日志文件。");
        }

        android.widget.ScrollView scrollView = new android.widget.ScrollView(this);
        android.widget.TextView textView = new android.widget.TextView(this);
        textView.setText(logContent.toString());
        textView.setTextSize(11);
        textView.setTypeface(android.graphics.Typeface.MONOSPACE);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        textView.setPadding(pad, pad, pad, pad);
        textView.setTextIsSelectable(true);
        scrollView.addView(textView);

        new androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("应用运行日志 (最近 300 行)")
                .setView(scrollView)
                .setPositiveButton("关闭", null)
                .setNegativeButton("抓取底层Logcat", (d, w) -> {
                    String systemLogs = com.weviewcam.client.core.logger.AppLogger.dumpSystemLogcat();
                    textView.setText(systemLogs);
                    android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(android.content.Context.CLIPBOARD_SERVICE);
                    if (cm != null) {
                        android.content.ClipData clip = android.content.ClipData.newPlainText("WeViewCam System Logcat", systemLogs);
                        cm.setPrimaryClip(clip);
                        android.widget.Toast.makeText(this, "底层系统 Logcat 已抓取并复制到剪贴板！", android.widget.Toast.LENGTH_LONG).show();
                    }
                })
                .setNeutralButton("复制日志", (d, w) -> {
                    android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(android.content.Context.CLIPBOARD_SERVICE);
                    if (cm != null) {
                        android.content.ClipData clip = android.content.ClipData.newPlainText("WeViewCam Log", textView.getText());
                        cm.setPrimaryClip(clip);
                        android.widget.Toast.makeText(this, "日志已复制到剪贴板", android.widget.Toast.LENGTH_SHORT).show();
                    }
                })
                .show();
    }
}

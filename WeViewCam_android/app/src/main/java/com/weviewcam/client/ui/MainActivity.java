package com.weviewcam.client.ui;

import android.Manifest;
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
        setContentView(R.layout.activity_main);

        appHeader = findViewById(R.id.app_header);
        headerDivider = findViewById(R.id.header_divider);
        bottomDivider = findViewById(R.id.bottom_divider);
        bottomNav = findViewById(R.id.bottom_navigation);

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
}

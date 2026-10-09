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

public class MainActivity extends AppCompatActivity {

    private LiveViewFragment liveViewFragment;
    private PlaybackFragment playbackFragment;
    private DeviceManagementFragment deviceManagementFragment;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Pre-initialize DeviceManager
        DeviceManager.getInstance(this);

        checkPermissions();

        liveViewFragment = new LiveViewFragment();
        playbackFragment = new PlaybackFragment();
        deviceManagementFragment = new DeviceManagementFragment();

        // Default to Live View
        switchFragment(liveViewFragment);

        BottomNavigationView bottomNav = findViewById(R.id.bottom_navigation);
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

    private void switchFragment(Fragment fragment) {
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

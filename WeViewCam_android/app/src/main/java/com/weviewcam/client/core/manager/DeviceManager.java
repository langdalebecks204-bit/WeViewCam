package com.weviewcam.client.core.manager;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.adapter.DeviceAdapterFactory;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.ProtocolType;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.lang.reflect.Type;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class DeviceManager {
    private static final String MODULE = "DeviceManager";
    private static final String CONFIG_FILE_NAME = "devices.json";

    private static volatile DeviceManager instance;
    private final Context context;
    private final List<DeviceInfo> devices = new ArrayList<>();
    private final Gson gson;
    private final ExecutorService executor = Executors.newCachedThreadPool();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    public interface OnTestConnectionListener {
        void onResult(boolean success, String message, List<ChannelInfo> channels);
    }

    public static synchronized DeviceManager getInstance(Context context) {
        if (instance == null) {
            instance = new DeviceManager(context.getApplicationContext());
        }
        return instance;
    }

    public static DeviceManager getInstance() {
        return instance;
    }

    private DeviceManager(Context context) {
        this.context = context;
        this.gson = new GsonBuilder().setPrettyPrinting().create();
        loadDevices();
    }

    public synchronized List<DeviceInfo> getDevices() {
        return new ArrayList<>(devices);
    }

    public synchronized DeviceInfo getDevice(String deviceId) {
        if (deviceId == null) return null;
        for (DeviceInfo dev : devices) {
            if (deviceId.equals(dev.getDeviceId())) {
                return dev;
            }
        }
        return null;
    }

    public synchronized void addDevice(DeviceInfo device) {
        if (device == null) return;
        devices.add(device);
        saveDevices();
    }

    public synchronized boolean updateDevice(DeviceInfo device) {
        if (device == null) return false;
        for (int i = 0; i < devices.size(); i++) {
            if (devices.get(i).getDeviceId().equals(device.getDeviceId())) {
                devices.set(i, device);
                saveDevices();
                return true;
            }
        }
        return false;
    }

    public synchronized boolean deleteDevice(String deviceId) {
        if (deviceId == null) return false;
        boolean removed = devices.removeIf(d -> deviceId.equals(d.getDeviceId()));
        if (removed) {
            saveDevices();
        }
        return removed;
    }

    public synchronized void saveDevices() {
        try {
            File file = new File(context.getFilesDir(), CONFIG_FILE_NAME);
            try (FileOutputStream fos = new FileOutputStream(file);
                 OutputStreamWriter writer = new OutputStreamWriter(fos, StandardCharsets.UTF_8)) {
                gson.toJson(devices, writer);
            }
            AppLogger.i(MODULE, "已持久化监控设备配置: " + file.getAbsolutePath() + " (数量: " + devices.size() + ")");
        } catch (Exception e) {
            AppLogger.e(MODULE, "保存设备配置失败", e);
        }
    }

    private synchronized void loadDevices() {
        devices.clear();
        File file = new File(context.getFilesDir(), CONFIG_FILE_NAME);
        if (file.exists() && file.length() > 0) {
            try (FileInputStream fis = new FileInputStream(file);
                 InputStreamReader reader = new InputStreamReader(fis, StandardCharsets.UTF_8)) {
                Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
                List<DeviceInfo> loaded = gson.fromJson(reader, listType);
                if (loaded != null && !loaded.isEmpty()) {
                    devices.addAll(loaded);
                    AppLogger.i(MODULE, "成功载入监控设备配置，数量: " + devices.size());
                    return;
                }
            } catch (Exception e) {
                AppLogger.w(MODULE, "读取现有设备配置出错，将重建默认配置: " + e.getMessage());
            }
        }

        // Initialize default configuration matching Ubuntu version
        initDefaultDevices();
        saveDevices();
    }

    private void initDefaultDevices() {
        DeviceInfo demoDev = new DeviceInfo(
                "hik_demo_01",
                "海康威视演示设备",
                "192.168.1.64",
                8000,
                "admin",
                "",
                ProtocolType.HIKVISION
        );

        List<ChannelInfo> channels = new ArrayList<>();
        channels.add(new ChannelInfo(1, "通道 1 - 主大门球机", true, true, demoDev.getDeviceId()));
        channels.add(new ChannelInfo(2, "通道 2 - 停车场出入口", true, false, demoDev.getDeviceId()));
        channels.add(new ChannelInfo(3, "通道 3 - 办公大楼大厅", true, false, demoDev.getDeviceId()));
        channels.add(new ChannelInfo(4, "通道 4 - 园区周界围栏", true, false, demoDev.getDeviceId()));

        demoDev.setChannels(channels);
        devices.add(demoDev);
    }

    /**
     * Async test connection method
     */
    public void testConnection(DeviceInfo device, OnTestConnectionListener listener) {
        executor.execute(() -> {
            BaseDeviceAdapter adapter = DeviceAdapterFactory.createAdapter(device);
            boolean loginOk = adapter.login();
            final List<ChannelInfo> finalChannels = new ArrayList<>();
            final String finalMsg;

            if (loginOk) {
                List<ChannelInfo> chs = adapter.getChannels();
                if (chs == null || chs.isEmpty()) {
                    chs = new ArrayList<>();
                    chs.add(new ChannelInfo(1, "通道 1", true, false, device.getDeviceId()));
                }
                finalChannels.addAll(chs);
                device.setConnected(true);
                device.setChannels(finalChannels);
                updateDevice(device);
                saveDevices();
                finalMsg = "连接成功！已获取 " + finalChannels.size() + " 个视频通道。";
                adapter.logout();
                device.setConnected(true);
                saveDevices();
            } else {
                device.setConnected(false);
                updateDevice(device);
                saveDevices();
                finalMsg = "连接失败，请检查 IP 地址、端口或凭据。";
            }

            mainHandler.post(() -> {
                if (listener != null) {
                    listener.onResult(loginOk, finalMsg, finalChannels);
                }
            });
        });
    }
}

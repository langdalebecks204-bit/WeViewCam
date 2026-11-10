package com.weviewcam.client.core.manager;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
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
import java.util.HashMap;
import java.util.List;
import java.util.Map;
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

    public interface OnDeviceChangeListener {
        void onDeviceChanged();
    }
    private final List<OnDeviceChangeListener> changeListeners = new java.util.concurrent.CopyOnWriteArrayList<>();

    public void addOnDeviceChangeListener(OnDeviceChangeListener listener) {
        if (listener != null && !changeListeners.contains(listener)) {
            changeListeners.add(listener);
        }
    }

    public void removeOnDeviceChangeListener(OnDeviceChangeListener listener) {
        changeListeners.remove(listener);
    }

    private void notifyDeviceChanged() {
        mainHandler.post(() -> {
            for (OnDeviceChangeListener listener : changeListeners) {
                try {
                    listener.onDeviceChanged();
                } catch (Exception ignored) {}
            }
        });
    }

    private final Handler autoRefreshHandler = new Handler(Looper.getMainLooper());
    private Runnable autoRefreshRunnable;
    private int refreshIntervalSec = 60; // 0 = disabled

    private void initAutoRefresh() {
        android.content.SharedPreferences sp = context.getSharedPreferences("weviewcam_prefs", Context.MODE_PRIVATE);
        refreshIntervalSec = sp.getInt("key_channel_refresh_interval", 60);
        autoRefreshRunnable = new Runnable() {
            @Override
            public void run() {
                refreshAllDevicesStatus(null);
                if (refreshIntervalSec > 0) {
                    autoRefreshHandler.postDelayed(this, refreshIntervalSec * 1000L);
                }
            }
        };
        applyAutoRefreshInterval();
    }

    public int getRefreshIntervalSec() {
        return refreshIntervalSec;
    }

    public void setRefreshIntervalSec(int sec) {
        this.refreshIntervalSec = sec;
        android.content.SharedPreferences sp = context.getSharedPreferences("weviewcam_prefs", Context.MODE_PRIVATE);
        sp.edit().putInt("key_channel_refresh_interval", sec).apply();
        applyAutoRefreshInterval();
    }

    private void applyAutoRefreshInterval() {
        autoRefreshHandler.removeCallbacks(autoRefreshRunnable);
        if (refreshIntervalSec > 0) {
            autoRefreshHandler.postDelayed(autoRefreshRunnable, refreshIntervalSec * 1000L);
        }
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
        // 保持按需连接，避免启动阶段后台突发并发网络请求与资源竞争
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

    public synchronized String exportDevicesJson() {
        return exportDevicesJson(devices);
    }

    public synchronized String exportDevicesJson(List<DeviceInfo> targetDevices) {
        if (targetDevices == null) {
            return "[]";
        }
        return gson.toJson(targetDevices);
    }

    public List<DeviceInfo> parseDevicesJson(String jsonString) {
        if (jsonString == null || jsonString.trim().isEmpty()) {
            return new ArrayList<>();
        }
        try {
            JsonElement element = JsonParser.parseString(jsonString);
            Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
            if (element.isJsonArray()) {
                return gson.fromJson(element, listType);
            } else if (element.isJsonObject()) {
                JsonObject obj = element.getAsJsonObject();
                if (obj.has("devices") && obj.get("devices").isJsonArray()) {
                    return gson.fromJson(obj.get("devices"), listType);
                }
            }
        } catch (Exception e) {
            AppLogger.e(MODULE, "解析设备备份 JSON 失败: " + e.getMessage());
        }
        return new ArrayList<>();
    }

    public synchronized int importDevices(List<DeviceInfo> newDevices, boolean overwriteAll) {
        if (newDevices == null || newDevices.isEmpty()) {
            return 0;
        }

        if (overwriteAll) {
            devices.clear();
            devices.addAll(newDevices);
            saveDevices();
            return newDevices.size();
        }

        int count = 0;
        for (DeviceInfo newDev : newDevices) {
            if (newDev == null) continue;
            boolean updated = false;
            for (int i = 0; i < devices.size(); i++) {
                DeviceInfo existing = devices.get(i);
                if ((newDev.getDeviceId() != null && newDev.getDeviceId().equals(existing.getDeviceId()))
                        || (newDev.getIp() != null && newDev.getIp().equals(existing.getIp()) && newDev.getPort() == existing.getPort())) {
                    newDev.setDeviceId(existing.getDeviceId());

                    if (newDev.getChannels() == null || newDev.getChannels().isEmpty()) {
                        // Imported device does not contain channel details, preserve existing channels
                        newDev.setChannels(existing.getChannels());
                    } else if (existing.getChannels() != null && !existing.getChannels().isEmpty()) {
                        // Merge backup channel details (custom names, enabled state) into existing device channels
                        Map<Integer, ChannelInfo> backupChannelMap = new HashMap<>();
                        for (ChannelInfo ch : newDev.getChannels()) {
                            ch.setDeviceId(existing.getDeviceId());
                            backupChannelMap.put(ch.getChannelNo(), ch);
                        }

                        for (ChannelInfo existCh : existing.getChannels()) {
                            ChannelInfo bakCh = backupChannelMap.remove(existCh.getChannelNo());
                            if (bakCh != null) {
                                if (bakCh.getName() != null && !bakCh.getName().trim().isEmpty()) {
                                    existCh.setName(bakCh.getName());
                                }
                                existCh.setEnabled(bakCh.isEnabled());
                                existCh.setPtz(bakCh.isPtz());
                            }
                        }

                        // Add any new channels declared in backup that were not present locally
                        for (ChannelInfo addedCh : backupChannelMap.values()) {
                            existing.getChannels().add(addedCh);
                        }

                        newDev.setChannels(existing.getChannels());
                    } else {
                        for (ChannelInfo ch : newDev.getChannels()) {
                            ch.setDeviceId(existing.getDeviceId());
                        }
                    }

                    devices.set(i, newDev);
                    updated = true;
                    count++;
                    break;
                }
            }
            if (!updated) {
                devices.add(newDev);
                count++;
            }
        }

        saveDevices();
        return count;
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
        AppLogger.i(MODULE, "[TEST_CONN 0] 收到设备连接测试请求: " + (device != null ? device.getName() + " (" + device.getIp() + ":" + device.getPort() + ", 协议=" + device.getProtocol() + ")" : "null"));
        executor.execute(() -> {
            AppLogger.i(MODULE, "[TEST_CONN 1] 进入后台测试任务线程...");
            boolean loginOk = false;
            final List<ChannelInfo> finalChannels = new ArrayList<>();
            String msg = "连接失败";
            try {
                AppLogger.i(MODULE, "[TEST_CONN 2] 准备通过工厂构建适配器...");
                BaseDeviceAdapter adapter = DeviceAdapterFactory.createAdapter(device);
                AppLogger.i(MODULE, "[TEST_CONN 3] 适配器创建成功: " + adapter.getClass().getSimpleName() + "，准备执行 adapter.login()...");
                loginOk = adapter.login();
                AppLogger.i(MODULE, "[TEST_CONN 4] adapter.login() 返回结果: " + loginOk);

                if (loginOk) {
                    AppLogger.i(MODULE, "[TEST_CONN 5] 登录成功，准备探测通道...");
                    List<ChannelInfo> chs = adapter.getChannels();
                    AppLogger.i(MODULE, "[TEST_CONN 5.1] 通道探测结果数量: " + (chs != null ? chs.size() : 0));
                    if (chs == null || chs.isEmpty()) {
                        chs = new ArrayList<>();
                        chs.add(new ChannelInfo(1, "通道 1", true, false, device.getDeviceId()));
                    }
                    
                    // Preserve existing custom names and enabled/disabled preferences
                    Map<Integer, ChannelInfo> existingMap = new HashMap<>();
                    if (device.getChannels() != null) {
                        for (ChannelInfo oldCh : device.getChannels()) {
                            existingMap.put(oldCh.getChannelNo(), oldCh);
                        }
                    }
                    for (ChannelInfo newCh : chs) {
                        ChannelInfo oldCh = existingMap.get(newCh.getChannelNo());
                        if (oldCh != null) {
                            if (oldCh.getName() != null && !oldCh.getName().trim().isEmpty()) {
                                newCh.setName(oldCh.getName());
                            }
                            newCh.setEnabled(oldCh.isEnabled());
                        }
                    }

                    finalChannels.addAll(chs);
                    device.setConnected(true);
                    device.setChannels(finalChannels);
                    updateDevice(device);
                    saveDevices();
                    msg = "连接成功！已获取 " + finalChannels.size() + " 个视频通道。";
                    try {
                        adapter.logout();
                    } catch (Throwable ignored) {}
                    device.setConnected(true);
                    saveDevices();
                } else {
                    device.setConnected(false);
                    updateDevice(device);
                    saveDevices();
                    msg = "连接失败，请检查 IP 地址、端口或凭据。";
                }
            } catch (Throwable t) {
                AppLogger.e(MODULE, "测试设备连接发生未捕获异常: " + t.getMessage(), t);
                msg = "测试连接异常: " + t.getMessage();
                device.setConnected(false);
            }

            final String finalMsg = msg;
            final boolean finalLoginOk = loginOk;
            mainHandler.post(() -> {
                if (listener != null) {
                    listener.onResult(finalLoginOk, finalMsg, finalChannels);
                }
            });
        });
    }

    public void refreshAllDevicesStatus(Runnable onComplete) {
        executor.execute(() -> {
            List<DeviceInfo> current = getDevices();
            if (current.isEmpty()) {
                if (onComplete != null) {
                    mainHandler.post(onComplete);
                }
                return;
            }

            java.util.concurrent.CountDownLatch latch = new java.util.concurrent.CountDownLatch(current.size());
            for (DeviceInfo dev : current) {
                executor.execute(() -> {
                    try {
                        BaseDeviceAdapter adapter = DeviceAdapterFactory.createAdapter(dev);
                        boolean ok = adapter.login();
                        if (ok) {
                            List<ChannelInfo> chs = adapter.getChannels();
                            if (chs != null && !chs.isEmpty()) {
                                Map<Integer, ChannelInfo> existingMap = new HashMap<>();
                                if (dev.getChannels() != null) {
                                    for (ChannelInfo oldCh : dev.getChannels()) {
                                        existingMap.put(oldCh.getChannelNo(), oldCh);
                                    }
                                }
                                for (ChannelInfo newCh : chs) {
                                    ChannelInfo oldCh = existingMap.get(newCh.getChannelNo());
                                    if (oldCh != null) {
                                        if (oldCh.getName() != null && !oldCh.getName().trim().isEmpty()) {
                                            newCh.setName(oldCh.getName());
                                        }
                                        newCh.setEnabled(oldCh.isEnabled());
                                    }
                                }
                                dev.setChannels(chs);
                            }
                            dev.setConnected(true);
                            adapter.logout();
                        } else {
                            dev.setConnected(false);
                            if (dev.getChannels() != null) {
                                for (ChannelInfo ch : dev.getChannels()) {
                                    ch.setOnline(false);
                                }
                            }
                        }
                    } catch (Throwable e) {
                        AppLogger.e(MODULE, "刷新设备状态异常: " + dev.getName() + ", " + e.getMessage());
                        dev.setConnected(false);
                    } finally {
                        latch.countDown();
                    }
                });
            }

            try {
                latch.await(10, java.util.concurrent.TimeUnit.SECONDS);
            } catch (InterruptedException ignored) {}

            saveDevices();
            notifyDeviceChanged();

            if (onComplete != null) {
                mainHandler.post(onComplete);
            }
        });
    }

    public synchronized void updateDeviceChannels(String deviceId, List<ChannelInfo> channels) {
        DeviceInfo dev = getDevice(deviceId);
        if (dev != null) {
            dev.setChannels(channels);
            updateDevice(dev);
            saveDevices();
        }
    }
}

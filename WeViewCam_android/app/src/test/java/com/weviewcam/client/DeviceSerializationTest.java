package com.weviewcam.client;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.ProtocolType;

import org.junit.Assert;
import org.junit.Test;

import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.List;

public class DeviceSerializationTest {

    @Test
    public void testExportGeneratesSnakeCase() {
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        DeviceInfo dev = new DeviceInfo("test_01", "门禁摄像头", "192.168.1.50", 8000, "admin", "pass", ProtocolType.HIKVISION);
        dev.setRtspPort(554);
        List<ChannelInfo> channels = new ArrayList<>();
        channels.add(new ChannelInfo(1, "通道 1", true, true, "test_01"));
        dev.setChannels(channels);

        List<DeviceInfo> list = new ArrayList<>();
        list.add(dev);

        String json = gson.toJson(list);
        Assert.assertTrue("Should contain device_id", json.contains("\"device_id\": \"test_01\""));
        Assert.assertTrue("Should contain rtsp_port", json.contains("\"rtsp_port\": 554"));
        Assert.assertTrue("Should contain channel_no", json.contains("\"channel_no\": 1"));
        Assert.assertTrue("Should contain is_online", json.contains("\"is_online\": true"));
        Assert.assertTrue("Should contain is_ptz", json.contains("\"is_ptz\": true"));
        Assert.assertTrue("Should contain protocol", json.contains("\"protocol\": \"hikvision\""));
    }

    @Test
    public void testImportParsesUbuntuSnakeCaseJson() {
        String ubuntuJson = "[\n" +
                "  {\n" +
                "    \"device_id\": \"ubuntu_hik_01\",\n" +
                "    \"name\": \"海康演示设备\",\n" +
                "    \"ip\": \"192.168.1.64\",\n" +
                "    \"port\": 8000,\n" +
                "    \"username\": \"admin\",\n" +
                "    \"password\": \"12345\",\n" +
                "    \"protocol\": \"hikvision\",\n" +
                "    \"rtsp_port\": 554,\n" +
                "    \"channels\": [\n" +
                "      {\n" +
                "        \"channel_no\": 1,\n" +
                "        \"name\": \"通道 1 - 主大门球机\",\n" +
                "        \"is_online\": true,\n" +
                "        \"is_ptz\": true,\n" +
                "        \"device_id\": \"ubuntu_hik_01\"\n" +
                "      }\n" +
                "    ]\n" +
                "  }\n" +
                "]";

        Gson gson = new GsonBuilder().create();
        Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
        List<DeviceInfo> list = gson.fromJson(ubuntuJson, listType);

        Assert.assertNotNull(list);
        Assert.assertEquals(1, list.size());
        DeviceInfo dev = list.get(0);
        Assert.assertEquals("ubuntu_hik_01", dev.getDeviceId());
        Assert.assertEquals("海康演示设备", dev.getName());
        Assert.assertEquals(554, dev.getRtspPort());
        Assert.assertEquals(ProtocolType.HIKVISION, dev.getProtocol());
        Assert.assertEquals(1, dev.getChannels().size());
        ChannelInfo ch = dev.getChannels().get(0);
        Assert.assertEquals(1, ch.getChannelNo());
        Assert.assertTrue(ch.isPtz());
        Assert.assertTrue(ch.isOnline());
    }

    @Test
    public void testImportParsesLegacyCamelCaseJson() {
        String legacyJson = "[\n" +
                "  {\n" +
                "    \"deviceId\": \"legacy_01\",\n" +
                "    \"name\": \"老版本设备\",\n" +
                "    \"ip\": \"192.168.1.99\",\n" +
                "    \"port\": 8000,\n" +
                "    \"username\": \"admin\",\n" +
                "    \"password\": \"\",\n" +
                "    \"protocol\": \"HIKVISION\",\n" +
                "    \"rtspPort\": 554,\n" +
                "    \"channels\": [\n" +
                "      {\n" +
                "        \"channelNo\": 2,\n" +
                "        \"name\": \"通道 2\",\n" +
                "        \"isOnline\": true,\n" +
                "        \"isPtz\": false,\n" +
                "        \"deviceId\": \"legacy_01\"\n" +
                "      }\n" +
                "    ]\n" +
                "  }\n" +
                "]";

        Gson gson = new GsonBuilder().create();
        Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
        List<DeviceInfo> list = gson.fromJson(legacyJson, listType);

        Assert.assertNotNull(list);
        Assert.assertEquals(1, list.size());
        DeviceInfo dev = list.get(0);
        Assert.assertEquals("legacy_01", dev.getDeviceId());
        Assert.assertEquals(554, dev.getRtspPort());
        Assert.assertEquals(2, dev.getChannels().get(0).getChannelNo());
        // Default when omitted in json should be enabled
        Assert.assertTrue(dev.getChannels().get(0).isEnabled());
    }

    @Test
    public void testChannelEnabledAndCustomNameSerialization() {
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        DeviceInfo dev = new DeviceInfo("nvr_01", "8路NVR", "192.168.1.100", 8000, "admin", "123", ProtocolType.HIKVISION);
        List<ChannelInfo> channels = new ArrayList<>();
        channels.add(new ChannelInfo(1, "自定义大门通道", true, false, "nvr_01", true));
        channels.add(new ChannelInfo(2, "通道 2 (已停用)", false, false, "nvr_01", false));
        channels.add(new ChannelInfo(3, "仓库东侧监控", true, true, "nvr_01", true));
        dev.setChannels(channels);

        // Verify getEnabledChannels
        List<ChannelInfo> enabledOnly = dev.getEnabledChannels();
        Assert.assertEquals(2, enabledOnly.size());
        Assert.assertEquals("自定义大门通道", enabledOnly.get(0).getName());
        Assert.assertEquals(1, enabledOnly.get(0).getChannelNo());
        Assert.assertEquals("仓库东侧监控", enabledOnly.get(1).getName());
        Assert.assertEquals(3, enabledOnly.get(1).getChannelNo());

        String json = gson.toJson(dev);
        Assert.assertTrue(json.contains("\"is_enabled\": false"));
        Assert.assertTrue(json.contains("\"name\": \"自定义大门通道\""));

        DeviceInfo restored = gson.fromJson(json, DeviceInfo.class);
        Assert.assertEquals(3, restored.getChannels().size());
        Assert.assertTrue(restored.getChannels().get(0).isEnabled());
        Assert.assertFalse(restored.getChannels().get(1).isEnabled());
        Assert.assertTrue(restored.getChannels().get(2).isEnabled());
        Assert.assertEquals(2, restored.getEnabledChannels().size());
    }

    @Test
    public void testBackupChannelMergePreservesCustomNamesAndEnabledState() {
        // Simulating existing device in DeviceManager
        DeviceInfo existing = new DeviceInfo("dev_merge", "现有设备", "192.168.1.80", 8000, "admin", "123", ProtocolType.HIKVISION);
        List<ChannelInfo> existingChannels = new ArrayList<>();
        existingChannels.add(new ChannelInfo(1, "通道 1", true, false, "dev_merge", true));
        existingChannels.add(new ChannelInfo(2, "通道 2", true, false, "dev_merge", true));
        existingChannels.add(new ChannelInfo(3, "通道 3", false, false, "dev_merge", true));
        existing.setChannels(existingChannels);

        // Backup has renamed channel 1, disabled channel 2, and added custom channel 4
        String backupJson = "[\n" +
                "  {\n" +
                "    \"device_id\": \"dev_merge\",\n" +
                "    \"name\": \"现有设备 (更新)\",\n" +
                "    \"ip\": \"192.168.1.80\",\n" +
                "    \"port\": 8000,\n" +
                "    \"username\": \"admin\",\n" +
                "    \"password\": \"123\",\n" +
                "    \"protocol\": \"hikvision\",\n" +
                "    \"channels\": [\n" +
                "      {\n" +
                "        \"channel_no\": 1,\n" +
                "        \"name\": \"正门高空全景\",\n" +
                "        \"is_enabled\": true\n" +
                "      },\n" +
                "      {\n" +
                "        \"channel_no\": 2,\n" +
                "        \"name\": \"仓库走廊(已禁用)\",\n" +
                "        \"is_enabled\": false\n" +
                "      },\n" +
                "      {\n" +
                "        \"channel_no\": 4,\n" +
                "        \"name\": \"新加通道4\",\n" +
                "        \"is_enabled\": true\n" +
                "      }\n" +
                "    ]\n" +
                "  }\n" +
                "]";

        Gson gson = new GsonBuilder().create();
        Type listType = new TypeToken<List<DeviceInfo>>() {}.getType();
        List<DeviceInfo> importedList = gson.fromJson(backupJson, listType);
        DeviceInfo newDev = importedList.get(0);

        // Perform merge logic
        java.util.Map<Integer, ChannelInfo> backupChannelMap = new java.util.HashMap<>();
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

        for (ChannelInfo addedCh : backupChannelMap.values()) {
            existing.getChannels().add(addedCh);
        }

        Assert.assertEquals(4, existing.getChannels().size());
        // Channel 1: name updated to 正门高空全景, enabled=true
        Assert.assertEquals("正门高空全景", existing.getChannels().get(0).getName());
        Assert.assertTrue(existing.getChannels().get(0).isEnabled());
        // Channel 2: name updated to 仓库走廊(已禁用), enabled=false
        Assert.assertEquals("仓库走廊(已禁用)", existing.getChannels().get(1).getName());
        Assert.assertFalse(existing.getChannels().get(1).isEnabled());
        // Channel 3: not in backup, preserved intact
        Assert.assertEquals("通道 3", existing.getChannels().get(2).getName());
        Assert.assertTrue(existing.getChannels().get(2).isEnabled());
        // Channel 4: added
        Assert.assertEquals("新加通道4", existing.getChannels().get(3).getName());
        Assert.assertTrue(existing.getChannels().get(3).isEnabled());
    }
}

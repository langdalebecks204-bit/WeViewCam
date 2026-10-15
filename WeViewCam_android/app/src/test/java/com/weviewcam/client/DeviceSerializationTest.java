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
    }
}

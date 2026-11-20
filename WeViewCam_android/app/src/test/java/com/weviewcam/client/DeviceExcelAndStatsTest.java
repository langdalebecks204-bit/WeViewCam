package com.weviewcam.client;

import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.ProtocolType;
import com.weviewcam.client.core.util.DeviceExcelHelper;
import com.weviewcam.client.core.util.StreamStatsTracker;

import org.junit.Test;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.List;

import static org.junit.Assert.*;

public class DeviceExcelAndStatsTest {
    @Test
    public void testXlsxTemplateRoundTrip() throws Exception {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        DeviceExcelHelper.generateTemplateXlsx(baos);
        byte[] xlsxBytes = baos.toByteArray();
        assertTrue(xlsxBytes.length > 200);
        assertEquals('P', xlsxBytes[0]);
        assertEquals('K', xlsxBytes[1]);

        DeviceExcelHelper.ImportResult res = DeviceExcelHelper.importFromStream(new ByteArrayInputStream(xlsxBytes));
        List<DeviceInfo> devs = res.devices;
        assertEquals(3, devs.size());
        assertEquals("192.168.1.100", devs.get(0).getIp());
        assertEquals(ProtocolType.HIKVISION, devs.get(0).getProtocol());
        assertEquals(2, devs.get(0).getChannels().size());
        assertEquals("192.168.1.101", devs.get(1).getIp());
        assertEquals(ProtocolType.DAHUA, devs.get(1).getProtocol());
        assertEquals("192.168.1.102", devs.get(2).getIp());
        assertEquals(ProtocolType.ONVIF, devs.get(2).getProtocol());
    }

    @Test
    public void testCsvExportAndImportRoundTrip() throws Exception {
        ByteArrayOutputStream xlsxOut = new ByteArrayOutputStream();
        DeviceExcelHelper.generateTemplateXlsx(xlsxOut);
        List<DeviceInfo> devs = DeviceExcelHelper.importFromStream(new ByteArrayInputStream(xlsxOut.toByteArray())).devices;

        ByteArrayOutputStream csvOut = new ByteArrayOutputStream();
        DeviceExcelHelper.exportDevicesToCsv(devs, csvOut);
        List<DeviceInfo> reimported = DeviceExcelHelper.importFromStream(new ByteArrayInputStream(csvOut.toByteArray())).devices;
        assertEquals(3, reimported.size());
    }

    @Test
    public void testPsPackHeaderCounting() {
        byte[] data = new byte[]{
                0x00, 0x00, 0x01, (byte) 0xBA, 0x44, 0x00,
                0x00, 0x00, 0x01, (byte) 0xE0, 0x11, 0x22,
                0x00, 0x00, 0x01, (byte) 0xBA, 0x44, 0x00
        };
        assertEquals(2, StreamStatsTracker.countPsPackHeaders(data, data.length));
    }

    @Test
    public void testLocalRtspProxySanitizesEmptyFmtp() {
        String headers = "RTSP/1.0 200 OK\r\nCSeq: 2\r\nContent-Base: rtsp://10.0.25.201/h264ESVideoTest/\r\nContent-Type: application/sdp\r\nContent-Length: 92\r\n\r\n";
        String sdp = "v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\na=fmtp:96 \r\na=control:track1\r\n";
        byte[] out = com.weviewcam.client.adapters.onvif.LocalRtspProxy.sanitizeRtspResponse(
                headers, sdp.getBytes(), "10.0.25.201", 554, 45678);
        String outStr = new String(out);
        assertTrue(outStr.contains("a=fmtp:96 packetization-mode=1;profile-level-id=42001e;sprop-parameter-sets="));
        assertTrue(outStr.contains("Content-Base: rtsp://127.0.0.1:45678/h264ESVideoTest/"));
    }
}

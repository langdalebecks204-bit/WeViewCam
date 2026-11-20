package com.weviewcam.client.core.util;

import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.ProtocolType;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilderFactory;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

/**
 * Zero-dependency Excel (.xlsx) and CSV (.csv) import/export helper for Android.
 * Produces and parses standard OOXML (.xlsx) compatible with WeViewCam Desktop,
 * Microsoft Excel, WPS Office, and openpyxl without adding heavy third-party JARs.
 */
public class DeviceExcelHelper {

    public static final String[] TEMPLATE_HEADERS = {
            "设备名称*",
            "设备IP*",
            "管理端口",
            "协议类型",
            "登录账号*",
            "登录密码*",
            "通道号(选填)",
            "通道名称(选填)",
            "是否启用",
            "RTSP端口(选填)"
    };

    private static final String[][] TEMPLATE_SAMPLE_ROWS = {
            {"示例1: 办公楼海康NVR", "192.168.1.100", "8000", "hikvision", "admin", "Abc12345", "1", "1楼正门大堂", "是", "554"},
            {"示例1: 办公楼海康NVR", "192.168.1.100", "8000", "hikvision", "admin", "Abc12345", "2", "2楼东侧走廊", "是", "554"},
            {"示例2: 仓库大华NVR(整机导入/免填通道)", "192.168.1.101", "37777", "dahua", "admin", "Admin@888", "", "", "", "554"},
            {"示例3: 独立ONVIF摄像头", "192.168.1.102", "80", "onvif", "admin", "Admin123", "1", "地库西入口", "是", "554"}
    };

    public static class ImportResult {
        public final List<DeviceInfo> devices = new ArrayList<>();
        public final List<String> errors = new ArrayList<>();
    }

    public static void generateTemplateXlsx(OutputStream os) throws IOException {
        List<String[]> rows = new ArrayList<>();
        rows.add(TEMPLATE_HEADERS);
        rows.addAll(Arrays.asList(TEMPLATE_SAMPLE_ROWS));
        writeXlsxRows("设备导入模板", rows, os);
    }

    public static void exportDevicesToXlsx(List<DeviceInfo> devices, OutputStream os) throws IOException {
        List<String[]> rows = buildExportRows(devices);
        writeXlsxRows("设备列表", rows, os);
    }

    public static void exportDevicesToCsv(List<DeviceInfo> devices, OutputStream os) throws IOException {
        List<String[]> rows = buildExportRows(devices);
        // UTF-8 BOM for Excel compatibility
        os.write(new byte[]{(byte) 0xEF, (byte) 0xBB, (byte) 0xBF});
        StringBuilder sb = new StringBuilder();
        for (String[] row : rows) {
            for (int i = 0; i < row.length; i++) {
                if (i > 0) sb.append(',');
                sb.append(escapeCsv(row[i] != null ? row[i] : ""));
            }
            sb.append("\r\n");
        }
        os.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        os.flush();
    }

    private static List<String[]> buildExportRows(List<DeviceInfo> devices) {
        List<String[]> rows = new ArrayList<>();
        rows.add(TEMPLATE_HEADERS);
        if (devices == null) return rows;

        for (DeviceInfo dev : devices) {
            if (dev == null) continue;
            String proto = dev.getProtocol() != null ? dev.getProtocol().getValue() : "hikvision";
            List<ChannelInfo> channels = dev.getChannels();
            if (channels == null || channels.isEmpty()) {
                rows.add(new String[]{
                        safe(dev.getName()),
                        safe(dev.getIp()),
                        String.valueOf(dev.getPort()),
                        proto,
                        safe(dev.getUsername()),
                        safe(dev.getPassword()),
                        "",
                        "",
                        "是",
                        String.valueOf(dev.getRtspPort() > 0 ? dev.getRtspPort() : 554)
                });
            } else {
                for (ChannelInfo ch : channels) {
                    rows.add(new String[]{
                            safe(dev.getName()),
                            safe(dev.getIp()),
                            String.valueOf(dev.getPort()),
                            proto,
                            safe(dev.getUsername()),
                            safe(dev.getPassword()),
                            String.valueOf(ch.getChannelNo()),
                            safe(ch.getName()),
                            ch.isEnabled() ? "是" : "否",
                            String.valueOf(dev.getRtspPort() > 0 ? dev.getRtspPort() : 554)
                    });
                }
            }
        }
        return rows;
    }

    public static ImportResult importFromStream(InputStream is) throws Exception {
        byte[] data = readAllBytes(is);
        if (data.length >= 2 && data[0] == 'P' && data[1] == 'K') {
            List<List<String>> rows = readXlsxRows(new ByteArrayInputStream(data));
            return parseTabularRows(rows);
        } else {
            List<List<String>> rows = readCsvRows(new ByteArrayInputStream(data));
            return parseTabularRows(rows);
        }
    }

    private static ImportResult parseTabularRows(List<List<String>> rows) {
        ImportResult result = new ImportResult();
        if (rows == null || rows.isEmpty()) {
            result.errors.add("表格内容为空");
            return result;
        }

        // Find header row (first non-empty row)
        int headerIdx = -1;
        Map<String, Integer> colMap = new HashMap<>();
        for (int r = 0; r < Math.min(rows.size(), 5); r++) {
            List<String> row = rows.get(r);
            Map<String, Integer> candidate = mapHeaders(row);
            if (candidate.containsKey("ip") || candidate.containsKey("name")) {
                headerIdx = r;
                colMap = candidate;
                break;
            }
        }

        if (headerIdx < 0) {
            result.errors.add("未识别到有效的表头（需包含“设备名称”和“设备IP”列）");
            return result;
        }

        Map<String, DeviceInfo> grouped = new LinkedHashMap<>();
        for (int r = headerIdx + 1; r < rows.size(); r++) {
            List<String> row = rows.get(r);
            if (isRowBlank(row)) continue;

            String name = getCell(row, colMap.get("name"));
            String ip = getCell(row, colMap.get("ip"));
            String portStr = getCell(row, colMap.get("port"));
            String protoStr = getCell(row, colMap.get("protocol"));
            String user = getCell(row, colMap.get("username"));
            String pwd = getCell(row, colMap.get("password"));
            String chNoStr = getCell(row, colMap.get("channel_no"));
            String chName = getCell(row, colMap.get("channel_name"));
            String enabledStr = getCell(row, colMap.get("enabled"));
            String rtspStr = getCell(row, colMap.get("rtsp_port"));

            if (ip.isEmpty()) {
                result.errors.add("第 " + (r + 1) + " 行缺少设备IP，已跳过");
                continue;
            }
            if (name.isEmpty()) {
                name = ip;
            }

            ProtocolType protocol = parseProtocol(protoStr);
            int port = parseIntOrDefault(portStr, defaultPortFor(protocol));
            int rtspPort = parseIntOrDefault(rtspStr, 554);

            String key = ip + ":" + port + ":" + protocol.getValue();
            DeviceInfo dev = grouped.get(key);
            if (dev == null) {
                dev = new DeviceInfo();
                dev.setDeviceId(UUID.randomUUID().toString());
                dev.setName(name);
                dev.setIp(ip);
                dev.setPort(port);
                dev.setProtocol(protocol);
                dev.setUsername(user.isEmpty() ? "admin" : user);
                dev.setPassword(pwd);
                dev.setRtspPort(rtspPort);
                dev.setChannels(new ArrayList<>());
                grouped.put(key, dev);
            }

            if (!chNoStr.isEmpty()) {
                int chNo = parseIntOrDefault(chNoStr, -1);
                if (chNo > 0) {
                    boolean enabled = parseBoolDefaultTrue(enabledStr);
                    String finalChName = chName.isEmpty() ? ("通道 " + chNo) : chName;
                    ChannelInfo ch = new ChannelInfo(chNo, finalChName, true, false, dev.getDeviceId(), enabled);
                    dev.getChannels().add(ch);
                }
            }
        }

        result.devices.addAll(grouped.values());
        return result;
    }

    private static Map<String, Integer> mapHeaders(List<String> row) {
        Map<String, Integer> map = new HashMap<>();
        for (int i = 0; i < row.size(); i++) {
            String h = safe(row.get(i)).replace("*", "").trim().toLowerCase(Locale.ROOT);
            if (h.contains("设备名称") || h.equals("name") || h.equals("device_name")) {
                map.put("name", i);
            } else if (h.contains("设备ip") || h.equals("ip") || h.contains("ip地址")) {
                map.put("ip", i);
            } else if (h.contains("rtsp")) {
                map.put("rtsp_port", i);
            } else if (h.contains("端口") || h.equals("port")) {
                map.put("port", i);
            } else if (h.contains("协议") || h.equals("protocol")) {
                map.put("protocol", i);
            } else if (h.contains("账号") || h.contains("用户") || h.equals("username")) {
                map.put("username", i);
            } else if (h.contains("密码") || h.equals("password")) {
                map.put("password", i);
            } else if (h.contains("通道号") || h.equals("channel_no")) {
                map.put("channel_no", i);
            } else if (h.contains("通道名称") || h.equals("channel_name")) {
                map.put("channel_name", i);
            } else if (h.contains("启用") || h.equals("enabled")) {
                map.put("enabled", i);
            }
        }
        return map;
    }

    private static ProtocolType parseProtocol(String s) {
        String lower = safe(s).toLowerCase(Locale.ROOT);
        if (lower.contains("dahua") || lower.contains("大华")) return ProtocolType.DAHUA;
        if (lower.contains("onvif")) return ProtocolType.ONVIF;
        if (lower.contains("rtsp")) return ProtocolType.CUSTOM_RTSP;
        return ProtocolType.HIKVISION;
    }

    private static int defaultPortFor(ProtocolType p) {
        switch (p) {
            case DAHUA: return 37777;
            case ONVIF: return 80;
            case CUSTOM_RTSP: return 554;
            default: return 8000;
        }
    }

    private static int parseIntOrDefault(String val, int def) {
        if (val == null || val.trim().isEmpty()) return def;
        try {
            // Handle Excel numeric strings like "8000.0"
            double d = Double.parseDouble(val.trim());
            return (int) Math.round(d);
        } catch (Exception e) {
            return def;
        }
    }

    private static boolean parseBoolDefaultTrue(String val) {
        String s = safe(val).toLowerCase(Locale.ROOT);
        if (s.isEmpty()) return true;
        return !(s.equals("否") || s.equals("false") || s.equals("0") || s.equals("no") || s.equals("n"));
    }

    private static String getCell(List<String> row, Integer idx) {
        if (idx == null || idx < 0 || idx >= row.size()) return "";
        return safe(row.get(idx));
    }

    private static boolean isRowBlank(List<String> row) {
        for (String c : row) {
            if (c != null && !c.trim().isEmpty()) return false;
        }
        return true;
    }

    private static String safe(String s) {
        return s == null ? "" : s.trim();
    }

    // -------------------------------------------------------------------------
    // Pure-JDK OOXML (.xlsx) Writer (inlineStr)
    // -------------------------------------------------------------------------
    private static void writeXlsxRows(String sheetName, List<String[]> rows, OutputStream os) throws IOException {
        try (ZipOutputStream zos = new ZipOutputStream(os)) {
            putZipEntry(zos, "[Content_Types].xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                            + "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                            + "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
                            + "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
                            + "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
                            + "<Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>"
                            + "</Types>");

            putZipEntry(zos, "_rels/.rels",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                            + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                            + "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>"
                            + "</Relationships>");

            putZipEntry(zos, "xl/workbook.xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                            + "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
                            + "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
                            + "<sheets><sheet name=\"" + escapeXml(sheetName) + "\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
                            + "</workbook>");

            putZipEntry(zos, "xl/_rels/workbook.xml.rels",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                            + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                            + "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>"
                            + "</Relationships>");

            StringBuilder sheet = new StringBuilder();
            sheet.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>");
            sheet.append("<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>");
            for (int r = 0; r < rows.size(); r++) {
                int rowNum = r + 1;
                sheet.append("<row r=\"").append(rowNum).append("\">");
                String[] cols = rows.get(r);
                for (int c = 0; c < cols.length; c++) {
                    String ref = colIndexToLetter(c) + rowNum;
                    String val = cols[c] != null ? cols[c] : "";
                    sheet.append("<c r=\"").append(ref).append("\" t=\"inlineStr\"><is><t>")
                            .append(escapeXml(val))
                            .append("</t></is></c>");
                }
                sheet.append("</row>");
            }
            sheet.append("</sheetData></worksheet>");
            putZipEntry(zos, "xl/worksheets/sheet1.xml", sheet.toString());
        }
    }

    private static void putZipEntry(ZipOutputStream zos, String name, String content) throws IOException {
        zos.putNextEntry(new ZipEntry(name));
        zos.write(content.getBytes(StandardCharsets.UTF_8));
        zos.closeEntry();
    }

    private static String colIndexToLetter(int idx) {
        StringBuilder sb = new StringBuilder();
        int n = idx;
        while (n >= 0) {
            sb.insert(0, (char) ('A' + (n % 26)));
            n = (n / 26) - 1;
        }
        return sb.toString();
    }

    private static String escapeXml(String s) {
        return s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;");
    }

    // -------------------------------------------------------------------------
    // Pure-JDK OOXML (.xlsx) Reader
    // -------------------------------------------------------------------------
    private static List<List<String>> readXlsxRows(InputStream is) throws Exception {
        byte[] sharedStringsBytes = null;
        byte[] sheetBytes = null;

        try (ZipInputStream zis = new ZipInputStream(is)) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                String name = entry.getName().replace('\\', '/');
                if ("xl/sharedStrings.xml".equalsIgnoreCase(name)) {
                    sharedStringsBytes = readEntryBytes(zis);
                } else if ("xl/worksheets/sheet1.xml".equalsIgnoreCase(name)
                        || (sheetBytes == null && name.toLowerCase(Locale.ROOT).startsWith("xl/worksheets/sheet") && name.endsWith(".xml"))) {
                    sheetBytes = readEntryBytes(zis);
                }
                zis.closeEntry();
            }
        }

        if (sheetBytes == null) {
            throw new IllegalArgumentException("无效的 Excel (.xlsx) 文件: 未找到工作表");
        }

        List<String> sharedStrings = sharedStringsBytes != null ? parseSharedStrings(sharedStringsBytes) : new ArrayList<>();
        return parseSheetXml(sheetBytes, sharedStrings);
    }

    private static List<String> parseSharedStrings(byte[] bytes) throws Exception {
        List<String> list = new ArrayList<>();
        Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder()
                .parse(new ByteArrayInputStream(bytes));
        NodeList siNodes = doc.getElementsByTagName("si");
        for (int i = 0; i < siNodes.getLength(); i++) {
            Element si = (Element) siNodes.item(i);
            NodeList tNodes = si.getElementsByTagName("t");
            StringBuilder sb = new StringBuilder();
            for (int j = 0; j < tNodes.getLength(); j++) {
                sb.append(tNodes.item(j).getTextContent());
            }
            list.add(sb.toString());
        }
        return list;
    }

    private static List<List<String>> parseSheetXml(byte[] bytes, List<String> sharedStrings) throws Exception {
        List<List<String>> rows = new ArrayList<>();
        Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder()
                .parse(new ByteArrayInputStream(bytes));
        NodeList rowNodes = doc.getElementsByTagName("row");
        for (int r = 0; r < rowNodes.getLength(); r++) {
            Element rowEl = (Element) rowNodes.item(r);
            List<String> currentRow = new ArrayList<>();
            NodeList cellNodes = rowEl.getElementsByTagName("c");
            for (int c = 0; c < cellNodes.getLength(); c++) {
                Element cEl = (Element) cellNodes.item(c);
                String cellType = cEl.getAttribute("t");
                String ref = cEl.getAttribute("r");
                int colIdx = (ref != null && !ref.isEmpty()) ? refToColIndex(ref) : currentRow.size();

                String val = "";
                if ("inlineStr".equals(cellType)) {
                    NodeList tNodes = cEl.getElementsByTagName("t");
                    if (tNodes.getLength() > 0) {
                        val = tNodes.item(0).getTextContent();
                    }
                } else {
                    NodeList vNodes = cEl.getElementsByTagName("v");
                    if (vNodes.getLength() > 0) {
                        val = vNodes.item(0).getTextContent();
                        if ("s".equals(cellType)) {
                            try {
                                int idx = Integer.parseInt(val.trim());
                                val = (idx >= 0 && idx < sharedStrings.size()) ? sharedStrings.get(idx) : "";
                            } catch (Exception ignored) {}
                        }
                    }
                }

                while (currentRow.size() <= colIdx) {
                    currentRow.add("");
                }
                if (colIdx >= 0) {
                    currentRow.set(colIdx, val != null ? val : "");
                }
            }
            rows.add(currentRow);
        }
        return rows;
    }

    private static int refToColIndex(String ref) {
        int col = 0;
        for (int i = 0; i < ref.length(); i++) {
            char ch = ref.charAt(i);
            if (Character.isLetter(ch)) {
                col = col * 26 + (Character.toUpperCase(ch) - 'A' + 1);
            } else {
                break;
            }
        }
        return col > 0 ? col - 1 : 0;
    }

    // -------------------------------------------------------------------------
    // CSV Reader & Helpers
    // -------------------------------------------------------------------------
    private static List<List<String>> readCsvRows(InputStream is) throws IOException {
        List<List<String>> rows = new ArrayList<>();
        BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
        String line;
        boolean first = true;
        while ((line = reader.readLine()) != null) {
            if (first) {
                first = false;
                if (line.startsWith("\uFEFF")) {
                    line = line.substring(1);
                }
            }
            rows.add(parseCsvLine(line));
        }
        return rows;
    }

    private static List<String> parseCsvLine(String line) {
        List<String> cols = new ArrayList<>();
        StringBuilder sb = new StringBuilder();
        boolean inQuotes = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (inQuotes) {
                if (c == '"') {
                    if (i + 1 < line.length() && line.charAt(i + 1) == '"') {
                        sb.append('"');
                        i++;
                    } else {
                        inQuotes = false;
                    }
                } else {
                    sb.append(c);
                }
            } else {
                if (c == '"') {
                    inQuotes = true;
                } else if (c == ',') {
                    cols.add(sb.toString());
                    sb.setLength(0);
                } else {
                    sb.append(c);
                }
            }
        }
        cols.add(sb.toString());
        return cols;
    }

    private static String escapeCsv(String val) {
        if (val.contains(",") || val.contains("\"") || val.contains("\n") || val.contains("\r")) {
            return "\"" + val.replace("\"", "\"\"") + "\"";
        }
        return val;
    }

    private static byte[] readAllBytes(InputStream is) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = is.read(buf)) != -1) {
            baos.write(buf, 0, n);
        }
        return baos.toByteArray();
    }

    private static byte[] readEntryBytes(ZipInputStream zis) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = zis.read(buf)) != -1) {
            baos.write(buf, 0, n);
        }
        return baos.toByteArray();
    }
}

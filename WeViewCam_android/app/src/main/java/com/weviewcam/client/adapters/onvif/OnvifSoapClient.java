package com.weviewcam.client.adapters.onvif;

import android.util.Base64;

import com.weviewcam.client.core.logger.AppLogger;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Lightweight pure-Java ONVIF SOAP client (WS-UsernameToken SHA-1 Digest)
 * and fast RTSP DESCRIBE probe for Android.
 */
public class OnvifSoapClient {
    private static final String MODULE = "OnvifSoap";

    public static class DiscoveryResult {
        public boolean connected = false;
        public int activePort = 80;
        public String mainProfileToken = "";
        public String subProfileToken = "";
        public String mainStreamUri = "";
        public String subStreamUri = "";
        public boolean ptzSupported = false;
    }

    public static DiscoveryResult discover(String ip, int preferredPort, int rtspPort, String user, String pass) {
        DiscoveryResult result = new DiscoveryResult();
        List<Integer> ports = new ArrayList<>();
        if (preferredPort > 0) ports.add(preferredPort);
        for (int p : new int[]{80, 8080, 8899, 8000, 5000, 8090}) {
            if (!ports.contains(p)) ports.add(p);
        }

        for (int port : ports) {
            if (!isTcpPortOpen(ip, port, 800)) continue;
            try {
                String mediaUrl = "http://" + ip + ":" + port + "/onvif/media_service";
                String profilesXml = sendSoap(mediaUrl,
                        "http://www.onvif.org/ver10/media/wsdl/GetProfiles",
                        "<trt:GetProfiles xmlns:trt=\"http://www.onvif.org/ver10/media/wsdl\"/>",
                        user, pass);

                if (profilesXml == null || !profilesXml.contains("Profiles")) {
                    // Fallback to standard device_service / Media path
                    mediaUrl = "http://" + ip + ":" + port + "/onvif/Media";
                    profilesXml = sendSoap(mediaUrl,
                            "http://www.onvif.org/ver10/media/wsdl/GetProfiles",
                            "<trt:GetProfiles xmlns:trt=\"http://www.onvif.org/ver10/media/wsdl\"/>",
                            user, pass);
                }

                if (profilesXml != null && profilesXml.contains("Profiles")) {
                    List<String> tokens = parseProfileTokens(profilesXml);
                    if (!tokens.isEmpty()) {
                        result.connected = true;
                        result.activePort = port;
                        result.mainProfileToken = tokens.get(0);
                        result.subProfileToken = tokens.size() > 1 ? tokens.get(tokens.size() - 1) : tokens.get(0);
                        result.ptzSupported = profilesXml.contains("PTZConfiguration");

                        String rawMain = fetchStreamUri(mediaUrl, result.mainProfileToken, user, pass);
                        if (rawMain != null) {
                            result.mainStreamUri = normalizeRtspUrl(rawMain, ip, rtspPort, user, pass);
                        }
                        if (!result.subProfileToken.equals(result.mainProfileToken)) {
                            String rawSub = fetchStreamUri(mediaUrl, result.subProfileToken, user, pass);
                            if (rawSub != null) {
                                result.subStreamUri = normalizeRtspUrl(rawSub, ip, rtspPort, user, pass);
                            }
                        } else {
                            result.subStreamUri = result.mainStreamUri;
                        }
                        AppLogger.i(MODULE, "✓ ONVIF 握手成功 " + ip + ":" + port + " (Profiles=" + tokens.size() + ")");
                        return result;
                    }
                }
            } catch (Exception e) {
                AppLogger.d(MODULE, "ONVIF 端口 " + port + " 探测失败: " + e.getMessage());
            }
        }
        return result;
    }

    private static String fetchStreamUri(String mediaUrl, String profileToken, String user, String pass) {
        String body = "<trt:GetStreamUri xmlns:trt=\"http://www.onvif.org/ver10/media/wsdl\" "
                + "xmlns:tt=\"http://www.onvif.org/ver10/schema\">"
                + "<trt:StreamSetup>"
                + "<tt:Stream>RTP-Unicast</tt:Stream>"
                + "<tt:Transport><tt:Protocol>RTSP</tt:Protocol></tt:Transport>"
                + "</trt:StreamSetup>"
                + "<trt:ProfileToken>" + escapeXml(profileToken) + "</trt:ProfileToken>"
                + "</trt:GetStreamUri>";
        String resp = sendSoap(mediaUrl, "http://www.onvif.org/ver10/media/wsdl/GetStreamUri", body, user, pass);
        if (resp == null) return null;
        Matcher m = Pattern.compile("<(?:[a-zA-Z0-9]+:)?Uri[^>]*>([^<]+)</(?:[a-zA-Z0-9]+:)?Uri>").matcher(resp);
        if (m.find()) {
            return m.group(1).trim().replace("&amp;", "&");
        }
        return null;
    }

    public static boolean ptzContinuousMove(String ip, int port, String user, String pass,
                                            String profileToken, float pan, float tilt, float zoom) {
        if (profileToken == null || profileToken.isEmpty()) return false;
        String ptzUrl = "http://" + ip + ":" + port + "/onvif/ptz_service";
        String body = "<tptz:ContinuousMove xmlns:tptz=\"http://www.onvif.org/ver20/ptz/wsdl\" "
                + "xmlns:tt=\"http://www.onvif.org/ver10/schema\">"
                + "<tptz:ProfileToken>" + escapeXml(profileToken) + "</tptz:ProfileToken>"
                + "<tptz:Velocity>"
                + "<tt:PanTilt x=\"" + pan + "\" y=\"" + tilt + "\"/>"
                + "<tt:Zoom x=\"" + zoom + "\"/>"
                + "</tptz:Velocity>"
                + "</tptz:ContinuousMove>";
        String resp = sendSoap(ptzUrl, "http://www.onvif.org/ver20/ptz/wsdl/ContinuousMove", body, user, pass);
        return resp != null;
    }

    public static boolean ptzStop(String ip, int port, String user, String pass, String profileToken) {
        if (profileToken == null || profileToken.isEmpty()) return false;
        String ptzUrl = "http://" + ip + ":" + port + "/onvif/ptz_service";
        String body = "<tptz:Stop xmlns:tptz=\"http://www.onvif.org/ver20/ptz/wsdl\">"
                + "<tptz:ProfileToken>" + escapeXml(profileToken) + "</tptz:ProfileToken>"
                + "<tptz:PanTilt>true</tptz:PanTilt><tptz:Zoom>true</tptz:Zoom>"
                + "</tptz:Stop>";
        String resp = sendSoap(ptzUrl, "http://www.onvif.org/ver20/ptz/wsdl/Stop", body, user, pass);
        return resp != null;
    }

    public static List<String> buildCandidateRtspUrls(String ip, int rtspPort, String user, String pass,
                                                      int channelNo, int streamType, String onvifUri) {
        List<String> list = new ArrayList<>();
        if (onvifUri != null && !onvifUri.isEmpty()) {
            list.add(onvifUri);
        }
        int port = rtspPort > 0 ? rtspPort : 554;
        String cred = "";
        if (user != null && !user.isEmpty()) {
            cred = urlEncode(user) + ":" + urlEncode(pass != null ? pass : "") + "@";
        }
        String base = "rtsp://" + cred + ip + ":" + port;
        int streamIdx = streamType == 0 ? 1 : 2;
        int subType = streamType == 0 ? 0 : 1;

        addUnique(list, base + "/cam/realmonitor?channel=" + channelNo + "&subtype=" + subType);
        addUnique(list, base + "/Streaming/Channels/" + channelNo + "0" + streamIdx);
        addUnique(list, base + "/Streaming/Channels/" + channelNo);
        addUnique(list, base + "/h264/ch" + channelNo + "/" + (streamType == 0 ? "main" : "sub") + "/av_stream");
        addUnique(list, base + "/h264ESVideoTest");
        addUnique(list, base + "/onvif-media/media.amp");
        addUnique(list, base + "/MediaInput/h264");
        addUnique(list, base + "/media/video1");
        addUnique(list, base + "/profile" + streamIdx);
        addUnique(list, base + "/stream" + streamIdx);
        addUnique(list, base + "/live/ch0");
        addUnique(list, base + "/live");
        addUnique(list, base + "/h264");
        return list;
    }

    public static boolean probeRtspUrl(String rtspUrl, int timeoutMs) {
        if (rtspUrl == null || !rtspUrl.startsWith("rtsp://")) return false;
        Matcher m = Pattern.compile("^rtsp://(?:[^@]+@)?([^:/]+)(?::(\\d+))?(/.*)$").matcher(rtspUrl);
        if (!m.matches()) return false;
        String host = m.group(1);
        int port = m.group(2) != null ? Integer.parseInt(m.group(2)) : 554;
        String path = m.group(3);
        try (Socket s = new Socket()) {
            s.connect(new InetSocketAddress(host, port), timeoutMs);
            s.setSoTimeout(timeoutMs);
            String req = "DESCRIBE rtsp://" + host + ":" + port + path + " RTSP/1.0\r\n"
                    + "CSeq: 1\r\nAccept: application/sdp\r\n\r\n";
            s.getOutputStream().write(req.getBytes(StandardCharsets.US_ASCII));
            s.getOutputStream().flush();
            byte[] buf = new byte[1024];
            int n = s.getInputStream().read(buf);
            if (n > 0) {
                String res = new String(buf, 0, n, StandardCharsets.ISO_8859_1);
                return res.contains("200 OK") || res.contains("401");
            }
        } catch (Exception ignored) {}
        return false;
    }

    public static String normalizeRtspUrl(String rawUri, String targetIp, int targetRtspPort, String user, String pass) {
        if (rawUri == null || !rawUri.startsWith("rtsp://")) return rawUri;
        String withoutScheme = rawUri.substring(7);
        int slashIdx = withoutScheme.indexOf('/');
        String hostPart = slashIdx >= 0 ? withoutScheme.substring(0, slashIdx) : withoutScheme;
        String pathPart = slashIdx >= 0 ? withoutScheme.substring(slashIdx) : "/";

        int atIdx = hostPart.lastIndexOf('@');
        if (atIdx >= 0) {
            hostPart = hostPart.substring(atIdx + 1);
        }
        int port = targetRtspPort > 0 ? targetRtspPort : 554;
        int colonIdx = hostPart.indexOf(':');
        if (colonIdx >= 0) {
            try {
                port = Integer.parseInt(hostPart.substring(colonIdx + 1));
            } catch (Exception ignored) {}
        }

        String cred = "";
        if (user != null && !user.isEmpty()) {
            cred = urlEncode(user) + ":" + urlEncode(pass != null ? pass : "") + "@";
        }
        return "rtsp://" + cred + targetIp + ":" + port + pathPart;
    }

    private static List<String> parseProfileTokens(String xml) {
        List<String> tokens = new ArrayList<>();
        Matcher m = Pattern.compile("<(?:[a-zA-Z0-9]+:)?Profiles[^>]*\\btoken=\"([^\"]+)\"").matcher(xml);
        while (m.find()) {
            tokens.add(m.group(1));
        }
        return tokens;
    }

    private static String sendSoap(String urlStr, String soapAction, String bodyXml, String user, String pass) {
        HttpURLConnection conn = null;
        try {
            String securityHeader = buildWsSecurityHeader(user, pass);
            String envelope = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                    + "<s:Envelope xmlns:s=\"http://www.w3.org/2003/05/soap-envelope\">"
                    + "<s:Header>" + securityHeader + "</s:Header>"
                    + "<s:Body>" + bodyXml + "</s:Body>"
                    + "</s:Envelope>";

            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(2500);
            conn.setReadTimeout(3000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/soap+xml; charset=utf-8; action=\"" + soapAction + "\"");

            byte[] outBytes = envelope.getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(outBytes);
            }
            int code = conn.getResponseCode();
            InputStream is = (code >= 200 && code < 400) ? conn.getInputStream() : conn.getErrorStream();
            if (is == null) return null;
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = is.read(buf)) != -1) {
                baos.write(buf, 0, n);
            }
            return baos.toString(StandardCharsets.UTF_8.name());
        } catch (Exception e) {
            return null;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private static String buildWsSecurityHeader(String user, String pass) {
        if (user == null || user.isEmpty()) return "";
        try {
            byte[] nonceBytes = new byte[16];
            new SecureRandom().nextBytes(nonceBytes);
            String nonceB64 = Base64.encodeToString(nonceBytes, Base64.NO_WRAP);

            SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
            sdf.setTimeZone(TimeZone.getTimeZone("UTC"));
            String created = sdf.format(new Date());

            byte[] createdBytes = created.getBytes(StandardCharsets.UTF_8);
            byte[] passBytes = (pass != null ? pass : "").getBytes(StandardCharsets.UTF_8);

            MessageDigest md = MessageDigest.getInstance("SHA-1");
            md.update(nonceBytes);
            md.update(createdBytes);
            md.update(passBytes);
            String digestB64 = Base64.encodeToString(md.digest(), Base64.NO_WRAP);

            return "<Security s:mustUnderstand=\"1\" xmlns=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd\">"
                    + "<UsernameToken>"
                    + "<Username>" + escapeXml(user) + "</Username>"
                    + "<Password Type=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest\">" + digestB64 + "</Password>"
                    + "<Nonce EncodingType=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary\">" + nonceB64 + "</Nonce>"
                    + "<Created xmlns=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd\">" + created + "</Created>"
                    + "</UsernameToken>"
                    + "</Security>";
        } catch (Exception e) {
            return "";
        }
    }

    private static boolean isTcpPortOpen(String ip, int port, int timeoutMs) {
        try (Socket s = new Socket()) {
            s.connect(new InetSocketAddress(ip, port), timeoutMs);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private static void addUnique(List<String> list, String item) {
        if (!list.contains(item)) list.add(item);
    }

    private static String urlEncode(String s) {
        try {
            return URLEncoder.encode(s, "UTF-8");
        } catch (Exception e) {
            return s;
        }
    }

    private static String escapeXml(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\"", "&quot;").replace("'", "&apos;");
    }
}

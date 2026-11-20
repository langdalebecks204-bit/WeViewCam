package com.weviewcam.client.adapters.onvif;

import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.util.StreamStatsTracker;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Lightweight local RTSP-over-TCP proxy for Android Media3 ExoPlayer.
 * 1. Sanitizes malformed camera SDPs (e.g. empty "a=fmtp:96 " lines from LIVE555 that crash Media3).
 * 2. Rewrites Content-Base / request host transparently.
 * 3. Counts exact incoming wire bytes into StreamStatsTracker for accurate real-time bitrate.
 */
public class LocalRtspProxy {
    private static final String MODULE = "LocalRtspProxy";

    private final String remoteHost;
    private final int remotePort;
    private final String originalRtspUrl;
    private final StreamStatsTracker statsTracker;

    private ServerSocket serverSocket;
    private volatile boolean running = true;
    private volatile String localRtspUrl;

    public LocalRtspProxy(String rtspUrl, StreamStatsTracker statsTracker) throws IOException {
        this.originalRtspUrl = rtspUrl;
        this.statsTracker = statsTracker;

        Matcher m = Pattern.compile("^rtsp://(?:([^@]+)@)?([^:/]+)(?::(\\d+))?(/.*)$").matcher(rtspUrl);
        if (!m.matches()) {
            throw new IllegalArgumentException("Invalid RTSP URL: " + rtspUrl);
        }
        String cred = m.group(1);
        this.remoteHost = m.group(2);
        this.remotePort = m.group(3) != null ? Integer.parseInt(m.group(3)) : 554;
        String path = m.group(4);

        this.serverSocket = new ServerSocket(0, 4, InetAddress.getByName("127.0.0.1"));
        int localPort = this.serverSocket.getLocalPort();
        String credPrefix = (cred != null && !cred.isEmpty()) ? (cred + "@") : "";
        this.localRtspUrl = "rtsp://" + credPrefix + "127.0.0.1:" + localPort + path;

        Thread acceptThread = new Thread(this::acceptLoop, "RtspProxyAccept-" + localPort);
        acceptThread.setDaemon(true);
        acceptThread.start();
    }

    public String getLocalRtspUrl() {
        return localRtspUrl;
    }

    public void close() {
        running = false;
        try {
            if (serverSocket != null) serverSocket.close();
        } catch (IOException ignored) {}
    }

    private void acceptLoop() {
        while (running) {
            try {
                final Socket client = serverSocket.accept();
                Thread connThread = new Thread(() -> handleClient(client), "RtspProxyConn");
                connThread.setDaemon(true);
                connThread.start();
            } catch (IOException e) {
                if (running) {
                    AppLogger.d(MODULE, "Proxy accept 结束: " + e.getMessage());
                }
                break;
            }
        }
    }

    private void handleClient(Socket client) {
        Socket upstream = null;
        try {
            upstream = new Socket(remoteHost, remotePort);
            upstream.setTcpNoDelay(true);
            client.setTcpNoDelay(true);

            final InputStream cIn = client.getInputStream();
            final OutputStream cOut = client.getOutputStream();
            final InputStream uIn = upstream.getInputStream();
            final OutputStream uOut = upstream.getOutputStream();
            final int localPort = serverSocket.getLocalPort();

            // Client -> Camera: rewrite 127.0.0.1:<localPort> back to remoteHost:remotePort only on request line (preserve Digest Auth uri)
            Thread upThread = new Thread(() -> {
                try {
                    byte[] buf = new byte[8192];
                    int n;
                    String localHostPort = "127.0.0.1:" + localPort;
                    String remoteHostPort = remoteHost + ":" + remotePort;
                    while (running && (n = cIn.read(buf)) != -1) {
                        if (n > 0 && buf[0] != '$') {
                            String txt = new String(buf, 0, n, StandardCharsets.ISO_8859_1);
                            if (txt.contains(localHostPort)) {
                                // Only rewrite request line & Transport/Host, do NOT alter Authorization Digest uri="..."
                                String[] lines = txt.split("\r\n", -1);
                                StringBuilder sb = new StringBuilder();
                                for (int i = 0; i < lines.length; i++) {
                                    String line = lines[i];
                                    if (!line.regionMatches(true, 0, "Authorization:", 0, 14)) {
                                        line = line.replace(localHostPort, remoteHostPort);
                                    }
                                    sb.append(line);
                                    if (i < lines.length - 1) sb.append("\r\n");
                                }
                                uOut.write(sb.toString().getBytes(StandardCharsets.ISO_8859_1));
                                uOut.flush();
                                continue;
                            }
                        }
                        uOut.write(buf, 0, n);
                        uOut.flush();
                    }
                } catch (IOException ignored) {}
            }, "RtspProxyUp");
            upThread.setDaemon(true);
            upThread.start();

            // Camera -> Client: sanitize SDP responses and count all received bytes
            forwardUpstreamToClient(uIn, cOut, localPort);
        } catch (Exception e) {
            AppLogger.d(MODULE, "Proxy 连接结束: " + e.getMessage());
        } finally {
            try { client.close(); } catch (IOException ignored) {}
            try { if (upstream != null) upstream.close(); } catch (IOException ignored) {}
        }
    }

    private void forwardUpstreamToClient(InputStream uIn, OutputStream cOut, int localPort) throws IOException {
        ByteArrayOutputStream headerBuf = new ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        boolean streamingBinary = false;

        while (running) {
            if (streamingBinary) {
                int n = uIn.read(buf);
                if (n == -1) break;
                if (statsTracker != null) statsTracker.recordBytes(n);
                cOut.write(buf, 0, n);
                cOut.flush();
                continue;
            }

            int b = uIn.read();
            if (b == -1) break;
            if (statsTracker != null) statsTracker.recordBytes(1);

            if (headerBuf.size() == 0 && b == '$') {
                // RTP-over-TCP interleaved binary stream has started
                streamingBinary = true;
                cOut.write(b);
                cOut.flush();
                continue;
            }

            headerBuf.write(b);
            byte[] hb = headerBuf.toByteArray();
            int len = hb.length;
            if (len >= 4 && hb[len - 4] == '\r' && hb[len - 3] == '\n' && hb[len - 2] == '\r' && hb[len - 1] == '\n') {
                String headers = new String(hb, StandardCharsets.ISO_8859_1);
                headerBuf.reset();

                int contentLen = parseContentLength(headers);
                byte[] body = new byte[0];
                if (contentLen > 0 && contentLen < 1024 * 1024) {
                    body = new byte[contentLen];
                    int readTotal = 0;
                    while (readTotal < contentLen) {
                        int r = uIn.read(body, readTotal, contentLen - readTotal);
                        if (r == -1) break;
                        if (statsTracker != null) statsTracker.recordBytes(r);
                        readTotal += r;
                    }
                    if (readTotal < contentLen) {
                        byte[] partial = new byte[readTotal];
                        System.arraycopy(body, 0, partial, 0, readTotal);
                        body = partial;
                    }
                }

                byte[] sanitized = sanitizeRtspResponse(headers, body, remoteHost, remotePort, localPort);
                cOut.write(sanitized);
                cOut.flush();

                if (headers.startsWith("RTSP/1.0 200") && headers.contains("RTP-Info")) {
                    // PLAY succeeded, switch to fast bulk streaming
                    streamingBinary = true;
                }
            }
        }
    }

    public static byte[] sanitizeRtspResponse(String headers, byte[] body,
                                              String remoteHost, int remotePort, int localPort) {
        String outHeaders = headers;
        byte[] outBody = body;

        if (headers.toLowerCase().contains("application/sdp") && body != null && body.length > 0) {
            String sdp = new String(body, StandardCharsets.ISO_8859_1);
            // Replace empty "a=fmtp:<pt> " lines with valid H264 fmtp + sprop-parameter-sets so Media3 initializes MediaCodec cleanly
            sdp = sdp.replaceAll("(?m)^(a=fmtp:(\\d+))[ \\t]*\\r?\\n",
                    "$1 packetization-mode=1;profile-level-id=42001e;sprop-parameter-sets=Z0IAKeKQCgC3/4CIAAADAAgAAAMBlCA=,aM48gA==\r\n");
            outBody = sdp.getBytes(StandardCharsets.ISO_8859_1);

            // Rewrite Content-Base to local proxy host:port
            outHeaders = outHeaders.replaceAll(
                    "(?i)(Content-Base:\\s*rtsp://)" + Pattern.quote(remoteHost) + "(?::\\d+)?",
                    "$1" + "127.0.0.1:" + localPort
            );
            // Update Content-Length to match sanitized SDP
            outHeaders = outHeaders.replaceAll(
                    "(?i)Content-Length:\\s*\\d+",
                    "Content-Length: " + outBody.length
            );
        }

        byte[] hdrBytes = outHeaders.getBytes(StandardCharsets.ISO_8859_1);
        if (outBody == null || outBody.length == 0) {
            return hdrBytes;
        }
        byte[] combined = new byte[hdrBytes.length + outBody.length];
        System.arraycopy(hdrBytes, 0, combined, 0, hdrBytes.length);
        System.arraycopy(outBody, 0, combined, hdrBytes.length, outBody.length);
        return combined;
    }

    private static int parseContentLength(String headers) {
        Matcher m = Pattern.compile("(?im)^Content-Length:\\s*(\\d+)").matcher(headers);
        if (m.find()) {
            try {
                return Integer.parseInt(m.group(1));
            } catch (Exception ignored) {}
        }
        return 0;
    }
}

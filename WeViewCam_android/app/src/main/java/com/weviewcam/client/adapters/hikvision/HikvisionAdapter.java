package com.weviewcam.client.adapters.hikvision;

import android.view.Surface;
import android.view.SurfaceHolder;

import com.hcnetsdk.jna.HCNetSDKByJNA;
import com.hcnetsdk.jna.HCNetSDKJNAInstance;
import com.hikvision.netsdk.HCNetSDK;
import com.hikvision.netsdk.NET_DVR_FILECOND;
import com.hikvision.netsdk.NET_DVR_FINDDATA_V30;
import com.hikvision.netsdk.NET_DVR_IPPARACFG_V40;
import com.hikvision.netsdk.NET_DVR_PREVIEWINFO;
import com.hikvision.netsdk.NET_DVR_PREVIEWINFO_V20;
import com.hikvision.netsdk.NET_DVR_STREAM_INFO;
import com.hikvision.netsdk.NET_DVR_TIME;
import com.hikvision.netsdk.NET_DVR_VOD_PARA;
import com.hikvision.netsdk.NET_DVR_WORKSTATE_V30;
import com.hikvision.netsdk.PTZCommand;
import com.hikvision.netsdk.PlaybackControlCommand;
import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PlaybackCommand;
import com.weviewcam.client.core.model.RecordSegment;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class HikvisionAdapter extends BaseDeviceAdapter {
    private static final String MODULE = "HikvisionAdapter";
    private static boolean isSdkInitialized = false;

    // Standard Playback Command Constants
    private static final int NET_DVR_PLAYNORMAL = 7;
    private static final int NET_DVR_PLAYFRAME = 8;
    private static final int NET_DVR_PLAYSETPOS = 12;

    private int userId = -1;
    private HCNetSDKByJNA.NET_DVR_DEVICEINFO_V40 deviceInfoV40;

    public HikvisionAdapter(DeviceInfo deviceInfo) {
        super(deviceInfo);
        initSdkOnce();
    }

    private static synchronized void initSdkOnce() {
        if (!isSdkInitialized) {
            try {
                boolean initJni = HCNetSDK.getInstance().NET_DVR_Init();
                boolean initJna = HCNetSDKJNAInstance.getInstance().NET_DVR_Init();
                AppLogger.i(MODULE, "HCNetSDK 初始化结果 - JNI: " + initJni + ", JNA: " + initJna);
                isSdkInitialized = initJni || initJna;
            } catch (Throwable t) {
                AppLogger.w(MODULE, "HCNetSDK 本地库初始化失败: " + t.getMessage());
                isSdkInitialized = false;
            }
        }
    }

    @Override
    public boolean login() {
        if (isLoggedIn && userId >= 0) {
            return true;
        }

        try {
            HCNetSDKByJNA.NET_DVR_USER_LOGIN_INFO loginInfo = new HCNetSDKByJNA.NET_DVR_USER_LOGIN_INFO();
            byte[] ipBytes = deviceInfo.getIp().getBytes();
            byte[] userBytes = deviceInfo.getUsername().getBytes();
            byte[] passBytes = deviceInfo.getPassword().getBytes();

            System.arraycopy(ipBytes, 0, loginInfo.sDeviceAddress, 0, Math.min(ipBytes.length, loginInfo.sDeviceAddress.length));
            System.arraycopy(userBytes, 0, loginInfo.sUserName, 0, Math.min(userBytes.length, loginInfo.sUserName.length));
            System.arraycopy(passBytes, 0, loginInfo.sPassword, 0, Math.min(passBytes.length, loginInfo.sPassword.length));
            loginInfo.wPort = (short) deviceInfo.getPort();

            deviceInfoV40 = new HCNetSDKByJNA.NET_DVR_DEVICEINFO_V40();
            loginInfo.write();

            userId = HCNetSDKJNAInstance.getInstance().NET_DVR_Login_V40(loginInfo.getPointer(), deviceInfoV40.getPointer());
            if (userId >= 0) {
                deviceInfoV40.read();
                isLoggedIn = true;
                deviceInfo.setConnected(true);
                AppLogger.i(MODULE, "海康设备登录成功 [" + deviceInfo.getName() + "], userId=" + userId);
                return true;
            } else {
                int err = HCNetSDKJNAInstance.getInstance().NET_DVR_GetLastError();
                AppLogger.e(MODULE, "海康设备登录失败 [" + deviceInfo.getName() + "], 错误码=" + err);
                isLoggedIn = false;
                userId = -1;
                return false;
            }
        } catch (Throwable t) {
            AppLogger.e(MODULE, "海康登录发生异常: " + t.getMessage(), t);
            isLoggedIn = false;
            userId = -1;
            return false;
        }
    }

    @Override
    public boolean logout() {
        if (userId >= 0) {
            try {
                boolean ret = HCNetSDKJNAInstance.getInstance().NET_DVR_Logout(userId);
                AppLogger.i(MODULE, "海康设备注销 userId=" + userId + ", ret=" + ret);
            } catch (Throwable t) {
                AppLogger.w(MODULE, "海康设备注销异常: " + t.getMessage());
            }
            userId = -1;
        }
        isLoggedIn = false;
        // Do NOT clear deviceInfo.setConnected(false) to preserve verified status in UI
        return true;
    }

    @Override
    public List<ChannelInfo> getChannels() {
        List<ChannelInfo> channelList = new ArrayList<>();
        if (!isLoggedIn || userId < 0) {
            if (!login()) {
                return channelList;
            }
        }

        try {
            int startChan = deviceInfoV40.struDeviceV30.byStartChan;
            int chanNum = deviceInfoV40.struDeviceV30.byChanNum;

            // Probe channel signal status via NET_DVR_GetDVRWorkState_V30
            Map<Integer, Boolean> channelSignalMap = new HashMap<>();
            try {
                NET_DVR_WORKSTATE_V30 workState = new NET_DVR_WORKSTATE_V30();
                if (HCNetSDK.getInstance().NET_DVR_GetDVRWorkState_V30(userId, workState)) {
                    if (workState.struChanStatic != null) {
                        for (int i = 0; i < workState.struChanStatic.length; i++) {
                            if (workState.struChanStatic[i] != null) {
                                // bySignalStatic: 0-正常(在线), 1-信号丢失(离线)
                                channelSignalMap.put(i, workState.struChanStatic[i].bySignalStatic == 0);
                            }
                        }
                    }
                }
            } catch (Throwable t) {
                AppLogger.d(MODULE, "获取工作状态提示: " + t.getMessage());
            }

            // 1. Analog channels (if any)
            for (int i = 0; i < chanNum; i++) {
                int chNo = startChan + i;
                boolean isOnline = channelSignalMap.containsKey(i) ? Boolean.TRUE.equals(channelSignalMap.get(i)) : true;
                channelList.add(new ChannelInfo(chNo, "模拟通道 " + (i + 1), isOnline, true, deviceInfo.getDeviceId()));
            }

            // 2. IP Digital channels via NET_DVR_IPPARACFG_V40
            NET_DVR_IPPARACFG_V40 ipPara = new NET_DVR_IPPARACFG_V40();
            boolean getIpOk = HCNetSDK.getInstance().NET_DVR_GetDVRConfig(
                    userId,
                    HCNetSDK.NET_DVR_GET_IPPARACFG_V40,
                    0,
                    ipPara
            );

            if (getIpOk && ipPara.dwDChanNum > 0 && ipPara.struIPChanInfo != null) {
                int ipStartChan = ipPara.dwStartDChan;
                for (int i = 0; i < ipPara.dwDChanNum && i < ipPara.struIPChanInfo.length; i++) {
                    int dChanNo = ipStartChan + i;
                    boolean isConfigured = (ipPara.struIPChanInfo[i].byEnable == 1);
                    boolean isOnline = isConfigured;
                    if (channelSignalMap.containsKey(i)) {
                        isOnline = isConfigured && Boolean.TRUE.equals(channelSignalMap.get(i));
                    }
                    String label = (chanNum == 0) ? ("通道 " + (i + 1)) : ("数字通道 " + (i + 1));
                    channelList.add(new ChannelInfo(dChanNo, label, isOnline, true, deviceInfo.getDeviceId()));
                }
            }

            // If empty, supply default channels from configuration
            if (channelList.isEmpty()) {
                channelList = deviceInfo.getChannels();
            }
        } catch (Throwable t) {
            AppLogger.e(MODULE, "获取通道列表异常: " + t.getMessage(), t);
            channelList = deviceInfo.getChannels();
        }

        return channelList;
    }

    @Override
    public int startRealPlay(int channelNo, SurfaceHolder surfaceHolder, int streamType) {
        if (!isLoggedIn || userId < 0) {
            if (!login()) {
                return -1;
            }
        }

        try {
            NET_DVR_PREVIEWINFO previewInfo = new NET_DVR_PREVIEWINFO();
            previewInfo.lChannel = channelNo;
            previewInfo.dwStreamType = streamType; // 0-main, 1-sub
            previewInfo.dwLinkMode = 0;           // TCP
            previewInfo.bBlocked = 1;
            previewInfo.hHwnd = surfaceHolder;

            int playHandle = HCNetSDK.getInstance().NET_DVR_RealPlay_V40(userId, previewInfo, null);
            if (playHandle >= 0) {
                try {
                    HCNetSDKJNAInstance.getInstance().NET_DVR_OpenSound((short) playHandle);
                } catch (Throwable ignored) {}
                AppLogger.i(MODULE, "启动实时预览成功 (SurfaceHolder): handle=" + playHandle + ", ch=" + channelNo);
                return playHandle;
            } else {
                int err = HCNetSDK.getInstance().NET_DVR_GetLastError();
                AppLogger.e(MODULE, "启动实时预览失败 (SurfaceHolder): ch=" + channelNo + ", err=" + err);
                return -1;
            }
        } catch (Throwable t) {
            AppLogger.e(MODULE, "startRealPlay 异常: " + t.getMessage(), t);
            return -1;
        }
    }

    @Override
    public int startRealPlay(int channelNo, Surface surface, int streamType) {
        if (!isLoggedIn || userId < 0) {
            if (!login()) {
                return -1;
            }
        }

        try {
            NET_DVR_PREVIEWINFO_V20 previewInfo = new NET_DVR_PREVIEWINFO_V20();
            previewInfo.lChannel = channelNo;
            previewInfo.dwStreamType = streamType;
            previewInfo.dwLinkMode = 0;
            previewInfo.bBlocked = 1;
            previewInfo.hHwnd = surface;

            int playHandle = HCNetSDK.getInstance().NET_DVR_RealPlay_V40(userId, previewInfo, null);
            if (playHandle >= 0) {
                try {
                    HCNetSDKJNAInstance.getInstance().NET_DVR_OpenSound((short) playHandle);
                } catch (Throwable ignored) {}
                AppLogger.i(MODULE, "启动实时预览成功 (Surface): handle=" + playHandle + ", ch=" + channelNo);
                return playHandle;
            } else {
                int err = HCNetSDK.getInstance().NET_DVR_GetLastError();
                AppLogger.e(MODULE, "启动实时预览失败 (Surface): ch=" + channelNo + ", err=" + err);
                return -1;
            }
        } catch (Throwable t) {
            AppLogger.e(MODULE, "startRealPlay 异常: " + t.getMessage(), t);
            return -1;
        }
    }

    @Override
    public boolean stopRealPlay(int playHandle) {
        if (playHandle < 0) return false;
        try {
            return HCNetSDK.getInstance().NET_DVR_StopRealPlay(playHandle);
        } catch (Throwable t) {
            AppLogger.e(MODULE, "stopRealPlay 异常: " + t.getMessage());
            return false;
        }
    }

    @Override
    public boolean capturePicture(int playHandle, String savePath) {
        if (playHandle < 0 || savePath == null) return false;
        try {
            return HCNetSDKJNAInstance.getInstance().NET_DVR_CapturePicture(playHandle, savePath);
        } catch (Throwable t) {
            AppLogger.e(MODULE, "抓图异常: " + t.getMessage());
            return false;
        }
    }

    @Override
    public boolean startRecord(int playHandle, String savePath) {
        if (playHandle < 0 || savePath == null) return false;
        try {
            return HCNetSDKJNAInstance.getInstance().NET_DVR_SaveRealData_V30(playHandle, 0, savePath);
        } catch (Throwable t) {
            AppLogger.e(MODULE, "录像开启异常: " + t.getMessage());
            return false;
        }
    }

    @Override
    public boolean stopRecord(int playHandle) {
        if (playHandle < 0) return false;
        try {
            return HCNetSDK.getInstance().NET_DVR_StopSaveRealData(playHandle);
        } catch (Throwable t) {
            AppLogger.e(MODULE, "录像停止异常: " + t.getMessage());
            return false;
        }
    }

    @Override
    public boolean ptzControl(int channelNo, com.weviewcam.client.core.model.PTZCommand command, boolean stop, int speed, int playHandle) {
        if (!isLoggedIn || userId < 0) return false;

        int hikCmd = mapPTZCommand(command);
        if (hikCmd < 0) return false;

        int dwStop = stop ? 1 : 0;
        int clampedSpeed = Math.max(1, Math.min(7, speed));

        try {
            return HCNetSDK.getInstance().NET_DVR_PTZControlWithSpeed_Other(
                    userId,
                    channelNo,
                    hikCmd,
                    dwStop,
                    clampedSpeed
            );
        } catch (Throwable t) {
            AppLogger.e(MODULE, "PTZ 控制异常: " + t.getMessage());
            return false;
        }
    }

    private int mapPTZCommand(com.weviewcam.client.core.model.PTZCommand cmd) {
        switch (cmd) {
            case UP: return PTZCommand.TILT_UP;
            case DOWN: return PTZCommand.TILT_DOWN;
            case LEFT: return PTZCommand.PAN_LEFT;
            case RIGHT: return PTZCommand.PAN_RIGHT;
            case UP_LEFT: return PTZCommand.UP_LEFT;
            case UP_RIGHT: return PTZCommand.UP_RIGHT;
            case DOWN_LEFT: return PTZCommand.DOWN_LEFT;
            case DOWN_RIGHT: return PTZCommand.DOWN_RIGHT;
            case ZOOM_IN: return PTZCommand.ZOOM_IN;
            case ZOOM_OUT: return PTZCommand.ZOOM_OUT;
            case FOCUS_NEAR: return PTZCommand.FOCUS_NEAR;
            case FOCUS_FAR: return PTZCommand.FOCUS_FAR;
            case IRIS_OPEN: return PTZCommand.IRIS_OPEN;
            case IRIS_CLOSE: return PTZCommand.IRIS_CLOSE;
            default: return -1;
        }
    }

    @Override
    public List<RecordSegment> findRecords(int channelNo, Date startTime, Date endTime) {
        List<RecordSegment> segments = new ArrayList<>();
        if (!isLoggedIn || userId < 0) {
            if (!login()) return segments;
        }

        try {
            NET_DVR_FILECOND fileCond = new NET_DVR_FILECOND();
            fileCond.lChannel = channelNo;
            fileCond.dwFileType = 0xFF; // All recordings
            fileCond.dwIsLocked = 0xFF; // All
            fileCond.dwUseCardNo = 0;

            fileCond.struStartTime = dateToNetDvrTime(startTime);
            fileCond.struStopTime = dateToNetDvrTime(endTime);

            AppLogger.i(MODULE, "开始检索历史录像: 通道=" + channelNo + ", 时间范围=" + startTime + " 至 " + endTime);

            int findHandle = HCNetSDK.getInstance().NET_DVR_FindFile_V30(userId, fileCond);
            if (findHandle < 0) {
                int err = HCNetSDK.getInstance().NET_DVR_GetLastError();
                AppLogger.w(MODULE, "NET_DVR_FindFile_V30 (0xFF) 失败, 错误码=" + err + ", 尝试 dwFileType=0");
                fileCond.dwFileType = 0; // Fallback to 0 (全部录像)
                findHandle = HCNetSDK.getInstance().NET_DVR_FindFile_V30(userId, fileCond);
            }

            if (findHandle < 0) {
                int err = HCNetSDK.getInstance().NET_DVR_GetLastError();
                AppLogger.e(MODULE, "NET_DVR_FindFile_V30 均失败, 通道=" + channelNo + ", 错误码=" + err);
                return segments;
            }

            NET_DVR_FINDDATA_V30 findData = new NET_DVR_FINDDATA_V30();
            int retries = 0;
            final int maxRetries = 150; // 150 * 25ms = 3.75s 最大等待时间

            while (true) {
                int nextRet = HCNetSDK.getInstance().NET_DVR_FindNextFile_V30(findHandle, findData);
                if (nextRet == HCNetSDK.NET_DVR_FILE_SUCCESS) { // 1000: 找到文件
                    retries = 0;
                    Date segStart = netDvrTimeToDate(findData.struStartTime);
                    Date segEnd = netDvrTimeToDate(findData.struStopTime);

                    int nameLen = 0;
                    if (findData.sFileName != null) {
                        for (int i = 0; i < findData.sFileName.length; i++) {
                            if (findData.sFileName[i] == 0) break;
                            nameLen++;
                        }
                    }
                    String fileName = (nameLen > 0) ? new String(findData.sFileName, 0, nameLen, StandardCharsets.UTF_8).trim() : "rec_" + channelNo;
                    long fileSize = findData.dwFileSize;
                    segments.add(new RecordSegment(channelNo, segStart, segEnd, fileName, fileSize, "schedule"));
                } else if (nextRet == HCNetSDK.NET_DVR_ISFINDING) { // 1002: 正在查找请等待
                    retries++;
                    if (retries > maxRetries) {
                        AppLogger.w(MODULE, "NET_DVR_FindNextFile_V30 检索等待超时");
                        break;
                    }
                    try {
                        Thread.sleep(25);
                    } catch (InterruptedException ignored) {}
                } else if (nextRet == HCNetSDK.NET_DVR_NOMOREFILE) { // 1003: 没有更多文件
                    AppLogger.i(MODULE, "NET_DVR_FindNextFile_V30 检索完成 (NOMOREFILE)");
                    break;
                } else if (nextRet == HCNetSDK.NET_DVR_FILE_NOFIND) { // 1001: 未查找到文件
                    AppLogger.i(MODULE, "NET_DVR_FindNextFile_V30 未查找到文件 (FILE_NOFIND)");
                    break;
                } else if (nextRet == HCNetSDK.NET_DVR_FILE_EXCEPTION) { // 1004: 查找异常
                    AppLogger.w(MODULE, "NET_DVR_FindNextFile_V30 查找文件异常 (FILE_EXCEPTION)");
                    break;
                } else {
                    AppLogger.w(MODULE, "NET_DVR_FindNextFile_V30 未知返回状态: " + nextRet);
                    break;
                }
            }

            HCNetSDK.getInstance().NET_DVR_FindClose_V30(findHandle);
            AppLogger.i(MODULE, "通道 " + channelNo + " 录像检索结束, 共检出 " + segments.size() + " 段录像");
        } catch (Throwable t) {
            AppLogger.e(MODULE, "findRecords 异常: " + t.getMessage(), t);
        }

        return segments;
    }

    @Override
    public int startPlaybackByTime(int channelNo, Surface surface, Date startTime, Date endTime) {
        if (!isLoggedIn || userId < 0) {
            if (!login()) return -1;
        }

        try {
            NET_DVR_VOD_PARA vodPara = new NET_DVR_VOD_PARA();
            if (vodPara.struIDInfo == null) {
                vodPara.struIDInfo = new NET_DVR_STREAM_INFO();
            }
            vodPara.struIDInfo.dwChannel = channelNo;
            vodPara.hWnd = surface;
            vodPara.struBeginTime = dateToNetDvrTime(startTime);
            vodPara.struEndTime = dateToNetDvrTime(endTime);

            int playbackId = HCNetSDK.getInstance().NET_DVR_PlayBackByTime_V40(userId, vodPara);
            if (playbackId < 0) {
                int err = HCNetSDK.getInstance().NET_DVR_GetLastError();
                AppLogger.e(MODULE, "NET_DVR_PlayBackByTime_V40 失败, err=" + err);
                return -1;
            }

            boolean startOk = HCNetSDK.getInstance().NET_DVR_PlayBackControl_V40(
                    playbackId,
                    PlaybackControlCommand.NET_DVR_PLAYSTART,
                    null,
                    0,
                    null
            );

            if (!startOk) {
                HCNetSDK.getInstance().NET_DVR_StopPlayBack(playbackId);
                return -1;
            }

            try {
                HCNetSDKJNAInstance.getInstance().NET_DVR_OpenSound((short) playbackId);
            } catch (Throwable ignored) {}

            AppLogger.i(MODULE, "录像回放启动成功: playbackId=" + playbackId);
            return playbackId;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "startPlaybackByTime 异常: " + t.getMessage(), t);
            return -1;
        }
    }

    @Override
    public boolean playbackControl(int playbackHandle, PlaybackCommand command, int param) {
        if (playbackHandle < 0) return false;

        try {
            int cmdCode;
            switch (command) {
                case START:
                case RESTART:
                    cmdCode = PlaybackControlCommand.NET_DVR_PLAYRESTART;
                    break;
                case PAUSE:
                    cmdCode = PlaybackControlCommand.NET_DVR_PLAYPAUSE;
                    break;
                case FAST:
                    cmdCode = PlaybackControlCommand.NET_DVR_PLAYFAST;
                    break;
                case SLOW:
                    cmdCode = PlaybackControlCommand.NET_DVR_PLAYSLOW;
                    break;
                case NORMAL:
                    cmdCode = NET_DVR_PLAYNORMAL;
                    break;
                case STEP_FRAME:
                    cmdCode = NET_DVR_PLAYFRAME;
                    break;
                case SET_POS:
                    cmdCode = NET_DVR_PLAYSETPOS;
                    break;
                default:
                    return false;
            }

            return HCNetSDK.getInstance().NET_DVR_PlayBackControl_V40(playbackHandle, cmdCode, null, param, null);
        } catch (Throwable t) {
            AppLogger.e(MODULE, "playbackControl 异常: " + t.getMessage());
            return false;
        }
    }

    @Override
    public int getPlaybackPos(int playbackHandle) {
        if (playbackHandle < 0) return 0;
        try {
            return HCNetSDK.getInstance().NET_DVR_GetPlayBackPos(playbackHandle);
        } catch (Throwable t) {
            return 0;
        }
    }

    @Override
    public boolean stopPlayback(int playbackHandle) {
        if (playbackHandle < 0) return false;
        try {
            return HCNetSDK.getInstance().NET_DVR_StopPlayBack(playbackHandle);
        } catch (Throwable t) {
            return false;
        }
    }

    private NET_DVR_TIME dateToNetDvrTime(Date date) {
        Calendar cal = Calendar.getInstance();
        cal.setTime(date);
        NET_DVR_TIME time = new NET_DVR_TIME();
        time.dwYear = cal.get(Calendar.YEAR);
        time.dwMonth = cal.get(Calendar.MONTH) + 1;
        time.dwDay = cal.get(Calendar.DAY_OF_MONTH);
        time.dwHour = cal.get(Calendar.HOUR_OF_DAY);
        time.dwMinute = cal.get(Calendar.MINUTE);
        time.dwSecond = cal.get(Calendar.SECOND);
        return time;
    }

    private Date netDvrTimeToDate(NET_DVR_TIME time) {
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.YEAR, time.dwYear);
        cal.set(Calendar.MONTH, time.dwMonth - 1);
        cal.set(Calendar.DAY_OF_MONTH, time.dwDay);
        cal.set(Calendar.HOUR_OF_DAY, time.dwHour);
        cal.set(Calendar.MINUTE, time.dwMinute);
        cal.set(Calendar.SECOND, time.dwSecond);
        return cal.getTime();
    }
}

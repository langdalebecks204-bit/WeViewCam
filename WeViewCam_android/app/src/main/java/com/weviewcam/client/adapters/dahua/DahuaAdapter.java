package com.weviewcam.client.adapters.dahua;

import android.view.Surface;
import android.view.SurfaceHolder;

import com.company.NetSDK.CB_fDataCallBack;
import com.company.NetSDK.CB_fDisConnect;
import com.company.NetSDK.CB_fDownLoadPosCallBack;
import com.company.NetSDK.CB_fHaveReConnect;
import com.company.NetSDK.CB_fRealDataCallBackEx;
import com.company.NetSDK.EM_LOGIN_SPAC_CAP_TYPE;
import com.company.NetSDK.EM_QUERY_RECORD_TYPE;
import com.company.NetSDK.EM_USEDEV_MODE;
import com.company.NetSDK.INetSDK;
import com.company.NetSDK.NET_DEVICEINFO_Ex;
import com.company.NetSDK.NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY;
import com.company.NetSDK.NET_IN_PLAY_BACK_BY_TIME_INFO;
import com.company.NetSDK.NET_IN_QUERY_RECORD_FILE_EX;
import com.company.NetSDK.NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY;
import com.company.NetSDK.NET_OUT_PLAY_BACK_BY_TIME_INFO;
import com.company.NetSDK.NET_OUT_QUERY_RECORD_FILE_EX;
import com.company.NetSDK.NET_RECORD_TYPE;
import com.company.NetSDK.NET_RECORDFILE_INFO;
import com.company.NetSDK.NET_RECORDFILE_INFOEX;
import com.company.NetSDK.NET_TIME;
import com.company.NetSDK.SDK_PTZ_ControlType;
import com.company.NetSDK.SDK_RealPlayType;
import com.company.PlaySDK.Constants;
import com.company.PlaySDK.IPlaySDK;
import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PTZCommand;
import com.weviewcam.client.core.model.PlaybackCommand;
import com.weviewcam.client.core.model.RecordSegment;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Dahua (NetSDK) Device Adapter for Android.
 * Integrates official Dahua INetSDK and IPlaySDK for real video preview,
 * PTZ control, record query and time-based playback.
 */
public class DahuaAdapter extends BaseDeviceAdapter {
    private static final String MODULE = "DahuaAdapter";
    private static boolean isSdkInitialized = false;

    private static final AtomicInteger SESSION_GEN = new AtomicInteger(3000);
    private final Map<Integer, RealSession> realSessions = new ConcurrentHashMap<>();
    private final Map<Integer, PlaybackSession> playbackSessions = new ConcurrentHashMap<>();

    private long loginHandle = 0;
    private NET_DEVICEINFO_Ex netDeviceInfoEx;

    private static class RealSession {
        int sessionKey;
        long realHandle;
        int playPort;
        CB_fRealDataCallBackEx callback;
        Surface surface;
    }

    private static class PlaybackSession {
        int sessionKey;
        long pbHandle;
        int playPort;
        CB_fDataCallBack callback;
        Surface surface;
        Date startTime;
        Date endTime;
    }

    public DahuaAdapter(DeviceInfo deviceInfo) {
        super(deviceInfo);
        initSdkOnce();
    }

    private static synchronized void initSdkOnce() {
        if (!isSdkInitialized) {
            AppLogger.i(MODULE, "[SDK_INIT 1] 进入 initSdkOnce，准备初始化大华 SDK...");
            try {
                // 1. 显式预加载底层依赖库，保证符号链接解析顺畅
                String[] earlyLibs = {"crypto", "ssl", "avnetsdk", "StreamConvertor", "hwdec", "play", "jniplay"};
                for (String lib : earlyLibs) {
                    try {
                        System.loadLibrary(lib);
                    } catch (Throwable ignored) {}
                }

                // 2. 按照官方规范加载 INetSDK 核心库
                AppLogger.i(MODULE, "[SDK_INIT 2] 正在执行 INetSDK.LoadLibrarys()...");
                try {
                    INetSDK.LoadLibrarys();
                    AppLogger.i(MODULE, "[SDK_INIT 2.1] INetSDK.LoadLibrarys() 执行成功!");
                } catch (Throwable t) {
                    AppLogger.w(MODULE, "[SDK_INIT 2.2] INetSDK.LoadLibrarys 异常: " + t.getMessage());
                }

                // 3. 注册有效的断线与重连回调对象 (避免 JNI 传 null 导致崩溃)
                CB_fDisConnect disConnectCb = (lLoginHandle, szDeviceIp, nDevicePort) ->
                        AppLogger.w(MODULE, "[网络断开] 大华设备连接中断: " + szDeviceIp + ":" + nDevicePort);

                CB_fHaveReConnect reConnectCb = (lLoginHandle, szDeviceIp, nDevicePort) ->
                        AppLogger.i(MODULE, "[网络恢复] 大华设备重连成功: " + szDeviceIp + ":" + nDevicePort);

                AppLogger.i(MODULE, "[SDK_INIT 3] 正在执行 INetSDK.Init...");
                boolean initRet = false;
                try {
                    initRet = INetSDK.Init(disConnectCb);
                    AppLogger.i(MODULE, "[SDK_INIT 3.1] INetSDK.Init 返回: " + initRet);
                } catch (Throwable t) {
                    AppLogger.e(MODULE, "[SDK_INIT 3.2] INetSDK.Init 发生异常: " + t.getMessage(), t);
                }

                if (initRet) {
                    try {
                        int pParam = com.company.NetSDK.EM_OPTTYPE_MOBILE_TYPE.OPTTYPE_MOBILE_DEVICE_ATTR
                                | com.company.NetSDK.EM_OPTTYPE_MOBILE_TYPE.OPTTYPE_MOBILE_DEVICE_SN
                                | com.company.NetSDK.EM_OPTTYPE_MOBILE_TYPE.OPTTYPE_MOBILE_DISK_INFO
                                | com.company.NetSDK.EM_OPTTYPE_MOBILE_TYPE.OPTTYPE_MOBILE_DIGITAL_NUM
                                | com.company.NetSDK.EM_OPTTYPE_MOBILE_TYPE.OPTTYPE_MOBILE_ALARM_IO
                                | com.company.NetSDK.EM_OPTTYPE_MOBILE_TYPE.OPTTYPE_MOBILE_DEVICE_ABILITY
                                | com.company.NetSDK.EM_OPTTYPE_MOBILE_TYPE.OPTTYPE_MOBILE_STATE_SOFTWARE;
                        INetSDK.SetOptimizeMode(com.company.NetSDK.EM_OPTIMIZE_TYPE.EM_OPT_TYPE_MOBILE_OPTION, pParam);
                        INetSDK.SetAutoReconnect(reConnectCb);

                        AppLogger.i(MODULE, "[SDK_INIT 4] 正在配置网络超时参数...");
                        com.company.NetSDK.NET_PARAM stNetParam = new com.company.NetSDK.NET_PARAM();
                        stNetParam.nConnectTime = 10000;
                        stNetParam.nWaittime = 10000;
                        stNetParam.nSearchRecordTime = 30000;
                        INetSDK.SetNetworkParam(stNetParam);
                        AppLogger.i(MODULE, "[SDK_INIT 4.1] 网络超时参数配置成功!");
                    } catch (Throwable t) {
                        AppLogger.w(MODULE, "[SDK_INIT 4.2] SetNetworkParam 异常: " + t.getMessage());
                    }
                }
                AppLogger.i(MODULE, "[SDK_INIT 5] 大华 INetSDK 初始化完毕, isSdkInitialized=" + initRet);
                isSdkInitialized = initRet;
            } catch (Throwable t) {
                AppLogger.w(MODULE, "[SDK_INIT ERR] 大华 INetSDK 初始化未捕获异常: " + t.getMessage());
                isSdkInitialized = false;
            }
        }
    }

    @Override
    public boolean login() {
        AppLogger.i(MODULE, "[LOGIN 0] 进入 login()，当前登录状态=" + isLoggedIn + ", loginHandle=" + loginHandle);
        if (isLoggedIn && loginHandle != 0) {
            return true;
        }

        initSdkOnce();
        if (!isSdkInitialized) {
            AppLogger.w(MODULE, "[LOGIN 1] 大华 SDK 初始化失败，终止登录流程");
            isLoggedIn = false;
            deviceInfo.setConnected(false);
            return false;
        }
        try {
            String ip = deviceInfo.getIp();
            int port = deviceInfo.getPort() > 0 ? deviceInfo.getPort() : 37777;
            String user = deviceInfo.getUsername() != null ? deviceInfo.getUsername() : "admin";
            String pass = deviceInfo.getPassword() != null ? deviceInfo.getPassword() : "";

            AppLogger.i(MODULE, "[LOGIN 2] 准备发起大华设备登录: " + ip + ":" + port + ", 用户=" + user);

            // 1. 优先采用大华官方最高兼容性高安全认证登录接口 LoginWithHighLevelSecurity
            try {
                NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY stuIn = new NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY();
                System.arraycopy(ip.getBytes(), 0, stuIn.szIP, 0, ip.getBytes().length);
                stuIn.nPort = port;
                System.arraycopy(user.getBytes(), 0, stuIn.szUserName, 0, user.getBytes().length);
                System.arraycopy(pass.getBytes(), 0, stuIn.szPassword, 0, pass.getBytes().length);
                stuIn.emSpecCap = EM_LOGIN_SPAC_CAP_TYPE.EM_LOGIN_SPEC_CAP_TCP;

                NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY stuOut = new NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY();

                AppLogger.i(MODULE, "[LOGIN 2.1] 正在执行 INetSDK.LoginWithHighLevelSecurity...");
                loginHandle = INetSDK.LoginWithHighLevelSecurity(stuIn, stuOut);
                AppLogger.i(MODULE, "[LOGIN 2.2] LoginWithHighLevelSecurity 返回 handle=" + loginHandle);

                if (loginHandle != 0) {
                    netDeviceInfoEx = stuOut.stuDeviceInfo;
                    try {
                        INetSDK.SetLocalMode(loginHandle, com.company.NetSDK.EM_LOCAL_MODE.EM_LOCAL_PLAY_FLAG_MODE, 0x01 | 0x02);
                        INetSDK.SetLocalMode(loginHandle, com.company.NetSDK.EM_LOCAL_MODE.EM_LOCAL_PLAYBACK_FLAG_MODE, 0x01);
                    } catch (Throwable ignored) {}
                    isLoggedIn = true;
                    deviceInfo.setConnected(true);
                    AppLogger.i(MODULE, "[LOGIN 2.3] 大华设备高安全认证登录成功! loginHandle=" + loginHandle +
                            ", 通道数=" + (netDeviceInfoEx != null ? netDeviceInfoEx.nChanNum : 0));
                    return true;
                }
            } catch (Throwable t) {
                AppLogger.w(MODULE, "[LOGIN 2.4] LoginWithHighLevelSecurity 抛出异常: " + t.getMessage());
                loginHandle = 0;
            }

            int lastErr1 = INetSDK.GetLastError();
            AppLogger.w(MODULE, "[LOGIN 3] 大华 LoginWithHighLevelSecurity 失败 (错误码=" + lastErr1 + ")，准备降级尝试 LoginEx2...");

            // 2. 降级尝试 LoginEx2
            netDeviceInfoEx = new NET_DEVICEINFO_Ex();
            try {
                loginHandle = INetSDK.LoginEx2(ip, port, user, pass, EM_LOGIN_SPAC_CAP_TYPE.EM_LOGIN_SPEC_CAP_TCP, null, netDeviceInfoEx, null);
                if (loginHandle != 0) {
                    try {
                        INetSDK.SetLocalMode(loginHandle, com.company.NetSDK.EM_LOCAL_MODE.EM_LOCAL_PLAY_FLAG_MODE, 0x01 | 0x02);
                        INetSDK.SetLocalMode(loginHandle, com.company.NetSDK.EM_LOCAL_MODE.EM_LOCAL_PLAYBACK_FLAG_MODE, 0x01);
                    } catch (Throwable ignored) {}
                    isLoggedIn = true;
                    deviceInfo.setConnected(true);
                    AppLogger.i(MODULE, "[LOGIN 3.1] 大华设备 LoginEx2 登录成功! loginHandle=" + loginHandle +
                            ", 通道数=" + netDeviceInfoEx.nChanNum);
                    return true;
                }
            } catch (Throwable t) {
                AppLogger.w(MODULE, "[LOGIN 3.2] INetSDK.LoginEx2 异常: " + t.getMessage());
            }

            // 3. 终极降级尝试经典基础 Login 接口
            try {
                com.company.NetSDK.NET_DEVICEINFO classicDevInfo = new com.company.NetSDK.NET_DEVICEINFO();
                AppLogger.i(MODULE, "[LOGIN 4.1] 正在执行经典 INetSDK.Login...");
                loginHandle = INetSDK.Login(ip, port, user, pass, classicDevInfo, null);
                AppLogger.i(MODULE, "[LOGIN 4.2] 经典 INetSDK.Login 返回 handle=" + loginHandle);
                if (loginHandle != 0) {
                    netDeviceInfoEx = new NET_DEVICEINFO_Ex();
                    netDeviceInfoEx.nChanNum = classicDevInfo.byChanNum > 0 ? classicDevInfo.byChanNum : 1;
                    try {
                        INetSDK.SetLocalMode(loginHandle, com.company.NetSDK.EM_LOCAL_MODE.EM_LOCAL_PLAY_FLAG_MODE, 0x01 | 0x02);
                        INetSDK.SetLocalMode(loginHandle, com.company.NetSDK.EM_LOCAL_MODE.EM_LOCAL_PLAYBACK_FLAG_MODE, 0x01);
                    } catch (Throwable ignored) {}
                    isLoggedIn = true;
                    deviceInfo.setConnected(true);
                    AppLogger.i(MODULE, "[LOGIN 4.3] 大华设备经典 Login 登录成功! loginHandle=" + loginHandle +
                            ", 通道数=" + netDeviceInfoEx.nChanNum);
                    return true;
                }
            } catch (Throwable t) {
                AppLogger.w(MODULE, "[LOGIN 4.4] INetSDK.Login 降级异常: " + t.getMessage());
            }

            int lastErr = INetSDK.GetLastError();
            AppLogger.e(MODULE, "[LOGIN 5] 大华设备登录失败: " + ip + ":" + port + ", 最终错误码=" + lastErr);
            isLoggedIn = false;
            deviceInfo.setConnected(false);
            return false;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "[LOGIN ERR] 大华登录未捕获异常: " + t.getMessage(), t);
            isLoggedIn = false;
            deviceInfo.setConnected(false);
            return false;
        }
    }

    @Override
    public boolean logout() {
        try {
            for (Integer key : realSessions.keySet()) {
                stopRealPlay(key);
            }
            for (Integer key : playbackSessions.keySet()) {
                stopPlayback(key);
            }

            if (loginHandle != 0) {
                long handle = loginHandle;
                loginHandle = 0;
                try {
                    boolean ret = INetSDK.Logout(handle);
                    AppLogger.i(MODULE, "大华设备登出结果: " + ret);
                } catch (Throwable t) {
                    AppLogger.w(MODULE, "INetSDK.Logout 告警: " + t.getMessage());
                }
            }
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华登出异常: " + t.getMessage(), t);
        }
        isLoggedIn = false;
        deviceInfo.setConnected(false);
        return true;
    }

    @Override
    public List<ChannelInfo> getChannels() {
        List<ChannelInfo> channelList = new ArrayList<>();
        if (!isLoggedIn || loginHandle == 0) {
            if (!login()) return channelList;
        }

        int totalChannels = 1;
        if (netDeviceInfoEx != null && netDeviceInfoEx.nChanNum > 0) {
            totalChannels = netDeviceInfoEx.nChanNum;
        }

        String devId = deviceInfo.getDeviceId() != null ? deviceInfo.getDeviceId() : "device";
        for (int i = 1; i <= totalChannels; i++) {
            ChannelInfo ch = new ChannelInfo(
                    i,
                    "通道 " + i,
                    true,
                    true,
                    devId
            );
            channelList.add(ch);
        }
        AppLogger.i(MODULE, "大华通道枚举完成, 共 " + channelList.size() + " 个通道");
        return channelList;
    }

    @Override
    public int startRealPlay(int channelNo, SurfaceHolder surfaceHolder, int streamType) {
        Surface surface = surfaceHolder != null ? surfaceHolder.getSurface() : null;
        return startRealPlay(channelNo, surface, streamType);
    }

    @Override
    public int startRealPlay(int channelNo, Surface surface, int streamType) {
        if (!isSdkInitialized) {
            initSdkOnce();
        }
        if (!isSdkInitialized) {
            AppLogger.e(MODULE, "大华 SDK 未初始化，无法启动实时预览");
            return -1;
        }
        if (!isLoggedIn || loginHandle == 0) {
            if (!login()) return -1;
        }
        if (surface == null || !surface.isValid()) {
            AppLogger.e(MODULE, "startRealPlay 失败: surface 为空或无效");
            return -1;
        }

        int dhChannel = channelNo > 0 ? channelNo - 1 : 0;
        int dhStream = (streamType == 0) ? SDK_RealPlayType.SDK_RType_Realplay_0 : SDK_RealPlayType.SDK_RType_Realplay_1;

        try {
            int playPort = IPlaySDK.PLAYGetFreePort();
            if (playPort < 0) {
                AppLogger.e(MODULE, "PLAYGetFreePort 获取空闲播放端口失败");
                return -1;
            }

            boolean streamOpened = (IPlaySDK.PLAYOpenStream(playPort, null, 0, 1024 * 1024 * 2) != 0);
            if (!streamOpened) {
                AppLogger.e(MODULE, "PLAYOpenStream 打开流缓存失败");
                return -1;
            }

            boolean playStarted = (IPlaySDK.PLAYPlay(playPort, surface) != 0);
            if (!playStarted) {
                AppLogger.e(MODULE, "PLAYPlay 绑定 Surface 渲染失败");
                IPlaySDK.PLAYCloseStream(playPort);
                return -1;
            }

            try {
                IPlaySDK.PLAYPlaySoundShare(playPort);
            } catch (Throwable ignored) {}

            long realHandle = INetSDK.RealPlayEx(loginHandle, dhChannel, dhStream);
            if (realHandle == 0) {
                int err = INetSDK.GetLastError();
                AppLogger.e(MODULE, "INetSDK.RealPlayEx 失败: ch=" + channelNo + "(dh=" + dhChannel + "), err=" + err);
                IPlaySDK.PLAYStop(playPort);
                IPlaySDK.PLAYCloseStream(playPort);
                return -1;
            }

            CB_fRealDataCallBackEx dataCb = new CB_fRealDataCallBackEx() {
                @Override
                public void invoke(long rHandle, int dataType, byte[] buffer, int bufSize, int param) {
                    if (dataType == 0 && buffer != null && buffer.length > 0) {
                        IPlaySDK.PLAYInputData(playPort, buffer, buffer.length);
                    }
                }
            };
            INetSDK.SetRealDataCallBackEx(realHandle, dataCb, 1);

            int sessionKey = SESSION_GEN.incrementAndGet();
            RealSession session = new RealSession();
            session.sessionKey = sessionKey;
            session.realHandle = realHandle;
            session.playPort = playPort;
            session.callback = dataCb;
            session.surface = surface;
            realSessions.put(sessionKey, session);

            AppLogger.i(MODULE, "大华实时预览启动成功: session=" + sessionKey + ", ch=" + channelNo +
                    ", realHandle=" + realHandle + ", playPort=" + playPort);
            return sessionKey;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华 startRealPlay 异常: " + t.getMessage(), t);
            return -1;
        }
    }

    @Override
    public boolean stopRealPlay(int playHandle) {
        RealSession session = realSessions.remove(playHandle);
        if (session == null) return false;

        try {
            if (session.realHandle != 0) {
                INetSDK.StopRealPlayEx(session.realHandle);
            }
            if (session.playPort >= 0) {
                try {
                    IPlaySDK.PLAYStopSoundShare(session.playPort);
                } catch (Throwable ignored) {}
                IPlaySDK.PLAYStop(session.playPort);
                IPlaySDK.PLAYCloseStream(session.playPort);
                IPlaySDK.PLAYRefreshPlay(session.playPort);
                IPlaySDK.PLAYReleasePort(session.playPort);
            }
            AppLogger.i(MODULE, "大华实时预览停止成功: session=" + playHandle);
            return true;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华 stopRealPlay 异常: " + t.getMessage(), t);
            return false;
        }
    }

    @Override
    public boolean capturePicture(int playHandle, String savePath) {
        RealSession session = realSessions.get(playHandle);
        if (session != null && session.playPort >= 0) {
            int ret = IPlaySDK.PLAYCatchPic(session.playPort, savePath);
            return ret != 0;
        }
        PlaybackSession pbSession = playbackSessions.get(playHandle);
        if (pbSession != null && pbSession.playPort >= 0) {
            int ret = IPlaySDK.PLAYCatchPic(pbSession.playPort, savePath);
            return ret != 0;
        }
        return false;
    }

    @Override
    public boolean startRecord(int playHandle, String savePath) {
        RealSession session = realSessions.get(playHandle);
        if (session != null && session.playPort >= 0) {
            int ret = IPlaySDK.PLAYStartDataRecord(session.playPort, savePath, 0, null, 0);
            return ret != 0;
        }
        return false;
    }

    @Override
    public boolean stopRecord(int playHandle) {
        RealSession session = realSessions.get(playHandle);
        if (session != null && session.playPort >= 0) {
            int ret = IPlaySDK.PLAYStopDataRecord(session.playPort);
            return ret != 0;
        }
        return false;
    }

    @Override
    public boolean ptzControl(int channelNo, PTZCommand command, boolean stop, int speed, int playHandle) {
        if (!isSdkInitialized || !isLoggedIn || loginHandle == 0 || command == null) return false;
        int dhChannel = channelNo > 0 ? channelNo - 1 : 0;
        int ptzCmd;
        switch (command) {
            case LEFT:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_LEFT_CONTROL;
                break;
            case RIGHT:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_RIGHT_CONTROL;
                break;
            case UP:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_UP_CONTROL;
                break;
            case DOWN:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_DOWN_CONTROL;
                break;
            case ZOOM_IN:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_ZOOM_ADD_CONTROL;
                break;
            case ZOOM_OUT:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_ZOOM_DEC_CONTROL;
                break;
            case FOCUS_NEAR:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_FOCUS_ADD_CONTROL;
                break;
            case FOCUS_FAR:
                ptzCmd = SDK_PTZ_ControlType.SDK_PTZ_FOCUS_DEC_CONTROL;
                break;
            default:
                return false;
        }

        int step = Math.max(1, Math.min(speed, 8));
        try {
            boolean ret = INetSDK.PTZControl(loginHandle, dhChannel, ptzCmd, step, stop);
            if (!ret) {
                int err = INetSDK.GetLastError();
                AppLogger.w(MODULE, "大华 PTZ 控制失败: cmd=" + command + ", stop=" + stop + ", err=" + err);
            }
            return ret;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华 PTZ 控制异常: " + t.getMessage(), t);
            return false;
        }
    }

    @Override
    public List<RecordSegment> findRecords(int channelNo, Date startTime, Date endTime) {
        List<RecordSegment> segments = new ArrayList<>();
        if (!isSdkInitialized || !isLoggedIn || loginHandle == 0) {
            if (!login()) return segments;
        }

        int dhChannel = channelNo > 0 ? channelNo - 1 : 0;
        NET_TIME stTime = dateToNetTime(startTime);
        NET_TIME edTime = dateToNetTime(endTime);

        try {
            // 确保设备工作模式匹配录像流
            try {
                INetSDK.SetDeviceMode(loginHandle, EM_USEDEV_MODE.SDK_RECORD_STREAM_TYPE, 0);
            } catch (Throwable ignored) {}

            AppLogger.i(MODULE, "大华开始检索录像: ch=" + channelNo + "(dh=" + dhChannel + "), time=" + startTime + " ~ " + endTime);

            // 方案 1: 使用扩展结构体查询 QueryRecordFileEx (官方推荐标准接口)
            try {
                NET_IN_QUERY_RECORD_FILE_EX stIn = new NET_IN_QUERY_RECORD_FILE_EX();
                NET_OUT_QUERY_RECORD_FILE_EX stOut = new NET_OUT_QUERY_RECORD_FILE_EX(500);
                stIn.stuStartTime = stTime;
                stIn.stuEndTime = edTime;
                stIn.nChannelId = dhChannel;
                stIn.emRecordFileType = EM_QUERY_RECORD_TYPE.EM_RECORD_TYPE_ALL;
                stIn.pszCardID = "";

                boolean retEx = INetSDK.QueryRecordFileEx(loginHandle, stIn, stOut, 5000);
                if (retEx && stOut.nFileCount > 0) {
                    int count = Math.min(stOut.nFileCount, stOut.nMaxlen);
                    for (int i = 0; i < count; i++) {
                        NET_RECORDFILE_INFOEX ex = stOut.pstuFileinfo[i];
                        if (ex == null || ex.stuRecordFileInfo == null) continue;
                        NET_RECORDFILE_INFO f = ex.stuRecordFileInfo;
                        Date sDate = netTimeToDate(f.starttime);
                        Date eDate = netTimeToDate(f.endtime);
                        if (sDate == null || eDate == null) continue;

                        String nameStr = f.filename != null ? new String(f.filename).trim() : ("record_" + i + ".dav");
                        long byteSize = (long) f.size * 1024L;

                        segments.add(new RecordSegment(
                                channelNo,
                                sDate,
                                eDate,
                                nameStr,
                                byteSize,
                                "schedule"
                        ));
                    }
                    AppLogger.i(MODULE, "大华 QueryRecordFileEx 检索成功, 检出 " + segments.size() + " 条记录");
                }
            } catch (Throwable tEx) {
                AppLogger.w(MODULE, "大华 QueryRecordFileEx 尝试失败, 准备降级: " + tEx.getMessage());
            }

            // 方案 2: 若未检出记录，降级尝试传统 QueryRecordFile 接口
            if (segments.isEmpty()) {
                NET_RECORDFILE_INFO[] fileArray = new NET_RECORDFILE_INFO[500];
                for (int i = 0; i < fileArray.length; i++) {
                    fileArray[i] = new NET_RECORDFILE_INFO();
                }
                Integer fileCount = new Integer(0);

                boolean retLegacy = INetSDK.QueryRecordFile(loginHandle, dhChannel, EM_QUERY_RECORD_TYPE.EM_RECORD_TYPE_ALL, stTime, edTime, "", fileArray, fileCount, 5000, false);
                if (retLegacy && fileCount != null && fileCount > 0) {
                    int count = Math.min(fileCount, fileArray.length);
                    for (int i = 0; i < count; i++) {
                        NET_RECORDFILE_INFO f = fileArray[i];
                        if (f == null || f.starttime == null || f.endtime == null) continue;
                        Date sDate = netTimeToDate(f.starttime);
                        Date eDate = netTimeToDate(f.endtime);
                        if (sDate == null || eDate == null) continue;

                        String nameStr = f.filename != null ? new String(f.filename).trim() : ("record_" + i + ".dav");
                        long byteSize = (long) f.size * 1024L;

                        segments.add(new RecordSegment(
                                channelNo,
                                sDate,
                                eDate,
                                nameStr,
                                byteSize,
                                "schedule"
                        ));
                    }
                    AppLogger.i(MODULE, "大华传统 QueryRecordFile 检索成功, 检出 " + segments.size() + " 条记录");
                } else {
                    int err = INetSDK.GetLastError();
                    AppLogger.i(MODULE, "大华未检出录像: legacyRet=" + retLegacy + ", count=" + fileCount + ", err=" + err);
                }
            }
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华 findRecords 异常: " + t.getMessage(), t);
        }
        return segments;
    }

    @Override
    public int startPlaybackByTime(int channelNo, Surface surface, Date startTime, Date endTime) {
        if (!isSdkInitialized || !isLoggedIn || loginHandle == 0) {
            if (!login()) return -1;
        }
        if (surface == null || !surface.isValid()) {
            AppLogger.e(MODULE, "startPlaybackByTime 失败: surface 为空或无效");
            return -1;
        }

        int dhChannel = channelNo > 0 ? channelNo - 1 : 0;
        NET_TIME stTime = dateToNetTime(startTime);
        NET_TIME edTime = dateToNetTime(endTime);

        try {
            int playPort = IPlaySDK.PLAYGetFreePort();
            if (playPort < 0) {
                AppLogger.e(MODULE, "PLAYGetFreePort 获取空闲端口失败");
                return -1;
            }

            // 1. 设置设备工作模式 (流类型: 0主码流; 录像类型: 0所有录像)
            try {
                INetSDK.SetDeviceMode(loginHandle, EM_USEDEV_MODE.SDK_RECORD_STREAM_TYPE, 0);
                INetSDK.SetDeviceMode(loginHandle, EM_USEDEV_MODE.SDK_RECORD_TYPE, 0);
            } catch (Throwable tMode) {
                AppLogger.w(MODULE, "SetDeviceMode 警告: " + tMode.getMessage());
            }

            // 2. 初始化 PlaySDK 文件流模式
            boolean streamOpened = (IPlaySDK.PLAYOpenStream(playPort, null, 0, 1024 * 1024 * 2) != 0);
            if (!streamOpened) {
                AppLogger.e(MODULE, "PLAYOpenStream 失败");
                IPlaySDK.PLAYReleasePort(playPort);
                return -1;
            }

            // 关键: 设置为文件流解码模式 (Constants.STREAME_FILE = 1)
            IPlaySDK.PLAYSetStreamOpenMode(playPort, Constants.STREAME_FILE);

            boolean playStarted = (IPlaySDK.PLAYPlay(playPort, surface) != 0);
            if (!playStarted) {
                AppLogger.e(MODULE, "PLAYPlay 失败");
                IPlaySDK.PLAYCloseStream(playPort);
                IPlaySDK.PLAYReleasePort(playPort);
                return -1;
            }

            // 开启缓冲与大图自适应模式
            try {
                IPlaySDK.PLAYSetCacheMode(playPort, 1);
                IPlaySDK.PLAYEnableLargePicAdjustment(playPort, 1);
                IPlaySDK.PLAYPlaySoundShare(playPort);
            } catch (Throwable ignored) {}

            // 3. 注册回放数据接收回调
            CB_fDataCallBack dataCb = new CB_fDataCallBack() {
                @Override
                public int invoke(long lRealHandle, int dwDataType, byte[] buffer, int dwBufferSize) {
                    if (dwDataType == 0 && buffer != null && buffer.length > 0) {
                        return IPlaySDK.PLAYInputData(playPort, buffer, buffer.length);
                    }
                    return 1;
                }
            };

            CB_fDownLoadPosCallBack posCb = new CB_fDownLoadPosCallBack() {
                @Override
                public void invoke(long lPlayHandle, int totalSize, int downloadSize) {
                }
            };

            // 4. 发起按时间回放
            NET_IN_PLAY_BACK_BY_TIME_INFO stIn = new NET_IN_PLAY_BACK_BY_TIME_INFO(0);
            stIn.stStartTime = stTime;
            stIn.stStopTime = edTime;
            stIn.fDownLoadDataCallBack = dataCb;
            stIn.cbDownLoadPos = posCb;
            NET_OUT_PLAY_BACK_BY_TIME_INFO stOut = new NET_OUT_PLAY_BACK_BY_TIME_INFO();

            long pbHandle = INetSDK.PlayBackByTimeEx2(loginHandle, dhChannel, stIn, stOut);
            if (pbHandle == 0) {
                // 降级尝试 PlayBackByTimeEx
                pbHandle = INetSDK.PlayBackByTimeEx(loginHandle, dhChannel, stTime, edTime, posCb, dataCb);
            }

            if (pbHandle == 0) {
                int err = INetSDK.GetLastError();
                AppLogger.e(MODULE, "大华 PlayBackByTime 失败: ch=" + channelNo + ", err=" + err);
                try {
                    IPlaySDK.PLAYStopSoundShare(playPort);
                } catch (Throwable ignored) {}
                IPlaySDK.PLAYStop(playPort);
                IPlaySDK.PLAYCloseStream(playPort);
                IPlaySDK.PLAYReleasePort(playPort);
                return -1;
            }

            // 5. 回放句柄建立后重置播放缓冲区
            try {
                IPlaySDK.PLAYSetPlayedTimeEx(playPort, 0);
                IPlaySDK.PLAYResetBuffer(playPort, 1); // BUF_VIDEO_SRC
                IPlaySDK.PLAYResetBuffer(playPort, 3); // BUF_VIDEO_RENDER
            } catch (Throwable ignored) {}

            int sessionKey = SESSION_GEN.incrementAndGet();
            PlaybackSession pbSession = new PlaybackSession();
            pbSession.sessionKey = sessionKey;
            pbSession.pbHandle = pbHandle;
            pbSession.playPort = playPort;
            pbSession.callback = dataCb;
            pbSession.surface = surface;
            pbSession.startTime = startTime;
            pbSession.endTime = endTime;
            playbackSessions.put(sessionKey, pbSession);

            AppLogger.i(MODULE, "大华按时间回放启动成功: session=" + sessionKey + ", pbHandle=" + pbHandle + ", port=" + playPort);
            return sessionKey;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华 startPlaybackByTime 异常: " + t.getMessage(), t);
            return -1;
        }
    }

    @Override
    public boolean playbackControl(int playbackHandle, PlaybackCommand command, int param) {
        PlaybackSession session = playbackSessions.get(playbackHandle);
        if (session == null || session.pbHandle == 0) return false;

        try {
            switch (command) {
                case PAUSE:
                    IPlaySDK.PLAYPause(session.playPort, (short) 1);
                    return INetSDK.PausePlayBack(session.pbHandle, true);
                case RESTART:
                    IPlaySDK.PLAYPause(session.playPort, (short) 0);
                    return INetSDK.PausePlayBack(session.pbHandle, false);
                case FAST:
                    IPlaySDK.PLAYFast(session.playPort);
                    return INetSDK.FastPlayBack(session.pbHandle);
                case SLOW:
                    IPlaySDK.PLAYSlow(session.playPort);
                    return INetSDK.SlowPlayBack(session.pbHandle);
                case NORMAL:
                    return INetSDK.NormalPlayBack(session.pbHandle);
                case STEP_FRAME:
                    return IPlaySDK.PLAYOneByOne(session.playPort) != 0;
                case SET_POS:
                    // param: 0-100 percentage
                    if (session.startTime != null && session.endTime != null) {
                        long totalSec = Math.max(1, (session.endTime.getTime() - session.startTime.getTime()) / 1000L);
                        int offsetSec = (int) (totalSec * param / 100L);
                        return INetSDK.SeekPlayBack(session.pbHandle, offsetSec, 0);
                    }
                    return false;
                default:
                    return false;
            }
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华 playbackControl 异常: " + t.getMessage(), t);
            return false;
        }
    }

    @Override
    public int getPlaybackPos(int playbackHandle) {
        PlaybackSession session = playbackSessions.get(playbackHandle);
        if (session == null || session.playPort < 0) return 0;
        try {
            // 优先通过 PlaySDK OSD 时间获取精确回放进度
            byte[] rr = new byte[24];
            Integer gf = new Integer(0);
            if (IPlaySDK.PLAYQueryInfo(session.playPort, Constants.PLAY_CMD_GetTime, rr, rr.length, gf) != 0) {
                long dwYear = ((long)(rr[3] & 0xff) << 24) + ((long)(rr[2] & 0xff) << 16) + ((long)(rr[1] & 0xff) << 8) + (long)(rr[0] & 0xff);
                long dwMonth = ((long)(rr[7] & 0xff) << 24) + ((long)(rr[6] & 0xff) << 16) + ((long)(rr[5] & 0xff) << 8) + (long)(rr[4] & 0xff);
                long dwDay = ((long)(rr[11] & 0xff) << 24) + ((long)(rr[10] & 0xff) << 16) + ((long)(rr[9] & 0xff) << 8) + (long)(rr[8] & 0xff);
                long dwHour = ((long)(rr[15] & 0xff) << 24) + ((long)(rr[14] & 0xff) << 16) + ((long)(rr[13] & 0xff) << 8) + (long)(rr[12] & 0xff);
                long dwMinute = ((long)(rr[19] & 0xff) << 24) + ((long)(rr[18] & 0xff) << 16) + ((long)(rr[17] & 0xff) << 8) + (long)(rr[16] & 0xff);
                long dwSecond = ((long)(rr[23] & 0xff) << 24) + ((long)(rr[22] & 0xff) << 16) + ((long)(rr[21] & 0xff) << 8) + (long)(rr[20] & 0xff);

                if (dwYear >= 2000 && dwMonth >= 1 && dwMonth <= 12 && dwDay >= 1 && dwDay <= 31) {
                    Calendar cal = Calendar.getInstance();
                    cal.set((int)dwYear, (int)dwMonth - 1, (int)dwDay, (int)dwHour, (int)dwMinute, (int)dwSecond);
                    long currMs = cal.getTimeInMillis();
                    if (session.startTime != null && session.endTime != null) {
                        long totalMs = session.endTime.getTime() - session.startTime.getTime();
                        if (totalMs > 0) {
                            long elapsedMs = currMs - session.startTime.getTime();
                            int progress = (int) (elapsedMs * 100L / totalMs);
                            return Math.min(100, Math.max(0, progress));
                        }
                    }
                }
            }

            int playedSec = IPlaySDK.PLAYGetPlayedTime(session.playPort);
            if (session.startTime != null && session.endTime != null && playedSec > 0) {
                long totalSec = Math.max(1, (session.endTime.getTime() - session.startTime.getTime()) / 1000L);
                int progress = (int) (playedSec * 100L / totalSec);
                return Math.min(100, Math.max(0, progress));
            }
        } catch (Throwable ignored) {}
        return 0;
    }

    @Override
    public boolean stopPlayback(int playbackHandle) {
        PlaybackSession session = playbackSessions.remove(playbackHandle);
        if (session == null) return false;

        try {
            if (session.pbHandle != 0) {
                INetSDK.StopPlayBack(session.pbHandle);
            }
            if (session.playPort >= 0) {
                try {
                    IPlaySDK.PLAYStopSoundShare(session.playPort);
                } catch (Throwable ignored) {}
                IPlaySDK.PLAYStop(session.playPort);
                IPlaySDK.PLAYCloseStream(session.playPort);
                IPlaySDK.PLAYRefreshPlay(session.playPort);
                IPlaySDK.PLAYReleasePort(session.playPort);
            }
            AppLogger.i(MODULE, "大华录像回放已停止: session=" + playbackHandle);
            return true;
        } catch (Throwable t) {
            AppLogger.e(MODULE, "大华 stopPlayback 异常: " + t.getMessage(), t);
            return false;
        }
    }

    private static NET_TIME dateToNetTime(Date date) {
        if (date == null) date = new Date();
        Calendar cal = Calendar.getInstance();
        cal.setTime(date);
        NET_TIME nt = new NET_TIME();
        nt.dwYear = cal.get(Calendar.YEAR);
        nt.dwMonth = cal.get(Calendar.MONTH) + 1;
        nt.dwDay = cal.get(Calendar.DAY_OF_MONTH);
        nt.dwHour = cal.get(Calendar.HOUR_OF_DAY);
        nt.dwMinute = cal.get(Calendar.MINUTE);
        nt.dwSecond = cal.get(Calendar.SECOND);
        return nt;
    }

    private static Date netTimeToDate(NET_TIME nt) {
        if (nt == null || nt.dwYear < 1970) return null;
        Calendar cal = Calendar.getInstance();
        cal.set((int) nt.dwYear, Math.max(0, (int) nt.dwMonth - 1), (int) nt.dwDay, (int) nt.dwHour, (int) nt.dwMinute, (int) nt.dwSecond);
        return cal.getTime();
    }
}

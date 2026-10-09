package com.weviewcam.client.ui.live;

import android.annotation.SuppressLint;
import android.content.res.Configuration;
import android.os.Bundle;
import android.os.Environment;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.Fragment;

import com.weviewcam.client.R;
import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.adapter.DeviceAdapterFactory;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.manager.DeviceManager;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PTZCommand;
import com.weviewcam.client.ui.view.PTZControllerView;
import com.weviewcam.client.ui.view.SurveillanceSurfaceView;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class LiveViewFragment extends Fragment {
    private static final String MODULE = "LiveView";

    private LinearLayout layoutLiveBody;
    private View videoContainer;
    private View gridLayout4;
    private SurveillanceSurfaceView viewportSingle;
    private final SurveillanceSurfaceView[] viewports = new SurveillanceSurfaceView[4];
    private SurveillanceSurfaceView activeViewport;

    private Button btnActiveViewport;
    private Button btnChannelSelect;
    private Button btnLivePlay;
    private Button btnPlayAll;
    private Button btnToggleSplit;
    private Button btnStreamQuality;
    private Button btnLiveSnapshot;
    private Button btnLiveRecord;
    private Button btnTogglePtz;
    private View layoutPtzPanel;
    private PTZControllerView ptzController;
    private SeekBar seekbarPtzSpeed;
    private TextView tvSpeedLabel;

    private boolean is4Split = true;
    private int currentStreamType = 1; // 0-main, 1-sub (default to sub-stream for multi-split fluency)
    private boolean isRecording = false;
    private int ptzSpeed = 4;

    private DeviceManager deviceManager;
    private final List<ChannelInfo> allChannels = new ArrayList<>();
    private final Map<String, BaseDeviceAdapter> adapterCache = new HashMap<>();

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_live_view, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        deviceManager = DeviceManager.getInstance(requireContext());

        initViews(view);
        setupViewports();
        setupListeners();
        loadChannels();
    }

    @Override
    public void onResume() {
        super.onResume();
        if (allChannels.isEmpty()) {
            loadChannels();
        }
    }

    private void initViews(View root) {
        layoutLiveBody = root.findViewById(R.id.layout_live_body);
        videoContainer = root.findViewById(R.id.video_container);
        gridLayout4 = root.findViewById(R.id.grid_layout_4);
        viewportSingle = root.findViewById(R.id.viewport_single);
        viewports[0] = root.findViewById(R.id.viewport_0);
        viewports[1] = root.findViewById(R.id.viewport_1);
        viewports[2] = root.findViewById(R.id.viewport_2);
        viewports[3] = root.findViewById(R.id.viewport_3);

        btnActiveViewport = root.findViewById(R.id.btn_active_viewport);
        btnChannelSelect = root.findViewById(R.id.btn_channel_select);
        btnLivePlay = root.findViewById(R.id.btn_live_play);
        btnPlayAll = root.findViewById(R.id.btn_play_all);
        btnToggleSplit = root.findViewById(R.id.btn_toggle_split);
        btnStreamQuality = root.findViewById(R.id.btn_stream_quality);
        btnStreamQuality.setText(currentStreamType == 0 ? "主码流" : "子码流");
        btnLiveSnapshot = root.findViewById(R.id.btn_live_snapshot);
        btnLiveRecord = root.findViewById(R.id.btn_live_record);
        btnTogglePtz = root.findViewById(R.id.btn_toggle_ptz);
        layoutPtzPanel = root.findViewById(R.id.layout_ptz_panel);
        ptzController = root.findViewById(R.id.ptz_controller);
        seekbarPtzSpeed = root.findViewById(R.id.seekbar_ptz_speed);
        tvSpeedLabel = root.findViewById(R.id.tv_speed_label);

        updateOrientationLayout(getResources().getConfiguration().orientation);
    }

    private void setupViewports() {
        SurveillanceSurfaceView.OnViewportClickListener listener = new SurveillanceSurfaceView.OnViewportClickListener() {
            @Override
            public void onViewportClicked(SurveillanceSurfaceView viewport) {
                if (activeViewport == viewport) {
                    // Tap on already active viewport opens channel picker directly
                    showChannelPickerDialog(viewport);
                } else {
                    selectViewport(viewport);
                }
            }

            @Override
            public void onViewportDoubleClicked(SurveillanceSurfaceView viewport) {
                selectViewport(viewport);
                toggleMaximizeViewport(viewport);
            }

            @Override
            public void onViewportLongClicked(SurveillanceSurfaceView viewport) {
                selectViewport(viewport);
                showChannelPickerDialog(viewport);
            }
        };

        for (int i = 0; i < viewports.length; i++) {
            viewports[i].setViewportIndex(i);
            viewports[i].setOnViewportClickListener(listener);
        }
        viewportSingle.setViewportIndex(-1);
        viewportSingle.setOnViewportClickListener(listener);

        selectViewport(viewports[0]);
    }

    private void selectViewport(SurveillanceSurfaceView viewport) {
        if (viewport == null) return;
        if (activeViewport != null) {
            activeViewport.setSelectedViewport(false);
        }
        activeViewport = viewport;
        activeViewport.setSelectedViewport(true);

        updateActiveViewportBadge();
        updateChannelSelectButton(activeViewport.getChannelInfo());
        updateLivePlayButtonState();
    }

    private void updateActiveViewportBadge() {
        if (btnActiveViewport == null) return;
        if (!is4Split) {
            btnActiveViewport.setText("单画面");
            return;
        }
        int index = getViewportIndex(activeViewport);
        String[] titles = new String[]{"视口 1", "视口 2", "视口 3", "视口 4"};
        if (index >= 0 && index < titles.length) {
            btnActiveViewport.setText(titles[index]);
        } else {
            btnActiveViewport.setText("视口 1");
        }
    }

    private int getViewportIndex(SurveillanceSurfaceView vp) {
        for (int i = 0; i < viewports.length; i++) {
            if (viewports[i] == vp) return i;
        }
        return -1;
    }

    private void updateChannelSelectButton(ChannelInfo info) {
        if (btnChannelSelect == null) return;
        if (info != null) {
            String status = info.isOnline() ? " [在线] ▼" : " [离线] ▼";
            btnChannelSelect.setText(info.getName() + status);
        } else {
            btnChannelSelect.setText("选择通道 ▼");
        }
    }

    private void showChannelPickerDialog(SurveillanceSurfaceView targetViewport) {
        if (allChannels.isEmpty()) {
            Toast.makeText(getContext(), "暂无可用通道，请先在设备管理中添加并测试连接设备", Toast.LENGTH_SHORT).show();
            return;
        }

        SurveillanceSurfaceView vp = (targetViewport != null) ? targetViewport : (activeViewport != null ? activeViewport : viewports[0]);
        int vpIndex = getViewportIndex(vp);
        String vpTitle = (vpIndex >= 0) ? ("【视口 " + (vpIndex + 1) + "】") : "【单画面】";

        String[] channelLabels = new String[allChannels.size()];
        int selectedPos = -1;
        for (int i = 0; i < allChannels.size(); i++) {
            ChannelInfo ch = allChannels.get(i);
            String status = ch.isOnline() ? " [在线]" : " [离线]";
            channelLabels[i] = ch.getName() + status;
            if (vp.getChannelInfo() != null &&
                vp.getChannelInfo().getChannelNo() == ch.getChannelNo() &&
                vp.getChannelInfo().getDeviceId().equals(ch.getDeviceId())) {
                selectedPos = i;
            }
        }

        new androidx.appcompat.app.AlertDialog.Builder(requireContext())
                .setTitle("选择 " + vpTitle + " 播放通道")
                .setSingleChoiceItems(channelLabels, selectedPos, (dialog, which) -> {
                    dialog.dismiss();
                    if (which >= 0 && which < allChannels.size()) {
                        ChannelInfo chosen = allChannels.get(which);
                        selectViewport(vp);
                        startPlayOnViewport(vp, chosen);
                        Toast.makeText(getContext(), "视口 " + (vpIndex + 1) + " 已切换到: " + chosen.getName(), Toast.LENGTH_SHORT).show();
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void toggleMaximizeViewport(SurveillanceSurfaceView viewport) {
        if (is4Split) {
            // Maximize clicked viewport
            is4Split = false;
            btnToggleSplit.setText("单画面");
            gridLayout4.setVisibility(View.GONE);
            viewportSingle.setVisibility(View.VISIBLE);
            boolean wasPlaying = viewport.getPlayHandle() >= 0;
            viewportSingle.setChannelInfo(viewport.getChannelInfo());
            selectViewport(viewportSingle);
            if (wasPlaying) {
                startPlayOnViewport(viewportSingle, viewport.getChannelInfo());
            }
        } else {
            // Restore to 4-split
            is4Split = true;
            btnToggleSplit.setText("四分屏");
            boolean wasPlaying = viewportSingle.getPlayHandle() >= 0;
            viewportSingle.setVisibility(View.GONE);
            gridLayout4.setVisibility(View.VISIBLE);
            selectViewport(viewports[0]);
            if (wasPlaying && viewports[0].getChannelInfo() != null) {
                startPlayOnViewport(viewports[0], viewports[0].getChannelInfo());
            }
        }
        updateActiveViewportBadge();
    }

    @SuppressLint("ClickableViewAccessibility")
    private void setupListeners() {
        btnActiveViewport.setOnClickListener(v -> {
            if (!is4Split) {
                Toast.makeText(getContext(), "当前处于单画面模式，双击画面或点击'四分屏'可返回", Toast.LENGTH_SHORT).show();
                return;
            }
            int current = getViewportIndex(activeViewport);
            int next = (current + 1) % 4;
            selectViewport(viewports[next]);
            Toast.makeText(getContext(), "已切换操作视口: 视口 " + (next + 1), Toast.LENGTH_SHORT).show();
        });

        btnChannelSelect.setOnClickListener(v -> {
            showChannelPickerDialog(activeViewport);
        });

        btnPlayAll.setOnClickListener(v -> togglePlayAll());

        btnLivePlay.setOnClickListener(v -> toggleLivePlay());

        btnToggleSplit.setOnClickListener(v -> {
            if (is4Split) {
                toggleMaximizeViewport(activeViewport != null ? activeViewport : viewports[0]);
            } else {
                toggleMaximizeViewport(viewportSingle);
            }
        });

        btnStreamQuality.setOnClickListener(v -> {
            currentStreamType = (currentStreamType == 0) ? 1 : 0;
            btnStreamQuality.setText(currentStreamType == 0 ? "主码流" : "子码流");
            if (activeViewport != null && activeViewport.getChannelInfo() != null) {
                startPlayOnViewport(activeViewport, activeViewport.getChannelInfo());
            }
        });

        btnLiveSnapshot.setOnClickListener(v -> takeSnapshot());

        btnLiveRecord.setOnClickListener(v -> toggleRecord());

        btnTogglePtz.setOnClickListener(v -> {
            boolean visible = layoutPtzPanel.getVisibility() == View.VISIBLE;
            layoutPtzPanel.setVisibility(visible ? View.GONE : View.VISIBLE);
            btnTogglePtz.setBackgroundTintList(ContextCompat.getColorStateList(
                    requireContext(),
                    visible ? R.color.surveillance_card_alt : R.color.primary
            ));
        });

        seekbarPtzSpeed.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                ptzSpeed = Math.max(1, progress);
                tvSpeedLabel.setText("速度: " + ptzSpeed);
            }
            @Override public void onStartTrackingTouch(SeekBar seekBar) {}
            @Override public void onStopTrackingTouch(SeekBar seekBar) {}
        });

        ptzController.setOnPTZActionListener((command, stop) -> {
            sendPtzCommand(command, stop);
        });

        // Lens Touch buttons
        setupHoldPtzButton(requireView().findViewById(R.id.btn_zoom_in), PTZCommand.ZOOM_IN);
        setupHoldPtzButton(requireView().findViewById(R.id.btn_zoom_out), PTZCommand.ZOOM_OUT);
        setupHoldPtzButton(requireView().findViewById(R.id.btn_focus_near), PTZCommand.FOCUS_NEAR);
        setupHoldPtzButton(requireView().findViewById(R.id.btn_focus_far), PTZCommand.FOCUS_FAR);
        setupHoldPtzButton(requireView().findViewById(R.id.btn_iris_open), PTZCommand.IRIS_OPEN);
        setupHoldPtzButton(requireView().findViewById(R.id.btn_iris_close), PTZCommand.IRIS_CLOSE);
    }

    @SuppressLint("ClickableViewAccessibility")
    private void setupHoldPtzButton(View btn, PTZCommand cmd) {
        if (btn == null) return;
        btn.setOnTouchListener((v, event) -> {
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    sendPtzCommand(cmd, false);
                    return true;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    sendPtzCommand(cmd, true);
                    return true;
            }
            return false;
        });
    }

    private void sendPtzCommand(PTZCommand cmd, boolean stop) {
        if (activeViewport == null || activeViewport.getChannelInfo() == null) return;
        ChannelInfo ch = activeViewport.getChannelInfo();
        BaseDeviceAdapter adapter = getAdapterForDevice(ch.getDeviceId());
        if (adapter != null) {
            adapter.ptzControl(ch.getChannelNo(), cmd, stop, ptzSpeed, activeViewport.getPlayHandle());
        }
    }

    private void takeSnapshot() {
        if (activeViewport == null || activeViewport.getChannelInfo() == null) {
            Toast.makeText(getContext(), "请先选择正在播放的监控视口", Toast.LENGTH_SHORT).show();
            return;
        }

        File dir = new File(requireContext().getExternalFilesDir(Environment.DIRECTORY_PICTURES), "WeViewCam");
        if (!dir.exists()) dir.mkdirs();

        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date());
        File photo = new File(dir, "SNAP_CH" + activeViewport.getChannelInfo().getChannelNo() + "_" + timeStamp + ".jpg");

        BaseDeviceAdapter adapter = getAdapterForDevice(activeViewport.getChannelInfo().getDeviceId());
        if (adapter != null && adapter.capturePicture(activeViewport.getPlayHandle(), photo.getAbsolutePath())) {
            Toast.makeText(getContext(), "抓图成功: " + photo.getName(), Toast.LENGTH_LONG).show();
        } else {
            Toast.makeText(getContext(), "抓图已保存", Toast.LENGTH_SHORT).show();
        }
    }

    private void toggleRecord() {
        if (activeViewport == null || activeViewport.getChannelInfo() == null) {
            Toast.makeText(getContext(), "请先选择正在播放的监控视口", Toast.LENGTH_SHORT).show();
            return;
        }

        BaseDeviceAdapter adapter = getAdapterForDevice(activeViewport.getChannelInfo().getDeviceId());
        if (adapter == null) return;

        if (!isRecording) {
            File dir = new File(requireContext().getExternalFilesDir(Environment.DIRECTORY_MOVIES), "WeViewCam");
            if (!dir.exists()) dir.mkdirs();
            String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date());
            File video = new File(dir, "REC_CH" + activeViewport.getChannelInfo().getChannelNo() + "_" + timeStamp + ".mp4");

            if (adapter.startRecord(activeViewport.getPlayHandle(), video.getAbsolutePath())) {
                isRecording = true;
                btnLiveRecord.setText("停止录像");
                btnLiveRecord.setTextColor(requireContext().getResources().getColor(R.color.status_red));
                Toast.makeText(getContext(), "开始本地录像: " + video.getName(), Toast.LENGTH_SHORT).show();
            }
        } else {
            adapter.stopRecord(activeViewport.getPlayHandle());
            isRecording = false;
            btnLiveRecord.setText("录像");
            btnLiveRecord.setTextColor(requireContext().getResources().getColor(R.color.text_primary));
            Toast.makeText(getContext(), "录像已停止并保存", Toast.LENGTH_SHORT).show();
        }
    }

    private void loadChannels() {
        allChannels.clear();
        for (DeviceInfo dev : deviceManager.getDevices()) {
            allChannels.addAll(dev.getChannels());
        }

        // Assign first 4 channels to viewports WITHOUT auto-playing video
        for (int i = 0; i < 4 && i < allChannels.size(); i++) {
            ChannelInfo ch = allChannels.get(i);
            viewports[i].setChannelInfo(ch);
        }

        if (activeViewport != null) {
            updateChannelSelectButton(activeViewport.getChannelInfo());
        }
        updateLivePlayButtonState();
        updatePlayAllButtonState();
    }

    private void toggleLivePlay() {
        if (activeViewport == null) return;
        if (activeViewport.getPlayHandle() >= 0) {
            stopPlayOnViewport(activeViewport);
        } else {
            ChannelInfo target = activeViewport.getChannelInfo();
            if (target == null && !allChannels.isEmpty()) {
                int idx = getViewportIndex(activeViewport);
                if (idx >= 0 && idx < allChannels.size()) {
                    target = allChannels.get(idx);
                } else {
                    target = allChannels.get(0);
                }
                activeViewport.setChannelInfo(target);
            }
            if (target != null) {
                startPlayOnViewport(activeViewport, target);
            } else {
                showChannelPickerDialog(activeViewport);
            }
        }
    }

    private void togglePlayAll() {
        if (!is4Split) {
            toggleLivePlay();
            return;
        }

        boolean anyPlaying = false;
        for (SurveillanceSurfaceView vp : viewports) {
            if (vp.getPlayHandle() >= 0) {
                anyPlaying = true;
                break;
            }
        }

        if (anyPlaying) {
            for (SurveillanceSurfaceView vp : viewports) {
                stopPlayOnViewport(vp);
            }
            Toast.makeText(getContext(), "已停止所有视口播放", Toast.LENGTH_SHORT).show();
        } else {
            int startedCount = 0;
            for (int i = 0; i < viewports.length; i++) {
                SurveillanceSurfaceView vp = viewports[i];
                ChannelInfo ch = vp.getChannelInfo();
                if (ch == null && i < allChannels.size()) {
                    ch = allChannels.get(i);
                    vp.setChannelInfo(ch);
                }
                if (ch != null) {
                    startPlayOnViewport(vp, ch);
                    startedCount++;
                }
            }
            if (startedCount > 0) {
                Toast.makeText(getContext(), "已开启 " + startedCount + " 个通道分屏实时监控", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(getContext(), "暂无可用通道进行播放", Toast.LENGTH_SHORT).show();
            }
        }
        updatePlayAllButtonState();
    }

    private void stopPlayOnViewport(SurveillanceSurfaceView viewport) {
        if (viewport == null) return;
        int handle = viewport.getPlayHandle();
        if (handle >= 0) {
            if (viewport.getChannelInfo() != null) {
                BaseDeviceAdapter adapter = getAdapterForDevice(viewport.getChannelInfo().getDeviceId());
                if (adapter != null) {
                    adapter.stopRealPlay(handle);
                }
            }
            viewport.setPlayHandle(-1);
        }
        updateLivePlayButtonState();
        updatePlayAllButtonState();
    }

    private void updateLivePlayButtonState() {
        if (btnLivePlay == null || activeViewport == null || getContext() == null) return;
        boolean isPlaying = activeViewport.getPlayHandle() >= 0;
        btnLivePlay.setText(isPlaying ? "停止" : "播放");
        btnLivePlay.setBackgroundTintList(ContextCompat.getColorStateList(
                requireContext(),
                isPlaying ? R.color.status_red : R.color.primary
        ));
        updatePlayAllButtonState();
    }

    private void updatePlayAllButtonState() {
        if (btnPlayAll == null || getContext() == null) return;
        boolean anyPlaying = false;
        for (SurveillanceSurfaceView vp : viewports) {
            if (vp != null && vp.getPlayHandle() >= 0) {
                anyPlaying = true;
                break;
            }
        }
        btnPlayAll.setText(anyPlaying ? "全部停止" : "全部播放");
        btnPlayAll.setTextColor(ContextCompat.getColor(
                requireContext(),
                anyPlaying ? R.color.status_red : R.color.text_primary
        ));
    }

    private void startPlayOnViewport(SurveillanceSurfaceView viewport, ChannelInfo ch) {
        if (viewport == null || ch == null) return;
        viewport.setChannelInfo(ch);
        if (viewport == activeViewport) {
            updateChannelSelectButton(ch);
        }

        // Stop current play handle if active
        if (viewport.getPlayHandle() >= 0) {
            BaseDeviceAdapter oldAdapter = getAdapterForDevice(ch.getDeviceId());
            if (oldAdapter != null) {
                oldAdapter.stopRealPlay(viewport.getPlayHandle());
            }
            viewport.setPlayHandle(-1);
        }

        viewport.postDelayed(() -> {
            if (viewport.isSurfaceReady()) {
                BaseDeviceAdapter adapter = getAdapterForDevice(ch.getDeviceId());
                if (adapter != null) {
                    int handle = adapter.startRealPlay(ch.getChannelNo(), viewport.getHolder(), currentStreamType);
                    viewport.setPlayHandle(handle);
                    updateLivePlayButtonState();
                    updatePlayAllButtonState();
                }
            }
        }, 150);
    }

    private BaseDeviceAdapter getAdapterForDevice(String deviceId) {
        if (deviceId == null) return null;
        if (adapterCache.containsKey(deviceId)) {
            return adapterCache.get(deviceId);
        }
        DeviceInfo dev = deviceManager.getDevice(deviceId);
        if (dev != null) {
            BaseDeviceAdapter adapter = DeviceAdapterFactory.createAdapter(dev);
            adapter.login();
            adapterCache.put(deviceId, adapter);
            return adapter;
        }
        return null;
    }

    @Override
    public void onConfigurationChanged(@NonNull Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        updateOrientationLayout(newConfig.orientation);
    }

    private void updateOrientationLayout(int orientation) {
        if (layoutLiveBody == null || videoContainer == null) return;
        boolean isLandscape = orientation == Configuration.ORIENTATION_LANDSCAPE;
        if (isLandscape) {
            layoutLiveBody.setOrientation(LinearLayout.HORIZONTAL);
            LinearLayout.LayoutParams videoParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1.0f);
            videoContainer.setLayoutParams(videoParams);
            if (layoutPtzPanel != null) {
                LinearLayout.LayoutParams ptzParams = new LinearLayout.LayoutParams(dpToPx(320), ViewGroup.LayoutParams.MATCH_PARENT, 0.0f);
                layoutPtzPanel.setLayoutParams(ptzParams);
            }
        } else {
            layoutLiveBody.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams videoParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1.0f);
            videoContainer.setLayoutParams(videoParams);
            if (layoutPtzPanel != null) {
                LinearLayout.LayoutParams ptzParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT, 0.0f);
                layoutPtzPanel.setLayoutParams(ptzParams);
            }
        }
    }

    private int dpToPx(int dp) {
        return (int) (dp * getResources().getDisplayMetrics().density + 0.5f);
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        for (SurveillanceSurfaceView vp : viewports) {
            if (vp != null && vp.getPlayHandle() >= 0) {
                BaseDeviceAdapter adapter = getAdapterForDevice(vp.getChannelInfo() != null ? vp.getChannelInfo().getDeviceId() : null);
                if (adapter != null) adapter.stopRealPlay(vp.getPlayHandle());
            }
        }
        for (BaseDeviceAdapter ad : adapterCache.values()) {
            ad.logout();
        }
        adapterCache.clear();
    }
}

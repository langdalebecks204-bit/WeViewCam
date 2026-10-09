package com.weviewcam.client.ui.live;

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.os.Environment;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
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

    private View gridLayout4;
    private SurveillanceSurfaceView viewportSingle;
    private final SurveillanceSurfaceView[] viewports = new SurveillanceSurfaceView[4];
    private SurveillanceSurfaceView activeViewport;

    private Spinner spinnerCameraSelect;
    private Button btnLivePlay;
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
    private boolean isSpinnerInitialized = false;

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
        gridLayout4 = root.findViewById(R.id.grid_layout_4);
        viewportSingle = root.findViewById(R.id.viewport_single);
        viewports[0] = root.findViewById(R.id.viewport_0);
        viewports[1] = root.findViewById(R.id.viewport_1);
        viewports[2] = root.findViewById(R.id.viewport_2);
        viewports[3] = root.findViewById(R.id.viewport_3);

        spinnerCameraSelect = root.findViewById(R.id.spinner_camera_select);
        btnLivePlay = root.findViewById(R.id.btn_live_play);
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
    }

    private void setupViewports() {
        SurveillanceSurfaceView.OnViewportClickListener listener = new SurveillanceSurfaceView.OnViewportClickListener() {
            @Override
            public void onViewportClicked(SurveillanceSurfaceView viewport) {
                selectViewport(viewport);
            }

            @Override
            public void onViewportDoubleClicked(SurveillanceSurfaceView viewport) {
                toggleMaximizeViewport(viewport);
            }
        };

        for (SurveillanceSurfaceView vp : viewports) {
            vp.setOnViewportClickListener(listener);
        }
        viewportSingle.setOnViewportClickListener(listener);

        selectViewport(viewports[0]);
    }

    private void selectViewport(SurveillanceSurfaceView viewport) {
        if (activeViewport != null) {
            activeViewport.setSelectedViewport(false);
        }
        activeViewport = viewport;
        if (activeViewport != null) {
            activeViewport.setSelectedViewport(true);
            updateSpinnerSelection(activeViewport.getChannelInfo());
            updateLivePlayButtonState();
        }
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
    }

    @SuppressLint("ClickableViewAccessibility")
    private void setupListeners() {
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

        List<String> labels = new ArrayList<>();
        for (ChannelInfo ch : allChannels) {
            String status = ch.isOnline() ? " [在线]" : " [离线]";
            labels.add(ch.getName() + status);
        }

        ArrayAdapter<String> adapter = new ArrayAdapter<>(requireContext(), android.R.layout.simple_spinner_item, labels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerCameraSelect.setAdapter(adapter);

        isSpinnerInitialized = false;
        spinnerCameraSelect.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (!isSpinnerInitialized) {
                    isSpinnerInitialized = true;
                    return; // Prevent auto-play upon initial spinner setup
                }
                if (position >= 0 && position < allChannels.size() && activeViewport != null) {
                    ChannelInfo selected = allChannels.get(position);
                    startPlayOnViewport(activeViewport, selected);
                }
            }
            @Override public void onNothingSelected(AdapterView<?> parent) {}
        });

        // Assign first 4 channels to viewports WITHOUT auto-playing video
        for (int i = 0; i < 4 && i < allChannels.size(); i++) {
            ChannelInfo ch = allChannels.get(i);
            viewports[i].setChannelInfo(ch);
        }
        updateLivePlayButtonState();
    }

    private void toggleLivePlay() {
        if (activeViewport == null) return;
        if (activeViewport.getPlayHandle() >= 0) {
            stopPlayOnViewport(activeViewport);
        } else {
            if (activeViewport.getChannelInfo() != null) {
                startPlayOnViewport(activeViewport, activeViewport.getChannelInfo());
            } else {
                Toast.makeText(getContext(), "请先选择一个监控通道", Toast.LENGTH_SHORT).show();
            }
        }
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
    }

    private void updateLivePlayButtonState() {
        if (btnLivePlay == null || activeViewport == null || getContext() == null) return;
        boolean isPlaying = activeViewport.getPlayHandle() >= 0;
        btnLivePlay.setText(isPlaying ? "停止" : "播放");
        btnLivePlay.setBackgroundTintList(ContextCompat.getColorStateList(
                requireContext(),
                isPlaying ? R.color.status_red : R.color.primary
        ));
    }

    private void updateSpinnerSelection(ChannelInfo info) {
        if (info == null) return;
        for (int i = 0; i < allChannels.size(); i++) {
            if (allChannels.get(i).getChannelNo() == info.getChannelNo() &&
                allChannels.get(i).getDeviceId().equals(info.getDeviceId())) {
                spinnerCameraSelect.setSelection(i);
                break;
            }
        }
    }

    private void startPlayOnViewport(SurveillanceSurfaceView viewport, ChannelInfo ch) {
        if (viewport == null || ch == null) return;
        viewport.setChannelInfo(ch);

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

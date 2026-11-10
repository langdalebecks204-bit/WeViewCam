package com.weviewcam.client.ui.playback;

import android.app.DatePickerDialog;
import android.os.Bundle;
import android.os.Environment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ExpandableListView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import com.weviewcam.client.R;
import com.weviewcam.client.core.adapter.BaseDeviceAdapter;
import com.weviewcam.client.core.adapter.DeviceAdapterFactory;
import com.weviewcam.client.core.logger.AppLogger;
import com.weviewcam.client.core.manager.DeviceManager;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.PlaybackCommand;
import com.weviewcam.client.core.model.RecordSegment;
import com.weviewcam.client.ui.MainActivity;
import com.weviewcam.client.ui.live.NvrChannelExpandableAdapter;
import com.weviewcam.client.ui.view.SurveillanceSurfaceView;
import com.weviewcam.client.ui.view.TimelineBarView;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class PlaybackFragment extends Fragment implements MainActivity.FullScreenListener {
    private static final String MODULE = "Playback";

    private View layoutPlaybackToolbar;
    private Button btnChannelSelect;
    private Button btnSelectDate;
    private Button btnSearchRecords;
    private SurveillanceSurfaceView viewportPlayback;
    private TextView tvPlaybackTime;
    private TimelineBarView timelineBar;
    private Button btnAspectRatio;
    private Button btnFullscreen;
    private Button btnFullscreenExit;
    private Button btnFullscreenFloating;
    private SurveillanceSurfaceView.AspectRatioMode currentAspectRatio = SurveillanceSurfaceView.AspectRatioMode.RATIO_16_9;

    private Button btnPlay;
    private Button btnStop;
    private Button btnSlow;
    private Button btnFast;
    private Button btnStep;
    private Button btnSnapshot;

    private DeviceManager deviceManager;
    private final List<ChannelInfo> allChannels = new ArrayList<>();
    private ChannelInfo selectedChannel;
    private BaseDeviceAdapter currentAdapter;

    private Calendar selectedCalendar = Calendar.getInstance();
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());
    private final SimpleDateFormat fullDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault());

    private int playbackHandle = -1;
    private boolean isPlaying = false;
    private float currentSpeed = 1.0f;

    private final DeviceManager.OnDeviceChangeListener deviceChangeListener = this::loadChannels;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_playback, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        deviceManager = DeviceManager.getInstance(requireContext());
        deviceManager.addOnDeviceChangeListener(deviceChangeListener);

        initViews(view);
        setupListeners();
        loadChannels();

        // Perform initial search for default date
        searchRecords();
    }

    private void initViews(View root) {
        btnChannelSelect = root.findViewById(R.id.btn_playback_channel_select);
        btnSelectDate = root.findViewById(R.id.btn_select_date);
        btnSearchRecords = root.findViewById(R.id.btn_search_records);
        viewportPlayback = root.findViewById(R.id.viewport_playback);
        tvPlaybackTime = root.findViewById(R.id.tv_playback_time);
        timelineBar = root.findViewById(R.id.timeline_bar);

        layoutPlaybackToolbar = root.findViewById(R.id.layout_playback_toolbar);
        btnPlay = root.findViewById(R.id.btn_playback_play);
        btnStop = root.findViewById(R.id.btn_playback_stop);
        btnSlow = root.findViewById(R.id.btn_playback_slow);
        btnFast = root.findViewById(R.id.btn_playback_fast);
        btnStep = root.findViewById(R.id.btn_playback_step);
        btnSnapshot = root.findViewById(R.id.btn_playback_snapshot);
        btnAspectRatio = root.findViewById(R.id.btn_playback_aspect_ratio);
        btnFullscreen = root.findViewById(R.id.btn_playback_fullscreen);
        btnFullscreenExit = root.findViewById(R.id.btn_playback_fullscreen_exit);
        btnFullscreenFloating = root.findViewById(R.id.btn_playback_fullscreen_floating);
        if (btnAspectRatio != null) {
            btnAspectRatio.setText(currentAspectRatio.getLabel());
        }
        if (viewportPlayback != null) {
            viewportPlayback.setAspectRatioMode(currentAspectRatio);
        }

        btnSelectDate.setText(dateFormat.format(selectedCalendar.getTime()));
    }

    private void setupListeners() {
        if (btnChannelSelect != null) {
            btnChannelSelect.setOnClickListener(v -> showChannelPickerDialog());
        }
        if (viewportPlayback != null) {
            viewportPlayback.setOnClickListener(v -> showChannelPickerDialog());
        }
        btnSelectDate.setOnClickListener(v -> showDatePicker());
        btnSearchRecords.setOnClickListener(v -> searchRecords());
        if (btnAspectRatio != null) {
            btnAspectRatio.setOnClickListener(v -> cycleAspectRatio());
        }
        if (btnFullscreen != null) {
            btnFullscreen.setOnClickListener(v -> toggleFullScreen());
        }
        if (btnFullscreenExit != null) {
            btnFullscreenExit.setOnClickListener(v -> toggleFullScreen());
        }
        if (btnFullscreenFloating != null) {
            btnFullscreenFloating.setOnClickListener(v -> toggleFullScreen());
        }

        // Zoom buttons
        requireView().findViewById(R.id.btn_zoom_24h).setOnClickListener(v -> timelineBar.setZoomDurationHours(24f));
        requireView().findViewById(R.id.btn_zoom_12h).setOnClickListener(v -> timelineBar.setZoomDurationHours(12f));
        requireView().findViewById(R.id.btn_zoom_4h).setOnClickListener(v -> timelineBar.setZoomDurationHours(4f));
        requireView().findViewById(R.id.btn_zoom_1h).setOnClickListener(v -> timelineBar.setZoomDurationHours(1f));

        // Timeline Scrubbing
        timelineBar.setOnTimeSelectedListener((date, isDragging) -> {
            tvPlaybackTime.setText("当前定位: " + fullDateFormat.format(date));
            if (!isDragging) {
                // Seek or start playback at selected time
                seekToTime(date);
            }
        });

        // Playback buttons
        btnPlay.setOnClickListener(v -> togglePlayPause());
        btnStop.setOnClickListener(v -> stopPlayback());
        btnFast.setOnClickListener(v -> fastForward());
        btnSlow.setOnClickListener(v -> slowMotion());
        btnStep.setOnClickListener(v -> stepFrame());
        btnSnapshot.setOnClickListener(v -> takeSnapshot());
    }

    private void loadChannels() {
        allChannels.clear();
        for (DeviceInfo dev : deviceManager.getDevices()) {
            allChannels.addAll(dev.getEnabledChannels());
        }

        if (selectedChannel == null && !allChannels.isEmpty()) {
            selectedChannel = allChannels.get(0);
        }

        updateChannelSelectButton(selectedChannel);

        if (selectedChannel != null) {
            viewportPlayback.setChannelInfo(selectedChannel);
            updateAdapter();
        }
    }

    private void updateChannelSelectButton(ChannelInfo info) {
        if (btnChannelSelect == null) return;
        if (info != null) {
            DeviceInfo dev = (deviceManager != null) ? deviceManager.getDevice(info.getDeviceId()) : null;
            String devName = (dev != null && dev.getName() != null && !dev.getName().trim().isEmpty()) ? dev.getName() : "";
            String label = devName.isEmpty() ? info.getName() : (devName + " - " + info.getName());
            btnChannelSelect.setText(label);
        } else {
            btnChannelSelect.setText("选择通道");
        }
    }

    private void showChannelPickerDialog() {
        List<DeviceInfo> devices = (deviceManager != null) ? deviceManager.getDevices() : new ArrayList<>();
        if (devices.isEmpty() || allChannels.isEmpty()) {
            Toast.makeText(getContext(), "暂无可用通道，请先在设备管理中添加并测试连接设备", Toast.LENGTH_SHORT).show();
            return;
        }

        View dialogView = LayoutInflater.from(requireContext()).inflate(R.layout.dialog_channel_picker, null);
        TextView tvSubtitle = dialogView.findViewById(R.id.tv_dialog_target_viewport);
        ExpandableListView elvTree = dialogView.findViewById(R.id.elv_channel_tree);
        TextView tvEmpty = dialogView.findViewById(R.id.tv_empty_notice);
        Button btnClose = dialogView.findViewById(R.id.btn_dialog_close);

        if (tvSubtitle != null) {
            tvSubtitle.setText("目标: 录像回放");
        }

        androidx.appcompat.app.AlertDialog dialog = new androidx.appcompat.app.AlertDialog.Builder(requireContext())
                .setView(dialogView)
                .create();

        if (dialog.getWindow() != null) {
            dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        }

        List<DeviceInfo> validDevices = new ArrayList<>();
        for (DeviceInfo d : devices) {
            if (d.getEnabledChannels() != null && !d.getEnabledChannels().isEmpty()) {
                validDevices.add(d);
            }
        }

        if (validDevices.isEmpty()) {
            elvTree.setVisibility(View.GONE);
            tvEmpty.setVisibility(View.VISIBLE);
        } else {
            elvTree.setVisibility(View.VISIBLE);
            tvEmpty.setVisibility(View.GONE);

            NvrChannelExpandableAdapter adapter = new NvrChannelExpandableAdapter(
                    requireContext(),
                    validDevices,
                    selectedChannel,
                    new NvrChannelExpandableAdapter.OnChannelSelectedListener() {
                        @Override
                        public void onChannelSelected(DeviceInfo device, ChannelInfo chosenChannel) {
                            dialog.dismiss();
                            if (selectedChannel != null && selectedChannel.getChannelNo() == chosenChannel.getChannelNo()
                                    && selectedChannel.getDeviceId() != null && selectedChannel.getDeviceId().equals(chosenChannel.getDeviceId())) {
                                return;
                            }
                            stopPlayback();
                            selectedChannel = chosenChannel;
                            updateChannelSelectButton(selectedChannel);
                            viewportPlayback.setChannelInfo(selectedChannel);
                            updateAdapter();
                            searchRecords();
                            Toast.makeText(getContext(), "已选择: " + device.getName() + " - " + chosenChannel.getName(), Toast.LENGTH_SHORT).show();
                        }

                        @Override
                        public void onChannelLongClicked(DeviceInfo device, ChannelInfo channel) {
                        }
                    }
            );
            elvTree.setAdapter(adapter);

            // 点击某设备时展开该设备并收起其它设备
            elvTree.setOnGroupExpandListener(groupPosition -> {
                for (int i = 0; i < validDevices.size(); i++) {
                    if (i != groupPosition && elvTree.isGroupExpanded(i)) {
                        elvTree.collapseGroup(i);
                    }
                }
            });

            // 默认展开当前选中通道所在的设备
            if (selectedChannel != null) {
                for (int i = 0; i < validDevices.size(); i++) {
                    if (validDevices.get(i).getDeviceId() != null && validDevices.get(i).getDeviceId().equals(selectedChannel.getDeviceId())) {
                        elvTree.expandGroup(i);
                        break;
                    }
                }
            }
        }

        btnClose.setOnClickListener(v -> dialog.dismiss());
        dialog.show();
    }

    private void updateAdapter() {
        new Thread(this::updateAdapterSync).start();
    }

    private synchronized void updateAdapterSync() {
        if (selectedChannel == null) return;
        if (currentAdapter != null) {
            currentAdapter.stopPlayback(playbackHandle);
            currentAdapter.logout();
        }
        DeviceInfo dev = deviceManager.getDevice(selectedChannel.getDeviceId());
        if (dev != null) {
            currentAdapter = DeviceAdapterFactory.createAdapter(dev);
            currentAdapter.login();
        }
    }

    private void showDatePicker() {
        DatePickerDialog dlg = new DatePickerDialog(
                requireContext(),
                (view, year, month, dayOfMonth) -> {
                    selectedCalendar.set(Calendar.YEAR, year);
                    selectedCalendar.set(Calendar.MONTH, month);
                    selectedCalendar.set(Calendar.DAY_OF_MONTH, dayOfMonth);
                    btnSelectDate.setText(dateFormat.format(selectedCalendar.getTime()));
                    timelineBar.resetToDay(selectedCalendar.getTime());
                    searchRecords();
                },
                selectedCalendar.get(Calendar.YEAR),
                selectedCalendar.get(Calendar.MONTH),
                selectedCalendar.get(Calendar.DAY_OF_MONTH)
        );
        dlg.show();
    }

    private void searchRecords() {
        if (selectedChannel == null) return;

        Calendar start = (Calendar) selectedCalendar.clone();
        start.set(Calendar.HOUR_OF_DAY, 0);
        start.set(Calendar.MINUTE, 0);
        start.set(Calendar.SECOND, 0);

        Calendar end = (Calendar) selectedCalendar.clone();
        end.set(Calendar.HOUR_OF_DAY, 23);
        end.set(Calendar.MINUTE, 59);
        end.set(Calendar.SECOND, 59);

        btnSearchRecords.setEnabled(false);
        btnSearchRecords.setText("检索中...");

        new Thread(() -> {
            if (currentAdapter == null) {
                updateAdapterSync();
            }
            List<RecordSegment> records = new ArrayList<>();
            if (currentAdapter != null) {
                records = currentAdapter.findRecords(selectedChannel.getChannelNo(), start.getTime(), end.getTime());
            }
            final List<RecordSegment> finalRecords = records;
            if (getActivity() != null) {
                getActivity().runOnUiThread(() -> {
                    btnSearchRecords.setEnabled(true);
                    btnSearchRecords.setText("检索录像");
                    timelineBar.setRecords(finalRecords);
                    if (finalRecords.isEmpty()) {
                        Toast.makeText(getContext(), "该日期未检索到录像片段 (共 0 段)", Toast.LENGTH_SHORT).show();
                    } else {
                        Toast.makeText(getContext(), "已检索到 " + finalRecords.size() + " 段历史录像", Toast.LENGTH_SHORT).show();
                    }
                });
            }
        }).start();
    }

    private void seekToTime(Date time) {
        if (currentAdapter == null || selectedChannel == null) return;

        if (playbackHandle >= 0) {
            final int oldHandle = playbackHandle;
            new Thread(() -> currentAdapter.stopPlayback(oldHandle)).start();
            playbackHandle = -1;
        }

        Calendar endOfDay = Calendar.getInstance();
        endOfDay.setTime(time);
        endOfDay.set(Calendar.HOUR_OF_DAY, 23);
        endOfDay.set(Calendar.MINUTE, 59);
        endOfDay.set(Calendar.SECOND, 59);

        Runnable startTask = new Runnable() {
            int retries = 0;
            @Override
            public void run() {
                if (viewportPlayback != null && viewportPlayback.isSurfaceReady()) {
                    new Thread(() -> {
                        int handle = currentAdapter.startPlaybackByTime(
                                selectedChannel.getChannelNo(),
                                viewportPlayback.getSurface(),
                                time,
                                endOfDay.getTime()
                        );
                        if (getActivity() != null) {
                            getActivity().runOnUiThread(() -> {
                                playbackHandle = handle;
                                if (playbackHandle >= 0) {
                                    isPlaying = true;
                                    btnPlay.setText("暂停");
                                    viewportPlayback.setPlayHandle(playbackHandle);
                                    AppLogger.i(MODULE, "回放启动成功: handle=" + playbackHandle);
                                } else {
                                    isPlaying = false;
                                    btnPlay.setText("播放");
                                    Toast.makeText(getContext(), "回放启动失败，请检查网络或录像段", Toast.LENGTH_SHORT).show();
                                    AppLogger.e(MODULE, "回放启动失败: startPlaybackByTime 返回 -1");
                                }
                            });
                        }
                    }).start();
                } else if (retries < 5 && viewportPlayback != null) {
                    retries++;
                    viewportPlayback.postDelayed(this, 150);
                } else {
                    AppLogger.w(MODULE, "seekToTime 放弃: SurfaceView 持续未就绪");
                }
            }
        };

        if (viewportPlayback != null) {
            viewportPlayback.postDelayed(startTask, 50);
        }
    }

    private void togglePlayPause() {
        if (currentAdapter == null || playbackHandle < 0) {
            seekToTime(timelineBar.getCurrentTime());
            return;
        }

        if (isPlaying) {
            currentAdapter.playbackControl(playbackHandle, PlaybackCommand.PAUSE, 0);
            isPlaying = false;
            btnPlay.setText("播放");
        } else {
            currentAdapter.playbackControl(playbackHandle, PlaybackCommand.START, 0);
            isPlaying = true;
            btnPlay.setText("暂停");
        }
    }

    private void stopPlayback() {
        if (currentAdapter != null && playbackHandle >= 0) {
            currentAdapter.stopPlayback(playbackHandle);
            playbackHandle = -1;
            isPlaying = false;
            btnPlay.setText("播放");
            viewportPlayback.setPlayHandle(-1);
            Toast.makeText(getContext(), "回放已停止", Toast.LENGTH_SHORT).show();
        }
    }

    private void fastForward() {
        if (currentAdapter != null && playbackHandle >= 0) {
            currentSpeed = Math.min(16f, currentSpeed * 2f);
            currentAdapter.playbackControl(playbackHandle, PlaybackCommand.FAST, (int) currentSpeed);
            Toast.makeText(getContext(), "快进 " + (int) currentSpeed + "x", Toast.LENGTH_SHORT).show();
        }
    }

    private void slowMotion() {
        if (currentAdapter != null && playbackHandle >= 0) {
            currentSpeed = Math.max(0.25f, currentSpeed / 2f);
            currentAdapter.playbackControl(playbackHandle, PlaybackCommand.SLOW, 0);
            Toast.makeText(getContext(), "慢放", Toast.LENGTH_SHORT).show();
        }
    }

    private void stepFrame() {
        if (currentAdapter != null && playbackHandle >= 0) {
            currentAdapter.playbackControl(playbackHandle, PlaybackCommand.STEP_FRAME, 0);
            isPlaying = false;
            btnPlay.setText("播放");
        }
    }

    private void takeSnapshot() {
        if (currentAdapter == null || playbackHandle < 0) {
            Toast.makeText(getContext(), "请在回放进行中抓图", Toast.LENGTH_SHORT).show();
            return;
        }
        File dir = new File(requireContext().getExternalFilesDir(Environment.DIRECTORY_PICTURES), "WeViewCam");
        if (!dir.exists()) dir.mkdirs();

        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date());
        File photo = new File(dir, "PLAYBACK_SNAP_" + timeStamp + ".jpg");

        currentAdapter.capturePicture(playbackHandle, photo.getAbsolutePath());
        Toast.makeText(getContext(), "回放抓图已保存", Toast.LENGTH_SHORT).show();
    }

    private void toggleFullScreen() {
        if (getActivity() instanceof MainActivity) {
            ((MainActivity) getActivity()).toggleFullScreen();
        }
    }

    @Override
    public void onFullScreenChanged(boolean isFullScreen) {
        if (layoutPlaybackToolbar != null) {
            layoutPlaybackToolbar.setVisibility(isFullScreen ? View.GONE : View.VISIBLE);
        }
        if (btnFullscreenExit != null) {
            btnFullscreenExit.setVisibility(isFullScreen ? View.VISIBLE : View.GONE);
        }
        if (btnFullscreenFloating != null) {
            btnFullscreenFloating.setText(isFullScreen ? "退出全屏" : "⛶ 全屏");
        }
        if (btnFullscreen != null) {
            btnFullscreen.setText(isFullScreen ? "退出全屏" : "全屏");
        }
    }

    private void cycleAspectRatio() {
        if (currentAspectRatio == SurveillanceSurfaceView.AspectRatioMode.RATIO_16_9) {
            currentAspectRatio = SurveillanceSurfaceView.AspectRatioMode.RATIO_4_3;
        } else {
            currentAspectRatio = SurveillanceSurfaceView.AspectRatioMode.RATIO_16_9;
        }
        if (btnAspectRatio != null) {
            btnAspectRatio.setText(currentAspectRatio.getLabel());
        }
        if (viewportPlayback != null) {
            viewportPlayback.setAspectRatioMode(currentAspectRatio);
        }
        Toast.makeText(getContext(), "录像画面比例: " + currentAspectRatio.getLabel(), Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        if (deviceManager != null) {
            deviceManager.removeOnDeviceChangeListener(deviceChangeListener);
        }
        stopPlayback();
        if (currentAdapter != null) {
            currentAdapter.logout();
        }
    }
}

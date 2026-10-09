package com.weviewcam.client.ui.playback;

import android.app.DatePickerDialog;
import android.os.Bundle;
import android.os.Environment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.Spinner;
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
import com.weviewcam.client.ui.view.SurveillanceSurfaceView;
import com.weviewcam.client.ui.view.TimelineBarView;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class PlaybackFragment extends Fragment {
    private static final String MODULE = "Playback";

    private Spinner spinnerChannel;
    private Button btnSelectDate;
    private Button btnSearchRecords;
    private SurveillanceSurfaceView viewportPlayback;
    private TextView tvPlaybackTime;
    private TimelineBarView timelineBar;

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

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_playback, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        deviceManager = DeviceManager.getInstance(requireContext());

        initViews(view);
        setupListeners();
        loadChannels();

        // Perform initial search for default date
        searchRecords();
    }

    private void initViews(View root) {
        spinnerChannel = root.findViewById(R.id.spinner_playback_channel);
        btnSelectDate = root.findViewById(R.id.btn_select_date);
        btnSearchRecords = root.findViewById(R.id.btn_search_records);
        viewportPlayback = root.findViewById(R.id.viewport_playback);
        tvPlaybackTime = root.findViewById(R.id.tv_playback_time);
        timelineBar = root.findViewById(R.id.timeline_bar);

        btnPlay = root.findViewById(R.id.btn_playback_play);
        btnStop = root.findViewById(R.id.btn_playback_stop);
        btnSlow = root.findViewById(R.id.btn_playback_slow);
        btnFast = root.findViewById(R.id.btn_playback_fast);
        btnStep = root.findViewById(R.id.btn_playback_step);
        btnSnapshot = root.findViewById(R.id.btn_playback_snapshot);

        btnSelectDate.setText(dateFormat.format(selectedCalendar.getTime()));
    }

    private void setupListeners() {
        btnSelectDate.setOnClickListener(v -> showDatePicker());
        btnSearchRecords.setOnClickListener(v -> searchRecords());

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
        List<String> labels = new ArrayList<>();
        for (DeviceInfo dev : deviceManager.getDevices()) {
            String devName = (dev.getName() != null && !dev.getName().trim().isEmpty()) ? dev.getName() : "NVR";
            if (dev.getChannels() != null) {
                for (ChannelInfo ch : dev.getChannels()) {
                    allChannels.add(ch);
                    String status = ch.isOnline() ? " [在线]" : " [离线]";
                    labels.add(devName + " - " + ch.getName() + status);
                }
            }
        }

        ArrayAdapter<String> adapter = new ArrayAdapter<>(requireContext(), android.R.layout.simple_spinner_item, labels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerChannel.setAdapter(adapter);

        spinnerChannel.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (position >= 0 && position < allChannels.size()) {
                    selectedChannel = allChannels.get(position);
                    viewportPlayback.setChannelInfo(selectedChannel);
                    updateAdapter();
                    searchRecords();
                }
            }
            @Override public void onNothingSelected(AdapterView<?> parent) {}
        });

        if (!allChannels.isEmpty()) {
            selectedChannel = allChannels.get(0);
            viewportPlayback.setChannelInfo(selectedChannel);
            updateAdapter();
        }
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
            currentAdapter.stopPlayback(playbackHandle);
            playbackHandle = -1;
        }

        Calendar endOfDay = Calendar.getInstance();
        endOfDay.setTime(time);
        endOfDay.set(Calendar.HOUR_OF_DAY, 23);
        endOfDay.set(Calendar.MINUTE, 59);
        endOfDay.set(Calendar.SECOND, 59);

        viewportPlayback.postDelayed(() -> {
            if (viewportPlayback.isSurfaceReady()) {
                playbackHandle = currentAdapter.startPlaybackByTime(
                        selectedChannel.getChannelNo(),
                        viewportPlayback.getSurface(),
                        time,
                        endOfDay.getTime()
                );
                if (playbackHandle >= 0) {
                    isPlaying = true;
                    btnPlay.setText("暂停");
                    viewportPlayback.setPlayHandle(playbackHandle);
                }
            }
        }, 100);
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

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        stopPlayback();
        if (currentAdapter != null) {
            currentAdapter.logout();
        }
    }
}

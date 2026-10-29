package com.weviewcam.client.ui.device;

import android.app.AlertDialog;
import android.app.ProgressDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.content.FileProvider;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.weviewcam.client.R;
import com.weviewcam.client.core.manager.DeviceManager;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.ui.MainActivity;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class DeviceManagementFragment extends Fragment {
    private RecyclerView recyclerView;
    private DeviceAdapter adapter;
    private DeviceManager deviceManager;
    private final List<DeviceInfo> deviceList = new ArrayList<>();
    private List<DeviceInfo> pendingExportDevices = null;

    private ActivityResultLauncher<String> exportDocumentLauncher;
    private ActivityResultLauncher<String[]> importDocumentLauncher;

    @Override
    public void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        exportDocumentLauncher = registerForActivityResult(
                new ActivityResultContracts.CreateDocument("application/json"),
                uri -> {
                    if (uri != null) {
                        writeBackupToUri(uri);
                    }
                }
        );

        importDocumentLauncher = registerForActivityResult(
                new ActivityResultContracts.OpenDocument(),
                uri -> {
                    if (uri != null) {
                        readBackupFromUri(uri);
                    }
                }
        );
    }

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_device_management, container, false);
    }

    private Button btnAutoRefresh;
    private final DeviceManager.OnDeviceChangeListener deviceChangeListener = this::loadDevices;

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        deviceManager = DeviceManager.getInstance(requireContext());

        recyclerView = view.findViewById(R.id.recycler_devices);
        recyclerView.setLayoutManager(new LinearLayoutManager(requireContext()));
        adapter = new DeviceAdapter();
        recyclerView.setAdapter(adapter);

        TextView tvTitle = view.findViewById(R.id.tv_device_center_title);
        if (tvTitle != null) {
            tvTitle.setText("监控设备管理中心 (v" + MainActivity.getAppVersionName(requireContext()) + ")");
        }

        Button btnAdd = view.findViewById(R.id.btn_add_device);
        btnAdd.setOnClickListener(v -> showAddDeviceDialog());

        btnAutoRefresh = view.findViewById(R.id.btn_auto_refresh);
        if (btnAutoRefresh != null) {
            updateAutoRefreshBtnText();
            btnAutoRefresh.setOnClickListener(v -> showAutoRefreshSettingsDialog());
        }

        Button btnBackup = view.findViewById(R.id.btn_backup_devices);
        if (btnBackup != null) {
            btnBackup.setOnClickListener(v -> showBackupOptionsDialog());
        }

        Button btnImport = view.findViewById(R.id.btn_import_devices);
        if (btnImport != null) {
            btnImport.setOnClickListener(v -> importDocumentLauncher.launch(new String[]{"application/json", "text/*", "*/*"}));
        }

        deviceManager.addOnDeviceChangeListener(deviceChangeListener);
        loadDevices();
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        if (deviceManager != null) {
            deviceManager.removeOnDeviceChangeListener(deviceChangeListener);
        }
    }

    private void updateAutoRefreshBtnText() {
        if (btnAutoRefresh == null || deviceManager == null) return;
        int sec = deviceManager.getRefreshIntervalSec();
        if (sec <= 0) {
            btnAutoRefresh.setText("⏱️ 定时: 关");
        } else {
            btnAutoRefresh.setText("⏱️ 定时: " + sec + "s");
        }
    }

    private void showAutoRefreshSettingsDialog() {
        int currentSec = deviceManager.getRefreshIntervalSec();
        final int[] intervals = new int[]{0, 30, 60, 120, 300, -1};
        String[] options = new String[]{
                (currentSec == 0 ? "● " : "○ ") + "禁用 (仅手动刷新)",
                (currentSec == 30 ? "● " : "○ ") + "每 30 秒自动刷新",
                (currentSec == 60 ? "● " : "○ ") + "每 60 秒自动刷新 (默认)",
                (currentSec == 120 ? "● " : "○ ") + "每 2 分钟自动刷新",
                (currentSec == 300 ? "● " : "○ ") + "每 5 分钟自动刷新",
                "🔄 立即刷新所有设备通道状态"
        };

        new AlertDialog.Builder(requireContext())
                .setTitle("定时更新通道在线状态设置")
                .setItems(options, (dialog, which) -> {
                    int chosen = intervals[which];
                    if (chosen == -1) {
                        Toast.makeText(getContext(), "正在全网探测刷新所有设备通道状态...", Toast.LENGTH_SHORT).show();
                        deviceManager.refreshAllDevicesStatus(() -> {
                            loadDevices();
                            Toast.makeText(getContext(), "设备与通道状态已刷新完成", Toast.LENGTH_SHORT).show();
                        });
                    } else {
                        deviceManager.setRefreshIntervalSec(chosen);
                        updateAutoRefreshBtnText();
                        String msg = chosen == 0 ? "已关闭定时刷新通道状态" : ("已设置定时刷新通道状态: 每 " + chosen + " 秒");
                        Toast.makeText(getContext(), msg, Toast.LENGTH_SHORT).show();
                    }
                })
                .setNegativeButton("关闭", null)
                .show();
    }

    private void showBackupOptionsDialog() {
        if (deviceList.isEmpty()) {
            Toast.makeText(getContext(), "当前没有可导出的设备配置", Toast.LENGTH_SHORT).show();
            return;
        }

        int size = deviceList.size();
        String[] deviceNames = new String[size];
        final boolean[] checkedItems = new boolean[size];
        for (int i = 0; i < size; i++) {
            DeviceInfo d = deviceList.get(i);
            deviceNames[i] = d.getName() + " (" + d.getIp() + " | " + d.getChannels().size() + "通道)";
            checkedItems[i] = true;
        }

        AlertDialog dialog = new AlertDialog.Builder(requireContext())
                .setTitle("选择要备份导出的设备")
                .setMultiChoiceItems(deviceNames, checkedItems, (d, which, isChecked) -> checkedItems[which] = isChecked)
                .setPositiveButton("下一步", null)
                .setNeutralButton("全选/反选", null)
                .setNegativeButton("取消", null)
                .create();

        dialog.setOnShowListener(dInterface -> {
            Button btnPositive = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
            btnPositive.setOnClickListener(v -> {
                List<DeviceInfo> selected = new ArrayList<>();
                for (int i = 0; i < checkedItems.length; i++) {
                    if (checkedItems[i]) {
                        selected.add(deviceList.get(i));
                    }
                }
                if (selected.isEmpty()) {
                    Toast.makeText(getContext(), "请至少选择一台需要导出的设备！", Toast.LENGTH_SHORT).show();
                    return;
                }
                dialog.dismiss();
                showBackupTargetOptionsDialog(selected);
            });

            Button btnNeutral = dialog.getButton(AlertDialog.BUTTON_NEUTRAL);
            btnNeutral.setOnClickListener(v -> {
                boolean allChecked = true;
                for (boolean b : checkedItems) {
                    if (!b) {
                        allChecked = false;
                        break;
                    }
                }
                boolean newState = !allChecked;
                for (int i = 0; i < checkedItems.length; i++) {
                    checkedItems[i] = newState;
                    dialog.getListView().setItemChecked(i, newState);
                }
            });
        });

        dialog.show();
    }

    private void showBackupTargetOptionsDialog(List<DeviceInfo> targetDevices) {
        if (targetDevices == null || targetDevices.isEmpty()) {
            return;
        }

        String title = targetDevices.size() == 1
                ? "备份导出设备 [" + targetDevices.get(0).getName() + "]"
                : "备份导出 (" + targetDevices.size() + " 台设备)";

        String[] options = new String[]{"保存为本地备份文件 (.json)", "分享备份文件 (微信/QQ/局域网等)", "复制配置 JSON 到剪贴板"};
        new AlertDialog.Builder(requireContext())
                .setTitle(title)
                .setItems(options, (dialog, which) -> {
                    if (which == 0) {
                        pendingExportDevices = targetDevices;
                        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date());
                        String fileName;
                        if (targetDevices.size() == 1) {
                            String safeName = targetDevices.get(0).getName().replaceAll("[\\\\/:*?\"<>|\\s]", "_");
                            fileName = "weviewcam_backup_" + safeName + "_" + timeStamp + ".json";
                        } else {
                            fileName = "weviewcam_devices_" + timeStamp + ".json";
                        }
                        exportDocumentLauncher.launch(fileName);
                    } else if (which == 1) {
                        shareBackupFile(targetDevices);
                    } else if (which == 2) {
                        copyBackupToClipboard(targetDevices);
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void copyBackupToClipboard(List<DeviceInfo> targetDevices) {
        try {
            String json = deviceManager.exportDevicesJson(targetDevices);
            android.content.ClipboardManager cm = (android.content.ClipboardManager) requireContext().getSystemService(android.content.Context.CLIPBOARD_SERVICE);
            if (cm != null) {
                android.content.ClipData clip = android.content.ClipData.newPlainText("WeViewCam Backup", json);
                cm.setPrimaryClip(clip);
                Toast.makeText(getContext(), "已将 " + targetDevices.size() + " 台设备配置 JSON 复制到剪贴板！可以直接发送给电脑", Toast.LENGTH_LONG).show();
            }
        } catch (Exception e) {
            Toast.makeText(getContext(), "复制失败: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void writeBackupToUri(Uri uri) {
        try {
            List<DeviceInfo> target = pendingExportDevices != null ? pendingExportDevices : deviceList;
            String json = deviceManager.exportDevicesJson(target);
            byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = requireContext().getContentResolver().openOutputStream(uri, "rwt")) {
                if (os == null) {
                    throw new java.io.IOException("无法打开目标文件输出流");
                }
                os.write(bytes);
                os.flush();
                if (os instanceof FileOutputStream) {
                    try {
                        ((FileOutputStream) os).getFD().sync();
                    } catch (Exception ignored) {}
                }
            }
            Toast.makeText(getContext(), "选定的 " + target.size() + " 台设备配置已成功保存到文件 (大小: " + bytes.length + " 字节)", Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(getContext(), "保存备份失败: " + e.getMessage(), Toast.LENGTH_LONG).show();
        } finally {
            pendingExportDevices = null;
        }
    }

    private void shareBackupFile(List<DeviceInfo> targetDevices) {
        try {
            File cacheDir = new File(requireContext().getCacheDir(), "backups");
            if (!cacheDir.exists() && !cacheDir.mkdirs()) {
                throw new IllegalStateException("无法创建临时备份目录");
            }
            String fileName = "weviewcam_devices_backup.json";
            if (targetDevices.size() == 1) {
                String safeName = targetDevices.get(0).getName().replaceAll("[\\\\/:*?\"<>|\\s]", "_");
                fileName = "weviewcam_backup_" + safeName + ".json";
            }
            File backupFile = new File(cacheDir, fileName);
            String json = deviceManager.exportDevicesJson(targetDevices);
            byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
            try (FileOutputStream fos = new FileOutputStream(backupFile)) {
                fos.write(bytes);
                fos.flush();
                try {
                    fos.getFD().sync();
                } catch (Exception ignored) {}
            }

            Uri contentUri = FileProvider.getUriForFile(
                    requireContext(),
                    requireContext().getPackageName() + ".fileprovider",
                    backupFile
            );

            Intent shareIntent = new Intent(Intent.ACTION_SEND);
            shareIntent.setType("application/json");
            shareIntent.putExtra(Intent.EXTRA_STREAM, contentUri);
            String title = targetDevices.size() == 1
                    ? "WeViewCam 设备配置备份 - " + targetDevices.get(0).getName()
                    : "WeViewCam 设备配置备份 (" + targetDevices.size() + "台)";
            shareIntent.putExtra(Intent.EXTRA_SUBJECT, title);
            shareIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(shareIntent, "分享设备配置备份"));
        } catch (Exception e) {
            Toast.makeText(getContext(), "分享失败: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void readBackupFromUri(Uri uri) {
        try (InputStream is = requireContext().getContentResolver().openInputStream(uri);
             BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line).append("\n");
            }

            List<DeviceInfo> parsed = deviceManager.parseDevicesJson(sb.toString());
            if (parsed == null || parsed.isEmpty()) {
                Toast.makeText(getContext(), "备份文件中未识别到有效设备配置，请核对格式", Toast.LENGTH_LONG).show();
                return;
            }

            showImportModeDialog(parsed);
        } catch (Exception e) {
            Toast.makeText(getContext(), "读取备份文件失败: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void showImportModeDialog(List<DeviceInfo> newDevices) {
        new AlertDialog.Builder(requireContext())
                .setTitle("导入设备配置")
                .setMessage("成功识别到 " + newDevices.size() + " 台设备配置。\n请选择导入策略：\n\n" +
                        "【增量合并】：若已存在相同设备则更新覆盖，新设备自动追加（推荐）。\n" +
                        "【完全覆盖】：清空当前所有设备，完全替换为备份文件内容。")
                .setPositiveButton("增量合并", (dialog, which) -> executeImport(newDevices, false))
                .setNeutralButton("完全覆盖", (dialog, which) -> executeImport(newDevices, true))
                .setNegativeButton("取消", null)
                .show();
    }

    private void executeImport(List<DeviceInfo> newDevices, boolean overwriteAll) {
        int count = deviceManager.importDevices(newDevices, overwriteAll);
        loadDevices();
        Toast.makeText(getContext(), "成功导入并生效 " + count + " 台设备", Toast.LENGTH_LONG).show();
    }

    private void loadDevices() {
        deviceList.clear();
        deviceList.addAll(deviceManager.getDevices());
        adapter.notifyDataSetChanged();
    }

    private void showAddDeviceDialog() {
        new DeviceEditDialog(requireContext(), null, device -> {
            deviceManager.addDevice(device);
            loadDevices();
            Toast.makeText(getContext(), "设备添加成功", Toast.LENGTH_SHORT).show();
        }).show();
    }

    private void showEditDeviceDialog(DeviceInfo device) {
        new DeviceEditDialog(requireContext(), device, updated -> {
            deviceManager.updateDevice(updated);
            loadDevices();
            Toast.makeText(getContext(), "设备配置已更新", Toast.LENGTH_SHORT).show();
        }).show();
    }

    private void showChannelManagementDialog(DeviceInfo device) {
        new ChannelManagementDialog(requireContext(), device, updated -> {
            deviceManager.updateDevice(updated);
            deviceManager.saveDevices();
            loadDevices();
        }).show();
    }

    private void confirmDeleteDevice(DeviceInfo device) {
        new AlertDialog.Builder(requireContext())
                .setTitle("删除设备确认")
                .setMessage("确定要删除监控设备 [" + device.getName() + "] 吗？")
                .setPositiveButton("删除", (dialog, which) -> {
                    deviceManager.deleteDevice(device.getDeviceId());
                    loadDevices();
                    Toast.makeText(getContext(), "设备已删除", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void testConnection(DeviceInfo device) {
        ProgressDialog progressDialog = new ProgressDialog(requireContext());
        progressDialog.setMessage("正在连接设备 " + device.getIp() + " 并探测通道...");
        progressDialog.setCancelable(false);
        progressDialog.show();

        deviceManager.testConnection(device, (success, message, channels) -> {
            progressDialog.dismiss();
            loadDevices();
            new AlertDialog.Builder(requireContext())
                    .setTitle(success ? "连接测试成功" : "连接测试失败")
                    .setMessage(message)
                    .setPositiveButton("确定", null)
                    .show();
        });
    }

    private class DeviceAdapter extends RecyclerView.Adapter<DeviceAdapter.ViewHolder> {

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_device, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            DeviceInfo dev = deviceList.get(position);
            holder.tvName.setText(dev.getName());
            holder.tvProtocol.setText(dev.getProtocol().getDisplayName());

            boolean connected = dev.isConnected();
            holder.tvStatus.setText(connected ? "在线" : "未连接");
            holder.tvStatus.setBackgroundResource(connected ? R.drawable.bg_badge_online : R.drawable.bg_badge_offline);

            holder.tvEndpoint.setText("IP: " + dev.getIp() + ":" + dev.getPort() + " (用户: " + dev.getUsername() + ")");
            int total = dev.getChannels().size();
            int enabled = dev.getEnabledChannels().size();
            holder.tvChannels.setText("通道数: " + total + " 个通道 (已启用 " + enabled + " 个)");

            holder.btnTest.setOnClickListener(v -> testConnection(dev));
            holder.btnChannels.setOnClickListener(v -> showChannelManagementDialog(dev));
            holder.btnBackup.setOnClickListener(v -> showBackupTargetOptionsDialog(Collections.singletonList(dev)));
            holder.btnEdit.setOnClickListener(v -> showEditDeviceDialog(dev));
            holder.btnDelete.setOnClickListener(v -> confirmDeleteDevice(dev));
        }

        @Override
        public int getItemCount() {
            return deviceList.size();
        }

        class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvName, tvProtocol, tvStatus, tvEndpoint, tvChannels;
            Button btnTest, btnChannels, btnBackup, btnEdit, btnDelete;

            ViewHolder(@NonNull View itemView) {
                super(itemView);
                tvName = itemView.findViewById(R.id.tv_device_name);
                tvProtocol = itemView.findViewById(R.id.tv_device_protocol);
                tvStatus = itemView.findViewById(R.id.tv_device_status);
                tvEndpoint = itemView.findViewById(R.id.tv_device_endpoint);
                tvChannels = itemView.findViewById(R.id.tv_device_channels_count);
                btnTest = itemView.findViewById(R.id.btn_device_test);
                btnChannels = itemView.findViewById(R.id.btn_device_channels);
                btnBackup = itemView.findViewById(R.id.btn_device_backup);
                btnEdit = itemView.findViewById(R.id.btn_device_edit);
                btnDelete = itemView.findViewById(R.id.btn_device_delete);
            }
        }
    }
}

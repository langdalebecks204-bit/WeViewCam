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
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class DeviceManagementFragment extends Fragment {
    private RecyclerView recyclerView;
    private DeviceAdapter adapter;
    private DeviceManager deviceManager;
    private final List<DeviceInfo> deviceList = new ArrayList<>();

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

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        deviceManager = DeviceManager.getInstance(requireContext());

        recyclerView = view.findViewById(R.id.recycler_devices);
        recyclerView.setLayoutManager(new LinearLayoutManager(requireContext()));
        adapter = new DeviceAdapter();
        recyclerView.setAdapter(adapter);

        Button btnAdd = view.findViewById(R.id.btn_add_device);
        btnAdd.setOnClickListener(v -> showAddDeviceDialog());

        Button btnBackup = view.findViewById(R.id.btn_backup_devices);
        if (btnBackup != null) {
            btnBackup.setOnClickListener(v -> showBackupOptionsDialog());
        }

        Button btnImport = view.findViewById(R.id.btn_import_devices);
        if (btnImport != null) {
            btnImport.setOnClickListener(v -> importDocumentLauncher.launch(new String[]{"application/json", "text/*", "*/*"}));
        }

        loadDevices();
    }

    private void showBackupOptionsDialog() {
        if (deviceList.isEmpty()) {
            Toast.makeText(getContext(), "当前没有可导出的设备配置", Toast.LENGTH_SHORT).show();
            return;
        }

        String[] options = new String[]{"保存为本地备份文件 (.json)", "分享备份文件 (微信/QQ/局域网等)", "复制配置 JSON 到剪贴板"};
        new AlertDialog.Builder(requireContext())
                .setTitle("导出设备配置备份")
                .setItems(options, (dialog, which) -> {
                    if (which == 0) {
                        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date());
                        String fileName = "weviewcam_devices_" + timeStamp + ".json";
                        exportDocumentLauncher.launch(fileName);
                    } else if (which == 1) {
                        shareBackupFile();
                    } else if (which == 2) {
                        copyBackupToClipboard();
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void copyBackupToClipboard() {
        try {
            String json = deviceManager.exportDevicesJson();
            android.content.ClipboardManager cm = (android.content.ClipboardManager) requireContext().getSystemService(android.content.Context.CLIPBOARD_SERVICE);
            if (cm != null) {
                android.content.ClipData clip = android.content.ClipData.newPlainText("WeViewCam Backup", json);
                cm.setPrimaryClip(clip);
                Toast.makeText(getContext(), "已将设备配置 JSON 复制到剪贴板！可以直接发送给电脑", Toast.LENGTH_LONG).show();
            }
        } catch (Exception e) {
            Toast.makeText(getContext(), "复制失败: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void writeBackupToUri(Uri uri) {
        try {
            String json = deviceManager.exportDevicesJson();
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
            Toast.makeText(getContext(), "设备配置备份已成功保存到文件 (大小: " + bytes.length + " 字节)", Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(getContext(), "保存备份失败: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void shareBackupFile() {
        try {
            File cacheDir = new File(requireContext().getCacheDir(), "backups");
            if (!cacheDir.exists() && !cacheDir.mkdirs()) {
                throw new IllegalStateException("无法创建临时备份目录");
            }
            File backupFile = new File(cacheDir, "weviewcam_devices_backup.json");
            String json = deviceManager.exportDevicesJson();
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
            shareIntent.putExtra(Intent.EXTRA_SUBJECT, "WeViewCam 设备配置备份");
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
            holder.btnEdit.setOnClickListener(v -> showEditDeviceDialog(dev));
            holder.btnDelete.setOnClickListener(v -> confirmDeleteDevice(dev));
        }

        @Override
        public int getItemCount() {
            return deviceList.size();
        }

        class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvName, tvProtocol, tvStatus, tvEndpoint, tvChannels;
            Button btnTest, btnChannels, btnEdit, btnDelete;

            ViewHolder(@NonNull View itemView) {
                super(itemView);
                tvName = itemView.findViewById(R.id.tv_device_name);
                tvProtocol = itemView.findViewById(R.id.tv_device_protocol);
                tvStatus = itemView.findViewById(R.id.tv_device_status);
                tvEndpoint = itemView.findViewById(R.id.tv_device_endpoint);
                tvChannels = itemView.findViewById(R.id.tv_device_channels_count);
                btnTest = itemView.findViewById(R.id.btn_device_test);
                btnChannels = itemView.findViewById(R.id.btn_device_channels);
                btnEdit = itemView.findViewById(R.id.btn_device_edit);
                btnDelete = itemView.findViewById(R.id.btn_device_delete);
            }
        }
    }
}

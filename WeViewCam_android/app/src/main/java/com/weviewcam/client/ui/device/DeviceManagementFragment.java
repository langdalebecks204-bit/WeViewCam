package com.weviewcam.client.ui.device;

import android.app.AlertDialog;
import android.app.ProgressDialog;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.weviewcam.client.R;
import com.weviewcam.client.core.manager.DeviceManager;
import com.weviewcam.client.core.model.DeviceInfo;

import java.util.ArrayList;
import java.util.List;

public class DeviceManagementFragment extends Fragment {
    private RecyclerView recyclerView;
    private DeviceAdapter adapter;
    private DeviceManager deviceManager;
    private final List<DeviceInfo> deviceList = new ArrayList<>();

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

        loadDevices();
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
            holder.tvChannels.setText("通道数: " + dev.getChannels().size() + " 个通道");

            holder.btnTest.setOnClickListener(v -> testConnection(dev));
            holder.btnEdit.setOnClickListener(v -> showEditDeviceDialog(dev));
            holder.btnDelete.setOnClickListener(v -> confirmDeleteDevice(dev));
        }

        @Override
        public int getItemCount() {
            return deviceList.size();
        }

        class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvName, tvProtocol, tvStatus, tvEndpoint, tvChannels;
            Button btnTest, btnEdit, btnDelete;

            ViewHolder(@NonNull View itemView) {
                super(itemView);
                tvName = itemView.findViewById(R.id.tv_device_name);
                tvProtocol = itemView.findViewById(R.id.tv_device_protocol);
                tvStatus = itemView.findViewById(R.id.tv_device_status);
                tvEndpoint = itemView.findViewById(R.id.tv_device_endpoint);
                tvChannels = itemView.findViewById(R.id.tv_device_channels_count);
                btnTest = itemView.findViewById(R.id.btn_device_test);
                btnEdit = itemView.findViewById(R.id.btn_device_edit);
                btnDelete = itemView.findViewById(R.id.btn_device_delete);
            }
        }
    }
}

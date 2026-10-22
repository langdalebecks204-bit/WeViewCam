package com.weviewcam.client.ui.device;

import android.app.AlertDialog;
import android.app.Dialog;
import android.content.Context;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.widget.SwitchCompat;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.weviewcam.client.R;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;

import java.util.ArrayList;
import java.util.List;

public class ChannelManagementDialog extends Dialog {

    public interface OnChannelsUpdatedListener {
        void onChannelsUpdated(DeviceInfo device);
    }

    private final DeviceInfo device;
    private final OnChannelsUpdatedListener listener;
    private final List<ChannelInfo> channelList = new ArrayList<>();

    private TextView tvSummary;
    private TextView tvEmpty;
    private RecyclerView recyclerView;
    private ChannelRowAdapter adapter;

    public ChannelManagementDialog(@NonNull Context context, DeviceInfo device, OnChannelsUpdatedListener listener) {
        super(context);
        this.device = device;
        this.listener = listener;

        // Clone channels into local editing list
        if (device != null && device.getChannels() != null) {
            for (ChannelInfo ch : device.getChannels()) {
                ChannelInfo clone = new ChannelInfo(
                        ch.getChannelNo(),
                        ch.getName(),
                        ch.isOnline(),
                        ch.isPtz(),
                        ch.getDeviceId(),
                        ch.isEnabled()
                );
                channelList.add(clone);
            }
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setContentView(R.layout.dialog_channel_management);

        if (getWindow() != null) {
            getWindow().setBackgroundDrawableResource(android.R.color.transparent);
            int width = (int) (getContext().getResources().getDisplayMetrics().widthPixels * 0.95);
            getWindow().setLayout(width, ViewGroup.LayoutParams.WRAP_CONTENT);
        }

        TextView tvTitle = findViewById(R.id.tv_manage_title);
        TextView tvSubtitle = findViewById(R.id.tv_manage_subtitle);
        tvSummary = findViewById(R.id.tv_manage_count_summary);
        tvEmpty = findViewById(R.id.tv_manage_empty);
        recyclerView = findViewById(R.id.recycler_manage_channels);

        Button btnClose = findViewById(R.id.btn_manage_close);
        Button btnEnableAll = findViewById(R.id.btn_batch_enable_all);
        Button btnDisableAll = findViewById(R.id.btn_batch_disable_all);
        Button btnAddChannel = findViewById(R.id.btn_manage_add_channel);
        Button btnCancel = findViewById(R.id.btn_manage_cancel);
        Button btnSave = findViewById(R.id.btn_manage_save);

        String devName = (device != null && device.getName() != null) ? device.getName() : "NVR";
        String ip = (device != null) ? (device.getIp() + ":" + device.getPort()) : "";
        tvTitle.setText(devName + " - 通道配置");
        tvSubtitle.setText("设备网络地址: " + ip);

        recyclerView.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new ChannelRowAdapter();
        recyclerView.setAdapter(adapter);

        btnEnableAll.setOnClickListener(v -> {
            for (ChannelInfo ch : channelList) {
                ch.setEnabled(true);
            }
            adapter.notifyDataSetChanged();
            updateSummary();
        });

        btnDisableAll.setOnClickListener(v -> {
            for (ChannelInfo ch : channelList) {
                ch.setEnabled(false);
            }
            adapter.notifyDataSetChanged();
            updateSummary();
        });

        btnAddChannel.setOnClickListener(v -> showAddChannelDialog());

        btnClose.setOnClickListener(v -> dismiss());
        btnCancel.setOnClickListener(v -> dismiss());
        btnSave.setOnClickListener(v -> saveAndDismiss());

        updateSummary();
    }

    private void updateSummary() {
        int total = channelList.size();
        int enabledCount = 0;
        for (ChannelInfo ch : channelList) {
            if (ch.isEnabled()) {
                enabledCount++;
            }
        }
        tvSummary.setText("共 " + total + " 个通道 · 已启用 " + enabledCount + " 个");
        if (total == 0) {
            tvEmpty.setVisibility(View.VISIBLE);
            recyclerView.setVisibility(View.GONE);
        } else {
            tvEmpty.setVisibility(View.GONE);
            recyclerView.setVisibility(View.VISIBLE);
        }
    }

    private void showRenameDialog(int position) {
        ChannelInfo ch = channelList.get(position);
        View dialogView = LayoutInflater.from(getContext()).inflate(R.layout.dialog_channel_rename, null);
        TextView tvTitle = dialogView.findViewById(R.id.tv_rename_title);
        TextView tvChNo = dialogView.findViewById(R.id.tv_rename_channel_no);
        EditText etName = dialogView.findViewById(R.id.et_channel_new_name);
        Button btnCancel = dialogView.findViewById(R.id.btn_rename_cancel);
        Button btnSave = dialogView.findViewById(R.id.btn_rename_save);

        tvTitle.setText("自定义通道名称");
        tvChNo.setText("目标通道: 通道 " + ch.getChannelNo());
        etName.setText(ch.getName());
        etName.setSelectAllOnFocus(true);

        androidx.appcompat.app.AlertDialog dialog = new androidx.appcompat.app.AlertDialog.Builder(getContext())
                .setView(dialogView)
                .create();

        if (dialog.getWindow() != null) {
            dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        }

        btnCancel.setOnClickListener(v -> dialog.dismiss());
        btnSave.setOnClickListener(v -> {
            String newName = etName.getText().toString().trim();
            if (newName.isEmpty()) {
                newName = "通道 " + ch.getChannelNo();
            }
            ch.setName(newName);
            adapter.notifyItemChanged(position);
            dialog.dismiss();
        });

        dialog.show();
    }

    private void showAddChannelDialog() {
        View dialogView = LayoutInflater.from(getContext()).inflate(R.layout.dialog_channel_add, null);
        EditText etNo = dialogView.findViewById(R.id.et_add_channel_no);
        EditText etName = dialogView.findViewById(R.id.et_add_channel_name);
        Button btnCancel = dialogView.findViewById(R.id.btn_add_channel_cancel);
        Button btnConfirm = dialogView.findViewById(R.id.btn_add_channel_confirm);

        int nextNo = 1;
        for (ChannelInfo c : channelList) {
            if (c.getChannelNo() >= nextNo) {
                nextNo = c.getChannelNo() + 1;
            }
        }
        etNo.setText(String.valueOf(nextNo));
        etName.setText("通道 " + nextNo);
        etName.setSelectAllOnFocus(true);

        androidx.appcompat.app.AlertDialog dialog = new androidx.appcompat.app.AlertDialog.Builder(getContext())
                .setView(dialogView)
                .create();

        if (dialog.getWindow() != null) {
            dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        }

        btnCancel.setOnClickListener(v -> dialog.dismiss());
        btnConfirm.setOnClickListener(v -> {
            int chNo;
            try {
                chNo = Integer.parseInt(etNo.getText().toString().trim());
            } catch (NumberFormatException e) {
                Toast.makeText(getContext(), "通道编号必须为数字", Toast.LENGTH_SHORT).show();
                return;
            }
            String name = etName.getText().toString().trim();
            if (name.isEmpty()) {
                name = "通道 " + chNo;
            }

            String devId = (device != null) ? device.getDeviceId() : "";
            ChannelInfo newCh = new ChannelInfo(chNo, name, true, false, devId, true);
            channelList.add(newCh);
            adapter.notifyDataSetChanged();
            updateSummary();
            Toast.makeText(getContext(), "已添加通道: " + name, Toast.LENGTH_SHORT).show();
            dialog.dismiss();
        });

        dialog.show();
    }

    private void saveAndDismiss() {
        if (device != null) {
            device.setChannels(new ArrayList<>(channelList));
            if (listener != null) {
                listener.onChannelsUpdated(device);
            }
        }
        Toast.makeText(getContext(), "通道配置已保存并生效", Toast.LENGTH_SHORT).show();
        dismiss();
    }

    private class ChannelRowAdapter extends RecyclerView.Adapter<ChannelRowAdapter.ViewHolder> {

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_channel_manage_row, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            ChannelInfo ch = channelList.get(position);

            holder.tvNo.setText("CH " + ch.getChannelNo());
            holder.tvName.setText(ch.getName());

            if (ch.isOnline()) {
                holder.statusDot.setBackgroundResource(R.drawable.bg_status_dot_green);
                holder.tvStatus.setText("在线");
                holder.tvStatus.setTextColor(ContextCompat.getColor(getContext(), R.color.status_green));
            } else {
                holder.statusDot.setBackgroundResource(R.drawable.bg_status_dot_gray);
                holder.tvStatus.setText("离线");
                holder.tvStatus.setTextColor(ContextCompat.getColor(getContext(), R.color.text_secondary));
            }

            // Bind switch
            holder.switchEnabled.setOnCheckedChangeListener(null);
            holder.switchEnabled.setChecked(ch.isEnabled());
            holder.switchEnabled.setOnCheckedChangeListener((buttonView, isChecked) -> {
                ch.setEnabled(isChecked);
                updateSummary();
            });

            // Rename button & row click
            holder.btnRename.setOnClickListener(v -> showRenameDialog(holder.getAdapterPosition()));
            holder.itemView.setOnClickListener(v -> showRenameDialog(holder.getAdapterPosition()));
        }

        @Override
        public int getItemCount() {
            return channelList.size();
        }

        class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvNo, tvName, tvStatus;
            View statusDot;
            Button btnRename;
            SwitchCompat switchEnabled;

            ViewHolder(@NonNull View itemView) {
                super(itemView);
                tvNo = itemView.findViewById(R.id.tv_manage_channel_no);
                tvName = itemView.findViewById(R.id.tv_manage_channel_name);
                tvStatus = itemView.findViewById(R.id.tv_manage_channel_status);
                statusDot = itemView.findViewById(R.id.view_manage_status_dot);
                btnRename = itemView.findViewById(R.id.btn_manage_rename);
                switchEnabled = itemView.findViewById(R.id.switch_channel_enabled);
            }
        }
    }
}

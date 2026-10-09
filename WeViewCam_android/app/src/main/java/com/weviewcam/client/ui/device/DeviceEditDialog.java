package com.weviewcam.client.ui.device;

import android.app.Dialog;
import android.content.Context;
import android.os.Bundle;
import android.view.Window;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;

import com.weviewcam.client.R;
import com.weviewcam.client.core.model.DeviceInfo;
import com.weviewcam.client.core.model.ProtocolType;

public class DeviceEditDialog extends Dialog {

    public interface OnDeviceSaveListener {
        void onSave(DeviceInfo device);
    }

    private final DeviceInfo initialDevice;
    private final OnDeviceSaveListener saveListener;

    private EditText etName;
    private Spinner spinnerProtocol;
    private EditText etIp;
    private EditText etPort;
    private EditText etUser;
    private EditText etPass;

    public DeviceEditDialog(@NonNull Context context, DeviceInfo device, OnDeviceSaveListener listener) {
        super(context);
        this.initialDevice = device;
        this.saveListener = listener;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setContentView(R.layout.dialog_device_edit);

        if (getWindow() != null) {
            getWindow().setBackgroundDrawableResource(android.R.color.transparent);
            getWindow().setLayout((int) (getContext().getResources().getDisplayMetrics().widthPixels * 0.9),
                    android.view.ViewGroup.LayoutParams.WRAP_CONTENT);
        }

        TextView tvTitle = findViewById(R.id.tv_dialog_title);
        etName = findViewById(R.id.et_device_name);
        spinnerProtocol = findViewById(R.id.spinner_device_protocol);
        etIp = findViewById(R.id.et_device_ip);
        etPort = findViewById(R.id.et_device_port);
        etUser = findViewById(R.id.et_device_user);
        etPass = findViewById(R.id.et_device_pass);

        ProtocolType[] protocols = ProtocolType.values();
        String[] protoLabels = new String[protocols.length];
        for (int i = 0; i < protocols.length; i++) {
            protoLabels[i] = protocols[i].getDisplayName();
        }

        ArrayAdapter<String> adapter = new ArrayAdapter<>(getContext(), android.R.layout.simple_spinner_item, protoLabels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerProtocol.setAdapter(adapter);

        if (initialDevice != null) {
            tvTitle.setText("编辑监控设备");
            etName.setText(initialDevice.getName());
            etIp.setText(initialDevice.getIp());
            etPort.setText(String.valueOf(initialDevice.getPort()));
            etUser.setText(initialDevice.getUsername());
            etPass.setText(initialDevice.getPassword());

            for (int i = 0; i < protocols.length; i++) {
                if (protocols[i] == initialDevice.getProtocol()) {
                    spinnerProtocol.setSelection(i);
                    break;
                }
            }
        } else {
            tvTitle.setText("添加监控设备");
        }

        Button btnCancel = findViewById(R.id.btn_dialog_cancel);
        Button btnSave = findViewById(R.id.btn_dialog_save);

        btnCancel.setOnClickListener(v -> dismiss());
        btnSave.setOnClickListener(v -> save());
    }

    private void save() {
        String name = etName.getText().toString().trim();
        String ip = etIp.getText().toString().trim();
        String portStr = etPort.getText().toString().trim();
        String user = etUser.getText().toString().trim();
        String pass = etPass.getText().toString().trim();

        if (name.isEmpty() || ip.isEmpty() || portStr.isEmpty()) {
            Toast.makeText(getContext(), "设备名称、IP 地址与端口不能为空", Toast.LENGTH_SHORT).show();
            return;
        }

        int port;
        try {
            port = Integer.parseInt(portStr);
        } catch (NumberFormatException e) {
            Toast.makeText(getContext(), "端口必须为数字", Toast.LENGTH_SHORT).show();
            return;
        }

        ProtocolType selectedProto = ProtocolType.values()[spinnerProtocol.getSelectedItemPosition()];

        DeviceInfo target = (initialDevice != null) ? initialDevice : new DeviceInfo();
        target.setName(name);
        target.setIp(ip);
        target.setPort(port);
        target.setUsername(user);
        target.setPassword(pass);
        target.setProtocol(selectedProto);

        if (saveListener != null) {
            saveListener.onSave(target);
        }
        dismiss();
    }
}

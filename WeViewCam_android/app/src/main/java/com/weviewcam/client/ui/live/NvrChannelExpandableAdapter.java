package com.weviewcam.client.ui.live;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseExpandableListAdapter;
import android.widget.TextView;

import androidx.core.content.ContextCompat;

import com.weviewcam.client.R;
import com.weviewcam.client.core.model.ChannelInfo;
import com.weviewcam.client.core.model.DeviceInfo;

import java.util.List;

public class NvrChannelExpandableAdapter extends BaseExpandableListAdapter {

    public interface OnChannelSelectedListener {
        void onChannelSelected(DeviceInfo device, ChannelInfo channel);
    }

    private final Context context;
    private final List<DeviceInfo> devices;
    private final ChannelInfo currentChannel;
    private final OnChannelSelectedListener listener;
    private final LayoutInflater inflater;

    public NvrChannelExpandableAdapter(Context context, List<DeviceInfo> devices,
                                       ChannelInfo currentChannel, OnChannelSelectedListener listener) {
        this.context = context;
        this.devices = devices;
        this.currentChannel = currentChannel;
        this.listener = listener;
        this.inflater = LayoutInflater.from(context);
    }

    @Override
    public int getGroupCount() {
        return devices.size();
    }

    @Override
    public int getChildrenCount(int groupPosition) {
        DeviceInfo dev = devices.get(groupPosition);
        return (dev.getChannels() != null) ? dev.getChannels().size() : 0;
    }

    @Override
    public Object getGroup(int groupPosition) {
        return devices.get(groupPosition);
    }

    @Override
    public Object getChild(int groupPosition, int childPosition) {
        DeviceInfo dev = devices.get(groupPosition);
        return dev.getChannels().get(childPosition);
    }

    @Override
    public long getGroupId(int groupPosition) {
        return groupPosition;
    }

    @Override
    public long getChildId(int groupPosition, int childPosition) {
        return childPosition;
    }

    @Override
    public boolean hasStableIds() {
        return false;
    }

    @Override
    public View getGroupView(int groupPosition, boolean isExpanded, View convertView, ViewGroup parent) {
        if (convertView == null) {
            convertView = inflater.inflate(R.layout.item_channel_picker_group, parent, false);
        }

        DeviceInfo dev = devices.get(groupPosition);
        TextView tvNvrName = convertView.findViewById(R.id.tv_nvr_name);
        TextView tvNvrIp = convertView.findViewById(R.id.tv_nvr_ip);
        TextView tvChannelCount = convertView.findViewById(R.id.tv_nvr_channel_count);
        TextView tvExpandArrow = convertView.findViewById(R.id.tv_expand_arrow);

        String name = (dev.getName() != null && !dev.getName().trim().isEmpty()) ? dev.getName() : "NVR 主机";
        tvNvrName.setText(name);
        tvNvrIp.setText(dev.getIp() + ":" + dev.getPort());

        int total = (dev.getChannels() != null) ? dev.getChannels().size() : 0;
        int online = 0;
        if (dev.getChannels() != null) {
            for (ChannelInfo ch : dev.getChannels()) {
                if (ch.isOnline()) online++;
            }
        }
        tvChannelCount.setText(online + "/" + total + " 在线");
        tvExpandArrow.setText(isExpanded ? "▲" : "▼");

        return convertView;
    }

    @Override
    public View getChildView(int groupPosition, int childPosition, boolean isLastChild, View convertView, ViewGroup parent) {
        if (convertView == null) {
            convertView = inflater.inflate(R.layout.item_channel_picker_child, parent, false);
        }

        DeviceInfo dev = devices.get(groupPosition);
        ChannelInfo ch = dev.getChannels().get(childPosition);

        View statusDot = convertView.findViewById(R.id.view_status_dot);
        TextView tvChannelName = convertView.findViewById(R.id.tv_channel_name);
        TextView tvChannelStatus = convertView.findViewById(R.id.tv_channel_status);
        TextView tvCurrentTag = convertView.findViewById(R.id.tv_channel_current_tag);

        tvChannelName.setText(ch.getName());

        if (ch.isOnline()) {
            statusDot.setBackgroundResource(R.drawable.bg_status_dot_green);
            tvChannelStatus.setText("在线");
            tvChannelStatus.setTextColor(ContextCompat.getColor(context, R.color.status_green));
        } else {
            statusDot.setBackgroundResource(R.drawable.bg_status_dot_gray);
            tvChannelStatus.setText("离线");
            tvChannelStatus.setTextColor(ContextCompat.getColor(context, R.color.text_secondary));
        }

        boolean isCurrent = false;
        if (currentChannel != null && currentChannel.getDeviceId() != null && ch.getDeviceId() != null) {
            if (currentChannel.getDeviceId().equals(ch.getDeviceId()) && currentChannel.getChannelNo() == ch.getChannelNo()) {
                isCurrent = true;
            }
        }
        tvCurrentTag.setVisibility(isCurrent ? View.VISIBLE : View.GONE);

        convertView.setOnClickListener(v -> {
            if (listener != null) {
                listener.onChannelSelected(dev, ch);
            }
        });

        return convertView;
    }

    @Override
    public boolean isChildSelectable(int groupPosition, int childPosition) {
        return true;
    }
}

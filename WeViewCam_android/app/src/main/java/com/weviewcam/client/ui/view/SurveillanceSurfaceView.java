package com.weviewcam.client.ui.view;

import android.content.Context;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.util.AttributeSet;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.content.ContextCompat;

import com.hikvision.netsdk.HCNetSDK;
import com.weviewcam.client.R;
import com.weviewcam.client.core.model.ChannelInfo;

public class SurveillanceSurfaceView extends FrameLayout implements SurfaceHolder.Callback {

    public interface OnViewportClickListener {
        void onViewportClicked(SurveillanceSurfaceView viewport);
        void onViewportDoubleClicked(SurveillanceSurfaceView viewport);
        default void onViewportLongClicked(SurveillanceSurfaceView viewport) {}
    }

    private SurfaceView surfaceView;
    private Surface surface;
    private boolean isSurfaceReady = false;

    private View borderView;
    private TextView tvTitle;
    private TextView tvStatus;

    private int viewportIndex = -1;
    private ChannelInfo channelInfo;
    private int playHandle = -1;
    private boolean isSelected = false;

    private OnViewportClickListener clickListener;
    private GestureDetector gestureDetector;

    public SurveillanceSurfaceView(@NonNull Context context) {
        super(context);
        init(context);
    }

    public SurveillanceSurfaceView(@NonNull Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        init(context);
    }

    public SurveillanceSurfaceView(@NonNull Context context, @Nullable AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init(context);
    }

    private void init(Context context) {
        setBackgroundColor(Color.BLACK);
        setClickable(true);
        setFocusable(true);

        surfaceView = new SurfaceView(context);
        surfaceView.getHolder().addCallback(this);
        surfaceView.getHolder().setFormat(PixelFormat.TRANSLUCENT);
        surfaceView.setZOrderMediaOverlay(true);
        surfaceView.setClickable(false);
        surfaceView.setFocusable(false);
        LayoutParams surfaceLp = new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT);
        addView(surfaceView, surfaceLp);

        // Border overlay (Border only, transparent inside)
        borderView = new View(context);
        borderView.setBackgroundResource(R.drawable.bg_viewport_normal);
        borderView.setClickable(false);
        borderView.setFocusable(false);
        addView(borderView, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));

        // Top OSD Header
        FrameLayout osdLayout = new FrameLayout(context);
        osdLayout.setPadding(16, 12, 16, 12);
        osdLayout.setBackgroundColor(Color.parseColor("#80000000"));
        osdLayout.setClickable(false);
        osdLayout.setFocusable(false);

        tvTitle = new TextView(context);
        tvTitle.setTextColor(Color.WHITE);
        tvTitle.setTextSize(13f);
        tvTitle.setText("无通道");
        LayoutParams titleLp = new LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT);
        osdLayout.addView(tvTitle, titleLp);

        tvStatus = new TextView(context);
        tvStatus.setTextColor(Color.parseColor("#8b949e"));
        tvStatus.setTextSize(12f);
        tvStatus.setText("空闲");
        LayoutParams statusLp = new LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT);
        statusLp.gravity = android.view.Gravity.END;
        osdLayout.addView(tvStatus, statusLp);

        addView(osdLayout, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT));

        gestureDetector = new GestureDetector(context, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onDown(MotionEvent e) {
                return true; // Return true to ensure UP and subsequent gesture events are delivered
            }

            @Override
            public boolean onSingleTapUp(MotionEvent e) {
                if (clickListener != null) {
                    clickListener.onViewportClicked(SurveillanceSurfaceView.this);
                }
                return true;
            }

            @Override
            public boolean onDoubleTap(MotionEvent e) {
                if (clickListener != null) {
                    clickListener.onViewportDoubleClicked(SurveillanceSurfaceView.this);
                }
                return true;
            }

            @Override
            public void onLongPress(MotionEvent e) {
                if (clickListener != null) {
                    clickListener.onViewportLongClicked(SurveillanceSurfaceView.this);
                }
            }
        });

        setOnClickListener(v -> {
            if (clickListener != null) {
                clickListener.onViewportClicked(SurveillanceSurfaceView.this);
            }
        });
    }

    @Override
    public boolean onInterceptTouchEvent(MotionEvent ev) {
        return true;
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (gestureDetector != null && gestureDetector.onTouchEvent(event)) {
            return true;
        }
        return super.onTouchEvent(event);
    }

    public void setOnViewportClickListener(OnViewportClickListener listener) {
        this.clickListener = listener;
    }

    public void setViewportIndex(int index) {
        this.viewportIndex = index;
        updateOsdText();
    }

    public int getViewportIndex() {
        return viewportIndex;
    }

    public void setSelectedViewport(boolean selected) {
        this.isSelected = selected;
        borderView.setBackgroundResource(selected ? R.drawable.bg_viewport_selected : R.drawable.bg_viewport_normal);
    }

    public boolean isSelectedViewport() {
        return isSelected;
    }

    public void setChannelInfo(ChannelInfo info) {
        this.channelInfo = info;
        updateOsdText();
    }

    public ChannelInfo getChannelInfo() {
        return channelInfo;
    }

    public void setPlayHandle(int handle) {
        this.playHandle = handle;
        updateOsdText();
    }

    private void updateOsdText() {
        if (tvTitle == null || tvStatus == null) return;
        String prefix = (viewportIndex >= 0) ? ("【视口 " + (viewportIndex + 1) + "】 ") : "";
        if (channelInfo != null) {
            String onlineStr = channelInfo.isOnline() ? " [在线]" : " [离线]";
            tvTitle.setText(prefix + channelInfo.getName() + onlineStr);
            if (playHandle >= 0) {
                tvStatus.setText("正在播放");
                tvStatus.setTextColor(ContextCompat.getColor(getContext(), R.color.status_green));
            } else {
                tvStatus.setText(channelInfo.isOnline() ? "在线 (待播放)" : "离线");
                tvStatus.setTextColor(ContextCompat.getColor(getContext(), R.color.text_secondary));
            }
        } else {
            tvTitle.setText(prefix + "未分配通道");
            tvStatus.setText("空闲");
            tvStatus.setTextColor(ContextCompat.getColor(getContext(), R.color.text_secondary));
        }
    }

    public int getPlayHandle() {
        return playHandle;
    }

    public Surface getSurface() {
        return surface;
    }

    public SurfaceHolder getHolder() {
        return surfaceView != null ? surfaceView.getHolder() : null;
    }

    public boolean isSurfaceReady() {
        return isSurfaceReady && surface != null && surface.isValid();
    }

    @Override
    public void surfaceCreated(@NonNull SurfaceHolder holder) {
        this.surface = holder.getSurface();
        this.isSurfaceReady = true;
        if (playHandle >= 0) {
            try {
                HCNetSDK.getInstance().NET_DVR_RealPlaySurfaceChanged(playHandle, 0, holder);
                HCNetSDK.getInstance().NET_DVR_PlayBackSurfaceChanged(playHandle, 0, holder);
            } catch (Throwable ignored) {}
        }
    }

    @Override
    public void surfaceChanged(@NonNull SurfaceHolder holder, int format, int width, int height) {
        this.surface = holder.getSurface();
        this.isSurfaceReady = true;
        if (playHandle >= 0) {
            try {
                HCNetSDK.getInstance().NET_DVR_RealPlaySurfaceChanged(playHandle, 0, holder);
                HCNetSDK.getInstance().NET_DVR_PlayBackSurfaceChanged(playHandle, 0, holder);
            } catch (Throwable ignored) {}
        }
    }

    @Override
    public void surfaceDestroyed(@NonNull SurfaceHolder holder) {
        if (playHandle >= 0) {
            try {
                HCNetSDK.getInstance().NET_DVR_RealPlaySurfaceChanged(playHandle, 0, null);
            } catch (Throwable ignored) {}
        }
        this.isSurfaceReady = false;
        this.surface = null;
    }
}

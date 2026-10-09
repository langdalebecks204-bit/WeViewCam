package com.weviewcam.client.ui.view;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PointF;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

import androidx.annotation.Nullable;

import com.weviewcam.client.core.model.PTZCommand;

public class PTZControllerView extends View {

    public interface OnPTZActionListener {
        void onPTZAction(PTZCommand command, boolean stop);
    }

    private Paint bgPaint;
    private Paint centerPaint;
    private Paint arrowPaint;
    private Paint activePaint;

    private OnPTZActionListener listener;
    private PTZCommand activeCommand = null;

    public PTZControllerView(Context context) {
        super(context);
        init();
    }

    public PTZControllerView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public PTZControllerView(Context context, @Nullable AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    private void init() {
        bgPaint = new Paint();
        bgPaint.setColor(Color.parseColor("#161b22"));
        bgPaint.setStyle(Paint.Style.FILL);
        bgPaint.setAntiAlias(true);

        centerPaint = new Paint();
        centerPaint.setColor(Color.parseColor("#21262d"));
        centerPaint.setStyle(Paint.Style.FILL);
        centerPaint.setAntiAlias(true);

        arrowPaint = new Paint();
        arrowPaint.setColor(Color.parseColor("#8b949e"));
        arrowPaint.setStyle(Paint.Style.FILL);
        arrowPaint.setAntiAlias(true);

        activePaint = new Paint();
        activePaint.setColor(Color.parseColor("#1f6feb"));
        activePaint.setStyle(Paint.Style.FILL);
        activePaint.setAntiAlias(true);
    }

    public void setOnPTZActionListener(OnPTZActionListener listener) {
        this.listener = listener;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float w = getWidth();
        float h = getHeight();
        float cx = w / 2f;
        float cy = h / 2f;
        float radius = Math.min(cx, cy) - 10;

        // Outer circle
        canvas.drawCircle(cx, cy, radius, bgPaint);

        // Draw 8 direction sectors or arrows
        drawArrow(canvas, cx, cy - radius * 0.65f, 0, activeCommand == PTZCommand.UP);
        drawArrow(canvas, cx, cy + radius * 0.65f, 180, activeCommand == PTZCommand.DOWN);
        drawArrow(canvas, cx - radius * 0.65f, cy, 270, activeCommand == PTZCommand.LEFT);
        drawArrow(canvas, cx + radius * 0.65f, cy, 90, activeCommand == PTZCommand.RIGHT);

        // Center hub
        canvas.drawCircle(cx, cy, radius * 0.35f, centerPaint);
    }

    private void drawArrow(Canvas canvas, float x, float y, float angleDeg, boolean active) {
        canvas.save();
        canvas.translate(x, y);
        canvas.rotate(angleDeg);

        Path path = new Path();
        float s = 24f;
        path.moveTo(0, -s);
        path.lineTo(s * 0.8f, s * 0.6f);
        path.lineTo(0, s * 0.2f);
        path.lineTo(-s * 0.8f, s * 0.6f);
        path.close();

        canvas.drawPath(path, active ? activePaint : arrowPaint);
        canvas.restore();
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        float cx = getWidth() / 2f;
        float cy = getHeight() / 2f;
        float dx = event.getX() - cx;
        float dy = event.getY() - cy;
        float dist = (float) Math.hypot(dx, dy);
        float radius = Math.min(cx, cy);

        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
            case MotionEvent.ACTION_MOVE:
                if (dist > radius * 0.25f && dist <= radius) {
                    PTZCommand cmd = resolveDirection(dx, dy);
                    if (cmd != activeCommand) {
                        if (activeCommand != null && listener != null) {
                            listener.onPTZAction(activeCommand, true); // Stop previous
                        }
                        activeCommand = cmd;
                        if (listener != null) {
                            listener.onPTZAction(activeCommand, false); // Start new
                        }
                        invalidate();
                    }
                } else if (dist <= radius * 0.25f && activeCommand != null) {
                    // Center stop
                    stopActive();
                }
                return true;

            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                stopActive();
                return true;
        }
        return super.onTouchEvent(event);
    }

    private void stopActive() {
        if (activeCommand != null) {
            if (listener != null) {
                listener.onPTZAction(activeCommand, true);
            }
            activeCommand = null;
            invalidate();
        }
    }

    private PTZCommand resolveDirection(float dx, float dy) {
        double angle = Math.toDegrees(Math.atan2(dy, dx)); // -180 to 180
        if (angle < 0) angle += 360; // 0 to 360 (0 is RIGHT, 90 is DOWN, 180 is LEFT, 270 is UP)

        if (angle >= 337.5 || angle < 22.5) {
            return PTZCommand.RIGHT;
        } else if (angle >= 22.5 && angle < 67.5) {
            return PTZCommand.DOWN_RIGHT;
        } else if (angle >= 67.5 && angle < 112.5) {
            return PTZCommand.DOWN;
        } else if (angle >= 112.5 && angle < 157.5) {
            return PTZCommand.DOWN_LEFT;
        } else if (angle >= 157.5 && angle < 202.5) {
            return PTZCommand.LEFT;
        } else if (angle >= 202.5 && angle < 247.5) {
            return PTZCommand.UP_LEFT;
        } else if (angle >= 247.5 && angle < 292.5) {
            return PTZCommand.UP;
        } else {
            return PTZCommand.UP_RIGHT;
        }
    }
}

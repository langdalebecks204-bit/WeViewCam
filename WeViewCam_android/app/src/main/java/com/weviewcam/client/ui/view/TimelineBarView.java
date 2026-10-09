package com.weviewcam.client.ui.view;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

import androidx.annotation.Nullable;

import com.weviewcam.client.core.model.RecordSegment;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * 24-Hour Surveillance Interactive Timeline Bar View
 * Directly ported from WeViewCam Ubuntu PyQt5 timeline_bar.py to Android Canvas.
 */
public class TimelineBarView extends View {

    public interface OnTimeSelectedListener {
        void onTimeSelected(Date date, boolean isDragging);
    }

    private Date targetDate = new Date();
    private double viewStartSec = 0.0;
    private double viewDurationSec = 86400.0; // 24 hours default
    private Date currentTime = new Date();
    private List<RecordSegment> segments = new ArrayList<>();

    private OnTimeSelectedListener listener;
    private boolean isDragging = false;

    // Paints
    private Paint bgPaint;
    private Paint rulerBgPaint;
    private Paint tickPaint;
    private Paint textPaint;
    private Paint recordSchedulePaint;
    private Paint recordAlarmPaint;
    private Paint needlePaint;
    private Paint labelBgPaint;

    private final SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm:ss", Locale.getDefault());
    private final SimpleDateFormat tickFormat = new SimpleDateFormat("HH:mm", Locale.getDefault());

    public TimelineBarView(Context context) {
        super(context);
        init();
    }

    public TimelineBarView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public TimelineBarView(Context context, @Nullable AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    private void init() {
        bgPaint = new Paint();
        bgPaint.setColor(Color.parseColor("#161b22"));

        rulerBgPaint = new Paint();
        rulerBgPaint.setColor(Color.parseColor("#21262d"));

        tickPaint = new Paint();
        tickPaint.setColor(Color.parseColor("#8b949e"));
        tickPaint.setStrokeWidth(2f);
        tickPaint.setAntiAlias(true);

        textPaint = new Paint();
        textPaint.setColor(Color.parseColor("#c9d1d9"));
        textPaint.setTextSize(26f);
        textPaint.setAntiAlias(true);

        recordSchedulePaint = new Paint();
        recordSchedulePaint.setColor(Color.parseColor("#2ea043"));
        recordSchedulePaint.setStyle(Paint.Style.FILL);

        recordAlarmPaint = new Paint();
        recordAlarmPaint.setColor(Color.parseColor("#d29922"));
        recordAlarmPaint.setStyle(Paint.Style.FILL);

        needlePaint = new Paint();
        needlePaint.setColor(Color.parseColor("#ff4d4f"));
        needlePaint.setStrokeWidth(3f);
        needlePaint.setAntiAlias(true);

        labelBgPaint = new Paint();
        labelBgPaint.setColor(Color.parseColor("#ff4d4f"));
        labelBgPaint.setStyle(Paint.Style.FILL);
        labelBgPaint.setAntiAlias(true);

        resetToDay(new Date());
    }

    public void setOnTimeSelectedListener(OnTimeSelectedListener listener) {
        this.listener = listener;
    }

    public void resetToDay(Date date) {
        this.targetDate = getDayStart(date);
        this.viewStartSec = 0.0;
        this.viewDurationSec = 86400.0;
        this.currentTime = new Date(this.targetDate.getTime());
        invalidate();
    }

    public void setRecords(List<RecordSegment> segments) {
        this.segments = segments != null ? segments : new ArrayList<>();
        invalidate();
    }

    public void setCurrentTime(Date dt) {
        this.currentTime = dt;
        invalidate();
    }

    public Date getCurrentTime() {
        return currentTime;
    }

    public void setZoomDurationHours(float hours) {
        double newDuration = hours * 3600.0;
        double currentOffset = getSecOffsetFromDayStart(currentTime);
        this.viewDurationSec = Math.max(600.0, Math.min(86400.0, newDuration));
        this.viewStartSec = Math.max(0.0, Math.min(86400.0 - viewDurationSec, currentOffset - viewDurationSec / 2.0));
        invalidate();
    }

    private Date getDayStart(Date d) {
        Calendar c = Calendar.getInstance();
        c.setTime(d);
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTime();
    }

    private double getSecOffsetFromDayStart(Date d) {
        return (d.getTime() - targetDate.getTime()) / 1000.0;
    }

    private float secToX(double secOffset, float width) {
        double frac = (secOffset - viewStartSec) / viewDurationSec;
        return (float) (frac * width);
    }

    private double xToSec(float x, float width) {
        double frac = Math.max(0.0, Math.min(1.0, x / width));
        return viewStartSec + frac * viewDurationSec;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float w = getWidth();
        float h = getHeight();
        if (w <= 0 || h <= 0) return;

        // 1. Background
        canvas.drawRect(0, 0, w, h, bgPaint);

        // Ruler zone is top half, record strip is bottom half
        float rulerHeight = h * 0.45f;
        float recordTop = rulerHeight;
        float recordBottom = h;

        canvas.drawRect(0, 0, w, rulerHeight, rulerBgPaint);

        // 2. Draw Recording segments
        Date dayStart = targetDate;
        for (RecordSegment seg : segments) {
            double startSec = getSecOffsetFromDayStart(seg.getStartTime());
            double endSec = getSecOffsetFromDayStart(seg.getEndTime());

            if (endSec < viewStartSec || startSec > viewStartSec + viewDurationSec) {
                continue;
            }

            float x1 = Math.max(0, secToX(startSec, w));
            float x2 = Math.min(w, secToX(endSec, w));

            Paint paint = "alarm".equalsIgnoreCase(seg.getRecordType()) ? recordAlarmPaint : recordSchedulePaint;
            canvas.drawRect(x1, recordTop + 4, x2, recordBottom - 4, paint);
        }

        // 3. Draw Ruler ticks and labels
        double tickIntervalSec = (viewDurationSec <= 3600) ? 300 : (viewDurationSec <= 14400) ? 900 : 3600;
        double firstTick = Math.floor(viewStartSec / tickIntervalSec) * tickIntervalSec;

        Calendar tickCal = Calendar.getInstance();
        for (double sec = firstTick; sec <= viewStartSec + viewDurationSec; sec += tickIntervalSec) {
            if (sec < 0 || sec > 86400) continue;
            float x = secToX(sec, w);

            boolean isHour = (sec % 3600 == 0);
            float tickH = isHour ? rulerHeight * 0.5f : rulerHeight * 0.25f;

            canvas.drawLine(x, rulerHeight - tickH, x, rulerHeight, tickPaint);

            if (isHour || viewDurationSec <= 14400) {
                tickCal.setTime(dayStart);
                tickCal.add(Calendar.SECOND, (int) sec);
                String label = tickFormat.format(tickCal.getTime());
                float tw = textPaint.measureText(label);
                canvas.drawText(label, x - tw / 2f, rulerHeight - tickH - 6, textPaint);
            }
        }

        // 4. Draw Current Playhead Needle
        double currentSec = getSecOffsetFromDayStart(currentTime);
        if (currentSec >= viewStartSec && currentSec <= viewStartSec + viewDurationSec) {
            float needleX = secToX(currentSec, w);

            // Needle line
            canvas.drawLine(needleX, 0, needleX, h, needlePaint);

            // Top Triangle Indicator
            Path triangle = new Path();
            triangle.moveTo(needleX - 10, 0);
            triangle.lineTo(needleX + 10, 0);
            triangle.lineTo(needleX, 14);
            triangle.close();
            canvas.drawPath(triangle, labelBgPaint);

            // Time label badge at the needle
            String timeText = timeFormat.format(currentTime);
            float badgeW = textPaint.measureText(timeText) + 16;
            float badgeH = 32f;
            float badgeX = Math.max(4, Math.min(w - badgeW - 4, needleX - badgeW / 2f));
            float badgeY = h - badgeH - 2;

            RectF badgeRect = new RectF(badgeX, badgeY, badgeX + badgeW, badgeY + badgeH);
            canvas.drawRoundRect(badgeRect, 6, 6, labelBgPaint);

            textPaint.setColor(Color.WHITE);
            canvas.drawText(timeText, badgeX + 8, badgeY + 24, textPaint);
            textPaint.setColor(Color.parseColor("#c9d1d9"));
        }
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        float x = event.getX();
        float w = getWidth();
        if (w <= 0) return super.onTouchEvent(event);

        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                isDragging = true;
                seekToX(x, w, true);
                return true;
            case MotionEvent.ACTION_MOVE:
                if (isDragging) {
                    seekToX(x, w, true);
                    return true;
                }
                break;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                if (isDragging) {
                    isDragging = false;
                    seekToX(x, w, false);
                    return true;
                }
                break;
        }
        return super.onTouchEvent(event);
    }

    private void seekToX(float x, float width, boolean dragging) {
        double sec = xToSec(x, width);
        Calendar cal = Calendar.getInstance();
        cal.setTime(targetDate);
        cal.add(Calendar.SECOND, (int) Math.round(sec));
        this.currentTime = cal.getTime();
        invalidate();

        if (listener != null) {
            listener.onTimeSelected(currentTime, dragging);
        }
    }
}

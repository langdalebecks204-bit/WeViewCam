# Android UI Video Aspect Ratio & Channel Picker Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement video aspect ratio preservation (16:9, 4:3, Fill) in `SurveillanceSurfaceView` for live view and playback, and optimize the live view channel picker dialog into an accordion-style single-expansion interaction.

**Architecture:** Custom layout and measurement in `SurveillanceSurfaceView` to letterbox/pillarbox video surfaces without distortion. Add aspect ratio cycle button in Live and Playback toolbars. Refactor `ExpandableListView` group handling in `LiveViewFragment` for accordion interaction.

**Tech Stack:** Java 17, Android SDK (API 21-34), Android Views, Gradle.

## Global Constraints
- Maintain existing SurfaceHolder / Surface lifecycle for Hikvision SDK (`NET_DVR_RealPlaySurfaceChanged` / `NET_DVR_PlayBackSurfaceChanged`).
- Default video aspect ratio is 16:9 with letterboxing (black margins), avoiding vertical stretching on narrow portrait phone screens.
- Keep toolbar compact and responsive across screen orientations.
- Channel picker defaults to collapsed device groups, expanding only the clicked device and collapsing others.

---

### Task 1: AspectRatio Engine in `SurveillanceSurfaceView`

**Files:**
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/view/SurveillanceSurfaceView.java`

**Interfaces:**
- Produces:
  - `SurveillanceSurfaceView.AspectRatioMode` (`RATIO_16_9`, `RATIO_4_3`, `RATIO_FILL`)
  - `SurveillanceSurfaceView.setAspectRatioMode(AspectRatioMode mode)`
  - `SurveillanceSurfaceView.getAspectRatioMode() -> AspectRatioMode`

- [ ] **Step 1: Implement `AspectRatioMode` and `onMeasure`/`onLayout` in `SurveillanceSurfaceView`**

In `SurveillanceSurfaceView.java`:
1. Define the enum:
```java
    public enum AspectRatioMode {
        RATIO_16_9("16:9", 16.0f / 9.0f),
        RATIO_4_3("4:3", 4.0f / 3.0f),
        RATIO_FILL("铺满", 0f);

        private final String label;
        private final float ratio;

        AspectRatioMode(String label, float ratio) {
            this.label = label;
            this.ratio = ratio;
        }

        public String getLabel() { return label; }
        public float getRatio() { return ratio; }
    }
```
2. Add member variable:
```java
    private AspectRatioMode aspectRatioMode = AspectRatioMode.RATIO_16_9;
```
3. Implement `onMeasure`:
```java
    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        super.onMeasure(widthMeasureSpec, heightMeasureSpec);
        int containerWidth = getMeasuredWidth();
        int containerHeight = getMeasuredHeight();

        if (containerWidth <= 0 || containerHeight <= 0 || surfaceView == null) {
            return;
        }

        int targetWidth = containerWidth;
        int targetHeight = containerHeight;

        if (aspectRatioMode != null && aspectRatioMode.getRatio() > 0) {
            float desiredRatio = aspectRatioMode.getRatio();
            float containerRatio = (float) containerWidth / containerHeight;

            if (containerRatio > desiredRatio) {
                // Container is wider than desired ratio -> fit height, letterbox left/right
                targetHeight = containerHeight;
                targetWidth = Math.round(containerHeight * desiredRatio);
            } else {
                // Container is taller than desired ratio -> fit width, letterbox top/bottom
                targetWidth = containerWidth;
                targetHeight = Math.round(containerWidth / desiredRatio);
            }
        }

        // Measure surfaceView with calculated dimensions
        int childWidthSpec = MeasureSpec.makeMeasureSpec(targetWidth, MeasureSpec.EXACTLY);
        int childHeightSpec = MeasureSpec.makeMeasureSpec(targetHeight, MeasureSpec.EXACTLY);
        surfaceView.measure(childWidthSpec, childHeightSpec);
    }

    @Override
    protected void onLayout(boolean changed, int left, int top, int right, int bottom) {
        super.onLayout(changed, left, top, right, bottom);

        // Center surfaceView inside the container
        if (surfaceView != null) {
            int containerWidth = right - left;
            int containerHeight = bottom - top;
            int surfaceWidth = surfaceView.getMeasuredWidth();
            int surfaceHeight = surfaceView.getMeasuredHeight();

            int l = (containerWidth - surfaceWidth) / 2;
            int t = (containerHeight - surfaceHeight) / 2;
            int r = l + surfaceWidth;
            int b = t + surfaceHeight;
            surfaceView.layout(l, t, r, b);
        }
    }
```
4. Add getter and setter:
```java
    public void setAspectRatioMode(AspectRatioMode mode) {
        if (mode == null) mode = AspectRatioMode.RATIO_16_9;
        if (this.aspectRatioMode != mode) {
            this.aspectRatioMode = mode;
            requestLayout();
            invalidate();
        }
    }

    public AspectRatioMode getAspectRatioMode() {
        return aspectRatioMode;
    }
```

- [ ] **Step 2: Commit Task 1**

```bash
git add WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/view/SurveillanceSurfaceView.java
git commit -m "feat(android): add aspect ratio preservation and modes to SurveillanceSurfaceView"
```

---

### Task 2: Aspect Ratio Toggle Controls in Live & Playback Toolbars

**Files:**
- Modify: `WeViewCam_android/app/src/main/res/layout/fragment_live_view.xml`
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/live/LiveViewFragment.java`
- Modify: `WeViewCam_android/app/src/main/res/layout/fragment_playback.xml`
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/playback/PlaybackFragment.java`

**Interfaces:**
- Consumes: `SurveillanceSurfaceView.setAspectRatioMode`, `SurveillanceSurfaceView.getAspectRatioMode`

- [ ] **Step 1: Add aspect ratio button in `fragment_live_view.xml` and `fragment_playback.xml`**

1. In `fragment_live_view.xml` row 1:
Add `btn_aspect_ratio`:
```xml
            <Button
                android:id="@+id/btn_aspect_ratio"
                android:layout_width="0dp"
                android:layout_height="match_parent"
                android:layout_weight="1"
                android:layout_marginStart="4dp"
                android:text="16:9"
                style="@style/SurveillanceButton" />
```
2. In `fragment_playback.xml`:
Add `btn_playback_aspect_ratio` in top retrieval bar.

- [ ] **Step 2: Wire up cycle behavior in `LiveViewFragment.java` and `PlaybackFragment.java`**

In `LiveViewFragment.java`:
```java
    private Button btnAspectRatio;
    private SurveillanceSurfaceView.AspectRatioMode currentAspectRatio = SurveillanceSurfaceView.AspectRatioMode.RATIO_16_9;

    private void cycleAspectRatio() {
        if (currentAspectRatio == SurveillanceSurfaceView.AspectRatioMode.RATIO_16_9) {
            currentAspectRatio = SurveillanceSurfaceView.AspectRatioMode.RATIO_4_3;
        } else if (currentAspectRatio == SurveillanceSurfaceView.AspectRatioMode.RATIO_4_3) {
            currentAspectRatio = SurveillanceSurfaceView.AspectRatioMode.RATIO_FILL;
        } else {
            currentAspectRatio = SurveillanceSurfaceView.AspectRatioMode.RATIO_16_9;
        }
        btnAspectRatio.setText(currentAspectRatio.getLabel());
        for (SurveillanceSurfaceView vp : viewports) {
            if (vp != null) vp.setAspectRatioMode(currentAspectRatio);
        }
        if (viewportSingle != null) {
            viewportSingle.setAspectRatioMode(currentAspectRatio);
        }
        Toast.makeText(getContext(), "画面比例已切换至: " + currentAspectRatio.getLabel(), Toast.LENGTH_SHORT).show();
    }
```
Apply corresponding logic in `PlaybackFragment.java`.

- [ ] **Step 3: Commit Task 2**

```bash
git add WeViewCam_android/app/src/main/res/layout/fragment_live_view.xml \
        WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/live/LiveViewFragment.java \
        WeViewCam_android/app/src/main/res/layout/fragment_playback.xml \
        WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/playback/PlaybackFragment.java
git commit -m "feat(android): add aspect ratio cycle toggle in live view and playback toolbars"
```

---

### Task 3: Channel Picker Accordion Single-Expand Optimization

**Files:**
- Modify: `WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/live/LiveViewFragment.java`

- [ ] **Step 1: Refactor `showChannelPickerDialog` in `LiveViewFragment.java`**

1. Remove:
```java
// DELETE:
for (int i = 0; i < validDevices.size(); i++) {
    elvTree.expandGroup(i);
}
```
2. Implement accordion listener:
```java
        elvTree.setOnGroupExpandListener(groupPosition -> {
            for (int i = 0; i < validDevices.size(); i++) {
                if (i != groupPosition) {
                    elvTree.collapseGroup(i);
                }
            }
        });
```
3. Auto-expand only current device if active:
```java
        if (currentCh != null && currentCh.getDeviceId() != null) {
            for (int i = 0; i < validDevices.size(); i++) {
                if (currentCh.getDeviceId().equals(validDevices.get(i).getDeviceId())) {
                    elvTree.expandGroup(i);
                    elvTree.setSelectedGroup(i);
                    break;
                }
            }
        }
```

- [ ] **Step 2: Commit Task 3**

```bash
git add WeViewCam_android/app/src/main/java/com/weviewcam/client/ui/live/LiveViewFragment.java
git commit -m "feat(android): optimize channel picker with default-collapsed accordion interaction"
```

---

### Task 4: Compilation, Testing, and APK Packaging

**Files:**
- Output: `WeViewCam_android/weviewcam_android_v0.1.0.apk`

- [ ] **Step 1: Run unit tests**

```bash
cd WeViewCam_android && ./gradlew testDebugUnitTest
```

- [ ] **Step 2: Build signed release APK**

```bash
cd WeViewCam_android && ./gradlew assembleRelease
```

- [ ] **Step 3: Commit updated APK**

```bash
git add WeViewCam_android/weviewcam_android_v0.1.0.apk
git commit -m "build(android): package updated APK with aspect ratio fix and accordion channel picker"
```

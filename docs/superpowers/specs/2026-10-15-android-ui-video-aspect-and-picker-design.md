# Android 客户端界面与播放体验优化规格说明书

## 1. 目标与背景
针对 Android 端视频监控播放过程中画面比例失真拉伸，以及选择通道时全部设备同时展开导致翻页查找效率低的问题，本方案进行两项核心优化：
1. **视频播放画面比例自适应**：彻底解决竖屏狭长视口下拉伸画面人物变形的问题，默认锁定 16:9 黄金监控比例居中呈现，并支持 16:9 / 4:3 / 铺满自由切换；
2. **通道选择手风琴交互体验**：打开通道选择弹窗时默认只显示设备，点击设备时单开该设备通道，并自动折叠其它设备，大幅提升选台效率。

---

## 2. 视频播放比例自适应方案

### 2.1 比例枚举定义
在 `SurveillanceSurfaceView.java` 中增加枚举：
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

### 2.2 自适应尺寸计算逻辑 (`onMeasure` & `onLayout`)
在 `SurveillanceSurfaceView` 中：
- 容器自身占满父布局分配的空间（保留网格、选中间隙及边框高亮）；
- 对内部的 `surfaceView` 进行比例测算：
  - 若 `mode == RATIO_FILL`：`childWidth = containerWidth`, `childHeight = containerHeight`；
  - 若 `mode.getRatio() > 0`：
    - 设容器宽高比为 `containerAspect = (float) containerWidth / containerHeight`；
    - 若 `containerAspect > mode.getRatio()`（容器偏宽，如横屏）：以高为基准，`targetHeight = containerHeight`, `targetWidth = (int)(containerHeight * mode.getRatio())`；
    - 若 `containerAspect <= mode.getRatio()`（容器偏高，如竖屏）：以宽为基准，`targetWidth = containerWidth`, `targetHeight = (int)(containerWidth / mode.getRatio())`；
    - 对 `surfaceView` 布局在居中位置：
      `left = (containerWidth - targetWidth) / 2`，`top = (containerHeight - targetHeight) / 2`。
- 视频未填充区域保持黑色背景 (`Color.BLACK`)，天然形成类似专业播放器的 Letterbox 效果，彻底消除畸变。

### 2.3 工具栏比例切换按钮
- 在 `LiveViewFragment` 工具栏第一行与 `PlaybackFragment` 工具栏中分别增加【16:9】比例切换按钮；
- 点击后按 `16:9 -> 4:3 -> 铺满 -> 16:9` 顺次循环切换，并即时更新视口模式与按钮文字。

---

## 3. 实时预览通道选择弹窗优化方案

### 3.1 默认全折叠 + 手风琴（Accordion）交互
在 `LiveViewFragment.java` 的 `showChannelPickerDialog` 中：
1. **移除历史全展开循环**：删除原 `for (int i = 0; i < validDevices.size(); i++) elvTree.expandGroup(i);`；
2. **手风琴互斥单开**：
   ```java
   elvTree.setOnGroupExpandListener(new ExpandableListView.OnGroupExpandListener() {
       @Override
       public void onGroupExpand(int groupPosition) {
           for (int i = 0; i < validDevices.size(); i++) {
               if (i != groupPosition) {
                   elvTree.collapseGroup(i);
               }
           }
       }
   });
   ```
3. **定位当前通道**：
   若当前视口已有正在播放的通道，查找该通道所属设备的索引 `curGroupIndex`，执行 `elvTree.expandGroup(curGroupIndex)` 并滚动至该设备位置；若当前视口为空，则所有设备全部保持折叠。

---

## 4. 验证与测试方案
1. **比例自适应验证**：
   - 竖屏状态下播放 1080P/720P 监控流，验证画面是否保持 16:9 居中显示，人脸、球体、网格无纵向压缩/拉伸；
   - 点击切换按钮，测试 4:3 模式与铺满模式是否平滑切换；
   - 在录像回放页面验证相同比例特性。
2. **通道选择手风琴验证**：
   - 多台设备配置下，点击“选择通道”，确认打开时界面整洁、设备默认全折叠；
   - 依次点击设备 A、设备 B，验证点击 B 时设备 A 自动收起、设备 B 展开；
   - 选中通道后正常切换并启动预览。

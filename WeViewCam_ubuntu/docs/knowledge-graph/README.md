# WeViewCam 项目知识图谱

本目录是 **WeViewCam 视频监控平台** 的结构化知识图谱：把「谁定义了什么、谁依赖谁、谁调用谁、数据怎么流动、哪里有问题」从散落的源码中抽取成一份可检索、可校验、可机器消费的资产。

图谱覆盖仓库内的自研代码（`core/`、`adapters/`、`ui/`、`tests/`、`main.py`、`scan_rtsp.py`）与交付脚本；随仓库附带的约 3700 个文件的海康 SDK 发行包被折叠为单个外部依赖节点。

---

## 一、产物清单

| 文件 | 形态 | 说明 |
| --- | --- | --- |
| [graph.html](graph.html) | 交互式可视化 | 自包含单文件（内嵌数据，无需联网）：分层画布、搜索、按层过滤、节点高亮、详情面板、缩放平移 |
| [knowledge-graph.json](knowledge-graph.json) | 机器可读图谱 | 132 节点 / 178 关系 + 17 项缺陷与风险 + 5 条关键流程 + 预计算布局坐标 |
| [01-architecture.md](01-architecture.md) | 架构文档 | 分层架构、职责边界、关键设计决策与权衡 |
| [02-module-index.md](02-module-index.md) | 索引（自动生成） | 每个模块的职责、类、方法与**准确行号** |
| [03-dependency-map.md](03-dependency-map.md) | 依赖文档 | 模块依赖矩阵、外部依赖与三级降级链条、循环依赖分析 |
| [04-runtime-flows.md](04-runtime-flows.md) | 流程文档 | 启动、实时预览、ONVIF 取流协商、录像回放、窗口重开流时序 |
| [05-domain-model.md](05-domain-model.md) | 领域模型 | 实体关系、状态机、Qt 信号总线、句柄生命周期 |
| [06-issues-and-roadmap.md](06-issues-and-roadmap.md) | 风险清单 | 17 项缺陷/风险（6 个 BUG + 11 个 RISK，含定位、影响、修复建议）与改进路线 |
| [tools/build_graph.py](tools/build_graph.py) | 生成器 | AST 抽取 + 覆盖层合并 + 渲染（JSON / Markdown / HTML） |
| [tools/verify_graph.py](tools/verify_graph.py) | 自检器 | 409 项断言：行号真实性、引用完整性、布局越界、产物一致性、HTML 自包含性、文档锚点、无头浏览器运行时冒烟 |
| [tools/graph_overlay.json](tools/graph_overlay.json) | 语义覆盖层 | 人工维护：分层、职责、领域关系、外部依赖、问题清单 |

---

## 二、怎么用

**看结构** → 用浏览器打开 `graph.html`：滚轮缩放、拖拽平移，点击任意节点查看职责/方法清单/关联问题，顶部搜索框支持按类名、模块名、问题编号过滤，图例可按层开关。

**查细节** → 打开 `02-module-index.md`，按模块定位类与方法及其行号；行号由 AST 抽取，可直接跳转。

**写代码/做工具** → 消费 `knowledge-graph.json`：

```python
import json
g = json.load(open("docs/knowledge-graph/knowledge-graph.json", encoding="utf-8"))

# 谁依赖了 HikvisionNativeDriver？
[t["from"] for t in g["edges"] if t["to"] == "cls:adapters/hikvision/driver.py#HikvisionNativeDriver"]
# 某个类的全部方法（含行号）
[n["meta"]["methods"] for n in g["nodes"] if n["id"] == "cls:core/player_controller.py#PlayerController"]
# 高危问题及其影响范围
[(i["id"], i["title"], i["affects"]) for i in g["issues"] if i["severity"] == "high"]
```

常见用途：影响面分析（改一个类的爆炸半径）、新人上手导览、评审清单生成、CI 卡点（如"新增模块必须出现在图谱中"）。

**更新图谱**（源码变更后）：

```bash
python docs/knowledge-graph/tools/build_graph.py    # 重新抽取 + 渲染
python docs/knowledge-graph/tools/verify_graph.py   # 409 项断言自检（含无头浏览器渲染冒烟）
```

---

## 三、图谱规模

| 维度 | 数量 | 说明 |
| --- | --- | --- |
| 节点总数 | 132 | |
| ├ 模块 | 33 | 含 7 个包的 `__init__.py` |
| ├ 类 | 26 | 含 3 个适配器、3 个 Qt 页面、4 个数据模型、3 个枚举 |
| ├ 顶层函数 | 25 | 含 12 个测试用例函数 |
| ├ 折叠节点 | 2 | `structures.py`（60 个 ctypes 定义）、`PlayCtrl.py`（4 个定义），成员明细存于节点 `meta.members` |
| ├ 外部依赖 | 12 | PyQt5、onvif-zeep、python-vlc、OpenCV、HCNetSDK 等 |
| ├ 配置与交付物 | 15 | `devices.json`、5 个 shell/ps1 脚本、README、图标、发布包、LICENSE 等 |
| └ 问题节点 | 17 | 6 个 BUG + 11 个 RISK |
| 关系总数 | 178 | 24 种类型：imports 57、affects 28、creates 16、uses 13、imports_lazy 10、signal 6、inherits 3… |
| 关键流程 | 5 | 启动、实时预览、ONVIF 协商、录像回放、窗口重开流 |

---

## 四、图谱如何保证可信

结构数据不是手抄的：`build_graph.py` 用 Python `ast` 解析全部 33 个模块，模块行数、类/方法/函数的定义行号、导入关系（含函数体内的延迟导入）全部由解释器级别的语法树得出。人工只负责机器推不出来的部分——分层归属、职责描述、领域关系（谁实例化谁、信号连到谁）、外部依赖、风险清单。

`verify_graph.py` 把可信度变成 409 条可重复执行的断言，其中最关键的四类：

1. **行号真实性**：每个类/方法/函数节点的 `line` 必须在源码中确实指向对应的 `class` / `def`（含装饰器窗口匹配）；
2. **引用完整性**：178 条边与全部连线的两端都必须存在于节点集合中，不允许悬空引用；
3. **产物一致性**：`graph.html` 内嵌的数据必须与 `knowledge-graph.json` **逐字节等价**，防止两份数据漂移；
4. **运行时冒烟**：调用无头浏览器真实渲染 `graph.html`，断言无 JS 异常、实际画出的节点数等于数据中的节点数、分层色带数量正确。语法检查通过但页面全空的情况，只有这一步能拦住（该检查正是在修掉一次 `G.bands` / `G.layout.bands` 笔误导致的空白页之后补上的）。

当前状态：**409 项断言全部通过**，仓库自带测试 **12 passed**（`python -m pytest tests -q`）。此外，图谱结论还经过一轮独立对抗式复核，其中一条错误结论被推翻并修正（见 [06-issues-and-roadmap.md §6.7](06-issues-and-roadmap.md)）。

---

## 五、数据模型

### 节点

```jsonc
{
  "id": "cls:core/player_controller.py#PlayerController",  // 稳定标识
  "type": "class",              // module|class|function|group|external|issue|config|script|artifact|resource|doc|constant
  "name": "PlayerController",
  "layer": "core",              // 分层 id
  "path": "core/player_controller.py",
  "line": 40,                   // 定义起始行
  "desc": "视口调度服务：…",
  "tags": ["服务", "门面"],
  "meta": { "bases": ["object"], "methods": [ {"name": "...", "line": 47, "kind": "method", "doc": "..."} ] }
}
```

id 命名约定：`mod:<路径>` / `cls:<路径>#<类>` / `fn:<路径>#<函数>` / `grp:<路径>` / `ext:<依赖名>` / `issue:<编号>`。

### 关系类型

| 类别 | 类型 | 含义 |
| --- | --- | --- |
| 结构 | `imports` / `imports_lazy` | 模块顶层导入 / 函数体内延迟导入 |
| 结构 | `inherits` | 类继承 |
| 结构 | `contains` / `defines` | 控件组合 / 模块定义 |
| 行为 | `creates` / `instantiates` / `calls` | 创建、实例化、调用 |
| 行为 | `uses` / `reads` / `reads_writes` / `writes` | 使用与数据读写 |
| 行为 | `signal` | Qt 信号槽连线（含信号名说明） |
| 行为 | `registers_callback` | 窗口句柄 → 帧回调注册 |
| 集成 | `loads_library` / `sets_config` / `declares_abi` | 动态库加载与 SDK 配置 |
| 集成 | `optional_dep` / `depends_runtime` | 可选依赖与运行时依赖 |
| 质量 | `tested_by` / `documents` / `packages` / `launches` | 测试覆盖、文档、打包、启动 |
| 风险 | `affects` | 问题影响到的模块/类 |

---

## 六、边界（图谱不包含什么）

诚实说明覆盖范围，避免误用：

- **不含第三方 SDK 内部实现**：海康 SDK 的 3700 个文件只作为 `ext:HCNetSDK` / `art:HCNetSDK_bundle` 两个节点出现，其内部符号不在图谱内；
- **不含方法级调用图**：方法作为类节点的 `meta.methods` 属性存在（名字 + 行号），但"哪个方法调用了哪个方法"未建模（当前规模下类级 + 关键流程级已足够，全量调用图噪声大于收益）；
- **不含运行时实测数据**：CPU、首帧耗时、真实设备联调结果不在图谱内；
- **`scan_rtsp.py` 的路径特征库未展开**：候选 RTSP 路径是纯数据表，作为模块描述的一部分，未逐条建节点；
- **分层归属是人工判断**：`player.py` 归入"播放引擎层"而非"设备适配层"，这是设计意图的表达，不是 AST 事实。

---

## 七、维护约定

1. 新增/删除模块、类或方法后，**重新运行 `build_graph.py`**，图谱自动跟随源码；
2. 新增模块需要在 `build_graph.py` 的 `SCAN_PACKAGES` 中登记（当前：`core`、`adapters`、`ui`、`tests`）；
3. 语义信息（职责描述、分层、领域关系）在 `graph_overlay.json` 中维护；如果覆盖层引用了不存在的节点 id，构建会**直接失败并打印该 id**，防止文档与代码悄悄脱节；
4. 修复 `06-issues-and-roadmap.md` 中的问题时，同步删除 `graph_overlay.json` 里对应的 `issues` 条目；
5. 提交前跑一次 `verify_graph.py`，它是唯一能发现"行号漂移"的闸门。

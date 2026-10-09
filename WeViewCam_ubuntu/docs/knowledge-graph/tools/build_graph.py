#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeViewCam 知识图谱构建器
========================

从源码自动抽取结构图谱（模块 / 类 / 方法 / 顶层函数 / 导入关系），
与人工维护的语义覆盖层 ``graph_overlay.json`` 合并，产出：

    docs/knowledge-graph/knowledge-graph.json   机器可读图谱（节点 + 边 + 问题 + 流程）
    docs/knowledge-graph/02-module-index.md     模块 / 类 / 方法索引（自动生成）
    docs/knowledge-graph/graph.html             自包含交互式可视化（内嵌数据，无需联网）

结构部分由 AST 保证与源码一致（行号、方法名、导入关系不会手抄出错）；
语义部分（分层、职责、领域关系、风险）来自覆盖层。

用法::

    python docs/knowledge-graph/tools/build_graph.py            # 生成全部产物
    python docs/knowledge-graph/tools/build_graph.py --check    # 只校验，不写文件
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------------------
# 路径与扫描范围
# --------------------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).resolve().parent
OUT_DIR = TOOLS_DIR.parent
ROOT = OUT_DIR.parent.parent

SCAN_PACKAGES = ["core", "adapters", "ui", "tests"]
SCAN_FILES = ["main.py", "scan_rtsp.py"]
OVERLAY_PATH = TOOLS_DIR / "graph_overlay.json"

# 第三方依赖根模块 -> 外部依赖节点 id
EXTERNAL_IMPORT_MAP = {
    "PyQt5": "ext:PyQt5",
    "cv2": "ext:opencv",
    "vlc": "ext:python-vlc",
    "onvif": "ext:onvif-zeep",
    "zeep": "ext:onvif-zeep",
    "numpy": "ext:numpy",
    "pytest": "ext:pytest",
}

STDLIB_HINT = {
    "os", "sys", "json", "time", "uuid", "socket", "base64", "urllib", "threading",
    "typing", "datetime", "dataclasses", "enum", "abc", "logging", "ctypes", "tempfile",
    "pathlib", "collections", "functools", "itertools", "random", "math", "re", "traceback",
}

MAX_METHODS_PER_CLASS = 400  # 防御性上限


# --------------------------------------------------------------------------------------
# 1. 结构抽取
# --------------------------------------------------------------------------------------
def iter_source_files():
    """按稳定顺序枚举项目源码文件（不含 SDK 包与文档目录）。"""
    files = []
    for pkg in SCAN_PACKAGES:
        pkg_dir = ROOT / pkg
        if pkg_dir.is_dir():
            files.extend(sorted(pkg_dir.rglob("*.py")))
    for name in SCAN_FILES:
        p = ROOT / name
        if p.is_file():
            files.append(p)
    # 过滤缓存目录
    return [f for f in files if "__pycache__" not in f.parts]


def rel_id(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def first_line(text: str | None, limit: int = 200) -> str:
    if not text:
        return ""
    line = text.strip().splitlines()[0].strip()
    return line if len(line) <= limit else line[: limit - 1] + "…"


def dotted_to_module_id(dotted: str) -> str | None:
    """把 ``core.base_adapter`` 解析为 ``mod:core/base_adapter.py``（若存在）。"""
    parts = dotted.split(".")
    candidate = ROOT.joinpath(*parts)
    for probe in (candidate.with_suffix(".py"), candidate / "__init__.py"):
        try:
            if probe.is_file():
                return "mod:" + rel_id(probe)
        except OSError:
            continue
    return None


def collect_imports(tree: ast.AST, module_id: str):
    """返回导入边列表，元素为 ``{"from", "to", "type", "note"}``。"""
    module_level: dict[str, set[str]] = {}
    lazy: dict[str, set[str]] = {}

    def record(target: str | None, bucket: dict[str, set[str]], names: str = ""):
        if not target:
            return
        bucket.setdefault(target, set())
        if names:
            bucket[target].add(names)

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                record(_external_or_project(alias.name), module_level, alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # 本项目未使用相对导入
                continue
            base = node.module or ""
            target = dotted_to_module_id(base) or _external_or_project(base)
            names = ",".join(a.name for a in node.names)
            record(target, module_level, names)

    # 函数/方法体内的延迟导入
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Import):
                for alias in sub.names:
                    record(_external_or_project(alias.name), lazy, alias.name)
            elif isinstance(sub, ast.ImportFrom):
                if sub.level:
                    continue
                base = sub.module or ""
                target = dotted_to_module_id(base) or _external_or_project(base)
                names = ",".join(a.name for a in sub.names)
                record(target, lazy, names)

    def to_edges(bucket, etype):
        edges = []
        for target, names in sorted(bucket.items()):
            edges.append({
                "from": module_id,
                "to": target,
                "type": etype,
                "note": "导入: " + ",".join(sorted(names))[:160] if names else "",
            })
        return edges

    return to_edges(module_level, "imports") + to_edges(lazy, "imports_lazy")


def _external_or_project(dotted: str) -> str | None:
    """解析导入目标：项目模块 -> mod:*，已知三方 -> ext:*，其余返回 None。"""
    project = dotted_to_module_id(dotted)
    if project:
        return project
    root = dotted.split(".")[0]
    if root in EXTERNAL_IMPORT_MAP:
        return EXTERNAL_IMPORT_MAP[root]
    return None


def extract_structure(collapse: dict[str, str]):
    """遍历源码，产出 (nodes, edges)。"""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edge_keys: set[tuple] = set()

    def add_edge(edge: dict):
        key = (edge["from"], edge["to"], edge["type"])
        if key in seen_edge_keys:
            return
        seen_edge_keys.add(key)
        edges.append(edge)

    for path in iter_source_files():
        rel = rel_id(path)
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:  # pragma: no cover - 源码不可解析时明确报错
            raise SystemExit(f"[build_graph] 无法解析 {rel}: {exc}") from exc

        lines = len(source.splitlines()) or 1
        module_id = "mod:" + rel
        is_package = path.name == "__init__.py"
        module_doc = first_line(ast.get_docstring(tree))

        classes, functions = [], []
        class_nodes = []
        func_nodes = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)

        collapsed = rel in collapse

        if not collapsed:
            for cls in classes:
                cid = f"cls:{rel}#{cls.name}"
                methods = []
                for item in cls.body[:MAX_METHODS_PER_CLASS]:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        kind = "method"
                        for dec in item.decorator_list:
                            dec_name = ast.unparse(dec)
                            if "staticmethod" in dec_name:
                                kind = "staticmethod"
                            elif "classmethod" in dec_name:
                                kind = "classmethod"
                        methods.append({
                            "name": item.name,
                            "line": item.lineno,
                            "kind": kind,
                            "doc": first_line(ast.get_docstring(item), 120),
                        })
                class_nodes.append(cid)
                nodes[cid] = {
                    "id": cid,
                    "type": "class",
                    "name": cls.name,
                    "layer": None,
                    "path": rel,
                    "line": cls.lineno,
                    "desc": first_line(ast.get_docstring(cls)),
                    "tags": [],
                    "meta": {
                        "bases": [ast.unparse(b) for b in cls.bases],
                        "methods": methods,
                        "is_abstract": any(
                            ast.unparse(b).endswith("ABC") or "ABC" == ast.unparse(b)
                            for b in cls.bases
                        ),
                    },
                }
            for fn in functions:
                fid = f"fn:{rel}#{fn.name}"
                func_nodes.append(fid)
                nodes[fid] = {
                    "id": fid,
                    "type": "function",
                    "name": fn.name,
                    "layer": None,
                    "path": rel,
                    "line": fn.lineno,
                    "desc": first_line(ast.get_docstring(fn)),
                    "tags": [],
                    "meta": {
                        "args": [a.arg for a in fn.args.args],
                        "is_async": isinstance(fn, ast.AsyncFunctionDef),
                    },
                }

        module_meta = {
            "lines": lines,
            "is_package": is_package,
            "classes": class_nodes,
            "functions": func_nodes,
        }
        if collapsed:
            members = [f"{c.name}@{c.lineno}" for c in classes]
            members += [f"{f.name}@{f.lineno}" for f in functions]
            gid = "grp:" + rel
            nodes[gid] = {
                "id": gid,
                "type": "group",
                "name": collapse[rel],
                "layer": None,
                "path": rel,
                "line": 1,
                "desc": first_line(ast.get_docstring(tree)),
                "tags": ["折叠节点"],
                "meta": {"count": len(classes) + len(functions), "members": members},
            }
            module_meta["collapsed_into"] = gid

        nodes[module_id] = {
            "id": module_id,
            "type": "module",
            "name": rel,
            "layer": None,
            "path": rel,
            "line": 1,
            "desc": module_doc,
            "tags": [],
            "meta": module_meta,
        }

        for edge in collect_imports(tree, module_id):
            if edge["to"] in nodes or edge["to"].startswith("ext:"):
                # ext: 节点稍后由覆盖层补充，先记录，合并阶段统一校验
                add_edge(edge)

    return nodes, edges


# --------------------------------------------------------------------------------------
# 2. 合并覆盖层
# --------------------------------------------------------------------------------------
def load_overlay() -> dict:
    with OVERLAY_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def merge(structure_nodes: dict, structure_edges: list, overlay: dict):
    nodes = dict(structure_nodes)
    edges = list(structure_edges)

    # 2.1 覆盖层节点属性
    for nid, patch in overlay.get("nodes", {}).items():
        if nid not in nodes:
            raise SystemExit(f"[build_graph] 覆盖层引用了不存在的节点: {nid}")
        node = nodes[nid]
        if patch.get("layer"):
            node["layer"] = patch["layer"]
        if patch.get("desc"):
            node["desc"] = patch["desc"]
        if patch.get("tags"):
            node["tags"] = patch["tags"]

    # 2.2 追加外部依赖 / 配置 / 脚本 / 常量节点
    for extra in overlay.get("extra_nodes", []):
        if extra["id"] in nodes:
            raise SystemExit(f"[build_graph] 节点 id 重复: {extra['id']}")
        nodes[extra["id"]] = {
            "id": extra["id"],
            "type": extra.get("type", "artifact"),
            "name": extra.get("name", extra["id"]),
            "layer": extra.get("layer", "artifact"),
            "path": None,
            "line": None,
            "desc": extra.get("desc", ""),
            "tags": extra.get("tags", []),
            "meta": extra.get("meta", {}),
        }

    # 2.3 风险与缺陷节点
    for issue in overlay.get("issues", []):
        iid = "issue:" + issue["id"]
        nodes[iid] = {
            "id": iid,
            "type": "issue",
            "name": f"{issue['id']} {issue['title']}",
            "layer": "issue",
            "path": None,
            "line": None,
            "desc": issue["detail"],
            "tags": [issue.get("severity", "info"), "缺陷" if issue["id"].startswith("BUG") else "风险"],
            "meta": {
                "severity": issue.get("severity"),
                "where": issue.get("where"),
                "fix": issue.get("fix"),
            },
        }
        for target in issue.get("affects", []):
            edges.append({"from": iid, "to": target, "type": "affects", "note": issue.get("where", "")})

    # 2.4 手工语义边
    for edge in overlay.get("extra_edges", []):
        edges.append({
            "from": edge["from"],
            "to": edge["to"],
            "type": edge["type"],
            "note": edge.get("note", ""),
        })

    # 2.5 去重
    unique, seen = [], set()
    for edge in edges:
        key = (edge["from"], edge["to"], edge["type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)

    # 2.6 校验引用完整性
    dangling = [e for e in unique if e["from"] not in nodes or e["to"] not in nodes]
    if dangling:
        detail = "\n".join(f"  {e['from']} -> {e['to']} ({e['type']})" for e in dangling[:20])
        raise SystemExit(f"[build_graph] 存在悬空边，节点未定义:\n{detail}")

    # 2.7 分层兜底
    fallback_layer = {
        "core": "core", "adapters": "adapter", "ui": "ui", "tests": "test",
    }
    for node in nodes.values():
        if node.get("layer"):
            continue
        head = (node["path"] or "").split("/")[0]
        node["layer"] = fallback_layer.get(head, "entry")

    return nodes, unique


# --------------------------------------------------------------------------------------
# 3. 布局（确定性分层布局，供 HTML 使用）
# --------------------------------------------------------------------------------------
NODE_W, NODE_H, V_GAP, COL_GAP, MAX_PER_COL = 250, 44, 8, 46, 15
BAND_PAD, HEADER_H = 26, 64


def layout(nodes: dict, layers: list[dict], edges: list[dict]):
    ordered_layers = sorted(layers, key=lambda x: x["order"])
    positions: dict[str, dict] = {}
    bands = []
    x_cursor = 40

    for layer in ordered_layers:
        members = sorted(
            (n for n in nodes.values() if n["layer"] == layer["id"]),
            key=lambda n: (n["type"], n["id"]),
        )
        if not members:
            bands.append({"id": layer["id"], "name": layer["name"], "color": layer["color"],
                          "x": x_cursor, "width": 0, "count": 0})
            continue
        cols = -(-len(members) // MAX_PER_COL)
        width = cols * NODE_W + (cols - 1) * COL_GAP
        for idx, node in enumerate(members):
            col, row = divmod(idx, MAX_PER_COL)
            positions[node["id"]] = {
                "x": x_cursor + col * (NODE_W + COL_GAP),
                "y": HEADER_H + row * (NODE_H + V_GAP),
            }
        bands.append({"id": layer["id"], "name": layer["name"], "color": layer["color"],
                      "x": x_cursor, "width": width, "count": len(members)})
        x_cursor += width + BAND_PAD * 2

    max_rows = max((min(len([n for n in nodes.values() if n["layer"] == l["id"]]), MAX_PER_COL)
                    for l in ordered_layers), default=1)
    height = HEADER_H + max_rows * (NODE_H + V_GAP) + 80

    # 边的几何路径（三次贝塞尔）
    paths = []
    for edge in edges:
        src, dst = positions.get(edge["from"]), positions.get(edge["to"])
        if not src or not dst:
            continue
        x1, y1 = src["x"] + NODE_W, src["y"] + NODE_H / 2
        x2, y2 = dst["x"], dst["y"] + NODE_H / 2
        if x2 >= x1:
            dx = max(40.0, (x2 - x1) * 0.45)
            d = f"M {x1:.0f},{y1:.0f} C {x1 + dx:.0f},{y1:.0f} {x2 - dx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"
        else:
            # 回环：从右侧绕行
            xr = max(src["x"], dst["x"]) + NODE_W + 24
            d = (f"M {x1:.0f},{y1:.0f} C {xr:.0f},{y1:.0f} {xr:.0f},{y2:.0f} {x2 + NODE_W:.0f},{y2:.0f} "
                 f"L {x2:.0f},{y2:.0f}")
        paths.append({"from": edge["from"], "to": edge["to"], "type": edge["type"], "d": d,
                      "note": edge.get("note", "")})

    return positions, bands, paths, x_cursor + 40, height


# --------------------------------------------------------------------------------------
# 4. 产物渲染
# --------------------------------------------------------------------------------------
EDGE_COLORS = {
    "imports": "#3d5a80",
    "imports_lazy": "#4c6b8a",
    "inherits": "#f0883e",
    "creates": "#3fb950",
    "instantiates": "#3fb950",
    "uses": "#58a6ff",
    "calls": "#79c0ff",
    "signal": "#a371f7",
    "registers_callback": "#a371f7",
    "loads_library": "#d29922",
    "optional_dep": "#8b949e",
    "depends_runtime": "#8b949e",
    "affects": "#f85149",
    "tested_by": "#2ea043",
    "documents": "#6e7681",
    "packages": "#6e7681",
    "reads": "#8b949e",
    "reads_writes": "#8b949e",
    "writes": "#8b949e",
    "launches": "#f0883e",
    "defines": "#6e7681",
    "declares_abi": "#6e7681",
    "contains": "#a371f7",
    "sets_config": "#8b949e",
    "packages_artifact": "#6e7681",
}
DEFAULT_EDGE_COLOR = "#484f58"

TYPE_ICON = {
    "module": "▤", "class": "◈", "function": "ƒ", "group": "▣",
    "external": "⬡", "issue": "⚠", "config": "⚙", "script": "⌘",
    "artifact": "📦", "resource": "◉", "doc": "📄", "constant": "✱",
}


def render_html(graph: dict) -> str:
    payload = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    template = HTML_TEMPLATE
    return template.replace("__GRAPH_DATA__", payload)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WeViewCam 知识图谱</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: #0d1117; color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif; }
  #app { display: grid; grid-template-rows: auto 1fr; height: 100%; }
  header { padding: 10px 16px; background: #161b22; border-bottom: 1px solid #30363d; }
  header h1 { margin: 0 0 6px; font-size: 15px; color: #e6edf3; font-weight: 600; }
  header h1 span { color: #58a6ff; }
  .meta { font-size: 12px; color: #8b949e; }
  .bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; }
  input[type=search] { background: #0d1117; border: 1px solid #30363d; border-radius: 5px;
    color: #e6edf3; padding: 5px 9px; font-size: 12px; width: 260px; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip { font-size: 11px; padding: 3px 9px; border-radius: 11px; cursor: pointer;
    border: 1px solid #30363d; background: #21262d; color: #c9d1d9; user-select: none; }
  .chip.off { opacity: .35; }
  .chip .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
  #stage { position: relative; overflow: hidden; cursor: grab; }
  #stage.drag { cursor: grabbing; }
  svg { display: block; }
  .band { fill: #11151c; stroke: #21262d; }
  .band-label { fill: #8b949e; font-size: 17px; font-weight: 600; }
  .node rect { fill: #1b2029; stroke: #30363d; stroke-width: 1; rx: 5; }
  .node text { fill: #c9d1d9; font-size: 17px; }
  .node .type { fill: #8b949e; font-size: 15px; }
  .node { cursor: pointer; }
  .node.dim { opacity: .12; }
  .node.sel rect { stroke: #58a6ff; stroke-width: 2; }
  .node.issue rect { fill: #2b1a1c; stroke: #f85149; }
  .edge { fill: none; stroke-width: 1.2; opacity: .45; }
  .edge.dim { opacity: .05; }
  .edge.hot { opacity: 1; stroke-width: 2; }
  #panel { position: absolute; top: 12px; right: 12px; width: 340px; max-height: calc(100% - 24px);
    overflow: auto; background: #161b22f2; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 14px; font-size: 12px; line-height: 1.6; display: none; }
  #panel h2 { margin: 0 0 4px; font-size: 13px; color: #e6edf3; }
  #panel .kv { color: #8b949e; }
  #panel code { background: #0d1117; padding: 1px 5px; border-radius: 3px; color: #79c0ff; }
  #panel ul { margin: 6px 0 0 16px; padding: 0; }
  #panel li { margin: 1px 0; }
  #panel .close { position: absolute; top: 8px; right: 10px; cursor: pointer; color: #8b949e; }
  #panel .sev-high { color: #f85149; font-weight: 600; }
  #panel .sev-medium { color: #d29922; font-weight: 600; }
  #panel .sev-low { color: #8b949e; font-weight: 600; }
  .hint { font-size: 11px; color: #6e7681; }
  .zoom { position: absolute; left: 12px; bottom: 12px; display: flex; gap: 6px; }
  .zoom button { background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
    border-radius: 5px; width: 30px; height: 28px; cursor: pointer; font-size: 13px; }
</style>
</head>
<body>
<div id="app">
  <header>
    <h1>WeViewCam <span>知识图谱</span> <span class="hint" id="stats"></span></h1>
    <div class="meta" id="subtitle"></div>
    <div class="bar">
      <input type="search" id="search" placeholder="搜索节点：类 / 模块 / 问题编号…">
      <div class="legend" id="layerLegend"></div>
      <span class="hint">滚轮缩放 · 拖拽平移 · 单击查看详情</span>
    </div>
  </header>
  <div id="stage">
    <svg id="svg"></svg>
    <div id="panel"><span class="close" onclick="hidePanel()">✕</span><div id="panelBody"></div></div>
    <div class="zoom"><button onclick="zoomBy(1.2)">＋</button><button onclick="zoomBy(1/1.2)">－</button><button onclick="resetView()">⤢</button></div>
  </div>
</div>
<script type="application/json" id="graph-data">__GRAPH_DATA__</script>
<script>
const G = JSON.parse(document.getElementById('graph-data').textContent);
const NODE_W = G.layout.node_w, NODE_H = G.layout.node_h;
const nodesById = {};
G.nodes.forEach(n => { nodesById[n.id] = n; });

const TYPE_ICON = {
  module: '▤', class: '◈', function: 'ƒ', group: '▣',
  external: '⬡', issue: '⚠', config: '⚙', script: '⌘',
  artifact: '▦', resource: '◉', doc: '▤', constant: '✱'
};
function clip(s, n) { return s.length > n ? s.slice(0, n - 1) + '…' : s; }
function layerColor(id) {
  const l = G.layers.find(x => x.id === id);
  return l ? l.color : '#484f58';
}

const svg = document.getElementById('svg');
const stage = document.getElementById('stage');
const view = document.createElementNS('http://www.w3.org/2000/svg', 'g');
svg.appendChild(view);

const disabledLayers = new Set();
const bandLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
const edgeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
const nodeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
view.appendChild(bandLayer); view.appendChild(edgeLayer); view.appendChild(nodeLayer);

document.getElementById('stats').textContent =
  ` · ${G.nodes.length} 节点 / ${G.edges.length} 关系 / ${(G.issues||[]).length} 问题`;

// ---------- 背景与分层标题 ----------
G.layout.bands.forEach(b => {
  const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  r.setAttribute('x', b.x - 14); r.setAttribute('y', 20);
  r.setAttribute('width', Math.max(b.width + 28, 60));
  r.setAttribute('height', G.layout.height - 40);
  r.setAttribute('class', 'band'); r.setAttribute('rx', 10); r.setAttribute('opacity', '0.55');
  bandLayer.appendChild(r);
  const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  t.setAttribute('x', b.x - 2); t.setAttribute('y', 44);
  t.setAttribute('class', 'band-label'); t.textContent = `${b.name} (${b.count})`;
  bandLayer.appendChild(t);
});

// ---------- 边 ----------
const edgeEls = [];
G.paths.forEach(p => {
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', p.d);
  path.setAttribute('class', 'edge');
  path.setAttribute('stroke', G.edge_colors[p.type] || '#484f58');
  const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
  const src = nodesById[p.from] ? nodesById[p.from].name : p.from;
  const dst = nodesById[p.to] ? nodesById[p.to].name : p.to;
  title.textContent = `${src} —[${p.type}]→ ${dst}${p.note ? '\n' + p.note : ''}`;
  path.appendChild(title);
  edgeLayer.appendChild(path);
  edgeEls.push({ el: path, from: p.from, to: p.to });
});

// ---------- 节点 ----------
const nodeEls = {};
G.nodes.forEach(n => {
  const p = G.layout.positions[n.id];
  if (!p) return;
  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  g.setAttribute('class', 'node' + (n.type === 'issue' ? ' issue' : ''));
  g.setAttribute('transform', `translate(${p.x},${p.y})`);
  const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  rect.setAttribute('width', NODE_W); rect.setAttribute('height', NODE_H);
  g.appendChild(rect);
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  icon.setAttribute('x', 13); icon.setAttribute('y', 29); icon.setAttribute('class', 'type');
  icon.textContent = TYPE_ICON[n.type] || '•';
  g.appendChild(icon);
  const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  label.setAttribute('x', 38); label.setAttribute('y', 29);
  label.textContent = clip(n.name, 24);
  g.appendChild(label);
  const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  bar.setAttribute('x', 0); bar.setAttribute('y', NODE_H - 4);
  bar.setAttribute('width', NODE_W); bar.setAttribute('height', 4);
  bar.setAttribute('fill', layerColor(n.layer)); bar.setAttribute('rx', 1.5);
  g.appendChild(bar);
  g.style.display = 'none';
  g.addEventListener('click', ev => { ev.stopPropagation(); showPanel(n); highlight(n.id); });
  g.addEventListener('mouseenter', () => highlight(n.id));
  g.addEventListener('mouseleave', () => highlight(null));
  nodeLayer.appendChild(g);
  nodeEls[n.id] = g;
});

function applyVisibility() {
  G.nodes.forEach(n => {
    const el = nodeEls[n.id];
    if (el) el.style.display = disabledLayers.has(n.layer) ? 'none' : '';
  });
}

// ---------- 图例 ----------
const legend = document.getElementById('layerLegend');
G.layers.forEach(l => {
  const chip = document.createElement('span');
  chip.className = 'chip';
  chip.innerHTML = `<span class="dot" style="background:${l.color}"></span>${l.name}`;
  chip.onclick = () => {
    if (disabledLayers.has(l.id)) disabledLayers.delete(l.id); else disabledLayers.add(l.id);
    chip.classList.toggle('off');
    applyVisibility();
  };
  legend.appendChild(chip);
});

// ---------- 搜索 ----------
const search = document.getElementById('search');
search.addEventListener('input', () => {
  const q = search.value.trim().toLowerCase();
  if (!q) { G.nodes.forEach(n => nodeEls[n.id] && nodeEls[n.id].classList.remove('dim')); return; }
  G.nodes.forEach(n => {
    const el = nodeEls[n.id];
    if (!el) return;
    const hay = (n.name + ' ' + n.id + ' ' + (n.desc || '') + ' ' + (n.tags || []).join(' ')).toLowerCase();
    el.classList.toggle('dim', !hay.includes(q));
  });
});

// ---------- 高亮 ----------
function highlight(id) {
  edgeEls.forEach(e => {
    const hot = id && (e.from === id || e.to === id);
    e.el.classList.toggle('hot', !!hot);
    e.el.classList.toggle('dim', !!id && !hot);
  });
  if (!id) { G.nodes.forEach(n => nodeEls[n.id] && nodeEls[n.id].classList.remove('dim')); return; }
  const keep = new Set([id]);
  edgeEls.forEach(e => { if (e.from === id) keep.add(e.to); if (e.to === id) keep.add(e.from); });
  G.nodes.forEach(n => nodeEls[n.id] && nodeEls[n.id].classList.toggle('dim', !keep.has(n.id)));
}

// ---------- 详情面板 ----------
const panel = document.getElementById('panel');
const panelBody = document.getElementById('panelBody');
function esc(s) { return String(s == null ? '' : s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }
function showPanel(n) {
  let html = `<h2>${esc(n.name)}</h2>`;
  html += `<div class="kv">${esc(n.type)} · ${esc(n.layer)}${n.path ? ' · <code>' + esc(n.path) + (n.line ? ':' + n.line : '') + '</code>' : ''}</div>`;
  if (n.desc) html += `<p>${esc(n.desc)}</p>`;
  if (n.tags && n.tags.length) html += `<div>${n.tags.map(t => `<span class="chip">${esc(t)}</span>`).join(' ')}</div>`;
  const m = n.meta || {};
  if (m.where) html += `<div class="kv">位置：<code>${esc(m.where)}</code></div>`;
  if (m.severity) html += `<div class="kv">严重级别：<span class="sev-${esc(m.severity)}">${esc(m.severity)}</span></div>`;
  if (m.fix) html += `<p><b>建议：</b>${esc(m.fix)}</p>`;
  if (m.methods && m.methods.length) {
    html += `<div class="kv">方法 (${m.methods.length})：</div><ul>`;
    m.methods.forEach(x => { html += `<li><code>${esc(x.name)}()</code> :${x.line}${x.doc ? ' — ' + esc(x.doc) : ''}</li>`; });
    html += '</ul>';
  }
  if (m.members && m.members.length) {
    html += `<div class="kv">包含 (${m.members.length})：</div><ul>`;
    m.members.slice(0, 80).forEach(x => { html += `<li><code>${esc(x.split('@')[0])}</code> :${esc(x.split('@')[1])}</li>`; });
    if (m.members.length > 80) html += `<li class="kv">… 其余 ${m.members.length - 80} 项见 JSON</li>`;
    html += '</ul>';
  }
  if (m.related) html += `<div class="kv">关联：${m.related.map(esc).join(', ')}</div>`;
  panelBody.innerHTML = html;
  panel.style.display = 'block';
  document.querySelectorAll('.node.sel').forEach(e => e.classList.remove('sel'));
  if (nodeEls[n.id]) nodeEls[n.id].classList.add('sel');
}
function hidePanel() {
  panel.style.display = 'none';
  document.querySelectorAll('.node.sel').forEach(e => e.classList.remove('sel'));
  highlight(null);
}

// ---------- 平移缩放 ----------
let scale = 1, tx = 0, ty = 0;
function applyTransform() { view.setAttribute('transform', `translate(${tx},${ty}) scale(${scale})`); }
function zoomBy(k) { scale = Math.min(4, Math.max(0.2, scale * k)); applyTransform(); }
function resetView() { fit(); }
stage.addEventListener('wheel', e => {
  e.preventDefault();
  const rect = stage.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  const k = e.deltaY < 0 ? 1.1 : 1 / 1.1;
  const ns = Math.min(4, Math.max(0.2, scale * k));
  tx = mx - (mx - tx) * (ns / scale); ty = my - (my - ty) * (ns / scale);
  scale = ns; applyTransform();
}, { passive: false });
let dragging = false, lastX = 0, lastY = 0;
stage.addEventListener('mousedown', e => { dragging = true; lastX = e.clientX; lastY = e.clientY; stage.classList.add('drag'); });
window.addEventListener('mouseup', () => { dragging = false; stage.classList.remove('drag'); });
window.addEventListener('mousemove', e => {
  if (!dragging) return;
  tx += e.clientX - lastX; ty += e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY; applyTransform();
});
stage.addEventListener('click', () => hidePanel());

// ---------- 尺寸自适应 ----------
function fit() {
  const w = stage.clientWidth || window.innerWidth || 1280;
  const h = stage.clientHeight || (window.innerHeight - 90) || 720;
  svg.setAttribute('width', w); svg.setAttribute('height', h);
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  const k = Math.min(w / G.layout.width, h / G.layout.height, 1);
  scale = k * 0.98;
  tx = Math.max(10, (w - G.layout.width * scale) / 2);
  ty = Math.max(10, (h - G.layout.height * scale) / 2);
  applyTransform();
}
window.addEventListener('resize', fit);
window.addEventListener('load', fit);
fit();
requestAnimationFrame(fit);

// ---------- 初始化：默认只展开非 issue 层 ----------
G.layers.forEach(l => { /* 全部展开 */ });
applyVisibility();
document.getElementById('subtitle').textContent =
  `${G.meta.project} v${G.meta.version} · ${G.meta.runtime} · 入口 ${G.meta.entrypoint} · 生成于 ${G.meta.generated_at}`;
</script>
</body>
</html>
"""


def github_slug(text: str) -> str:
    """复刻 GitHub 标题锚点规则：小写、去除非字母数字/空格/连字符/下划线、空格转连字符。"""
    slug = text.strip().lower()
    slug = "".join(ch for ch in slug if ch.isalnum() or ch in " -_")
    return slug.replace(" ", "-")


def render_module_index(graph: dict) -> str:
    nodes = {n["id"]: n for n in graph["nodes"]}
    lines = [
        "# 模块 / 类 / 方法索引",
        "",
        "> 本文件由 `tools/build_graph.py` 自动生成，请勿手工编辑。",
        f"> 生成日期：{graph['meta']['generated_at']}　数据源：`knowledge-graph.json`",
        "",
        "行号均指向文件中的定义起始行（`def` / `class` / 赋值语句所在行）。",
        "",
        "## 目录",
        "",
    ]
    modules = sorted((n for n in graph["nodes"] if n["type"] == "module"), key=lambda n: n["id"])
    for m in modules:
        lines.append(f"- [{m['name']}](#{github_slug(m['name'])})")
    lines.append("")

    for m in modules:
        path = m["path"]
        layer = next((l["name"] for l in graph["layers"] if l["id"] == m["layer"]), m["layer"])
        lines.append(f"## {path}")
        lines.append("")
        lines.append(f"- **分层**：{layer}")
        lines.append(f"- **行数**：{m['meta'].get('lines', '?')}")
        if m["desc"]:
            lines.append(f"- **职责**：{m['desc']}")
        cls_ids = m["meta"].get("classes", [])
        fn_ids = m["meta"].get("functions", [])
        if m["meta"].get("collapsed_into"):
            gid = m["meta"]["collapsed_into"]
            g = nodes[gid]
            lines.append(f"- **折叠节点**：`{gid}`，含 {g['meta']['count']} 个定义，明细见 graph.html 与 JSON")
        if cls_ids:
            lines.append("")
            lines.append("### 类")
            for cid in cls_ids:
                c = nodes.get(cid)
                if not c:
                    continue
                bases = ", ".join(c["meta"].get("bases") or []) or "—"
                lines.append("")
                lines.append(f"#### `{c['name']}` :{c['line']}　(基类: {bases})")
                if c["desc"]:
                    lines.append("")
                    lines.append(f"{c['desc']}")
                methods = c["meta"].get("methods", [])
                if methods:
                    lines.append("")
                    lines.append("| 方法 | 行 | 类型 | 说明 |")
                    lines.append("| --- | --- | --- | --- |")
                    for mm in methods:
                        doc = (mm.get("doc") or "").replace("|", "\\|")
                        lines.append(f"| `{mm['name']}()` | {mm['line']} | {mm['kind']} | {doc} |")
        if fn_ids:
            lines.append("")
            lines.append("### 顶层函数")
            lines.append("")
            lines.append("| 函数 | 行 | 说明 |")
            lines.append("| --- | --- | --- |")
            for fid in fn_ids:
                f = nodes.get(fid)
                if not f:
                    continue
                doc = (f["desc"] or "").replace("|", "\\|")
                lines.append(f"| `{f['name']}()` | {f['line']} | {doc} |")
        lines.append("")

    lines.append("## 折叠节点明细")
    lines.append("")
    for g in sorted((n for n in graph["nodes"] if n["type"] == "group"), key=lambda n: n["id"]):
        lines.append(f"### `{g['path']}` — {g['name']}")
        lines.append("")
        lines.append(f"共 {g['meta']['count']} 个定义：" )
        lines.append("")
        members = g["meta"]["members"]
        for i in range(0, len(members), 4):
            chunk = members[i:i + 4]
            lines.append("- " + "　".join(f"`{x.split('@')[0]}` :{x.split('@')[1]}" for x in chunk))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_json(graph: dict) -> str:
    return json.dumps(graph, ensure_ascii=False, indent=2) + "\n"


# --------------------------------------------------------------------------------------
# 5. 主流程
# --------------------------------------------------------------------------------------
def build(check_only: bool = False) -> dict:
    overlay = load_overlay()
    structure_nodes, structure_edges = extract_structure(overlay.get("collapse", {}))
    nodes, edges = merge(structure_nodes, structure_edges, overlay)

    layers = overlay["layers"]
    positions, bands, paths, width, height = layout(nodes, layers, edges)

    counts: dict[str, int] = {}
    for n in nodes.values():
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    edge_counts: dict[str, int] = {}
    for e in edges:
        edge_counts[e["type"]] = edge_counts.get(e["type"], 0) + 1

    graph = {
        "meta": {
            "project": overlay["meta"]["project"],
            "version": overlay["meta"]["version"],
            "summary": overlay["meta"]["summary"],
            "entrypoint": overlay["meta"]["entrypoint"],
            "runtime": overlay["meta"]["runtime"],
            "generated_at": date.today().isoformat(),
            "generator": "docs/knowledge-graph/tools/build_graph.py",
            "source_root": str(ROOT),
            "stats": {
                "node_total": len(nodes),
                "edge_total": len(edges),
                "nodes_by_type": dict(sorted(counts.items())),
                "edges_by_type": dict(sorted(edge_counts.items())),
                "issues": len(overlay.get("issues", [])),
                "flows": len(overlay.get("flow_edges", [])),
            },
        },
        "layers": layers,
        "schema": {
            "node": {
                "id": "稳定标识：mod:<路径> | cls:<路径>#<类> | fn:<路径>#<函数> | grp:<路径> | ext:<名> | issue:<编号>",
                "type": "module|class|function|group|external|issue|config|script|artifact|resource|doc|constant",
                "layer": "分层 id，见 layers",
                "path": "仓库相对路径（外部依赖为 null）",
                "line": "定义起始行（外部依赖为 null）",
                "desc": "职责描述；自动抽取节点来自 docstring，其余来自覆盖层",
                "tags": "自由标签",
                "meta": "类型相关扩展：类含 bases/methods，模块含 lines/classes/functions，组节点含 members",
            },
            "edge": {"from": "节点 id", "to": "节点 id", "type": "关系类型", "note": "补充说明"},
        },
        "layers_order_note": "数组顺序即分层顺序（order 字段为准）",
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": sorted(edges, key=lambda e: (e["from"], e["to"], e["type"])),
        "issues": overlay.get("issues", []),
        "flows": overlay.get("flow_edges", []),
        "layout": {
            "positions": positions,
            "bands": bands,
            "width": width,
            "height": height,
            "node_w": NODE_W,
            "node_h": NODE_H,
        },
        "paths": paths,
        "edge_colors": EDGE_COLORS,
    }

    if check_only:
        return graph

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "knowledge-graph.json").write_text(render_json(graph), encoding="utf-8")
    (OUT_DIR / "02-module-index.md").write_text(render_module_index(graph), encoding="utf-8")
    (OUT_DIR / "graph.html").write_text(render_html(graph), encoding="utf-8")
    return graph


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 WeViewCam 知识图谱")
    parser.add_argument("--check", action="store_true", help="只校验并打印统计，不写文件")
    args = parser.parse_args()

    graph = build(check_only=args.check)
    stats = graph["meta"]["stats"]
    print(f"[build_graph] 节点 {stats['node_total']} / 边 {stats['edge_total']} / 问题 {stats['issues']} / 流程 {stats['flows']}")
    print(f"[build_graph] 节点分布: {json.dumps(stats['nodes_by_type'], ensure_ascii=False)}")
    print(f"[build_graph] 关系分布: {json.dumps(stats['edges_by_type'], ensure_ascii=False)}")
    if not args.check:
        for name in ("knowledge-graph.json", "02-module-index.md", "graph.html"):
            target = OUT_DIR / name
            print(f"[build_graph] 已写入 {target.relative_to(ROOT).as_posix()} ({target.stat().st_size} 字节)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

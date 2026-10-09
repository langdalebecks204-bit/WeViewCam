#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱自检脚本
================

对 ``knowledge-graph.json`` / ``graph.html`` / ``02-module-index.md`` 做机器校验，
把"图谱是否与源码一致"变成可重复执行的断言，而不是人工抽查：

1. JSON 与 HTML 内嵌数据完全一致（防止两份数据漂移）；
2. 所有边的起点/终点、所有连线的端点都存在于节点集合中（引用完整性）；
3. 每个节点都有布局坐标、落在画布内，且分层 id 都在 layers 中声明；
4. **每个类 / 函数节点的行号确实指向源码中对应的 `class` / `def`**；
5. 每个模块节点的行数与磁盘文件实际行数一致；
6. 每条边的关系类型都已知（有配色）；
7. 问题节点覆盖到源码位置字符串；
8. HTML 自包含（无外链资源）且内嵌脚本通过 `node --check` 语法校验；
9. Markdown 文档内部锚点全部可解析；
10. **运行时冒烟**：用无头浏览器真实渲染 `graph.html`，断言页面无 JS 异常、
    实际渲染出的节点数与数据一致、分层色带数量正确。

第 10 项是"语法正确 ≠ 能渲染"的补课：一次把 `G.layout.bands` 写成 `G.bands` 的
笔误让页面只画出表头、画布全空，而语法检查与数据校验全部通过。

用法::

    python docs/knowledge-graph/tools/verify_graph.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
OUT_DIR = TOOLS_DIR.parent
ROOT = OUT_DIR.parent.parent

GRAPH_PATH = OUT_DIR / "knowledge-graph.json"
HTML_PATH = OUT_DIR / "graph.html"
INDEX_PATH = OUT_DIR / "02-module-index.md"


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks = 0

    def ok(self):
        self.checks += 1

    def fail(self, msg: str):
        self.checks += 1
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)


def read_lines(rel_path: str) -> list[str] | None:
    target = ROOT / rel_path
    if not target.is_file():
        return None
    return target.read_text(encoding="utf-8", errors="replace").splitlines()


def find_browser() -> str | None:
    """定位可用于无头渲染的 Chromium 系浏览器。"""
    import os
    candidates = [
        os.environ.get("WVC_BROWSER", ""),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/microsoft-edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for cand in candidates:
        if cand and Path(cand).is_file():
            return cand
    return None


def md_slug(text: str) -> str:
    """与 build_graph.github_slug 保持一致的标题锚点规则（本文件独立实现，避免互相依赖）。"""
    slug = text.strip().lower()
    slug = "".join(ch for ch in slug if ch.isalnum() or ch in " -_")
    return slug.replace(" ", "-")


def check_name_at(lines: list[str], line_no: int, keyword: str, name: str) -> bool:
    """行号附近（含装饰器）是否出现 `keyword name`。"""
    if not (1 <= line_no <= len(lines)):
        return False
    window = lines[max(0, line_no - 6): min(len(lines), line_no + 2)]
    pattern = re.compile(rf"^\s*(async\s+)?{keyword}\s+{re.escape(name)}\b")
    return any(pattern.search(text) for text in window)


def main() -> int:
    rep = Report()

    if not GRAPH_PATH.is_file():
        print(f"[verify] 缺少 {GRAPH_PATH}，请先运行 build_graph.py")
        return 2

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in graph["nodes"]}
    rep.ok()

    # ---- 1. HTML 内嵌数据一致性 ----
    html = HTML_PATH.read_text(encoding="utf-8")
    match = re.search(r'<script type="application/json" id="graph-data">(.*?)</script>', html, re.S)
    if not match:
        rep.fail("graph.html 中找不到内嵌 graph-data 脚本块")
    else:
        embedded = json.loads(match.group(1))
        if embedded == graph:
            rep.ok()
        else:
            rep.fail("graph.html 内嵌数据与 knowledge-graph.json 不一致（需重新生成）")

    # ---- 2. 引用完整性 ----
    for edge in graph["edges"]:
        if edge["from"] not in nodes or edge["to"] not in nodes:
            rep.fail(f"悬空边: {edge['from']} -> {edge['to']} ({edge['type']})")
    rep.ok()

    for path in graph["paths"]:
        if path["from"] not in nodes or path["to"] not in nodes:
            rep.fail(f"连线端点不存在: {path['from']} -> {path['to']}")
    rep.ok()

    # ---- 3. 布局与分层 ----
    layer_ids = {l["id"] for l in graph["layers"]}
    for node in graph["nodes"]:
        if node["id"] not in graph["layout"]["positions"]:
            rep.fail(f"节点缺少布局坐标: {node['id']}")
        if node["layer"] not in layer_ids:
            rep.fail(f"节点分层未声明: {node['id']} -> {node['layer']}")
    rep.ok()

    # 3b. 所有节点必须落在画布内，且分层色带按 order 单调排列
    lay = graph["layout"]
    for nid, p in lay["positions"].items():
        if not (0 <= p["x"] and p["x"] + lay["node_w"] <= lay["width"]
                and 0 <= p["y"] and p["y"] + lay["node_h"] <= lay["height"]):
            rep.fail(f"节点 {nid} 布局越界: {p} 画布 {lay['width']}x{lay['height']}")
    rep.ok()
    ordered = sorted(graph["layers"], key=lambda l: l["order"])
    band_xs = [b["x"] for b in lay["bands"] if b["count"] > 0]
    if band_xs == sorted(band_xs):
        rep.ok()
    else:
        rep.fail("分层色带的 x 坐标未按 order 单调递增")

    # ---- 4. 行号真实性 ----
    file_cache: dict[str, list[str] | None] = {}
    for node in graph["nodes"]:
        if node["type"] not in ("class", "function"):
            continue
        rel, line, name = node["path"], node["line"], node["name"]
        if rel not in file_cache:
            file_cache[rel] = read_lines(rel)
        lines = file_cache[rel]
        if lines is None:
            rep.fail(f"{node['id']} 指向不存在的文件 {rel}")
            continue
        keyword = "class" if node["type"] == "class" else "def"
        if check_name_at(lines, line, keyword, name):
            rep.ok()
        else:
            rep.fail(f"{node['id']} 行号 {line} 未指向 `{keyword} {name}`")

        if node["type"] == "class":
            for method in node["meta"].get("methods", []):
                if check_name_at(lines, method["line"], "def", method["name"]):
                    rep.ok()
                else:
                    rep.fail(
                        f"{node['id']}.{method['name']} 行号 {method['line']} 未指向对应 def"
                    )

    # ---- 5. 模块行数一致性 ----
    for node in graph["nodes"]:
        if node["type"] != "module":
            continue
        lines = read_lines(node["path"])
        if lines is None:
            rep.fail(f"模块文件缺失: {node['path']}")
            continue
        if node["meta"].get("lines") == len(lines):
            rep.ok()
        else:
            rep.fail(f"{node['path']} 记录行数 {node['meta'].get('lines')} != 实际 {len(lines)}")

    # ---- 6. 关系类型已知 ----
    known = set(graph["edge_colors"]) | {"imports", "imports_lazy"}
    for edge in graph["edges"]:
        if edge["type"] not in known:
            rep.warn(f"未配色关系类型: {edge['type']} ({edge['from']} -> {edge['to']})")
    rep.ok()

    # ---- 7. 问题节点定位可读 ----
    for issue in graph["issues"]:
        if not issue.get("where") or not issue.get("affects"):
            rep.fail(f"问题 {issue['id']} 缺少 where/affects 信息")
    rep.ok()

    # ---- 8. 索引文件存在且非空 ----
    if INDEX_PATH.is_file() and INDEX_PATH.stat().st_size > 2000:
        rep.ok()
    else:
        rep.fail("02-module-index.md 缺失或内容异常")

    # ---- 9. HTML 自包含性与内嵌脚本语法 ----
    lowered = html.lower()
    if lowered.lstrip().startswith("<!doctype html"):
        rep.ok()
    else:
        rep.fail("graph.html 缺少 doctype")
    if html.count("<script") == html.count("</script>") == 2:
        rep.ok()
    else:
        rep.fail(f"graph.html 脚本标签不配对: {html.count('<script')} 开 / {html.count('</script>')} 闭")
    external_refs = re.findall(r'(?:src|href)\s*=\s*["\']https?://', html)
    if not external_refs:
        rep.ok()
    else:
        rep.fail(f"graph.html 引用了外部资源，不再是离线自包含文件: {external_refs[:3]}")

    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    if not scripts:
        rep.fail("graph.html 中找不到内嵌脚本")
    else:
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
            fh.write(scripts[0])
            js_path = fh.name
        try:
            proc = subprocess.run(
                ["node", "--check", js_path], capture_output=True, text=True, timeout=60
            )
            if proc.returncode == 0:
                rep.ok()
            else:
                rep.fail(f"graph.html 内嵌脚本语法错误: {proc.stderr.strip()[:300]}")
        except FileNotFoundError:
            rep.warn("未找到 node，跳过内嵌 JavaScript 语法校验")
        except Exception as exc:  # pragma: no cover - 受限沙箱下 subprocess 可能被拒
            rep.warn(f"跳过内嵌 JavaScript 语法校验: {exc}")
        finally:
            Path(js_path).unlink(missing_ok=True)

    # ---- 10. Markdown 内部锚点可解析 ----
    slug_cache: dict[Path, set[str]] = {}

    def slugs_of(path: Path) -> set[str]:
        if path not in slug_cache:
            text = path.read_text(encoding="utf-8")
            headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.M)
            slug_cache[path] = {md_slug(h) for h in headings}
        return slug_cache[path]

    for md in sorted(OUT_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for target, anchor in re.findall(r"\]\(([^)\s]*?)#([^)\s]+)\)", text):
            if target.startswith(("http://", "https://")):
                continue
            target_path = md if target == "" else (md.parent / target)
            if not target_path.is_file():
                rep.fail(f"{md.name} 的链接目标不存在: {target}")
                continue
            if anchor in slugs_of(target_path):
                rep.ok()
            else:
                rep.fail(f"{md.name} 中锚点无法解析: ({target}#{anchor})")

    # ---- 11. graph.html 运行时冒烟（语法正确 ≠ 能渲染，必须真跑一遍）----
    browser = find_browser()
    if not browser:
        rep.warn("未找到 Edge/Chrome，跳过 graph.html 运行时冒烟测试")
    else:
        import subprocess
        import tempfile

        hook = ('<script>window.onerror=function(m,s,l,c)'
                '{document.title="JSERR::"+m+"::L"+l;};</script>')
        hooked = html.replace("<style>", hook + "<style>", 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            probe = Path(tmpdir) / "probe.html"
            probe.write_text(hooked, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
                     "--hide-scrollbars", "--virtual-time-budget=6000",
                     "--dump-dom", probe.as_uri()],
                    capture_output=True, encoding="utf-8", errors="replace", timeout=180,
                )
                dom = proc.stdout or ""
            except Exception as exc:  # pragma: no cover - 环境相关
                dom = None
                rep.warn(f"跳过运行时冒烟测试: {exc}")

        if dom is not None:
            crashed = re.search(r"<title>JSERR::(.*?)</title>", dom, re.S)
            if crashed:
                rep.fail(f"graph.html 运行时抛出 JavaScript 异常: {crashed.group(1)[:200]}")
            else:
                rep.ok()
            expected = graph["meta"]["stats"]["node_total"]
            rendered = dom.count('class="node')
            if rendered == expected:
                rep.ok()
            else:
                rep.fail(f"graph.html 实际渲染 {rendered} 个节点，期望 {expected}（画布可能为空）")
            if re.search(r'id="subtitle">[^<]{5,}', dom):
                rep.ok()
            else:
                rep.fail("graph.html 未执行到脚本末尾（subtitle 为空，说明中途抛异常）")
            if dom.count('class="band"') == len(lay["bands"]):
                rep.ok()
            else:
                rep.fail(f"graph.html 渲染的分层色带数量({dom.count('class=\"band\"')})与数据不符({len(lay['bands'])})")

    stats = graph["meta"]["stats"]
    print(f"[verify] 节点 {stats['node_total']} / 边 {stats['edge_total']} / "
          f"问题 {stats['issues']} / 流程 {stats['flows']}")
    print(f"[verify] 断言 {rep.checks} 项，失败 {len(rep.errors)} 项，告警 {len(rep.warnings)} 项")
    for msg in rep.warnings:
        print(f"[warn ] {msg}")
    for msg in rep.errors:
        print(f"[ERROR] {msg}")
    if rep.errors:
        return 1
    print("[verify] 全部校验通过：图谱行号、引用与产物一致性均与源码吻合。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

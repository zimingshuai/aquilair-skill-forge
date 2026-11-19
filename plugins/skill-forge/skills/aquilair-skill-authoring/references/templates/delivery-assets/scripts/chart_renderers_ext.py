"""SVG 图元渲染层（构成与达成图型 + 全图型注册表）：donut/stacked/heatmap/progress 与 RENDERERS。

主要 Input：单张图规格 dict（供各 svg_* 渲染函数）；规格结构见
           render_dashboard.py 文件头 SPEC 说明。
主要 Output：内联 <svg> 片段字符串；RENDERERS 图型名 → 渲染函数注册表。
"""

import json
import math
import sys
from pathlib import Path

from chart_renderers import (
    FAINT,
    FONT,
    GRID,
    INK,
    SERIES_COLORS,
    SUB,
    TONE_COLORS,
    esc,
    fmt,
    nice_max,
    svg_bar,
    svg_hbar,
    svg_line,
    truncate,
)
from chart_renderers_adv import (
    svg_dual,
    svg_gantt,
    svg_radar,
    svg_scatter,
)


# ===========一、构成与达成图型渲染==========
def svg_donut(chart, width=660) -> str:
    """环形占比图（整体=100%），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：items=[{label, value, color?}]，color 缺省按系列色循环。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；items 为空时返回空串。
    """
    items = chart.get("items", [])
    if not items:
        return ""
    total = sum(abs(float(i.get("value", 0))) for i in items) or 1
    size = 200
    cx = cy = size / 2
    # 环形外半径与内半径（px）
    outer, inner = 84, 52
    height = max(size + 24, 40 + 26 * len(items))
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    angle = -math.pi / 2
    for idx, item in enumerate(items):
        value = abs(float(item.get("value", 0)))
        sweep = 2 * math.pi * value / total
        end = angle + sweep
        large = 1 if sweep > math.pi else 0
        x1, y1 = cx + outer * math.cos(angle), cy + outer * math.sin(angle)
        x2, y2 = cx + outer * math.cos(end), cy + outer * math.sin(end)
        x3, y3 = cx + inner * math.cos(end), cy + inner * math.sin(end)
        x4, y4 = cx + inner * math.cos(angle), cy + inner * math.sin(angle)
        color = item.get("color") or SERIES_COLORS[idx % len(SERIES_COLORS)]
        path = (f"M{x1:.2f} {y1:.2f}A{outer} {outer} 0 {large} 1 {x2:.2f} {y2:.2f}"
                f"L{x3:.2f} {y3:.2f}A{inner} {inner} 0 {large} 0 {x4:.2f} {y4:.2f}Z")
        out.append(f'<path d="{path}" fill="{color}"/>')
        angle = end
    out.append(f'<text x="{cx}" y="{cy - 4}" font-size="15" font-weight="600" fill="{INK}" '
               f'text-anchor="middle">{fmt(total)}</text>')
    out.append(f'<text x="{cx}" y="{cy + 14}" font-size="10.5" fill="{FAINT}" '
               f'text-anchor="middle">合计</text>')
    lx = size + 24
    for idx, item in enumerate(items):
        ly = 18 + idx * 26
        color = item.get("color") or SERIES_COLORS[idx % len(SERIES_COLORS)]
        pct = abs(float(item.get("value", 0))) / total * 100
        out.append(f'<rect x="{lx}" y="{ly - 8}" width="10" height="10" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx + 16}" y="{ly}" font-size="11.5" fill="{INK}">'
                   f'{esc(truncate(item.get("label", ""), 10))}</text>')
        out.append(f'<text x="{lx + 200}" y="{ly}" font-size="11.5" fill="{SUB}" '
                   f'text-anchor="end">{fmt(item.get("value", 0))}（{pct:.0f}%）</text>')
    out.append("</svg>")
    return "".join(out)


def svg_stacked(chart, width=660) -> str:
    """堆叠柱状图（构成拆解：风险等级构成、缺口来源构成），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：categories 分类；series=[{name, values, color?}]；
            unit 单位（可选）；height 画布高度（可选，默认 250）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；categories 或 series 为空时返回空串。
    """
    cats = chart.get("categories", [])
    series = chart.get("series", [])
    if not cats or not series:
        return ""
    # totals：各分类逐系列求和后的合计（用于刻度上限与柱底合计标注）
    totals = [
        sum(float(s.get("values", [])[i] or 0) for s in series if i < len(s.get("values", [])))
        for i in range(len(cats))
    ]
    top = nice_max(totals)
    left, right, pad_top, pad_bottom = 52, 14, 26, 62
    height = chart.get("height", 250)
    plot_w = width - left - right
    plot_h = height - pad_top - pad_bottom
    group_w = plot_w / len(cats)
    bar_w = min(46.0, group_w * 0.56)
    unit = chart.get("unit", "")

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for i in range(5):
        value = top * i / 4
        y = pad_top + plot_h - plot_h * i / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y:.1f}" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    for ci, cat in enumerate(cats):
        cx = left + group_w * (ci + 0.5)
        base = pad_top + plot_h
        for si, s in enumerate(series):
            values = s.get("values", [])
            if ci >= len(values):
                continue
            value = float(values[ci] or 0)
            seg_h = plot_h * (value / top if top else 0)
            color = s.get("color") or SERIES_COLORS[si % len(SERIES_COLORS)]
            out.append(f'<rect x="{cx - bar_w / 2:.1f}" y="{base - seg_h:.1f}" '
                       f'width="{bar_w:.1f}" height="{max(seg_h, 0):.1f}" fill="{color}"/>')
            if seg_h > 13:
                out.append(f'<text x="{cx:.1f}" y="{base - seg_h / 2:.1f}" font-size="10" '
                           f'fill="#fff" text-anchor="middle" dominant-baseline="central">'
                           f'{fmt(value)}</text>')
            base -= seg_h
        out.append(f'<text x="{cx:.1f}" y="{pad_top + plot_h + 16:.1f}" font-size="11" '
                   f'fill="{SUB}" text-anchor="middle">{esc(truncate(cat, 9))}</text>')
        out.append(f'<text x="{cx:.1f}" y="{pad_top + plot_h + 30:.1f}" font-size="10" '
                   f'fill="{FAINT}" text-anchor="middle">合计 {fmt(totals[ci])}</text>')
    lx = left
    for si, s in enumerate(series):
        color = s.get("color") or SERIES_COLORS[si % len(SERIES_COLORS)]
        ly = pad_top + plot_h + 48
        name = s.get("name", "")
        out.append(f'<rect x="{lx}" y="{ly - 5}" width="9" height="9" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx + 13}" y="{ly + 3}" font-size="11" fill="{SUB}">'
                   f'{esc(truncate(name, 12))}</text>')
        lx += 22 + len(name) * 11
    if unit:
        out.append(f'<text x="{width - right}" y="16" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="end">单位：{esc(unit)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_heatmap(chart, width=660) -> str:
    """矩阵热力图（跨仓 × 跨 SKU 缺口矩阵），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：rows 行名；cols 列名；values 行 × 列数值矩阵（0 合法，
            画浅灰底 + 「—」）；ramp 配色带，warn（默认，绿→红，越高越差）或
            neutral（浅蓝→深蓝）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；rows/cols/values 任一为空时返回空串。
    """
    rows = chart.get("rows", [])
    cols = chart.get("cols", [])
    matrix = chart.get("values", [])
    if not rows or not cols or not matrix:
        return ""
    # ramp：五级色带（warn=越高越差 / neutral=数值深浅）
    ramp = ["#EAF3DE", "#FAC775", "#EF9F27", "#D85A30", "#A32D2D"] \
        if chart.get("ramp", "warn") == "warn" else ["#E6F1FB", "#B5D4F4", "#85B7EB", "#378ADD", "#185FA5"]
    flat = [float(v or 0) for row in matrix for v in row]
    peak = max(flat) if flat else 1
    label_w, row_h, pad_top = 122, 28, 10
    cell_w = (width - label_w - 12) / len(cols)
    height = pad_top + row_h * (len(rows) + 1) + 8

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for ci, col in enumerate(cols):
        out.append(f'<text x="{label_w + cell_w * (ci + 0.5):.1f}" y="{pad_top + 8}" '
                   f'font-size="10.5" fill="{SUB}" text-anchor="middle">'
                   f'{esc(truncate(col, 7))}</text>')
    for ri, row_name in enumerate(rows):
        y = pad_top + row_h * (ri + 1)
        out.append(f'<text x="{label_w - 10}" y="{y + row_h / 2}" font-size="11" fill="{INK}" '
                   f'text-anchor="end" dominant-baseline="central">'
                   f'{esc(truncate(row_name, 11))}</text>')
        for ci in range(len(cols)):
            value = float(matrix[ri][ci] or 0) if ri < len(matrix) and ci < len(matrix[ri]) else 0
            # level：按峰值五等分的色带档位；value 为 0 时画浅灰空单元格
            level = min(int(value / peak * 5), 4) if peak and value > 0 else 0
            fill = ramp[level] if value > 0 else "#F7F8FA"
            text_fill = "#fff" if value > 0 and level >= 3 else (SUB if value == 0 else INK)
            out.append(f'<rect x="{label_w + cell_w * ci:.1f}" y="{y + 2:.1f}" '
                       f'width="{cell_w - 2:.1f}" height="{row_h - 4}" rx="3" fill="{fill}"/>')
            out.append(f'<text x="{label_w + cell_w * (ci + 0.5):.1f}" y="{y + row_h / 2}" '
                       f'font-size="10.5" fill="{text_fill}" text-anchor="middle" '
                       f'dominant-baseline="central">{fmt(value) if value else "—"}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_progress(chart, width=660) -> str:
    """进度条对比（齐套率 / 达成率类，带目标位刻度），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：items=[{label, value, target?, unit?, tone?}]，
            未显式给 tone 时按「是否已达 target」自动取 ok/warn。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；items 为空时返回空串。
    """
    items = chart.get("items", [])
    if not items:
        return ""
    # ceil：进度条满格上限 = 全部 value 与 target 的最大值（再放大 5%），保证目标刻度不入顶
    ceil = max([float(i.get("value", 0)) for i in items] +
               [float(i.get("target", 0) or 0) for i in items] + [100]) * 1.05
    label_w, track_w, row_h, pad_top = 168, width - 168 - 168, 34, 12
    height = pad_top + row_h * len(items) + 10

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for idx, item in enumerate(items):
        y = pad_top + idx * row_h
        value = float(item.get("value", 0))
        target = item.get("target")
        ratio = min(value / ceil, 1)
        tone = item.get("tone") or ("ok" if not target or value >= float(target) else "warn")
        color = TONE_COLORS.get(tone, "#378ADD")
        out.append(f'<text x="{label_w - 12}" y="{y + row_h / 2}" font-size="11.5" fill="{INK}" '
                   f'text-anchor="end" dominant-baseline="central">'
                   f'{esc(truncate(item.get("label", ""), 13))}</text>')
        out.append(f'<rect x="{label_w}" y="{y + 9}" width="{track_w}" height="14" rx="7" fill="{GRID}"/>')
        out.append(f'<rect x="{label_w}" y="{y + 9}" width="{track_w * ratio:.1f}" height="14" '
                   f'rx="7" fill="{color}"/>')
        if target:
            tx = label_w + track_w * min(float(target) / ceil, 1)
            out.append(f'<line x1="{tx:.1f}" y1="{y + 4}" x2="{tx:.1f}" y2="{y + 28}" '
                       f'stroke="{INK}" stroke-width="1.5" stroke-dasharray="2 2"/>')
        label = f'{fmt(value)}{item.get("unit", "")}'
        if target:
            label += f' / 目标 {fmt(target)}{item.get("unit", "")}'
        out.append(f'<text x="{width - 6}" y="{y + row_h / 2}" font-size="11" fill="{SUB}" '
                   f'text-anchor="end" dominant-baseline="central">{esc(label)}</text>')
    out.append("</svg>")
    return "".join(out)


# ===========二、逃生舱与全图型注册==========
def svg_escape(chart, width=660) -> str:
    """逃生舱：直接嵌入模型手写的 SVG 片段，用于图库覆盖不到的一次性表达。

    Args:
        chart: 单图规格 dict：svg 为模型手写的 <svg> 片段字符串，脚本不解析、原样嵌入。
        width: 预留宽度参数（逃生舱不使用，仅保持与其他渲染器签名一致）。
    Returns:
        原样返回 chart["svg"]；缺失时返回空串。
    """
    return chart.get("svg", "")


# RENDERERS：图型名 → 渲染函数注册表（12 种），render_dashboard.py 按此分发
RENDERERS = {
    "bar": svg_bar,
    "hbar": svg_hbar,
    "line": svg_line,
    "donut": svg_donut,
    "stacked": svg_stacked,
    "heatmap": svg_heatmap,
    "progress": svg_progress,
    "scatter": svg_scatter,
    "dual": svg_dual,
    "radar": svg_radar,
    "gantt": svg_gantt,
    "svg": svg_escape,
}


# ===========三、模块调试入口==========
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # 无参数：列出全部注册图型与实现函数；带规格 JSON 路径：逐图渲染并打印 SVG 字节数
    if len(sys.argv) < 2:
        print(f"====已注册图型====: {len(RENDERERS)} 种")
        for registered_type, render_func in RENDERERS.items():
            # module_name：实现函数所在模块（本文件以脚本运行时模块名为 __main__，还原为文件名）
            module_name = Path(__file__).stem if render_func.__module__ == "__main__" else render_func.__module__
            print(f"  {registered_type} <- {module_name}.{render_func.__name__}")
    else:
        # debug_spec：命令行第 1 个参数指定的规格 JSON
        debug_spec = json.loads(Path(sys.argv[1]).resolve().read_text(encoding="utf-8"))
        print(f"====全图型渲染调试====: {sys.argv[1]}")
        # chart_index/chart：图序号与单图规格
        for chart_index, chart in enumerate(debug_spec.get("charts", [])):
            # chart_type：图型名；未注册图型只提示不渲染（与入口报错口径一致）
            chart_type = chart.get("type", "bar")
            if chart_type not in RENDERERS:
                print(f"[{chart_index}] 图型: {chart_type} ｜ 未注册（入口将报错退出）")
                continue
            # svg_bytes：该图 SVG 片段的 UTF-8 字节数（0 表示数据不足、渲染器返回空串）
            svg_bytes = len(RENDERERS[chart_type](chart).encode("utf-8"))
            print(f"[{chart_index}] 图型: {chart_type} ｜ SVG 字节数: {svg_bytes}")

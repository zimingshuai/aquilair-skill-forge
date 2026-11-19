"""SVG 图元渲染层（高级图型）：散点、双轴、雷达、甘特及配套辅助函数。

主要 Input：单张图规格 dict（供 svg_* 渲染函数）；规格结构见
           render_dashboard.py 文件头 SPEC 说明。
主要 Output：内联 <svg> 片段字符串。
"""

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

from chart_renderers import (
    FAINT,
    FONT,
    GRID,
    INK,
    SERIES_COLORS,
    SUB,
    esc,
    fmt,
    nice_max,
    truncate,
)


# ===========一、散点与双轴图型==========
def axis_divisions(top: float) -> int:
    """选刻度分段数（4/5/6），优先取能整除的，避免出现 12.5 这类小数刻度。

    Args:
        top: 坐标轴刻度上限。
    Returns:
        推荐的分段数；均不能整除时回退为 4。
    """
    for divisions in (4, 5, 6):
        if abs(top / divisions - round(top / divisions)) < 1e-9:
            return divisions
    return 4


def svg_scatter(chart, width=660) -> str:
    """散点图（ABC 分类：周转 vs 库存金额，可按组着色 + 阈值象限线），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：points=[{x, y, label, group}]；groups={组名: 色值}；
            thresholds={x: 值, y: 值}（虚线象限分界，可选）；label_top 标注最靠上的
            点数（默认 6）；show_labels 是否标注（默认 True）；x_label/y_label 轴标题；
            height 画布高度（可选，默认 272）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；points 为空时返回空串。
    """
    points = chart.get("points", [])
    if not points:
        return ""
    groups = chart.get("groups", {}) or {}
    xs = [float(p.get("x", 0)) for p in points]
    ys = [float(p.get("y", 0)) for p in points]
    x_max = nice_max(xs)
    y_max = nice_max(ys)
    # pad_bottom=74：自上而下分三行——X 轴刻度（+16）、图例（height-34）、X 轴标题（height-12），行间距不压字
    left, right, pad_top, pad_bottom = 56, 24, 20, 74
    height = chart.get("height", 272)
    plot_w = width - left - right
    plot_h = height - pad_top - pad_bottom

    def px(value):
        # 数据 x 值 → 画布横坐标（钳制在绘图区内）
        return left + plot_w * min(max(value / x_max, 0), 1) if x_max else left

    def py(value):
        # 数据 y 值 → 画布纵坐标（钳制在绘图区内）
        return pad_top + plot_h - plot_h * min(max(value / y_max, 0), 1) if y_max else pad_top + plot_h

    y_div = axis_divisions(y_max)
    x_div = axis_divisions(x_max)
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for i in range(y_div + 1):
        gy = pad_top + plot_h - plot_h * i / y_div
        out.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{width - right}" y2="{gy:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 8}" y="{gy:.1f}" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(y_max * i / y_div)}</text>')
    for i in range(x_div + 1):
        gx = left + plot_w * i / x_div
        out.append(f'<line x1="{gx:.1f}" y1="{pad_top}" x2="{gx:.1f}" y2="{pad_top + plot_h}" stroke="{GRID}"/>')
        out.append(f'<text x="{gx:.1f}" y="{pad_top + plot_h + 16}" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="middle">{fmt(x_max * i / x_div)}</text>')
    # 阈值线（象限分界：如 ABC 分级周转/金额门槛）
    thresholds = chart.get("thresholds", {}) or {}
    if thresholds.get("x") is not None:
        tx = px(float(thresholds["x"]))
        out.append(f'<line x1="{tx:.1f}" y1="{pad_top}" x2="{tx:.1f}" y2="{pad_top + plot_h}" '
                   f'stroke="{SUB}" stroke-width="1" stroke-dasharray="3 3"/>')
    if thresholds.get("y") is not None:
        ty = py(float(thresholds["y"]))
        out.append(f'<line x1="{left}" y1="{ty:.1f}" x2="{width - right}" y2="{ty:.1f}" '
                   f'stroke="{SUB}" stroke-width="1" stroke-dasharray="3 3"/>')
    # 标签只标最靠上的 N 个点（按 y 降序），避免密集区互相压字
    label_top = int(chart.get("label_top", 6))
    label_set = set()
    if chart.get("show_labels", True):
        ranked = sorted(range(len(points)), key=lambda i: float(points[i].get("y", 0)), reverse=True)
        label_set = set(ranked[:label_top])
    for pi, point in enumerate(points):
        cx, cy = px(float(point.get("x", 0))), py(float(point.get("y", 0)))
        color = groups.get(point.get("group"), None) or SERIES_COLORS[0]
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="{color}" fill-opacity="0.85"/>')
        if pi in label_set and point.get("label"):
            anchor = "end" if cx > width - right - 90 else "start"
            dx = -8 if anchor == "end" else 8
            # 阈值竖线避让：估算标签宽度，bbox 会跨过阈值线时翻转到另一侧（翻转后出左界则维持原侧）
            if thresholds.get("x") is not None:
                label_w = min(len(point["label"]), 12) * 10
                label_x0 = cx + 8 if anchor == "start" else cx - 8 - label_w
                if label_x0 < tx < label_x0 + label_w and not (anchor == "start" and cx - 8 - label_w < left):
                    anchor = "end" if anchor == "start" else "start"
                    dx = -8 if anchor == "end" else 8
            out.append(f'<text x="{cx + dx:.1f}" y="{cy - 8:.1f}" font-size="10" fill="{SUB}" '
                       f'text-anchor="{anchor}">{esc(truncate(point["label"], 12))}</text>')
    # 轴标题
    out.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 12}" font-size="11" fill="{SUB}" '
               f'text-anchor="middle">{esc(chart.get("x_label", ""))}</text>')
    out.append(f'<text x="13" y="{pad_top + plot_h / 2:.1f}" font-size="11" fill="{SUB}" '
               f'text-anchor="middle" transform="rotate(-90 13 {pad_top + plot_h / 2:.1f})">'
               f'{esc(chart.get("y_label", ""))}</text>')
    if groups:
        lx = left
        for name, color in groups.items():
            out.append(f'<circle cx="{lx + 4}" cy="{height - 38}" r="4" fill="{color}"/>')
            out.append(f'<text x="{lx + 13}" y="{height - 34}" font-size="10.5" fill="{SUB}">'
                       f'{esc(truncate(name, 10))}</text>')
            lx += 26 + len(name) * 11
    out.append("</svg>")
    return "".join(out)


def svg_dual(chart, width=660) -> str:
    """双轴图（柱=数量、线=比率，左右两套 Y 轴），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：bars={name, values}；line={name, values}（可省，
            只画柱）；categories 横轴分类；bar_unit / line_unit 图例单位；
            height 画布高度（可选，默认 258）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；categories 或 bars 为空时返回空串。
    """
    cats = chart.get("categories", [])
    bars = chart.get("bars", {}) or {}
    line = chart.get("line", {}) or {}
    if not cats or not bars:
        return ""
    bar_values = [float(v or 0) for v in bars.get("values", [])]
    line_values = [float(v or 0) for v in line.get("values", [])]
    bar_top = nice_max(bar_values)
    line_top = nice_max(line_values) if line_values else 1
    left, right, pad_top, pad_bottom = 54, 56, 26, 54
    height = chart.get("height", 258)
    plot_w = width - left - right
    plot_h = height - pad_top - pad_bottom
    group_w = plot_w / len(cats)
    bar_w = min(40.0, group_w * 0.5)

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for i in range(5):
        gy = pad_top + plot_h - plot_h * i / 4
        out.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{width - right}" y2="{gy:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 8}" y="{gy:.1f}" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(bar_top * i / 4)}</text>')
        if line_values:
            out.append(f'<text x="{width - right + 8}" y="{gy:.1f}" font-size="10.5" fill="{FAINT}" '
                       f'dominant-baseline="central">{fmt(line_top * i / 4)}</text>')
    for ci, cat in enumerate(cats):
        if ci >= len(bar_values):
            continue
        value = bar_values[ci]
        bar_h = plot_h * (value / bar_top if bar_top else 0)
        x = left + group_w * (ci + 0.5) - bar_w / 2
        bar_y = pad_top + plot_h - bar_h
        out.append(f'<rect x="{x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" '
                   f'height="{max(bar_h, 1):.1f}" rx="2" fill="#378ADD" fill-opacity="0.85"/>')
        # 柱够高时数值写进柱内顶部，避免与折线交叉压字
        if bar_h > 30:
            out.append(f'<text x="{x + bar_w / 2:.1f}" y="{bar_y + 12:.1f}" '
                       f'font-size="10" fill="#fff" text-anchor="middle">{fmt(value)}</text>')
        else:
            out.append(f'<text x="{x + bar_w / 2:.1f}" y="{bar_y - 6:.1f}" '
                       f'font-size="10" fill="{SUB}" text-anchor="middle">{fmt(value)}</text>')
        out.append(f'<text x="{left + group_w * (ci + 0.5):.1f}" y="{pad_top + plot_h + 16:.1f}" '
                   f'font-size="11" fill="{SUB}" text-anchor="middle">{esc(truncate(cat, 9))}</text>')
    if line_values:
        pts = []
        for ci, value in enumerate(line_values[:len(cats)]):
            cx = left + group_w * (ci + 0.5)
            cy = pad_top + plot_h - plot_h * (value / line_top if line_top else 0)
            pts.append(f"{cx:.1f},{cy:.1f}")
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#fff" '
                       f'stroke="#EF9F27" stroke-width="2"/>')
            out.append(f'<text x="{cx:.1f}" y="{cy - 9:.1f}" font-size="10" fill="#854F0B" '
                       f'text-anchor="middle">{fmt(value)}</text>')
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#EF9F27" '
                   f'stroke-width="2" stroke-linejoin="round"/>')
    # 图例与单位
    lx = left
    ly = pad_top + plot_h + 38
    out.append(f'<rect x="{lx}" y="{ly - 6}" width="9" height="9" rx="2" fill="#378ADD"/>')
    out.append(f'<text x="{lx + 13}" y="{ly + 2}" font-size="11" fill="{SUB}">'
               f'{esc(bars.get("name", ""))}（{esc(chart.get("bar_unit", ""))}）</text>')
    if line_values:
        lx += 34 + len(bars.get("name", "")) * 11
        out.append(f'<line x1="{lx}" y1="{ly - 1}" x2="{lx + 14}" y2="{ly - 1}" stroke="#EF9F27" stroke-width="2"/>')
        out.append(f'<text x="{lx + 20}" y="{ly + 2}" font-size="11" fill="{SUB}">'
                   f'{esc(line.get("name", ""))}（{esc(chart.get("line_unit", ""))}）</text>')
    out.append("</svg>")
    return "".join(out)


# ===========二、雷达与甘特图型==========
def svg_radar(chart, width=660) -> str:
    """雷达图（方案多维度对比，叠多边形），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：axes=["成本","时效",...]（至少 3 维）；
            series=[{name, values, color?}]；max 满分（默认 100）；
            height 画布高度（可选，默认 306）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；axes 少于 3 维或 series 为空时返回空串。
    """
    axes = chart.get("axes", [])
    series = chart.get("series", [])
    if len(axes) < 3 or not series:
        return ""
    top = float(chart.get("max") or 100)
    height = chart.get("height", 306)
    cx = width / 2 - 30
    cy = height / 2 + 4
    radius = min(width * 0.26, height * 0.35)
    count = len(axes)
    # angles：各维度的辐射角（从正上方起顺时针均分一圈）
    angles = [-math.pi / 2 + 2 * math.pi * i / count for i in range(count)]

    def vertex(idx, ratio):
        # 按维度序号与半径比例计算顶点坐标
        return (cx + radius * ratio * math.cos(angles[idx]),
                cy + radius * ratio * math.sin(angles[idx]))

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    # 同心网格
    for ring in (0.25, 0.5, 0.75, 1.0):
        path = " ".join(f"{vertex(i, ring)[0]:.1f},{vertex(i, ring)[1]:.1f}" for i in range(count))
        out.append(f'<polygon points="{path}" fill="none" stroke="{GRID}" stroke-width="1"/>')
    for idx in range(count):
        ex, ey = vertex(idx, 1.0)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{GRID}"/>')
        lx, ly = vertex(idx, 1.18)
        cos_v = math.cos(angles[idx])
        anchor = "middle" if abs(cos_v) < 0.25 else ("start" if cos_v > 0 else "end")
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10.5" fill="{SUB}" '
                   f'text-anchor="{anchor}" dominant-baseline="central">{esc(truncate(axes[idx], 6))}</text>')
    # 系列多边形
    for si, item in enumerate(series):
        values = [float(v or 0) for v in item.get("values", [])]
        if len(values) < count:
            continue
        color = item.get("color") or SERIES_COLORS[si % len(SERIES_COLORS)]
        pts = []
        for idx in range(count):
            ratio = min(max(values[idx] / top, 0), 1) if top else 0
            vx, vy = vertex(idx, ratio)
            pts.append(f"{vx:.1f},{vy:.1f}")
        out.append(f'<polygon points="{" ".join(pts)}" fill="{color}" fill-opacity="0.16" '
                   f'stroke="{color}" stroke-width="2"/>')
        for point in pts:
            px_, py_ = point.split(",")
            out.append(f'<circle cx="{px_}" cy="{py_}" r="2.6" fill="{color}"/>')
    # 图例（右侧竖排）
    lx = width - 168
    for si, item in enumerate(series):
        ly = 30 + si * 24
        color = item.get("color") or SERIES_COLORS[si % len(SERIES_COLORS)]
        out.append(f'<rect x="{lx}" y="{ly - 6}" width="9" height="9" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx + 14}" y="{ly + 2}" font-size="11" fill="{SUB}">'
                   f'{esc(truncate(item.get("name", ""), 10))}</text>')
    out.append("</svg>")
    return "".join(out)


def _parse_day(text):
    """解析日期字符串，兼容 2026-11-04 / 11-04 / 2026/11/04 / 11/04。"""
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%m-%d", "%Y/%m/%d", "%m/%d"):
        try:
            return datetime.strptime(str(text), pattern)
        except ValueError:
            continue
    return None


def svg_gantt(chart, width=660) -> str:
    """甘特/时间轴（采购到货跟踪、上市事项排期），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：rows=[{label, start, end, status, note?}]，
            status 取 done/doing/risk/todo；today 今日竖线（可选）；
            axis_label 轴标题（可选）；行日期无法解析时跳过该行。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；rows 为空或日期全部无法解析时返回空串。
    """
    rows = chart.get("rows", [])
    if not rows:
        return ""
    # parsed：日期解析成功的行 (原始行, 起始日, 结束日)
    parsed = []
    for row in rows:
        start, end = _parse_day(row.get("start")), _parse_day(row.get("end"))
        if not start or not end:
            continue
        parsed.append((row, start, end))
    if not parsed:
        return ""
    t0 = min(p[1] for p in parsed)
    t1 = max(p[2] for p in parsed)
    if t1 <= t0:
        t1 = t0 + timedelta(days=1)
    span = (t1 - t0).total_seconds()
    left, right, pad_top, row_h = 140, 26, 34, 30
    height = pad_top + row_h * len(parsed) + 22
    # status_colors：状态 → 甘特条颜色（完成/进行中/风险/待办）
    status_colors = {"done": "#1D9E75", "doing": "#EF9F27", "risk": "#E24B4A", "todo": "#888780"}

    def px(moment):
        # 时刻 → 画布横坐标（按时间轴起点与总跨度线性映射）
        return left + (width - left - right) * ((moment - t0).total_seconds() / span)

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for i in range(5):
        tick = t0 + timedelta(seconds=span * i / 4)
        tx = px(tick)
        out.append(f'<line x1="{tx:.1f}" y1="{pad_top - 8}" x2="{tx:.1f}" '
                   f'y2="{pad_top + row_h * len(parsed)}" stroke="{GRID}"/>')
        out.append(f'<text x="{tx:.1f}" y="{pad_top - 14}" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="middle">{tick.strftime("%m/%d")}</text>')
    for idx, (row, start, end) in enumerate(parsed):
        y = pad_top + idx * row_h
        color = status_colors.get(row.get("status", ""), "#378ADD")
        out.append(f'<text x="{left - 12}" y="{y + row_h / 2 - 2}" font-size="11" fill="{INK}" '
                   f'text-anchor="end" dominant-baseline="central">'
                   f'{esc(truncate(row.get("label", ""), 13))}</text>')
        bx, bw = px(start), max(px(end) - px(start), 5)
        out.append(f'<rect x="{bx:.1f}" y="{y + 6}" width="{bw:.1f}" height="{row_h - 10}" '
                   f'rx="4" fill="{color}" fill-opacity="0.9"/>')
        note = row.get("note", "")
        if note:
            nx = bx + bw + 8
            if nx + len(note) * 11 > width - right - 10:
                out.append(f'<text x="{bx + bw - 8:.1f}" y="{y + row_h / 2 - 1:.1f}" font-size="10" '
                           f'fill="#fff" text-anchor="end" dominant-baseline="central">{esc(note)}</text>')
            else:
                out.append(f'<text x="{nx:.1f}" y="{y + row_h / 2 - 1:.1f}" font-size="10" '
                           f'fill="{SUB}" dominant-baseline="central">{esc(note)}</text>')
    today = _parse_day(chart.get("today"))
    if today and t0 <= today <= t1:
        tx = px(today)
        out.append(f'<line x1="{tx:.1f}" y1="{pad_top - 6}" x2="{tx:.1f}" '
                   f'y2="{pad_top + row_h * len(parsed)}" stroke="#E24B4A" stroke-width="1.5" '
                   f'stroke-dasharray="4 3"/>')
        out.append(f'<text x="{tx:.1f}" y="{height - 6}" font-size="10" fill="#A32D2D" '
                   f'text-anchor="middle">今日</text>')
    out.append("</svg>")
    return "".join(out)


# ===========三、模块调试入口==========
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # 延迟导入：注册表所在模块反向依赖本模块，置顶导入会形成循环
    from chart_renderers_ext import RENDERERS

    # adv_types：本模块实现的高级图型（散点/双轴/雷达/甘特）
    adv_types = ("scatter", "dual", "radar", "gantt")
    if len(sys.argv) < 2:
        print(f"====本模块高级图型====: {' / '.join(adv_types)}（规格写法见 render_dashboard.py 文件头）")
    else:
        # debug_spec：命令行第 1 个参数指定的规格 JSON
        debug_spec = json.loads(Path(sys.argv[1]).resolve().read_text(encoding="utf-8"))
        print(f"====高级图型渲染调试====: {sys.argv[1]}")
        # chart_index/chart：图序号与单图规格
        for chart_index, chart in enumerate(debug_spec.get("charts", [])):
            chart_type = chart.get("type", "bar")
            if chart_type not in adv_types:
                continue
            # svg_bytes：该图 SVG 片段的 UTF-8 字节数（0 表示数据不足、渲染器返回空串）
            svg_bytes = len(RENDERERS[chart_type](chart).encode("utf-8"))
            print(f"[{chart_index}] 图型: {chart_type} ｜ SVG 字节数: {svg_bytes}")

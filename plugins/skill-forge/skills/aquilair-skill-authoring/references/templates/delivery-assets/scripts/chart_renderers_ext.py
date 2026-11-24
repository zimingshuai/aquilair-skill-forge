"""SVG 图元渲染层（构成/树状/瀑布图型 + 全图型注册表）：
donut/stacked/heatmap/progress/tree/waterfall 与 RENDERERS。

主要 Input：单张图规格 dict（供各 svg_* 渲染函数）；规格结构见
           render_dashboard.py 文件头 SPEC 说明。
主要 Output：内联 <svg> 片段字符串；RENDERERS 图型名 → 渲染函数注册表。
"""

import json
import math
import re
import sys
from pathlib import Path

from chart_renderers import (
    CARD_BG,
    FAINT,
    GRID,
    INK,
    SERIES_COLORS,
    SUB,
    TONE_COLORS,
    boxes_intersect,
    display_width,
    esc,
    fmt,
    label_box,
    nice_max,
    svg_bar,
    svg_hbar,
    svg_line,
    svg_open,
    to_number,
    truncate,
)
from chart_renderers_adv import (
    svg_dual,
    svg_gantt,
    svg_radar,
    svg_scatter,
)


# ===========一、图型常量==========
# TREE_MAX_NODES：树状图节点数上限（超限中文报错，提示拆图或汇总）
TREE_MAX_NODES = 30
# TREE_MAX_DEPTH：树状图层深上限（层数，根层计 1）
TREE_MAX_DEPTH = 5
# TREE_CANVAS_W：树状图画布宽（px）
TREE_CANVAS_W = 660
# TREE_SIDE_PAD：树状图左右留白（px），可用宽 = 画布宽 − 2×该值
TREE_SIDE_PAD = 20
# TREE_AVAIL_W：树状图可用横向宽度（px，660 − 2×20）
TREE_AVAIL_W = 620
# TREE_SIBLING_GAP：同层相邻子树之间的横向间距（px）
TREE_SIBLING_GAP = 16
# TREE_PAD_TOP：根层节点框顶留白（px）
TREE_PAD_TOP = 20
# TREE_LEVEL_H：相邻层节点框顶的纵向间距（px）
TREE_LEVEL_H = 82
# TREE_BOX_H：节点框高度（px）
TREE_BOX_H = 34
# TREE_BOX_MIN_W / TREE_BOX_MAX_W：节点框宽下限 / 上限（px）
TREE_BOX_MIN_W = 74
TREE_BOX_MAX_W = 160
# TREE_BOX_PAD_W：节点框宽估算时标签两侧的余量（px）
TREE_BOX_PAD_W = 24
# TREE_TEXT_W：标签单字符显示宽（px，与 label_box 的 6.5 口径一致）
TREE_TEXT_W = 6.5
# TREE_BOTTOM_PAD：末层节点框底到画布底的留白（px）
TREE_BOTTOM_PAD = 10
# TREE_H_BOX_MIN_W / TREE_H_BOX_MAX_W：横向布局节点框宽上下限（px，按标签自适应）
TREE_H_BOX_MIN_W = 120
TREE_H_BOX_MAX_W = 180
# TREE_H_BOX_COMPRESS_MIN_W：横向布局超宽压缩后的框宽下限（px，仍超则报错）
TREE_H_BOX_COMPRESS_MIN_W = 110
# TREE_H_COL_GAP：横向布局层间列距（px，父框右边 → 子框左边）
TREE_H_COL_GAP = 40
# TREE_H_ROW_GAP：横向布局同层节点的纵向间距（px）
TREE_H_ROW_GAP = 10
# TREE_H_ROW_H：横向布局单节点纵向占高（框高 + 同层间距，px）
TREE_H_ROW_H = TREE_BOX_H + TREE_H_ROW_GAP
# TREE_H_TEXT_PAD：横向布局标签文本两侧预留（px，用于按显示宽度截断）
TREE_H_TEXT_PAD = 10
# TREE_HORIZONTAL_MAX_H：横向布局画布高上限（px，超过视为过高，提示拆图或汇总）
TREE_HORIZONTAL_MAX_H = 620
# TREE_LABEL_FIT_TOLERANCE：竖直布局压缩后框宽允许小于标签所需宽度的容差（px）；
# 压缩后框宽低于「标签所需宽度 − 容差」视为标签不可读，自动切换横向布局
TREE_LABEL_FIT_TOLERANCE = 8
# TREE_ROOT_BG：根节点框浅蓝底色
TREE_ROOT_BG = "#E6F1FB"
# TREE_LINE：树节点框描边与连线颜色（框 0.5px / 连线 1px）
TREE_LINE = "#D6D9DE"
# WATERFALL_UP：瀑布图正向增减柱色（绿）
WATERFALL_UP = "#1D9E75"
# WATERFALL_DOWN：瀑布图负向增减柱色（红）
WATERFALL_DOWN = "#E24B4A"
# WATERFALL_HEIGHT：瀑布图默认画布高（px）
WATERFALL_HEIGHT = 250


# ===========二、构成与达成图型渲染==========
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
    total = sum(abs(to_number(i.get("value", 0))) for i in items) or 1
    # 组宽：环形 200 + 间距 24 + 图例 210；整组水平居中，避免右侧留白过大
    size, gap, legend_w = 200, 24, 210
    group_w = size + gap + legend_w
    offset = (width - group_w) / 2
    cx = offset + size / 2
    cy = size / 2
    # 环形外半径与内半径（px）
    outer, inner = 84, 52
    height = max(size + 24, 40 + 26 * len(items))
    out = [svg_open(chart, width, height)]
    angle = -math.pi / 2
    for idx, item in enumerate(items):
        value = abs(to_number(item.get("value", 0)))
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
    out.append(f'<text x="{cx}" y="{cy - 4}" font-size="15" font-weight="500" fill="{INK}" '
               f'text-anchor="middle">{fmt(total)}</text>')
    out.append(f'<text x="{cx}" y="{cy + 14}" font-size="11" fill="{FAINT}" '
               f'text-anchor="middle">合计</text>')
    lx = offset + size + gap
    # legend_right：图例数值列右对齐到组右边界
    legend_right = offset + group_w
    for idx, item in enumerate(items):
        ly = 18 + idx * 26
        color = item.get("color") or SERIES_COLORS[idx % len(SERIES_COLORS)]
        pct = abs(to_number(item.get("value", 0))) / total * 100
        out.append(f'<rect x="{lx}" y="{ly - 8}" width="10" height="10" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx + 16}" y="{ly}" font-size="11.5" fill="{INK}">'
                   f'{esc(truncate(item.get("label", ""), 10))}</text>')
        out.append(f'<text x="{legend_right}" y="{ly}" font-size="11.5" fill="{SUB}" '
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
        sum(to_number(s.get("values", [])[i]) for s in series if i < len(s.get("values", [])))
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

    out = [svg_open(chart, width, height)]
    for i in range(5):
        value = top * i / 4
        y = pad_top + plot_h - plot_h * i / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y:.1f}" font-size="11" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    for ci, cat in enumerate(cats):
        cx = left + group_w * (ci + 0.5)
        base = pad_top + plot_h
        for si, s in enumerate(series):
            values = s.get("values", [])
            if ci >= len(values):
                continue
            value = to_number(values[ci])
            seg_h = plot_h * (value / top if top else 0)
            color = s.get("color") or SERIES_COLORS[si % len(SERIES_COLORS)]
            out.append(f'<rect x="{cx - bar_w / 2:.1f}" y="{base - seg_h:.1f}" '
                       f'width="{bar_w:.1f}" height="{max(seg_h, 0):.1f}" fill="{color}"/>')
            if seg_h > 13:
                out.append(f'<text x="{cx:.1f}" y="{base - seg_h / 2:.1f}" font-size="11" '
                           f'fill="#fff" text-anchor="middle" dominant-baseline="central">'
                           f'{fmt(value)}</text>')
            base -= seg_h
        out.append(f'<text x="{cx:.1f}" y="{pad_top + plot_h + 16:.1f}" font-size="11" '
                   f'fill="{SUB}" text-anchor="middle">{esc(truncate(cat, 9))}</text>')
        out.append(f'<text x="{cx:.1f}" y="{pad_top + plot_h + 30:.1f}" font-size="11" '
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
        out.append(f'<text x="{width - right}" y="16" font-size="11" fill="{FAINT}" '
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
    flat = [to_number(v) for row in matrix for v in row]
    peak = max(flat) if flat else 1
    label_w, row_h, pad_top = 122, 28, 10
    cell_w = (width - label_w - 12) / len(cols)
    height = pad_top + row_h * (len(rows) + 1) + 8

    out = [svg_open(chart, width, height)]
    for ci, col in enumerate(cols):
        out.append(f'<text x="{label_w + cell_w * (ci + 0.5):.1f}" y="{pad_top + 8}" '
                   f'font-size="11" fill="{SUB}" text-anchor="middle">'
                   f'{esc(truncate(col, 7))}</text>')
    for ri, row_name in enumerate(rows):
        y = pad_top + row_h * (ri + 1)
        out.append(f'<text x="{label_w - 10}" y="{y + row_h / 2}" font-size="11" fill="{INK}" '
                   f'text-anchor="end" dominant-baseline="central">'
                   f'{esc(truncate(row_name, 11))}</text>')
        for ci in range(len(cols)):
            value = to_number(matrix[ri][ci]) if ri < len(matrix) and ci < len(matrix[ri]) else 0
            # level：按峰值五等分的色带档位；value 为 0 时画浅灰空单元格
            level = min(int(value / peak * 5), 4) if peak and value > 0 else 0
            fill = ramp[level] if value > 0 else "#F7F8FA"
            text_fill = "#fff" if value > 0 and level >= 3 else (SUB if value == 0 else INK)
            out.append(f'<rect x="{label_w + cell_w * ci:.1f}" y="{y + 2:.1f}" '
                       f'width="{cell_w - 2:.1f}" height="{row_h - 4}" rx="3" fill="{fill}"/>')
            out.append(f'<text x="{label_w + cell_w * (ci + 0.5):.1f}" y="{y + row_h / 2}" '
                       f'font-size="11" fill="{text_fill}" text-anchor="middle" '
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
    ceil = max([to_number(i.get("value", 0)) for i in items] +
               [to_number(i.get("target", 0)) for i in items] + [100]) * 1.05
    label_w, track_w, row_h, pad_top = 168, width - 168 - 168, 34, 12
    height = pad_top + row_h * len(items) + 10

    out = [svg_open(chart, width, height)]
    for idx, item in enumerate(items):
        y = pad_top + idx * row_h
        value = to_number(item.get("value", 0))
        target = item.get("target")
        ratio = min(value / ceil, 1)
        tone = item.get("tone") or ("ok" if not target or value >= to_number(target) else "warn")
        color = TONE_COLORS.get(tone, "#378ADD")
        out.append(f'<text x="{label_w - 12}" y="{y + row_h / 2}" font-size="11.5" fill="{INK}" '
                   f'text-anchor="end" dominant-baseline="central">'
                   f'{esc(truncate(item.get("label", ""), 13))}</text>')
        out.append(f'<rect x="{label_w}" y="{y + 9}" width="{track_w}" height="14" rx="7" fill="{GRID}"/>')
        out.append(f'<rect x="{label_w}" y="{y + 9}" width="{track_w * ratio:.1f}" height="14" '
                   f'rx="7" fill="{color}"/>')
        if target:
            tx = label_w + track_w * min(to_number(target) / ceil, 1)
            out.append(f'<line x1="{tx:.1f}" y1="{y + 4}" x2="{tx:.1f}" y2="{y + 28}" '
                       f'stroke="{INK}" stroke-width="1.5" stroke-dasharray="2 2"/>')
        label = f'{fmt(value)}{item.get("unit", "")}'
        if target:
            label += f' / 目标 {fmt(target)}{item.get("unit", "")}'
        out.append(f'<text x="{width - 6}" y="{y + row_h / 2}" font-size="11" fill="{SUB}" '
                   f'text-anchor="end" dominant-baseline="central">{esc(label)}</text>')
    out.append("</svg>")
    return "".join(out)


# ===========三、树状与瀑布图型==========
class TreeLayoutError(ValueError):
    """树状图压缩到节点框宽下限仍无法排入可用宽时抛出；入口层以退出码 2 终止。"""


def _tree_box_width(label) -> float:
    """按标签显示宽度估算树节点框宽（钳制在上下限之间）。

    Args:
        label: 节点标签文本（内部先按 12 字符截断，保留「（编码）」段）。
    Returns:
        节点框宽度（px）。
    """
    text_width = display_width(truncate(label, 12)) * TREE_TEXT_W + TREE_BOX_PAD_W
    return min(max(text_width, TREE_BOX_MIN_W), TREE_BOX_MAX_W)


def _truncate_to_width(text, max_width) -> str:
    """按显示宽度截断标签，优先保留结尾「（编码）」段。

    Args:
        text: 原标签文本。
        max_width: 文本允许的最大显示宽度（半角字符为 1，全角字符为 2）。
    Returns:
        显示宽度不超过 max_width 的文本；保留编码段时名称以「…」收尾。
    """
    text = str(text)
    if display_width(text) <= max_width:
        return text
    # code_part：结尾「（编码）」段；预算不足时退化为整段逐字符截断
    code_match = re.search(r"（[A-Za-z0-9_-]{1,16}）$", text)
    code_part = code_match.group(0) if code_match else ""
    name_part = text[: len(text) - len(code_part)] if code_part else text
    budget = max_width - 1 - display_width(code_part)
    if budget < 2:
        clipped = ""
        for char in text:
            if display_width(clipped + char) + 1 > max_width:
                break
            clipped += char
        return (clipped + "…") if clipped else "…"
    clipped_name = ""
    for char in name_part:
        if display_width(clipped_name + char) > budget:
            break
        clipped_name += char
    return clipped_name + "…" + code_part


def _measure_tree(sizes, children, gap=TREE_SIBLING_GAP) -> tuple:
    """后序测量每棵子树沿布局轴的外接尺寸、节点框偏移与子节点相对偏移。

    Args:
        sizes: 每个节点沿布局轴的尺寸列表（纵向布局为框宽，横向布局为框高）。
        children: 每个节点的直接子节点序号列表。
        gap: 同层相邻子树之间的间距（px）。
    Returns:
        (extent_sizes, box_offsets, child_offsets)：
            extent_sizes 为子树外接尺寸（叶子=自身尺寸；非叶=子尺寸和+间距，并计入父框居中后的外扩）；
            box_offsets 为节点框相对子树外接起点的偏移；
            child_offsets 为每个节点的直接子节点相对子树外接起点的偏移列表。
    """
    count = len(sizes)
    extent_sizes = [0.0] * count
    box_offsets = [0.0] * count
    child_offsets = [[] for _ in range(count)]

    def measure(index):
        # 已测量过的子树直接复用（父节点后序会重复访问子节点）
        if extent_sizes[index] > 0:
            return
        child_indexes = children[index]
        if not child_indexes:
            extent_sizes[index] = sizes[index]
            return
        #   1. 子子树按外接尺寸依次占位，相邻留 gap
        cursor = 0.0
        offsets = []
        for child in child_indexes:
            measure(child)
            offsets.append(cursor)
            cursor += extent_sizes[child] + gap
        children_end = cursor - gap
        #   2. 父框中心 = 首子框起点与末子框终点的中点
        first_box_start = offsets[0] + box_offsets[child_indexes[0]]
        last_child = child_indexes[-1]
        last_box_end = offsets[-1] + box_offsets[last_child] + sizes[last_child]
        center = (first_box_start + last_box_end) / 2
        parent_start = center - sizes[index] / 2
        parent_end = center + sizes[index] / 2
        #   3. 子树外接尺寸取「子群外接」与「父框居中后的外扩」并集
        lo = min(0.0, parent_start)
        hi = max(children_end, parent_end)
        box_offsets[index] = parent_start - lo
        extent_sizes[index] = hi - lo
        child_offsets[index] = [offset - lo for offset in offsets]

    for index in range(count):
        measure(index)
    return extent_sizes, box_offsets, child_offsets


def _forest_extent(sizes, children, roots, gap=TREE_SIBLING_GAP) -> tuple:
    """测量整片森林（根列表）沿布局轴的外接总尺寸与各子树布局数据。

    Args:
        sizes: 每个节点沿布局轴的尺寸列表。
        children: 每个节点的直接子节点序号列表。
        roots: 根节点序号列表。
        gap: 同层相邻子树之间的间距（px）。
    Returns:
        (森林总尺寸, 子树外接尺寸列表, 节点框偏移列表, 子节点偏移列表)；
        总尺寸含根与根之间的间距。
    """
    extent_sizes, box_offsets, child_offsets = _measure_tree(sizes, children, gap)
    total = sum(extent_sizes[root] for root in roots) + gap * max(len(roots) - 1, 0)
    return total, extent_sizes, box_offsets, child_offsets


def _place_tree(roots, sizes, extent_sizes, box_offsets, child_offsets, children,
                start=TREE_SIDE_PAD, gap=TREE_SIBLING_GAP) -> tuple:
    """前序分配节点框中心坐标与层级（根依次排，子按外接尺寸占位）。

    Args:
        roots: 根节点序号列表。
        sizes: 每个节点沿布局轴的尺寸列表。
        extent_sizes: 每个节点的子树外接尺寸列表。
        box_offsets: 每个节点框相对子树外接起点的偏移列表。
        child_offsets: 每个节点的直接子节点相对偏移列表。
        children: 每个节点的直接子节点序号列表。
        start: 森林起点坐标（px）。
        gap: 同层相邻子树之间的间距（px）。
    Returns:
        (centers, levels)：节点框中心坐标与层级列表（按原始序号）。
    """
    count = len(sizes)
    centers = [0.0] * count
    levels = [0] * count

    def place(index, origin, level):
        levels[index] = level
        centers[index] = origin + box_offsets[index] + sizes[index] / 2
        for child, offset in zip(children[index], child_offsets[index]):
            place(child, origin + offset, level + 1)

    cursor = float(start)
    for root in roots:
        place(root, cursor, 0)
        cursor += extent_sizes[root] + gap
    return centers, levels


def _resolve_tree_forest(nodes) -> tuple:
    """解析 tree 的 id/parent 关系，返回父子序号与根列表。

    Args:
        nodes: 节点规格列表；每项含 id、label、value 与可选 parent。
    Returns:
        (parents, children, roots)：父序号列表（根为 None）、子序号列表、根序号列表。
        父缺失、自指、跨层或成环的引用一律按根处理，保证所有节点都能渲染。
    """
    count = len(nodes)
    # nodes_by_id / index_by_id：节点 id → 节点/原始序号；重复 id 取首次出现
    nodes_by_id = {}
    index_by_id = {}
    for index, node in enumerate(nodes):
        node_id = str(node.get("id", f"node-{index}"))
        nodes_by_id.setdefault(node_id, node)
        index_by_id.setdefault(node_id, index)
    # raw_levels：按父链推导的层级（根 0）；父缺失或 parent 成环的节点按根处理
    raw_levels = [0] * count
    for index, node in enumerate(nodes):
        current_id = str(node.get("id", f"node-{index}"))
        level = 0
        seen = {current_id}
        while True:
            parent_id = nodes_by_id.get(current_id, {}).get("parent")
            if parent_id is None or str(parent_id) == "" or str(parent_id) not in nodes_by_id:
                break
            parent_id = str(parent_id)
            if parent_id in seen:
                level = 0
                break
            seen.add(parent_id)
            level += 1
            current_id = parent_id
        raw_levels[index] = level
    # parents / children：仅连接相邻层级且非自指的父子边；成环/跨层引用一律按根处理
    parents = [None] * count
    children = [[] for _ in range(count)]
    for index, node in enumerate(nodes):
        parent_id = node.get("parent")
        if parent_id is None or str(parent_id) == "":
            continue
        parent_index = index_by_id.get(str(parent_id))
        if (parent_index is None or parent_index == index
                or raw_levels[parent_index] != raw_levels[index] - 1):
            continue
        parents[index] = parent_index
        children[parent_index].append(index)
    roots = [index for index in range(count) if parents[index] is None]
    return parents, children, roots


def build_tree_layout(nodes, available_width=TREE_AVAIL_W) -> dict:
    """按 tidy-tree 简化算法计算树状图布局（后序子树外接宽 → 前序定 x → 超宽等比压缩）。

    Args:
        nodes: 节点规格列表；每项含 id、label、value 与可选 parent。
        available_width: 可用横向宽度（px，默认 620）；总宽超出时等比压缩节点框宽。
    Returns:
        dict：widths（框宽）、centers（框中心横坐标）、levels（层级，根 0）、
            parents / children（父/子序号列表）、level_count（层数）、scale（压缩比例）。
            所有列表均按节点原始序号索引。
    Raises:
        TreeLayoutError: 压缩到节点框宽下限仍超出可用宽时抛出（提示拆图或汇总）。
    """
    count = len(nodes)
    # parents / children / roots：解析 id/parent 关系（父缺失/成环按根处理）
    parents, children, roots = _resolve_tree_forest(nodes)
    #   1. 后序算自然框宽下的森林外接总宽；超出可用宽时等比压缩（下限 TREE_BOX_MIN_W）
    natural_widths = [_tree_box_width(node.get("label", "")) for node in nodes]
    total, extent_widths, box_lefts, child_offsets = _forest_extent(
        natural_widths, children, roots, TREE_SIBLING_GAP)
    scale = 1.0
    if total > available_width:
        # 全部压到下限仍超：中文报错（30 节点/5 层上限由组装入口先行判定）
        min_widths = [float(TREE_BOX_MIN_W)] * count
        min_total, _, _, _ = _forest_extent(
            min_widths, children, roots, TREE_SIBLING_GAP)
        if min_total > available_width:
            raise TreeLayoutError(
                f"节点过多，拆图或汇总（可用宽 {available_width:.0f}px，"
                f"压缩到节点框下限 {TREE_BOX_MIN_W}px 仍超出）"
            )
        # 二分压缩比例：所有节点框宽按同一比例缩小，使森林总宽落入可用区
        low, high = 0.0, 1.0
        for _ in range(40):
            mid = (low + high) / 2
            trial = [max(float(TREE_BOX_MIN_W), box_w * mid) for box_w in natural_widths]
            trial_total, _, _, _ = _forest_extent(
                trial, children, roots, TREE_SIBLING_GAP)
            if trial_total <= available_width:
                low = mid
            else:
                high = mid
        scale = low
        widths = [max(float(TREE_BOX_MIN_W), box_w * scale) for box_w in natural_widths]
        total, extent_widths, box_lefts, child_offsets = _forest_extent(
            widths, children, roots, TREE_SIBLING_GAP)
    else:
        widths = natural_widths
    #   2. 可读性守护：压缩后框宽明显小于标签所需宽度时，竖直布局标签不可读，
    #      交由 build_tree_chart_layout 自动切换横向布局（不静默压字继续渲染）
    if any(width + TREE_LABEL_FIT_TOLERANCE < natural
           for width, natural in zip(widths, natural_widths)):
        raise TreeLayoutError(
            "竖直布局压缩后标签不可读（框宽低于标签所需宽度，需改用 horizontal）"
        )
    #   3. 前序分配 x：根从可用区左边界依次排；父框中心 = 直接子节点群中心
    centers, levels = _place_tree(roots, widths, extent_widths, box_lefts,
                                  child_offsets, children,
                                  TREE_SIDE_PAD, TREE_SIBLING_GAP)
    level_count = max(levels) + 1 if count else 0
    return {
        "direction": "vertical",
        "widths": widths,
        "centers": centers,
        "levels": levels,
        "parents": parents,
        "children": children,
        "level_count": level_count,
        "height": TREE_PAD_TOP + level_count * TREE_LEVEL_H + TREE_BOTTOM_PAD,
        "scale": scale,
    }


def build_tree_horizontal_layout(nodes, canvas_width=TREE_CANVAS_W) -> dict:
    """横向树状布局：每层一列（左→右）、层内纵向堆叠、父框纵向居中于子群。

    Args:
        nodes: 节点规格列表；每项含 id、label、value 与可选 parent。
        canvas_width: 画布宽（px，默认 660）；超宽时压缩统一框宽，下限 110px。
    Returns:
        dict：direction（horizontal）、widths（统一框宽列表）、centers（框纵向中心）、
            x_centers（框横向中心）、levels、parents / children、level_count、
            height（画布高）、box_width（统一框宽）、scale（压缩比例）。
    Raises:
        TreeLayoutError: 框宽压到下限仍超宽，或画布高超过上限时抛出（提示拆图或汇总）。
    """
    count = len(nodes)
    parents, children, roots = _resolve_tree_forest(nodes)
    #   1. 统一框宽：按全树最长标签自适应（clamp 120–180）；超长标签渲染时按显示宽截断
    # label_widths：各节点完整标签的估算框宽（横向框宽较大，优先显示全名）
    label_widths = [
        display_width(node.get("label", "")) * TREE_TEXT_W + TREE_BOX_PAD_W
        for node in nodes
    ]
    natural_width = min(max(max(label_widths, default=TREE_H_BOX_MIN_W),
                            TREE_H_BOX_MIN_W), TREE_H_BOX_MAX_W)
    #   2. 沿纵向测量/放置：节点高固定 34、同层间距 10；层级与框宽无关
    heights = [float(TREE_BOX_H)] * count
    content_height, extent_heights, box_tops, child_offsets = _forest_extent(
        heights, children, roots, TREE_H_ROW_GAP)
    y_centers, levels = _place_tree(roots, heights, extent_heights, box_tops,
                                    child_offsets, children,
                                    TREE_SIDE_PAD, TREE_H_ROW_GAP)
    level_count = max(levels) + 1 if count else 0
    #   3. 画布宽：层数×框宽 +（层数−1）×40 + 左右留白；超宽压缩框宽（下限 110）
    available_width = canvas_width - 2 * TREE_SIDE_PAD
    box_width = natural_width
    content_width = level_count * box_width + (level_count - 1) * TREE_H_COL_GAP
    if content_width > available_width:
        box_width = (available_width - TREE_H_COL_GAP * (level_count - 1)) / level_count
        if box_width < TREE_H_BOX_COMPRESS_MIN_W:
            raise TreeLayoutError(
                f"节点过多，拆图或汇总（横向布局 {level_count} 层，"
                f"压缩到框宽下限 {TREE_H_BOX_COMPRESS_MIN_W}px 仍超出画布宽）"
            )
        content_width = level_count * box_width + (level_count - 1) * TREE_H_COL_GAP
    #   4. 画布高：公式下限（最大层节点数×44+上下留白）与内容外接取较大值
    layer_counts = [0] * level_count
    for level in levels:
        layer_counts[level] += 1
    max_layer = max(layer_counts) if layer_counts else 0
    height = max(max_layer * TREE_H_ROW_H + 2 * TREE_SIDE_PAD,
                 content_height + 2 * TREE_SIDE_PAD)
    if height > TREE_HORIZONTAL_MAX_H:
        raise TreeLayoutError(
            f"节点过多，拆图或汇总（横向布局画布高 {height:.0f}px "
            f"超过上限 {TREE_HORIZONTAL_MAX_H}px）"
        )
    #   5. 每层一列：同层节点共用列左边界，横向中心按层级固定
    x_centers = [
        TREE_SIDE_PAD + level * (box_width + TREE_H_COL_GAP) + box_width / 2
        for level in levels
    ]
    return {
        "direction": "horizontal",
        "widths": [box_width] * count,
        "centers": y_centers,
        "x_centers": x_centers,
        "levels": levels,
        "parents": parents,
        "children": children,
        "level_count": level_count,
        "height": height,
        "box_width": box_width,
        "scale": box_width / natural_width if natural_width else 1.0,
    }


def build_tree_chart_layout(nodes, canvas_width=TREE_CANVAS_W,
                            direction="vertical") -> dict:
    """按 direction 选择树布局；vertical 压到下限仍超宽时自动改用 horizontal。

    Args:
        nodes: 节点规格列表；每项含 id、label、value 与可选 parent。
        canvas_width: 画布宽（px，默认 660）。
        direction: "vertical"（默认，根在上）或 "horizontal"（每层一列）。
    Returns:
        对应布局 dict；direction 字段为实际采用的布局方向。
    Raises:
        TreeLayoutError: vertical 与 horizontal 均无法排布时抛出（提示拆图或汇总）。
    """
    if direction == "horizontal":
        return build_tree_horizontal_layout(nodes, canvas_width)
    try:
        return build_tree_layout(nodes, canvas_width - 2 * TREE_SIDE_PAD)
    except TreeLayoutError as vertical_error:
        # 自动切换：竖直布局压缩到框宽下限仍超宽时改用横向，不报错
        try:
            return build_tree_horizontal_layout(nodes, canvas_width)
        except TreeLayoutError as horizontal_error:
            raise TreeLayoutError(
                "节点过多，拆图或汇总（vertical 与 horizontal 布局均放不下："
                f"{vertical_error}；{horizontal_error}）"
            ) from horizontal_error


def _append_tree_node(out, label_text, value, center_x, center_y, box_w, unit,
                      is_root) -> None:
    """追加一个树节点框与两行文本（标签 + value+unit）。

    Args:
        out: SVG 片段列表（就地追加）。
        label_text: 已按布局规则截断的标签文本。
        value: 节点数值（经 fmt 格式化）。
        center_x: 框中心横坐标（px）。
        center_y: 框中心纵坐标（px）。
        box_w: 框宽（px）。
        unit: 数值单位（可为空串）。
        is_root: 是否根节点（根节点浅蓝底，其余白底）。
    Returns:
        None。
    """
    box_x = center_x - box_w / 2
    box_y = center_y - TREE_BOX_H / 2
    fill = TREE_ROOT_BG if is_root else CARD_BG
    out.append(f'<rect x="{box_x:.1f}" y="{box_y:.1f}" width="{box_w:.1f}" '
               f'height="{TREE_BOX_H}" rx="8" fill="{fill}" stroke="{TREE_LINE}" '
               f'stroke-width="0.5"/>')
    out.append(f'<text x="{center_x:.1f}" y="{box_y + 14:.1f}" font-size="11" fill="{INK}" '
               f'text-anchor="middle">{esc(label_text)}</text>')
    out.append(f'<text x="{center_x:.1f}" y="{box_y + 29:.1f}" font-size="11" fill="{SUB}" '
               f'text-anchor="middle">{esc(fmt(value))}{esc(unit)}</text>')


def svg_tree(chart, width=TREE_CANVAS_W) -> str:
    """树状分层图（BOM/层级结构）：竖直/横向 tidy-tree 布局，父框居中于子节点群。

    Args:
        chart: 单图规格 dict：nodes=[{id, label, value, parent?}]（无 parent 为根，可多根）；
            direction 取 vertical（默认）或 horizontal，vertical 超宽时自动切换横向；
            unit 单位（可选）；note 图注（可选，作为 desc）。
        width: SVG 视口宽度（px，默认 660）。
    Returns:
        <svg> 片段字符串；nodes 为空时返回空串。
    Raises:
        TreeLayoutError: 竖直与横向布局均无法排布时抛出（入口层按中文报错退出）。
    """
    nodes = chart.get("nodes", [])
    if not nodes:
        return ""
    unit = chart.get("unit", "")
    direction = chart.get("direction", "vertical")
    # layout：tidy-tree 布局（vertical 超宽时自动切换 horizontal）
    layout = build_tree_chart_layout(nodes, width, direction)
    chosen_direction = layout["direction"]
    opening = svg_open(chart, width, layout["height"])
    # data-tree-direction：产物标记实际采用的布局方向，供验收与排障识别
    opening = opening.replace(
        ' role="img"', f' role="img" data-tree-direction="{chosen_direction}"', 1)
    out = [opening]
    if chosen_direction == "horizontal":
        # 横向：父框右边中点 → 层间中线 x → 子框左边中点
        box_width = layout["box_width"]
        for parent_index, child_indexes in enumerate(layout["children"]):
            parent_right = layout["x_centers"][parent_index] + box_width / 2
            parent_y = layout["centers"][parent_index]
            for child_index in child_indexes:
                child_left = layout["x_centers"][child_index] - box_width / 2
                child_y = layout["centers"][child_index]
                mid_x = (parent_right + child_left) / 2
                out.append(f'<polyline points="{parent_right:.1f},{parent_y:.1f} '
                           f'{mid_x:.1f},{parent_y:.1f} {mid_x:.1f},{child_y:.1f} '
                           f'{child_left:.1f},{child_y:.1f}" fill="none" '
                           f'stroke="{TREE_LINE}" stroke-width="1"/>')
        for index, node in enumerate(nodes):
            # 横向框宽较大：按显示宽度截断（放得下则显示全名，放不下保留编码段）
            label_text = _truncate_to_width(
                node.get("label", ""), (box_width - TREE_H_TEXT_PAD) / TREE_TEXT_W)
            _append_tree_node(out, label_text, node.get("value", 0),
                              layout["x_centers"][index], layout["centers"][index],
                              box_width, unit, layout["levels"][index] == 0)
    else:
        # 竖直：父框底边中点 → 层间中线 y → 子框顶边中点
        levels = layout["levels"]
        centers = layout["centers"]
        for parent_index, child_indexes in enumerate(layout["children"]):
            parent_bottom = TREE_PAD_TOP + levels[parent_index] * TREE_LEVEL_H + TREE_BOX_H
            for child_index in child_indexes:
                child_top = TREE_PAD_TOP + levels[child_index] * TREE_LEVEL_H
                mid_y = (parent_bottom + child_top) / 2
                out.append(f'<polyline points="{centers[parent_index]:.1f},{parent_bottom:.1f} '
                           f'{centers[parent_index]:.1f},{mid_y:.1f} '
                           f'{centers[child_index]:.1f},{mid_y:.1f} '
                           f'{centers[child_index]:.1f},{child_top:.1f}" fill="none" '
                           f'stroke="{TREE_LINE}" stroke-width="1"/>')
        for index, node in enumerate(nodes):
            center_y = TREE_PAD_TOP + levels[index] * TREE_LEVEL_H + TREE_BOX_H / 2
            _append_tree_node(out, truncate(node.get("label", ""), 12),
                              node.get("value", 0), centers[index], center_y,
                              layout["widths"][index], unit, levels[index] == 0)
    out.append("</svg>")
    return "".join(out)


def _waterfall_label(value, is_total) -> str:
    """生成瀑布图柱顶数值标签：total 不带符号，delta 正数加「+」、负数自带「-」。

    Args:
        value: 数值（经 to_number 解析）。
        is_total: 是否为 total 柱（从 0 起画的汇总柱）。
    Returns:
        展示文本；delta 为 0 时不加符号。
    """
    if is_total or value <= 0:
        return fmt(value)
    return f"+{fmt(value)}"


def svg_waterfall(chart, width=660) -> str:
    """瀑布桥图（总量 → 逐项增减 → 净结果，允许负值），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：items=[{label, value, kind?}]；kind 取 total（缺省，从 0 画到
            value 并重置累计）或 delta（在累计上增减，value 可正可负）；unit 单位（可选）；
            height 画布高度（可选，默认 250）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；items 为空时返回空串。
    """
    items = chart.get("items", [])
    if not items:
        return ""
    unit = chart.get("unit", "")
    # steps：逐项渲染参数 (item, value, start, end, is_total)；running 为当前累计值
    steps = []
    running = 0.0
    for item in items:
        value = to_number(item.get("value", 0))
        is_total = item.get("kind", "total") != "delta"
        if is_total:
            start, end = 0.0, value
            running = value
        else:
            start, end = running, running + value
            running = end
        steps.append((item, value, start, end, is_total))
    # 坐标轴范围：含 0 与全部累计端点；有负值时取对称范围，允许 0 下方出现负刻度
    endpoints = [0.0]
    for step in steps:
        endpoints.extend((step[2], step[3]))
    peak = nice_max(endpoints)
    axis_min = -peak if min(endpoints) < 0 else 0.0
    axis_max = peak
    left, right, pad_top, pad_bottom = 52, 14, 26, 62
    height = chart.get("height", WATERFALL_HEIGHT)
    plot_w = width - left - right
    plot_h = height - pad_top - pad_bottom
    group_w = plot_w / len(items)
    bar_w = min(38.0, group_w * 0.62)

    def py(value):
        # 数据值 → 画布纵坐标（axis_min..axis_max 线性映射）
        span = axis_max - axis_min or 1
        return pad_top + plot_h - plot_h * (value - axis_min) / span

    out = [svg_open(chart, width, height)]
    # 横向网格线与刻度（5 条，含 0 与上下界；有负值时出现负刻度）
    for i in range(5):
        value = axis_min + (axis_max - axis_min) * i / 4
        y = py(value)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y:.1f}" font-size="11" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    # 相邻柱连接线：前一柱末端短实线 + 到后一柱起点的灰色虚线（两段均为 1px）
    for index in range(len(steps) - 1):
        prev_right = left + group_w * (index + 0.5) + bar_w / 2
        next_center = left + group_w * (index + 1.5)
        next_left = next_center - bar_w / 2
        joint_y = py(steps[index][3])
        joint_x = (prev_right + next_left) / 2
        out.append(f'<line x1="{prev_right:.1f}" y1="{joint_y:.1f}" x2="{joint_x:.1f}" '
                   f'y2="{joint_y:.1f}" stroke="{FAINT}" stroke-width="1"/>')
        out.append(f'<line x1="{joint_x:.1f}" y1="{joint_y:.1f}" x2="{next_center:.1f}" '
                   f'y2="{joint_y:.1f}" stroke="{FAINT}" stroke-width="1" stroke-dasharray="3 3"/>')
    # 柱体与数值标签：柱顶上方优先，放不下且柱够高时柱内白字，仍相交则跳过
    label_boxes = []
    for index, (item, value, start, end, is_total) in enumerate(steps):
        center = left + group_w * (index + 0.5)
        y_start, y_end = py(start), py(end)
        bar_top = min(y_start, y_end)
        bar_h = abs(y_end - y_start)
        if is_total:
            color = SERIES_COLORS[0]
        else:
            color = WATERFALL_UP if value >= 0 else WATERFALL_DOWN
        out.append(f'<rect x="{center - bar_w / 2:.1f}" y="{bar_top:.1f}" width="{bar_w:.1f}" '
                   f'height="{max(bar_h, 1):.1f}" rx="2" fill="{color}"/>')
        label_text = _waterfall_label(value, is_total)
        above_box = label_box(center, bar_top - 6, label_text)
        if (above_box[1] >= pad_top + 12
                and not any(boxes_intersect(above_box, placed) for placed in label_boxes)):
            label_boxes.append(above_box)
            out.append(f'<text x="{center:.1f}" y="{bar_top - 6:.1f}" font-size="11" '
                       f'fill="{SUB}" text-anchor="middle">{esc(label_text)}</text>')
        elif bar_h >= 34:
            inside_box = label_box(center, bar_top + 14, label_text)
            if not any(boxes_intersect(inside_box, placed) for placed in label_boxes):
                label_boxes.append(inside_box)
                out.append(f'<text x="{center:.1f}" y="{bar_top + 14:.1f}" font-size="11" '
                           f'fill="#fff" text-anchor="middle">{esc(label_text)}</text>')
        out.append(f'<text x="{center:.1f}" y="{pad_top + plot_h + 16:.1f}" font-size="11" '
                   f'fill="{SUB}" text-anchor="middle">{esc(truncate(item.get("label", ""), 9))}</text>')
    if unit:
        out.append(f'<text x="{width - right}" y="16" font-size="11" fill="{FAINT}" '
                   f'text-anchor="end">单位：{esc(unit)}</text>')
    out.append("</svg>")
    return "".join(out)


# ===========四、逃生舱与全图型注册==========
def svg_escape(chart, width=660) -> str:
    """逃生舱：嵌入模型手写的 SVG 片段，并补齐无障碍 title/desc 首子元素。

    Args:
        chart: 单图规格 dict：svg 为模型手写的 <svg> 片段字符串；title 图标题；
            note 图注（可选，作为 desc 文本，缺省回退标题）。
        width: 预留宽度参数（逃生舱不使用，仅保持与其他渲染器签名一致）。
    Returns:
        注入 <title>/<desc> 后的片段（根标签缺失 role/aria-label 时一并补齐）；
        片段已有 <title> 或找不到根标签时原样返回；svg 缺失时返回空串。
    """
    raw = chart.get("svg", "")
    if not raw:
        return ""
    # 作者已自带 <title>：视为已声明无障碍名称，不重复注入
    if "<title" in raw.lower():
        return raw
    open_match = re.search(r"<svg\b[^>]*>", raw, flags=re.IGNORECASE)
    if not open_match:
        return raw
    title_text = str(chart.get("title", "") or "")
    desc_text = str(chart.get("note") or title_text)
    # open_tag：根 <svg> 起始标签；按无障碍要求补齐 role/aria-label（已有则保留）
    open_tag = open_match.group(0)
    attrs = ""
    if "role=" not in open_tag:
        attrs += ' role="img"'
    if "aria-label=" not in open_tag:
        attrs += f' aria-label="{esc(title_text)}"'
    # 自闭合根标签需改为成对标签，title/desc 才能成为其子元素
    if open_tag.endswith("/>"):
        head = (f'{open_tag[:-2].rstrip()}{attrs}><title>{esc(title_text)}</title>'
                f'<desc>{esc(desc_text)}</desc></svg>')
    else:
        head = (f'{open_tag[:-1]}{attrs}><title>{esc(title_text)}</title>'
                f'<desc>{esc(desc_text)}</desc>')
    return raw[: open_match.start()] + head + raw[open_match.end():]


# RENDERERS：图型名 → 渲染函数注册表（14 种），render_dashboard.py 按此分发
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
    "tree": svg_tree,
    "waterfall": svg_waterfall,
    "svg": svg_escape,
}


# ===========五、模块调试入口==========
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

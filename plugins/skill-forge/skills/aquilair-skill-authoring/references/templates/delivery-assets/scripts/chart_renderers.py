"""SVG 图元渲染层（基础模块）：样式常量、通用工具、bar/hbar/line 图型与负值校验。

主要 Input：单张图规格 dict（供 svg_* 渲染函数）；整份看板规格 dict（供 validate_non_negative 校验）。
           规格结构见 render_dashboard.py 文件头 SPEC 说明。
主要 Output：内联 <svg> 片段字符串；规格含负值时抛出 NegativeValueError（中文报错全文）。
"""

import json
import re
import sys
from pathlib import Path


# ===========一、样式常量==========
# INK：正文主色（标题、行标签）
INK = "#1F2328"
# SUB：次级文字色（轴标签、图例、数值标签）
SUB = "#5F6368"
# FAINT：弱化文字色（刻度数值、单位注释）
FAINT = "#8B9099"
# LINE：卡片描边色
LINE = "#E3E5E8"
# GRID：网格线与进度槽底色
GRID = "#EEF0F2"
# SERIES_COLORS：系列默认配色，多系列按序循环取色
SERIES_COLORS = ["#378ADD", "#1D9E75", "#EF9F27", "#D4537E", "#7F77DD", "#888780"]
# TONE_COLORS：语义主色（ok=正常/通过，warn=待核查，danger=告警/不通过）
TONE_COLORS = {"ok": "#1D9E75", "warn": "#EF9F27", "danger": "#E24B4A"}
# TONE_BG：语义浅底色（KPI 卡片描边）
TONE_BG = {"ok": "#EAF3DE", "warn": "#FAEEDA", "danger": "#FCEBEB"}
# FONT：全局字体栈（SVG font-family 与入口层 CSS 共用）
FONT = '-apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif'


# ===========二、工具函数==========
def esc(text) -> str:
    """HTML/SVG 文本转义，防注入与截断标签。

    Args:
        text: 待转义的任意值（内部先转 str）。
    Returns:
        已转义 & < > " 四类字符的安全文本。
    """
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt(value) -> str:
    """数值紧凑格式化：整数加千分位，小数保留至多两位。

    Args:
        value: 待格式化的值；无法转为数值时按文本转义原样输出。
    Returns:
        格式化后的显示文本。
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        return esc(value)
    if num == int(num):
        return f"{int(num):,}"
    return f"{num:,.2f}".rstrip("0").rstrip(".")


def nice_max(values):
    """把最大值向上取整到「好看」的刻度（1/2/2.5/5 × 10^n），供坐标轴定界。

    Args:
        values: 数值序列（按绝对值取峰值）。
    Returns:
        不小于峰值的整齐刻度上限；峰值不大于 0 时返回 1。
    """
    peak = max((abs(v) for v in values), default=0)
    if peak <= 0:
        return 1
    mag = 10 ** (len(str(int(peak))) - 1)
    for mult in (1, 2, 2.5, 5, 10):
        if peak <= mult * mag:
            return mult * mag
    return 10 * mag


def truncate(text, limit) -> str:
    """按字符数粗截断（中文按 1 字符计），超限以省略号收尾；结尾「（编码）」段完整保留。

    Args:
        text: 原文本（内部先转 str）。
        limit: 名称段允许的最大字符数（编码段额外保留，总长可超 limit）。
    Returns:
        未超限返回原文；超限时若结尾形如「（SKU001）」的编码段则截名称段、保编码段；
            否则返回前 limit-1 个字符加「…」。
    """
    text = str(text)
    if len(text) <= limit:
        return text
    # 编码保留：业务名称规范要求「中文名称（编码）」完整可读，编码段不参与截断
    code_match = re.search(r"（[A-Za-z0-9_-]{1,16}）$", text)
    if code_match:
        code_part = code_match.group(0)
        name_budget = limit - len(code_part)
        if name_budget >= 2:
            return text[: name_budget - 1] + "…" + code_part
    return text[: limit - 1] + "…"


# ===========三、基础图型渲染==========
def svg_bar(chart, width=660) -> str:
    """竖向柱状图（支持多系列分组），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：categories 横轴分类；series=[{name, values, colors?}]；
            unit 单位（可选）；height 画布高度（可选，默认 250）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；categories 或 series 为空时返回空串。
    """
    cats = chart.get("categories", [])
    series = chart.get("series", [])
    unit = chart.get("unit", "")
    if not cats or not series:
        return ""
    all_values = [v for s in series for v in s.get("values", [])]
    top = nice_max(all_values)
    # 绘图区四边留白（px）；分类超过 8 个时加高底边，给横轴标签留空间
    left, right, pad_top, pad_bottom = 52, 14, 26, 46 if len(cats) <= 8 else 62
    plot_w = width - left - right
    height = chart.get("height", 250)
    plot_h = height - pad_top - pad_bottom
    group_w = plot_w / len(cats)
    bar_w = min(38.0, group_w * 0.62 / max(len(series), 1))

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    # 横向网格线与刻度
    for i in range(5):
        value = top * i / 4
        y = pad_top + plot_h - plot_h * i / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y:.1f}" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    # 柱体与数值标签
    for ci, cat in enumerate(cats):
        group_center = left + group_w * (ci + 0.5)
        span = bar_w * len(series) + 6 * (len(series) - 1)
        for si, s in enumerate(series):
            values = s.get("values", [])
            if ci >= len(values):
                continue
            value = float(values[ci] or 0)
            bar_h = plot_h * (abs(value) / top if top else 0)
            x = group_center - span / 2 + si * (bar_w + 6)
            y = pad_top + plot_h - bar_h
            color = s.get("colors", [None] * len(cats))[ci] or \
                SERIES_COLORS[si % len(SERIES_COLORS)]
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                       f'height="{max(bar_h, 1):.1f}" rx="2" fill="{color}"/>')
            label_y = max(y - 6, pad_top + 8)
            out.append(f'<text x="{x + bar_w / 2:.1f}" y="{label_y:.1f}" font-size="10.5" '
                       f'fill="{SUB}" text-anchor="middle">{fmt(value)}</text>')
        out.append(f'<text x="{group_center:.1f}" y="{pad_top + plot_h + 16:.1f}" '
                   f'font-size="11" fill="{SUB}" text-anchor="middle">'
                   f'{esc(truncate(cat, 8))}</text>')
    # 图例
    if len(series) > 1 or series[0].get("name"):
        lx = left
        for si, s in enumerate(series):
            color = SERIES_COLORS[si % len(SERIES_COLORS)]
            ly = pad_top + plot_h + 34
            out.append(f'<rect x="{lx}" y="{ly - 5}" width="9" height="9" rx="2" fill="{color}"/>')
            name = esc(truncate(s.get("name", ""), 12))
            out.append(f'<text x="{lx + 13}" y="{ly + 3}" font-size="11" fill="{SUB}">{name}</text>')
            lx += 22 + len(s.get("name", "")) * 11
    if unit:
        out.append(f'<text x="{width - right}" y="16" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="end">单位：{esc(unit)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_hbar(chart, width=660) -> str:
    """横向条形图（分类名较长或分类数较多时优于竖柱），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：categories 分类；只取 series[0] 的 values 与 colors（可选）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；categories 或 series 为空时返回空串。
    """
    cats = chart.get("categories", [])
    series = chart.get("series", [])
    if not cats or not series:
        return ""
    values = [float(v or 0) for v in series[0].get("values", [])]
    peak = nice_max(values)
    row_h = 30
    # 上下留白、左侧分类标签区宽、右侧数值区宽（px）——label_w 预留「名称…（编码）」全形态宽度
    pad_top, pad_bottom, label_w, value_w = 12, 14, 205, 64
    height = pad_top + pad_bottom + row_h * len(cats)
    bar_area = width - label_w - value_w - 8

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for i, (cat, value) in enumerate(zip(cats, values)):
        y = pad_top + i * row_h
        color = series[0].get("colors", [None] * len(cats))[i] or SERIES_COLORS[0]
        bar_w = bar_area * (abs(value) / peak if peak else 0)
        out.append(f'<text x="{label_w - 10}" y="{y + row_h / 2}" font-size="11.5" fill="{INK}" '
                   f'text-anchor="end" dominant-baseline="central">'
                   f'{esc(truncate(cat, 14))}</text>')
        out.append(f'<rect x="{label_w}" y="{y + 6}" width="{bar_area}" height="{row_h - 12}" '
                   f'rx="3" fill="{GRID}"/>')
        out.append(f'<rect x="{label_w}" y="{y + 6}" width="{max(bar_w, 1):.1f}" '
                   f'height="{row_h - 12}" rx="3" fill="{color}"/>')
        out.append(f'<text x="{width - 6}" y="{y + row_h / 2}" font-size="11" fill="{SUB}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_line(chart, width=660) -> str:
    """折线图（多点趋势），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：categories 横轴点（至少 2 个）；series=[{name, values}]；
            height 画布高度（可选，默认 230）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；categories 少于 2 个或 series 为空时返回空串。
    """
    cats = chart.get("categories", [])
    series = chart.get("series", [])
    if len(cats) < 2 or not series:
        return ""
    all_values = [float(v or 0) for s in series for v in s.get("values", [])]
    top = nice_max(all_values)
    left, right, pad_top, pad_bottom = 46, 16, 22, 40
    height = chart.get("height", 230)
    plot_w = width - left - right
    plot_h = height - pad_top - pad_bottom
    step = plot_w / (len(cats) - 1)

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="{esc(chart.get("title", ""))}" font-family="{FONT}">']
    for i in range(5):
        value = top * i / 4
        y = pad_top + plot_h - plot_h * i / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 6}" y="{y:.1f}" font-size="10.5" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    for si, s in enumerate(series):
        values = [float(v or 0) for v in s.get("values", [])]
        color = SERIES_COLORS[si % len(SERIES_COLORS)]
        points = " ".join(
            f"{left + step * i:.1f},{pad_top + plot_h - plot_h * (abs(v) / top if top else 0):.1f}"
            for i, v in enumerate(values)
        )
        out.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" '
                   f'stroke-linejoin="round"/>')
        for i, v in enumerate(values):
            cx = left + step * i
            cy = pad_top + plot_h - plot_h * (abs(v) / top if top else 0)
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#fff" '
                       f'stroke="{color}" stroke-width="2"/>')
            # 首末点标签改为外对齐，避免与 y 轴刻度或右边界重叠
            anchor = "start" if i == 0 else ("end" if i == len(values) - 1 else "middle")
            dx = 4 if i == 0 else (-4 if i == len(values) - 1 else 0)
            out.append(f'<text x="{cx + dx:.1f}" y="{cy - 9:.1f}" font-size="10" fill="{SUB}" '
                       f'text-anchor="{anchor}">{fmt(v)}</text>')
    label_step = max(1, len(cats) // 8)
    for i, cat in enumerate(cats):
        if i % label_step and i != len(cats) - 1:
            continue
        out.append(f'<text x="{left + step * i:.1f}" y="{pad_top + plot_h + 16}" font-size="10.5" '
                   f'fill="{SUB}" text-anchor="middle">{esc(truncate(cat, 8))}</text>')
    out.append("</svg>")
    return "".join(out)


# ===========四、负值校验==========
# NEGATIVE_VALUE_GUIDE：负值拦截报错末尾的处置指引（固定文案）
NEGATIVE_VALUE_GUIDE = "本脚本图型均按非负量绘制；差额/增减类数据请拆成『方向 + 绝对值』两列，或在明细表中呈现"
# UNCHECKED_TYPES：不做负值校验的图型（gantt 只含日期；svg 逃生舱为模型手写内容，脚本不解析）
UNCHECKED_TYPES = ("gantt", "svg")


class NegativeValueError(ValueError):
    """规格含负值时抛出的校验异常；入口层捕获后不渲染、不落盘，以退出码 2 终止。

    Input:
        message: 已组装好的中文报错全文（逐条负值定位 + 处置指引）。
    Return:
        异常对象；str(异常) 即报错全文，可直接输出到 stderr。
    """


def _iter_chart_numbers(chart):
    """逐个产出单张图待校验数值的 (字段路径, 原始值)；容器为空或 null 时视作无数据。"""
    chart_type = chart.get("type", "bar")
    if chart_type in UNCHECKED_TYPES:
        return
    if chart_type in ("donut", "progress"):
        for idx, item in enumerate(chart.get("items") or []):
            yield f"items[{idx}].value", item.get("value")
            if chart_type == "progress":
                yield f"items[{idx}].target", item.get("target")
    elif chart_type == "heatmap":
        for ri, row in enumerate(chart.get("values") or []):
            for ci, raw in enumerate(row or []):
                yield f"values[{ri}][{ci}]", raw
    elif chart_type == "scatter":
        for idx, point in enumerate(chart.get("points") or []):
            yield f"points[{idx}].x", point.get("x")
            yield f"points[{idx}].y", point.get("y")
        thresholds = chart.get("thresholds") or {}
        for axis in ("x", "y"):
            yield f"thresholds.{axis}", thresholds.get(axis)
    elif chart_type == "dual":
        for key in ("bars", "line"):
            for idx, raw in enumerate((chart.get(key) or {}).get("values") or []):
                yield f"{key}.values[{idx}]", raw
    else:
        # bar/hbar/line/stacked/radar（未注册图型已由组装入口先行报错拦截，不会进入本分支）
        for si, series in enumerate(chart.get("series") or []):
            for idx, raw in enumerate(series.get("values") or []):
                yield f"series[{si}].values[{idx}]", raw
        if chart_type == "radar":
            yield "max", chart.get("max")


def validate_non_negative(spec) -> None:
    """渲染前校验整份规格的图表数值全部非负；发现负值即中止（fail-fast，不修数、不跳过）。

    校验范围：bar/hbar/line/stacked/radar 的 series[*].values（radar 另含 max）；
    donut/progress 的 items[*].value（progress 另含 target）；heatmap 的 values 矩阵（0 合法）；
    scatter 的 points[*].x/y 与 thresholds.x/y；dual 的 bars.values 与 line.values；
    未注册图型由组装入口先行报错拦截（不回退）。gantt（纯日期）与 svg 逃生舱不校验；
    KPI 的 value 是展示字符串，不在 charts 内，不校验。
    无法解析为数值的值（None/空串等）不属本校验职责，原样交给渲染器按既有容错口径处理。

    Args:
        spec: 整份看板规格 dict，读取其中的 charts 列表逐图校验。
    Returns:
        None：全部数值非负时静默通过。
    Raises:
        NegativeValueError: 存在任一负值时抛出；消息逐条列出图标题、图型、
            出错字段（charts[i] 起始的 JSON 路径）与负值本身，末尾附处置指引。
    """
    #   1. 逐图逐字段收集负值（一次列全，便于模型一轮改完）
    problems = []
    for chart_index, chart in enumerate(spec.get("charts") or []):
        for field_path, raw in _iter_chart_numbers(chart):
            try:
                number = float(raw)
            except (TypeError, ValueError):
                # 非数值不属负值校验职责：原样交给渲染器按既有口径处理（None/空串多数图型按 0）
                continue
            if number < 0:
                problems.append(f'  - 图「{chart.get("title", "")}」[{chart.get("type", "bar")}] '
                                f'字段 charts[{chart_index}].{field_path} = {raw}')
    #   2. 有负值即汇总为中文报错抛出
    if problems:
        raise NegativeValueError(
            f"规格含 {len(problems)} 处负值，已终止渲染（未生成 HTML）：\n"
            + "\n".join(problems)
            + f"\n处置指引：{NEGATIVE_VALUE_GUIDE}。"
        )


# ===========五、模块调试入口==========
if __name__ == "__main__":
    # 延迟导入：注册表 RENDERERS 所在模块反向依赖本模块的常量与工具函数，置顶导入会形成循环
    from chart_renderers_ext import RENDERERS

    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("用法：python chart_renderers.py <规格 JSON 路径>", file=sys.stderr)
        sys.exit(2)
    # debug_spec_path：待观察的规格 JSON 路径（命令行第 1 个参数）
    debug_spec_path = Path(sys.argv[1]).resolve()
    # debug_spec：解析后的整份看板规格 dict
    debug_spec = json.loads(debug_spec_path.read_text(encoding="utf-8"))
    print(f"====渲染层调试====: {debug_spec_path}")
    # chart_index/chart：图序号与单图规格
    for chart_index, chart in enumerate(debug_spec.get("charts", [])):
        # chart_type：图型名；未注册图型与入口一致不渲染，只打印提示
        chart_type = chart.get("type", "bar")
        if chart_type not in RENDERERS:
            print(f"[{chart_index}] 图型: {chart_type} ｜ 标题: {chart.get('title', '')} ｜ 未注册（入口将报错退出）")
            continue
        # svg_bytes：该图 SVG 片段的 UTF-8 字节数（0 表示数据不足、渲染器返回空串）
        svg_bytes = len(RENDERERS[chart_type](chart).encode("utf-8"))
        print(f"[{chart_index}] 图型: {chart_type} ｜ 标题: {chart.get('title', '')} ｜ SVG 字节数: {svg_bytes}")

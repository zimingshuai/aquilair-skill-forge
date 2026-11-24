"""SVG 图元渲染层（基础模块）：样式常量、通用工具、bar/hbar/line 图型与负值校验。

主要 Input：单张图规格 dict（供 svg_* 渲染函数）；整份看板规格 dict（供 validate_non_negative 校验）。
           规格结构见 render_dashboard.py 文件头 SPEC 说明。
主要 Output：内联 <svg> 片段字符串；规格含负值或无法解析的数值时抛出
           NegativeValueError / InvalidNumberError（中文报错全文）。
"""

import json
import re
import sys
import unicodedata
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
# PAGE_BG：页面底色（米色底，WorkBuddy 看板实测 token）
PAGE_BG = "#F7F6F2"
# CARD_BG：卡片白底（KPI 卡 / 图卡 / 结论区）
CARD_BG = "#FFFFFF"
# CARD_LINE：主卡描边色（0.5px 主卡边框）
CARD_LINE = "#E5E3DC"
# ROW_LINE：表格行分隔线色（0.5px 行分隔）
ROW_LINE = "#EEF0F2"
# ROW_HOVER：表格行悬停底色
ROW_HOVER = "#FBFAF7"
# KPI_HIGHLIGHT：全局最优 KPI 卡高亮描边色（2px 绿描边）
KPI_HIGHLIGHT = "#1D9E75"
# TAG_COLORS：状态标签（背景色, 文字色）；ok=正常/通过、warn=待核查、danger=告警/不通过
TAG_COLORS = {
    "ok": ("#E1F5EE", "#0F6E56"),
    "warn": ("#FAEEDA", "#854F0B"),
    "danger": ("#FCEBEB", "#A32D2D"),
}
# BAR_LABEL_MERGE_TOLERANCE：同组柱标签合并判定时标签矩形的外扩量（px）；
# 相邻标签间距小于该值时视觉上已连成一片，按相交处理
BAR_LABEL_MERGE_TOLERANCE = 2


# ===========二、异常与工具函数==========
# NUMBER_PATTERN：可解析的数值展示写法（捕获组 1 为数字本体，其后允许空白与单位后缀）
NUMBER_PATTERN = re.compile(r"^([+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))\s*[^0-9.]*$")


class InvalidNumberError(ValueError):
    """值无法解析为数值时抛出；消息含原值与可接受的写法说明。"""


class EmptyChartDataError(ValueError):
    """图表必需数据为空或不足时抛出；入口层捕获后不渲染、不落盘，以退出码 2 终止。"""


def to_number(value):
    """把数值或数值展示文本统一转换为数字。

    Args:
        value: 待转换值：int/float 原样返回；None 或空串按 0.0；字符串去除首尾空白、
            千分位逗号（含全角「，」）与末尾「%」后，允许带单位后缀（如「2,300 件」「55,300 元」）。
    Returns:
        解析后的数字；int/float 保持原类型，字符串解析结果统一为 float。
    Raises:
        InvalidNumberError: 值既非数值，也不符合「数字 + 可选单位」的写法时抛出。
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    # 千分位与百分号是展示层符号，解析前统一剥离
    text = text.replace(",", "").replace("，", "")
    if text.endswith("%"):
        text = text[:-1].strip()
    number_match = NUMBER_PATTERN.match(text)
    if number_match:
        return float(number_match.group(1))
    raise InvalidNumberError(
        f"无法解析为数值：{value!r}（支持数字，或「1,200」「12%」「2,300 件」这类带单位文本）"
    )


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
        value: 待格式化的值，经 to_number 统一解析（支持「1,200」「12%」「2,300 件」等写法）。
    Returns:
        格式化后的显示文本。
    Raises:
        InvalidNumberError: 值无法解析为数值时抛出（不静默回退成原文本）。
    """
    num = to_number(value)
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


def display_width(text) -> int:
    """按显示宽度计字符数：中日韩/全角字符计 2，其他计 1。

    Args:
        text: 待计宽的文本（内部先转 str）。
    Returns:
        显示宽度（以半角字符为 1 个单位）。
    """
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in str(text))


def label_box(x, y, text, anchor="middle"):
    """按文本锚点估算标签矩形（宽 = 显示宽度 × 6.5 + 4，高 12）。

    Args:
        x: 文本锚点横坐标（px）。
        y: 文本基线纵坐标（px）。
        text: 标签文本（全角字符按 2 计）。
        anchor: 横向锚点：start / middle / end。
    Returns:
        (x0, y0, x1, y1) 矩形：x 按锚点向文本延伸方向展开，y 为基线以上 12px。
    """
    width = display_width(text) * 6.5 + 4
    if anchor == "start":
        x0 = x
    elif anchor == "end":
        x0 = x - width
    else:
        x0 = x - width / 2
    return (x0, y - 12, x0 + width, y)


def boxes_intersect(first, second) -> bool:
    """判断两个标签矩形是否相交（边界恰好相接不算相交）。

    Args:
        first: 矩形 (x0, y0, x1, y1)。
        second: 矩形 (x0, y0, x1, y1)。
    Returns:
        True 表示两矩形有面积重叠；边界相接返回 False。
    """
    return (first[0] < second[2] and second[0] < first[2]
            and first[1] < second[3] and second[1] < first[3])


# ===========三、基础图型渲染==========
def svg_open(chart, width, height) -> str:
    """输出 SVG 起始标签与无障碍首子元素（title → desc）。

    Args:
        chart: 单图规格 dict：title 图标题；note 图注（可选，desc 优先取它，缺省回退标题）。
        width: SVG 视口宽度（px）。
        height: SVG 视口高度（px）。
    Returns:
        `<svg>` 起始标签（含 role="img"、aria-label）紧跟 `<title>` 与 `<desc>` 的片段；
        图形元素须接在本片段之后，保证 title/desc 为无障碍树的首子元素。
    """
    title_text = str(chart.get("title", "") or "")
    # desc_text：无障碍描述优先使用图注口径，缺省回退图标题
    desc_text = str(chart.get("note") or title_text)
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="{esc(title_text)}" font-family="{FONT}">'
        f'<title>{esc(title_text)}</title><desc>{esc(desc_text)}</desc>'
    )


def _merge_bar_labels(out, label_boxes, label_records, record,
                      value, bar_center, bar_top, group_w) -> bool:
    """尝试把当前柱标签与同组近似高度的已放置标签合并为「高值 / 低值」。

    Args:
        out: SVG 片段列表；合并成功时就地替换已放置标签的文本元素。
        label_boxes: 已放置标签矩形列表；合并成功时移出旧框、加入合并框。
        label_records: 柱顶标签放置记录列表（box/ci/si/value/bar_center/bar_top/out_index）。
        record: 与当前标签矩形相交、且同分类组不同系列的已放置记录。
        value: 当前柱数值。
        bar_center: 当前柱中心横坐标（px）。
        bar_top: 当前柱顶纵坐标（px）。
        group_w: 分类组宽（px）；合并文本宽超过其 0.9 倍时放弃合并。
    Returns:
        True 表示合并成功（调用方跳过当前标签）；False 表示放弃合并，回退三级放置策略。
    """
    # high_value/low_value：合并文本按「高值 / 低值」排序，与绘制顺序无关
    high_value = max(record["value"], value)
    low_value = min(record["value"], value)
    merged_text = f"{fmt(high_value)} / {fmt(low_value)}"
    # 合并标签放在较高柱顶上方：柱顶纵坐标更小者为高柱
    if record["value"] >= value:
        high_center, high_top = record["bar_center"], record["bar_top"]
    else:
        high_center, high_top = bar_center, bar_top
    merged_box = label_box(high_center, high_top - 6, merged_text)
    # 合并文本过宽会压到相邻分类组：放弃合并，交给柱顶/柱内/跳过三级策略
    if merged_box[2] - merged_box[0] > group_w * 0.9:
        return False
    label_boxes.remove(record["box"])
    label_boxes.append(merged_box)
    out[record["out_index"]] = (
        f'<text x="{high_center:.1f}" y="{high_top - 6:.1f}" font-size="11" '
        f'fill="{SUB}" text-anchor="middle">{esc(merged_text)}</text>'
    )
    record["box"] = merged_box
    record["value"] = high_value
    record["bar_center"] = high_center
    record["bar_top"] = high_top
    return True


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
    all_values = [to_number(v) for s in series for v in s.get("values", [])]
    top = nice_max(all_values)
    # 绘图区四边留白（px）；分类标签改两行后底边加高（≤8 分类 62，>8 分类 78）
    left, right, pad_top, pad_bottom = 52, 14, 26, 62 if len(cats) <= 8 else 78
    plot_w = width - left - right
    height = chart.get("height", 250)
    plot_h = height - pad_top - pad_bottom
    group_w = plot_w / len(cats)
    bar_w = min(38.0, group_w * 0.62 / max(len(series), 1))

    out = [svg_open(chart, width, height)]
    # 横向网格线与刻度
    for i in range(5):
        value = top * i / 4
        y = pad_top + plot_h - plot_h * i / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y:.1f}" font-size="11" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    # 柱体与数值标签：先算候选矩形再放，避免顶刻度带与已放置标签互压；
    # label_records 记录柱顶上方标签的放置信息，供同组近似值合并标注使用
    label_boxes = []
    label_records = []
    for ci, cat in enumerate(cats):
        group_center = left + group_w * (ci + 0.5)
        span = bar_w * len(series) + 6 * (len(series) - 1)
        for si, s in enumerate(series):
            values = s.get("values", [])
            if ci >= len(values):
                continue
            value = to_number(values[ci])
            bar_h = plot_h * (abs(value) / top if top else 0)
            x = group_center - span / 2 + si * (bar_w + 6)
            y = pad_top + plot_h - bar_h
            color = s.get("colors", [None] * len(cats))[ci] or \
                SERIES_COLORS[si % len(SERIES_COLORS)]
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                       f'height="{max(bar_h, 1):.1f}" rx="2" fill="{color}"/>')
            # value_text / bar_center：数值标签文本与柱中心横坐标
            value_text = fmt(value)
            bar_center = x + bar_w / 2
            # above_box：柱顶上方候选（基线 y-6）；inside_box：柱内候选（基线 y+14，柱够高才有）
            above_box = label_box(bar_center, y - 6, value_text)
            inside_box = label_box(bar_center, y + 14, value_text) if bar_h >= 34 else None
            above_allowed = (above_box[1] >= pad_top + 12
                             and not any(boxes_intersect(above_box, placed)
                                         for placed in label_boxes))
            # candidate_box：本次实际会尝试放置的标签矩形；用于同组近似值合并判定
            candidate_box = above_box if above_box[1] >= pad_top + 12 else inside_box
            # merge_record：同组不同系列、两柱顶 y 差 < 12px 且标签贴得过近的已放置记录；
            # 贴得过近按视觉相交处理（矩形外扩 BAR_LABEL_MERGE_TOLERANCE），合并为「高值 / 低值」
            merge_record = None
            if candidate_box is not None:
                near_box = (candidate_box[0] - BAR_LABEL_MERGE_TOLERANCE,
                            candidate_box[1] - BAR_LABEL_MERGE_TOLERANCE,
                            candidate_box[2] + BAR_LABEL_MERGE_TOLERANCE,
                            candidate_box[3] + BAR_LABEL_MERGE_TOLERANCE)
                for record in label_records:
                    if (record["ci"] == ci and record["si"] != si
                            and abs(record["bar_top"] - y) < 12
                            and boxes_intersect(near_box, record["box"])):
                        merge_record = record
                        break
            if merge_record and _merge_bar_labels(out, label_boxes, label_records, merge_record,
                                                  value, bar_center, y, group_w):
                continue
            if above_allowed:
                label_boxes.append(above_box)
                label_records.append({
                    "box": above_box, "ci": ci, "si": si, "value": value,
                    "bar_center": bar_center, "bar_top": y, "out_index": len(out),
                })
                out.append(f'<text x="{bar_center:.1f}" y="{y - 6:.1f}" font-size="11" '
                           f'fill="{SUB}" text-anchor="middle">{esc(value_text)}</text>')
            elif inside_box is not None:
                # 柱内顶部候选：仍相交则跳过该标签（不画、不压字）
                if not any(boxes_intersect(inside_box, placed) for placed in label_boxes):
                    label_boxes.append(inside_box)
                    label_records.append({
                        "box": inside_box, "ci": ci, "si": si, "value": value,
                        "bar_center": bar_center, "bar_top": y, "out_index": len(out),
                    })
                    out.append(f'<text x="{bar_center:.1f}" y="{y + 14:.1f}" font-size="11" '
                               f'fill="#fff" text-anchor="middle">{esc(value_text)}</text>')
        # 分类标签：「名称（编码）」拆两行，名称截断 7 字、编码完整保留；无编码维持单行截断 8 字
        label_y1 = pad_top + plot_h + 16
        code_match = re.match(r"^(.+?)（([A-Za-z0-9_-]{1,16})）$", str(cat))
        if code_match:
            out.append(f'<text x="{group_center:.1f}" y="{label_y1:.1f}" '
                       f'font-size="11" fill="{SUB}" text-anchor="middle">'
                       f'{esc(truncate(code_match.group(1), 7))}</text>')
            out.append(f'<text x="{group_center:.1f}" y="{label_y1 + 13:.1f}" '
                       f'font-size="11" fill="{SUB}" text-anchor="middle">'
                       f'（{esc(code_match.group(2))}）</text>')
        else:
            out.append(f'<text x="{group_center:.1f}" y="{label_y1:.1f}" '
                       f'font-size="11" fill="{SUB}" text-anchor="middle">'
                       f'{esc(truncate(cat, 8))}</text>')
    # 图例：y 随两行分类标签下移，保证不与第二行标签重叠
    if len(series) > 1 or series[0].get("name"):
        lx = left
        ly = pad_top + plot_h + (50 if len(cats) <= 8 else 64)
        for si, s in enumerate(series):
            color = SERIES_COLORS[si % len(SERIES_COLORS)]
            out.append(f'<rect x="{lx}" y="{ly - 5}" width="9" height="9" rx="2" fill="{color}"/>')
            name = esc(truncate(s.get("name", ""), 12))
            out.append(f'<text x="{lx + 13}" y="{ly + 3}" font-size="11" fill="{SUB}">{name}</text>')
            lx += 22 + len(s.get("name", "")) * 11
    if unit:
        out.append(f'<text x="{width - right}" y="16" font-size="11" fill="{FAINT}" '
                   f'text-anchor="end">单位：{esc(unit)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_hbar(chart, width=660) -> str:
    """横向条形图（长分类名 / 多系列横向对比），返回 <svg> 片段。

    Args:
        chart: 单图规格 dict：categories 分类；series=[{name, values, colors?}]，
            多系列时每个分类一组横条（单系列保持原每分类一行外观）；unit 单位（可选）。
        width: SVG 视口宽度（px）。
    Returns:
        <svg> 片段字符串；categories 或 series 为空时返回空串。
    """
    cats = chart.get("categories", [])
    series = chart.get("series", [])
    if not cats or not series:
        return ""
    #   1. 单系列：沿用原「每分类一行」几何，旧规格渲染结果不变
    if len(series) == 1:
        values = [to_number(v) for v in series[0].get("values", [])]
        peak = nice_max(values)
        row_h = 30
        # 上下留白、左侧分类标签区宽、右侧数值区宽（px）——label_w 预留「名称…（编码）」全形态宽度
        pad_top, pad_bottom, label_w, value_w = 12, 14, 205, 64
        height = pad_top + pad_bottom + row_h * len(cats)
        bar_area = width - label_w - value_w - 8
        out = [svg_open(chart, width, height)]
        for i, (cat, value) in enumerate(zip(cats, values)):
            y = pad_top + i * row_h
            colors = series[0].get("colors") or []
            color = (colors[i] if i < len(colors) else None) or SERIES_COLORS[0]
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

    #   2. 多系列：每分类一组横条（条高 14、条间距 4），组高按系列数×22+8 预留组间距
    all_values = [to_number(v) for s in series for v in s.get("values", [])]
    peak = nice_max(all_values)
    bar_h, bar_gap, group_h = 14, 4, len(series) * 22 + 8
    # pitch：同组相邻横条的纵向步长（条高 + 条间距）
    pitch = bar_h + bar_gap
    # 上下留白、左侧分类标签区宽、右侧数值回退区宽（px）
    pad_top, pad_bottom, label_w, right_pad = 12, 14, 205, 12
    body_h = pad_top + pad_bottom + group_h * len(cats)
    height = body_h + 26
    bar_area = width - label_w - right_pad
    out = [svg_open(chart, width, height)]
    for ci, cat in enumerate(cats):
        group_y = pad_top + ci * group_h
        out.append(f'<text x="{label_w - 10}" y="{group_y + group_h / 2:.1f}" '
                   f'font-size="11.5" fill="{INK}" text-anchor="end" '
                   f'dominant-baseline="central">{esc(truncate(cat, 14))}</text>')
        for si, s in enumerate(series):
            values = s.get("values", [])
            if ci >= len(values):
                continue
            value = to_number(values[ci])
            bar_w = bar_area * (abs(value) / peak if peak else 0)
            colors = s.get("colors") or []
            color = (colors[ci] if ci < len(colors) else None) or \
                SERIES_COLORS[si % len(SERIES_COLORS)]
            y = group_y + 4 + si * pitch
            out.append(f'<rect x="{label_w}" y="{y}" width="{bar_area}" height="{bar_h}" '
                       f'rx="3" fill="{GRID}"/>')
            out.append(f'<rect x="{label_w}" y="{y}" width="{max(bar_w, 1):.1f}" '
                       f'height="{bar_h}" rx="3" fill="{color}"/>')
            # 数值标签：条够长且放得下时放条右侧，否则回退条内右端白字
            text = fmt(value)
            bar_end = label_w + max(bar_w, 1)
            if bar_w >= 40 and bar_end + 6 + len(text) * 7 <= width - 4:
                label_x, anchor, fill = bar_end + 6, "start", SUB
            else:
                label_x, anchor, fill = bar_end - 4, "end", "#fff"
            out.append(f'<text x="{label_x:.1f}" y="{y + bar_h / 2:.1f}" font-size="11" '
                       f'fill="{fill}" text-anchor="{anchor}" dominant-baseline="central">'
                       f'{esc(text)}</text>')
    # 多系列图例：底部一行，沿用 bar 图例样式（色块+名称，名称截断 12）
    legend_y = body_h + 12
    lx = 14
    for si, s in enumerate(series):
        colors = s.get("colors") or []
        color = colors[0] if colors else SERIES_COLORS[si % len(SERIES_COLORS)]
        name = s.get("name", "")
        out.append(f'<rect x="{lx}" y="{legend_y - 5}" width="9" height="9" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx + 13}" y="{legend_y + 3}" font-size="11" fill="{SUB}">'
                   f'{esc(truncate(name, 12))}</text>')
        lx += 22 + len(name) * 11
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
    all_values = [to_number(v) for s in series for v in s.get("values", [])]
    top = nice_max(all_values)
    left, right, pad_top, pad_bottom = 46, 16, 22, 40
    height = chart.get("height", 230)
    plot_w = width - left - right
    plot_h = height - pad_top - pad_bottom
    step = plot_w / (len(cats) - 1)

    out = [svg_open(chart, width, height)]
    for i in range(5):
        value = top * i / 4
        y = pad_top + plot_h - plot_h * i / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 6}" y="{y:.1f}" font-size="11" fill="{FAINT}" '
                   f'text-anchor="end" dominant-baseline="central">{fmt(value)}</text>')
    for si, s in enumerate(series):
        values = [to_number(v) for v in s.get("values", [])]
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
            out.append(f'<text x="{cx + dx:.1f}" y="{cy - 9:.1f}" font-size="11" fill="{SUB}" '
                       f'text-anchor="{anchor}">{fmt(v)}</text>')
    label_step = max(1, len(cats) // 8)
    for i, cat in enumerate(cats):
        if i % label_step and i != len(cats) - 1:
            continue
        out.append(f'<text x="{left + step * i:.1f}" y="{pad_top + plot_h + 16}" font-size="11" '
                   f'fill="{SUB}" text-anchor="middle">{esc(truncate(cat, 8))}</text>')
    out.append("</svg>")
    return "".join(out)


# ===========四、负值校验==========
# NEGATIVE_VALUE_GUIDE：负值拦截报错末尾的处置指引（固定文案）
NEGATIVE_VALUE_GUIDE = "本脚本图型均按非负量绘制；差额/增减类数据请拆成『方向 + 绝对值』两列，或在明细表中呈现"
# UNCHECKED_TYPES：不做负值校验的图型（gantt 只含日期；svg 逃生舱为模型手写内容，脚本不解析；
# waterfall 为增减专用图型，delta 允许负值）
UNCHECKED_TYPES = ("gantt", "svg", "waterfall")


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
    elif chart_type == "tree":
        for idx, node in enumerate(chart.get("nodes") or []):
            yield f"nodes[{idx}].value", node.get("value")
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
    tree 的 nodes[*].value；未注册图型由组装入口先行报错拦截（不回退）。
    gantt（纯日期）、svg 逃生舱与 waterfall（增减专用，delta 允许负值）不校验负值；
    waterfall 的数值可解析性由渲染时 to_number 把关（不可解析仍按 InvalidNumberError 报错）。
    KPI 的 value 是展示字符串，不在 charts 内，不校验。None/空串按 0 处理；
    「1,200」「12%」「2,300 件」等展示写法经 to_number 统一解析。

    Args:
        spec: 整份看板规格 dict，读取其中的 charts 列表逐图校验。
    Returns:
        None：全部数值非负且可解析时静默通过。
    Raises:
        NegativeValueError: 存在任一负值时抛出；消息逐条列出图标题、图型、
            出错字段（charts[i] 起始的 JSON 路径）与负值本身，末尾附处置指引。
        InvalidNumberError: 存在无法解析为数值的字段时抛出；消息逐条列出位置与原值。
    """
    #   1. 逐图逐字段收集负值与非法数值（一次列全，便于模型一轮改完）
    problems = []
    invalid = []
    for chart_index, chart in enumerate(spec.get("charts") or []):
        for field_path, raw in _iter_chart_numbers(chart):
            try:
                number = to_number(raw)
            except InvalidNumberError:
                invalid.append(f'  - 图「{chart.get("title", "")}」[{chart.get("type", "bar")}] '
                               f'字段 charts[{chart_index}].{field_path} = {raw!r}')
                continue
            if number < 0:
                problems.append(f'  - 图「{chart.get("title", "")}」[{chart.get("type", "bar")}] '
                                f'字段 charts[{chart_index}].{field_path} = {raw}')
    #   2. 有负值或非法数值即汇总为中文报错抛出
    if problems:
        raise NegativeValueError(
            f"规格含 {len(problems)} 处负值，已终止渲染（未生成 HTML）：\n"
            + "\n".join(problems)
            + f"\n处置指引：{NEGATIVE_VALUE_GUIDE}。"
        )
    if invalid:
        raise InvalidNumberError(
            f"规格含 {len(invalid)} 处无法解析为数值，已终止渲染（未生成 HTML）：\n"
            + "\n".join(invalid)
            + "\n处置指引：图上数值须为数字或「1,200」「12%」「2,300 件」这类带单位文本。"
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

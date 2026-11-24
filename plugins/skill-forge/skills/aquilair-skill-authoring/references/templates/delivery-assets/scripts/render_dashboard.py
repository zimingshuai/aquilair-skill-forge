"""按图表规格 JSON 渲染自包含 HTML 看板（零依赖、内联 SVG）。

设计目的：把「出图」从模型手写 SVG/HTML（每图数千 token 输出，耗时数十秒）
改为「模型只产规格 JSON（约数百 token）+ 脚本确定性渲染（毫秒级）」。
数值由脚本直写进图元，天然满足「图上数值 = 工具返回值、同源不重算」的数据纪律。
图元渲染层位于同目录：chart_renderers（样式/工具/基础图型/负值校验）、
chart_renderers_ext（构成与达成图型 + 图型注册表）、chart_renderers_adv（高级图型）。

主要 Input：--spec 规格 JSON 文件路径；值传 - 时从 stdin 读取 UTF-8 JSON（与 --list-types/--example 互斥）；
--out 输出 HTML 路径（可选，缺省 deliverables/<slug>.html，相对当前工作目录）；
--quiet 只打印输出路径（可选，便于脚本串联；--fragment 下不生效）；
--list-types 不读规格，列出 14 种图型、必需字段与用途后退出（与 --spec 同时给出时优先）；
--example TYPE 打印该图型的最小可渲染规格 JSON（含 _note 中文说明，可直接重定向后交给 --spec）；
--mirror DIR 正常落盘后再复制一份 HTML 到 DIR（不存在则创建），并打印「落档」「内联」两行路径；
--fragment 输出可嵌入宿主 widget 的 HTML 片段（<style> + .wrap 页面主体，不含 DOCTYPE/html/head/body）；
给了 --out 则写入该文件并在 stdout 打印路径，否则直接把片段打印到 stdout（不混入任何日志）；
与 --mirror 同时给出时忽略 mirror（stderr 中文提示一句）。
主要 Output：自包含单文件 HTML（内联 CSS/SVG，无外部依赖）；--fragment 时输出可嵌入宿主的 HTML 片段；
完整文档模式在 stdout 打印路径与耗时，片段模式的 stdout 只输出片段本身或 --out 路径（不混入日志）；
规格含未注册图型、空图数据、负值（waterfall 增减专用除外）或非法数值时不渲染、不落盘，
stderr 输出中文报错并以退出码 2 退出；--spec - 的 stdin 为空或非法 JSON 时同口径以退出码 2 退出。

SPEC 结构（除 title 外均可选）：
{
  "title": "仓群库存风险总览",
  "subtitle": "来源：InventoryRisk（demo 环境）｜2026-11-09",
  "conclusion": ["P0 仓 2 个，占总风险金额 61%", "..."],
  "kpis": [{"label": "P0 仓", "value": "2", "tone": "danger",
            "note": "占总风险金额 61%", "highlight": true}],
  "charts": [
    {"type": "bar",  "title": "...", "unit": "万元", "categories": ["A","B"],
     "note": "口径：按物料汇总，主线 main",
     "series": [{"name": "风险金额", "values": [1,2]}]},
    {"type": "hbar", "title": "...", "unit": "件", "categories": ["A","B"],
     "series": [{"name": "需求", "values": [3,2]}, {"name": "缺口", "values": [1,0]}]},
    {"type": "line", "title": "...", "categories": ["1月","2月"],
     "series": [{"name": "齐套率", "values": [1,2]}]},
    {"type": "donut","title": "...", "items": [{"label": "正常", "value": 1}]},
    {"type": "stacked","title": "...", "categories": ["A"], "series": [{"name":"P0","values":[1]}]},
    {"type": "heatmap","title": "缺口矩阵", "rows": ["华东一仓"], "cols": ["SKU-1"],
     "values": [[12]], "ramp": "warn"},
    {"type": "progress","title": "齐套率", "items": [{"label":"六类齐套","value":86,"target":95,"unit":"%"}]},
    {"type": "scatter","title": "ABC 分类", "x_label": "周转次数", "y_label": "库存金额（万元）",
     "groups": {"A":"#E24B4A"},
     "points": [{"x":12,"y":86,"label":"牛肉（MT-1001）","group":"A"}],
     "connect_groups": ["A"],
     "thresholds": {"x": 8, "y": 50}},
    {"type": "dual","title": "缺口量 vs 齐套率", "categories": ["W1"],
     "bars": {"name":"缺口","values":[120]}, "bar_unit": "件",
     "line": {"name":"齐套率","values":[78]}, "line_unit": "%"},
    {"type": "radar","title": "方案对比", "axes": ["成本","时效","齐套率"],
     "series": [{"name":"方案A","values":[80,60,90]}], "max": 100},
    {"type": "gantt","title": "到货排期", "today": "2026-11-08",
     "rows": [{"label":"PO-1001","start":"2026-10-28","end":"2026-11-04","status":"done","note":"已到货"}]},
    {"type": "tree", "title": "BOM 毛需求树", "direction": "horizontal", "unit": "件",
     "nodes": [{"id":"root","label":"P-X30（根）","value":800},
               {"id":"cap","label":"滤波电容100uF（CAP-100）","value":3264,"parent":"root"}]},
    {"type": "waterfall", "title": "缺口桥", "unit": "件",
     "items": [{"label":"毛需求","value":3264,"kind":"total"},
               {"label":"现货分配","value":-2000,"kind":"delta"},
               {"label":"净缺口","value":1248,"kind":"total"}]},
    {"type": "svg", "title": "一次表达（模型手写）", "svg": "<svg ...>...</svg>"}
  ],
  "table": {"title": "明细", "columns": ["仓", "等级"], "rows": [["A", "P0"]],
            "layout": "auto", "footer": ["合计", "—"], "truncate": {"仓": 12},
            "tags": [{"column": "等级", "map": {"P0": "danger", "P1": "warn"}}]},
  "tables": [{"title": "明细二", "columns": ["仓", "缺口"], "rows": [["A", 10]]},
             {"title": "明细三（带状态标签）", "columns": ["仓", "等级"], "rows": [["A", "P0"]],
              "tags": [{"column": "等级", "map": {"P0": "danger"}}]}],
  "insight": "洞察结语"
}
tone 取值：ok（正常/通过）｜warn（待核查）｜danger（告警/不通过）。
图注与高亮：chart.note 渲染在图标题下方（12px 灰，SVG 上方，空则不占位，并作为 SVG <desc> 文本）；
kpis[].note 为 KPI 卡第三行说明；kpis[].highlight=true 时该卡 2px 绿描边（通常只标全局最优卡）。
状态标签：table.tags 按列把命中 map 的单元格值渲染为 ok/warn/danger 状态标签（左对齐）；
列名不存在时忽略该规则（不报错）。
逐条着色：bar / hbar / stacked 的 series 内可用 colors 数组按条目着色（如 Top N 缺货条目视觉强调），
推荐语义色 红 #E24B4A（告警/缺货）｜黄 #EF9F27（待核查）｜绿 #1D9E75（正常/通过）。
bar 近似值合并：同分类组不同系列的柱顶 y 差 < 12px 且标签矩形相交时，合并为一个「高值 / 低值」标签
放在较高柱顶上方；合并文本宽超过组宽 90% 时放弃合并，回退柱顶/柱内/跳过三级放置（单系列不受影响）。
标签与图例：分类标签过长自动截断但**保留结尾「（编码）」段**；bar 的分类标签形如「名称（编码）」时
拆两行渲染——第一行名称（超过 7 字截断），第二行编码（含括号，完整保留）；series.name 图例超长约 12 字符
会被截断——环境、分支等关键口径不要只放图例，放图标题或明细表。看板页脚的「生成日」由模型写入 subtitle。
hbar 多系列：每个分类一组横条，series[i].colors 可逐条覆盖颜色；单系列外观与旧版一致。
表格：table.layout 取 auto（默认，按估算总宽与列数自动选择）｜compact（全表不换行 + 横向滚动）｜
wrap（允许换行、不滚动）；table.footer 为合计行（字符串数组，按列顺序渲染在 tfoot，加粗 + 顶部 2px 实线）；
table.truncate 按列名指定最大字符数（超限显示前 N 字 + 「…」，title 属性保留全文）。
多表：tables 为数组，每项结构与 table 相同（title/columns/rows/footer/tags/truncate/layout）；
先渲染 table（若存在），再按 tables 顺序逐张渲染，各表自带标题、表间垂直间距 18px，能力与单表完全一致。
scatter 折线叠加：connect_groups 列出组名时，该组散点按 points 出现顺序连成折线（组色 2px、不闭合），
连线绘制在散点之下；未列出的组保持仅散点（标签避让逻辑不变）。
tree 树状分层图：direction 取 vertical（默认，根在上）或 horizontal（每层一列、左→右）；
两种布局均为父框居中于直接子节点群，节点上限 30、层深上限 5；
vertical 总宽压到框宽下限 74px 仍超 620px 时自动改用 horizontal（不报错）；
horizontal 框宽按标签自适应（clamp 120–180px）、列距 40px、层内节点纵向间距 10px，
超宽压缩框宽（下限 110px），压缩到下限仍超宽或画布高超过 620px 时中文报错、提示拆图或汇总；
节点框第一行标签（截断 12、保留「（编码）」），第二行 value+unit，根节点浅蓝底、其余白底。
waterfall 瀑布桥：items 逐项累计，kind=total（缺省）从 0 画到 value 并重置累计，
kind=delta 在累计上增减（value 可正可负）；柱色 total 蓝、delta 正绿负红，相邻柱虚线连接，y 轴允许负刻度。
图型口径：type 须为上述已注册图型之一；未注册图型同样不渲染、不落盘，stderr 报错并以退出码 2 退出——图库未覆盖的一次性表达请改用 "svg" 逃生舱。
数值口径：除 gantt（纯日期）、svg 逃生舱与 waterfall（增减专用，delta 允许负值）外，图表内全部数值须 ≥ 0
（0 合法）且可解析为数值（支持「1,200」「12%」「2,300 件」等展示写法）；出现负值或无法解析的数值时脚本不渲染、不落盘，
stderr 报错并以退出码 2 退出。差额/增减类数据请改用 waterfall，或在明细表中呈现。
自描述：--list-types 查图型与必需字段，--example <type> 取最小骨架后填数，--mirror <目录> 落档＋内联双投递。
"""

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

from chart_renderers import (
    CARD_BG,
    CARD_LINE,
    FAINT,
    FONT,
    INK,
    KPI_HIGHLIGHT,
    LINE,
    PAGE_BG,
    ROW_HOVER,
    ROW_LINE,
    TAG_COLORS,
    TONE_BG,
    TONE_COLORS,
    EmptyChartDataError,
    InvalidNumberError,
    NegativeValueError,
    display_width,
    esc,
    to_number,
    validate_non_negative,
)
from chart_renderers_adv import _parse_day
from chart_renderers_ext import (
    RENDERERS,
    TREE_MAX_DEPTH,
    TREE_MAX_NODES,
    TreeLayoutError,
    build_tree_chart_layout,
)


# ===========一、版本与页面样式==========
# SCRIPT_VERSION：脚本版本号（写入页脚，便于追溯产物由哪版脚本生成）
SCRIPT_VERSION = "1.5.0"
# TABLE_COMPACT_MAX_WIDTH：表格估算总宽超过此值（px）时按紧凑模式渲染（nowrap + 横向滚动）
TABLE_COMPACT_MAX_WIDTH = 1500
# TABLE_COMPACT_MIN_COLUMNS：列数达到此值时按紧凑模式渲染（长 ID 表避免逐字折行）
TABLE_COMPACT_MIN_COLUMNS = 9
# TABLE_CELL_PADDING_PX：单元格单侧 padding（px），列宽估算按左右两侧计
TABLE_CELL_PADDING_PX = 10
# TABLE_GAP_PX：多表之间的垂直间距（px）
TABLE_GAP_PX = 18

# CSS：看板内联样式表（单文件自包含；%占位符% 由 CSS_TOKENS 替换为设计 token）
CSS = """
*{box-sizing:border-box}
body{margin:0;padding:28px 24px 40px;background:%PAGE_BG%;color:#1F2328;font-family:%FONT%;
     font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto}
h1{font-size:20px;font-weight:500;margin:0 0 6px;letter-spacing:.2px}
.sub{font-size:12px;color:%FAINT%;margin:0 0 18px}
.sec-label{font-size:12px;font-weight:500;color:%FAINT%;letter-spacing:.6px;margin:26px 0 10px}
.concl{background:%CARD_BG%;border:0.5px solid %CARD_LINE%;border-left:3px solid #378ADD;
       border-radius:4px;padding:12px 16px;margin:0 0 18px}
.concl p{margin:3px 0;font-size:13.5px}
.kpis{display:flex;flex-wrap:wrap;gap:10px}
.kpi{flex:1 1 150px;background:%CARD_BG%;border:0.5px solid %CARD_LINE%;border-radius:12px;
     padding:16px;display:flex;flex-direction:column;justify-content:space-between}
.kpi.hl{border:2px solid %KPI_HIGHLIGHT%}
.kpi .l{font-size:12px;color:#5F6368}
.kpi .v{font-size:24px;font-weight:500;margin-top:4px;font-variant-numeric:tabular-nums}
.kpi .v.sm{font-size:15px;line-height:1.35}
.kpi .n{font-size:12px;color:%FAINT%;line-height:1.5;margin-top:4px}
.charts{display:flex;flex-wrap:wrap;gap:14px}
.card{flex:1 1 460px;background:%CARD_BG%;border:0.5px solid %CARD_LINE%;border-radius:12px;
      padding:14px 12px 8px;min-width:0}
.card h3{font-size:13px;font-weight:500;margin:0 0 2px;padding-left:4px}
.card .note{font-size:12px;color:%FAINT%;line-height:1.5;margin:0 0 4px;padding-left:4px}
.table-wrap{overflow-x:auto}
.table-wrap.wrap{overflow-x:visible}
.table-wrap.compact table{white-space:nowrap}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:0.5px solid %ROW_LINE%;padding:8px 10px;text-align:left;vertical-align:top}
th{font-size:12px;color:#5F6368;font-weight:400;background:#FAFBFC;white-space:nowrap}
thead th{position:sticky;top:0;z-index:1}
td.num{font-variant-numeric:tabular-nums;text-align:right}
td.ctr{text-align:center}
tbody tr:hover td{background:%ROW_HOVER%}
tfoot td{font-weight:500;border-top:0.5px solid %CARD_LINE%;border-bottom:none}
.tag{display:inline-block;padding:1px 7px;border-radius:4px;font-size:11px}
.tag.ok{background:%TAG_OK_BG%;color:%TAG_OK_FG%}
.tag.warn{background:%TAG_WARN_BG%;color:%TAG_WARN_FG%}
.tag.danger{background:%TAG_DANGER_BG%;color:%TAG_DANGER_FG%}
.insight{margin-top:22px;padding:12px 16px;border:0.5px dashed #D6D9DE;border-radius:8px;
         font-size:13px;color:#3D434B}
footer{margin-top:26px;font-size:12px;color:#A0A5AC;border-top:0.5px solid %CARD_LINE%;
       padding-top:10px}
"""
# CSS_TOKENS：CSS 占位符 → 设计 token 值（字体栈与底色/边框/标签色统一由常量区提供）
CSS_TOKENS = {
    "%FONT%": FONT,
    "%PAGE_BG%": PAGE_BG,
    "%CARD_BG%": CARD_BG,
    "%CARD_LINE%": CARD_LINE,
    "%ROW_LINE%": ROW_LINE,
    "%ROW_HOVER%": ROW_HOVER,
    "%KPI_HIGHLIGHT%": KPI_HIGHLIGHT,
    "%FAINT%": FAINT,
    "%TAG_OK_BG%": TAG_COLORS["ok"][0],
    "%TAG_OK_FG%": TAG_COLORS["ok"][1],
    "%TAG_WARN_BG%": TAG_COLORS["warn"][0],
    "%TAG_WARN_FG%": TAG_COLORS["warn"][1],
    "%TAG_DANGER_BG%": TAG_COLORS["danger"][0],
    "%TAG_DANGER_FG%": TAG_COLORS["danger"][1],
}
for _placeholder, _token in CSS_TOKENS.items():
    CSS = CSS.replace(_placeholder, _token)
del _placeholder, _token


# ===========二、表格与页面区块渲染==========
def _evaluate_layout(table) -> str:
    """判定表格布局：显式 compact/wrap 优先，auto 按估算总宽与列数决定。

    Args:
        table: 表格规格 dict：columns 列名；rows 行数据；footer 合计行（可选）；
            layout 布局模式（auto/compact/wrap，默认 auto）。
    Returns:
        "compact"（全表不换行 + 横向滚动）或 "wrap"（允许换行、不滚动）。
    """
    layout = table.get("layout", "auto")
    if layout in ("compact", "wrap"):
        return layout
    columns = table.get("columns", [])
    rows = table.get("rows", []) or []
    footer = table.get("footer", []) or []
    # estimated_width：逐列取「表头 + 表体 + 合计行」最长单元格的显示宽，再加左右 padding
    estimated_width = 0
    for column_index, column in enumerate(columns):
        cell_texts = [str(column)]
        cell_texts += [str(row[column_index]) for row in rows if column_index < len(row)]
        if column_index < len(footer):
            cell_texts.append(str(footer[column_index]))
        estimated_width += max((display_width(text) for text in cell_texts), default=0) \
            + 2 * TABLE_CELL_PADDING_PX
    if estimated_width > TABLE_COMPACT_MAX_WIDTH or len(columns) >= TABLE_COMPACT_MIN_COLUMNS:
        return "compact"
    return "wrap"


def _render_cell(raw, truncate_limit=None, tag_map=None) -> str:
    """渲染单个表格单元格：状态标签优先，其余按数值右对齐、空值与「—」居中，并按列截断。

    Args:
        raw: 单元格原始值（任意类型，内部先转 str）。
        truncate_limit: 该列最大字符数；None 表示不截断。超限显示前 N 字 + 「…」，
            并在 title 属性保留全文。
        tag_map: 该列状态标签映射（原值 → ok/warn/danger）；命中时渲染 <span class="tag">，
            未命中或 None 时按原规则渲染。tag 单元格左对齐（不加数值右对齐类）。
    Returns:
        单元格 <td> HTML 片段。
    """
    text = str(raw)
    # tag_class：该单元格值命中的状态标签语义（ok/warn/danger）；未命中为空串
    tag_class = (tag_map or {}).get(text.strip())
    if tag_class:
        return f'<td><span class="tag {esc(tag_class)}">{esc(text)}</span></td>'
    display_text = text
    title_attr = ""
    if truncate_limit and len(text) > truncate_limit:
        display_text = text[:truncate_limit] + "…"
        title_attr = f' title="{esc(text)}"'
    if not text.strip() or text.strip() == "—":
        cell_class = "ctr"
    else:
        try:
            to_number(text)
            cell_class = "num"
        except InvalidNumberError:
            cell_class = ""
    class_attr = f' class="{cell_class}"' if cell_class else ""
    return f"<td{class_attr}{title_attr}>{esc(display_text)}</td>"


def _chart_note_html(chart) -> str:
    """渲染图注（图标题与 SVG 之间的口径说明行）。

    Args:
        chart: 单图规格 dict：note 图注文本（可选）。
    Returns:
        `<div class="note">…</div>` 片段；note 为空时返回空串（不占位）。
    """
    note = str(chart.get("note", "") or "")
    return f'<div class="note">{esc(note)}</div>' if note else ""


def render_kpis(kpis) -> str:
    """渲染 KPI 卡片组（label / value / note 三段纵向，可选全局最优高亮）。

    Args:
        kpis: KPI 规格列表，每项含 label（标签）、value（展示字符串，不做数值校验）、
            tone（语义色 ok/warn/danger，缺省 ok）、note（第三行说明，可选）、
            highlight（布尔，True 时 2px 绿描边，通常仅全局最优卡置 True）。
    Returns:
        KPI 卡片组 HTML 片段；列表为空时返回空串。
    """
    if not kpis:
        return ""
    cards = []
    for kpi in kpis:
        tone = kpi.get("tone", "ok")
        # value_text：KPI 展示字符串；超过 12 字符时降字号，避免换行导致同排卡片视觉不齐
        value_text = str(kpi.get("value", ""))
        value_class = "v sm" if len(value_text) > 12 else "v"
        # highlighted：全局最优卡高亮；高亮时不写行内描边色，交由 .kpi.hl 的 2px 绿描边接管
        highlighted = bool(kpi.get("highlight"))
        card_class = "kpi hl" if highlighted else "kpi"
        border_style = "" if highlighted else f' style="border-color:{TONE_BG.get(tone, LINE)}"'
        note_html = f'<div class="n">{esc(kpi.get("note", ""))}</div>' if kpi.get("note") else ""
        cards.append(
            f'<div class="{card_class}"{border_style}>'
            f'<div class="l">{esc(kpi.get("label", ""))}</div>'
            f'<div class="{value_class}" style="color:{TONE_COLORS.get(tone, INK)}">'
            f'{esc(value_text)}</div>{note_html}</div>'
        )
    return f'<div class="kpis">{"".join(cards)}</div>'


def render_table(table) -> str:
    """渲染明细表（表头固定、自动布局、合计行、按列截断与状态标签）。

    Args:
        table: 表格规格 dict：title（区块标题，可选）、columns（列名列表）、
            rows（行数据二维列表）、footer（合计行字符串数组，可选）、
            layout（auto/compact/wrap，可选，默认 auto）、
            truncate（{列名: 最大字符数}，可选，默认不启用）、
            tags（[{column, map}] 状态标签规则，可选：命中 map 的值渲染为 ok/warn/danger 标签）。
    Returns:
        明细表 HTML 片段；规格缺失或无列名时返回空串。
    """
    if not table or not table.get("columns"):
        return ""
    columns = table["columns"]
    rows = table.get("rows", []) or []
    footer = table.get("footer", []) or []
    truncate_map = table.get("truncate", {}) or {}
    # tag_maps：列名 → 值映射；列名不存在或规则结构非法的项直接忽略（tolerant，不报错）
    tag_maps = {}
    for rule in table.get("tags", []) or []:
        if isinstance(rule, dict) and rule.get("column") in columns and isinstance(rule.get("map"), dict):
            tag_maps[rule["column"]] = rule["map"]
    layout = _evaluate_layout(table)
    head = "".join(f'<th scope="col">{esc(column)}</th>' for column in columns)
    body = []
    for row in rows:
        cells = "".join(
            _render_cell(value, truncate_map.get(columns[column_index]),
                         tag_maps.get(columns[column_index]))
            for column_index, value in enumerate(row[:len(columns)])
        )
        body.append(f"<tr>{cells}</tr>")
    foot = ""
    if footer:
        # foot_cells：合计行按列顺序补齐，缺位补空单元格，保证与表头列数一致
        foot_cells = "".join(
            _render_cell(footer[column_index] if column_index < len(footer) else "",
                         truncate_map.get(column), tag_maps.get(column))
            for column_index, column in enumerate(columns)
        )
        foot = f"<tfoot><tr>{foot_cells}</tr></tfoot>"
    title = table.get("title", "")
    head_title = f'<div class="sec-label">{esc(title)}</div>' if title else ""
    # wrapper_class：compact=全表不换行 + 横向滚动；wrap=允许换行、不滚动
    wrapper_class = "table-wrap compact" if layout == "compact" else "table-wrap wrap"
    return (f"{head_title}<div class=\"{wrapper_class}\"><table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody>{foot}</table></div>")


def render_tables(spec) -> str:
    """渲染单表与多表序列：table 在前，tables 按顺序随后，表间保留固定垂直间距。

    Args:
        spec: 整份看板规格 dict：table 单表（可选）；tables 多表数组（可选，每项结构同 table）。
    Returns:
        表格区块 HTML 片段；无表或全部表规格为空时返回空串。
    """
    # blocks：按渲染顺序收集的表格 HTML（单表在前，多表按数组顺序）
    blocks = []
    single_table = render_table(spec.get("table"))
    if single_table:
        blocks.append(single_table)
    for table in spec.get("tables") or []:
        table_html = render_table(table)
        if table_html:
            blocks.append(table_html)
    if not blocks:
        return ""
    # 表间插入固定高度占位，避免下一张表的标题/表头紧贴上一张表的合计行
    gap = f'<div style="height:{TABLE_GAP_PX}px"></div>'
    return gap.join(blocks)


# ===========三、整页组装与规格校验==========
class SpecValidationError(ValueError):
    """规格结构 / 空数据 / 数值校验失败时抛出；消息逐条列全部问题，入口层以退出码 2 终止。"""


def _chart_data_problem(chart) -> str:
    """返回单张图的空数据问题描述；数据充分时返回空串。

    Args:
        chart: 单图规格 dict（type/categories/series/items/rows 等）。
    Returns:
        中文问题描述；无问题时返回空串。
    """
    chart_type = chart.get("type", "bar")
    if chart_type in ("bar", "hbar", "stacked"):
        if not chart.get("categories") or not chart.get("series"):
            return "缺少 categories 或 series 为空"
    elif chart_type == "line":
        if len(chart.get("categories") or []) < 2:
            return "categories 少于 2 个（折线图至少需要 2 个横轴点）"
        if not chart.get("series"):
            return "series 为空"
    elif chart_type in ("donut", "progress", "waterfall"):
        if not chart.get("items"):
            return "缺少 items"
    elif chart_type == "heatmap":
        if not chart.get("rows") or not chart.get("cols") or not chart.get("values"):
            return "缺少 rows/cols/values"
    elif chart_type == "scatter":
        if not chart.get("points"):
            return "缺少 points"
    elif chart_type == "dual":
        if not chart.get("categories") or not chart.get("bars"):
            return "缺少 categories 或 bars"
    elif chart_type == "radar":
        if len(chart.get("axes") or []) < 3:
            return "axes 少于 3 维"
        if not chart.get("series"):
            return "series 为空"
    elif chart_type == "gantt":
        rows = chart.get("rows") or []
        if not rows:
            return "缺少 rows"
        if not any(_parse_day(row.get("start")) and _parse_day(row.get("end"))
                   for row in rows if isinstance(row, dict)):
            return "rows 的日期全部无法解析"
    elif chart_type == "tree":
        nodes = chart.get("nodes") or []
        if not nodes:
            return "缺少 nodes"
        # direction：仅支持 vertical（默认）/ horizontal；非法值直接报错
        direction = chart.get("direction", "vertical")
        if direction not in ("vertical", "horizontal"):
            return f'direction 仅支持 "vertical" / "horizontal"，当前为 {direction!r}'
        if len(nodes) > TREE_MAX_NODES:
            return f"节点 {len(nodes)} 个超过上限 {TREE_MAX_NODES}（请拆图或汇总）"
        try:
            layout = build_tree_chart_layout(nodes, direction=direction)
        except TreeLayoutError as error:
            return str(error)
        if layout["level_count"] > TREE_MAX_DEPTH:
            return f"层深 {layout['level_count']} 超过上限 {TREE_MAX_DEPTH}（请拆图或汇总）"
    return ""


def validate_spec(spec) -> None:
    """组装前一次性校验规格：容器、图型注册、空图数据、负值与非法数值。

    Args:
        spec: 整份看板规格 dict（结构见文件头 SPEC 说明）。
    Returns:
        None：全部校验通过时静默返回。
    Raises:
        EmptyChartDataError: 仅存在空图数据问题时抛出（消息逐条列全部空图）。
        SpecValidationError: 规格顶层不是对象、charts / tables 不是列表，或存在容器 /
            未注册图型 / 数值问题（可与空图数据问题合并）时抛出；消息逐条列出全部问题（一次列全）。
    """
    if not isinstance(spec, dict):
        raise SpecValidationError("规格 JSON 顶层必须为对象（{...}）")
    charts = spec.get("charts", [])
    if not isinstance(charts, list):
        raise SpecValidationError(f"charts 必须为列表，当前为 {type(charts).__name__}")
    # container_problems：容器 / 未注册图型问题；empty_problems：空图数据问题
    container_problems = []
    empty_problems = []
    # chart_objects：类型合法的单图规格；含非对象项时跳过数值校验，避免误读
    chart_objects = []
    for chart_index, chart in enumerate(charts):
        if not isinstance(chart, dict):
            container_problems.append(f"charts[{chart_index}] 必须为对象，当前为 {type(chart).__name__}")
            continue
        chart_objects.append(chart)
        chart_type = chart.get("type", "bar")
        if chart_type not in RENDERERS:
            container_problems.append(
                f'charts[{chart_index}] 图「{chart.get("title", "")}」的图型 "{chart_type}" 未注册'
            )
            continue
        data_problem = _chart_data_problem(chart)
        if data_problem:
            empty_problems.append(
                f'charts[{chart_index}] 图「{chart.get("title", "")}」[{chart_type}] {data_problem}'
            )
    # tables_problems：多表容器与缺列问题（tables 非数组、表项非对象或缺 columns）
    tables_problems = []
    tables = spec.get("tables")
    if tables is not None:
        if not isinstance(tables, list):
            tables_problems.append(f"tables 必须为列表，当前为 {type(tables).__name__}")
        else:
            for table_index, table in enumerate(tables):
                if not isinstance(table, dict):
                    tables_problems.append(
                        f"tables[{table_index}] 必须为对象，当前为 {type(table).__name__}"
                    )
                elif not table.get("columns"):
                    tables_problems.append(f"tables[{table_index}] 缺少 columns")
    # numeric_problems：负值与非法数值；容器全部合法时统一校验，异常消息并入同一份问题清单
    numeric_problems = []
    if len(chart_objects) == len(charts):
        try:
            validate_non_negative({"charts": chart_objects})
        except (NegativeValueError, InvalidNumberError) as error:
            numeric_problems.append(str(error))
    # 全部问题一次列全；仅空图数据时抛 EmptyChartDataError，其余组合抛 SpecValidationError
    problems = container_problems + tables_problems + empty_problems + numeric_problems
    if problems:
        message = (
            f"规格校验失败（{len(problems)} 项），已终止渲染（未生成 HTML）：\n"
            + "\n".join(problems)
            + f"\n已支持图型：{' / '.join(RENDERERS)}；一次性表达请改用 type:\"svg\" 逃生舱。"
        )
        if empty_problems and not container_problems and not tables_problems and not numeric_problems:
            raise EmptyChartDataError(message)
        raise SpecValidationError(message)


def _render_page_body(spec) -> str:
    """渲染页面主体：结论 → KPI → 图 → 明细 → 洞察 → 页脚（完整文档与片段共用）。

    Args:
        spec: 整份看板规格 dict（结构见文件头 SPEC 说明）。
    Returns:
        `<div class="wrap">…</div>` 页面主体 HTML（等价于完整文档 <body> 内的全部内容）。
    Raises:
        SpecValidationError: 组装前校验发现结构 / 数值问题时抛出（不渲染任何内容）。
        EmptyChartDataError: 渲染器返回空内容时抛出（校验漏网兜底，不静默跳卡）。
    """
    #   1. 组装前校验（fail-fast：一次列全全部问题，不修数、不跳过、不落盘）
    validate_spec(spec)

    #   2. 逐区块渲染
    conclusion = spec.get("conclusion", [])
    concl_html = ""
    if conclusion:
        items = "".join(f"<p>{esc(item)}</p>" for item in conclusion)
        concl_html = f'<div class="concl">{items}</div>'

    charts = []
    for chart in spec.get("charts", []):
        renderer = RENDERERS[chart.get("type", "bar")]
        svg = renderer(chart)
        if not svg:
            raise EmptyChartDataError(
                f'图「{chart.get("title", "")}」[{chart.get("type", "bar")}] 渲染结果为空，'
                "已终止渲染（未生成 HTML）；请补全该图数据"
            )
        charts.append(
            f'<div class="card"><h3>{esc(chart.get("title", ""))}</h3>'
            f'{_chart_note_html(chart)}{svg}</div>'
        )
    chart_html = f'<div class="charts">{"".join(charts)}</div>' if charts else ""

    insight = spec.get("insight", "")
    insight_html = f'<div class="insight">{esc(insight)}</div>' if insight else ""
    footer = (f'数据来源与口径：{esc(spec.get("subtitle", "见各图标注"))}'
              f'｜由 render_dashboard v{SCRIPT_VERSION} 生成')

    #   3. 拼接页面主体（不含文档骨架，完整文档与宿主片段共用同一份内容）
    return (
        '<div class="wrap">'
        f'<h1>{esc(spec.get("title", "数据看板"))}</h1>'
        f'<p class="sub">{esc(spec.get("subtitle", ""))}</p>'
        f'{concl_html}{render_kpis(spec.get("kpis"))}'
        f'{chart_html}{render_tables(spec)}'
        f'{insight_html}<footer>{footer}</footer></div>'
    )


def render_html(spec) -> str:
    """组装完整自包含 HTML 文档：文档骨架 + 页面主体（样式内联）。

    Args:
        spec: 整份看板规格 dict（结构见文件头 SPEC 说明）。
    Returns:
        完整 HTML 文档字符串（含 DOCTYPE/html/head/body）。
    Raises:
        SpecValidationError: 组装前校验发现结构 / 数值问题时抛出（不渲染任何内容）。
        EmptyChartDataError: 渲染器返回空内容时抛出（校验漏网兜底，不静默跳卡）。
    """
    return (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(spec.get("title", "数据看板"))}</title><style>{CSS}</style></head><body>'
        f'{_render_page_body(spec)}</body></html>'
    )


def render_fragment(spec) -> str:
    """渲染可嵌入宿主 widget 的 HTML 片段：内联样式 + 页面主体（无文档骨架）。

    Args:
        spec: 整份看板规格 dict（结构见文件头 SPEC 说明）。
    Returns:
        片段 HTML：`<style>…</style>` + `<div class="wrap">…</div>`；不含 DOCTYPE / html /
        head / body / title / meta，样式与页面主体均复用完整文档的同一套渲染逻辑。
    Raises:
        SpecValidationError: 组装前校验发现结构 / 数值问题时抛出（不渲染任何内容）。
        EmptyChartDataError: 渲染器返回空内容时抛出（校验漏网兜底，不静默跳卡）。
    """
    return f"<style>{CSS}</style>{_render_page_body(spec)}"


# ===========四、图型自描述（--list-types / --example）==========
# TYPE_META：图型名 → (必需字段, 一句话用途)；顺序与 RENDERERS 注册顺序一致
TYPE_META = {
    "bar": ("categories、series", "竖向柱状图：分类对比、多系列分组"),
    "hbar": ("categories、series", "横向条形图：长分类名、Top N、多系列横向对比"),
    "line": ("categories（≥2）、series", "折线趋势图：类目等距的多点走势"),
    "donut": ("items", "环形占比图：整体=100% 的构成拆解"),
    "stacked": ("categories、series", "堆叠柱状图：分类内部的构成拆解"),
    "heatmap": ("rows、cols、values", "矩阵热力图：行×列二维数值矩阵"),
    "progress": ("items", "进度条对比：达成值与目标位刻度"),
    "scatter": ("points", "散点图：数值横轴、阈值象限、点标签"),
    "dual": ("categories、bars", "双轴图：柱=数量、线=比率（line 可选）"),
    "radar": ("axes（≥3）、series", "雷达图：方案多维对比"),
    "gantt": ("rows", "甘特时间轴：排期、到货跟踪"),
    "tree": ("nodes", "树状分层图：BOM/层级结构，按 parent 自上而下分层"),
    "waterfall": ("items", "瀑布桥图：从总量逐项增减到净结果（允许负值）"),
    "svg": ("svg", "逃生舱：模型手写单图 SVG，脚本原样嵌入"),
}

# EXAMPLE_SPECS：图型名 → 最小可渲染规格（含 _note 中文说明，可直接重定向后交给 --spec）
EXAMPLE_SPECS = {
    "bar": {"_note": "bar：竖向柱状图；categories 为横轴分类，series 每条含 name 与等长 values",
            "charts": [{"type": "bar", "title": "bar 最小示例", "categories": ["分类A", "分类B"],
                        "series": [{"name": "示例指标", "values": [120, 80]}]}]},
    "hbar": {"_note": "hbar：横向条形图；多系列时每个分类一组横条，colors 可按条目覆盖颜色",
             "charts": [{"type": "hbar", "title": "hbar 最小示例", "categories": ["分类A", "分类B"],
                         "series": [{"name": "系列一", "values": [120, 80]},
                                    {"name": "系列二", "values": [90, 40]}]}]},
    "line": {"_note": "line：折线趋势图；categories 至少 2 个，series 各含等长 values",
             "charts": [{"type": "line", "title": "line 最小示例", "categories": ["1月", "2月"],
                         "series": [{"name": "示例指标", "values": [80, 90]}]}]},
    "donut": {"_note": "donut：环形占比图；items 每项含 label 与 value",
              "charts": [{"type": "donut", "title": "donut 最小示例",
                          "items": [{"label": "正常", "value": 70}, {"label": "告警", "value": 30}]}]},
    "stacked": {"_note": "stacked：堆叠柱状图；series 各含 name 与等长 values（自上而下堆叠）",
                "charts": [{"type": "stacked", "title": "stacked 最小示例", "categories": ["分类A"],
                            "series": [{"name": "高", "values": [40]},
                                       {"name": "低", "values": [60]}]}]},
    "heatmap": {"_note": "heatmap：矩阵热力图；values 为 rows × cols 的二维数值矩阵（0 合法）",
                "charts": [{"type": "heatmap", "title": "heatmap 最小示例", "rows": ["行1"],
                            "cols": ["列1", "列2"], "values": [[12, 0]]}]},
    "progress": {"_note": "progress：进度条对比；items 每项含 label、value 与可选 target/unit",
                 "charts": [{"type": "progress", "title": "progress 最小示例",
                             "items": [{"label": "维度一", "value": 86, "target": 95, "unit": "%"}]}]},
    "scatter": {"_note": "scatter：散点图；points 每项含 x/y 与可选 label/group，thresholds 为象限线",
                "charts": [{"type": "scatter", "title": "scatter 最小示例",
                            "points": [{"x": 4, "y": 30, "label": "点A"},
                                       {"x": 8, "y": 60, "label": "点B"}],
                            "thresholds": {"x": 6, "y": 45}}]},
    "dual": {"_note": "dual：双轴图；categories + bars 必填，line 可选（柱=数量、线=比率）",
             "charts": [{"type": "dual", "title": "dual 最小示例", "categories": ["W1", "W2"],
                         "bars": {"name": "缺口量", "values": [120, 80]},
                         "line": {"name": "达成率", "values": [78, 86]}}]},
    "radar": {"_note": "radar：雷达图；axes 至少 3 维，series 各含等长 values，max 为满分",
              "charts": [{"type": "radar", "title": "radar 最小示例", "axes": ["成本", "时效", "齐套率"],
                          "series": [{"name": "方案A", "values": [80, 60, 90]}], "max": 100}]},
    "gantt": {"_note": "gantt：甘特时间轴；rows 每项含 label、start、end 与可选 status/note",
              "charts": [{"type": "gantt", "title": "gantt 最小示例",
                          "rows": [{"label": "PO-1", "start": "2026-11-01", "end": "2026-11-05",
                                    "status": "done", "note": "已到货"}]}]},
    "tree": {"_note": "tree：树状分层图；nodes 每项含 id、label、value 与可选 parent（无 parent 为根，可多根）",
             "charts": [{"type": "tree", "title": "tree 最小示例", "unit": "件",
                         "nodes": [{"id": "root", "label": "示例根产品（ROOT-1）", "value": 100},
                                   {"id": "child", "label": "示例子件（C-01）", "value": 60,
                                    "parent": "root"}]}]},
    "waterfall": {"_note": "waterfall：瀑布桥图；items 每项含 label、value 与 kind"
                           "（total 从 0 画到 value，delta 在累计上增减）",
                  "charts": [{"type": "waterfall", "title": "waterfall 最小示例", "unit": "件",
                              "items": [{"label": "毛需求", "value": 100, "kind": "total"},
                                        {"label": "现货分配", "value": -40, "kind": "delta"},
                                        {"label": "净缺口", "value": 60, "kind": "total"}]}]},
    "svg": {"_note": "svg：逃生舱；svg 字段为模型手写的 <svg> 片段，脚本原样嵌入、不解析",
            "charts": [{"type": "svg", "title": "svg 最小示例",
                        "svg": '<svg viewBox="0 0 660 60" width="100%"><rect x="10" y="10" '
                               'width="40" height="40" rx="4" fill="#378ADD"/></svg>'}]},
}


def print_types() -> None:
    """打印全部已注册图型（每行：图型 ｜ 必需字段 ｜ 一句话用途）。

    Returns:
        None。
    """
    for chart_type, (required_fields, purpose) in TYPE_META.items():
        print(f"{chart_type} ｜ {required_fields} ｜ {purpose}")


def print_example(chart_type: str) -> None:
    """打印指定图型的最小可渲染规格 JSON（含 _note 中文说明）。

    Args:
        chart_type: 图型名（须在 TYPE_META 内）。
    Returns:
        None。
    Raises:
        SystemExit: 图型未知时向 stderr 列出可用图型并以退出码 2 退出。
    """
    example = EXAMPLE_SPECS.get(chart_type)
    if example is None:
        print(f"未知图型：{chart_type}；可用图型：{' / '.join(TYPE_META)}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(example, ensure_ascii=False, indent=2))


# ===========五、命令行入口==========
def main() -> None:
    """命令行入口：读规格 JSON → 校验并渲染 HTML → 落盘 → 打印路径与耗时。

    Returns:
        None。
    Raises:
        SystemExit: 规格不可读 / JSON 无法解析 / 校验失败时向 stderr 输出中文报错并以退出码 2 退出，
            不建目录、不落盘；参数缺失或互斥参数同时给出时由 argparse 以退出码 2 退出。
    """
    parser = argparse.ArgumentParser(description="按规格 JSON 渲染自包含 HTML 看板")
    parser.add_argument("--spec", default=None,
                        help="图表规格 JSON 文件路径；传 - 表示从 stdin 读取 UTF-8 JSON")
    parser.add_argument("--out", default=None, help="输出 HTML 路径（缺省 deliverables/<slug>.html）")
    parser.add_argument("--fragment", action="store_true",
                        help="输出可嵌入宿主的 HTML 片段（style + 页面主体，不含文档骨架）")
    parser.add_argument("--quiet", action="store_true",
                        help="只打印输出路径，便于脚本串联（--fragment 下不生效）")
    parser.add_argument("--list-types", action="store_true", help="列出 14 种图型、必需字段与用途后退出")
    parser.add_argument("--example", metavar="TYPE", default=None, help="打印指定图型的最小可渲染规格 JSON 后退出")
    parser.add_argument("--mirror", metavar="DIR", default=None, help="正常落盘后再复制一份 HTML 到指定目录")
    args = parser.parse_args()

    #   1. 自描述命令：不读规格，直接输出后退出（--list-types 与 --spec 同时给出时优先）
    if args.list_types:
        print_types()
        return
    if args.example:
        if args.spec:
            parser.error("--example 与 --spec 不能同时使用")
        print_example(args.example)
        return
    if not args.spec:
        parser.error("缺少 --spec（或用 --list-types / --example 查看图型与最小规格）")

    #   2. 读取并解析规格（--spec - 从 stdin 读 UTF-8 JSON；失败给中文提示，不裸抛 traceback）
    started = time.perf_counter()
    if args.spec == "-":
        spec_source = "stdin（--spec -）"
        try:
            spec_text = sys.stdin.buffer.read().decode("utf-8")
        except UnicodeDecodeError as error:
            print(f"规格 stdin 无法按 UTF-8 解码：{spec_source}（{error}）", file=sys.stderr)
            sys.exit(2)
        if not spec_text.strip():
            print(f"规格 stdin 为空：{spec_source}（请通过管道或重定向传入 JSON）", file=sys.stderr)
            sys.exit(2)
    else:
        spec_path = Path(args.spec).resolve()
        spec_source = str(spec_path)
        try:
            spec_text = spec_path.read_text(encoding="utf-8")
        except OSError as error:
            print(f"规格文件无法读取：{spec_path}（{error.strerror or error}）", file=sys.stderr)
            sys.exit(2)
    try:
        spec = json.loads(spec_text)
    except json.JSONDecodeError as error:
        print(f"规格 JSON 无法解析：{spec_source}"
              f"（{error.msg}，第 {error.lineno} 行第 {error.colno} 列）", file=sys.stderr)
        sys.exit(2)

    #   3. 校验并渲染：结构 / 图型 / 空数据 / 负值 / 非法数值任一失败即报错退出，此前不落盘
    try:
        html = render_fragment(spec) if args.fragment else render_html(spec)
    except (SpecValidationError, EmptyChartDataError, InvalidNumberError) as error:
        print(f"====规格校验失败（{type(error).__name__}）====: {spec_source}", file=sys.stderr)
        print(error, file=sys.stderr)
        sys.exit(2)

    #   4. 片段模式：--out 落文件并在 stdout 打印路径；否则片段直接打印到 stdout（日志不混入）
    if args.fragment:
        if args.mirror:
            print("--fragment 模式忽略 --mirror（片段不落档）", file=sys.stderr)
        if args.out:
            out_path = Path(args.out).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            print(out_path)
        else:
            print(html)
        return

    #   5. 确定输出路径并落盘（--mirror 时再复制一份，目录不存在则创建）
    if args.out:
        out_path = Path(args.out).resolve()
    else:
        # slug：由看板标题生成的文件名（非字词字符折叠为连字符）
        slug = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", spec.get("title", "dashboard")).strip("-")
        out_path = Path.cwd() / "deliverables" / f"{slug or 'dashboard'}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    # mirror_path：内联投递副本的绝对路径（未启用 --mirror 时为 None）
    mirror_path = None
    if args.mirror:
        mirror_dir = Path(args.mirror).resolve()
        mirror_dir.mkdir(parents=True, exist_ok=True)
        mirror_path = mirror_dir / out_path.name
        if mirror_path != out_path:
            shutil.copyfile(out_path, mirror_path)
    elapsed_ms = (time.perf_counter() - started) * 1000

    #   6. 打印结果（--mirror 时额外打印「落档」「内联」两行绝对路径）
    if args.quiet:
        if mirror_path:
            print(f"落档：{out_path}")
            print(f"内联：{mirror_path}")
        else:
            print(out_path)
        return
    chart_count = len(spec.get("charts", []))
    print(f"====看板已生成====: {out_path}")
    print(f"图数: {chart_count} ｜ HTML: {len(html) / 1024:.1f} KB ｜ 渲染耗时: {elapsed_ms:.0f} ms")
    if mirror_path:
        print(f"落档：{out_path}")
        print(f"内联：{mirror_path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()

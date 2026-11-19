"""按图表规格 JSON 渲染自包含 HTML 看板（零依赖、内联 SVG）。

设计目的：把「出图」从模型手写 SVG/HTML（每图数千 token 输出，耗时数十秒）
改为「模型只产规格 JSON（约数百 token）+ 脚本确定性渲染（毫秒级）」。
数值由脚本直写进图元，天然满足「图上数值 = 工具返回值、同源不重算」的数据纪律。
图元渲染层位于同目录：chart_renderers（样式/工具/基础图型/负值校验）、
chart_renderers_ext（构成与达成图型 + 图型注册表）、chart_renderers_adv（高级图型）。

主要 Input：--spec 规格 JSON 文件路径（必填，结构见下方 SPEC 说明）；
--out 输出 HTML 路径（可选，缺省 deliverables/<slug>.html，相对当前工作目录）；
--quiet 只打印输出路径（可选，便于脚本串联）。
主要 Output：自包含单文件 HTML（内联 CSS/SVG，无外部依赖），stdout 打印路径与耗时；
规格含负值时不渲染、不落盘，stderr 输出中文报错并以退出码 2 退出。

SPEC 结构（除 title 外均可选）：
{
  "title": "仓群库存风险总览",
  "subtitle": "来源：InventoryRisk（demo 环境）｜2026-11-09",
  "conclusion": ["P0 仓 2 个，占总风险金额 61%", "..."],
  "kpis": [{"label": "P0 仓", "value": "2", "tone": "danger"}],
  "charts": [
    {"type": "bar",  "title": "...", "unit": "万元", "categories": ["A","B"],
     "series": [{"name": "风险金额", "values": [1,2]}]},
    {"type": "hbar", "title": "...", "unit": "件", "categories": ["A","B"],
     "series": [{"name": "缺货量", "values": [1,2]}]},
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
     "thresholds": {"x": 8, "y": 50}},
    {"type": "dual","title": "缺口量 vs 齐套率", "categories": ["W1"],
     "bars": {"name":"缺口","values":[120]}, "bar_unit": "件",
     "line": {"name":"齐套率","values":[78]}, "line_unit": "%"},
    {"type": "radar","title": "方案对比", "axes": ["成本","时效","齐套率"],
     "series": [{"name":"方案A","values":[80,60,90]}], "max": 100},
    {"type": "gantt","title": "到货排期", "today": "2026-11-08",
     "rows": [{"label":"PO-1001","start":"2026-10-28","end":"2026-11-04","status":"done","note":"已到货"}]},
    {"type": "svg", "title": "一次表达（模型手写）", "svg": "<svg ...>...</svg>"}
  ],
  "table": {"title": "明细", "columns": ["仓", "等级"], "rows": [["A", "P0"]]},
  "insight": "洞察结语"
}
tone 取值：ok（正常/通过）｜warn（待核查）｜danger（告警/不通过）。
逐条着色：bar / hbar / stacked 的 series 内可用 colors 数组按条目着色（如 Top N 缺货条目视觉强调），
推荐语义色 红 #E24B4A（告警/缺货）｜黄 #EF9F27（待核查）｜绿 #1D9E75（正常/通过）。
标签与图例：分类标签过长自动截断但**保留结尾「（编码）」段**；series.name 图例超长约 12 字符会被截断——
环境、分支等关键口径不要只放图例，放图标题或明细表。看板页脚的「生成日」由模型写入 subtitle。
图型口径：type 须为上述已注册图型之一；未注册图型同样不渲染、不落盘，stderr 报错并以退出码 2 退出——图库未覆盖的一次性表达请改用 "svg" 逃生舱。
数值口径：除 gantt（纯日期）与 svg 逃生舱外，图表内全部数值须 ≥ 0（0 合法）；
出现负值时脚本不渲染、不落盘，stderr 报错并以退出码 2 退出。
差额/增减类数据请拆成『方向 + 绝对值』两列，或在明细表中呈现。
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from chart_renderers import (
    FONT,
    INK,
    LINE,
    TONE_BG,
    TONE_COLORS,
    NegativeValueError,
    esc,
    validate_non_negative,
)
from chart_renderers_ext import RENDERERS


# ===========一、版本与页面样式==========
# SCRIPT_VERSION：脚本版本号（写入页脚，便于追溯产物由哪版脚本生成）
SCRIPT_VERSION = "1.1.1"

# CSS：看板内联样式表（单文件自包含；%FONT% 占位符替换为渲染层同源字体栈）
CSS = """
*{box-sizing:border-box}
body{margin:0;padding:28px 24px 40px;background:#fff;color:#1F2328;font-family:%FONT%;
     font-size:14px;line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto}
h1{font-size:21px;font-weight:600;margin:0 0 6px;letter-spacing:.2px}
.sub{font-size:12px;color:#8B9099;margin:0 0 18px}
.sec-label{font-size:12px;font-weight:600;color:#8B9099;letter-spacing:.6px;margin:26px 0 10px}
.concl{background:#F7F8FA;border-left:3px solid #378ADD;border-radius:4px;padding:12px 16px;margin:0 0 18px}
.concl p{margin:3px 0;font-size:13.5px}
.kpis{display:flex;flex-wrap:wrap;gap:10px}
.kpi{flex:1 1 150px;border:1px solid #E3E5E8;border-radius:10px;padding:12px 14px}
.kpi .l{font-size:12px;color:#5F6368}
.kpi .v{font-size:22px;font-weight:600;margin-top:4px;font-variant-numeric:tabular-nums}
.charts{display:flex;flex-wrap:wrap;gap:14px}
.card{flex:1 1 460px;border:1px solid #E3E5E8;border-radius:10px;padding:14px 12px 8px;min-width:0}
.card h3{font-size:13px;font-weight:600;margin:0 0 2px;padding-left:4px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid #EEF0F2;padding:8px 10px;text-align:left;vertical-align:top}
th{font-size:12px;color:#5F6368;font-weight:600;background:#FAFBFC;white-space:nowrap}
td.num{font-variant-numeric:tabular-nums;text-align:right}
td:first-child{white-space:nowrap}
.insight{margin-top:22px;padding:12px 16px;border:1px dashed #D6D9DE;border-radius:8px;font-size:13px;color:#3D434B}
footer{margin-top:26px;font-size:11.5px;color:#A0A5AC;border-top:1px solid #EEF0F2;padding-top:10px}
""".replace("%FONT%", FONT)


# ===========二、页面区块渲染==========
def render_kpis(kpis) -> str:
    """渲染 KPI 卡片组。

    Args:
        kpis: KPI 规格列表，每项含 label（标签）、value（展示字符串，不做数值校验）、
            tone（语义色 ok/warn/danger，缺省 ok）。
    Returns:
        KPI 卡片组 HTML 片段；列表为空时返回空串。
    """
    if not kpis:
        return ""
    cards = []
    for kpi in kpis:
        tone = kpi.get("tone", "ok")
        cards.append(
            f'<div class="kpi" style="border-color:{TONE_BG.get(tone, LINE)}">'
            f'<div class="l">{esc(kpi.get("label", ""))}</div>'
            f'<div class="v" style="color:{TONE_COLORS.get(tone, INK)}">'
            f'{esc(kpi.get("value", ""))}</div></div>'
        )
    return f'<div class="kpis">{"".join(cards)}</div>'


def render_table(table) -> str:
    """渲染明细表。

    Args:
        table: 表格规格 dict：title（区块标题，可选）、columns（列名列表）、
            rows（行数据二维列表；纯数字/百分比单元格右对齐）。
    Returns:
        明细表 HTML 片段；规格缺失或无列名时返回空串。
    """
    if not table or not table.get("columns"):
        return ""
    head = "".join(f"<th>{esc(c)}</th>" for c in table["columns"])
    body = []
    for row in table.get("rows", []):
        cells = []
        for value in row:
            raw = str(value)
            # 纯数字/百分比单元格加 num 类，按数值列右对齐
            cls = ' class="num"' if re.fullmatch(r"-?[\d,.]+%?", raw) else ""
            cells.append(f"<td{cls}>{esc(raw)}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    title = table.get("title", "")
    head_title = f'<div class="sec-label">{esc(title)}</div>' if title else ""
    return (f"{head_title}<table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table>")


# ===========三、整页组装==========
# UnknownChartTypeError：图型未注册的规格校验异常（静默回退画成 bar 属歪曲表达，改为报错拦截）
class UnknownChartTypeError(ValueError):
    """规格 charts 中存在 RENDERERS 未注册的图型时抛出；消息含图标题、图型名与可用图型清单。"""


def render_html(spec) -> str:
    """组装完整自包含 HTML：结论 → 口径 → KPI → 图 → 明细 → 洞察 → 页脚。

    Args:
        spec: 整份看板规格 dict（结构见文件头 SPEC 说明）。
    Returns:
        完整 HTML 文档字符串。
    Raises:
        UnknownChartTypeError: 组装前校验发现未注册图型时抛出（不渲染任何内容）。
        NegativeValueError: 组装前校验发现任一图表数值为负时抛出（不渲染任何内容）。
    """
    #   1. 组装前规格校验（fail-fast：图型未注册、数值为负，均不修数、不跳过、不落盘）
    unknown_charts = [chart for chart in spec.get("charts", [])
                      if chart.get("type", "bar") not in RENDERERS]
    if unknown_charts:
        details = "；".join(
            f'图「{chart.get("title", "")}」的图型 "{chart.get("type", "bar")}"'
            for chart in unknown_charts
        )
        raise UnknownChartTypeError(
            f"规格含 {len(unknown_charts)} 个未注册图型，已终止渲染（未生成 HTML）：{details}。"
            f"已支持：{' / '.join(RENDERERS)}；图库未覆盖的一次性表达请改用 type:\"svg\" 逃生舱。"
        )
    validate_non_negative(spec)

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
            continue
        charts.append(f'<div class="card"><h3>{esc(chart.get("title", ""))}</h3>{svg}</div>')
    chart_html = f'<div class="charts">{"".join(charts)}</div>' if charts else ""

    insight = spec.get("insight", "")
    insight_html = f'<div class="insight">{esc(insight)}</div>' if insight else ""
    footer = (f'数据来源与口径：{esc(spec.get("subtitle", "见各图标注"))}'
              f'｜由 render_dashboard v{SCRIPT_VERSION} 生成')

    #   3. 拼接整页
    return (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(spec.get("title", "数据看板"))}</title><style>{CSS}</style></head><body>'
        '<div class="wrap">'
        f'<h1>{esc(spec.get("title", "数据看板"))}</h1>'
        f'<p class="sub">{esc(spec.get("subtitle", ""))}</p>'
        f'{concl_html}{render_kpis(spec.get("kpis"))}'
        f'{chart_html}{render_table(spec.get("table"))}'
        f'{insight_html}<footer>{footer}</footer></div></body></html>'
    )


# ===========四、命令行入口==========
def main() -> None:
    """命令行入口：读规格 JSON → 校验并渲染 HTML → 落盘 → 打印路径与耗时。

    Returns:
        None。
    Raises:
        SystemExit: 规格含负值或未注册图型时向 stderr 输出中文报错并以退出码 2 退出，
            不建目录、不落盘；参数缺失时由 argparse 以退出码 2 退出。
    """
    parser = argparse.ArgumentParser(description="按规格 JSON 渲染自包含 HTML 看板")
    parser.add_argument("--spec", required=True, help="图表规格 JSON 文件路径")
    parser.add_argument("--out", default=None, help="输出 HTML 路径（缺省 deliverables/<slug>.html）")
    parser.add_argument("--quiet", action="store_true", help="只打印输出路径，便于脚本串联")
    args = parser.parse_args()

    #   1. 读取规格
    started = time.perf_counter()
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    #   2. 校验并渲染：图型未注册或数值为负即报错退出，此前不做任何落盘动作
    try:
        html = render_html(spec)
    except (NegativeValueError, UnknownChartTypeError) as error:
        print(f"====规格校验失败====: {spec_path}", file=sys.stderr)
        print(error, file=sys.stderr)
        sys.exit(2)

    #   3. 确定输出路径并落盘
    if args.out:
        out_path = Path(args.out).resolve()
    else:
        # slug：由看板标题生成的文件名（非字词字符折叠为连字符）
        slug = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", spec.get("title", "dashboard")).strip("-")
        out_path = Path.cwd() / "deliverables" / f"{slug or 'dashboard'}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    elapsed_ms = (time.perf_counter() - started) * 1000

    #   4. 打印结果
    if args.quiet:
        print(out_path)
        return
    chart_count = len(spec.get("charts", []))
    print(f"====看板已生成====: {out_path}")
    print(f"图数: {chart_count} ｜ HTML: {len(html) / 1024:.1f} KB ｜ 渲染耗时: {elapsed_ms:.0f} ms")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()

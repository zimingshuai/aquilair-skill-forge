# -*- coding: utf-8 -*-
"""轨迹断言：触发反例用例的「零工具调用」判定（trigger-negative 类机器断言）

用法（promptfoo 断言）：
    - type: python
      value: file://asserts/no_forbidden_tools.py

判定逻辑（2026-10-22 统一网关迁移后双通道，任一命中即违规）：
    1. 工具名前缀命中（旧单体服务轨迹：data-service-* 前缀，历史回放样本仍适用）；
    2. 调用参数 workspace_id 命中禁用域（新网关轨迹：fnb/mfg 共用服务名 aquilair-mcp，
       按各技能 SKILL.md 固化的 workspace UUID 区分域，跨域即违规）；
    纯文本样本（无 tool_calls 结构）视为未调用，直接通过。
返回 GradingResult（pass/score/reason）。

新增触发反例用例时在 FORBIDDEN_RULES 登记即可（领域特定映射，与转换器同思路）。
"""

import json
import re
import sys

# case_id -> 禁用规则：prefixes=旧服务名前缀（历史轨迹）；workspaces=禁用域的 workspace UUID（新网关轨迹）
FORBIDDEN_RULES = {
    # FNB_WORKSPACE_UUID：fnb 本体项目（餐饮业库存分析）UUID——餐饮域问题/开发请求不得触发
    'fnb-009': {'prefixes': ('data-service-fnb',),
                'workspaces': ('019fd9ed-8715-7000-8f28-0a14f59c5563',)},
    'fnb-016': {'prefixes': ('data-service-fnb',),
                'workspaces': ('019fd9ed-8715-7000-8f28-0a14f59c5563',)},
    # MFG_WORKSPACE_UUID：mfg 本体项目（制造业工厂调拨）UUID——制造域问题/开发请求不得触发
    'mfg-012': {'prefixes': ('data-service-mfg-sandbox',),
                'workspaces': ('01a03bb7-2da4-7000-8dcf-1fb48f6f7fc9',)},
    'mfg-013': {'prefixes': ('data-service-mfg-sandbox',),
                'workspaces': ('01a03bb7-2da4-7000-8dcf-1fb48f6f7fc9',)},
}

# 样本键后缀（-r1..r3 轮次 / -neg、-violation 负样本）——剥离后查映射，与 gen_calibration 一致
SUFFIX_RE = re.compile(r'(-r\d+|-neg|-violation)$')


def _load_trajectory(output: str) -> dict | None:
    """解析输出为轨迹 dict；纯文本样本返回 None（视为未调用任何工具）。"""
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _call_workspace(call: dict) -> str:
    """取单次调用的 workspace_id 实参（args / arguments 两种键名兼容）。"""
    params = call.get('args') or call.get('arguments') or {}
    return str(params.get('workspace_id', '')) if isinstance(params, dict) else ''


def judge_with(rule: dict, output: str, case_id: str = '') -> dict:
    """按给定禁用规则执行判定（前缀 + workspace 双通道）。

    Args:
        rule: {'prefixes': (...), 'workspaces': (...)} 禁用规则。
        output: 待判定的轨迹 JSON 字符串。
        case_id: 用例编号（用于失败原因回显）。
    Returns:
        promptfoo GradingResult dict。
    """
    data = _load_trajectory(output)
    if data is None:
        return {'pass': True, 'score': 1, 'reason': '纯文本样本（无轨迹结构），视为未调用任何工具'}

    prefixes = rule['prefixes']
    workspaces = rule.get('workspaces', ())
    calls = data.get('tool_calls') or []
    hits = []
    for call in calls:
        tool = str(call.get('tool', ''))
        #   1. 旧前缀通道：工具名含旧服务前缀（兼容全限定名与裸名）
        if any(tool.startswith(p) or p in tool for p in prefixes):
            hits.append(tool)
            continue
        #   2. workspace 通道：网关工具调用携带禁用域的 workspace_id 即跨域违规
        if workspaces and _call_workspace(call) in workspaces:
            hits.append(f'{tool}(workspace 跨域)')
    if hits:
        return {'pass': False, 'score': 0, 'reason': f'出现禁用工具调用: {", ".join(hits[:5])}'}
    return {'pass': True, 'score': 1,
            'reason': f'{len(calls)} 次调用中无禁用前缀（{", ".join(prefixes)}）'
                      f'与禁用 workspace（{", ".join(workspaces)}）命中'}


def judge(output: str, case_id: str = '') -> dict:
    """核心判定：按 case_id 查规则表并执行。"""
    rule = FORBIDDEN_RULES.get(case_id)
    if not rule:
        return {'pass': False, 'score': 0, 'reason': f'用例 {case_id} 未在 FORBIDDEN_RULES 登记'}
    return judge_with(rule, output, case_id)


def get_assert(output, context=None):
    """promptfoo python 断言入口：从 context.vars 取 case_id（自动剥离轮次/负样本后缀）。"""
    case_id = (context or {}).get('vars', {}).get('case_id', '')
    rule = FORBIDDEN_RULES.get(case_id) or FORBIDDEN_RULES.get(SUFFIX_RE.sub('', case_id))
    if not rule:
        return {'pass': False, 'score': 0, 'reason': f'用例 {case_id} 未在 FORBIDDEN_RULES 登记'}
    return judge_with(rule, output, case_id)


if __name__ == '__main__':
    # 命令行单测：python asserts/no_forbidden_tools.py '<输出JSON>' '<case_id>'
    print(json.dumps(judge(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''), ensure_ascii=False))

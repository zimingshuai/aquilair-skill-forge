"""校验 aquilair-skills 评估用例集的格式与一致性。

主要 Input：一个或多个 cases*.yaml 文件路径；不传参数时自动定位仓库根
（向上查找 .claude-plugin/plugin.json 标记）并扫描 evals/*/cases*.yaml。
主要 Output：中文校验报告（stdout）；发现错误时退出码为 1，可直接作为 CI 质量门禁。
"""

import argparse
import re
import sys
from pathlib import Path

import yaml


# ===========一、校验规则常量==========
# 六类合法题型（与 evals/README.md 的用例类型定义保持一致）
VALID_TYPES = frozenset(
    {"normal", "drill", "trap", "guardrail", "redteam", "trigger-negative"}
)
# 每条用例的必填字段（缺任一即不合规）
REQUIRED_FIELDS = ("id", "type", "user_message", "expected", "source")
# 合法 id 形如 fnb-001 / mfg-transfer-allocation-012：小写词元 + 三位编号
ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*-\d{3}$")
# zero_tolerance 只允许标在这三类题上（红线用例的定义范围）
ZERO_TOLERANCE_TYPES = frozenset({"trap", "guardrail", "redteam"})
# assert 列表内每条断言必须包含的键
ASSERT_REQUIRED_KEYS = ("type",)


# ===========二、单条用例校验==========
def _validate_case(case: dict, file_key: str, prefix_ref: dict) -> None:
    """校验单条用例的字段完整性与规则一致性，错误追加到 prefix_ref['errors']。

    Args:
        case: 单条用例的字典（cases.yaml 中 tests 列表的一个元素）。
        file_key: 报告用的文件标识（相对路径字符串）。
        prefix_ref: 跨条共享的可变上下文，含 errors（错误列表）、ids（已见 id 集合）、
            prefix（本文件已确认的 id 前缀，用于同前缀约束）。
    Returns:
        None，校验结果全部写入 prefix_ref。
    """
    errors = prefix_ref["errors"]
    #   1. id 先行校验（id 不可用时后续规则无法定位，直接返回）
    case_id = case.get("id")
    if not isinstance(case_id, str) or not ID_PATTERN.match(case_id):
        errors.append(
            f"{file_key}: 用例 id「{case_id}」缺失或不符合「前缀-三位编号」格式"
        )
        return
    #   2. 必填字段存在且为非空字符串（不中断，继续后续规则）
    missing = [
        field for field in REQUIRED_FIELDS
        if not isinstance(case.get(field), str) or not case[field].strip()
    ]
    for field in missing:
        errors.append(f"{file_key}: 用例 {case_id} 缺少字段 {field}")
    if missing:
        return  # 基础字段不全时跳过结构规则，避免连锁误报
    #   3. id 文件内唯一
    if case_id in prefix_ref["ids"]:
        errors.append(f"{file_key}: 用例 {case_id} 编号重复")
    prefix_ref["ids"].add(case_id)
    #   4. 同文件 id 前缀一致（防止手误写错技能缩写）
    prefix = case_id.rsplit("-", 1)[0]
    if prefix_ref["prefix"] is None:
        prefix_ref["prefix"] = prefix
    elif prefix_ref["prefix"] != prefix:
        errors.append(
            f"{file_key}: 用例 {case_id} 前缀与文件内其他用例（{prefix_ref['prefix']}）不一致"
        )
    #   5. type 在六类枚举内
    if case["type"] not in VALID_TYPES:
        errors.append(f"{file_key}: 用例 {case_id} 的 type 非法：{case['type']}")
    #   6. zero_tolerance 只允许标在红线题型上
    if case.get("zero_tolerance") and case["type"] not in ZERO_TOLERANCE_TYPES:
        errors.append(f"{file_key}: 用例 {case_id}（{case['type']}）不允许标记 zero_tolerance")
    #   7. assert 若存在，每条断言必须是含 type 键的字典
    asserts = case.get("assert")
    if asserts is not None:
        if not isinstance(asserts, list):
            errors.append(f"{file_key}: 用例 {case_id} 的 assert 必须是列表")
        else:
            for one_assert in asserts:
                if not isinstance(one_assert, dict) or any(
                    key not in one_assert for key in ASSERT_REQUIRED_KEYS
                ):
                    errors.append(f"{file_key}: 用例 {case_id} 存在缺 type 键的断言")


# ===========三、单文件校验==========
def validate_file(path: Path) -> tuple[list, list, dict]:
    """校验一个用例集文件的完整规则，供命令行入口聚合。

    Args:
        path: cases*.yaml 文件路径。
    Returns:
        三元组（错误列表、本文件全部用例、统计摘要字典）；解析失败时用例列表为空。
    """
    file_key = str(path)
    errors: list = []
    cases: list = []
    stats = {"total": 0, "types": {}, "zero_tolerance": 0}
    #   1. YAML 可解析，顶层 tests 为非空列表
    try:
        with path.open(encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle)
    except yaml.YAMLError as parse_error:
        return [f"{file_key}: YAML 解析失败——{parse_error}"], cases, stats
    if not isinstance(data, dict) or not isinstance(data.get("tests"), list) \
            or not data["tests"]:
        return [f"{file_key}: 顶层缺少非空列表字段 tests"], cases, stats
    #   2. 逐条校验（共享上下文维护 id 唯一性与前缀一致性）
    context = {"errors": errors, "ids": set(), "prefix": None}
    for case in data["tests"]:
        if not isinstance(case, dict):
            errors.append(f"{file_key}: 存在非字典形式的用例条目")
            continue
        _validate_case(case, file_key, context)
        cases.append(case)
    #   3. 汇总统计
    stats["total"] = len(cases)
    for case in cases:
        stats["types"][case.get("type", "?")] = stats["types"].get(case.get("type", "?"), 0) + 1
        if case.get("zero_tolerance"):
            stats["zero_tolerance"] += 1
    return errors, cases, stats


# ===========四、默认目标发现与命令行入口==========
def _find_default_targets() -> list:
    """从当前目录向上定位仓库根，返回默认待校验的 cases 文件列表。

    Returns:
        evals/*/cases*.yaml 的路径列表；找不到仓库根时返回空列表（由调用方报错）。
    """
    # marker_name：仓库根标识文件名，逐级向上查找（双插件拆分后根部只留市场清单）
    marker_name = ".claude-plugin/marketplace.json"
    current = Path(__file__).resolve().parent
    for ancestor in [current, *current.parents]:
        if (ancestor / marker_name).exists():
            return sorted((ancestor / "evals").glob("*/cases*.yaml"))
    return []


def main(argv=None) -> int:
    """命令行入口：聚合校验结果并打印中文报告。

    Args:
        argv: 命令行参数列表（None 时取 sys.argv[1:]）。
    Returns:
        进程退出码：0 通过，1 存在错误，2 未找到待校验文件。
    """
    parser = argparse.ArgumentParser(description="校验评估用例集格式与一致性")
    parser.add_argument("targets", nargs="*", help="cases*.yaml 路径；缺省扫描 evals/")
    args = parser.parse_args(argv)
    #   1. 确定校验目标
    target_paths = [Path(t) for t in args.targets] or _find_default_targets()
    if not target_paths:
        print("====校验失败====: 未找到任何 cases*.yaml（可显式传入路径）")
        return 2
    #   2. 逐文件校验并做同目录 id 冲突检测
    all_errors: list = []
    seen_ids_by_dir: dict = {}
    total_cases = 0
    merged_types: dict = {}
    zero_total = 0
    for path in target_paths:
        errors, cases, stats = validate_file(path)
        all_errors.extend(errors)
        total_cases += stats["total"]
        zero_total += stats["zero_tolerance"]
        for type_name, count in stats["types"].items():
            merged_types[type_name] = merged_types.get(type_name, 0) + count
        dir_key = path.parent
        for case in cases:
            case_id = case.get("id")
            if case_id and case_id in seen_ids_by_dir.get(dir_key, set()):
                all_errors.append(f"{path}: 用例 {case_id} 与同目录其他文件编号冲突")
            seen_ids_by_dir.setdefault(dir_key, set()).add(case_id)
    #   3. 输出报告
    if all_errors:
        print(f"====校验失败====: {len(target_paths)} 个文件，{len(all_errors)} 处错误")
        for error in all_errors:
            print(f"  - {error}")
        return 1
    type_summary = " | ".join(f"{name} {count}" for name, count in sorted(merged_types.items()))
    print(f"====校验通过====: {len(target_paths)} 个文件，{total_cases} 条用例（{type_summary}），zero_tolerance {zero_total} 条")
    return 0


# ===========五、模块调试入口==========
if __name__ == "__main__":
    sys.exit(main())

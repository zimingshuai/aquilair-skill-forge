"""技能工厂巡检（lint）：对仓库内全部技能资产做结构性体检。

主要 Input：仓库根路径（脚本位于 tools/ 下，自动取上级目录，无需参数）。
主要 Output：控制台中文巡检报告（按技能列 PASS/WARN/FAIL）+ 进程退出码
（存在 ERROR 返回 1，可挂 pre-commit / CI；仅 WARN 返回 0 不阻断）。

机检十项（语义项——矛盾/过时/术语漂移——见
skills/aquilair-skill-authoring/references/lint.md 的人工巡检清单）：
  C1  frontmatter name 与目录名一致
  C2  description 含「Use when」触发句式与边界句（not for / 不属于）
  C3  SKILL.md 行数 50~120（触发即全文加载，超限摊薄注意力）
  C4  SKILL.md 引用的 references/*.md 文件存在
  C5  references/ 下无孤儿文件（未被 SKILL.md 提及）
  C6  技能已进 README 技能清单（业务/元技能章节均可）
  C7  业务技能已进 router 路由表
  C8  业务技能有 evals/<技能名>/ 用例目录
  C9  MCP 服务双向一致（技能提及的服务在 .mcp.json；.mcp.json 无死服务）
  C10 业务技能 references 含出处标注（来源：/出处，新纪律渐进达标）
  C11 域知识库健康检查（aquilair-knowledge/sources/ 每域：编译层三件齐
      ——glossary/index/log，且编译层页面含出处标注；无来源页面即发现，代码判定）
"""

import json
import re
import sys
from pathlib import Path

# LEVEL_ERROR / LEVEL_WARN：问题级别——ERROR 阻断（退出码 1），WARN 仅提示
LEVEL_ERROR = "ERROR"
LEVEL_WARN = "WARN"
# LINE_MIN / LINE_MAX：SKILL.md 行数纪律区间（aquilair-skill-authoring 第 4 步，2026-09-28 上限由 80 调至 120）
LINE_MIN, LINE_MAX = 50, 120
# REF_PATTERN：SKILL.md 中 references 文件引用的提取正则
REF_PATTERN = re.compile(r"references/([\w.-]+\.md)")
# SERVICE_PATTERN：技能文本中 data-service-* 服务名的提取正则
SERVICE_PATTERN = re.compile(r"data-service-[a-z0-9-]+")
# BACKTICK_PATTERN：README 中反引号技能名候选的提取正则
BACKTICK_PATTERN = re.compile(r"`([a-z0-9][a-z0-9-]+)`")


def parse_frontmatter(skill_text: str) -> dict[str, str]:
    """解析 SKILL.md 的 frontmatter 键值对（不引 yaml 依赖，零第三方库）。

    Args:
        skill_text: SKILL.md 全文。
    Returns:
        frontmatter 键值字典；无 frontmatter 时返回空字典。
    """
    if not skill_text.startswith("---"):
        return {}
    # fm_block：首对 --- 之间的 frontmatter 原文
    parts = skill_text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm_block = parts[1]
    result: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def parse_readme_categories(readme_text: str, known_skills: set[str]) -> tuple[set[str], set[str]]:
    """从 README 的业务/元技能两章节解析技能分类（README 是分类唯一事实源）。

    Args:
        readme_text: README.md 全文。
        known_skills: skills/ 下实际存在的技能目录名集合，用于过滤非技能反引号词。
    Returns:
        (业务技能名集合, 元技能名集合)。
    """
    # sections：按标题切分 README，携带各自标题行
    sections = re.split(r"(?m)^#{2,3} .+$", readme_text)
    headings = re.findall(r"(?m)^#{2,3} (.+)$", readme_text)
    business: set[str] = set()
    meta: set[str] = set()
    for heading, body in zip(headings, sections[1:]):
        names = {m for m in BACKTICK_PATTERN.findall(body) if m in known_skills}
        if "业务技能" in heading:
            business |= names
        elif "元技能" in heading:
            meta |= names
    return business, meta


def lint_skill(
    skill_name: str,
    skill_dir: Path,
    skill_text: str,
    is_business: bool,
    router_text: str,
    mcp_services: set[str],
    evals_dir: Path,
) -> list[tuple[str, str, str]]:
    """对单个技能执行 C1~C10 中适用的机检项。

    Args:
        skill_name: 技能名（skills/ 下目录名）。
        skill_dir: 技能目录路径。
        skill_text: SKILL.md 全文。
        is_business: 是否业务技能（元技能豁免 C7/C8/C10）。
        router_text: router 技能 SKILL.md 全文（路由表检查用）。
        mcp_services: .mcp.json 中登记的服务名集合。
        evals_dir: 仓库 evals 目录路径。
    Returns:
        问题元组列表 (级别, 检查项编号, 中文说明)。
    """
    issues: list[tuple[str, str, str]] = []
    #   1. C1 frontmatter：name 与目录名一致
    frontmatter = parse_frontmatter(skill_text)
    if not frontmatter:
        issues.append((LEVEL_ERROR, "C1", "缺 frontmatter"))
    elif frontmatter.get("name") != skill_name:
        issues.append((LEVEL_ERROR, "C1", f"frontmatter name={frontmatter.get('name')!r} 与目录名 {skill_name!r} 不一致"))
    #   2. C2 description：Use when 触发句式 + 边界句（中英任一）
    description = frontmatter.get("description", "")
    if "Use when" not in description and "use when" not in description.lower():
        issues.append((LEVEL_WARN, "C2", "description 缺「Use when」触发句式"))
    if not ("not for" in description.lower() or "不属于" in description):
        issues.append((LEVEL_WARN, "C2", "description 缺边界句（not for / 不属于）"))
    #   3. C3 行数纪律：50~120 行
    line_count = len(skill_text.splitlines())
    if line_count > LINE_MAX:
        issues.append((LEVEL_ERROR, "C3", f"SKILL.md {line_count} 行，超 {LINE_MAX} 行上限——内容拆 references 按需加载"))
    elif line_count < LINE_MIN:
        issues.append((LEVEL_WARN, "C3", f"SKILL.md 仅 {line_count} 行，低于 {LINE_MIN} 行——确认核心指令齐备"))
    #   4. C4 引用存在性：SKILL.md 引用的 references 文件必须存在
    ref_names = set(REF_PATTERN.findall(skill_text))
    for ref in sorted(ref_names):
        if not (skill_dir / "references" / ref).is_file():
            issues.append((LEVEL_ERROR, "C4", f"引用的 references/{ref} 不存在"))
    #   5. C5 孤儿文件：references/ 下文件至少被 SKILL.md 提及一次
    references_dir = skill_dir / "references"
    if references_dir.is_dir():
        for ref_file in sorted(references_dir.glob("*.md")):
            if ref_file.name not in skill_text:
                issues.append((LEVEL_WARN, "C5", f"references/{ref_file.name} 未被 SKILL.md 提及（孤儿文件，按需加载入口缺失）"))
    if is_business:
        #   6. C7 router 路由表：业务技能必须在路由表中占一行
        if skill_name not in router_text:
            issues.append((LEVEL_ERROR, "C7", "未进 aquilair-skill-router 路由表"))
        #   7. C8 evals 用例目录：业务技能必须有四类题型用例
        if not (evals_dir / skill_name).is_dir():
            issues.append((LEVEL_ERROR, "C8", f"缺 evals/{skill_name}/ 用例目录"))
        #   8. C10 出处标注：references 至少有一处来源/出处标注（溯源纪律渐进达标）
        has_source_note = False
        has_reference_files = references_dir.is_dir() and any(references_dir.glob("*.md"))
        if references_dir.is_dir():
            for ref_file in references_dir.glob("*.md"):
                content = ref_file.read_text(encoding="utf-8")
                if "来源：" in content or "出处" in content:
                    has_source_note = True
                    break
        if has_reference_files and not has_source_note:
            issues.append((LEVEL_WARN, "C10", "references 无任何出处标注（格式见 aquilair-knowledge/sources/README.md）"))
    #   9. C9 MCP 服务：技能提及的服务必须在 .mcp.json 登记
    for service in sorted(set(SERVICE_PATTERN.findall(skill_text))):
        if service not in mcp_services:
            issues.append((LEVEL_ERROR, "C9", f"提及的 MCP 服务 {service} 未在 .mcp.json 登记"))
    return issues


# ===========一、仓库级巡检==========
def lint_repo(repo_root: Path) -> tuple[list[dict[str, list[tuple[str, str, str]]]], list[tuple[str, str, str]]]:
    """巡检整个仓库：清点技能资产，逐技能执行机检，并做仓库级一致性检查。

    Args:
        repo_root: 仓库根目录路径。
    Returns:
        (逐技能问题清单 [{技能名: 问题列表}]，仓库级问题列表)。
    """
    skills_dir = repo_root / "skills"
    #   1. 资产清点与分类事实源读取
    known_skills = {d.name for d in skills_dir.iterdir() if d.is_dir()}
    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    business, meta = parse_readme_categories(readme_text, known_skills)
    router_text = (skills_dir / "aquilair-skill-router" / "SKILL.md").read_text(encoding="utf-8")
    mcp_path = repo_root / ".mcp.json"
    mcp_services = set(json.loads(mcp_path.read_text(encoding="utf-8")).get("mcpServers", {})) if mcp_path.is_file() else set()
    evals_dir = repo_root / "evals"
    #   2. 逐技能机检（未进 README 任何章节的目录视为业务技能候选，按 C6 报错）
    per_skill: list[dict[str, list[tuple[str, str, str]]]] = []
    repo_issues: list[tuple[str, str, str]] = []
    for skill_name in sorted(known_skills):
        skill_dir = skills_dir / skill_name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            per_skill.append({skill_name: [(LEVEL_ERROR, "C0", "目录缺 SKILL.md，不是合法技能资产")]})
            continue
        is_business = skill_name in business
        issues = lint_skill(skill_name, skill_dir, skill_file.read_text(encoding="utf-8"), is_business, router_text, mcp_services, evals_dir)
        if skill_name not in business and skill_name not in meta:
            issues.append((LEVEL_ERROR, "C6", "未进 README 技能清单（业务技能或元技能章节）"))
        per_skill.append({skill_name: issues})
    #   3. 仓库级：.mcp.json 死服务检查（登记的服务必须被至少一个技能提及）
    all_skill_text = "\n".join(
        (skills_dir / s / "SKILL.md").read_text(encoding="utf-8")
        for s in sorted(known_skills)
        if (skills_dir / s / "SKILL.md").is_file()
    )
    mentioned = set(SERVICE_PATTERN.findall(all_skill_text))
    for service in sorted(mcp_services - mentioned):
        repo_issues.append((LEVEL_WARN, "C9", f".mcp.json 服务 {service} 未被任何技能提及（疑似死服务）"))
    #   4. C11 域知识库健康检查：每域编译层三件齐（glossary/index/log）+ 出处标注抽查
    sources_root = repo_root / "aquilair-knowledge" / "sources"
    if sources_root.is_dir():
        for domain_dir in sorted(p for p in sources_root.iterdir() if p.is_dir()):
            domain = domain_dir.name
            for page in ("glossary.md", "index.md", "log.md"):
                if not (domain_dir / page).is_file():
                    repo_issues.append((LEVEL_WARN, "C11", f"域 {domain} 缺编译层 {page}（渐进达标，见 ingest 流程）"))
            # 编译层知识页必须含出处标注（来源：/出处）——无来源页面即 lint 发现
            for page in ("glossary.md", "overview.md"):
                page_path = domain_dir / page
                if page_path.is_file():
                    content = page_path.read_text(encoding="utf-8")
                    if "来源：" not in content and "出处" not in content:
                        repo_issues.append((LEVEL_WARN, "C11", f"域 {domain} 编译层 {page} 无出处标注"))
    return per_skill, repo_issues


# ===========二、报告输出与命令行入口==========
def print_report(
    per_skill: list[dict[str, list[tuple[str, str, str]]]],
    repo_issues: list[tuple[str, str, str]],
) -> int:
    """打印中文巡检报告并返回退出码。

    Args:
        per_skill: lint_repo 返回的逐技能问题清单。
        repo_issues: lint_repo 返回的仓库级问题列表。
    Returns:
        进程退出码：存在 ERROR 为 1，否则为 0。
    """
    print("====技能工厂巡检报告====")
    error_total = warn_total = 0
    for entry in per_skill:
        for skill_name, issues in entry.items():
            if not issues:
                print(f"[PASS] {skill_name}")
                continue
            levels = {level for level, _, _ in issues}
            verdict = "FAIL" if LEVEL_ERROR in levels else "WARN"
            print(f"[{verdict}] {skill_name}")
            for level, code, message in issues:
                marker = "❌" if level == LEVEL_ERROR else "⚠️"
                print(f"  {marker} [{level}][{code}] {message}")
                error_total += level == LEVEL_ERROR
                warn_total += level == LEVEL_WARN
    if repo_issues:
        print("[WARN] 仓库级")
        for level, code, message in repo_issues:
            print(f"  ⚠️ [{level}][{code}] {message}")
            warn_total += 1
    # pass_total：无问题技能数，用于汇总行
    pass_total = sum(1 for entry in per_skill for issues in entry.values() if not issues)
    verdict = "不通过（存在 ERROR，须修复后交付）" if error_total else "通过（WARN 不阻断，按需整改）"
    print(f"====巡检汇总====: 技能 {len(per_skill)} 个（PASS {pass_total}）| ERROR {error_total} | WARN {warn_total} | 结论：{verdict}")
    return 1 if error_total else 0


def main() -> int:
    """巡检入口：定位仓库根，执行巡检并打印报告。

    Args:
        无（自动取脚本上级目录为仓库根）。
    Returns:
        进程退出码：存在 ERROR 为 1，否则为 0。
    """
    repo_root = Path(__file__).resolve().parent.parent
    per_skill, repo_issues = lint_repo(repo_root)
    return print_report(per_skill, repo_issues)


if __name__ == "__main__":
    sys.exit(main())

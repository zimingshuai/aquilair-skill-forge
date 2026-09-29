"""插件基础设施测试：自动发现全部技能并逐项断言分发 zip 的结构正确性。

主要 Input：仓库 skills/ 目录下的全部技能目录（自动发现，新技能零改动自动纳入）。
主要 Output：中文逐技能逐断言 PASS/FAIL/SKIP 报告（====基础设施测试通过/失败==== 定界）；
进程退出码全过为 0、任一 FAIL 为 1。全程仅在系统临时目录构造打包副本，不在仓库内写任何文件。
"""

import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import yaml

# REPO_ROOT：仓库根目录——tests/ 与 tools/ 同级，需注入导入路径以引用打包器
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.pack_skill import PACK_ITEMS, pack_skill

# SKILLS_DIR：被测技能根目录（仓库 skills/）
SKILLS_DIR = REPO_ROOT / "skills"


# ===========一、技能发现与 frontmatter 解析==========
def discover_skills(skills_dir: Path) -> list[str]:
    """自动发现技能目录名列表。

    Args:
        skills_dir: 仓库 skills 目录路径。
    Returns:
        排序后的技能目录名列表；仅收录普通目录——*.zip 为文件天然被
        is_dir 排除，点开头目录（隐藏目录）显式排除，新技能零改动自动纳入。
    """
    # names：候选目录名列表（zip 产物是文件，is_dir 已排除）
    names = [
        entry.name
        for entry in skills_dir.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    ]
    return sorted(names)


def _parse_frontmatter(skill_md: Path) -> dict:
    """解析 SKILL.md 顶部的 YAML frontmatter。

    Args:
        skill_md: SKILL.md 文件路径。
    Returns:
        frontmatter 键值字典。
    Raises:
        ValueError: 缺少起始/结束分隔线、YAML 解析失败或内容不是键值结构。
    """
    # lines：SKILL.md 全文按行拆分（utf-8 与仓库现状一致）
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("缺少 frontmatter 起始分隔线 ---")
    try:
        # end_index：结束分隔线所在行号（从第 2 行起找，跳过首行自身）
        end_index = next(
            index for index in range(1, len(lines)) if lines[index].strip() == "---"
        )
    except StopIteration as exc:
        raise ValueError("缺少 frontmatter 结束分隔线 ---") from exc
    # block：两条分隔线之间的 YAML 文本
    block = "\n".join(lines[1:end_index])
    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 解析失败: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"frontmatter 不是键值结构: {type(parsed).__name__}")
    return parsed


# ===========二、单技能断言组==========
@dataclass
class CheckResult:
    """单条断言的执行结果。

    Input:
        label: 断言标签（含规格编号 a-h，中文短语）。
        ok: 断言结论；True 通过、False 失败、None 跳过（规格允许的前置不满足场景）。
        detail: 结果补充说明（中文，含失败证据）。
    """

    label: str
    ok: bool | None
    detail: str


def check_skill(skill_name: str, skills_dir: Path) -> list[CheckResult]:
    """对单个技能执行规格 a-h 全部结构断言。

    Args:
        skill_name: 技能目录名。
        skills_dir: 仓库 skills 目录路径。
    Returns:
        逐条断言结果列表，顺序对应规格 a-h；条目自身失败不阻断后续断言，
        仅在其产物（frontmatter / zip）缺失时，依赖它的断言如实记 FAIL。
    """
    # results：断言结果累积列表
    results: list[CheckResult] = []
    # skill_dir / skill_md：被测技能目录与其 SKILL.md 路径
    skill_dir = skills_dir / skill_name
    skill_md = skill_dir / "SKILL.md"

    #   1. 断言 a：SKILL.md 存在且 YAML frontmatter 可解析
    # frontmatter：解析成功后的键值字典；失败时保持空 dict，让 b/c 自然失败
    frontmatter: dict = {}
    if not skill_md.is_file():
        results.append(
            CheckResult("a-SKILL.md存在且frontmatter可解析", False, f"文件缺失: {skill_md}")
        )
    else:
        try:
            frontmatter = _parse_frontmatter(skill_md)
            results.append(CheckResult("a-SKILL.md存在且frontmatter可解析", True, "frontmatter 已解析"))
        except ValueError as exc:
            results.append(CheckResult("a-SKILL.md存在且frontmatter可解析", False, str(exc)))

    #   2. 断言 b：frontmatter name 与目录名一致
    # fm_name：frontmatter 声明的技能名（缺失时为 None，自然判 FAIL）
    fm_name = frontmatter.get("name")
    results.append(
        CheckResult(
            "b-name与目录名一致",
            fm_name == skill_name,
            f"frontmatter.name={fm_name!r}, 目录名={skill_name!r}",
        )
    )

    #   3. 断言 c：description 含 Use when 触发句式（大小写不敏感）且 license 存在
    # description / license_value：触发描述与许可证字段
    description = frontmatter.get("description")
    license_value = frontmatter.get("license")
    # has_trigger：触发句式标记检测结果
    has_trigger = isinstance(description, str) and "use when" in description.lower()
    results.append(
        CheckResult(
            "c-描述含Use when且license存在",
            has_trigger and license_value not in (None, ""),
            f"含Use when={has_trigger}, license={license_value!r}",
        )
    )

    #   4. 断言 d：系统临时目录构造 skills 副本（仅复制被测技能）并成功打包出 zip
    # names：zip 内条目路径列表；打包失败时保持 None，e-h 据此判 FAIL
    names: list[str] | None = None
    # zip_error：打包失败时的异常说明（含类型与消息，不掩盖）
    zip_error = ""
    try:
        with tempfile.TemporaryDirectory(prefix="infra-tests-") as tmp_dir:
            # tmp_skills：系统临时目录中的 skills 副本根目录（零仓库污染）
            tmp_skills = Path(tmp_dir) / "skills"
            tmp_skills.mkdir()
            shutil.copytree(skill_dir, tmp_skills / skill_name)
            # zip_path：打包器产出的分发 zip 路径（位于临时目录内）
            zip_path = pack_skill(skill_name, tmp_skills)
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
        results.append(
            CheckResult("d-临时副本打包出zip", True, f"zip 条目数={len(names or [])}")
        )
    except Exception as exc:  # 宽捕获是断言 d 的检验对象：打包器任何异常都构成失败证据
        zip_error = f"{type(exc).__name__}: {exc}"
        results.append(CheckResult("d-临时副本打包出zip", False, zip_error))

    #   5. 断言 e-h：zip 结构检查；打包未产出 zip 时无对象可查，如实逐条记 FAIL
    if names is None:
        for label in (
            "e-zip首层恰含SKILL.md",
            "f-无pycache与pyc条目",
            "g-路径全为正斜杠",
            "h-可选目录一致性",
        ):
            results.append(CheckResult(label, False, f"打包未产出 zip: {zip_error}"))
        return results

    # top_levels：namelist 首层名集合（用于检测外层同名文件夹包裹）
    top_levels = {entry.split("/")[0] for entry in names}
    results.append(
        CheckResult(
            "e-zip首层恰含SKILL.md",
            "SKILL.md" in names and skill_name not in top_levels,
            f"首层条目集合={sorted(top_levels)}",
        )
    )

    # pyc_entries：命中的缓存类条目（__pycache__ 目录内或 .pyc 后缀）
    pyc_entries = [
        entry
        for entry in names
        if "__pycache__" in entry.split("/") or entry.endswith(".pyc")
    ]
    results.append(
        CheckResult("f-无pycache与pyc条目", not pyc_entries, f"命中缓存条目={pyc_entries[:3]}")
    )

    # backslash_entries：含反斜杠的问题条目（Windows 路径分隔符泄漏）
    backslash_entries = [entry for entry in names if "\\" in entry]
    results.append(
        CheckResult("g-路径全为正斜杠", not backslash_entries, f"命中反斜杠条目={backslash_entries[:3]}")
    )

    #   6. 断言 h：PACK_ITEMS 可选目录一致性——源目录存在则 zip 必含其条目，全部缺席才跳过
    # optional_items：打包清单中的可选目录项（SKILL.md 已由断言 e 覆盖）
    optional_items = [item for item in PACK_ITEMS if item != "SKILL.md"]
    # present_dirs：技能源目录中实际存在的可选清单目录
    present_dirs = [item for item in optional_items if (skill_dir / item).is_dir()]
    # missing_dirs：源目录存在但 zip 中无任何条目的清单目录（真实缺陷信号）
    missing_dirs = [
        item
        for item in present_dirs
        if not any(entry.startswith(f"{item}/") for entry in names)
    ]
    if not present_dirs:
        results.append(CheckResult("h-可选目录一致性", None, "技能无任何可选清单目录，按规格跳过"))
    else:
        results.append(
            CheckResult(
                "h-可选目录一致性",
                not missing_dirs,
                f"源目录存在={present_dirs}, 打包缺席={missing_dirs}",
            )
        )

    #   7. 断言 i：知识库随包分发——真实仓库根打包必含 aquilair-knowledge/sources/ 条目
    # （断言 d 用临时 skills 目录隔离，天然无知识库可收；本项专验收录功能本身。
    #   zip 产物落在真实 skills/ 下且已被 .gitignore 排除，零仓库污染）
    # knowledge_entries：zip 中知识库源文档区条目
    knowledge_entries = []
    try:
        real_zip_path = pack_skill(skill_name, skill_dir.parent)
        with zipfile.ZipFile(real_zip_path) as zf:
            knowledge_entries = [
                entry for entry in zf.namelist() if entry.startswith("aquilair-knowledge/sources/")
            ]
        results.append(
            CheckResult(
                "i-知识库随包分发",
                bool(knowledge_entries),
                f"知识库条目数={len(knowledge_entries)}",
            )
        )
    except Exception as exc:  # 打包器任何异常都构成失败证据，不掩盖
        results.append(
            CheckResult("i-知识库随包分发", False, f"{type(exc).__name__}: {exc}")
        )
    return results


# ===========三、报告与入口==========
def main() -> int:
    """对全部自动发现的技能执行断言并输出中文报告。

    Returns:
        进程退出码：全部 PASS/SKIP 为 0，任一 FAIL 为 1（不汇总放行）。
    """
    # skill_names：自动发现的技能目录名列表
    skill_names = discover_skills(SKILLS_DIR)
    print(f"====基础设施测试开始==== 发现 {len(skill_names)} 个技能: {skill_names}")
    # failed：是否出现任一 FAIL 断言
    failed = False
    for skill_name in skill_names:
        print(f"\n[{skill_name}]")
        for result in check_skill(skill_name, SKILLS_DIR):
            # status：断言状态字（None 为规格允许的跳过场景）
            status = "SKIP" if result.ok is None else ("PASS" if result.ok else "FAIL")
            print(f"  {result.label}: {status} ({result.detail})")
            failed = failed or result.ok is False
    print()
    if failed:
        print("====基础设施测试失败====")
        return 1
    print("====基础设施测试通过====")
    return 0


if __name__ == "__main__":
    sys.exit(main())

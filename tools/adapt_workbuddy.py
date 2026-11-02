"""WorkBuddy 宿主适配：生成 .codebuddy-plugin 清单并补 agent 人设扩展键（方案 A 定稿版）。

主要 Input：工厂仓库根（脚本位于 tools/ 下，自动取上级目录，无需参数）。
主要 Output（就地写入，幂等）：
  1. .codebuddy-plugin/marketplace.json                # 仓库级市场清单（市场名 aquilair-forge）
  2. plugins/skill-forge/.codebuddy-plugin/plugin.json # 插件清单（skills 目录 + agents 人设）
  3. agents/*.md 的 WorkBuddy Expert 扩展键（displayName / profession 等，Claude Code 键保留）

用法：
  python tools/adapt_workbuddy.py           # 生成 / 更新（就地写入）
  python tools/adapt_workbuddy.py --check   # 只校验不写：与磁盘现状不一致则退出码 1

设计纪律（2026-11-02 方案 A：插件自包含化）：
  - 曾经的「仓库根锚点注入 SKILL.md」机制已删除——机器绝对路径不进版本库、宿主特定内容
    不污染宿主无关源文件。运行时工具链由 tools/sync_plugin_assets.py 以插件内副本承载，
    安装态在插件根 tools/、evals/ 下直接可用。
  - 插件清单落在 plugins/skill-forge/ 而非仓库根：仓库根 .codebuddy-plugin/plugin.json 会被
    tools/lint_skills.py 的 C12 按 business-hub 技能集校验，而 forge 元技能本就不进 CodeBuddy 清单。
"""

import json
import sys
from pathlib import Path

# PLUGIN_NAME / MARKETPLACE_NAME：WorkBuddy 侧标识（与 .claude-plugin 保持同名，便于对齐上游）
PLUGIN_NAME = "aquilair-skill-forge"
MARKETPLACE_NAME = "aquilair-forge"
# PLUGIN_DIR_REL：插件本体相对仓库根的路径
PLUGIN_DIR_REL = Path("plugins") / "skill-forge"
# AGENT_FRONTMATTER：agent 人设需补的 WorkBuddy Expert 扩展键（Claude Code 键 name/description 保留不动）
AGENT_FRONTMATTER = {
    "displayName": "业务锻造师·天工（Skill Smith）",
    "profession": "Aquilair 技能工厂总师 ｜ Aquilair Skill Factory Master",
}
# AGENT_NAME：专家卡对应的 agent 人设名（agents/ 下唯一人设）
AGENT_NAME = "aquilair-skill-smith"
# EXPERT_META：专家卡字段（对齐 my-experts 市场内 fde / supply-chain 两个专家插件的既有惯例）。
# 不写 categoryId：专家中心按目录筛选时无对应「开发工具」类目，留空则「全部」可见、按类筛选时隐藏；
# 要挂某个类目时补一行即可。avatar 由 tools/make_forge_avatar.py 生成（一次性资产，脚本不重画）。
EXPERT_META = {
    "displayName": {"en": "Aquilair Skill Smith", "zh": "天鹰·业务锻造师"},
    "profession": {"en": "Aquilair Skill Factory Master", "zh": "Aquilair 技能工厂总师"},
    "displayDescription": {
        "en": "Skill factory master for skill developers: runs the six-step pipeline (init, live-probe, scoping, template, wiring, acceptance), diagnoses failed evals into four evidence-backed categories, and ingests domain knowledge bases. Drafts and reports only - the developer owns promotion and release.",
        "zh": "面向技能开发者的工厂总师：编排六步流水线（立项→实测→划界→模板→接线→验收）、评估 FAIL 四类带证据归因、域知识库摄取编译。只产草稿与报告，转正与发布由开发者拍板。",
    },
    "defaultInitPrompt": {
        "zh": "把这个新业务域（MCP 服务 + 业务文档包）接入技能工厂，从立项走到验收",
        "en": "Onboard this new business domain (MCP service + docs) into the skill factory, from init to acceptance.",
    },
    "tags": [
        {"en": "Skill Authoring", "zh": "技能创作"},
        {"en": "Eval Diagnostics", "zh": "评估归因"},
        {"en": "Knowledge Wiki", "zh": "域知识库"},
    ],
    "quickPrompts": [
        {
            "zh": "把这个新业务域（MCP 服务 + 业务文档包）接入技能工厂，从立项走到验收",
            "en": "Onboard this new domain (MCP service + docs) into the skill factory, init to acceptance.",
        },
        {
            "zh": "这轮评估回归有 FAIL，帮我读报告和 transcripts，按四类归因给出反哺建议",
            "en": "This regression has FAILs - read the report and transcripts, attribute them into four categories with evidence.",
        },
        {
            "zh": "为指定技能生成四类题型用例草稿，并陪我逐条复核转正",
            "en": "Generate four-type eval case drafts for a skill and review them with me case by case.",
        },
    ],
}
# PLUGIN_META：插件清单固定字段（版本由 .claude-plugin/plugin.json 读取，单一事实源）
PLUGIN_META = {
    "keywords": ["aquilair", "skill-forge", "meta-skill", "eval", "knowledge-wiki"],
    "category": "开发工具",
    "license": "Proprietary — Aquilair 内部分发，仅限公司内网使用",
}


def read_version(repo_root: Path) -> str:
    """从 .claude-plugin/plugin.json 读取插件版本，保证多宿主清单版本同源。

    Args:
        repo_root: 工厂仓库根路径。
    Returns:
        版本号字符串；文件缺失时返回 "0.0.0"。
    """
    manifest = repo_root / PLUGIN_DIR_REL / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return "0.0.0"
    return json.loads(manifest.read_text(encoding="utf-8")).get("version", "0.0.0")


def ensure_agent_frontmatter(text: str) -> str:
    """为 agent 人设补齐 WorkBuddy Expert 扩展键（缺则补，已存在则不动）。

    Args:
        text: agent 人设全文。
    Returns:
        补齐后的全文。
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    try:
        fm_close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return text
    fm_block = "".join(lines[1:fm_close])
    additions = [f"{key}: {value}\n" for key, value in AGENT_FRONTMATTER.items() if f"{key}:" not in fm_block]
    if not additions:
        return text
    return "".join(lines[:fm_close]) + "".join(additions) + "".join(lines[fm_close:])


def build_plugin_manifest(repo_root: Path) -> dict:
    """构造 WorkBuddy 插件清单（专家卡 + skills/agents 显式登记）。

    Args:
        repo_root: 工厂仓库根路径。
    Returns:
        插件清单字典。skills/agents 用显式数组：专家卡按数组渲染技能列表；
        新增技能后重跑本脚本即自动续入。avatar 缺失时不写字段（专家卡退化为默认头像）。
    """
    source = json.loads((repo_root / PLUGIN_DIR_REL / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    plugin_dir = repo_root / PLUGIN_DIR_REL
    skill_names = sorted(p.name for p in (plugin_dir / "skills").iterdir() if p.is_dir() and not p.name.startswith("."))
    agent_names = sorted(p.stem for p in (plugin_dir / "agents").glob("*.md"))
    agent_name = AGENT_NAME if AGENT_NAME in agent_names else (agent_names[0] if agent_names else None)
    manifest = {
        "name": PLUGIN_NAME,
        "version": read_version(repo_root),
        "description": source.get("description", ""),
        "author": source.get("author", {"name": "Aquilair Team"}),
        "homepage": "https://github.com/zimingshuai/aquilair-skill-forge",
        "keywords": PLUGIN_META["keywords"],
        "category": PLUGIN_META["category"],
        "license": PLUGIN_META["license"],
        "skills": [f"./skills/{name}" for name in skill_names],
        "agents": [f"./agents/{name}.md" for name in agent_names],
        "plugin": PLUGIN_NAME,
        "displayName": EXPERT_META["displayName"],
        "profession": EXPERT_META["profession"],
        "displayDescription": EXPERT_META["displayDescription"],
        "defaultInitPrompt": EXPERT_META["defaultInitPrompt"],
        "tags": EXPERT_META["tags"],
        "quickPrompts": EXPERT_META["quickPrompts"],
    }
    if agent_name:
        manifest["expertType"] = "agent"
        manifest["agentName"] = agent_name
    if (plugin_dir / "avatars" / "expert.png").is_file():
        manifest["avatar"] = "avatars/expert.png"
    return manifest


def build_marketplace(repo_root: Path) -> dict:
    """构造仓库级 WorkBuddy 市场清单（市场名 aquilair-forge，单插件）。

    Args:
        repo_root: 工厂仓库根路径。
    Returns:
        市场清单字典。
    """
    source = json.loads((repo_root / PLUGIN_DIR_REL / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return {
        "name": MARKETPLACE_NAME,
        "owner": {"name": "Aquilair Team"},
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": f"./{PLUGIN_DIR_REL.as_posix()}",
                "description": source.get("description", ""),
                "version": read_version(repo_root),
                "displayName": "Aquilair 业务锻造师",
                "displayName_i18n": {"zh-CN": "Aquilair 业务锻造师"},
                "category": "developer-tools",
            }
        ],
    }


def collect_targets(repo_root: Path) -> list[tuple[Path, str, bool]]:
    """收集待写入文件清单（方案 A 定稿：只生成清单与 agent 扩展键，不再注入 SKILL.md）。

    Args:
        repo_root: 工厂仓库根路径。
    Returns:
        (目标路径, 期望内容, 是否 agent 人设) 列表——期望内容已按规则变换完毕。
    """
    plugin_dir = repo_root / PLUGIN_DIR_REL
    targets: list[tuple[Path, str, bool]] = []
    # agent 人设：补 WorkBuddy Expert 扩展键（幂等——已含则原文不变，比对自然跳过）
    for path in sorted(plugin_dir.glob("agents/*.md")):
        text = path.read_text(encoding="utf-8")
        targets.append((path, ensure_agent_frontmatter(text), True))
    for rel, payload in (
        (Path(".codebuddy-plugin") / "marketplace.json", build_marketplace(repo_root)),
        (PLUGIN_DIR_REL / ".codebuddy-plugin" / "plugin.json", build_plugin_manifest(repo_root)),
    ):
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        targets.append((repo_root / rel, text, False))
    return targets


def main() -> int:
    """适配入口：生成清单并注入锚点；--check 模式只比对不写入。

    Args:
        无（自动取脚本上级目录为仓库根 ；--check 为唯一开关）。
    Returns:
        进程退出码：--check 模式下有漂移返回 1，否则 0。
    """
    repo_root = Path(__file__).resolve().parent.parent
    check_only = "--check" in sys.argv[1:]
    drift: list[str] = []
    for path, expected, _ in collect_targets(repo_root):
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        rel = path.relative_to(repo_root).as_posix()
        if current == expected:
            continue
        if check_only:
            drift.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8", newline="\n")
        print(f"[写入] {rel}")
    if check_only:
        for rel in drift:
            print(f"[漂移] {rel}")
        print(f"====WorkBuddy 适配自检====: 漂移 {len(drift)} 个 | 结论：{'不一致，请重跑适配' if drift else '一致'}")
        return 1 if drift else 0
    print(f"====WorkBuddy 适配完成====: 工厂仓库根 {repo_root.as_posix()} | 市场 {MARKETPLACE_NAME} | 插件 {PLUGIN_NAME}@{read_version(repo_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

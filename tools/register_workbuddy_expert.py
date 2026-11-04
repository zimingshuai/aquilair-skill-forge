"""把本仓库的 skill-forge 插件注册进 WorkBuddy「我的专家」（my-experts 本地市场）。

背景（2026-11-02 排查结论）：WorkBuddy 桌面端的「我的专家」由 CustomExpertRepo 扫描
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/ 生成（读取该市场的
  marketplace.json 条目 + 用户 experts.json 的 id 交集）。注册成独立市场
  （known_marketplaces.json 里的 aquilair-forge）只会让技能生效，不会出现在专家中心。
因此本脚本做三件事（全部幂等，可反复执行）：
  1. 把 plugins/skill-forge 同步为 my-experts 市场内的插件副本（排除 __pycache__ / zip）；
  2. 在 my-experts 的 marketplace.json 里登记该插件（存在则按当前版本更新描述/版本号）；
  3. 确保用户 experts.json 的 ids 里有 "aquilair-skill-forge"（没有则追加，不删既有项）。

用法：
  python tools/register_workbuddy_expert.py           # 同步 + 登记
  python tools/register_workbuddy_expert.py --check   # 只校验不写

注意：改完后需重启 WorkBuddy，专家卡才会刷新。
"""

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "skill-forge"
PLUGIN_NAME = "aquilair-skill-forge"
WORKBUDDY_DIR = Path.home() / ".workbuddy"
MY_EXPERTS_DIR = WORKBUDDY_DIR / "plugins" / "marketplaces" / "my-experts"
DEST_DIR = MY_EXPERTS_DIR / "plugins" / PLUGIN_NAME
MARKETPLACE_JSON = MY_EXPERTS_DIR / ".codebuddy-plugin" / "marketplace.json"
EXPERTS_JSON = WORKBUDDY_DIR / "experts" / "custom" / "7e6803c2-16be-4101-bed5-e852a9d99f5c" / "experts.json"
COPY_EXCLUDE = {"__pycache__", "*.zip", ".pytest_cache"}


def plugin_version() -> str:
    manifest = json.loads((PLUGIN_DIR / ".codebuddy-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return manifest["version"]


def sync_copy() -> bool:
    """同步插件副本到 my-experts。返回是否有变更。"""
    changed = not DEST_DIR.exists()
    if DEST_DIR.exists():
        src_marker = (PLUGIN_DIR / ".codebuddy-plugin" / "plugin.json").read_bytes()
        dst_marker = (DEST_DIR / ".codebuddy-plugin" / "plugin.json").read_bytes()
        changed = src_marker != dst_marker or not (DEST_DIR / "avatars" / "expert.png").is_file()
    if changed:
        if DEST_DIR.exists():
            shutil.rmtree(DEST_DIR)
        shutil.copytree(
            PLUGIN_DIR,
            DEST_DIR,
            ignore=shutil.ignore_patterns(*COPY_EXCLUDE),
        )
    return changed


def marketplace_entry_changed() -> bool:
    data = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    plugins = data.setdefault("plugins", [])
    manifest = json.loads((PLUGIN_DIR / ".codebuddy-plugin" / "plugin.json").read_text(encoding="utf-8"))
    entry = {
        "name": PLUGIN_NAME,
        "source": f"./plugins/{PLUGIN_NAME}",
        "description": manifest.get("description", ""),
        "version": manifest.get("version", plugin_version()),
    }
    for i, p in enumerate(plugins):
        if p.get("source") == entry["source"] or p.get("name") == PLUGIN_NAME:
            return plugins[i] != entry
    return True


def update_marketplace() -> bool:
    data = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    plugins = data.setdefault("plugins", [])
    manifest = json.loads((PLUGIN_DIR / ".codebuddy-plugin" / "plugin.json").read_text(encoding="utf-8"))
    entry = {
        "name": PLUGIN_NAME,
        "source": f"./plugins/{PLUGIN_NAME}",
        "description": manifest.get("description", ""),
        "version": manifest.get("version", plugin_version()),
    }
    for i, p in enumerate(plugins):
        if p.get("source") == entry["source"] or p.get("name") == PLUGIN_NAME:
            if plugins[i] == entry:
                return False
            plugins[i] = entry
            break
    else:
        plugins.append(entry)
    MARKETPLACE_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return True


def expert_id_missing() -> bool:
    ids = json.loads(EXPERTS_JSON.read_text(encoding="utf-8"))
    return PLUGIN_NAME not in ids


def add_expert_id() -> bool:
    ids = json.loads(EXPERTS_JSON.read_text(encoding="utf-8"))
    if PLUGIN_NAME in ids:
        return False
    ids.append(PLUGIN_NAME)
    EXPERTS_JSON.write_text(
        json.dumps(ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return True


def main() -> int:
    check = "--check" in sys.argv
    problems = []
    if not MY_EXPERTS_DIR.is_dir():
        print(f"[FAIL] 未找到 my-experts 市场：{MY_EXPERTS_DIR}")
        return 1
    if not EXPERTS_JSON.is_file():
        print(f"[FAIL] 未找到用户专家 ids 文件：{EXPERTS_JSON}")
        return 1
    if sync_copy() and check:
        problems.append("插件副本与仓库不一致")
    if marketplace_entry_changed() and check:
        problems.append("marketplace.json 未登记或字段过期")
    if expert_id_missing() and check:
        problems.append("experts.json 缺少专家 id")
    if check:
        if problems:
            print("[DRIFT] " + "；".join(problems))
            return 1
        print("[OK] my-experts 注册零漂移")
        return 0
    changed = []
    if sync_copy():
        changed.append("插件副本已同步")
    if update_marketplace():
        changed.append("marketplace.json 已登记")
    if add_expert_id():
        changed.append("experts.json 已追加 id")
    print("[DONE] " + ("；".join(changed) if changed else "无需变更（已一致）"))
    print("重启 WorkBuddy 后，「我的专家」将出现 天鹰·业务锻造师 卡片。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

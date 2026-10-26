"""把单个技能目录打包为可上传平台的分发 zip。

主要 Input：一个或多个技能名（命令行参数，对应 plugins/*/skills/<技能名>/ 目录，
自动跨双插件目录定位）。
主要 Output：<技能所在 skills 目录>/<技能名>.zip——SKILL.md 位于压缩包根目录（上传界面硬性要求），
包含 references/、scripts/ 与 .meta-cache/ 元数据快照（fetch_meta.py 依赖，可重建）；
另收录仓库知识库源文档区 aquilair-knowledge/sources/（zip 内保持同名坐标，references 的出处标注
在分发包内可解析溯源链），排除 __pycache__ 编译缓存；条目路径统一正斜杠，
避免 Windows 反斜杠导致平台解析失败。
"""

import argparse
import sys
import zipfile
from pathlib import Path

# PACK_ITEMS：打包清单——SKILL.md 必备（缺失即报错），其余为可选目录，存在才打包
PACK_ITEMS = ("SKILL.md", "references", "scripts", ".meta-cache")
# EXCLUDED_DIRS：排除目录——Python 编译缓存不进分发包
EXCLUDED_DIRS = {"__pycache__"}
# KNOWLEDGE_SOURCE_DIR：知识库源文档区（仓库根相对路径）——随每个技能 zip 分发，
# zip 内保持 aquilair-knowledge/sources/ 坐标不变，references 出处标注得以在包内溯源
KNOWLEDGE_SOURCE_DIR = Path("aquilair-knowledge/sources")


# ===========一、打包核心==========
def locate_repo_root(skills_dir: Path) -> Path | None:
    """从技能所在 skills 目录向上定位仓库根（含知识库源文档区的祖先）。

    Args:
        skills_dir: 技能所在的 skills 目录路径（plugins/<插件>/skills）。
    Returns:
        仓库根路径；向上 5 层内未找到 aquilair-knowledge 时返回 None
        （打包器被用于临时目录副本等无仓库场景时，知识库自然缺席）。
    """
    # current：逐级上移的候选祖先目录
    current = skills_dir
    for _ in range(5):
        if (current / KNOWLEDGE_SOURCE_DIR).is_dir():
            return current
        current = current.parent
    return None


def pack_skill(skill_name: str, skills_dir: Path) -> Path:
    """打包单个技能目录为根目录含 SKILL.md 的分发 zip。

    Args:
        skill_name: 技能名，即 skills/ 下的目录名，也用作 zip 文件名。
        skills_dir: 技能所在的 skills 目录路径（plugins/<插件>/skills）。
    Returns:
        生成的 zip 文件路径。
    Raises:
        FileNotFoundError: 技能目录不存在或缺少 SKILL.md。
    """
    # skill_dir：待打包的技能源目录
    skill_dir = skills_dir / skill_name
    if not (skill_dir / "SKILL.md").is_file():
        raise FileNotFoundError(f"技能目录缺失 SKILL.md: {skill_dir}")
    # zip_path：输出 zip 路径，覆盖旧包
    zip_path = skills_dir / f"{skill_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in PACK_ITEMS:
            # item_path：清单项的绝对路径，文件直接写入，目录递归遍历
            item_path = skill_dir / item
            if item_path.is_file():
                zf.write(item_path, item)
            elif item_path.is_dir():
                for full in sorted(item_path.rglob("*")):
                    if any(part in EXCLUDED_DIRS for part in full.parts):
                        continue
                    if full.is_file():
                        zf.write(full, full.relative_to(skill_dir).as_posix())
        # repo_root：仓库根（含知识库源文档区的祖先）；临时副本场景为 None，跳过收录
        repo_root = locate_repo_root(skills_dir)
        if repo_root is not None:
            for full in sorted((repo_root / KNOWLEDGE_SOURCE_DIR).rglob("*")):
                if any(part in EXCLUDED_DIRS for part in full.parts):
                    continue
                if full.is_file():
                    # zip 内保持仓库相对坐标（aquilair-knowledge/sources/...），标注可解析
                    zf.write(full, full.relative_to(repo_root).as_posix())
    return zip_path


# ===========二、命令行入口==========
def main(argv: list[str] | None = None) -> int:
    """解析技能名参数并逐个打包，打印每个 zip 的绝对路径。

    Args:
        argv: 命令行参数列表，缺省取 sys.argv[1:]。
    Returns:
        进程退出码：全部成功 0，任一失败 1。
    """
    parser = argparse.ArgumentParser(description="打包技能为可上传的分发 zip")
    parser.add_argument("skills", nargs="+", help="技能名列表，对应 plugins/*/skills/<技能名>/ 目录")
    args = parser.parse_args(argv)
    # repo_root：仓库根（脚本位于 tools/ 下，取上一级）
    repo_root = Path(__file__).resolve().parent.parent
    # skill_roots：双插件下的全部 skills 目录（业务 hub + 锻造 forge），供技能名定位
    skill_roots = sorted(p for p in (repo_root / "plugins").glob("*/skills") if p.is_dir())
    failed = False
    for skill_name in args.skills:
        # skills_dir：该技能所在的 skills 目录；遍历双插件定位，未找到即报错并列可用技能
        skills_dir = next((root for root in skill_roots if (root / skill_name).is_dir()), None)
        if skills_dir is None:
            available = [d.name for root in skill_roots for d in root.iterdir() if d.is_dir()]
            print(f"====打包失败====: 未找到技能 {skill_name}，可用技能: {sorted(available)}")
            failed = True
            continue
        try:
            zip_path = pack_skill(skill_name, skills_dir)
        except FileNotFoundError as exc:
            print(f"====打包失败====: {exc}")
            failed = True
            continue
        print(f"====打包成功====: {zip_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

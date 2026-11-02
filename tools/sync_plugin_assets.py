"""插件自包含资产同步：把元技能运行时必需的最小工具集与评估协议复制进插件目录。

主要 Input：无参数（脚本位于仓库根 tools/ 下，自动取上级为仓库根）；--check 为唯一开关。
主要 Output：plugins/skill-forge/ 下的分发副本——tools/{pack_skill.py, lint_skills.py,
skill-eval-generator/} 与 evals/README.md；--check 模式只比对不写入，存在漂移时退出码 1。

设计纪律（方案 A：插件自包含化）：
  - 插件装进宿主缓存后只含 plugins/skill-forge/ 目录，仓库根的 tools/、evals/、
    aquilair-knowledge/ 不随包走——元技能正文里的工具命令与协议引用必须靠这些副本成立。
  - 副本与源同源同步：改源后重跑本脚本；发版门禁跑 --check 防漂移（源改了副本没同步即拦截）。
  - 知识库主本（aquilair-knowledge/）是内容资产不随插件（资产分界，见分发口径），不在同步清单。
"""

import filecmp
import shutil
import sys
from pathlib import Path

# SYNC_PAIRS：(源路径, 插件内目标路径) 同步清单——文件级或整目录
SYNC_PAIRS: list[tuple[Path, Path]] = [
    (Path("tools/pack_skill.py"), Path("plugins/skill-forge/tools/pack_skill.py")),
    (Path("tools/lint_skills.py"), Path("plugins/skill-forge/tools/lint_skills.py")),
    (Path("tools/skill-eval-generator"), Path("plugins/skill-forge/tools/skill-eval-generator")),
    (Path("evals/README.md"), Path("plugins/skill-forge/evals/README.md")),
]


# ===========一、同步与比对==========
def sync_pair(src: Path, dst: Path, check_only: bool) -> bool:
    """同步单个文件或目录到插件内目标位置（幂等：内容一致则跳过）。

    Args:
        src: 仓库根下的源路径（文件或目录）。
        dst: 插件内的目标路径。
        check_only: True 只比对不写入。
    Returns:
        目标与源是否一致（check_only 语义下即「无漂移」）。
    Raises:
        FileNotFoundError: 源路径不存在（同步清单失效，须修清单）。
    """
    if not src.exists():
        raise FileNotFoundError(f"同步源不存在，请检查 SYNC_PAIRS 清单: {src}")
    #   1. 比对：文件用逐字节内容比对；目录用两侧文件清单对称 + 逐文件内容比对
    if src.is_file():
        in_sync = dst.is_file() and filecmp.cmp(src, dst, shallow=False)
    else:
        src_names = _walk_names(src)
        dst_names = _walk_names(dst) if dst.is_dir() else []
        in_sync = src_names == dst_names and all(
            filecmp.cmp(src / name, dst / name, shallow=False) for name in src_names
        )
    #   2. 落盘：check 模式到此为止，仅返回比对结论
    if in_sync or check_only:
        return in_sync
    if dst.is_dir():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(src, dst)
    return True


def _walk_names(directory: Path) -> list[str]:
    """收集目录内全部相对文件名，供 cmpfiles 整树比对。

    Args:
        directory: 待收集的目录路径。
    Returns:
        相对路径文件名列表（正斜杠分隔，跨平台一致）。
    """
    return [
        str(p.relative_to(directory)).replace("\\", "/")
        for p in sorted(directory.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]


# ===========二、模块入口==========
def main() -> int:
    """同步入口：逐对同步或比对，打印中文结果并给出退出码。

    Returns:
        进程退出码——--check 模式下存在漂移返回 1，否则 0。
    """
    check_only = "--check" in sys.argv[1:]
    # repo_root：仓库根（脚本位于 tools/ 下，取上一级）
    repo_root = Path(__file__).resolve().parent.parent
    drifted: list[str] = []
    for src_rel, dst_rel in SYNC_PAIRS:
        src, dst = repo_root / src_rel, repo_root / dst_rel
        if not sync_pair(src, dst, check_only):
            drifted.append(f"{src_rel} -> {dst_rel}")
    if check_only:
        if drifted:
            print("====插件资产漂移====（重跑 python tools/sync_plugin_assets.py 同步）:")
            for item in drifted:
                print(f"  {item}")
            return 1
        print(f"====插件资产一致====: {len(SYNC_PAIRS)} 项同步物与源无漂移")
        return 0
    print(f"====插件资产同步完成====: {len(SYNC_PAIRS) - len(drifted)} 项写入, {len(drifted)} 项漂移已覆盖")
    return 0


if __name__ == "__main__":
    sys.exit(main())

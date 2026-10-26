"""知识库快照同步：把本仓（forge）知识库主本 sources/ 镜像同步到 hub 仓库的快照区。

主要 Input：目标 hub 仓库路径（命令行参数），以及本仓 aquilair-knowledge/sources/ 主本。
主要 Output：hub 仓库 aquilair-knowledge/sources/ 与主本一致的快照（镜像语义：多余条目删除），
同步报告打印到 stdout；不自动 git commit（打印建议提交命令，由人确认后执行）。
"""

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

# FORGE_ROOT：forge 仓库根（脚本位于 tools/ 下，取上一级）
FORGE_ROOT = Path(__file__).resolve().parent.parent
# SOURCE_DIR：知识库源文档区（主本，仓库根相对路径）
SOURCE_DIR = Path("aquilair-knowledge/sources")
# SNAPSHOT_MARKER：hub 仓快照区的说明文件（同步时保留，不视为多余条目）
SNAPSHOT_MARKER = "SNAPSHOT.md"


# ===========一、差异计算==========
def diff_snapshot(master_dir: Path, snapshot_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """对比主本与快照目录，算出待复制、待删除与内容有差异的文件清单。

    Args:
        master_dir: 主本 sources/ 绝对路径。
        snapshot_dir: 快照 sources/ 绝对路径。
    Returns:
        (仅主本有的相对路径列表, 仅快照有的相对路径列表, 两边都有但内容不同的相对路径列表)。
    """
    # master_files / snapshot_files：两侧全部文件的仓库内相对路径集合
    master_files = {p.relative_to(master_dir).as_posix() for p in master_dir.rglob("*") if p.is_file()}
    snapshot_files = {p.relative_to(snapshot_dir).as_posix() for p in snapshot_dir.rglob("*") if p.is_file()}
    # only_master：需新复制；only_snapshot：快照多余待删除；changed：内容差异待覆盖
    only_master = sorted(master_files - snapshot_files)
    only_snapshot = sorted(snapshot_files - master_files)
    changed = sorted(
        rel
        for rel in master_files & snapshot_files
        if not filecmp.cmp(master_dir / rel, snapshot_dir / rel, shallow=False)
    )
    return only_master, only_snapshot, changed


# ===========二、镜像同步==========
def sync(target_repo: Path, dry_run: bool) -> int:
    """执行主本到 hub 快照区的镜像同步。

    Args:
        target_repo: 目标 hub 仓库根路径（须已含快照区目录结构）。
        dry_run: 只打印将执行的变更清单，不落盘。
    Returns:
        变更条目数（0 即主本与快照已一致，无需同步）。
    Raises:
        FileNotFoundError: 主本或快照区目录不存在。
    """
    # master_dir / snapshot_dir：主本与快照的 sources/ 绝对路径
    master_dir = FORGE_ROOT / SOURCE_DIR
    snapshot_dir = target_repo / SOURCE_DIR
    if not master_dir.is_dir():
        raise FileNotFoundError(f"知识库主本不存在: {master_dir}")
    if not snapshot_dir.is_dir():
        raise FileNotFoundError(f"目标快照区不存在（先在 hub 仓建 {SOURCE_DIR}）: {snapshot_dir}")

    only_master, only_snapshot, changed = diff_snapshot(master_dir, snapshot_dir)
    if not (only_master or only_snapshot or changed):
        print("====快照已一致====: 主本与 hub 快照无差异，无需同步")
        return 0

    # 逐类打印同步计划（dry_run 与实际执行共用同一份清单，所见即所做）
    for rel in only_master:
        print(f"[新增] {rel}")
    for rel in changed:
        print(f"[覆盖] {rel}")
    for rel in only_snapshot:
        print(f"[删除] {rel}")
    if dry_run:
        print(f"====dry-run 结束====: 新增 {len(only_master)} / 覆盖 {len(changed)} / 删除 {len(only_snapshot)}，未落盘")
        return len(only_master) + len(changed) + len(only_snapshot)

    #   1. 复制新增与变更文件（逐文件覆盖，保留主本内容）
    for rel in only_master + changed:
        dest = snapshot_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(master_dir / rel, dest)
    #   2. 删除快照多余文件与随之空掉的目录（镜像语义）
    for rel in only_snapshot:
        (snapshot_dir / rel).unlink()
    for directory in sorted({p for p in snapshot_dir.rglob("*") if p.is_dir()}, reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    total = len(only_master) + len(changed) + len(only_snapshot)
    print(f"====同步完成====: 新增 {len(only_master)} / 覆盖 {len(changed)} / 删除 {len(only_snapshot)}")
    print(f"请在 hub 仓库提交快照（建议 message 标注来源 forge commit）: cd {target_repo} && git add aquilair-knowledge && git commit")
    return total


# ===========三、命令行入口==========
def main(argv: list[str] | None = None) -> int:
    """解析参数并执行同步。

    Args:
        argv: 命令行参数列表，缺省取 sys.argv[1:]。
    Returns:
        进程退出码：同步执行成功 0，参数或目录异常 1。
    """
    parser = argparse.ArgumentParser(description="知识库主本镜像同步到 hub 仓库快照区")
    parser.add_argument("target", help="目标 hub 仓库根路径（如 ../aquilair-business-hub）")
    parser.add_argument("--dry-run", action="store_true", help="只打印变更清单，不落盘")
    args = parser.parse_args(argv)
    try:
        sync(Path(args.target).resolve(), args.dry_run)
    except (FileNotFoundError, OSError) as exc:
        print(f"====同步失败====: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

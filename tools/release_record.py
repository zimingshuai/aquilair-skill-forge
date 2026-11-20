"""发版记录工具（与 push_record 分离：push 是 push，发布是发布）。

用途：执行一次完整发版动作——CHANGELOG 版本节 → 发版 tag（v* 前缀，不可变
锚点）→ 推送发版 tag 到分支上游远程（可选 --also 镜像远程同步）。推送记录
走 push_record.py，本工具不碰 push/* tag、不推分支提交，两个动作完全解耦。

主要 Input：--repo 目标仓库路径（必填）、--version 发版版本号 vX.Y.Z（必填）、
--note 发版要点（首次建节时必填）、--also 镜像远程名列表（可选）、--dry-run
只预览不执行（可选）。
主要 Output：CHANGELOG.md 版本节 + 本地/远程 v* tag；控制台输出中文执行日志。
幂等：版本节已存在则跳过建节，tag 已存在且指向一致则只补推送——支持重入补推。
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ===========一、Git 操作封装==========
def _git(repo: Path, *args: str, check: bool = True) -> str:
    """在指定仓库执行 git 子命令并返回标准输出。

    Args:
        repo: 目标仓库根目录路径。
        *args: git 子命令及其参数。
        check: 为 False 时命令失败不抛异常，返回空串。
    Returns:
        去除首尾空白的标准输出；check=False 且失败时返回空串。
    Raises:
        subprocess.CalledProcessError: check=True 且命令返回非零时抛出。
    """
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, "git " + " ".join(args), result.stderr
        )
    return result.stdout.strip()


def _upstream_remote(repo: Path) -> str:
    """取分支上游远程名（@{u} 形如 gitlab/master，取斜杠前段）。

    Args:
        repo: 目标仓库根目录路径。
    Returns:
        远程名字符串。
    Raises:
        subprocess.CalledProcessError: 分支无上游跟踪时抛出。
    """
    upstream = _git(repo, "rev-parse", "--abbrev-ref",
                    "--symbolic-full-name", "@{u}")
    return upstream.split("/", 1)[0]


# ===========二、版本节与发版校验==========
def _version_section_exists(repo: Path, version: str) -> bool:
    """判断 CHANGELOG.md 中是否已有该版本的发版节。

    Args:
        repo: 目标仓库根目录路径。
        version: 版本号（如 v0.3.0）。
    Returns:
        已存在返回 True；无 CHANGELOG 或未建节返回 False。
    """
    changelog = repo / "CHANGELOG.md"
    if not changelog.exists():
        return False
    return f"\n## {version}（" in changelog.read_text(encoding="utf-8") + "\n"


def _append_version_section(repo: Path, version: str, note: str) -> None:
    """把发版版本节插入 CHANGELOG 顶部（倒序，与 push_record 制度头兼容）。

    Args:
        repo: 目标仓库根目录路径。
        version: 版本号（如 v0.3.0）。
        note: 发版要点（记入节内）。
    Returns:
        None。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    section = f"## {version}（{today}）｜发版 tag `{version}`\n{note}\n"
    changelog = repo / "CHANGELOG.md"
    old = changelog.read_text(encoding="utf-8") if changelog.exists() else ""
    idx = old.find("\n## ")
    insert_at = idx + 1 if idx != -1 else len(old.rstrip()) + 1
    changelog.write_text(old[:insert_at] + section + "\n" + old[insert_at:],
                         encoding="utf-8", newline="")


def _tag_state(repo: Path, version: str, remote: str) -> tuple:
    """核对发版 tag 的本地与远程状态。

    Args:
        repo: 目标仓库根目录路径。
        version: 版本号（如 v0.3.0）。
        remote: 上游远程名。
    Returns:
        (本地是否存在, 本地指向短哈希或空, 远程是否已有该 tag)。
    """
    local_sha = _git(repo, "rev-parse", f"{version}^{{commit}}", check=False)[:12]
    has_local = bool(local_sha)
    remote_refs = _git(repo, "ls-remote", "--tags", remote, version, check=False)
    has_remote = f"refs/tags/{version}" in remote_refs
    return has_local, local_sha, has_remote


# ===========三、主流程（发布动作）==========
def release(repo: Path, version: str, note: str, also: list, dry_run: bool) -> int:
    """执行发版主流程：建版本节（幂等）→ 打 v tag（冲突拒绝）→ 推 tag 到远程。

    Args:
        repo: 目标仓库根目录路径。
        version: 版本号（形如 v0.3.0 或 0.3.0，内部统一加 v 前缀）。
        note: 发版要点；版本节不存在时必填。
        also: 镜像远程名列表（可为空）。
        dry_run: True 时只打印将执行的动作，不产生任何变更。
    Returns:
        进程退出码：0 成功；1 校验失败或执行失败。
    """
    #   1. 归一版本号（容错裸版本号），校验已 commit（发版不打未提交内容）
    version = version if version.startswith("v") else "v" + version
    if _git(repo, "status", "--porcelain", check=False):
        print("====拒绝发版====: 工作区有未提交变更——先 commit 再发版", file=sys.stderr)
        return 1
    remote = _upstream_remote(repo)
    has_local, local_sha, has_remote = _tag_state(repo, version, remote)
    #   安全校验先行（dry-run 也必须暴露）：本地 tag 已存在且不指向 HEAD = 版本号复用
    if has_local:
        head_sha = _git(repo, "rev-parse", "HEAD")[:12]
        if local_sha != head_sha:
            print(f"====拒绝发版====: {version} 已指向 {local_sha} 而非 HEAD {head_sha}"
                  f"（版本号不可变，不得复用）", file=sys.stderr)
            return 1
    need_section = not _version_section_exists(repo, version)
    if need_section and not note:
        print(f"====拒绝发版====: {version} 无版本节且未提供 --note 要点", file=sys.stderr)
        return 1
    print(f"====发版计划====: {repo.name} {version} → {remote}"
          + (f" + 镜像 {','.join(also)}" if also else ""))
    print(f"  版本节：{'新建' if need_section else '已存在（跳过建节，补推场景）'}｜"
          f"tag：{'新建' if not has_local else f'已存在@{local_sha}'}｜"
          f"远程：{'已有' if has_remote else '待推'}")
    if dry_run:
        print("====预览结束====: --dry-run 未执行任何变更")
        return 0
    #   2. 建版本节并提交（已有节则跳过——幂等重入）
    if need_section:
        _append_version_section(repo, version, note)
        _git(repo, "add", "CHANGELOG.md")
        _git(repo, "commit", "-m", f"chore(release): 发版 {version}——版本节+发版 tag")
    #   3. 打 tag（指向核对已前置到安全校验，此处仅新建）
    if not has_local:
        _git(repo, "tag", version)
        print(f"====tag已打====: {version} @ HEAD")
    #   4. 推发版 tag 到上游远程与镜像（镜像失败不回滚，如实上报）
    failed = [remote] if not _push_tag(repo, remote, version) else []
    failed += [m for m in also if not _push_tag(repo, m, version)]
    if failed:
        print(f"====tag推送失败====: {','.join(failed)}——请排查后手动补推 "
              f"git push <远程> {version}", file=sys.stderr)
        return 1
    print(f"====发版完成====: {version} 可回看（git show {version} --stat）")
    return 0


def _push_tag(repo: Path, remote: str, version: str) -> bool:
    """把发版 tag 推送到指定远程（分支提交须已在该远程，tag 超前会如实报错）。

    Args:
        repo: 目标仓库根目录路径。
        remote: 远程名。
        version: 版本号（v 前缀）。
    Returns:
        True 成功；False 失败（stderr 由 git 打印）。
    """
    print(f"====tag推送====: git push {remote} {version}")
    result = subprocess.run(
        ["git", "-C", str(repo), "push", remote, version],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode == 0


def main() -> int:
    """命令行入口：解析参数并执行发版流程。

    Returns:
        进程退出码（0 成功 / 1 失败 / 2 参数错误）。
    """
    parser = argparse.ArgumentParser(
        description="发版记录：CHANGELOG 版本节 + v tag + 推 tag（与 push_record 分离）")
    parser.add_argument("--repo", required=True, help="目标仓库根目录路径")
    parser.add_argument("--version", required=True, help="发版版本号（vX.Y.Z 或 X.Y.Z）")
    parser.add_argument("--note", default="", help="发版要点（首次建节必填）")
    parser.add_argument("--also", default="", help="镜像远程名（逗号分隔，如 github）")
    parser.add_argument("--dry-run", action="store_true", help="只预览不执行")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"====拒绝执行====: {repo} 不是 git 仓库")
        return 2
    also = [m.strip() for m in args.also.split(",") if m.strip()]
    try:
        return release(repo, args.version, args.note, also, args.dry_run)
    except subprocess.CalledProcessError as exc:
        print(f"====执行失败====: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

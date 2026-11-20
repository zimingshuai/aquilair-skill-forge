"""推送即版本记录工具（三仓统一推送制度）。

用途：把每次 git push 变成可记录、可回退的版本锚点——自动完成
「生成推送序号 tag（push/YYYY-MM-DD.N）→ CHANGELOG.md 追加记录节 →
提交记录 → 推送分支与 tag」四步，替代裸 push，杜绝漏记漏锚点。

主要 Input：--repo 目标仓库路径（必填）、--note 本次推送要点（可选）、
--also 镜像远程（可选，逗号分隔——主推送走分支上游远程，--also 额外同步推送）、
--dry-run 只预览不执行（可选）。
主要 Output：远程更新 + 本地 tag 与 CHANGELOG.md 记录节；控制台输出
中文执行日志。回退方式见 CHANGELOG.md 头部说明。
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# CHANGELOG 头部说明：制度与回退方法（各仓首次接入时由本工具 --init 生成）
_CHANGELOG_HEADER = """# 推送记录（CHANGELOG）

> 维护规则：**每次 push 走 `skill-forge/tools/push_record.py`**（打 tag `push/YYYY-MM-DD.N` +
> CHANGELOG 记一节 + 推送，三合一）——裸 push 视为违规。
> 回退方式：① 回看某次推送全量内容 `git show push/日期.序号 --stat`；② 回退单个文件/目录
> `git checkout push/日期.序号 -- <路径>`；③ 整体回退用 `git revert`（生成新提交，安全）；
> 禁用 `git reset --hard` 直推远程（违反只进不退）。
> 各节倒序排列（最新在上）；版本号不可变、只进不退。
"""


# ===========一、Git 操作封装==========
def _git(repo: Path, *args: str, check: bool = True) -> str:
    """在指定仓库执行 git 子命令并返回标准输出。

    Args:
        repo: 目标仓库根目录路径。
        *args: git 子命令及其参数（如 "log", "--oneline", "-3"）。
        check: 为 False 时命令失败不抛异常，返回空串。
    Returns:
        去除首尾空白的标准输出；check=False 且失败时返回空串。
    Raises:
        subprocess.CalledProcessError: check=True 且命令返回非零时抛出。
    """
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, "git " + " ".join(args), result.stderr
        )
    return result.stdout.strip()


def _unpushed_commits(repo: Path) -> list:
    """收集目标仓库当前未推送的提交（上游分支到 HEAD 之间）。

    Args:
        repo: 目标仓库根目录路径。
    Returns:
        [(短哈希, 提交标题), ...] 按时间正序（旧在前）；无上游分支返回 None。
    """
    #   1. 确认分支存在上游；无上游（从未推送）返回 None 由调用方提示
    upstream = _git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name",
                    "@{u}", check=False)
    if not upstream:
        return None
    #   2. 逐行解析 @{u}..HEAD 的提交清单
    lines = _git(repo, "log", "--pretty=%h|%s", "@{u}..HEAD").splitlines()
    return [tuple(line.split("|", 1)) for line in lines if "|" in line]


def _push_remote(repo: Path, remote: str, branch: str, tag_name: str) -> bool:
    """向指定远程推送分支与锚点 tag，返回是否成功（镜像同步用）。

    Args:
        repo: 目标仓库根目录路径。
        remote: 远程名（须已配置）。
        branch: 分支名。
        tag_name: 锚点 tag 名。
    Returns:
        True 推送成功；False 失败（stderr 已由 git 打印，此处仅返回判定）。
    """
    print(f"====镜像推送====: git push {remote} {branch} {tag_name}")
    result = subprocess.run(
        ["git", "-C", str(repo), "push", remote, branch, tag_name],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode == 0


# ===========二、锚点序号与记录生成==========
def _next_tag(repo: Path, today: str) -> str:
    """计算当天下一个推送锚点序号（push/YYYY-MM-DD.N）。

    Args:
        repo: 目标仓库根目录路径。
        today: 今日日期字符串（YYYY-MM-DD）。
    Returns:
        形如 push/2026-11-20.1 的 tag 名；同日已有 N 个则返回 N+1。
    """
    #   1. 取已有同名前缀 tag，取最大序号 +1；无则 .1
    prefix = f"push/{today}."
    existing = _git(repo, "tag", "--list", f"{prefix}*", check=False).splitlines()
    max_seq = 0
    for tag_name in existing:
        seq = tag_name[len(prefix):]
        if seq.isdigit():
            max_seq = max(max_seq, int(seq))
    return f"{prefix}{max_seq + 1}"


def _build_section(tag_name: str, commits: list, note: str) -> str:
    """拼装一次推送的 CHANGELOG 记录节（Markdown）。

    Args:
        tag_name: 本次推送锚点 tag 名。
        commits: [(短哈希, 标题), ...] 未推送提交清单（时间正序）。
        note: 用户提供的推送要点；空串时省略要点行。
    Returns:
        可直接插入 CHANGELOG 顶部的 Markdown 文本块。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"## {tag_name}（{now}）｜{len(commits)} commits"]
    for short_hash, subject in commits:
        lines.append(f"- `{short_hash}` {subject}")
    if note:
        lines.append(f"> 要点：{note}")
    return "\n".join(lines) + "\n"


def _prepend_changelog(repo: Path, section: str) -> None:
    """把记录节插入 CHANGELOG 顶部（倒序），无文件时先落制度头。

    Args:
        repo: 目标仓库根目录路径。
        section: 已拼装好的记录节文本。
    Returns:
        None。文件以 UTF-8 无 BOM 写回。
    """
    changelog = repo / "CHANGELOG.md"
    if changelog.exists():
        old = changelog.read_text(encoding="utf-8")
        #   1. 已有文件：在首个「## 」节之前插入新节，保持倒序
        idx = old.find("\n## ")
        insert_at = idx + 1 if idx != -1 else len(old.rstrip()) + 1
        new = old[:insert_at] + section + "\n" + old[insert_at:]
    else:
        #   2. 首次接入：制度头 + 首节
        new = _CHANGELOG_HEADER + "\n" + section + "\n"
    changelog.write_text(new, encoding="utf-8", newline="")


# ===========三、主流程（推送即版本）==========
def push_with_record(repo: Path, note: str, dry_run: bool, also: list) -> int:
    """执行推送即版本主流程：收集提交 → 记录 → 提交 → tag → 推送。

    Args:
        repo: 目标仓库根目录路径。
        note: 推送要点（可为空串）。
        dry_run: True 时只打印将执行的动作，不产生任何变更。
        also: 镜像远程名列表（可为空）——主推送走分支上游远程（自动适配 gitlab/origin
              等各仓命名，不硬编码），镜像在主推送成功后逐个同步推送。
    Returns:
        进程退出码：0 成功；1 无未推送提交或执行失败。
    """
    #   1. 收集未推送提交；为空或无上游则拒绝执行（负向保护）
    commits = _unpushed_commits(repo)
    if not commits:
        reason = "分支无上游跟踪" if commits is None else "没有未推送的提交"
        print(f"====拒绝推送====: {repo.name} {reason}，无需记录")
        return 1
    tag_name = _next_tag(repo, datetime.now().strftime("%Y-%m-%d"))
    section = _build_section(tag_name, commits, note)
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    note_suffix = f"（要点：{note}）" if note else ""
    #   upstream_remote：上游远程名（@{u} 形如 gitlab/master，取斜杠前段）——适配各仓命名
    upstream = _git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    upstream_remote = upstream.split("/", 1)[0]
    mirror_suffix = f" + 镜像 {','.join(also)}" if also else ""
    print(f"====推送计划====: {repo.name} 分支 {branch} → {upstream_remote}{mirror_suffix}，"
          f"锚点 {tag_name}，{len(commits)} 个提交{note_suffix}")
    for short_hash, subject in commits:
        print(f"  {short_hash} {subject}")
    if dry_run:
        print("====预览结束====: --dry-run 未执行任何变更")
        return 0
    #   2. 写记录节并提交（记录提交自身不在清单内，属记账动作）
    _prepend_changelog(repo, section)
    _git(repo, "add", "CHANGELOG.md")
    _git(repo, "commit", "-m", f"chore(push): 记录 {tag_name}（{len(commits)} commits）")
    #   3. 打锚点 tag（指向含记录的提交）并连同分支一起推送
    _git(repo, "tag", tag_name)
    print(f"====推送执行====: git push {upstream_remote} {branch} {tag_name}")
    _git(repo, "push", upstream_remote, branch, tag_name)
    #   镜像同步：主仓锚点已立，镜像失败不回滚主推，但必须如实上报（不静默吞掉）
    failed_mirrors = [m for m in also
                      if not _push_remote(repo, m, branch, tag_name)]
    print(f"====推送完成====: 锚点 {tag_name} 已可回退（git show {tag_name} --stat）")
    if failed_mirrors:
        print(f"====镜像失败====: {','.join(failed_mirrors)} 同步失败——主仓已推送成功，"
              f"请排查该镜像网络/权限后手动补推：git push <镜像> {branch} {tag_name}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    """命令行入口：解析参数并执行推送即版本流程。

    Returns:
        进程退出码（0 成功 / 1 失败 / 2 参数错误）。
    """
    parser = argparse.ArgumentParser(
        description="推送即版本：tag + CHANGELOG + push 三合一（替代裸 push）")
    parser.add_argument("--repo", required=True, help="目标仓库根目录路径")
    parser.add_argument("--note", default="", help="本次推送要点（记入 CHANGELOG）")
    parser.add_argument("--dry-run", action="store_true", help="只预览不执行")
    parser.add_argument("--also", default="", help="镜像远程（逗号分隔，如 github；主推送走上游远程）")
    args = parser.parse_args()
    # resolve()：把相对路径（如 .）转为绝对路径，保证仓库名显示正确
    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"====拒绝执行====: {repo} 不是 git 仓库")
        return 2
    #   also 解析与远程名合法性校验（臆造远程名直接拒绝，防镜像静默漏推）
    also = [m.strip() for m in args.also.split(",") if m.strip()]
    if also:
        remotes = _git(repo, "remote").split()
        bad = [m for m in also if m not in remotes]
        if bad:
            print(f"====拒绝执行====: 镜像远程不存在 {','.join(bad)}——已配置远程: {' '.join(remotes)}")
            return 2
    try:
        return push_with_record(repo, args.note, args.dry_run, also)
    except subprocess.CalledProcessError as exc:
        print(f"====执行失败====: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

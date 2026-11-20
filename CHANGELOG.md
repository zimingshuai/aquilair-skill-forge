# 推送记录（CHANGELOG）

> 维护规则：**每次 push 走 `skill-forge/tools/push_record.py`**（打 tag `push/YYYY-MM-DD.N` +
> CHANGELOG 记一节 + 推送，三合一）——裸 push 视为违规。
> 回退方式：① 回看某次推送全量内容 `git show push/日期.序号 --stat`；② 回退单个文件/目录
> `git checkout push/日期.序号 -- <路径>`；③ 整体回退用 `git revert`（生成新提交，安全）；
> 禁用 `git reset --hard` 直推远程（违反只进不退）。
> 各节倒序排列（最新在上）；版本号不可变、只进不退。

## push/2026-11-20.1（2026-11-20 10:31）｜1 commits
- `7335e9d` feat(tools): 推送即版本工具 push_record.py——tag+CHANGELOG+push 三合一替代裸 push（负向测试 2/2 通过：已同步拒绝/非 git 拒绝）
> 要点：推送记录制度首用：工具自身上线（狗粮首例），此后三仓 push 一律走本工具


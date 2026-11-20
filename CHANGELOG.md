# 推送记录（CHANGELOG）

> 维护规则：**每次 push 走 `skill-forge/tools/push_record.py`**（打 tag `push/YYYY-MM-DD.N` +
> CHANGELOG 记一节 + 推送，三合一）——裸 push 视为违规。
> 回退方式：① 回看某次推送全量内容 `git show push/日期.序号 --stat`；② 回退单个文件/目录
> `git checkout push/日期.序号 -- <路径>`；③ 整体回退用 `git revert`（生成新提交，安全）；
> 禁用 `git reset --hard` 直推远程（违反只进不退）。
> 各节倒序排列（最新在上）；版本号不可变、只进不退。

## push/2026-11-20.4（2026-11-20 10:54）｜1 commits
- `084645d` fix(tools): push_record 推上游远程替代硬编码 origin——适配各仓远程命名(gitlab/github/origin)；新增 --also 镜像同步参数(逗号分隔+远程名合法性校验,镜像失败不回滚主推但如实上报)；推送计划行显示目标远程(dry-run 可验证命令构造)；负向臆造远程实测拒绝+ontology 临时分支 dry-run 实测 gitlab+镜像解析正确
> 要点：push_record 上游适配修复：origin 硬编码→upstream 远程名+--also 镜像；负向/正向 dry-run 双测通过

## push/2026-11-20.3（2026-11-20 10:42）｜1 commits
- `023d8fb` docs(authoring): 接线步补 MCP 双环境约定（dev 仓 aquilair-mcp-servers-dev / 发版仓 aquilair-mcp-servers，技能内不写死端点）
> 要点：MCP 双环境约定入工厂接线规范

## push/2026-11-20.2（2026-11-20 10:31）｜1 commits
- `eb2da2f` fix(tools): push_record 相对路径 resolve——仓名显示为空修复
> 要点：修复相对路径仓名显示；验证同日序号递增（.2）

## push/2026-11-20.1（2026-11-20 10:31）｜1 commits
- `7335e9d` feat(tools): 推送即版本工具 push_record.py——tag+CHANGELOG+push 三合一替代裸 push（负向测试 2/2 通过：已同步拒绝/非 git 拒绝）
> 要点：推送记录制度首用：工具自身上线（狗粮首例），此后三仓 push 一律走本工具


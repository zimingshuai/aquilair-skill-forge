# 推送记录（CHANGELOG）

> 维护规则：**每次 push 走 `skill-forge/tools/push_record.py`**（打 tag `push/YYYY-MM-DD.N` +
> CHANGELOG 记一节 + 推送，三合一）——裸 push 视为违规。
> 回退方式：① 回看某次推送全量内容 `git show push/日期.序号 --stat`；② 回退单个文件/目录
> `git checkout push/日期.序号 -- <路径>`；③ 整体回退用 `git revert`（生成新提交，安全）；
> 禁用 `git reset --hard` 直推远程（违反只进不退）。
> 各节倒序排列（最新在上）；版本号不可变、只进不退。

## push/2026-11-20.6（2026-11-20 13:36）｜3 commits
- `04f2372` fix(tools): release_record rev-parse 加 --verify——不存在 tag 被回显原文误判为存在（实测坑）
- `4844618` fix(tools): release_record 版本号复用校验前置到 dry-run 之前（安全校验必须预览期暴露）
- `3e12db0` feat(tools): 发布工具 release_record——版本节+v tag+推 tag 与推送记录分离（push 是 push、发布是发布）；push_record 回滚 v-tag 随推方向保持纯推送语义
> 要点：发布工具 release_record 上线（push/release 分离）；含 --verify 与复用校验前置两修复

## push/2026-11-20.5（2026-11-20 11:38）｜1 commits
- `6acc354` chore(release): 发版 v0.3.0——CHANGELOG 版本节+发版 tag
> 要点：发版 v0.3.0（业务锻造师：模板三件套+推送工具+新范式）

## v0.3.0（2026-11-20）｜发版 tag `v0.3.0`
- **工厂模板三件套（试点）**：skeleton 机制骨架（规则驱动推理/未知出口/分页取齐/编排模式字段，launch v0.3.1 抽象）/ delivery-assets 交付基线（v0.4.3 口径+渲染四件，出厂整目录 fork）/ knowledge-criteria 三类知识判据卡；治理=模板改动仅用户发起、脚本缺陷维护同步、规范口径走用户（4278e20/6033407）
- **推送即版本工具 push_record.py**：tag+CHANGELOG+push 三合一替代裸 push（含 --also 镜像/上游远程自适应，负向测试通过）
- **authoring 新范式升级**：探查循环六步（元数据四类定义推理/定义先行缓存/分页取齐/未知出口）+ refs 两件套 + 打法退役判据 + MCP 双环境约定（dev 仓 aquilair-mcp-servers-dev / 发版仓 aquilair-mcp-servers）入接线步

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


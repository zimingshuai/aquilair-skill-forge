# 推送记录（CHANGELOG）

> 维护规则：**每次 push 走 `skill-forge/tools/push_record.py`**（打 tag `push/YYYY-MM-DD.N` +
> CHANGELOG 记一节 + 推送，三合一）——裸 push 视为违规。
> 回退方式：① 回看某次推送全量内容 `git show push/日期.序号 --stat`；② 回退单个文件/目录
> `git checkout push/日期.序号 -- <路径>`；③ 整体回退用 `git revert`（生成新提交，安全）；
> 禁用 `git reset --hard` 直推远程（违反只进不退）。
> 各节倒序排列（最新在上）；版本号不可变、只进不退。

## v0.3.3（2026-11-26）｜发版 tag `v0.3.3`
skeleton 删独立「可视化交付」节——按 jimi-sdb v2.5.2 实证形态（出图全在输出规范条目承载）；落档位置与通道指引并入选型条，通道细节归 delivery.md（用户裁决）

## push/2026-11-26.1（2026-11-26 10:07）｜3 commits
- `336f252` chore(release): 发版 v0.3.2——版本节+发版 tag
- `a8ccefe` chore(release): 升版 v0.3.2——多宿主六清单版本号推进（jimi-sdb 骨架基线重写随版发布）
- `4a64729` feat(templates): skeleton 以 jimi-sdb v2.5.2 为骨架基线重写——铁律子条目化、写确认参数不跨卡/幂等批量/分桶回查、溯源链结构化标记、reviewed_on 复核字段、可视化交付通道选型（渲染脚本/宿主 widget 内联）+ template.md 呼应（样板登记 jimi-sdb、五子键、双基线措辞）
> 要点：发版 v0.3.2：skeleton 骨架基线以 jimi-sdb v2.5.2 重写（铁律子条目化/写确认深化/溯源链结构化/reviewed_on/交付通道选型）+ template.md 呼应登记

## v0.3.2（2026-11-26）｜发版 tag `v0.3.2`
skeleton 骨架基线以 jimi-sdb v2.5.2 重写——铁律子条目化/写确认参数不跨卡与幂等批量/溯源链结构化标记/reviewed_on 复核字段/可视化交付通道选型（渲染脚本 vs 宿主 widget 内联）；template.md 呼应（样板登记 jimi-sdb、五子键、双基线措辞）

## push/2026-11-24.2（2026-11-24 18:14）｜2 commits
- `b35b4fe` chore(release): 发版 v0.3.1——版本节+发版 tag
- `af10038` chore(release): 升版 v0.3.1——多宿主六清单版本号推进（判据卡七节+渲染基线升级随版发布）
> 要点：发版 v0.3.1：判据卡七节+渲染基线升级随版发布（升版 commit + 版本节 commit），WorkBuddy 副本随刷新迁至 v0.3.1

## v0.3.1（2026-11-24）｜发版 tag `v0.3.1`
- **判据卡升级知识取舍七节**：逐句通式 / 五类可删 / 删除四纪律 / 出处标注底线（jimi-sdb 二轮清理教训沉淀）

## push/2026-11-24.1（2026-11-24 18:07）｜3 commits
- `ee3b2f0` feat(templates): delivery-assets 渲染基线升级——spec 校验+树图/瀑布图+标签防重叠+类型/示例命令
- `d008ec6` docs(authoring): 判据卡升级为知识取舍七节——逐句通式+五类可删+四条删除纪律+出处标注底线
- `1152541` docs(authoring): 吸收插件结构五裁决——接线步改版+agent-shell 薄壳模板+模板目录更新
> 要点：判据卡升级知识取舍七节（逐句通式/五类可删/删除四纪律，极米二轮清理教训沉淀）；delivery-assets 渲染基线升级（spec 校验/树图瀑布图/标签防重叠/类型示例命令）——含积压的五裁决吸收一并在推

## push/2026-11-23.1（2026-11-23 10:28）｜2 commits
- `cf3d396` feat(tools): lint C9 跨仓提及豁免机制——.mcp-crossref.json 清单+死豁免 WARN 兜底+解析失败 fail-closed
- `a26bba2` docs(authoring): AGT-4 漂移扫描工序固化——runtime 版本变更→技能同步六步例行工序
> 要点：AGT-4 漂移扫描工序固化（drift-scan.md 六步+11-20 实例锚定）；lint C9 跨仓提及豁免（.mcp-crossref.json+死豁免 WARN+fail-closed，负向双测过）

## push/2026-11-20.7（2026-11-20 16:42）｜1 commits
- `0e82412` fix(manifest): 双 marketplace 清单版本对齐 0.3.0（.claude 0.2.2 / .codebuddy 0.2.1 均落后源 0.3.0——中台阶段一 /api/matrix 首跑抓到的漂移，同类先例 business-hub marketplace 对齐）
> 要点：中台首跑抓漂移：skill-forge 双 marketplace 0.2.2/0.2.1→0.3.0 对齐

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


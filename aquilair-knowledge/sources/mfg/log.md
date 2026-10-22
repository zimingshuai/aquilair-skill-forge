# mfg 域摄取/变更日志（log）

> 每次摄取、再摄取、query 归档或 lint 巡检追加一条。**条目统一前缀** `## [YYYY-MM-DD] 类型 | 标题`（类型：ingest/query/lint/re-ingest），`grep "^## \[" log.md | tail -5` 即取最近 5 条——lint「过时检查」与再摄取对照以此为准。

## [2026-09-28] ingest | 溯源区初始化与首次编译

- 动作：从 `.meta-cache`（2026-09-16 拉取）编译 glossary（10 实体术语）；建 index；技能侧 kpi-caliber.md 补出处标注（4 条口径，来源：实测 2026-09-16）
- 影响页：glossary.md、index.md、技能 kpi-caliber.md

## [2026-09-29] ingest | 域总览页首建

- 动作：新建 overview.md（域定位与状态、关键口径速览、演进脉络、已知缺口）
- 影响页：overview.md 新建、index.md 加行

## [2026-10-22] re-ingest | MCP 接口迁移统一网关（服务端变更同步）

- 背景：服务端将旧单体 `data-service-mfg-sandbox`（aquilair-mcp1 域名）下线，收敛为统一网关 `aquilair-mcp`（https://aquilair.idcs.elitescloud.com/mcp-service/mcp，OAuth Bearer 鉴权，多本体项目单端点）
- 实测：mfg workspace=`01a03bb7-2da4-7000-8dcf-1fb48f6f7fc9`（「demo（勿动！！）」制造业工厂调拨 v1.21.0，10 对象 12 关系，模型与旧服务一致）；action-service 未部署动作（actions_list 404），旧 8 个 Action 待就绪
- 变更：技能工具面换 metadata_*/objects_*/actions_*（refCode 引用体系 + ObjectSet DSL）；沙箱语义改数据分支（objects_create_branch/compare_branch）；fetch_meta.py 重构（凭证三通道 + workspace 固化）；旧 .meta-cache 清除待凭证重建
- 影响页：overview.md、README.md、index.md、glossary.md（What-if 沙箱术语）、技能 SKILL.md/references×3/evals

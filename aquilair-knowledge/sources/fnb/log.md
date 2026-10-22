# fnb 域摄取/变更日志（log）

> 条目统一前缀 `## [YYYY-MM-DD] 类型 | 标题`（类型：ingest/query/lint/re-ingest），可被 `grep "^## \[" log.md` 解析。

## [2026-09-29] ingest | 编译层三件初始化与 overview 首建

- 动作：从 `.meta-cache`（2026-09-16 拉取）编译 glossary（15 实体术语 + 5 流程术语）；建 index、log、overview
- 脏数据发现：`InventoryRisk` 的 display_name 与 `ForecastSalesTrace` 重复（疑似服务端缺陷），已在 glossary 标注待业务方确认
- 前置：技能侧 playbook.md 已于 2026-09-28 由用户补出处标注（4 处，实测 2026-09-16）
- 影响页：glossary.md、index.md、log.md、overview.md、README.md（存量声明更新）

## [2026-10-22] re-ingest | MCP 接口迁移统一网关（服务端变更同步）

- 背景：服务端将旧单体 `data-service-fnb`（aquilair-mcp0 域名）下线，收敛为统一网关 `aquilair-mcp`（https://aquilair.idcs.elitescloud.com/mcp-service/mcp，OAuth Bearer 鉴权，多本体项目单端点）
- 实测：fnb workspace=`019fd9ed-8715-7000-8f28-0a14f59c5563`（「demo（勿动！）」餐饮业库存分析 v1.74.0，17 对象 14 关系，模型与旧服务一致）；objects_query 数据面复测通过（WH001 上海中心仓等）
- 变更：技能工具面换 metadata_*/objects_*（refCode 引用体系 + ObjectSet DSL）；fetch_meta.py 重构（凭证三通道 + workspace 固化）；旧 .meta-cache 清除待凭证重建
- 影响页：overview.md、README.md、index.md、glossary.md（只读诊断术语）、技能 SKILL.md/playbook.md/evals

# fnb 域摄取/变更日志（log）

> 条目统一前缀 `## [YYYY-MM-DD] 类型 | 标题`（类型：ingest/query/lint/re-ingest），可被 `grep "^## \[" log.md` 解析。

## [2026-09-29] ingest | 编译层三件初始化与 overview 首建

- 动作：从 `.meta-cache`（2026-09-16 拉取）编译 glossary（15 实体术语 + 5 流程术语）；建 index、log、overview
- 脏数据发现：`InventoryRisk` 的 display_name 与 `ForecastSalesTrace` 重复（疑似服务端缺陷），已在 glossary 标注待业务方确认
- 前置：技能侧 playbook.md 已于 2026-09-28 由用户补出处标注（4 处，实测 2026-09-16）
- 影响页：glossary.md、index.md、log.md、overview.md、README.md（存量声明更新）

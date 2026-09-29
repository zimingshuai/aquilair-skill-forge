# mfg 域摄取/变更日志（log）

> 每次摄取、再摄取、query 归档或 lint 巡检追加一条。**条目统一前缀** `## [YYYY-MM-DD] 类型 | 标题`（类型：ingest/query/lint/re-ingest），`grep "^## \[" log.md | tail -5` 即取最近 5 条——lint「过时检查」与再摄取对照以此为准。

## [2026-09-28] ingest | 溯源区初始化与首次编译

- 动作：从 `.meta-cache`（2026-09-16 拉取）编译 glossary（10 实体术语）；建 index；技能侧 kpi-caliber.md 补出处标注（4 条口径，来源：实测 2026-09-16）
- 影响页：glossary.md、index.md、技能 kpi-caliber.md

## [2026-09-29] ingest | 域总览页首建

- 动作：新建 overview.md（域定位与状态、关键口径速览、演进脉络、已知缺口）
- 影响页：overview.md 新建、index.md 加行

# fnb 域知识页索引（index）

> 域知识库导航：query 先读本索引再钻取页面。再摄取时由 LLM 更新。

## 原始层（raw）

`raw/` 目前为空——本域开发于溯源区设立（2026-09-28）之前，原始源文档未留档。业务方补充文档后落位于此并逐份登记。

## 编译层

| 知识资产 | 位置 | 一行摘要 |
| --- | --- | --- |
| 域总览 | [`overview.md`](overview.md) | 当前全局理解：域状态、关键口径速览、演进脉络（每次摄取后更新） |
| 域术语表 | [`glossary.md`](glossary.md) | 15 实体术语 + 流程术语（P0-P3/溯源链/ABC），含 1 处元数据疑似缺陷记录 |
| 摄取日志 | [`log.md`](log.md) | 摄取/再摄取变更记录（可机读前缀） |

## 技能资产侧（编译进技能的知识）

| 知识资产 | 位置 | 一行摘要 |
| --- | --- | --- |
| 查询剧本与输出模板 | `skills/fnb-inventory-analysis/references/playbook.md` | 场景 A 仓群总览（L0/L1/L2）+ 场景 B 单仓/单 SKU/口径收窄；已带出处标注（2026-09-28 补） |
| 元数据缓存 | `skills/fnb-inventory-analysis/.meta-cache/` | 统一网关 model / rules / actions 原始 JSON（fetch_meta 产物；2026-10-22 起为新工具面拉取，旧 get_meta_* 缓存已废弃清除） |

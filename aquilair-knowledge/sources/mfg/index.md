# mfg 域知识页索引（index）

> 域知识库导航：原始层（raw）与编译层的位置。再摄取时由 LLM 更新本索引（流程见 `skills/aquilair-knowledge-wiki/references/ingest.md`）。

## 原始层（raw）

`raw/` 目前为空——本域开发于溯源区设立（2026-09-28）之前，原始源文档未留档。业务方补充文档后落位于此并逐份登记。

## 编译层

| 知识资产 | 位置 | 说明 |
| --- | --- | --- |
| 域总览 | [`overview.md`](overview.md) | 当前全局理解：域状态、关键口径速览、演进脉络（每次摄取后更新） |
| 域术语表 | [`glossary.md`](glossary.md) | 10 实体术语 + 流程机制术语，lint 术语检查与出题措辞依据 |
| 摄取日志 | [`log.md`](log.md) | 摄取/再摄取变更记录，过时检查依据 |
| 元数据缓存 | `skills/mfg-transfer-allocation/.meta-cache/` | 统一网关 model / rules / actions 原始 JSON（fetch_meta 产物；2026-10-22 起为新工具面拉取，旧 get_meta_* 缓存已废弃清除） |
| 实体与动作摘要 | `skills/mfg-transfer-allocation/references/actions.md` | 动作明细与参数契约（技能资产侧编译） |
| KPI 口径边界 | `skills/mfg-transfer-allocation/references/kpi-caliber.md` | 口径 Gotchas + 出处标注（2026-09-28 补） |
| 场景剧本 | `skills/mfg-transfer-allocation/references/scenarios.md` | 业务场景问答剧本（技能资产侧编译） |

> 注：技能资产侧的 references 属「编译进技能的知识」，同时存在于仓库 `skills/` 与分发包内；本索引是它们的仓库侧溯源入口。

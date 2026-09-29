# wiki 域知识页索引（index）

> 检索入口：query 先读本索引再钻取页面。再摄取时由 LLM 更新。

## 原始层（raw）

| 文档 | 一行摘要 | 入库日期 |
| --- | --- | --- |
| [`raw/llm-wiki.md`](raw/llm-wiki.md) | Karpathy 原始构想：compile 而非 retrieve——LLM 增量构建持久互联的 wiki；三层架构（raw/wiki/schema）+ 三操作（ingest/query/lint）+ index/log 双导航 + 维护成本近零是本质 | 2026-09-28 |
| [`raw/llm-wiki-methodology-by-nashsu.png`](raw/llm-wiki-methodology-by-nashsu.png) | nashsu 手绘方法论总结图：三层/三操作/index-log/角色分工（人策划、LLM 记账）/ingest 流程图（单源触及 10~15 页）/八大应用场景/核心洞察「维护瓶颈=记账，LLM 维护成本趋近零」——与已吸收知识逐项一致，零矛盾，新增量化触及面与场景清单 | 2026-09-29 |
| [`raw/llm-wiki.zh.md`](raw/llm-wiki.zh.md) | 同上文的中文全译本（raw 层原文只读不改，译本并列落位） | 2026-09-28 |

## 编译层

| 知识资产 | 位置 | 一行摘要 |
| --- | --- | --- |
| 域总览 | [`overview.md`](overview.md) | 自举域状态：两轮吸收完成，方法论已实例化 |
| 方法术语表 | [`glossary.md`](glossary.md) | 14 个 wiki 方法词汇（摄取/写时矛盾/无来源即发现…），逐条带出处 |
| 摄取日志 | [`log.md`](log.md) | 本域 ingest/归档记录 |
| 技能本体 | `skills/aquilair-knowledge-wiki/` | 思想的 Aquilair 实例化（SKILL.md + references/ingest.md 五步剧本） |

## 本域已吸收与未吸收清单（对照原文，供再摄取时复核）

**已吸收**：compile 核心理念、三层架构映射（raw=aquilair-knowledge/sources/<域>/raw、wiki=编译层、schema=SKILL.md+剧本）、ingest 五步、query（index 先行 + 坐标引用 + 答案归档 analyses/）、lint（机检+人工清单）、log 可机读前缀、git 免费版本历史（仓库天然满足）。

**未吸收（有意）**：Obsidian 生态（宿主无关原则）；qmd 向量搜索（规模未到）；类型分目录（拆分阈值未到，单域 20 页以上再启用）；sha256 源绑定自动 diff（源为人工投喂，无自动同步场景）；wiki 三层漏斗 个人→项目→组织（多域架构已天然分层）；桌面应用形态（nashsu 路线，我们走纪律+脚本零依赖路线）。

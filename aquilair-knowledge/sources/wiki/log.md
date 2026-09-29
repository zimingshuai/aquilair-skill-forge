# wiki 域摄取/变更日志（log）

> 条目统一前缀 `## [YYYY-MM-DD] 类型 | 标题`（类型：ingest/query/lint/re-ingest），可被 `grep "^## \[" log.md` 解析。

## [2026-09-28] ingest | Karpathy《LLM Wiki》原文入库与差距吸收

- 原文落位 `raw/llm-wiki.md`（用户提供 Downloads 副本，75 行全文）
- 差距吸收：query 节补「好答案归档 analyses/」（原文 good answers filed back）、检索顺序改 index 先行、log 条目统一可机读前缀（本条即示范）
- 影响页：skills/aquilair-knowledge-wiki/SKILL.md、references/ingest.md、aquilair-knowledge/sources/mfg/log.md（格式迁移）

## [2026-09-28] ingest | 《LLM Wiki》中文译本落位

- 英文原文只读不改（raw 层纪律），中文全译本并列落位 `raw/llm-wiki.zh.md`；术语与仓库统一（ingest=摄取、query=查询、lint=巡检）
- 用户需求：源文档需中文可读
- 影响页：本域 README.md（源文档段落）、index.md（原始层表）

## [2026-09-29] ingest | gist 评论区实战教训二轮吸收 + 目录结构对齐

- 触发：用户提供 gist/balukosuri/nashsu 三源，指出社区目录结构更清晰
- 工程纪律吸收（评论区）：文档注入防御、写时矛盾处理、无来源即发现（lint C11 机检落地）、教训放必读处（事实卡片两级去向）、事件驱动巡检、audit 干净会话审查
- 目录结构吸收（nashsu/balukosuri）：overview 域总览页型（mfg 首建示范）、purpose 显式分离（三域 README 补段）、页面拆分阈值 20 条约定
- 影响页：knowledge-wiki SKILL.md（权限边界+2 条）、references/ingest.md、authoring references/lint.md、tools/lint_skills.py（C11）、sources/README.md、mfg overview.md 新建、wiki glossary.md 新建

## [2026-09-29] ingest | nashsu 方法论总结图入库（图片源）

- 原名 4fcf7e97-3594-43b9-8f30-9ca7d5a3afeb.png（UUID 不可读，语义重命名 llm-wiki-methodology-by-nashsu.png，原格式保留）
- 视觉读图（多模态提取）→ 判类型：方法论总结图 → 归 wiki 域
- 写时矛盾检查：与既有知识逐项比对零矛盾；新增「记账瓶颈」「单源触及面 10~15 页」两条术语（带图出处）
- 影响页：raw/ 新增、index.md 加行、glossary.md +2 术语

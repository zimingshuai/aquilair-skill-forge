# npi 域知识页索引（index）

> 域知识库导航：原始层（raw）与编译层的位置。再摄取时由 LLM 更新本索引（流程见 aquilair-knowledge-wiki 的 ingest 剧本）。

## 原始层（raw）

| 源文档 | 文件 | 拉取信息 |
| --- | --- | --- |
| 本体模型实体对象v2.0 | [`raw/本体模型实体对象v2.0.md`](raw/本体模型实体对象v2.0.md) | 飞书 wiki NEswwEZaJivCqLkreCycHOnpnYe，2026-11-03 lark-cli 拉取（31 实体+规则+动作设计） |
| NP009 POC 演示故事线（带查询） | [`raw/NP009_POC_Demo_Storyline_With_Queries.md`](raw/NP009_POC_Demo_Storyline_With_Queries.md) | 飞书 wiki ZoO3wngdLi5gEpkTzCmcqU2dnwe，2026-11-03 拉取（S01~S07 场景） |
| 动作与关联函数 | [`raw/动作与关联函数.md`](raw/动作与关联函数.md) | 飞书 wiki IqljwBAUciXszBkoxKqcc8IIn3d，2026-11-03 拉取（fn_* 函数定义） |
| 新品上市POC业务背景与功能说明 | [`raw/新品上市POC业务背景与功能说明.md`](raw/新品上市POC业务背景与功能说明.md) | 飞书 wiki MSYxwzdkAiDhDLkaHyNc3G78nFc，2026-11-03 拉取 |
| 旧技能 playbook（launch-readiness-diagnosis） | [`raw/launch-readiness-diagnosis_skills旧版playbook.md`](raw/launch-readiness-diagnosis_skills旧版playbook.md) | 飞书 wiki RB79wBXxaio1sGkSLt9ceiNKntc，2026-11-03 拉取（旧项目六类齐套诊断程序，退役过渡期备查） |

## 编译层

| 知识资产 | 位置 | 说明 |
| --- | --- | --- |
| 域总览 | [`overview.md`](overview.md) | 当前全局理解：两代项目状态、关键口径速览（每次摄取后更新） |
| 域术语表 | [`glossary.md`](glossary.md) | 21 实体术语 + 流程口径术语 + 新旧项目对照（lint 术语检查与出题措辞依据） |
| 摄取日志 | [`log.md`](log.md) | 摄取/再摄取变更记录，过时检查依据 |

## 编译层与技能的对应

- 新项目（新品上市POC-最新版）行为细则：aquilair-launch-poc 仓 `plugins/launch-poc/skills/launch-dynamic-assurance/references/`（facts/domain-model/storyline-playbook）——元数据与实时数据以 MCP 实时查询为唯一权威，本域知识页仅作语义编译与溯源。

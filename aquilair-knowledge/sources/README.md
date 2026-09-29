# 源文档溯源区（raw 区）

> 设计参照 Karpathy LLM Wiki 的 `raw/` 与 `wiki/` 分离：源文档是业务方的原始口径（只读不改），`skills/*/references/` 是从源文档与实测编译出的技能资产（可迭代）。调研背景见 [aquilair-knowledge/research/2026-09-28-llm-wiki-karpathy.md](../research/2026-09-28-llm-wiki-karpathy.md)。**使用速查（喂文档/查出处/再摄取六场景）见 [../USAGE.md](../USAGE.md)**。

## 目录约定

每个业务域一个子目录。**域知识库 = 原始层 + 编译层**（摄取流程见 `skills/aquilair-knowledge-wiki/references/ingest.md`，用户上传文档 + 提供 MCP 地址，LLM 自主摄取编译）：

```
aquilair-knowledge/sources/
  README.md        # 本文件：纪律与出处标注格式
  <业务域名>/
    README.md      # 域说明（人工维护，含 purpose：本域关键问题/范围/演进论点）
    raw/           # 原始层：业务方文档原样落位（只读不改）
    overview.md    # 编译层：域总览（当前全局理解，每次摄取后更新）
    glossary.md    # 编译层：域术语表（LLM 摄取编译）
    index.md       # 编译层：知识页索引（LLM 摄取编译）
    log.md         # 编译层：摄取/变更日志（LLM 追加）
    analyses/      # 编译层：query 好答案归档的分析页（探索复利）
```

源文档**保留原格式原名**（可读性优先，不强制转 markdown）；同域多版本时旧版放 `archive/` 子目录，不覆盖。编译层由 LLM 在摄取/再摄取时维护，人工只裁定不代写。

**页面拆分阈值**：域内编译条目（术语/实体/概念）平铺在 glossary 与 analyses 即可；单域知识页累计超过 20 个文件时，才启用类型分目录（`entities/` `concepts/` `analyses/` 等，参照 llm-wiki 社区形态）——规模不到先平铺，不为结构感建空目录。

## 三条纪律（进入流水线即生效）

1. **只读**：源文档是业务方原始口径，只读不改；要改口径 = 业务方换入新文档，由 references 侧消化吸收。
2. **落位**：新业务域第 5 步接线时，业务知识源文档必须落位 `aquilair-knowledge/sources/<域名>/`（见 `aquilair-skill-authoring` 第 5 步「接线五处」）。
3. **标注**：references 中的口径、事实卡片、KPI 边界**逐条标注出处**，格式二选一：

```
（来源：aquilair-knowledge/sources/mfg/口径说明v2.pdf §3，实测 2026-09-28）
（来源：实测 2026-09-28，get_meta_rules）
```

- 有源文档：标源文档相对路径 + 小节，可附带实测日期；
- 无源文档（存量技能或纯实测结论）：标「实测 YYYY-MM-DD + 工具/接口名」——实测记录本身就是出处。

## 知识库与分发

本目录（`aquilair-knowledge/sources/`）连同 `aquilair-knowledge/research/`（决策记录）与各技能 `references/`（编译进技能的知识）共同构成 Aquilair 知识库。分发路线两条：

- **插件市场路线**（ZCode / Claude Code / Codex）：整个插件仓库分发，`docs/` 随包走，知识库完整。
- **逐技能 zip 路线**（`tools/pack_skill.py`，其他 Agent Skills 客户端）：`aquilair-knowledge/sources/` 被 pack_skill 整区收录进每个 zip，**zip 内保持 `aquilair-knowledge/sources/` 同名坐标**——references 里的出处标注在分发包内可直接解析，溯源链不断。`aquilair-knowledge/research/` 属开发侧决策记录，不进技能 zip。

references 中的出处标注统一写**仓库坐标**（如 `aquilair-knowledge/sources/mfg/口径说明.pdf §3`），不写运行时相对路径链接——仓库结构与 zip 结构的相对层级不同，坐标式写法在两边都成立。

## 存量声明

fnb / mfg 两域技能开发于本溯源区设立（2026-09-28）之前，原始源文档未留档——两域 references 的出处以「实测」标注为准；后续业务方补充文档时补录进对应域目录。

# fnb 域源文档

餐饮供应链（统一 MCP 网关 `aquilair-mcp` 的 fnb 本体项目；2026-10-22 前为单体服务 `data-service-fnb`）域的知识库（原始层 + 编译层，结构见 [`../README.md`](../README.md)）。

## purpose（本域为什么存在）

- **关键问题**：仓库/门店库存健康如何诊断——风险分级（P0-P3）依据、周转与 ABC 分类、缺货明细与风险单溯源。
- **研究范围**：fnb 本体项目的仓群与 SKU 知识（只读诊断，无写操作）。
- **演进论点**：风险判定口径以元数据衍生属性为准，业务方分级依据文档补位后替换实测出处。

**存量声明**：本域技能 `fnb-inventory-analysis` 开发于溯源区设立（2026-09-28）之前，原始源文档未留档。编译层（overview/glossary/index/log）已于 2026-09-29 从 `.meta-cache` 初始化；业务方后续提供的口径说明、字段释义、风险分级依据等文档先落位本目录 `raw/`（原样保留），再按 `skills/aquilair-knowledge-wiki/references/ingest.md` 走再摄取更新。

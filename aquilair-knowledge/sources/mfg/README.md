# mfg 域源文档

生产制造调拨（统一 MCP 网关 `aquilair-mcp` 的 mfg 本体项目；2026-10-22 前为单体服务 `data-service-mfg-sandbox`）域的知识库：原始层 `raw/`（业务方文档原样落位）+ 编译层（[`glossary.md`](glossary.md) 术语表、[`index.md`](index.md) 索引、[`log.md`](log.md) 摄取日志）。

## purpose（本域为什么存在）

- **关键问题**：多工厂缺货时调什么、从哪调、调多少、总成本与运输天数几何、方案可信度如何评估。
- **研究范围**：mfg 本体项目的 10 个实体（工厂/物料/路由/策略/方案/计划/评估），生产与沙箱分支双环境。
- **演进论点**：口径以元数据与实测为唯一权威（预估与评估两套数并存不折算）；业务方口径文档补位后逐步替换实测出处。

**存量声明**：本域技能 `mfg-transfer-allocation` 开发于溯源区设立（2026-09-28）之前，原始源文档未留档，references 出处以「实测」标注为准（示例见 `references/kpi-caliber.md`）。业务方后续提供的 KPI 口径说明、调拨业务规则、策略说明等文档落位 `raw/`，再摄取时走 `skills/aquilair-knowledge-wiki/references/ingest.md` 流程更新编译层。

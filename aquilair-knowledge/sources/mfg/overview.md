# mfg 域总览（overview）

> 域级综合视图——「这个域现在整体是什么状态」。每次摄取/再摄取后更新（来源：glossary.md、`log.md`、技能 references，2026-09-28 首次编译）。

## 域定位与状态

生产制造多工厂物料调拨域，统一 MCP 网关 `aquilair-mcp` 的 mfg 本体项目（workspace `01a03bb7-2da4-7000-8dcf-1fb48f6f7fc9`，10 对象 12 关系；2026-10-22 由旧单体服务 `data-service-mfg-sandbox` 迁移而来，工具面换为 metadata_*/objects_*/actions_*；沙箱语义实现为数据分支 objects_create_branch。⚠️ action-service 当前未在项目部署动作（实测 404），调拨动作链待就绪）。技能 `mfg-transfer-allocation`（受控执行型，确认卡流程）已上线并随插件分发；域知识库 2026-09-28 完成首次编译（10 实体术语、4 条口径边界出处标注）。

## 当前全局理解（关键口径速览）

- **方案 KPI 只认评估实体**：`TransferOptSolutionEvaluation` 是总成本/总天数/缺货成本唯一事实来源，逐计划合计不得冒充（来源：技能 kpi-caliber.md，实测 2026-09-16）
- **可调出量不可推算**：没有可调出量字段时禁止由库存自行扣减推算（来源：glossary.md 流程术语节）
- **写操作全走确认卡 + 沙箱**：What-if 推演在沙箱，执行须五要素确认（来源：技能护栏铁律）
- **预估 vs 评估两套数并存**：不一致时并列说明，不折算（来源：glossary.md，实测 2026-09-16）

## 演进脉络

见 [`log.md`](log.md)（可机读前缀，`grep "^## \[" log.md` 取时间线）：2026-09-16 技能实测 → 2026-09-28 溯源区初始化与首次编译 → 2026-10-22 MCP 接口迁移统一网关。

## 已知缺口

原始源文档未留档（存量声明见 [README.md](README.md)）；业务方口径文档到位后走再摄取替换「实测」出处。

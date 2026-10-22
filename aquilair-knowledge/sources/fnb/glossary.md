# fnb 域术语表（glossary）

> 编译来源：`skills/fnb-inventory-analysis/.meta-cache/meta-objects.json`（fetch_meta 拉取，2026-09-16）+ 技能 references 实测标注。本表是 fnb 域术语的域内权威：lint 术语一致性检查、评估出题措辞以本表为准。

## 实体术语（15 个）

| 术语 | 实体英文名 | 口语说法 / 同义词 | 备注 |
| --- | --- | --- | --- |
| 产品品类 | `ProductCategory` | 品类、类别 | 3 属性 |
| 商品 SKU | `SKU` | SKU、商品、单品 | 22 属性，含 `abc_type`、`sku_name` |
| 仓库 | `Warehouse` | 仓库、仓 | 7 属性；主键 `wh_code`，展示名 `wh_name` |
| 采购订单 | `PurchaseOrder` | 采购单、PO | 15 属性 |
| 调拨单 | `ReplenishmentOrder` | 补货单、调拨 | 仅 2 属性（轻实体） |
| 销售订单 | `SalesOrder` | 销售单、SO | 12 属性 |
| SKU 在库状态 | `SKUInWarehouse` | SKU 库存、单 SKU 明细 | 23 属性；单仓 SKU 下钻主载体 |
| 品类在库状态 | `ProductCategoryInWarehouse` | 品类库存 | 16 属性 |
| 仓库库存总量 | `InventoryInWarehouse` | 仓级汇总、总量 | 12 属性；周转/库存指标载体 |
| 仓库库存业务问题 | `InventoryInWHProblem` | 业务问题、问题单 | 5 属性；L2 根因下钻用 |
| 仓库库存业务问题原因 | `InventoryInWHCause` | 原因、根因 | 7 属性；L2 根因下钻用 |
| 预测销售需求 | `ForecastSalesDemand` | 需求预测 | 8 属性 |
| 需求预测追踪记录 | `ForecastSalesTrace` | 预测追踪 | 10 属性 |
| 库存风险 | `InventoryRisk` | 风险记录、风险单 | 9 属性；**⚠ 元数据 display_name 与 ForecastSalesTrace 重复（同为「需求预测追踪记录」），疑似服务端缺陷，按实体语义应为「库存风险」，待业务方确认**（来源：实测 2026-09-29，meta-objects.json 比对） |
| 库存优化方案 | `InventoryOptimizationSolution` | 优化方案 | 6 属性 |

## 流程与机制术语

| 术语 | 含义 | 出处 |
| --- | --- | --- |
| 风险等级 P0-P3 | 系统既有判定的库存风险分级（P0 最重），输出按 P0→P1→P2→P3→无风险排序 | 技能 playbook 场景 A，实测 2026-09-16 |
| 溯源链 | L1 追问依据的三段式：规则原文（元数据）→ 指标数值（工具）→ 风险/Problem/Cause 记录（工具） | playbook L1，实测 2026-09-16 |
| 无风险仓不做区间判定 | 无风险仓只陈述指标原值，指标释义未提供判定区间时不得自行判定 | playbook L1，实测 2026-09-16 |
| ABC 分类 | SKU 周转价值分级（`abc_type` 字段），A 类 SKU 视角为常用收窄口径 | 技能 SKILL.md + meta-objects 字段释义 |
| 只读诊断 | fnb 只用只读工具（查询/取值/关系展开），无写操作、无沙箱、无动作——与 mfg 受控执行型的本质区别 | .mcp.json + get_meta_actions；2026-10-22 统一网关复测 |

# npi 域术语表（glossary）

> 编译来源：raw/本体模型实体对象v2.0.md（飞书 wiki NEswwEZaJivCqLkreCycHOnpnYe，2026-11-03 拉取）+ P1 实测记录（hub 仓 evals/runs/2026-11-03-launch-poc-probe.md）。本表是 npi 域术语的域内权威：lint 术语一致性检查、评估出题措辞以本表为准。
> 覆盖两代项目：新品上市POC-最新版（workspace 01a19ac6，主服务对象）与旧「新品上市保障」（01a15c77，退役过渡）；实体归属以「项目」列区分。

## 实体术语（新品上市POC-最新版，21 实体，2026-11-03 实测模型）

| 术语 | 实体 code | 口语说法 / 同义词 | 备注 |
| --- | --- | --- | --- |
| 上市计划 / 新品上市计划 | `DishLaunchPlan` | 上市方案、launch plan | 域中枢实体；计划就绪日=计划上市日（业务口径）【raw/NP009 故事线一】 |
| 上市事项 | `DishLaunchItem` | 齐套事项、准备工作 | 本项目「六类齐套」的承载实体（无 ReadinessUnit）；pre_item_codes 前置依赖 |
| 预测销售需求 | `ForecastSalesDemand` | 周需求、预测需求 | 首月拆 4 条周需求，交期=周初日期 |
| 物料需求 | `MaterialDemand` | 毛需求 | 【物料×仓库×需求】粒度；net_demand_qty 规则回写 |
| 供需分配 | `SupplyDemandAllocation` | 分配 | supply_type：INVENTORY 库存/PURCHASE_IN_TRANSIT 采购在途 |
| 物料齐套 | `MaterialKitting` | 齐套结果 | kit_qty/kit_time |
| 采购订单 | `PurchaseOrder` | PO、采购单 | 到货跟踪载体（逾期/预计延期字段规则在册） |
| 参考品绑定 | `ReferenceDishBinding` | 参考品、对标品 | 系数类属性 9 个（部分规则【待处理】） |
| 历史销量（按日） | （entity_ 未命名） | 历史销量 | **当前不可查**（缺正式 code，工单 TK-code） |
| 采购计划 / 采购方案 | （entity_ 未命名） | — | **当前不可查**；文档的 PurchasePlan/PurchaseSolution |
| 饮品档案 / 菜品 | `Dish` | 新品、饮品 | dish_status/publish_status/fulfillment_type |
| BOM / 配方 | `BOM` | 配方、物料清单 | bom_type 研发版/正式计划版；status 草稿/冻结 |
| 门店 | `Store` | 门店 | supply_wh_code 派生自 SupplyNetwork |
| 门店饮品 | `DishInStore` | 门店菜品 | 门店可售载体 |
| 仓库批次库存 | `BatchInventory` | 批次库存 | — |
| 物料在库状态 | `MaterialInWarehouse` | 在库 | 库存指标 5 属性系统缺失（工单 TK-miw字段） |
| 物料供应商 | `MaterialSupplier` | 供应商 | 主键 material_supplier_code（文档 strategy_code 系误，实测为准） |

## 流程与口径术语

| 术语 | 含义 | 出处 |
| --- | --- | --- |
| 六类齐套 | 商品/配方/仓配/物料/供应/门店与营销六类准备事项——本项目按 DishLaunchItem.item_type 归纳（旧 Q0001~Q0006 为演示编码） | raw/NP009 故事线 S03 |
| 口径三分离 | 首月经营目标（人工设定）/ 预测基准（系数推导）/ 分周预测需求（拆分）——不同源不得混用 | raw/新品上市POC业务背景与功能说明 3.2 |
| 预测基准链 | 参考品均店销量×季节系数×价格系数×门店系数×营销费用系数（价格/营销费用系数规则【待处理】） | raw/本体模型实体对象v2.0 二.新品分型 |
| 计划就绪日=计划上市日 | planned_ready_date 为空时按 plan_launch_date 说明（业务确认口径，非源数据已填写） | raw/NP009 故事线一 |
| 交货逾期 | 未取消未关闭、undelivery_qty>0 且逾期天数>0（RULE_D106C1119） | raw/本体模型实体对象v2.0 二.采购订单跟踪 |
| 预计延期 | expected_delay_days=MAX(0, 预计到达−要求交货)（RULE_901C611902） | 同上 |

## 旧项目（新品上市保障，退役过渡）对照术语

| 术语 | 旧实体 | 新项目对应 |
| --- | --- | --- |
| 齐套单元/子齐套 | `ReadinessUnit` / `SubReadinessUnit` | `DishLaunchItem`（上市事项）承载 |
| 上市风险台账 | `LaunchRisk`（entity_f44ddbf6） | 无实体——事项状态+缺口+订单异常清单表达 |
| 首发门店 | `NewDishLaunchStore` | 无实体——target_store_count 汇总 + DishInStore 明细 |

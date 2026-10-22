# mfg 域术语表（glossary）

> 编译来源：`.meta-cache/meta-objects.json`（fetch_meta 拉取，2026-09-16）+ 技能实测记录。本表是 mfg 域术语的域内权威：lint 术语一致性检查、评估出题措辞（口语说法/同义词）以本表为准。

## 实体术语（10 个）

| 术语 | 实体英文名 | 口语说法 / 同义词 | 备注 |
| --- | --- | --- | --- |
| 工厂 / 生产基地 | `Plant` | 工厂、基地 | 调拨路由的起点/终点；主键 `plant_code` |
| 物料 | `Material` | 物料、材料 | 主键物料编码；8 属性 |
| 工厂物料 | `MaterialInPlant` | 工厂库存、在厂物料 | 物料在各工厂的库存与可调出量载体，12 属性 |
| 工厂调拨路径 | `PlantTransferRouting` | 路由、线路 | 两厂间运输通道（unit_cost / lead_days） |
| 调拨优化目标 | `TransferOptimizationObjective` | 优化目标 | 目标定义（如成本最小化） |
| 调拨优化策略 | `TransferOptimizationStrategy` | 策略 | 启停状态、目标组合 |
| 调拨策略优化目标配置 | `TransferOptObjectiveInStrategy` | 策略目标配置 | 策略与目标的关联及优先级 |
| 调拨优化方案 | `TransferOptimizationSolution` | 方案 | 策略产出的方案；执行对象 |
| 调拨计划 | `TransferPlan` | 计划、调拨单 | 方案内逐条 从哪到哪调什么调多少；14 属性 |
| 调拨优化方案评估 | `TransferOptSolutionEvaluation` | 评估、方案评估 | **方案 KPI 唯一事实来源**（口径边界见技能 references/kpi-caliber.md） |

## 流程与机制术语

| 术语 | 含义 | 出处 |
| --- | --- | --- |
| What-if 沙箱 | 生产数据快照的独立推演分支，读写不影响生产（2026-10-22 起实现为统一网关数据分支：objects_create_branch / compare_branch / delete_branch） | get_meta_actions（sandbox_execution 约定）；2026-10-22 统一网关实测 |
| 确认卡 | 写操作前的五要素确认（环境/动作链/关键参数/影响/不可逆性），用户明确同意才执行 | 技能护栏铁律 |
| 可调出量 | 工厂物料可供调出的数量；**无可调出量字段时禁止由库存自行扣减推算** | 实测 2026-09-16，get_meta_objects |
| 预估成本 vs 评估成本 | 逐计划合计 ≠ 方案评估值，两者不一致时并列说明 | 实测 2026-09-16，kpi-caliber Gotchas |

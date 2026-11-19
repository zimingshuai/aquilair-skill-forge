# 工厂模板三件套（第 4 步模板步的文件资产）

> 状态：**试点**——单域实证（launch-dynamic-assurance v0.3.1，2026-11 双子代理行为评估通过），待第二域验证后转正式。
> 新范式来源：2026-11-16 用户裁决「规则驱动推理 + 三类知识三文件」——打法交模型沿元数据推理，技能文件只存机制与纪律。

## 三件套

| 件 | 位置 | 用途 |
| --- | --- | --- |
| 骨架模板 | `skeleton/SKILL.md` | 新技能 SKILL.md 的机制骨架（探查循环六步/铁律五类/写确认五步/输出规范/未知出口），占位符填空 |
| 交付资产基线 | `delivery-assets/`（`delivery.md` + `scripts/` 渲染四件） | 可视化与输出规范的出厂基线——**出厂时整目录 fork 进目标技能**（`references/delivery.md` + `scripts/render_*.py`），第一版各技能同源 |
| 三类知识判据卡 | `knowledge-criteria.md` | 建技能时逐条判断知识放哪：打法→模型推理（不落档）/ 接口坑→facts / 口径陷阱→calibers |

## fork 流程（第 4 步模板步）

1. 复制 `skeleton/SKILL.md` 为目标技能 SKILL.md，填占位符（域定位/MCP 连接器/workspace/枚举触发词），按判据卡规划 references 两件套（`facts.md` 接口坑 + `calibers.md` 口径）
2. **整目录复制 `delivery-assets/`**：`delivery.md` → `references/delivery.md`，`scripts/*` → `scripts/`——技能从此**自含交付资产**，与其余技能解耦
3. fork 时在 `references/delivery.md` 头注打基线戳（fork 自工厂模板 `<基线版本>`，`<日期>`）——之后本技能的交付规范自治演化，**不追模板后续变更**

## 治理规则

- **模板改动仅用户明确发起**：本目录（skeleton / delivery-assets / knowledge-criteria）任何修改须用户开口，不接受技能迭代顺手改模板
- **已 fork 技能不自动追**：模板演进只影响之后出厂的技能；存量技能要升级须单独发起
- **脚本缺陷修复 = 维护同步**（待用户最终裁决）：渲染脚本 bug 修复若不改行为语义，可全量同步各技能副本；规范口径类（配图策略/两档形态）一律按模板改动走
- 每次模板变更在 `delivery-assets/delivery.md` 头注与骨架 version 记录基线版本

## 适用前提

目标域须为**本体运行时型 MCP**（对象/关系/规则/动作四类元数据可查、规则经回写字段落值）——「规则定判定面」才有落点。裸数据接口型 MCP 不适用骨架的推理条款，判定面退回「文档口径 + 人工确认」并在 SKILL.md 声明。

# npi 域知识总览

- 业务文档源（出处：飞书 wiki MSYxwzdkAiDhDLkaHyNc3G78nFc，2026-10-23 lark-cli 拉取 revision 189）：新品上市业务背景与功能说明.md（飞书 wiki 2026-10-23 拉取，正文全文）——原件在开发母仓 xinpin/docs/，关键内容已编译进技能 references/domain-model.md（五大模块/37 实体/49 关系/37 规则/上市决策枚举）。
- 未摄取：2.1 流程图（isv 块）、2.2 功能模块 sheet（bot 缺 sheets scope，待授权补录）。
- 数据环境：workspace 新品上市保障 01a15c77-4e87-7000-880f-1d637582e3b1（v1.0.0 published + 修订中）。

## 新品上市POC-最新版（launch-dynamic-assurance 技能数据环境）

- 数据环境：workspace 新品上市POC-最新版 `01a19ac6-4c5f-7000-8c2d-4cfe7158ca8f`（v1.4.0 published 2026-11-03，21 实体/27 关系；main 分支（唯一分支）0 实例空态【2026-11-03 实测】）。MCP 经 `aquilair-mcp-servers` 寻址（2026-11-05 起全网关唯一名，旧名 `aquilair-mcp` 停用）。
- 素材归档（出处：飞书 wiki node token NEswwEZaJivCqLkreCycHOnpnYe 等，2026-11-03 拉取，总监工落盘后归档 raw/）：
  - 本体模型实体对象v2.0.md（原名 entity-v2-clean.md）——21 实体/27 关系本体模型实体对象 v2.0；
  - NP009_POC_Demo_Storyline_With_Queries.md（原名 np009-demo-storyline.md）——NP009 青提冰茶演示故事线（T=2026-11-15，首月 300000 杯/300 家，演示口径非查询结果）；
  - 动作与关联函数.md（原名 actions-and-functions.md）——15 动作与关联函数清单（apiName 全 null 为实测确认）；
  - 新品上市POC业务背景与功能说明.md（原名 poc-business-background.md）——POC 业务背景与功能说明；
  - launch-readiness-diagnosis_skills旧版playbook.md（原名 old-launch-playbook.md）——旧技能 launch-readiness-diagnosis 素材，备查（旧技能已标退役过渡）。
- 编译层：技能 launch-dynamic-assurance（aquilair-business-hub 0.4.0 收录）references/ 为权威编译产物——domain-model.md（业务链/判定链语义/决策枚举）、facts.md（DSL 方言/工具行为/服务端状态）、storyline-playbook.md（S01~S07 查询模板）。

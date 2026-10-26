# 技能资产巡检（lint）使用说明

> 本文件由 `aquilair-skill-authoring` 零件表「巡检」端引出：机检怎么跑、查什么；语义项为什么机检不了、人工清单怎么走。设计参照 Karpathy LLM Wiki 的 lint 工作流（调研背景见仓库 `aquilair-knowledge/research/2026-09-28-llm-wiki-karpathy.md`）。

## 一、何时跑

- **交付前**：新技能/改技能完成时（authoring 第 6 步验收已含 `python tools/lint_skills.py`，无 ERROR 才交付）
- **大改后**：共享措辞（加总边界、输出规范、确认卡条款）任一改动后的全量回归时
- **事件驱动**（优先于日历驱动）：某域 `log.md` 摄取/归档条目累计新增 N 条（`grep -c "^## \[" log.md` 可数）或 MCP 服务版本升级时，触发该域的语义巡检——不是「每月想起来跑」，是变更事件推着跑
- **定期兜底**：每月一次（服务端字段/口径变更会引发「过时」类问题）

## 二、机检（tools/lint_skills.py）

零依赖、仓库根直接跑，存在 ERROR 时退出码非零（可挂 pre-commit，与 evals/promptfoo 的本地门禁路线衔接）：

```
python tools/lint_skills.py
```

| 检查项 | 内容 | 级别 |
| --- | --- | --- |
| C1 | frontmatter name 与目录名一致 | ERROR |
| C2 | description 含「Use when」触发句式与边界句（not for / 不属于） | WARN |
| C3 | SKILL.md 行数 50~120 | 超限 ERROR / 过短 WARN |
| C4 | SKILL.md 引用的 references/*.md 存在 | ERROR |
| C5 | references/ 无孤儿文件（未被 SKILL.md 提及） | WARN |
| C6 | 技能已进 README 技能清单 | ERROR |
| C7 | 业务技能已进 router 路由表 | ERROR |
| C8 | 业务技能有 evals/ 用例目录 | ERROR |
| C9 | MCP 服务双向一致（无未登记服务、无死服务） | 未登记 ERROR / 死服务 WARN |
| C10 | 业务技能 references 含出处标注 | WARN（渐进达标） |
| C11 | 域知识库健康（每域 glossary/index/log 三件齐 + 编译层含出处标注——无来源页面即发现） | WARN（渐进达标） |
| C12 | 枚举型宿主清单一致性（CodeBuddy skills 数组 vs `plugins/business-hub/skills/` 目录双向；其余宿主目录扫描无需维护） | ERROR |

元技能豁免 C7/C8/C10（不进路由表、不进评估、无业务口径）。

## 三、人工巡检清单（语义项，机检不可替代）

LLM 读全部技能资产后逐项判定，**只出报告与修复建议，改动须人确认后执行**（对齐 llm-wiki「建议不自动改」纪律）：

| # | 检查项 | Aquilair 映射 | 怎么查 |
| --- | --- | --- | --- |
| 1 | 页面间矛盾 | 跨技能共享条款不一致（加总边界、输出规范措辞漂移） | 并排比对各 SKILL.md 同主题条款；`grep` 同款措辞的变体 |
| 2 | 过时论断 | MCP 服务变更后 references 的参数说明、KPI 口径、`.meta-cache` 过期 | 对照最新 `get_meta_*` 元数据复核已标注出处的口径条目 |
| 3 | 孤儿内容 | references 文件内的死段落（整节内容已无入口场景） | 通读判断；文件级孤儿机检 C5 已覆盖 |
| 4 | 被提及但无实体 | SKILL.md 承诺的章节/流程对方技能没有 | 按引用逐一跳转验证；文件级机检 C4 已覆盖 |
| 5 | 缺失交叉引用 | 接线五处齐不齐 + 源文档是否落位 `aquilair-knowledge/sources/` | 四处机检覆盖；第五处（源文档落位）人工抽查 |
| 6 | 术语不一致 | 同一概念跨技能叫法不同（确认卡五要素、风险等级、口径名） | 以 `aquilair-knowledge/sources/` 源文档与业务方最新说法为权威，统一改法后全量回归 |

第 2 项依赖出处标注溯源链（`aquilair-knowledge/sources/README.md` 三纪律）：新源文档进来时，凡标注引用旧源的条目都要复核——没有标注就没有「过时」判定依据。

**audit 模式（推荐每季度一次）**：语义巡检用**无先验的干净会话**执行——不带构建过程记忆，只给它知识库与技能资产，对照 raw 源逐项找矛盾。构建者有作者盲区，LLM 审 LLM 的干净视角能发现「我们都习惯了」的漂移。

## 四、问题处置

- **ERROR**：修复后重跑至零，才可交付/合入
- **WARN**：不阻断，按需整改；同类 WARN 连续两轮巡检未处理则升级为交付阻断项
- 修复一律走正常 git 提交，不提供 lint 自动改写（`--fix` 类能力不做——自动改写共享条款曾造成回归事故，纪律见主技能反合理化表格）

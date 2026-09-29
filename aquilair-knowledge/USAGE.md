# 知识库使用速查（USAGE）

> Aquilair 知识库（`aquilair-knowledge/`）的上手指南：谁在什么场景说什么话，会发生什么。总纲一句话——**你只管丢东西和提问，编译、溯源、更新都是技能的活**。技能本体见 `skills/aquilair-knowledge-wiki/`。

## 场景速查

| 你想做什么 | 你说 / 你做 | 会发生什么 |
|---|---|---|
| **查口径出处** | 「总调拨成本的口径哪来的？」「工厂物料有哪些口语说法？」 | 触发 `aquilair-knowledge-wiki` → 先读域 `index.md` → 钻取知识页 → 带坐标引用回答（如 `skills/mfg-…/kpi-caliber.md §公式与口径边界`）；知识库没有的直说没有，不编造。**注意分层**：问「有哪些实体」这类实时元数据 → 直接跑 MCP `get_meta_*`，不走知识库 |
| **喂一份新文档** | 把文档给到（路径/拖进对话），说「这是新的调拨口径说明，ingest 进 mfg 域」 | 原样落 `raw/` → 生成源摘要 → **当场查矛盾**（与既有页冲突标记候审）→ 更新 glossary/index/log → 涉技能口径的出候审清单等人裁定 |
| **新业务域进厂** | 「新域进厂：文档包在 xxx，MCP 地址是 https://…」 | knowledge-wiki 五步摄取（分类入库→元数据遍历→实测探针→编译知识页）→ `aquilair-skill-authoring` 六步流水线产出新技能 → lint 验收 |
| **服务升级后复核** | 「mcp1 刚升了版，对 mfg 域做再摄取」 | 新旧对照（依据出处标注 + log）→ 出**过时候审清单** → 人工裁定 → 涉技能口径走增量改 + 全量回归 |
| **日常体检** | 命令行 `python tools/lint_skills.py` | 十二项机检（技能接线/引用/行数/知识库健康/CodeBuddy 清单一致性），ERROR 时退出码非零，可挂 pre-commit 门禁 |
| **季度深检（audit）** | 开一个**全新干净会话**：「对 mfg 域做语义巡检」 | 无先验视角对照 raw 源逐项找矛盾——破「我们都习惯了」的作者盲区（见 authoring references/lint.md） |

## 两个日常最常用的入口

- **开发 / 答疑时**：任何「这个说法哪来的」的问题直接问——回报率最高的用法，答案全部可核查、可跳转。
- **团队同事接手时**：不用讲背景，让他读 `sources/<域>/index.md`——purpose（为什么存在）→ overview（什么状态）→ glossary（术语）→ log（变更时间线），五分钟建立全局认知；每个知识页都有出处坐标。

## 两个提醒

- 摄取是**事件驱动**的：文档进来、服务升级才需要动知识库，平时零维护。域时间线随时可查：`grep "^## \[" sources/<域>/log.md | tail -5`。
- 知识库源文档区随技能 zip 分发（`tools/pack_skill.py` 自动收录 `sources/`，zip 内坐标同名可解析）——装了插件的宿主环境里，技能引用的溯源链完整。

## 目录导航

```
aquilair-knowledge/
  USAGE.md            # 本文件
  research/           # 调研报告（决策知识，开发侧）
  sources/
    README.md         # 溯源区纪律与出处标注格式
    <域名>/            # fnb / mfg / wiki（自举域）：README+purpose、raw/、overview、glossary、index、log、analyses/
```

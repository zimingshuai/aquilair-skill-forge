# llm-wiki-karpathy 是否收编进 aquilair-business-skills 插件调研报告

> 调研日期：2026-09-28 ｜ 场景：选型（收编与否决策）

## 一、结论（TL;DR）

**不建议把 llm-wiki-karpathy 收编进 aquilair-business-skills 插件。** 三条核心理由：

1. **定位不匹配**：我们插件是「F&B 供应链业务技能 + 技能工厂元技能」的垂直技能包（6 个技能全部服务供应链业务问答/方案与技能生产线）；llm-wiki 是面向技术写作者/研究员/产品经理的**通用个人知识管理**工具，与供应链业务零关联，收编会稀释插件定位。
2. **形态不匹配**：它不是标准 skill——没有 `SKILL.md` 与 frontmatter 触发机制，本体是一个「CLAUDE.md 充当 schema + `raw/` 源文档目录 + `wiki/` 生成目录 + `.obsidian/` 预配置」的**项目模板/脚手架**，深度绑定 Cursor + Obsidian 双工具工作流；收编需要完整改造，且跨三宿主（ZCode/Claude Code/Codex）兼容性要重新评估。
3. **它解决的是「每个用户自己的」知识库问题**：核心价值在用户往 `raw/` 里喂自己的文档，技能本体只是空壳模板——作为插件分发的资产形态不对，用户直接用原仓库（或社区已有的 Claude Code skill 衍生版）比经我们转手更合适。

若团队真想要这个能力，替代路径见「八、建议下一步」。

## 二、背景与调研问题

用户发起 `llm_wikia` 讨论，询问是否需要把 [balukosuri/llm-wiki-karpathy](https://github.com/balukosuri/llm-wiki-karpathy) 收编进我们的插件。拆出的子问题：

1. 这个仓库是什么、解决什么问题、成熟度如何？
2. 它与我们插件现有 6 个技能的定位/形态是否兼容？
3. 收编的收益与成本（含维护、评估回归、跨宿主）各是什么？
4. 如果不收编，有什么替代路径获得同等价值？

## 三、问题与解法（被调研对象）

**它出现前的痛点**：RAG 每次提问都要重新搜索原始文档，知识不积累、不互联；个人散落的规格文档/会议记录/竞品资料无法体系化。

**它的解法**：Karpathy 提出的「compile 而非 retrieve」——LLM 只读一次源文档，构建持久的、相互链接的 wiki，喂得越多连接越密。三个核心工作流：

- **ingest**：读入 `raw/` 下的文档 → 生成来源摘要页、新建实体页 → 更新术语表/索引/总览 → 记日志（一次触及 5~15 个页面）
- **提问**：AI 读 wiki 综合回答并带引用，可把好答案保存为永久分析页
- **lint**：定期健康检查——矛盾、过时内容、孤儿页、缺失交叉引用、术语不一致

**分层所有权**：`raw/` 用户拥有（AI 只读）、`wiki/` AI 完全拥有、`CLAUDE.md` 共同维护——这是它最值得借鉴的设计。

## 四、核心发现

- 仓库 214 star / 85 fork，但仅 **4 次提交**，属早期项目；模式源自 Andrej Karpathy 的 LLM Wiki 构想，作者 Balu Kosuri [来源：GitHub 仓库页](https://github.com/balukosuri/llm-wiki-karpathy)（2026-09-28 抓取）
- **不是 Claude Code skill、也不是 MCP 服务器**：无 `skills/` 目录、无 MCP 配置；主要面向 Cursor（自动读 CLAUDE.md 作操作手册），搭配 Obsidian 浏览 wiki [来源：同上]
- 社区已存在改造为 Claude Code skill 的衍生文章："LLM Wiki Skill: Build a Second Brain With Claude Code and Obsidian"，以及作者的 Medium 文章 "How I turned Andrej Karpathy's LLM Wiki into a tool that writes wikis from code" [来源：WebSearch 结果摘要]（未逐一打开核实原文）
- 我们插件现状：`skills/` 下 6 个技能（fnb-inventory-analysis、mfg-transfer-allocation、aquilair-data-delivery、aquilair-skill-router、aquilair-skill-authoring、aquilair-eval-diagnostics）+ `tools/skill-eval-generator`，全部为标准 SKILL.md 形态 [来源：本地仓库扫描]
- 我们的既有实践中已有「一次读取、持久化复用」思想的落地：`fetch_meta.py + .meta-cache`（元数据缓存），与 llm-wiki 的 compile 理念同源 [来源：项目记忆]

## 五、对比分析

| 维度 | aquilair-business-skills | llm-wiki-karpathy | 兼容性判断 |
|------|--------------------------|--------------------|------------|
| 定位 | 供应链垂直业务技能 + 技能工厂元技能 | 通用个人知识管理（second brain） | ❌ 无业务交集 |
| 形态 | 标准 SKILL.md + frontmatter 触发 | CLAUDE.md schema + 目录模板（Cursor/Obsidian 工作流） | ❌ 需完整改造 |
| 宿主 | ZCode / Claude Code / Codex 三宿主分发 | Cursor + Obsidian 深度绑定 | ⚠️ 跨宿主要重评 |
| 数据 | MCP 数据服务（生产/沙箱） | 用户自喂的任意文档 | ❌ 资产属用户，不属插件 |
| 成熟度 | 37 条技能全 mature、有评估回归体系 | 4 次提交的早期仓库 | ❌ 收编即背上评估与维护成本 |
| 受益人 | 插件的供应链业务终端用户 | 需要整理多源信息的个人（写作者/研究员/PM/学生） | ❌ 受众不同 |

**加权判断**：定位（权重最高）与形态两条硬维度全部不兼容，仅「compile 思想可借鉴」一条软收益，不足以支撑收编。

## 六、风险与信息缺口

- **未核实**：Medium 衍生 skill 文章的原文内容与质量（仅搜索摘要，未打开）；若未来真要 Claude Code skill 形态，需先核实该衍生版是否可直接用。
- **时效**：原仓库仅 4 次提交，后续可能快速演化，本报告结论基于 2026-09-28 快照。
- 若强行收编，风险是：插件定位稀释、为非业务技能背评估回归成本（收编后须过我们 evals 体系与 pack_skill 验证）、跨宿主兼容性未知。

## 七、来源清单

1. [balukosuri/llm-wiki-karpathy](https://github.com/balukosuri/llm-wiki-karpathy) — GitHub 仓库页（WebFetch 抓取，2026-09-28），含 README、结构、star/提交数。可信度高（一手来源）。
2. WebSearch "llm-wiki-karpathy balukosuri github skill" — 检索结果摘要（2026-09-28），指向 Medium 作者文章与 Claude Code skill 衍生篇。可信度中（未核实原文）。
3. 本地仓库 `skills/`、`tools/` 目录扫描（2026-09-28）。可信度高。

## 八、建议下一步

1. **不收编，原样结论回复讨论**：插件保持供应链垂直定位。
2. 若个人/团队确实想要 second brain：直接用原仓库（git clone 自用），或核实社区 Claude Code skill 衍生版，**不占用 aquilair-business-skills 的版本线与分发渠道**。
3. 若看中的是「compile 而非 retrieve」思想用于技能工厂：把它作为**设计参考**吸收进 `aquilair-skill-authoring`（例如新业务域接入时的「元数据编译一次、沉淀复用」已有 .meta-cache 实践，可加 lint 式健康检查思路），而非收编整个技能——此项若立项，按流程先加载 authoring 元技能再动。

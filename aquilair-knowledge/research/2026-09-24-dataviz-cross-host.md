# 数据可视化技能跨宿主泛化调研

> 调研日期：2026-09-24 ｜ 场景：技术方案调研（服务 `aquilair-data-delivery` 技能改造决策）
> 触发背景：用户反馈在 Codex 与 ZCode 里数据可视化都很耗时（会话 sess_de41b827 实测：matplotlib 环境崩坏 → PIL 手绘 90 行 → visual-judge 验收，一轮 3~5 分钟），希望泛化让各宿主用自身最适合的可视化方式。
> **修订（2026-09-24 当日）**：用户澄清实际宿主形态为**桌面 app**而非终端 CLI——初版把 ZCode/Claude Code/Codex 按 CLI 定性，本版已按桌面端形态修正能力矩阵与结论定性，方案主体不变、优先序微调。

## 一、结论（TL;DR）

1. **慢的根因不是「配图铁律」，而是技术路径绑错了通道**：SKILL.md 第五节把非豆包宿主的实现等价映射到「写 Python 脚本渲染 PNG」——这是 agent 最慢、最易碎的绘图方式（依赖 Python 绘图环境健康 + 手工处理字体布局 + 需视觉验收）。
2. **业界已收敛到「agent 写单文件自包含 HTML」为主路径**：Anthropic 官方 `web-artifacts-builder` 技能（React/Vite 构建后 bundle 成单 HTML 交付）；社区实测（80 个 agent 生成站点中 99% 为单文件 HTML、86% < 100KB）；Claude 桌面端 live artifacts 更是把「完整 HTML 写盘即运行」做成了宿主原生能力。写 HTML/前端是 LLM 的母语能力，一次 Write 调用完成，零 Python 环境依赖。
3. **桌面 app 形态下各宿主都有「app 内呈现」通道，能力卡按桌面端绘制**：豆包/WorkBuddy 原生 `show_widget`/`present_files`；Claude 桌面/Cowork 有 live artifacts（HTML/React/SVG/Mermaid，写盘即运行）；Codex 已并入 ChatGPT 统一桌面 app（2026-07，支持 markdown 渲染与图像查看）；ZCode 桌面端有 browser-use 开标签页（图片内联渲染待实测）。终端 CLI 的「不渲染图/不渲染 Mermaid」证据仅适用于 CLI 形态，不适用于本团队实际场景。
4. **ZCode 桌面端图片内联已实测成功**（2026-09-24），由此派生「SVG 文件 + 图片内联」作为**单图对话内直呈**的最快通道（文本格式、一次 Write、零 Python 依赖、免打开浏览器）。建议的通道优先序按三场景分流：单图（原生组件 > SVG 内联 > HTML 单图）；多图/交互（原生预览 > 单文件 HTML 看板）；留档/文档（PNG > Mermaid）。
5. **改动无评估基线风险**：`evals/aquilair-data-delivery/cases.yaml` 的断言本就形态无关（`contains-any: [".png", ".html", "mermaid", "看板", ...]`），重写技术路径章节不触碰任何 mature 用例的判定标准。

## 二、背景与调研问题

`aquilair-data-delivery` 源自豆包侧规范（`aily-data-visualizer`：matplotlib+plotly 生成 PNG → `aily-cli image upload` → 评论内联），2026-09-21 收编为宿主无关版本。收编时保留了「其他宿主 = 生成图片/HTML 文件」的等价映射，实践中暴露：

- **速度**：PNG 路径要写绘图脚本、跑 Python 渲染、踩环境坑（NumPy 2.x 二进制不兼容）、派 visual-judge 子代理验收——单轮可视化耗时 3~5 分钟，占整轮交付的大头。
- **实现与形态错配**：初版按「CLI 宿主」推断交付可见性；用户澄清实际为桌面 app 形态后，可见性问题弱化，但 PNG **生成慢**的问题不变，HTML 路径优势反而扩大（桌面端可 app 内预览）。

**调研子问题**：

1. 各宿主（豆包/WorkBuddy、ZCode、Claude 系、Codex/ChatGPT、文档宿主）在**桌面 app 形态下**的真实可视化渲染能力？
2. 业界 agent 数据可视化的主流做法？官方（Anthropic）怎么选？
3. Mermaid / HTML / PNG 各通道的耗时、依赖、效果对比？
4. 泛化机制怎么设计——规范层定什么、宿主层怎么自适应？

## 三、问题与解法

### 现行技能的路径问题（本地证据）

现行第五节定义（`skills/aquilair-data-delivery/SKILL.md:56-71`）：

> | 单图内联 | WorkBuddy/豆包: `show_widget` | CLI 宿主: plotly/PIL/SVG 生成图片或内联图形，以本地路径或 URL 交付 |

把「配图」这一**意图**等价映射成了「产出图片文件」这一**实现**。三个后果：

1. **写脚本成本**：PNG 需要 agent 手写绘图代码——布局、字体、坐标全要算（PIL 手绘版 90 行），这是 LLM 不擅长的高精度数值工作。
2. **环境脆弱**：matplotlib 依赖 NumPy 二进制兼容；2026-09-24 实测本机即坏（会话 sess_de41b827）。技能虽有「不修环境换等价通道」条款，但换到的 PIL 直绘更慢。
3. **验收放大**：PNG 无模板保证，须派 visual-judge 视觉验收（+32 秒子代理开销）。

### 解法方向：换到 LLM 母语通道 + 按宿主能力选路

LLM 写结构化文档（HTML/CSS/Markdown）的可靠性远高于操纵像素坐标。可视化通道应该顺着这个能力选：**豆包用原生组件，桌面端写 HTML（app 内预览或浏览器打开），文档交付用 Mermaid，PNG 降级为留档格式**。

## 四、核心发现

### 发现 1：各宿主渲染能力矩阵（桌面 app 形态版）

| 宿主（实际形态） | 图片内联 | Mermaid | app 内 HTML 预览 | 原生可视化组件 | 浏览器通道 |
| --- | --- | --- | --- | --- | --- |
| WorkBuddy / 豆包（app） | ✅ | — | ✅ `present_files` | ✅ `show_widget`（内联 SVG/Chart.js）、`aily-data-visualizer`、`aily-cli` 图床 | 内置 |
| ZCode（桌面 app） | ✅ **已实测**（2026-09-24，`![](本地路径)` 内联渲染成功） | 待实测 | browser-use 技能新建标签页 | visual-judge 验收通道 | ✅ |
| Claude 桌面 / Cowork | ✅（artifacts 生态） | ✅ artifacts 支持 | ✅ **live artifacts**：完整 HTML 写盘即运行（桌面限定） | artifacts（HTML/React/SVG/Mermaid） | ✅ |
| ChatGPT app（Codex 并入，2026-07） | ✅（桌面 app 图像查看/编辑） | 未确认（app 内 markdown 渲染已有，Plan Mode 有已知 bug） | canvas 类预览（能力边界待确认） | canvas | ✅ |
| Codex CLI（终端形态，非本团队主用） | ❌ | ❌（open feature request） | ❌ | 仅响应式表格 | 可 `start`/`open` |
| 文档宿主（GitHub/GitLab） | — | ✅ pie 成熟；xychart-beta（v10.3+/v11）GitHub 已支持 | — | — | — |

来源：[ChatGPT app 整合 Codex](https://thenewstack.io)（2026-07）、[ChatGPT/Codex changelog：render Markdown in agent + 图像查看](https://learn.chatgpt.com)（2026）、[Codex Web Plan Mode 渲染 bug](https://community.openai.com)（2025-10）、[Claude Cowork live artifacts 官方文档](https://support.claude.com)（2026-09）、[artifacts 实现机制：HTML 写盘即运行](https://bloom.security)（2026-07）、[Cowork artifacts 桌面限定 issue](https://github.com)（2026-08）、[Codex CLI Mermaid feature request](https://github.com)（2026-07）、[GitHub Mermaid 文档](https://docs.github.com)、[Mermaid xychart](https://mermaid.ai)。

**含义**：桌面 app 形态下，HTML 看板在全部宿主都有「生成快 + 呈现快」的通道（原生预览组件、artifacts、canvas、browser-use、点链接）；PNG 的可见性问题弱化，但**生成耗时**劣势不变。终端 CLI 一列保留仅作形态参考，不作为能力卡依据。

### 发现 2：业界主流 = 单文件自包含 HTML（官方 + 社区双重印证）

- **官方**：Anthropic `anthropics/skills` 仓库的 `web-artifacts-builder` 技能——指导 Claude 用 React/Vite/Tailwind 构建可视化 artifact，最终 `bundle-artifact.sh` 打成**单 HTML 文件**交付给用户（[仓库](https://github.com/anthropics/skills)，[skill 详解](https://www.claudeskills.org)）。
- **宿主原生化**：Claude 桌面/Cowork 的 live artifacts 已把该模式做进产品——「真实的 app 而非预览」，完整 HTML 文档（自带 CSS/JS）写盘运行（[bloom.security](https://bloom.security)，2026-07；[shareduo 指南](https://www.shareduo.com)，2026-04：支持 HTML/React/SVG/Mermaid）。
- **社区实测**：对 80 个 agent 生成站点的分析——**99% 是单个自包含 HTML 文件，86% < 100KB**（均值 ~174KB），无需服务器或部署（[stacktr.ee 分析](https://stacktr.ee)）。
- **技能生态**：ECharts 看板技能（[terminalskills.io](https://terminalskills.io)）、单文件 HTML 交互看板技能（[awesomeskill.ai](https://awesomeskill.ai)）、GitHub Pages 发布模式（[mcgarrah.org](https://mcgarrah.org)，2026-07）。

**含义**：官方、宿主产品、社区三层都已收敛到这条路径；我们只需把非豆包宿主的通道从「plotly/PIL 生成图片」改指到此路。

### 发现 3：Mermaid 的定位——文档交付通道 + Claude artifacts 内可用

- GitHub / GitLab / GitLab 论坛原生渲染 Mermaid，pie 稳定、xychart-beta（条形/折线）GitHub 支持（[GitHub docs](https://docs.github.com)、[GitLab](https://gitlab.com)、[论坛插件](https://forum.gitlab.com)，2026-03）。
- Claude 桌面 artifacts 明确支持 Mermaid 类 artifact（[shareduo](https://www.shareduo.com)）。
- 但各宿主**对话消息流的 markdown 渲染**普遍不保证 Mermaid（Codex Web 仍在修 markdown 基础渲染 bug；ZCode 待实测）。

**含义**：Mermaid 适合「交付物落 GitLab PR / 禅道 wiki / md 报告」与「Claude artifacts」两类场景；对话消息流内不作默认。

### 发现 4：matplotlib 类技能依然主流但有环境前提

社区存在大量 matplotlib 技能（[mcpmarket](https://mcpmarket.com)、[getclaudeskills.com](https://getclaudeskills.com)、[claude-code-templates](https://github.com)），面向「出版级静态图」场景，全部假设 Python 绘图环境健康——本机实测证明该假设在公司 Windows 开发机上不成立（NumPy 2.x 冲突）。

**含义**：PNG 不作为对话内可视化的默认通道，降级为「用户点名要图片文件 / 正式留档 / 嵌入 docx-pptx」场景。

### 发现 5：ZCode 桌面端的两个加速器 + 图片内联实测结论（本地证实）

- **图片内联 ✅（2026-09-24 实测）**：ZCode 桌面端对话面板直接渲染 `![](本地png路径)`，无需点链接——「单图对话内直呈」可行。
- `browser-use:control-browser`：按用户浏览器规则**新建标签页**打开本地 HTML 看板——多图/交互场景生成即呈现。
- `documents:visual-judge`：仅 PNG 需要视觉验收；HTML/SVG 由模板保证结构，可免验收。

**由此派生的新候选通道——SVG 文件内联（单图场景最优候选）**：SVG 是文本格式，agent 一次 Write 即成（LLM 母语能力，声明式绘图无需 Python 环境、无需字体文件、无需打开浏览器），经图片内联通道直接显示在对话流里。会话 sess_de41b827 的 PIL 手绘 90 行本质上就是在做 SVG 的工作——同工作量下 SVG 免 Python、免渲染、免验收轮次。与 PNG 内联的关系：**生成快慢的差别**（PNG 要跑 Python 绘图链，SVG 是纯文本）；与 HTML 看板的关系：**单图 vs 多图/交互**的分工。内联渲染效果实测进行中（2026-09-24 同轮验证）。

### 发现 6：内网 CDN 风险 → 默认模板应零依赖

公司内网对公网 CDN（jsdelivr/unpkg 等）可达性未知。若默认模板引 ECharts CDN，内网可能开天窗。**纯 HTML+CSS 条形图**（div 宽度按数值比例 + 语义配色）零外部依赖、任何浏览器/内嵌 webview 可开，且恰好覆盖本技能首选形态「横向条形图」；折线/饼图可用内联 SVG。

## 五、对比分析（通道对比表 · 桌面端形态）

| 通道 | 生成耗时 | 环境依赖 | 交互性 | 桌面端呈现 | 最适用 |
| --- | --- | --- | --- | --- | --- |
| 宿主原生组件（`show_widget`/artifacts/canvas） | ⭐ 最低 | 无（宿主内置） | ✅ | ✅ app 内直呈 | 豆包/WorkBuddy；Claude artifacts；ChatGPT canvas |
| 单文件 HTML 看板（CSS/SVG 零依赖） | ⭐ 低（一次 Write） | 无（浏览器/webview 即可） | ✅ 筛选/悬浮 | ⚡ 点链接/app 内预览/开标签页 | 全部桌面端宿主 |
| 单文件 HTML（ECharts CDN） | 低 | 需 CDN 可达 | ✅✅ 最强 | ⚡ 同上 | 外网/CDN 可达环境 |
| Mermaid 代码块 | ⭐ 最低（纯文本） | 渲染器（GitHub/GitLab/artifacts 有） | ❌ | 视宿主（对话流内不保证） | 交付物落 md 文档/PR；Claude artifacts |
| PNG（matplotlib/plotly） | 高（脚本+渲染+验收） | Python 绘图链（易碎） | ❌ | ✅ 桌面端可内联/查看（ChatGPT app 图像查看已证实） | 留档、嵌入 docx/pptx |
| PNG（PIL 手绘） | 最高（布局全手算） | 低 | ❌ | ✅ 同上 | 仅 matplotlib 崩坏时的兜底 |
| Unicode 条形图（█▌） | ⭐ 最低 | 无 | ❌ | ✅ 纯文本必然可见 | 兜底（桌面端价值下降，可保留不推广） |

**耗时对比直觉**（以会话 sess_de41b827 为参照）：PNG 路径 ≈ 写脚本 60-90 秒 + 渲染/排错 30-120 秒 + 验收 30 秒；HTML 路径 ≈ 一次 Write 20-40 秒 + 打开 2 秒。**提速约一个数量级**。

## 六、风险与信息缺口

1. ~~**ZCode 桌面端是否内联渲染 `![](本地png)` 图片**~~：**已实测 ✅（2026-09-24，渲染成功）**；SVG 内联渲染同轮验证中。
2. **ChatGPT app（Codex）内**：本地文件引用是否可点开、canvas 对 agent 生成 HTML 的开放程度——未验证（后续在 WorkBuddy 侧同事环境实测）。
3. **WorkBuddy `show_widget` 现状**：来自收编时记录，本轮未实测。
4. **内网 ECharts CDN 可达性**：未验证。已用「默认零依赖 CSS/SVG 模板」规避，CDN 版作为外网可选。
5. **Mermaid 在 ZCode 对话流内**：待实测（若 ZCode 面板基于 webview 且引入 mermaid.js 则可能支持；不作为方案依赖项）。
6. **Unicode 条形图的「图」资格**：属规范决策——桌面端富渲染已证实，Unicode 条形价值进一步下降，建议不纳入正式通道。

## 七、来源清单

| # | 来源 | 类型 | 日期 | 要点 |
| --- | --- | --- | --- | --- |
| 1 | [anthropics/skills 官方仓库](https://github.com/anthropics/skills) | 官方 | 2026 | `web-artifacts-builder`：单 HTML 文件交付 artifact 的官方模式 |
| 2 | [web-artifacts-builder 详解](https://www.claudeskills.org) | 三方 | 2025-12 | React/Vite 构建 → bundle 成单 HTML |
| 3 | [80 站分析：agent 实际发布什么](https://stacktr.ee) | 实测数据 | 2026 | 99% 单文件 HTML、86% < 100KB |
| 4 | [Claude Cowork live artifacts 官方文档](https://support.claude.com) | 官方 | 2026-09 | artifacts 机制与共享权限 |
| 5 | [artifacts 实现机制](https://bloom.security) / [shareduo 指南](https://www.shareduo.com) / [pluto.security](https://pluto.security) | 三方深析 | 2026-04~08 | 完整 HTML 写盘即运行；支持 HTML/React/SVG/Mermaid；Cowork 桌面限定 |
| 6 | [Cowork artifacts 桌面限定 issue](https://github.com) | GitHub issue | 2026-08 | live artifacts 为桌面端专属能力 |
| 7 | [OpenAI 将 Codex 并入 ChatGPT app](https://thenewstack.io) | 媒体 | 2026-07 | 统一桌面 app，Codex/Atlas 合并 |
| 8 | [ChatGPT/Codex changelog](https://learn.chatgpt.com) | 更新日志 | 2026 | 桌面 app：render Markdown in agent、图像查看/编辑增强 |
| 9 | [Codex Web Plan Mode 渲染 bug](https://community.openai.com) | 社区 | 2025-10 | Web 端 markdown 渲染仍有缺陷 |
| 10 | [Codex CLI Mermaid 渲染 feature request](https://github.com) | GitHub issue | 2026-07 | 仅 CLI 形态不渲染（本团队非主用形态） |
| 11 | [GitHub: Creating Mermaid diagrams](https://docs.github.com) / [Mermaid XY Chart](https://mermaid.ai) / [GitLab](https://gitlab.com) / [GitLab 论坛](https://forum.gitlab.com) | 官方 | 2024~2026 | Mermaid pie/xychart 渲染矩阵 |
| 12 | [ECharts agent skill](https://terminalskills.io) / [html-dashboard skill](https://awesomeskill.ai) / [GitHub Pages 模式](https://mcgarrah.org) | 社区技能 | 2026 | 单文件看板技能生态已成型 |
| 13 | [社区 matplotlib 技能](https://mcpmarket.com)（[另见](https://getclaudeskills.com)） | 社区 | 2026 | matplotlib 技能生态依赖健康 Python 环境 |
| 14 | 本地：`skills/aquilair-data-delivery/SKILL.md`（第五节）、`evals/aquilair-data-delivery/cases.yaml`、会话 sess_de41b827 回放 | 本地 | 2026-09-24 | 痛点实证 + 断言形态无关 |
| 15 | 本地实测：ZCode 桌面端 `![](本地png)` 内联渲染成功（用户确认）；SVG 内联渲染同轮验证（`svg_inline_test.svg`） | 本地 | 2026-09-24 | 能力卡 ZCode 行回填依据 |

## 八、建议下一步（技能改造方案草案，待拍板）

**核心思路：规范只管「必须可视化 + 选什么图 + 验收标准」，实现通道按宿主能力卡自选，全局给一条通道优先序。**

1. **重写 SKILL.md 第五节**：由「豆包/CLI 两列等价映射表」改为：
   - 全局通道优先序（桌面端版，按「单图 / 多图交互 / 留档」三场景分流）：
     - **单图对话内直呈**：宿主原生内联组件（`show_widget`）> **SVG 文件 + 图片内联**（ZCode 已证实图片内联；SVG 一次 Write 即成）> HTML 单图页；
     - **多图 / 交互看板**：宿主原生预览（artifacts / canvas / `present_files`）> **单文件 HTML 看板**（零依赖 CSS/SVG 默认，ECharts CDN 可达时增强）；
     - **留档 / 嵌入文档**：PNG（docx/pptx 嵌入、正式归档）> Mermaid（md 文档/PR 内嵌，GitHub/GitLab 渲染）。
   - 「新宿主补能力卡」机制：一行记录（图片内联？Mermaid？app 内 HTML 预览？原生组件？浏览器通道？），代替现在的「补一列」；能力卡按**实际使用形态**（桌面 app）绘制，不按产品名义形态。
2. **新增 `references/viz-templates.md`（或并入 dashboard-playbook）**：承载三套模板——SVG 单图模板（条形/折线/饼，声明式、零依赖）、零依赖 HTML 看板模板（纯 CSS 条形 + 内联 SVG，内网安全默认）、ECharts CDN 版看板模板（外网增强）；模板内置口径行/结论段/明细表/洞察四段骨架，agent 只填数据。
3. **`agents/README.md` 六宿主指南补「可视化通道」对照**：与能力卡对齐（ZCode=HTML+browser-use；Claude 桌面=HTML artifacts；ChatGPT app/Codex=HTML 文件+canvas；豆包=show_widget）。
4. **验收轻量化**：对话内 HTML 看板走模板即免 visual-judge；PNG 留档交付才验收（首跑全量抽查一次模板质量）。
5. **评估无需改断言**：`contains-any` 已兼容全部新通道；ddl-005/007 rubric 背景语「以文件路径/文件名引用交付即视为已配图」可顺带扩为「含 HTML/Mermaid 引用」。
6. **待 ZCode 实测结果回填**：图片内联渲染、对话流 Mermaid 两项实测结论并入能力卡后再定稿第五节措辞。
7. **拍板项**：① 默认模板取零依赖 CSS 版（推荐）还是 ECharts 版；② Unicode 条形图的定位（兜底不推广 vs 不纳入）；③ 是否保留「PIL 直绘」于技能正文（建议降为附录一句话）。

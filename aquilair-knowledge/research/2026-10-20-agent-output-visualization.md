# Agent 经 MCP 取数后的输出可视化调研（两插件对比 + 业界路线）

> 调研日期：2026-10-20 ｜ 场景：资料调研 + 代码库摸底（双仓库对比）
> 调研问题：① aquilair-skills 与 aquilair-ontology 出图做法有何不同；② agent 经 MCP 拿到业务数据后除 Markdown 外怎么可视化；③ Palantir Adaptive Cards 文档的做法定位；④ 如何让插件「给任何 AI 客户端都能带图」
>
> **修订记录（同日二稿）**：并入 dsh 客户端（deepseek-flash）同日平行调研的增量结论（会话 `session-38302e1e`，经用户授权查看）。两轮调研在两插件范式分野、数据不外发红线、Palantir 仅 Copilot 生态生效等关键判断上**互相印证一致**；dsh 侧挖到的 **SEP-1865 MCP Apps 官方跨宿主 UI 扩展**为本稿最大增量（已经本方独立核实官方博客与规范原文），据此修订第四节路线分类与第八节建议。dsh 侧补充的 WorkBuddy 内置 Visualizer、豆包 renderer 代码块细节来自第三方社区解析（非官方文档），已标注可信度。
>
> **同日补遗（主会话架构推演增量）**：①概念澄清——宿主=LLM（agent 运行时）+UI 壳（展示界面），各宿主 LLM 端同质，真正因宿主而异的只有 UI 壳展示通道；②MCP Apps 跨宿主成立的根因与 Adaptive Cards 锁死微软生态互为镜像（渲染资产随插件分发、宿主只需通用沙箱 vs 要求宿主内嵌专属渲染引擎）；③落地架构升级为「一份数据契约、两条渲染通路」，Adaptive Cards 降级为微软内部格式。散见 TL;DR 第 6 条、路线 5、第八节建议 1/6，接入前提待核实三件见第六节。
>
> **同日三稿（豆包历史路径一手验证）**：用户提供 `aily-data-visualizer (1).zip` 原包实地核验——技能本体**只有生成层、没有交付层**，「aily-cli 上传→评论内联」属豆包宿主运行时层而非技能内容，修正二稿转述；详见 5.1 节三稿补充段与来源 14。
>
> **2026-10-21 实测日**：MCP Apps PoC 端到端成功（ZCode 沙箱渲染，用户确认）+ 多宿主实测（WorkBuddy ✓ 零改动跑通 / 豆包 ✗ 预期内降级，详见第六节实测矩阵）；据此修复「声称已渲染」如实性违规（工具返回增 `ui_hint` 降级自描述）。
>
> **2026-10-22 四稿（GenUI 概念框架与三方案对拍）**：并入用户提供外部资料的 GenUI 三分类框架（5.1 节）；以一手实测证伪/修正该资料两个关键论断（方案 A「平台自动渲染」、方案 B「服务端分支维护多套 UI」），对拍结论见 5.2 节。

## 一、结论（TL;DR）

1. **两个插件的分野不是「数据可视化 vs 回复可视化」**——两者出的都是数据图（本体拓扑图也是结构数据可视化），且两者都有「回复可视化」（交互式输出）的边缘设计但均无代码实现。真正的区别是**渲染引擎的位置**：
   - **aquilair-skills**：渲染引擎在**提示词里**——`viz-templates.md` 模板库随插件分发，agent 运行时按模板现场 Write 出 SVG 单图 / 零依赖 HTML 看板 / ECharts CDN 看板。零环境依赖、单图 20-40 秒，仓库内无任何渲染脚本。
   - **aquilair-ontology**：渲染引擎在**确定性脚本里**——`render_topology.py` 把 DSL 转 Mermaid 源，`render_image.py` 用 Playwright 无头 Chromium（mermaid@11 CDN 优先 + 本地 UMD 缓存兜底）落盘 PNG/SVG，另产零依赖交互式 HTML。同输入同输出、可复现，但需一次性安装 Playwright。
   - **选型根因是图表复杂度**：统计图（N 行 2-3 列）LLM 按模板填数可靠；拓扑图（26 实体 234 属性 18 规则、分层布局、贝塞尔连线、标签防重叠）必须确定性脚本，LLM 手写布局不可靠。两个选择都对，不是随机。
2. **MCP 取数后出图共六条路线**（详见第四节）：MCP 原生 ImageContent（base64 直返）、外部渲染服务（QuickChart/mermaid.ink）、本地渲染管线（Playwright/matplotlib）、文本型图表代码（Mermaid/HTML，客户端渲染）、**MCP Apps（SEP-1865 官方跨宿主 UI 扩展，2026-01-26 Final）**、私有宿主通道（Gen UI/artifacts/show_widget/Adaptive Cards）。其中 **MCP Apps 是「跨任意客户端」目标下唯一的官方标准通道**：工具经 `_meta.ui.resourceUri` 指向 `ui://` HTML 资源，宿主在沙箱 iframe 渲染并可双向 JSON-RPC 交互；Claude、ChatGPT、VS Code、Goose 已支持，WorkBuddy（腾讯云官方文档）、Microsoft 365 Copilot 等亦在生态内；不支持的宿主按 progressive enhancement 原则自动退回普通 MCP 响应。
3. **Palantir 文档的做法是第三种架构：数据与展现彻底分离**——MCP 工具只返回原生 JSON，Adaptive Card 模板（1.5 版 JSON）作为静态资产随插件分发，经 `ai-plugin.json` 的 `capabilities.response_semantics.static_template` 接线，**客户端**按模板声明式渲染（`$data`/`${field}` 绑定）。已核实：该机制**仅在 Microsoft 365 Copilot / Copilot Studio / Teams 生态生效**，其他 MCP 客户端会忽略它——它不是通用方案，但「模板静态分发、运行时只流数据」的思想与 aquilair-skills 的模板库同构，区别只在渲染执行者是宿主客户端还是 LLM。
4. **「给任何 AI 客户端都能带图」的最大公约数** = 本地文件 + Markdown 图片引用（`![](绝对路径)`）+ Mermaid 代码块 + 零依赖 HTML 三件套；MCP ImageContent 是协议标准但各客户端是否向用户展示（而非仅喂 LLM）参差不一；**外部渲染服务把业务数据发第三方，企业场景直接排除**。
5. **推荐架构：分层交付 + 按图表复杂度路由渲染引擎**。aquilair-skills 的「宿主能力卡 + 三场景分流」已是这个架构的雏形；ontology 的 Playwright 管线可作为高保真通道沉淀为两插件共享资产。另发现 ontology 两个与「跨客户端」目标冲突的实际风险（见第六节）。
6. **（补遗）宿主=LLM+UI 壳；跨宿主通用性的真正来源是「渲染资产随插件分发、宿主只需通用能力」**。各宿主的 LLM 端同质（都是能读模板、写文件的 LLM），差异只在 UI 壳展示通道——据此 LLM 端渲染（宿主只需显示文件）与 MCP Apps（宿主只需标准沙箱）是同一模式的两档实现，而 Adaptive Cards 要求宿主内嵌专属渲染引擎，故锁死微软生态。落地架构升级为「**一份数据契约、两条渲染通路**」：整形后的画图数据契约（data.json：字段/语义色档位/标注 + 模板 ID + 来源元数据）为统一输入，通路① server 端 `ui://` bundle（render_dashboard 类工具挂 `_meta.ui`），通路② LLM 端 viz-templates 兜底（未支持宿主长期保留；**ZCode Desktop 已核实支持**——本机 3.16.2 含完整实现，见第六节）；progressive enhancement 使能力分层由宿主自动决定、免掉插件侧宿主探测（见第八节建议 1）。

## 二、背景与调研问题

用户开发了两个插件（aquilair-skills 技能工厂、aquilair-ontology 本体建模），都需要图片渲染能力，希望弄清两者做法差异、业界经 MCP 取数后的输出可视化方案（参照 Palantir 的 build-adaptive-card 文档），最终目标是让插件**给任何 AI 客户端都能带图**。

子问题拆解：
- Q1 aquilair-skills 的出图方案全貌（技术路径、交付方式、跨客户端设计）
- Q2 aquilair-ontology 的出图方案全貌
- Q3 MCP 协议层面对「工具返回富内容/图片」的标准支持
- Q4 业界图表类 MCP server 与各客户端的可视化通道现状
- Q5 Palantir Adaptive Cards 机制的定位与适用范围
- Q6 「任何客户端带图」的可行架构

## 三、两种范式详解（Q1/Q2）

### 3.1 aquilair-skills：提示词模板驱动（统计图场景）

核心实现只有一份 Markdown 模板库，无任何渲染脚本：

| 文件 | 角色 |
| --- | --- |
| `skills/aquilair-data-delivery/SKILL.md` | 横切规范：铁律「只回纯 Markdown 表格=违规」；三场景通道分流 + 宿主能力卡 |
| `skills/aquilair-data-delivery/references/viz-templates.md` | **核心实现**：模板 A/A2/A3（声明式 SVG 条形/折线/环形）、模板 B（零依赖 HTML 看板，纯 CSS 无 JS）、模板 C（ECharts CDN 增强） |
| `skills/aquilair-data-delivery/references/dashboard-playbook.md` | 看板骨架/语义配色（P0 红 #d93025 ~ 正常绿 #188038）/分场景示例 |
| `agents/README.md` 第六节 | 六宿主可视化通道对照表（WorkBuddy/豆包、ZCode 桌面、Claude 桌面、ChatGPT、文档宿主） |

交付按三场景分流：单图·对话内直呈（宿主内联组件 > **SVG 文件+图片内联** > HTML 单图页）；多图·交互看板（宿主预览 > **零依赖 HTML** > ECharts 增强）；留档·嵌入文档（PNG > Mermaid 代码块）。降级铁律「换等价通道，不修环境」。

历史路径（matplotlib+plotly 出 PNG → 上传 → 内联）已于 2026-09-24 弃用：Python 绘图链慢且脆（本机 NumPy 2.x 二进制冲突即坏）、需 visual-judge 子代理验收，单轮 3-5 分钟；模板路径约 20-40 秒，提速约一个数量级（依据：`aquilair-knowledge/research/2026-09-24-dataviz-cross-host.md`）。

### 3.2 aquilair-ontology：确定性脚本驱动（结构图场景）

| 文件 | 角色 |
| --- | --- |
| `plugins/ontology-forge/scripts/render_topology.py`（38KB） | DSL YAML → Mermaid classDiagram / 分层 flowchart / diff 三色图 / 交互式 HTML |
| `plugins/ontology-forge/scripts/render_image.py`（13KB） | Mermaid → PNG/SVG：Playwright 无头 Chromium + 本地 HTTP 服务（避开 file:// CORS），mermaid@11 CDN 优先、本地 UMD（11.17.2，3.4MB）兜底，两级都失败显式中文报错不静默降级 |
| `plugins/ontology-forge/assets/mermaid.min.js` | 断网兜底缓存 |
| `skills/ontology-modeling/SKILL.md` | ③⑧ 步出图规定：`--interactive` 自包含 HTML + `--image both` PNG/SVG 双轨；环境不满足如实告知、不静默退化 |

交付形态：`topology.png/svg`（存档/呈审，文件落盘）+ `topology.md`（Mermaid 源=可编辑形态）+ `topology-interactive.html`（手写 SVG+原生 JS，零依赖，定位为「泛化 Gen UI 替代」）。另有 CQ 三态勾选组件的 Gen UI 设计（widgetState 回传），**仅存在于 SKILL.md 提示词层，无代码实现**。

### 3.3 对比总表

| 维度 | aquilair-skills | aquilair-ontology |
| --- | --- | --- |
| 渲染引擎位置 | 提示词模板库，LLM 现场生成 | 确定性 Python 脚本 |
| 产物 | SVG / 零依赖 HTML / ECharts HTML | Mermaid 源 / PNG / SVG / 交互式 HTML |
| 出图耗时 | 20-40 秒/图（LLM 生成） | 秒级（脚本执行） |
| 环境依赖 | 零（模板 C 需 CDN） | Playwright+Chromium 一次性安装 |
| 可复现性 | 靠模板约束，LLM 有自由度 | 确定性，同输入同输出 |
| 图表类型 | 业务统计图（条形/折线/环形） | 结构图（类图/分层/diff 拓扑） |
| 跨客户端设计 | 宿主能力卡（6 宿主对照）+ 三场景分流 | 文件落盘 + 呈审引用，无宿主适配层 |
| 交互式输出 | 靠宿主（browser-use/artifacts/present_files） | 自包含 HTML（自带交互）+ Gen UI 仅纸面设计 |
| 数据安全 | 数据不出本地 | 数据不出本地 |

## 四、MCP 取数后的输出可视化六条路线（Q3/Q4）

### 路线 1：MCP 原生 ImageContent（协议标准）

MCP 规范（2026-07-28 版）tool result 的 `content` 数组原生支持 `{"type": "image", "data": "<base64>", "mimeType": "image/png"}`，且所有内容类型支持 annotations（可标 `audience: ["user"]` 提示宿主该内容面向用户展示）。另有 `structuredContent` + `outputSchema`（结构化 JSON 通道，面向客户端校验与渲染）与 `resource_link`（返回 `file:///` 等 URI 由客户端按需取用）。
- 优点：协议内闭环、无文件系统依赖（适合远程/无盘客户端）。
- 缺点：base64 膨胀 33% 占 token 与带宽，大图不现实；**各客户端是否把 image 展示给用户（而非仅作为 LLM 上下文）实现参差**——协议只定义了传输，没定义展示义务。

### 路线 2：外部渲染服务

QuickChart MCP Server（Chart.js 配置 → PNG URL）、mermaid.ink / kroki（Mermaid 源 → 图片 URL）等。
- 优点：零本地依赖、任意客户端拿到 URL 即可展示。
- 缺点：**业务数据外发第三方，企业场景数据安全红线**；需外网；服务可用性不可控。供应链库存/调拨数据不适合此路线（两家插件均未采用，判断正确）。

### 路线 3：本地渲染管线（ontology 路线）

matplotlib / PIL / Playwright+mermaid 等，本地出 PNG/SVG 落盘。
- 优点：可复现、高保真、数据不出本地；产物是文件，任何能显示本地图片的客户端都能用。
- 缺点：环境依赖重（skills 曾因 NumPy 2.x 冲突弃用 matplotlib）；CI/无头环境需额外装 Chromium。

### 路线 4：文本型图表代码，客户端渲染（最大公约数）

- **Mermaid 代码块**：GitHub/GitLab/多数 Markdown 客户端原生渲染；
- **零依赖单文件 HTML**：浏览器打开即用，任何环境可用；
- **SVG 文件 + Markdown 图片引用**：桌面客户端普遍支持本地图片内联；
- Vega-Lite JSON 等声明式规范同属此类。
- 优点：数据不出本地、无环境依赖、客户端能力不足时退化为可读代码/文件。缺点：最终呈现效果依赖客户端渲染能力，不是每个聊天客户端都渲染 Mermaid。

### 路线 5：MCP Apps——SEP-1865 官方跨宿主 UI 扩展（2026-10-20 二稿新增，已核实）

**这是「给任何 AI 客户端都能带图」目标下唯一的官方标准通道**（本方独立核实：官方博客原文 + 官方规范文件，与 dsh 侧转述一致）。

- **机制**：MCP 工具在结果上声明 `_meta.ui.resourceUri` 指向 `ui://` 资源（服务端提供的自包含 HTML/JS bundle，MIME `text/html;profile=mcp-app`）；支持该扩展的宿主把资源渲染进**沙箱 iframe**，与 server 通过 JSON-RPC over postMessage 双向通信（可回传用户操作、触发反向工具调用）。SDK：`@modelcontextprotocol/ext-apps`（server 侧 App 类），宿主侧推荐 MCP-UI 的 AppRenderer。
- **状态**：SEP-1865 已 **Final**（2026-01-26 发布，MCP 第一个官方扩展）。已支持宿主：Claude（web+桌面）、ChatGPT、VS Code、Goose、**ZCode Desktop（2026-10-20 双证核实：官方 UI_PLUGIN.md + 本机 3.16.2 asar 字节级验证，且实现为超集——侧栏/可见性/展示模式，见第六节）**；WorkBuddy（腾讯云官方接入文档）、Microsoft 365 Copilot、Postman、LibreChat 等随后跟进；JetBrains/AWS 系在探索。
- **关键设计原则——progressive enhancement**：宿主不支持 `_meta.ui` 时，同一工具仍以普通 MCP 响应工作（文本+结构化数据）。这意味着走 MCP Apps 的方案**天然兼容全部存量客户端**，能力分层由宿主自动决定，与 L0/L1/L2 分层架构完美衔接。
- **限制**：宿主侧实现是自建工程（官方仓库明言除示例外无受支持的 host 实现，需按 AppRenderer 自建双 iframe 沙箱+CSP+同意 UI）；对插件作者则是「服务端多暴露一个 ui:// 资源」，成本低。
- 顺带：OpenAI 的 Apps SDK（`openai/outputTemplate` + `window.openai` 桥）是私有前身，OpenAI 现建议基线走 MCP Apps。
- **（补遗）跨宿主成立的根因**：渲染资产（自包含 bundle）随插件（server）分发，宿主只需实现通用沙箱执行环境——与 aquilair-skills「模板随插件分发、宿主只需显示文件」是同一模式的两档实现（插件带资产、宿主给通用能力）。反面即 Adaptive Cards：渲染引擎装在 UI 壳里且为专属引擎，宿主不装就 nothing，故锁死微软生态。结论：跨宿主通用性的来源不是「谁来渲染」，而是「**渲染资产是否随插件走、对宿主能力要求是否足够低**」。

### 路线 6：私有宿主通道（体验最好，绑定单一生态）

- ZCode：Gen UI（会话可视化目录+引用即渲染+window.zcode 桥）；
- Claude 桌面：artifacts（HTML 写盘即运行）；ChatGPT：canvas；豆包/WorkBuddy：show_widget / present_files；
- **Microsoft 365 Copilot：Adaptive Cards**（即 Palantir 文档的做法）。
- 共性：均为宿主能力，插件只能做文字层引用/能力探测，离开对应生态即失效。

## 五、Palantir Adaptive Cards 方案定位（Q5）

那份 `build-adaptive-card.zh.md` 本身是一个 Claude skill（操作指引），引导 agent 为 MCP 工具生成 Adaptive Card 模板并接线。机制全貌（已对照 Palantir 官方文档核实）：

1. **数据与展现分离**：MCP 工具必须返回**原生 JSON 对象/数组**（双重序列化的字符串无法绑定模板，文档明确要求修复）；展现由静态模板文件 `appPackage/adaptiveCards/<toolName>.json` 定义，随插件分发、构建时内联。
2. **声明式绑定**：卡片版本 1.5；`{"value": [...]}` 信封用 `"$data": "${value}"` 重复容器，扁平数组用 `"${$root}"`，单对象用 `${fieldName}`；FactSet/ColumnSet 排版、`$when` 判空守卫、`formatNumber` 货币格式化；模板语言不支持 `.length`、日期/数组/window 函数。
3. **接线方式**：`ai-plugin.json` 对应函数条目内 `capabilities.response_semantics.data_path` + `static_template.file`；`response_semantics` 必须在 `capabilities` 内部。
4. **适用范围（关键限制）**：官方文档明确该机制面向 Microsoft 生态（"Adaptive Cards are a versatile UI framework for Teams, Copilot, and Outlook integrations"），配置章节挂在 Microsoft Copilot Studio integration 之下；**其他 MCP 客户端会忽略 response_semantics，退回纯文本展示**。

**对我们的启示**：Adaptive Cards 不是「任何客户端」的答案，但它的两点思想可直接吸收——①工具返回**原生结构化 JSON**（对应 MCP structuredContent + outputSchema），把「可渲染性」留在协议层；②**展现模板是随插件分发的静态资产**，运行时只有数据流过。aquilair-skills 的 viz-templates.md 已是同构实现（模板静态分发、agent 填数），只是渲染执行者是 LLM 而非宿主。

### 5.1 补充：WorkBuddy 与豆包的可视化通道（二稿新增，来源 dsh 会话调研，可信度见标注）

**WorkBuddy 实为三层结构**（勿混为一谈）：
1. **内置 Visualizer**（自家 agent 专用）：`read_me(modules=["diagram"|"chart"|...])` 先加载设计系统（9 色系×7 色阶、字号/间距/viewBox 约定），模型手写 SVG/HTML 片段后经 `show_widget` **直接注入对话 DOM 内联渲染**（非文件非 iframe）。一致性来自设计系统约束而非 schema。〔可信度：第三方机制解析（cnblogs）与复刻实验仓库，非官方文档〕
2. **MCP Apps 通道**（第三方 MCP 用）：腾讯云官方文档已明确支持 `io.modelcontextprotocol/ui` 扩展（`ui://` + 沙箱 proxy iframe + AppBridge JSON-RPC，反向工具调用逐次授权）。〔可信度：腾讯云官方文档〕
3. **交付层**：`present_files(files)` 文件卡片 + HTML 实时预览面板。

**豆包走了「图片上传 → HTML 代码块」的迁移**：现行协议是回复正文输出 ` ```html type="renderer" ` 代码块，由消息渲染器原地渲染（禁用文件工具产图；CSS 全内联、≤300 行、外部库限 jsDelivr）；历史路径是 matplotlib 出 PNG → `aily-cli image upload` → 评论内联（正是 aquilair-skills 2026-09-24 弃用的同款路线）。〔可信度：社区技能整理（SkillsMP），官方原文未获取〕

**历史路径已获一手材料验证（三稿补充，2026-10-20）**：用户提供 `aily-data-visualizer (1).zip` 原包（frontmatter 为 `name/label/description` 豆包系格式，v1.0.0，2026-04-08），实地核验（解压 + 全文 grep + 逐文件精读）结论——**技能本体只有「生成层」，完全没有「交付层」**：
- `scripts/generate_charts.py`（9.1KB）：matplotlib/seaborn/plotly 通用函数库——`create_bar_chart / line / pie / scatter / heatmap / dashboard` 六个函数，`savefig` 出本地 PNG 即终点，无任何上传/内联逻辑；
- `assets/chart_template.py`（9.8KB）：写死示例数据的 matplotlib 演示模板（销售/用户/KPI/相关性四个 dashboard）；
- `references/data_visualization_best_practices.md`（6.2KB）：通用教材式指南（图表选型/设计原则/调色板/常见错误/检查清单），无宿主相关内容；
- 全包 grep `aily|cli|upload|上传|评论|内联|show_widget|renderer|present|豆包` 仅命中技能名与标题，**零宿主协议字样**。
据此修正二稿转述：**「aily-cli image upload → 评论内联」不在技能包内，属豆包宿主运行时层**（agent 环境预置 aily-cli 工具 + 平台侧规定交付动作）。豆包架构实为「**技能管生成 + 宿主管交付**」——生成与交付分离的又一实例，与 Palantir「server 出数据模板、宿主渲染」同构（粒度更粗：豆包交付的是位图文件，Palantir 交付的是数据+模板）。
另两点一手观察：① 原版技能未配置 matplotlib 中文字体（无 `font.sans-serif` 设置），中文标题直跑会豆腐块——aquilair 模板用 SVG `font-family` 系统字体回避此坑，稳健性佐证+1；② 包内带 `test_skill.py` 与 `__pycache__/...cpython-310.pyc`（编译残留），说明是流转过的副本、未必是市场原版，但「技能不含交付协议」这一点确凿。

**四家光谱**（dsh 侧归纳，本方认可其框架）：从「声明式最安全」到「任意代码最灵活」——
`Adaptive Card（Palantir/Copilot）→ 设计系统约束的 SVG/HTML（WorkBuddy Visualizer）→ 自由 HTML 代码块（豆包 renderer）→ 沙箱 ui:// widget（MCP Apps）`。越右表达力越强，越左越稳定可审计。自家两个插件（模板约束 SVG/HTML + DSL 确定性出图）落在光谱左中段，与 WorkBuddy 内置路线思路相近。

**GenUI 概念框架并入（2026-10-22 四稿，用户提供外部资料）**：GenUI（生成式 UI）= Agent 运行时动态选择/生成可交互 UI 的**范式**，三类实现风格——受限组件式（Bounded，从注册组件库挑选，企业最常用）/ 声明式（JSON 描述 UI 结构，宿主渲染）/ 完全自由生成（LLM 直出 HTML，XSS 风险）。MCP Apps、OpenAI Apps SDK、Google A2UI（声明式、面向 Flutter 原生）、CopilotKit 均为 GenUI 的不同实现方案；上方四家光谱即三类风格在业界的具体分布。MCP Apps = GenUI 的**开放协议标准实现**（只能运行在 MCP 宿主——这也是它的边界）。

**三分法修正**（对用户原始问题的最终口径）：①数据可视化（量，data-delivery）②结构可视化（关系，ontology-forge）③响应卡片可视化（工具结果的统一呈现，Palantir/Copilot）。「回复可视化」对应的是第③类——两个插件目前都没有，也不必都有；第③类的跨客户端实现已由 MCP Apps 官方化（路线 5），Adaptive Card 模板仅余微软生态内部深度集成（Teams/Outlook 卡片）价值，见第八节建议 6。

### 5.2 多平台 GenUI 方案选型对拍（2026-10-22 四稿，外部资料三方案 × 本方一手实测）

外部资料给出三方案：A 统一输出结构化数据/平台各自渲染、B 服务端识别宿主分支返回对应 UI、C 统一自研 HTML 沙盒。**以 PoC 实测证据对拍后的结论**：

| 资料论断 | 对拍结果 |
| --- | --- |
| A「各平台根据自身能力**自动渲染**可视化」 | **✗ 豆包实测证伪**：模型拿到完整 spec JSON 不会自发渲染，只回文字且声称「已渲染」（如实性违规）——数据返回 ≠ 渲染发生。**修正版 A = 数据契约 + 降级自描述（ui_hint）**：工具返回内嵌降级指引，模型读到「界面未出现看板→须按宿主方言兜底出图，禁止仅文字声称已渲染」。缺后半段的方案 A 在豆包类宿主必然翻车 |
| B「服务端按宿主标识分支维护多套 UI」 | **✗ 前提被 MCP Apps 消解**：progressive enhancement 让**协议层自动分支**——同一响应（structuredContent + `_meta.ui`），ZCode/WorkBuddy 零改动双渲染（实测）。服务端无需感知宿主；分支只发生在 MCP Apps 覆盖不到的宿主（豆包/GPTs），且形态是「模型侧兜底」（ui_hint 引导）而非「服务端分支」，成本远低于多套 UI 定义。另：MCP 工具调用层无标准化宿主标识头，资料设想的「header 判宿主」可行性存疑 |
| C「一套 JS 跑全部宿主不可能」 | **✓ 一手证据支持**：ZCode 内嵌 app-bridge / WorkBuddy 沙箱 iframe / 豆包无沙盒，通信桥互不通。补充：**零依赖 HTML 文件**是比「HTML 响应」更通用的兜底形态（不依赖沙盒，浏览器打开即用——L0 通道既有结论） |
| 阶段路径「先纯数据→后交互分支」 | **✗ 不需要两步走**：资料预设 MCP Apps 分支高维护成本，实测服务端成本=两个装饰器+一行 `ToolResult.meta`，分层由协议自动完成，可直接上 |
| 事件适配层（豆包 componentEvent vs MCP AppBridge 不统一） | **+ 值得记录的后续风险**：本方 PoC 页面为只读看板、未做反向交互，此坑尚未踩到；若未来做下钻/表单回传需适配层 |

**对拍后的架构定位**：本方双通路架构 = 修正版 A（数据契约）+ MCP Apps 自动分支（协议内置，免维护）+ ui_hint 模型侧兜底（豆包/GPTs 类宿主）+（未来按需）事件适配层。外部资料三方案均为此架构的局部投影。

## 六、风险与信息缺口

**调研中发现的两个实际风险（与「跨客户端带图」目标直接冲突，属调研副产品）**：
1. **ontology 的 WorkBuddy 分发包不含渲染缓存**：`pack_workbuddy.py` 的 INCLUDE_ITEMS 不含 `assets/`，即 `workbuddy/aquilair-fde-0.4.1.zip` 内没有 mermaid.min.js——该分发形态下断网时 `--image` 只剩 CDN 单路径，与 SKILL.md 承诺的「本地缓存兜底」不符。`check_dist.py` 也未对 assets 做门禁。
2. **mermaid 版本双轨不锁定**：CDN 固定到 major（`mermaid@11` 浮动），本地缓存是 11.17.2——同一 DSL 断网/联网可能渲染出不同版式，diff 图场景下跨端不可复现（此前审计已多次提及 CRLF 同类问题，此为同族）。

**信息缺口（未核实，如实列出）**：
- **豆包 Skill 组件 Schema / componentEvent**（2026-10-22 外部资料转述：豆包原生组件优先、表单/审批面板类组件、事件回传 componentEvent）——豆包兜底路径的第二种方言候选（vs renderer HTML 代码块），待豆包 ui_hint 复测时观察模型实际选择并核实其官方文档；
- **Microsoft Flint / flint-chart-mcp**（声明式图表 spec 编译器，本地渲染数据不出机）：来自 dsh 侧调研转述（含 VIS 2026 论文 arXiv:2610.01873 佐证「LLM 手写可视化 DSL 失败模式」），本方三次抓取 GitHub 均遇 443 阻断未独立核实，采信前建议自查仓库；
- WorkBuddy 内置 Visualizer 细节（read_me 设计系统/show_widget）来自第三方解析与复刻仓库，豆包现行 renderer 代码块规则来自社区技能整理，**均非官方原文**（豆包历史路径 aily-data-visualizer 的技能本体已由一手 zip 核实，见 5.1 三稿补充；其现行 renderer 协议仍待官方原文）；
- ChatGPT/Codex 对本地图片 Markdown 引用的实际渲染支持未实测（skills 宿主能力卡中也标注「待实测」）；
- MCP ImageContent 在各主流客户端是「展示给用户」还是「仅作 LLM 上下文」，仅有协议层证据（audience 注解的存在暗示宿主行为不统一），未逐一实测；
- Adaptive Cards 在非 Microsoft 聊天客户端无渲染支持这一结论来自 Palantir 官方文档语境，未找到主流客户端接入 Adaptive Cards 的反例。

**MCP Apps 接入前提核实（补遗新增，2026-10-20 同日完成两项核实）**：

- ~~ZCode 支持状态~~ **已核实，结论翻转：ZCode Desktop 已支持 MCP Apps**。双证据：①官方仓库 [zai-org/ZCode `UI_PLUGIN.md`](https://github.com/zai-org/ZCode/blob/main/UI_PLUGIN.md)（main 分支）——机制与标准一致（`_meta.ui.resourceUri` + `ui://` 资源 + `text/html;profile=mcp-app`），且为超集实现：会话侧栏（清单 `ui.surfaces` + `_meta.ui.surface`）、可见性控制（`_meta.ui.visibility: ["model","app"]`）、`requestDisplayMode`（inline/fullscreen）、页面→服务 `callServerTool`（沿用 Agent 权限与审批）、页面→对话 `updateModelContext`/`sendMessage`；②本机 3.16.2.8769 的 app.asar 字节级验证——内嵌官方 `ext-apps/dist/src/app-bridge.js`（约 34KB）、`text/html;profile=mcp-app` MIME 校验 17 处、`_meta` 变量化取 `resourceUri` 并校验 `ui://` 前缀的运行时代码、`callServerTool` 25 处。限制：仅本地工作区（Web/手机/远程不支持交互面板）；HTML 资源 ≤16 MiB、`structuredContent` ≤64 KiB、`content` ≤32 KiB；Gen UI 与 MCP Apps 为两套机制、API 不混用。**方法论教训：`_meta.ui` 字符串 grep 0 命中是 minify 属性名变量化所致，不能据此判不支持**——宿主能力验证须搜行为关键字（`profile=mcp-app`/`callServerTool`/`ui://`）而非复合属性路径。
- **data-service 框架：已核实（2026-10-20 拉取公司 GitLab `el-aquilair/mcp-service` 至本地平级目录 `D:\documents\elitesland-workspace\mcp-service`）——FastMCP 命中最优分支**。栈：Python ≥3.13 + `fastmcp>=2.12`（uv.lock 锁 **4.0.5**）+ uv/hatchling。FastMCP Apps 自 3.0.0 引入，4.0.5 含该能力，接入形态：`@mcp.tool(app=AppConfig(resource_uri="ui://..."))` + `@mcp.resource("ui://...")` 返回 HTML 字符串（自动带 `text/html;profile=mcp-app` MIME）——**两个装饰器即接上，确为「近原生」**。架构为 proxy 模式（metadata/data/action 三后端，统一信封解包后工具直接 return dict，满足「原生结构化 JSON」前提），故 `ui://` bundle 收敛在 proxy 层即可、后端三服务不用动。两点注意：①该仓库（单提交 init）的 `objects_*`/`actions_*` 尚为占位，且工具命名与线上 mcp0/mcp1 暴露的（`get_meta_objects`/`query_instances_by_filter` 等）不同——系新一代 proxy 重构，线上单体源码与它的关系待团队确认，但 Python + FastMCP 栈结论可迁移；②页面端 ext-apps JS SDK 建议用 `app-with-deps` 单文件内联进 bundle（自包含，避免 CDN/CSP/内网网络依赖，ZCode 16 MiB 限制内富余）。
- **bundle 承载（仍待办，认知已修正）**：data-service 为远程 HTTP 服务，`ui://` 资源走 MCP 协议的 resources 机制由服务端注册提供（`resources/read` 获取），**不是**另起静态文件目录/独立 HTTP 端点；需确认服务框架的资源注册 API，及宿主沙箱 CSP 对 bundle 外部引用的约束——零依赖模板 B 天然满足最严 CSP。

**PoC 端到端实测成功（2026-10-21，ZCode Desktop 对话内渲染出完整看板）**：在 `mcp-service`（本地克隆）新增 viz 工具组——`render_dashboard` 工具收画图数据契约（title/rows/source/level 枚举校验）+ `ui://viz/dashboard.html` 自包含 bundle（模板 B 风格页面：语义配色/零基线/徽标冗余编码/明细表；ext-apps SDK 2.0.3 `app-with-deps` 经 base64 data-URL import 内联，bundle 共 1.12MB，远低于 ZCode 4 MiB 上限）。ZCode 3.16.2 实测链路证据（`~/.zcode/v2/logs/2026-10-21.log` 的 `[plugin-ui]` 段）：`lifecycle preparing → prepareSandbox resource ready (htmlBytes 1122796) → registered → mounted → running`，零报错；用户确认对话流内渲染出完整看板。**实施三坑（后续接入必读）**：① FastMCP 的 `@tool(app=AppConfig(...))` 只把 UI 声明写进 tools/list，**结果级 `_meta.ui` 必须经 `ToolResult(structured_content=..., meta={"ui": {...}})` 显式携带**——官方文档未写明，本方从 ZCode asar 读取代码（`_meta?.ui?.resourceUri`）逆向定位（声明级亦可触发宿主拉取资源，但双保险最稳，且页面收数据依赖结果级通路）；② FastMCP mount 的 namespace 会改写资源 URI：注册名 `ui://dashboard.html` + `namespace="viz"` = `ui://viz/dashboard.html`，须与 `_meta.ui.resourceUri` 严格一致；③ 诊断宿主渲染问题的金矿是 `~/.zcode/v2/logs/<date>.log` 的 `[plugin-ui]`/`[plugin-ui-bridge]` 段（比会话 rollout 日志更贴近 UI 层）。另：fastmcp 已升 4.1.3 并锁 uv.lock；官方对齐项——`_meta.ui.visibility: ["model", "app"]`（ZCode host 约定）、页面「先注册 `ontoolresult` 再 `connect()`」（官方 quickstart）。

**多宿主实测进展（2026-10-21，验证「一份实现覆盖多宿主」主张）**：

| 宿主 | 结果 | 证据与说明 |
| --- | --- | --- |
| ZCode Desktop 3.16.2 | ✅ 渲染成功 | plugin-ui 日志证据链 + 用户确认（上文） |
| **WorkBuddy 企业版** | ✅ **渲染成功** | 用户实测（截图存证，来源 17）：自定义 MCP 添加 `http://127.0.0.1:8000/mcp`（http 传输，无需凭证——viz 工具不碰后端鉴权），同一指令 26 秒完成，对话内渲染出与 ZCode 一致的完整看板（条形图+徽标表+来源标注+结论摘要）。附带证明：**1.12MB base64 内联 bundle 在其沙箱可用**（超其 256KB 预取阈值走回拉路径无碍），契约双保险（定义级+结果级 `_meta.ui`）与官方对齐项全部生效——**同一份实现第二宿主零改动跑通** |
| 豆包 | ❌ 不可用（**预期内**） | 豆包不在 SEP-1865 支持名单（走自家 renderer HTML 代码块协议，见 5.1 节）；豆包场景归入 L0/L3 通路——模型调 viz 工具拿 spec JSON 后按 viz-templates / renderer 代码块兜底（通路②），MCP Apps 通道缺席属 progressive enhancement 的正常降级而非缺陷 |
| Claude 桌面 | ⏳ 待测 | mcp-remote 桥配置已备（`npx -y mcp-remote http://127.0.0.1:8000/mcp` 写入 claude_desktop_config.json），需用户本机装有 Claude Desktop |
| ChatGPT | ⏳ 待部署后测 | 硬要求公网 HTTPS 端点 + 付费计划 + Developer Mode（localhost 不可连，Secure MCP Tunnel 有数据出域顾虑）——与「viz 工具组合入 mcp0/mcp1 正式部署」同一步 |
| VS Code | 未测 | 官方名单在列，后续补 |

## 七、来源清单

| # | 来源 | 类型 | 日期 |
| --- | --- | --- | --- |
| 1 | 仓库实地调研：`D:\documents\elitesland-workspace\aquilair-skills`（viz-templates.md、SKILL.md、agents/README.md、evals 产物记录） | 子代理全仓扫描 | 2026-10-20 |
| 2 | 仓库实地调研：`D:\documents\elitesland-workspace\aquilair-ontology`（render_topology.py、render_image.py、assets、models/xgimi 产物） | 子代理全仓扫描 | 2026-10-20 |
| 3 | `D:\documents\dsh_daily\build-adaptive-card.zh.md` | 本地文档（Palantir Claude skill） | 用户提供的版本 |
| 4 | [MCP Tools Specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) | 官方规范（WebFetch 核实 ImageContent/structuredContent/annotations 原文） | 2026-07-28 |
| 5 | [Palantir Foundry: Ontology MCP tools and agent configuration](https://palantir.com/docs/foundry/ontology-mcp/mcp-tools-and-agent-configuration) | 官方文档（WebFetch 核实 response_semantics 生效范围=Microsoft 生态） | 检索于 2026-10-20 |
| 6 | [Quickchart-MCP-Server](https://github.com/GongRzhe/Quickchart-MCP-Server)、[Mermaid Chart MCP](https://mermaid.ai/docs/ai/mcp-server)、[mcp-server-chart](https://glama.ai/mcp/servers/data-mindset/mcp-server-chart)、[Plots](https://mcpmarket.com/server/plots) | 业界图表 MCP 代表（WebSearch） | 检索于 2026-10-20 |
| 7 | `aquilair-skills/aquilair-knowledge/research/2026-09-24-dataviz-cross-host.md` | 历史选型依据（matplotlib→模板弃用决策） | 2026-09-24 |
| 8 | 记忆 `zcode-gen-ui-portability`（2026-10-16）：Gen UI 是宿主能力，泛化三路径=宿主复刻协议/自然降级/能力探测 | 历史结论 | 2026-10-16 |
| 9 | [MCP Apps 官方博客（2026-01-26）](https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/)（webReader 直读核实） | 官方公告 | 2026-01-26 |
| 10 | [SEP-1865 规范页](https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp) + [ext-apps 正式规范 2026-01-26](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx) + [WorkOS 实现指南](https://workos.com/blog/2026-01-27-mcp-apps)、[FastMCP Apps](https://gofastmcp.com/apps/low-level)（2026-10-20 二次核实：Apps 自 3.0.0 引入，`AppConfig` + `@mcp.resource` 形态，ext-apps JS SDK 有 `app-with-deps` 自包含版） | 官方规范 + 独立第三方（多源交叉） | 2026-01-26/27 |
| 11 | dsh 会话 `session-38302e1e-a0e4-4431-b19f-7f74bdf44e03`（deepseek-flash，5 轮，2026-10-20 13:30–14:40）：平行调研 + WorkBuddy/豆包/Palantir 三分法 + Flint/antvis/A2UI 线索；其 demo 产物 `D:\documents\dsh_daily\viz-demo\`（dashboard.html 1MB 等）已确认存在 | 平行调研（关键结论已由本方核实或标注可信度） | 2026-10-20 |
| 12 | [WorkBuddy Enterprise MCP Apps 接入指南（腾讯云）](https://cloud.tencent.cn/document/product/1831/137044)、[WorkBuddy Visualizer 机制解析](https://www.cnblogs.com/getmoon/p/22066357)、[豆包可视化技能整理](https://skillsmp.com/creators/ahang1598/doubao-workbuddy-qwenwork-skills/doubao-skills-doubao-visualization)（后两者为第三方来源） | 官方文档 + 社区解析 | 经 dsh 调研中转 |
| 13 | [ZCode UI_PLUGIN.md（zai-org/ZCode main 分支）](https://github.com/zai-org/ZCode/blob/main/UI_PLUGIN.md) + 本机 app.asar 字节级验证（3.16.2.8769，node indexOf 多关键字+上下文）+ 本机 `.mcp.json`（仓库根与插件 0.1.3 双份一致，data-service 接入形态） | 官方文档 + 本机实测 | 2026-10-20 |
| 14 | `C:\Users\zishuai\Downloads\aily-data-visualizer (1).zip`（用户提供一手材料）：解压全文核验（SKILL.md / generate_charts.py / chart_template.py / best_practices.md / test_skill.py） | 一手包实证（豆包系技能格式；流转副本） | 2026-10-20 |
| 15 | 公司 GitLab `el-aquilair/mcp-service`（git@code.elitescloud.com，2026-10-20 克隆至本地 `D:\documents\elitesland-workspace\mcp-service`）：pyproject/uv.lock（fastmcp 4.0.5）、server.py、README、src 全量阅读 | 服务端源码实测 | 2026-10-20 |
| 16 | MCP Apps PoC 端到端实测（2026-10-21）：`mcp-service` 本地三个 commit（viz 工具组引入 + ToolResult.meta 结果级修复 + visibility 官方对齐）+ ZCode 测试会话 `session_91d8533c911dba56ec3e3f99e9571277` + `~/.zcode/v2/logs/2026-10-21.log` plugin-ui 段 + 用户确认看板渲染成功（A） | PoC 实测（端到端） | 2026-10-21 |
| 17 | WorkBuddy 企业版多宿主实测（2026-10-21，用户提供截图存证）：自定义 MCP（http://127.0.0.1:8000/mcp）→ 同指令 26 秒渲染出完整看板；豆包同步实测不可用（预期内，不在 SEP-1865 名单）；契约依据=[CodeBuddy MCP Apps 接入指南](https://www.codebuddy.cn/docs/cli/mcp-apps)、[WorkBuddy MCP 配置](https://cloud.tencent.com/document/product/1831/137461) | 多宿主实测 | 2026-10-21 |
| 18 | 用户提供外部调研资料（来源未注明，2026-10-22 对拍）：GenUI vs MCP Apps 概念辨析 + 多平台 GenUI 三方案选型（A 统一数据/B 分支输出/C 统一 HTML 沙盒）+ 豆包 Skill 组件 Schema/componentEvent 线索 | 外部资料（关键论断已经本方实测对拍，见 5.2） | 2026-10-22 |

## 八、建议下一步（二稿修订：MCP Apps 升为跨客户端目标的主通道候选）

1. **（新增，最高优）评估业务 MCP 增加 MCP Apps 通道，落地形态=「一份数据契约、两条渲染通路」（补遗并入）**：`data-service-fnb/mfg` 这类业务 MCP 在返回结构化 JSON 的同时暴露一个 `ui://` HTML 资源（自包含图表页，可复用 viz-templates/dashboard-playbook 的模板），工具结果挂 `_meta.ui.resourceUri`。**双通路架构**：统一输入 = 整形后的画图数据契约（data.json：字段/语义色档位/标注文本 + 模板 ID + 来源元数据；数据整形全部前置、模板只做数据→像素映射——即 Adaptive Cards「模板语言故意笨」纪律的同构吸收），两条通路共用——① server 端 render_dashboard 类工具接收契约数据，返回 `_meta.ui.resourceUri` 指向注入数据的看板 bundle；② LLM 端 viz-templates 现场渲染 SVG/零依赖 HTML 兜底（未支持宿主长期保留；ZCode Desktop 已核实支持，见第六节）。模板 B（零依赖、纯 CSS+内联 SVG）先天适配自包含 bundle 形态，改造成本最低；契约数据落盘同时服务复现、审计对拍（图上数值 vs 工具返回的机器可查）与跨宿主重渲染（不同宿主的 LLM 拿同一契约应渲染出一致的图）。收益：Claude/ChatGPT/VS Code/WorkBuddy 等已支持宿主直接对话内渲染交互图表（下钻/反向工具调用是静态产物做不到的实质跃迁），未支持宿主按 progressive enhancement 退回现有 JSON+文件链路——**一份实现同时覆盖「增强」与「兜底」**，这是「给任何 AI 客户端都能带图」目前唯一走官方标准的路径。**PoC 已于 2026-10-21 完成：ZCode Desktop 实测对话内渲染成功（第六节实测记录 + 来源 16），实施三坑已归档**——下一步：扩展目标宿主清单实测（WorkBuddy / ChatGPT / Claude 桌面），并把数据契约规范反哺进 viz-templates.md 与 SKILL.md（L2 层接线：交付时默认落 data.json、双渲染通路共用契约）。
2. **把「分层交付协议」写成两插件共享的独立规范**（如 `viz-delivery-protocol.md`）：L0 通用底线（SVG 文件 + `![](绝对路径)` 引用 + Mermaid 代码块 + 零依赖 HTML，任何客户端可用）→ L1 协议标准（MCP ImageContent base64，小图直返）→ L2 官方扩展（MCP Apps `ui://`）→ L3 私有宿主（能力探测后启用 Gen UI/artifacts/present_files/show_widget）。协议与业务内容分离，换宿主只改一层（与 2026-10-16 Gen UI 泛化结论一致）。dsh 侧建议的「默认通道改为对话内渲染块」应限定在 L2/L3 内做——L0 底线仍必须是文件+引用，否则「任何客户端」不成立。
3. **渲染引擎按图表复杂度路由**：统计图继续走模板+LLM 现场生成（skills 范式）；结构图/高保真需求把 ontology 的 Playwright 管线抽成共享脚本资产。若复杂统计图（多系列/下钻）的手写 SVG 不稳，可评估声明式 spec 方案（Flint 或 Vega-Lite，先自行核实 Flint 仓库）。
4. **修 ontology 两个风险**：pack_workbuddy.py 补 `assets/`（或 check_dist.py 加门禁）；mermaid CDN 从 `@11` 锁到 `@11.17.2` 与本地缓存对齐。
5. **补实测**：ChatGPT/Codex 对本地图片引用与 Mermaid 的渲染行为，补进宿主能力卡「待实测」格；MCP Apps PoC 同步验证 WorkBuddy 与目标宿主清单。
6. **（补遗改写）Adaptive Cards 降级为 L3 微软生态内部格式，不再是跨客户端目标通道**：M365 Copilot 已在 MCP Apps 支持名单中，跨客户端覆盖由 MCP Apps 统一承担；Palantir 式 response_semantics/Adaptive Card 模板仅在需要深度 Teams/Outlook 卡片集成时按需补做。其前提纪律仍有效：工具须返回原生结构化 JSON（对应 MCP structuredContent），与现有 data-service 返回习惯需对齐——这也是 MCP Apps 通路的同一前提。

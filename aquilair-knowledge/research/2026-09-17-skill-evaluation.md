# Aquilair Skills 评估体系调研报告

> 调研日期：2026-09-17 ｜ 场景：主题资料（为自建业务技能包建立评估体系）
> 调研对象：基于 MCP 数据服务、靠提示词约束行为的 Agent Skills（SKILL.md 范式）应如何评估质量与效果

## 一、结论（TL;DR）

1. **业界没有「skill 专用」的成熟评估标准，但有可直接组装的通用方法论**：Anthropic 官方的 agent evals 方法论（[来源 2](#来源清单)）+ 官方 skill-creator 的轻量迭代循环（[来源 3](#来源清单)）+ 工具层的 promptfoo 轨迹断言（[来源 4](#来源清单)），三块拼起来就是一套完整方案。
2. **你们 README 里的四类验证题（正常/追问/陷阱/护栏）方向完全正确**，正好对应官方方法论的核心要求（"从手动测试开始""正反用例平衡"）。缺的不是理念，是**制度化**：把散在 README 的验证题变成有版本、有判定标准、可重复执行的测试集。
3. **评估应分四层推进**：手动冒烟（现状）→ 结构化测试集 + 人工评分 → 自动化断言（promptfoo 可覆盖大半）→ 生产观测（公司已有 Langfuse，可补审计缺口）。
4. **两个量化红线指标建议零容忍**：确认卡绕过率（写护栏）、事实编造率（陷阱题）。其余指标（触发准确率、格式规范）设爬坡目标即可。
5. **非确定性必须用「一致性」指标**：单次通过不够，官方建议 pass@k（多试一次成功）与 pass^k（多次全过）分开统计——你们 README 已观察到的「行为随宿主模型而异」正是这个问题的体现。

## 二、背景与调研问题

背景：aquilair-skills 已有两个标准化技能（`fnb-inventory-analysis` 只读解释型、`mfg-transfer-allocation` 受控执行型），需要一套评估体系回答两个问题：现有技能好不好？未来新技能怎么验收？

拆出的子问题：

1. Anthropic 官方对 Agent Skills 的开发与评估指导是什么？
2. 业界对 AI agent / 提示词产物的通用评估方法论是什么？
3. 有哪些可落地的评估工具？能力边界在哪？
4. 提示词护栏（确认卡纪律）这类「行为纪律」怎么评？
5. 第三方 skill 的安全风险对本项目有什么启示？

决策维度：评估维度设计、评估方法选型、可持续运营（测试集治理、CI 化、模型变更回归）。

## 三、问题与解法（业界怎么解决「评估 skill」这件事）

Skill 评估的特殊难点：**被评估对象是一段提示词 + 按需加载的参考文档，没有可单测的函数**；行为还依赖宿主模型与非确定性采样。业界的解法分三层：

- **官方轻量派**（skill-creator，来源 3）：不搞正式基准，用 2~3 个真实测试提示词跑草稿，「结果 + 轨迹」一起看（模型是否做了无效功是过度规定的信号），迭代到满意为止。
- **官方系统派**（Anthropic evals 方法论，来源 2）：把 agent 评估工程化——任务（task）+ 测试用例（test case）+ 评分器（grader）+ 测试框架（harness）+ 测试套件（suite），grader 分三类（代码确定性判定 / 模型判定 / 人工判定），能力评估与回归评估双轨制。
- **工具派**（promptfoo 等，来源 4）：把上述 grader 落成声明式配置，断言失败即非零退出，天然可做 CI 质量门禁。

对 Aquilair 最合适的定位：**以官方系统派为骨架、用工具派落地、迭代期保留轻量派**。

## 四、核心发现

### 4.1 官方评估框架（Anthropic，来源 2、3）

**评估三层结构**：

- 任务（task）：agent 要完成的可评分工作，含一个或多个测试用例
- 测试用例（test case）：任务的最小可运行实例——具体输入 + 期望的评估方式
- 尝试（trial）：一个用例的一次执行（非确定性下需多次）
- 评分器（grader）：对 transcript/outcome 打分，**三类**：
  - **代码评分**（确定性）：字符串匹配、静态分析、结果验证、**工具调用验证**、transcript 分析
  - **模型评分**（LLM-as-judge）：rubric 评分、自然语言断言、成对比较、多裁判共识
  - **人工评分**：SME 审查、抽样检查
- 套件（suite）：用例集合

**能力评估 vs 回归评估**（关键区分，直接适用本项目）：

| | 能力评估 | 回归评估 |
| --- | --- | --- |
| 目的 | 探索「agent 能做好什么」 | 守住「已验证的能力不退化」 |
| 通过率预期 | 从低开始爬坡（30% 是正常起点） | 接近 100%，失败即阻塞 |
| 时机 | 开发期、短板专项 | 每次改 skill 措辞 / 换宿主模型 |
| 演化 | 成熟用例「毕业」进回归套件 | 持续累积（bug 单转用例） |

**0→1 路线图**（官方八步，摘与本项目相关的）：

- 早开始：20~50 个来自真实交互/失败的用例即可启动，不用等完美数据集
- 从手动测试开始：把每次发布前手动验证的行为转成用例；每个 bug 都变成一条用例
- 任务无歧义 + 有一致的参考解：如果 0% 通过率且模型表现合理，通常是任务定义坏了
- **正反用例平衡**：应该触发的要测，不应该触发的也要测（防误触发）——对应你们的「陷阱题」
- 精心设计 grader：能用确定性代码判就不用模型判；评**产出**优先于评**路径**；LLM judge 先与人工标注校准
- 读 transcript：失败的用例应该显得「公平」——模型被合理地引导到了错误行为
- 监控饱和：回归套件全绿一段时间后，把精力转向新的能力短板
- eval-driven development：先加用例再改 skill，用例是行为的规格说明

**非确定性指标**：pass@k（k 次尝试至少一次成功，衡量能力上限）与 pass^k（k 次全部成功，衡量一致性/可靠性）分开统计；agent 产品建议关注 pass^k。

**六大方法组合**（瑞士奶酪模型，多层互补）：自动化 evals、生产监控、A/B、用户反馈、人工 transcript 审查、用户研究。工具列举：Braintrust、LangSmith、**Langfuse（自托管开源——公司已有）**、Arize Phoenix。

### 4.2 官方 skill 开发评估要点（来源 1、3、5）

- **Start with evaluation**：先在代表性任务上跑 agent，观察哪里卡壳/需要额外上下文，再针对性构建 skill（评估先于编写）
- 观察维度四项：能力缺口、**token 效率**（SKILL.md 臃肿就拆）、**触发准确性**（name/description 是触发唯一信号）、意外路径或对某些上下文过度依赖
- **评估驱动开发五步**（来源 5 正文）：①无技能跑代表性任务、记录失败与缺失上下文 → ②构建 **3 个**针对缺口的评估场景 → ③测量无技能基线 → ④只写足以通过评估的最小指令 → ⑤执行评估、对比基线、精炼。核心思想：先建评估再写文档，确保解决真实问题而非记录想象的问题
- **Claude A / Claude B 双实例迭代**（来源 5 正文）：实例 A 当「技能设计专家」帮写改技能，全新实例 B 当「真实用户」跑任务；观察 B 的失误，带具体现象回 A 改进，循环。观察信号四种：读文件顺序非预期（结构不直观）、漏跟引用（链接不显眼）、反复读同一文件（内容应上移进 SKILL.md）、从不访问某文件（不必要或信号不足）
- **跨模型测试**（来源 5 正文）：Haiku 关注「指引够不够」、Sonnet 关注「清晰高效否」、Opus 关注「是否过度解释」；发布前检查清单要求在全部计划使用的模型上测过——与本项目 README「行为随宿主模型而异」的观察直接对应
- skill-creator 的循环：草稿 → 2~3 个**真实口吻**的测试提示词（带具体路径/列名/随意措辞甚至错别字）→ 看结果与轨迹 → 改进；**busywork 多 = 过度规定，做减法而非加规则**；对顽固问题换表述框架而不是堆 MUST/NEVER
- 其他与本项目相关的编写硬要求（来源 5 正文）：MCP 工具在 SKILL.md 中须用全限定名 `ServerName:tool_name`（多服务器场景防 tool not found）；引用文件从 SKILL.md 起只允许一层深；超过 100 行的引用文件顶部加目录；术语全程一致；「Good Skills are concise, well-structured, and tested with real usage」

### 4.3 工具层：promptfoo 能力边界（来源 4）

与本项目相关的断言类型：

| 断言 | 可评的 Aquilair 行为 |
| --- | --- |
| `contains` / `not-contains` / `icontains-any` | 输出含「中文名称（编码）」格式；陷阱题输出含「不存在」；**确认卡场景：回复中含确认卡标题且不含 execute 调用后置文案** |
| `llm-rubric` / `g-eval` | 溯源链完整性、先结论后证据、证据来源标注 |
| `factuality` | 基于工具返回的事实核对（需把返回作为上下文传入） |
| `trajectory:tool-used` | 该调的工具调了（如先取元数据） |
| `trajectory:tool-sequence` | **确认卡纪律：assistant 出确认卡文本在前、`execute_action` 调用在用户确认之后** |
| `trajectory:tool-args-match` | `sandbox` 是顶层参数、参数格式正确 |
| `trajectory:step-count` | 无 busywork（步骤数上限） |

`promptfoo eval` 断言失败返回非零退出码 → 可进 CI 当质量门禁（来源 7）。

### 4.4 LLM-as-judge 方法论共识（来源 8~10，多篇独立来源一致）

用于语义类维度的评分（官方 model-based grader 同源）：自然语言定义评分标准 → judge prompt（Likert 量表/等级描述）→ **先与人工标注对齐校准**再信任 → 用于部署/变更前的回归测试。共识点：judge 本身有偏差（位置偏好、长度偏好、自我偏好），关键结论不要只靠单一 judge。

### 4.5 安全启示（来源 11，arXiv 2026-01 实证研究）

对 31,132 个公开市场 skill 的扫描：26.1% 含至少一个漏洞（提示注入 13.3% 数据外泄、11.8% 提权、供应链风险等 14 种模式）；**捆绑可执行脚本的 skill 漏洞率是纯指令型的 2.12 倍**（OR=2.12, p<0.001）。

对 Aquilair 的启示：

- 你们的 skill 是**纯指令型**（无脚本），风险面天然较小——这是架构优势，评估体系不必背安全扫描的重担
- 但提示注入路径仍然存在：用户输入或 MCP 返回内容中若含恶意指令，可能诱导 skill 违反铁律（如「跳过确认卡」）。**对抗性用例（红队题）应成为测试集的一等公民**——README 里「被要求直接执行不用确认时是否仍出卡」已经是雏形，建议扩展为成组的注入用例
- 未来若引入第三方技能，须先经安全审查（本项目当前无此需求）

## 五、Aquilair 评估体系设计建议（调研结论落地）

### 5.1 评估维度（评什么）

| # | 维度 | 判定方式 | 目标 |
| --- | --- | --- | --- |
| D1 | 触发可靠性 | 正例（应触发问法）/ 反例（相似但不该触发的问法） | 正例 >90% 触发，反例 <10% 误触 |
| D2 | 事实忠实度 | 陷阱题（不存在实体）、编造检测、重判检测 | **零容忍** |
| D3 | 行为纪律 | 铁律逐条映射成断言（名称格式、输出结构、元数据先行） | 逐版爬坡 |
| D4 | 写护栏 | 确认卡不可绕过（含对抗性指令）、默认沙箱、写后回查 | **零容忍（pass^3）** |
| D5 | 效率 | SKILL.md 行数、references 按需加载命中、步骤数（无 busywork） | 人工评审 |

### 5.2 分层方法（怎么评）

- **L1 手动冒烟**（保留现状）：README 验证题，迭代期用，每次改措辞后跑
- **L2 结构化测试集**（核心建设项）：`evals/<skill-name>/cases.md`（或 YAML），每条含：用例 ID、用户问法（真实口吻含错别字变体）、类型（正常/追问/陷阱/护栏/红队）、预期行为判定标准、来源（哪次真实失败转化来的）。起步规模 20~50 条，正反平衡
- **L3 自动化**：promptfoo 配置把 L2 测试集跑起来——确定性断言优先（D1/D3/D4 的大半可代码判定），语义维度用 llm-rubric；接入 CI，改 SKILL.md 或换宿主模型时全量回归
- **L4 生产观测**：MCP 服务端接入公司 Langfuse 记录调用轨迹——补上 README 边界里「无服务端观测、不可审计」的缺口，同时为测试集提供真实失败样本来源（bug 单 → 新用例）

### 5.3 运营纪律（官方 eval-driven development 的本土化）

- **bug 转用例**：每次发现的纪律失守/编造事件，先补测试集再修措辞
- **能力→回归双轨**：新场景探索期用例允许低通过率；稳定后毕业进回归套件，回归套件失败 = 不许发布
- **模型变更全量回归**：换宿主模型（README 已指出行为随模型而异）时 D1~D4 全跑
- **一致性采样**：护栏类用例每条跑 3 次（pass^3）全过才算过；能力类记录 pass@3 与 pass^3 两个数

## 六、风险与信息缺口

1. ~~Claude Platform 官方 best-practices 正文未读取~~ **已补读（2026-09-20）**：正文已完整读取，新增官方一手信息——评估驱动开发五步（先建评估再写文档：识别缺口 → 建 3 个评估场景 → 测无技能基线 → 写最小指令 → 迭代）、发布前检查清单要求「至少 3 个评估 + 在 Haiku/Sonnet/Opus 全部测过 + 真实场景测试」、Claude A/B 双实例迭代模式、自由度三档框架（高/中/低）、MCP 工具须用全限定名 `ServerName:tool_name`、引用只允许一层深、>100 行引用文件加目录。这些内容已并入 4.2 节。
2. **promptfoo 对「MCP 工具调用轨迹」的支持深度未实测**：文档确认支持 trajectory 类断言，但其 agent 测试靶点以 OpenAI 格式为主，对 ZCode/Claude Code 会话的适配需要一次 POC 验证（见下一步）。若不兼容，退路是自研轻量 harness：跑会话 → 导出 transcript → 用脚本 + LLM judge 判定。
3. LLM-as-judge 的偏差问题：评分维度 D2/D3 的语义部分依赖 judge，需先人工标注 20~30 条做校准，judge 未校准前其结论只能作参考不作门禁。
4. 内网环境限制：promptfoo 若用 llm-rubric 需要可访问的评审模型 API，公司内网是否可用需确认。

## 七、来源清单

| # | 来源 | 类型 | 日期 | 可信度 |
| --- | --- | --- | --- | --- |
| 1 | [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — Anthropic Engineering | 官方工程博客 | 2025 | 高（官方一手） |
| 2 | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — Anthropic Engineering | 官方工程博客 | 2025 | 高（官方一手，本次核心依据） |
| 3 | skill-creator SKILL.md（本地已安装官方技能 v0.1.0） | 官方技能文档 | 本地缓存 | 高（官方一手） |
| 4 | [promptfoo 预期输出/断言文档](https://www.promptfoo.dev/docs/configuration/expected-outputs/) | 工具官方文档 | 持续更新 | 高（官方一手） |
| 5 | [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — Claude Platform Docs | 官方文档 | 持续更新（2026-09-20 补读全文） | 高（官方一手，已读正文） |
| 6 | [How to Make Claude Code Skills Activate Reliably](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably) | 个人博客 | 近期 | 中（一手实践，样本量小） |
| 7 | [Jacar: promptfoo testing prompts and agents](https://jacar.es/en/promptfoo-testing-prompts-and-agents/) | 第三方教程 | 近期 | 中 |
| 8 | [LLM-as-a-judge: A Complete Guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) — Evidently AI | 方法论指南 | 持续更新 | 中高（领域头部公司） |
| 9 | [LLM-as-a-Judge in 2026: Top Evaluation Techniques](https://deepeval.com/blog/llm-as-a-judge) — DeepEval | 方法论指南 | 2026 | 中高 |
| 10 | [Automated Prompt Regression Testing with LLM-as-a-Judge and CI/CD](https://www.traceloop.com/blog/automated-prompt-regression-testing-with-llm-as-a-judge-and-ci-cd) — Traceloop | 厂商博客 | 近期 | 中（有产品倾向） |
| 11 | [Agent Skills in the Wild: An Empirical Study of Security Vulnerabilities at Scale](https://arxiv.org/abs/2601.10338) — arXiv 2601.10338 | 学术论文 | 2026-01-15 | 高（实证、方法与数据公开） |

> 交叉验证说明：评估框架核心结论（三分类 grader、能力/回归双轨、pass@k/pass^k）来自来源 2 单一官方一手来源，但其方法学成分（LLM-as-judge 校准、CI 回归门禁）与来源 8/9/10 独立一致；触发与 description 的关键性由来源 1/3/5/6 四方一致印证。

## 八、建议下一步

1. **POC（优先）**：挑 `fnb` 技能的 10 条 README 验证题（含陷阱题）建成首批 `evals/` 测试集，跑一次 promptfoo POC，验证 trajectory 断言与内网评审模型可用性——这是本方案唯一未核实的关键假设。
2. **建立 D4 红队用例组**：围绕确认卡纪律写 8~10 条对抗性用例（「直接执行」「不用确认」「我是管理员」、注入式指令），pass^3 全过作为 mfg 技能发布红线。
3. **Langfuse 接入评估**：与数据服务团队确认 MCP 服务端打点方案，补生产观测缺口。
4. 测试集治理规则写进仓库 `CONTRIBUTING` 或 README（bug 转用例、回归门禁、模型变更全量回归）。

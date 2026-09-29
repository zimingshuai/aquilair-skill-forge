# wiki 域术语表（glossary）

> 本域是知识库技能自身的设计源域，术语即方法词汇。来源：Karpathy gist 正文与评论区、nashsu/balukosuri 实现、Aquilair 落地实践（出处逐条标注）。

| 术语 | 含义 | 同义词/英文 | 出处 |
| --- | --- | --- | --- |
| 摄取 | 读源一次、编译进知识库的动作 | ingest / compile | raw/llm-wiki.md Operations 节 |
| 编译而非检索 | 知识一次摄取持久积累，不每次从原始文档重推 | compile, not retrieve | raw/llm-wiki.md The core idea |
| 原始层 | 业务方文档原样落位区，只读不改 | raw / raw sources | raw/llm-wiki.md Architecture |
| 编译层 | LLM 生成维护的知识页总称 | wiki 层 | raw/llm-wiki.md Architecture |
| schema | 告诉 LLM 知识库怎么运作的配置文档（我们的形态=SKILL.md+剧本） | 操作手册 | raw/llm-wiki.md Architecture |
| 溯源坐标 | 出处标注的「文件路径+小节」写法，两边结构都成立 | citation / [@path] | Aquilair 实践（frankchu91 评论区同思路） |
| 候审 | 写时矛盾/过时条目的待人工裁定状态 | pending review | Aquilair 实践 |
| 写时矛盾处理 | 捕获时当场标记矛盾，不留到 lint | handle contradictions at write time | crajah 评论区 |
| 无来源即发现 | 没有出处标注的页面直接算 lint 发现，代码可判定 | no-source = lint finding | frankchu91 评论区 |
| 教训放必读处 | 工具级坑写进 SKILL.md 模型必读区，不埋按需加载深处 | LESSON: in tool description | orcosto-lab 评论区 |
| 文档注入防御 | 源文档内容视为数据不是指令，指令性文字不执行 | untrusted input | ShootJackal(Cortex) 评论区 |
| audit 模式 | 用无先验干净会话对知识库做一致性审查，避免作者盲区 | clean-room audit | frankchu91 评论区 |
| 事件驱动巡检 | 摄取计数/服务变更触发 lint，而非日历驱动 | event-driven lint | 评论区多家共识 |
| 探索复利 | 好答案归档回知识库成为新页 | file answers back | raw/llm-wiki.md Query 节 |
| 记账瓶颈 | 知识库维护的瓶颈不是阅读或思考，是记账（更新引用/保持一致/标注矛盾）；LLM 不厌烦不遗忘，维护成本趋近零 | bookkeeping bottleneck | raw/llm-wiki-methodology-by-nashsu.png 核心洞察框（2026-09-29 读图） |
| 单源触及面 | 一次 ingest 可更新 10~15 个 wiki 页面——编译是有涟漪的，不是单文件操作 | touch 10-15 pages | raw/llm-wiki-methodology-by-nashsu.png（2026-09-29 读图） |

# 插件拆分规格：业务锻造师 × 智能应用中枢

> 日期：2026-10-26 ｜ 状态：方案定稿，待实施
> 决策人：用户（拆分方向拍板）+ 本规格（归属映射与实施细节）
> 前置：v0.2.0 统一 MCP 网关迁移版已发布闭环（origin/main 097ca9f），两动作不叠版本。

## 一、动机（为什么拆）

当前 `aquilair-business-skills` 单包 7 技能 + agent + MCP + hooks，受众混装：

1. **受众分离**：终端业务用户（多数）不需要技能工厂元技能；技能开发者（少数）不需要业务技能长 description 常驻。拆后双方系统提示各减一半噪音，路由误触发面收窄。
2. **安全边界**：锻造师带写文件/建技能能力，不应默认分发给终端用户；对外分发可只放应用中枢。
3. **版本节奏**：业务技能高频迭代（措辞回归/数据口径），元技能低频稳定——分版本线各自 bump。
4. **产线显式化**：锻造师吃 MCP + 业务知识产出技能，应用中枢吃技能 + MCP 产出业务答案——「骨架归工厂、数据随消费方」原则的插件层延伸。

## 二、归属映射（终版）

| 资产 | 去向 | 说明 |
| --- | --- | --- |
| fnb-inventory-analysis、mfg-transfer-allocation | hub | 纯终端业务 |
| aquilair-data-delivery | hub | 交付规范，业务回答时生效 |
| aquilair-skill-router + hooks/（session-start 路由注入） | hub | 引导业务入口 |
| agents/aquilair-supply-chain-advisor + agents/README | hub | 中央业务顾问 + 六宿主接入指南 |
| .mcp.json（aquilair-mcp 网关） | hub | 业务数据消费方；工厂验收走会话内宿主 MCP |
| aquilair-skill-authoring、aquilair-eval-diagnostics | forge | 六步流水线 + 质量门 |
| aquilair-knowledge-wiki（技能本体） | forge | ingest/再摄取是流水线一环 |
| aquilair-knowledge/（知识库工作区） | **仓库根共享** | sources 全量随包分发机制不变；wiki 在 forge 编译，hub 技能引用产物 |
| evals/（框架 + cases）、tools/、tests/ | **仓库根共享** | 单仓库方案下 evals 归属难题消解（见三） |
| avatars/、.codebuddy-plugin/（WorkBuddy 线） | 仓库根，清单改指 hub 技能 | WorkBuddy 是终端用户宿主，只随 hub |

## 三、仓库策略：单仓库、双插件目录（关键决策）

**不拆仓库**，marketplace 单源列两个插件：

```
aquilair-skills/
├── .claude-plugin/marketplace.json      # plugins 数组列两个插件，source 指子目录
├── plugins/
│   ├── skill-forge/                     # Aquilair 业务锻造师
│   │   ├── .claude-plugin/plugin.json   # 三宿主清单（claude/zcode/codex 同源派生）
│   │   ├── .zcode-plugin/plugin.json
│   │   ├── .codex-plugin/plugin.json
│   │   └── skills/（authoring、eval-diagnostics、knowledge-wiki）
│   └── business-hub/                    # Aquilair 智能应用中枢
│       ├── .claude-plugin/plugin.json
│       ├── .zcode-plugin/plugin.json
│       ├── .codex-plugin/plugin.json
│       ├── .mcp.json                    # aquilair-mcp 网关（全仓库唯一地址源不变）
│       ├── hooks/                       # session-start 路由注入（仅 hub）
│       ├── agents/                      # supply-chain-advisor + 六宿主指南
│       └── skills/（fnb、mfg、data-delivery、skill-router）
├── evals/  tools/  tests/  aquilair-knowledge/   # 开发资产留根，不进任何插件包
└── README.md                            # 重写：按受众分安装指引
```

理由：
- **evals 跨仓回归难题消解**：框架与 cases 物理不动，「改 hub 技能 → 根目录跑全量回归」的既有铁律流程零变化；双仓库则须重定义跨仓规程。
- **三宿主清单成本不翻倍**：一个 marketplace.json 列两插件，市场源地址不变，用户只多一步「装哪个」。
- **git 历史连续**：git mv 保留技能文件追溯。
- **退路**：目录已分家，未来要拆物理仓库，整体搬 `plugins/<name>` 即可。

风险点（实施后必测）：ZCode/Codex 对 marketplace plugin `source` 指向**子目录**的兼容性（历史实测过 `source: "./"` 根形式，子目录理论同构但未实测）——本地市场源实测两插件分别可装。

## 四、版本线

| 插件 | 版本起点 | 依据 |
| --- | --- | --- |
| aquilair-business-hub | **0.3.0** | 0.2.0 直系延续（内容 = 0.2.0 的业务侧 + 目录迁移） |
| aquilair-skill-forge | **0.1.0** | 新线起步（内容 = 既有元技能，无功能变更） |
| WorkBuddy 线（.codebuddy-plugin） | v1.2.x 续 | 只随 hub，清单 skills 指针改 hub 目录 |

## 五、实施步骤

1. `git mv` 建目录搬技能（保留历史）：根 `skills/` 四业务技能 → `plugins/business-hub/skills/`，三元技能 → `plugins/skill-forge/skills/`；hooks、agents、.mcp.json → business-hub。
2. 清单拆写：marketplace.json 双插件条目（含 i18n 展示名）；各插件三宿主 plugin.json（skills/mcpServers/hooks 指针相对插件根）；.codebuddy-plugin 指针改 hub。
3. 引用同步（authoring 红线：grep 全仓同款措辞）：
   - skill-router 路由表：拆后若只装 hub，对 forge 技能的引用改为「工厂侧指引」（提 aquilair-skill-forge 插件名而非直接技能名）；
   - hooks/bootstrap.md 路由引导同上分家；
   - authoring 六步流水线内对 wiki 的引用（同包，路径相对引用检查）；
   - README/各 SKILL.md 中仓库相对路径（`aquilair-knowledge/` 坐标不变，`skills/...` 路径全量 grep 更新）。
4. 工具适配：tests/run_infra_tests.py 扫描 `plugins/*/skills/`；tools/pack_skill.py 的 knowledge_root 推断改为「向上定位含 aquilair-knowledge 的仓库根」。
5. README 重写：双插件介绍、按受众选装、更新流程（市场源刷新 → 各插件详情更新）。

## 六、验证门禁（全部通过才算拆分完成）

1. `python tests/run_infra_tests.py`：两插件全部技能 a-i 断言全绿（含知识库随包 19 条）。
2. `python -m pre_commit run --all-files`：cases 校验绿。
3. 措辞回归：fnb/mfg 共享条款回放（evals 既有用例集，路径不动零适配）。
4. grep 检查：仓库内无指向旧 `skills/` 根路径的死链；无跨包技能直引未加插件名限定。
5. 本地市场源实测：ZCode 添加本仓库市场 → 两插件分别可装、hub 装后 MCP + hook 生效（此步需用户在 UI 侧配合，列为发布前实测项）。

## 七、风险与对策

- **宿主不认子目录 source** → 对策：marketplace.json 兼容写法实测；不行则退回「根清单声明两个插件、source 均指向根但 skills 指针各取所需」的变体（skills 数组枚举而非目录指针——plugin.json 的 skills 指针支持目录，若不支持多目录则该变体不可行，实测定）。
- **已装 0.2.0 用户迁移断裂** → 对策：README 迁移段说明（卸旧装 hub；要工厂再装 forge）；marketplace 版本递增走各插件详情更新。
- **拆分当版功能零变更被回归噪声掩盖** → 对策：拆分提交纯搬运（git mv + 清单改写），任何措辞/逻辑修正独立提交，不混搬。

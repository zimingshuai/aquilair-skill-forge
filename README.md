# Aquilair 业务锻造师（aquilair-skill-forge）

> 天鹰智能中枢（Aquilair）的**技能工厂插件仓库**：六步流水线产出新业务技能、评估失败自诊断、域知识库摄取编译。**产出以跨仓 PR 进入** [aquilair-business-hub 仓库](https://code.elitescloud.com/el-aquilair/business-hub)（智能应用中枢，终端业务技能的分发插件）——本仓库是产线，那边是产品。

## 产线关系（一张图）

```
新业务域（MCP 服务 + 业务知识）
        │
        ▼
┌─ 本仓库（业务锻造师）──────────────────┐
│  knowledge-wiki 摄取编译域知识库（主本）   │
│  skill-authoring 六步流水线造技能         │
│  skill-eval-generator 生成用例草稿        │
│  首次验收评估（evals 能力层，本仓跑）      │──通过──▶ 跨仓 PR：技能 + 用例
│  eval-diagnostics FAIL 归因（迭代）       │
└────────────────────────────────────┘              │
        知识更新后 sync_knowledge.py 推快照 ──────────▶ hub 仓库（cases 随技能同 PR）
                                                     ▼
                                          hub 版本递增 → 市场源刷新 → 终端用户更新
```

## 包内容

### 元技能（随 skill-forge 插件分发，仅供技能开发者）

- 🏗️ `aquilair-skill-authoring`：工厂主技能——新业务领域携带 MCP 服务 + 业务知识，经六步流水线（立项→实测→划界→模板→接线→验收）产出业务技能并评估迭代
- 🔍 `aquilair-eval-diagnostics`：评估失败自诊断——读评估报告与 transcripts 轨迹，按四类归因（A 文档缺陷 / B 模型未遵守 / C 数据问题 / D 断言口径）给带证据的反哺建议
- 📚 `aquilair-knowledge-wiki`：域知识库——喂文档 + MCP 地址自动摄取编译知识库（主本在本仓 `aquilair-knowledge/`），支撑溯源问答与再摄取迭代

### 业务技能（不在本仓库）

终端业务技能（fnb 库存诊断 / mfg 多工厂调拨 / data-delivery 数据交付 / skill-router 路由）在 aquilair-business-hub 仓库分发；接线指引见 authoring 第五步。

## 快速开始

### 安装插件（技能开发者）

| 宿主 | 安装 |
| --- | --- |
| Claude Code | `/plugin marketplace add <本仓库地址>` → 安装 `aquilair-skill-forge` |
| ZCode | 插件市场 → 添加市场源（本仓库根目录）→「个人 → aquilair-forge」安装 |
| Codex | `codex plugin marketplace add <仓库地址>` → `codex plugin add aquilair-skill-forge@aquilair-forge` |

本插件不绑 MCP、无 hook（评估/摄取所需的 MCP 连接走宿主会话或各技能自带寻址）。

### 造一个新技能（六步流水线）

加载 `aquilair-skill-authoring` 技能后按其流水线执行；可从任意阶段进入（新域素材 / SKILL.md 草稿 / 评估 FAIL 报告均有对应入口）。关键纪律：

- **铁律只能来自实测踩坑**（第 2 步真实调用 MCP 记事实卡片，文档不记录参数坑）；
- **首次验收不通过不交付**（第 6 步四类题型，evals 能力层主本在本仓 `evals/`）；
- **交付 = 跨仓 PR**：技能 + 用例同一 PR 进**目标分发仓库**（官方产线默认本组织的 hub 仓库；外部团队使用本工厂时即你自己的业务技能插件仓库——第 5 步接线五处的泛化指引见 authoring SKILL.md）。

## 知识库与快照同步

`aquilair-knowledge/` 是域知识库**主本**（sources/ 源文档溯源区 + research/ 调研与决策记录）：摄取、编译、再摄取都在本仓进行。hub 技能 zip 打包需要 `sources/` 随包——主本知识更新后执行：

```
python tools/sync_knowledge.py <hub仓库路径>            # 镜像同步快照（--dry-run 预览）
```

同步后在 hub 仓库提交快照（message 标注来源 forge commit）。hub 侧快照区不接受直接编辑（见其 `aquilair-knowledge/SNAPSHOT.md`）。

## 评估体系（能力层）

用例规范（六类题型）、运行协议（pass^3 采样）、回归纪律（零容忍红线）与 promptfoo L3 框架的主本在本仓 [`evals/README.md`](evals/README.md)；用例数据层（cases + runs）随被测技能在 hub 仓库，改技能措辞后在 hub 仓跑全量回归。当前基线：3 技能 37/37 全部 `mature: true`。

## 开发质量门禁

- **pre-commit**：`pip install pre-commit && pre-commit install`（用例格式校验；hub 仓挂同款 vendored 副本）；
- **lint 巡检**：`python tools/lint_skills.py`（C1~C12 机检 + 仓库级一致性；业务技能侧的 C6/C7/C12 在 hub 仓跑）；
- **基础设施测试**：`python tests/run_infra_tests.py`（发布前，断言插件结构与分发 zip 规范）；
- **打包验证**：`python tools/pack_skill.py <技能名>`（SKILL.md 位于 zip 根、知识库随包）。

## 目录结构

```
aquilair-skill-forge/
├── .claude-plugin/            # 市场清单（marketplace.json，市场名 aquilair-forge）
├── plugins/skill-forge/       # 插件本体
│   ├── .claude-plugin/ .zcode-plugin/ .codex-plugin/   # 三宿主插件清单
│   └── skills/                # 3 元技能（authoring / eval-diagnostics / knowledge-wiki）
├── evals/                     # 评估能力层：规范主本 + promptfoo 框架（数据层在 hub 仓）
├── aquilair-knowledge/        # 知识库主本：sources/ 溯源区 + research/ 调研决策
├── tools/                     # pack_skill 打包 / lint_skills 巡检 / skill-eval-generator 用例生成 / sync_knowledge 快照同步
└── tests/                     # 插件基础设施测试
```

技能格式符合 [Agent Skills 开放标准](https://agentskills.io)。

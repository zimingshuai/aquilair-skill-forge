# WorkBuddy 宿主适配（aquilair-skill-forge）

> 本文件记录本仓库作为 **WorkBuddy 插件**接入的适配层：改了什么、怎么装、怎么更新、怎么自检。
> 上游多宿主清单（`.claude-plugin` / `.zcode-plugin` / `.codex-plugin`）一字未动，适配是**增量**的。

## 一、适配层做了什么（2026-11-02 方案 A 定稿：插件自包含化）

| 项 | 落点 | 作用 |
| --- | --- | --- |
| 市场清单 | `.codebuddy-plugin/marketplace.json` | 市场名 `aquilair-forge`，插件源指向 `./plugins/skill-forge`；WorkBuddy「添加市场源」认这个目录 |
| 插件清单 | `plugins/skill-forge/.codebuddy-plugin/plugin.json` | `skills: ./skills`（目录扫描，新增技能零改动）+ `agents` 显式登记 |
| 运行时资产副本 | `plugins/skill-forge/tools/`（pack / lint / skill-eval-generator）+ `plugins/skill-forge/evals/README.md` | **插件自包含**：安装态（宿主缓存里只有插件目录）工具与评估协议直接可用——由 `tools/sync_plugin_assets.py` 从仓库根同步，`--check` 防漂移 |
| agent 扩展键 | `agents/aquilair-skill-smith.md` frontmatter | 补 `displayName` / `profession`（WorkBuddy Expert 扩展键）；Claude Code 的 `name` / `description` 原样保留，双宿主共存 |
| 适配脚本 | `tools/adapt_workbuddy.py` | 幂等生成清单与 agent 扩展键（**不再注入 SKILL.md**——早期版本的仓库根锚点机制已删除，机器绝对路径不进版本库、宿主特定内容不污染宿主无关源文件） |

**为什么插件清单不在仓库根**：`tools/lint_skills.py` 的 C12 会把仓库根 `.codebuddy-plugin/plugin.json` 按
business-hub 技能集双向校验，而 forge 元技能本就不进 CodeBuddy 清单——清单下沉到插件目录，lint 保持全绿。

## 二、安装（本机已装）

```bash
python tools/sync_plugin_assets.py      # 1. 同步运行时资产副本进插件目录（必跑，幂等）
python tools/adapt_workbuddy.py         # 2. 生成 WorkBuddy 清单与 agent 扩展键（必跑，幂等）
# 3. WorkBuddy 插件市场 → 添加市场源 → 选本仓库根目录 → 安装「Aquilair 业务锻造师」
```

装好后得到：3 个元技能（`aquilair-skill-authoring` / `aquilair-eval-diagnostics` / `aquilair-knowledge-wiki`）
+ agent 人设「业务锻造师·天工」（`aquilair-skill-smith`）+ 插件根 `tools/`（打包 / 巡检 / 用例生成器）
+ `evals/README.md`（评估运行协议）。插件不绑 MCP，评估与摄取的数据连接走宿主会话配置。

## 三、更新与自检

```bash
git pull                                  # 上游技能或工具链更新
python tools/sync_plugin_assets.py        # 重新同步运行时资产副本
python tools/adapt_workbuddy.py           # 重新对齐清单与 agent 键（版本号跟 .zcode-plugin 同源）
python tools/sync_plugin_assets.py --check  # 只校验：副本漂移退出码 1
python tools/adapt_workbuddy.py --check   # 只校验：清单漂移退出码 1
python tools/lint_skills.py               # 巡检必须仍为 0 ERROR（仓库根跑；插件根跑同样支持）
```

宿主侧的插件副本在 `%USERPROFILE%\.workbuddy\plugins\cache\aquilair-forge\aquilair-skill-forge\<版本>\`，
是安装时点的快照；脚本改动后在插件市场里更新该插件（或删掉缓存目录重装）才会生效。

## 四、已知限制

- **CLI 的 `plugin` 子命令在桌面端运行期间不可用**：它会尝试绑定桌面端已占用的本地端口（本机为 2829），
  报 `EADDRINUSE`。插件安装/更新请走插件市场界面；命令行侧只用 `adapt_workbuddy.py` / `sync_plugin_assets.py`
  与 `lint_skills.py` 这套工厂工具链。
- **知识库主本不随插件**：`aquilair-knowledge/` 是内容资产（资产分界，见分发口径），仅随整仓/工具链级
  安装存在；插件级安装的 knowledge-wiki 只提供摄取剧本指导，主本位置须向开发者确认。换机器时知识库随仓库搬。
- **插件态工具即副本**：`plugins/skill-forge/tools/` 是分发副本，权威源在仓库根 `tools/`——改工具先改源，
  再跑 `sync_plugin_assets.py`；发版门禁的 `--check` 会拦截「源改了副本没同步」。

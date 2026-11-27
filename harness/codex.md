# Codex Windows 本地配置迁移手册

> 快照日期：2026-11-27（Asia/Shanghai）
> 源环境：Windows 11 Pro `10.0.26300`、Codex Desktop `26.1120.6357.0`、内置 Codex CLI `0.167.2`
> 目标环境：另一台 Windows 电脑  
> 迁移范围：Codex 配置、模型提供商、UI、字体、MCP、插件、技能、AGENTS 规则和必要依赖  
> 不迁移：登录凭据、API token、会话、记忆、历史记录、日志、索引和其他私有状态
>
> 本次更新同步插件、技能、Desktop/Runtime 版本及非模型提供商设置。模型提供商相关配置沿用 2026-11-19 记录，未在本次核对。

本文档是一个快照，不是“把整个 `.codex` 目录原样复制过去”的教程。Codex Desktop、插件缓存、CUA runtime 和 MCP 路径包含版本哈希、用户目录和命名管道，必须让新电脑重新生成；用户自己的技能和规则则需要单独迁移。

---

## 0. 一页式迁移清单

推荐顺序：

1. 在新电脑安装并至少启动一次 Codex Desktop，完成账号登录。
2. 在旧电脑运行“第 2 节”的导出命令，生成不包含密钥的迁移资源包。
3. 在新电脑运行“第 3 节”的恢复命令，复制技能、模型目录、字体和规则。
4. 配置 `config.toml`：从“第 4.3 节”的便携模板开始，不要直接覆盖新电脑的自动生成配置。
5. 用 Codex Plugin Manager 或 `codex plugin add` 重新安装 13 个插件。
6. 用 ARS 的 GitHub marketplace 重新安装 `ars-codex`；Windows 更新异常时再使用本地 marketplace 备用方案。
7. 安装 Maple Mono NF CN 字体，重启 Codex Desktop，检查主题和字体。
8. 重新添加本地项目；如使用远程连接，再单独添加，不要复制旧机器的凭据或数据库。
9. 运行 `codex doctor`、`codex plugin list` 和 `codex mcp list --json` 做验收。

最小验收标准：

- `codex plugin list` 显示 13 个已安装且启用的插件：7 个 `openai-bundled`、5 个 `openai-primary-runtime`、1 个 `ars-codex`。
- `$CODEX_HOME/skills` 下有 31 个用户技能目录，另有自动维护的 `.system` 目录。
- `$HOME/.agents/skills` 下有 `answer-me-with-html`，且 `.skill-lock.json` 存在。
- 3 个 MCP 记录可见：`node_repl`、`cua_repl`、`codex_app`；当前 `node_repl`、`cua_repl` 启用，`codex_app` 在 CLI 视角为禁用。实际路径应来自新电脑。
- 模型目录中有 `deepseek-v4.1-flash` 和 `qwen4-max`。
- 新电脑打开新对话后，`codex doctor` 不再报告配置语法错误；安全提示和可选依赖缺失可以按需处理。

---

## 1. 当前环境快照

| 项目 | 当前值 |
|---|---|
| 操作系统 | Windows 11 Pro `10.0.26300`，64 位，中文系统 |
| Codex Desktop | `26.1120.6357.0` |
| Codex CLI | `0.167.2` |
| Codex Primary Runtime | `26.1123.915.0` |
| Codex Home | `%USERPROFILE%\.codex` |
| 默认 shell | PowerShell |
| 默认模型提供商 | 自定义 `custom` provider，名称为 `opencode_go` |
| 默认模型 | `deepseek-v4.1-flash`，reasoning `high` |
| 模型目录 | `%USERPROFILE%\.codex\cc-switch-model-catalog.json` |
| 子 agent 默认模型 | `deepseek-v4.1-flash` |
| 已启用插件 | 13 个 |
| 用户技能 | 31 个目录（包含 `nature-shared`、PaperSpine 六项、`impeccable` 和 `taste-skill`） |
| 系统技能 | 6 个，位于 `.codex\skills\.system` |
| Hooks | `%CODEX_HOME%\hooks.json` 含 `PostToolUse` 和 `Stop` 配置；Codex 是否加载尚未验证 |
| 已配置 MCP 记录 | `node_repl`、`cua_repl` 启用；`codex_app` 在 CLI 视角禁用 |
| Desktop 语言 | `zh-CN` |
| Desktop 主题 | 深色 Lobster，accent 为 `#ff5c5c` |
| UI/代码字体 | Maple Mono NF CN |

### 1.1 快照的边界

- 第 1 节中的模型提供商、默认模型和子 agent 模型值沿用 2026-11-19 记录，本次未核对；请勿把它们当作当前模型设置。
- 插件版本和 Codex Desktop 版本会随更新变化。本文档记录的是当前机器上的版本，不是要求新电脑固定使用这些版本。
- 新电脑的用户名、Codex runtime 哈希、命名管道 ID 和 CLI 路径通常不同。
- `openai-bundled`、`openai-primary-runtime`、CUA runtime 和插件缓存属于 Codex Desktop 管理的组件，不应从旧电脑复制。
- 视觉设置可以迁移，但必须满足字体依赖；字体不可用时 Codex 会回退到系统可用字体。
- 当前配置把 sandbox 设为 `danger-full-access`。这能复现当前工作方式，但不应被误认为安全默认值；新电脑应在知情后选择是否保留。

### 1.2 明确不迁移的内容

不要把下面这些内容放进迁移包，也不要提交到仓库：

- `%USERPROFILE%\.codex\auth.json` 及任何登录缓存。
- 真实 API token、OAuth token、Cookie、SSH 私钥或密码。
- `sessions`、`memories_v2`、`memories_1.sqlite`、`thread_history_1.sqlite`、`state_5.sqlite`、`logs_2.sqlite`。
- `.codex-global-state.json`，其中包含项目、线程、远程连接和 UI 状态等本地私有元数据。
- `plugins/cache`、`.tmp`、`.sandbox*`、`browser`、`cache`、日志、索引、队列和线程数据。
- CC Switch 的 `cc-switch.db`、`codex-login-stash.json` 或其中保存的 provider 凭据。
- `%USERPROFILE%\.codex\hooks.json` 当前含 Impeccable hook 配置，但 Codex 接线未验证；不要仅凭复制该文件就认为 hook 已启用。
- 任何个人对话、工作区文件或附件。

---

## 2. 旧电脑：生成迁移资源包

下面的命令只导出可迁移的用户资产，不复制 `config.toml`，因此不会把明文 token 放进压缩包。请在旧电脑的 PowerShell 中运行。

```powershell
$ErrorActionPreference = 'Stop'

$codexHome = Join-Path $env:USERPROFILE '.codex'
$agentsHome = Join-Path $env:USERPROFILE '.agents'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$bundleRoot = Join-Path ([Environment]::GetFolderPath('Desktop')) "codex-migration-$stamp"

New-Item -ItemType Directory -Path $bundleRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundleRoot 'codex-skills') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundleRoot 'agents-skills') -Force | Out-Null

# 模型目录：deepseek-v4.1-flash / qwen4-max
Copy-Item -LiteralPath (Join-Path $codexHome 'cc-switch-model-catalog.json') `
  -Destination $bundleRoot -Force

# 用户技能，不包含 Codex 自动维护的 .system 目录
Get-ChildItem -LiteralPath (Join-Path $codexHome 'skills') -Directory |
  Where-Object { $_.Name -ne '.system' } |
  ForEach-Object {
    Copy-Item -LiteralPath $_.FullName `
      -Destination (Join-Path $bundleRoot 'codex-skills') -Recurse -Force
  }

# Codex 的 .agents 技能注册信息和 answer-me-with-html
$agentsSkill = Join-Path $agentsHome 'skills\answer-me-with-html'
if (Test-Path -LiteralPath $agentsSkill) {
  Copy-Item -LiteralPath $agentsSkill `
    -Destination (Join-Path $bundleRoot 'agents-skills') -Recurse -Force
}
$skillLock = Join-Path $agentsHome '.skill-lock.json'
if (Test-Path -LiteralPath $skillLock) {
  Copy-Item -LiteralPath $skillLock -Destination $bundleRoot -Force
}

# 全局 AGENTS 规则
$globalAgentsFile = Join-Path $codexHome 'AGENTS.md'
if (Test-Path -LiteralPath $globalAgentsFile) {
  Copy-Item -LiteralPath $globalAgentsFile -Destination (Join-Path $bundleRoot 'AGENTS.global.md') -Force
}

# 当前项目的父级 AGENTS 规则
$agentsFile = 'Q:\workspace\2026Spring2Winter\AGENTS.md'
if (Test-Path -LiteralPath $agentsFile) {
  Copy-Item -LiteralPath $agentsFile -Destination $bundleRoot -Force
}

# 迁移手册本身
$handbook = 'Q:\workspace\2026Spring2Winter\harness\codex.md'
if (Test-Path -LiteralPath $handbook) {
  Copy-Item -LiteralPath $handbook -Destination $bundleRoot -Force
}

# 可选：字体。字体很大，不需要时跳过。
$fontSource = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
$fontDest = Join-Path $bundleRoot 'fonts'
New-Item -ItemType Directory -Path $fontDest -Force | Out-Null
Get-ChildItem -LiteralPath $fontSource -Filter 'MapleMono-NF-CN-*.ttf' -ErrorAction SilentlyContinue |
  Copy-Item -Destination $fontDest -Force

# 可选：ARS 的本地 marketplace 备份，用于 Windows Git marketplace 更新异常时的回退。
$arsSource = Join-Path $codexHome 'local-marketplaces\academic-research-skills-codex'
if (Test-Path -LiteralPath $arsSource) {
  Copy-Item -LiteralPath $arsSource `
    -Destination (Join-Path $bundleRoot 'academic-research-skills-codex') -Recurse -Force
}

$zipPath = "$bundleRoot.zip"
Compress-Archive -Path (Join-Path $bundleRoot '*') -DestinationPath $zipPath -Force
Write-Host "迁移资源包已生成：$zipPath"
```

检查点：

- `codex-skills` 中应有 31 个目录。
- `agents-skills\answer-me-with-html` 和 `.skill-lock.json` 应存在。
- `AGENTS.global.md` 和工作区 `AGENTS.md` 应存在。
- `cc-switch-model-catalog.json` 应存在。
- 压缩包中不应有 `config.toml`、`auth.json`、`.codex-global-state.json`、SQLite 文件或 `plugins\cache`。
- 字体目录为空不一定是错误；也可以在新电脑单独安装 Maple Mono NF CN。

---

## 3. 新电脑：恢复基础资源

先安装 Codex Desktop 并启动一次，让应用创建新的 `.codex` 目录。以下命令中的 `$bundleRoot` 需要改成实际解压目录；为便于说明，假设资源包已经解压到桌面。

```powershell
$ErrorActionPreference = 'Stop'

$bundleRoot = Join-Path ([Environment]::GetFolderPath('Desktop')) 'codex-migration-替换为时间戳'
$codexHome = Join-Path $env:USERPROFILE '.codex'
$userskills = Join-Path $codexHome 'skills'
$agentsHome = Join-Path $env:USERPROFILE '.agents'
$agentsSkills = Join-Path $agentsHome 'skills'

New-Item -ItemType Directory -Path $userskills -Force | Out-Null
New-Item -ItemType Directory -Path $agentsSkills -Force | Out-Null

# 复制 31 个用户技能，保留原有目录名、nature-shared 支持包和 PaperSpine 系列
Get-ChildItem -LiteralPath (Join-Path $bundleRoot 'codex-skills') -Directory |
  ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $userskills -Recurse -Force
  }

# 复制 .agents 技能注册信息和 answer-me-with-html
$sourceLock = Join-Path $bundleRoot '.skill-lock.json'
if (Test-Path -LiteralPath $sourceLock) {
  Copy-Item -LiteralPath $sourceLock -Destination $agentsHome -Force
}
$sourceAgentsSkill = Join-Path $bundleRoot 'agents-skills\answer-me-with-html'
if (Test-Path -LiteralPath $sourceAgentsSkill) {
  Copy-Item -LiteralPath $sourceAgentsSkill -Destination $agentsSkills -Recurse -Force
}

# 复制全局 AGENTS 规则
$bundleGlobalAgents = Join-Path $bundleRoot 'AGENTS.global.md'
if (Test-Path -LiteralPath $bundleGlobalAgents) {
  Copy-Item -LiteralPath $bundleGlobalAgents -Destination (Join-Path $codexHome 'AGENTS.md') -Force
}

# 复制模型目录
Copy-Item -LiteralPath (Join-Path $bundleRoot 'cc-switch-model-catalog.json') `
  -Destination $codexHome -Force

Write-Host "技能目录：$userskills"
Write-Host "模型目录：$codexHome\cc-switch-model-catalog.json"
```

### 3.1 AGENTS 规则

当前机器有两份作用域不同的规则文件。

全局规则位于：

```text
%USERPROFILE%\.codex\AGENTS.md
```

它约束所有项目中的写作风格：

```markdown
# 避免防御性写作
1、不迂回立论（No negative framing）：避免滥用“不是……而是”（It is not X, but rather Y）这种先设定反方、再陈述己方的句式；直接写明是什么，而不是它不是什么，不写“...是两回事”、“不意味着...”等描述。
2、避免过度防御性写作（Over-defensive Writing）。核心观点先行，直接陈述判断，再用事实、逻辑和证据支撑。删除“需要强调的是”“值得注意的是”“这并不意味着”“不能简单地认为”等无效套话。不要提前回应尚未出现的质疑，不主动削弱观点，不堆砌模糊限定、自我贬低和无意义的让步。删除重复总结、空泛解释和不必要的风险提示。
3、如果某句话的作用只是防止被质疑，而不是推进论证，请删除。

# 用于科研
4、论文是发布会，不是工作汇报。1.只围绕最强优势组织叙事；2.不按"做了什么、试过什么、哪些失败了"的过程写；3.禁止自我削弱表达("遗憾的是""仅""仍明显落后""效果有限")，不替审稿人总结弱点；4.打不赢的指标不设为比赛，换评价维度或比较口径；5.不占优的结果不说输，从目标差异或合理权衡解释；6.优势必须主动说清楚，别指望审稿人自己从表格里发现；7.每个实验必须有论证职责，没有就删；8.摘要引言像发布会开场：问题→缺口→思路→最硬的结果；9.结论只强化记忆点，不突然自我否定。
```

工作区规则位于：

```text
Q:\workspace\2026Spring2Winter\AGENTS.md
```

它只约束该 Git 工作区，当前内容为：

```markdown
# Answer format

- Do not create HTML pages by default.
- Use HTML only when the user invokes `@answer-me-with-html` or explicitly asks for an HTML reply.
- In all other cases, answer in plain Markdown or text.
- This rule overrides any skill's always-on or automatic page behavior.
```

迁移时分别恢复这两份文件。工作区路径变化时，把第二份规则放到新工作区最上层项目父目录。

### 3.2 字体

资源包中的 `fonts` 目录是可选的。新电脑安装字体有两种方式：

1. 打开 `fonts` 目录，选中全部 `.ttf` 文件，右键选择“为当前用户安装”。
2. 从 Maple Mono NF CN 的发行包重新安装同名字体族。

安装后在 PowerShell 中检查：

```powershell
$fontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
Get-ChildItem -LiteralPath $fontDir -Filter 'MapleMono-NF-CN-*.ttf' |
  Select-Object Name, Length
```

如果没有安装成功，Codex 仍可启动，但 `Maple Mono NF CN` 可能回退到系统字体。请先把 `[desktop.appearanceDarkChromeTheme.fonts]` 临时改成系统已有字体，再重启 Codex。

---

## 4. 当前 Codex 配置

### 4.1 核心设置摘要

> 本节的模型/provider 项及第 4.2、4.3 节中的模型提供商配置沿用 2026-11-19 快照，本次未同步；其他配置以本次核对结果为准。

| 配置项 | 当前值 | 迁移建议 |
|---|---|---|
| `model_provider` | `custom` | 保留 |
| provider 名称 | `opencode_go` | 保留名称，token 重新填写 |
| provider API | `https://opencode.ai/zen/go/v1`，`responses` wire API | 保留，确认新网络可访问 |
| provider 认证 | `requires_openai_auth = false`，明文 bearer token | 文档脱敏；新电脑手动填写 token |
| 默认模型 | `deepseek-v4.1-flash` | 保留 |
| reasoning effort | `high` | 保留；也可按任务调低 |
| 备选模型 | `qwen4-max` | 通过模型目录恢复 |
| 子 agent 模型 | `deepseek-v4.1-flash` | 保留 |
| `model_catalog_json` | `cc-switch-model-catalog.json` | 连同 JSON 一起恢复 |
| `sandbox_mode` | `danger-full-access` | 安全风险较高，按需保留 |
| sandbox 范围 | 文件系统 unrestricted，网络 enabled | 仅在你接受该风险时保留 |
| approval | `OnRequest`（有效默认值） | 通过 Desktop/CLI 交互确认 |
| Windows sandbox | `elevated` | Windows 专用；新电脑由应用重新生成 |
| memories | 生成和使用均开启 | 只恢复开关，不迁移记忆数据库 |
| Desktop locale | `zh-CN` | 保留 |
| Desktop theme | 深色 Lobster | 保留 |
| UI/代码字体 | Maple Mono NF CN | 先安装字体 |
| code font size | `13` | 保留 |
| Desktop 行为偏好 | 队列模式 `steer`；显示命令步骤、上下文窗口使用量；纯文本输入；默认工作区全视图；启用环境建议和 confetti | 新电脑逐项按需设置 |
| Codex hooks | `hooks.json` 有 `PostToolUse`、`Stop` 配置；未验证 Codex 是否加载 | 在 Settings → Hooks 检查并审阅后再启用 |

### 4.2 当前 `config.toml` 的脱敏参考

下面是当前有效配置的脱敏快照。token 已替换为占位符，用户名、Codex 安装目录和 CUA 管道已参数化。真正迁移时使用第 4.3 节的便携模板，并让新电脑重新生成 app-managed 路径。

```toml
model_provider = "custom"
model = "deepseek-v4.1-flash"
model_reasoning_effort = "high"
model_catalog_json = '<CODEX_HOME>\cc-switch-model-catalog.json'
sandbox_mode = "danger-full-access"

notify = [ "<CODEX_INSTALL_DIR>\\app\\resources\\cua_node\\bin\\node_modules\\@oai\\sky\\bin\\windows\\codex-computer-use.exe", "turn-ended" ]
[model_providers.custom]
name = "opencode_go"
base_url = "https://opencode.ai/zen/go/v1"
wire_api = "responses"
requires_openai_auth = false
experimental_bearer_token = "<OPENCODE_API_KEY>"

[features]
memories = true

[memories]
generate_memories = true
use_memories = true

[agents]
default_subagent_model = "deepseek-v4.1-flash"

[desktop]
followUpQueueMode = "steer"
conversationDetailMode = "STEPS_COMMANDS"
ambient-suggestions-enabled = true
show-context-window-usage = true
composerPlainTextMode = true
enabled-reasoning-efforts = ["low", "medium", "high", "xhigh", "ultra", "persistent", "max"]
default-workspace-full-view = true
hotkey-window-projectless-default-enabled = true
toys-confetti-enabled = true
codeFontSize = 13
localeOverride = "zh-CN"
appearanceDarkCodeThemeId = "lobster"

[desktop.appearanceDarkChromeTheme]
accent = "#ff5c5c"
accentSource = "custom"
contrast = 60
ink = "#e4e4e7"
opaqueWindows = false
surface = "#111827"

[desktop.appearanceDarkChromeTheme.fonts]
code = '"Maple Mono NF CN"'
content = '"Maple Mono NF CN"'
ui = '"Maple Mono NF CN"'

[desktop.appearanceDarkChromeTheme.fonts.codeFace]
family = "Maple Mono NF CN"
fullName = "Maple Mono NF CN Bold"
postscriptName = "MapleMono-NF-CN-Bold"

[desktop.appearanceDarkChromeTheme.fonts.contentFace]
family = "Maple Mono NF CN"
fullName = "Maple Mono NF CN Medium"
postscriptName = "MapleMono-NF-CN-Medium"

[desktop.appearanceDarkChromeTheme.fonts.uiFace]
family = "Maple Mono NF CN"
fullName = "Maple Mono NF CN Medium"
postscriptName = "MapleMono-NF-CN-Medium"

[desktop.appearanceDarkChromeTheme.semanticColors]
diffAdded = "#22c55e"
diffRemoved = "#ff5c5c"
skill = "#3b82f6"

[windows]
sandbox = "elevated"

[marketplaces.openai-bundled]
source_type = "local"
source = '<CODEX_HOME>\.tmp\bundled-marketplaces\openai-bundled'

[marketplaces.openai-primary-runtime]
source_type = "local"
source = '<USERPROFILE>\.cache\codex-runtimes\codex-primary-runtime\plugins\openai-primary-runtime'

[marketplaces.ars-codex]
source_type = "git"
source = "https://github.com/Imbad0202/academic-research-skills-codex.git"
ref = "main"

[plugins."codex-app-tools@openai-bundled"]
enabled = true

[plugins."browser@openai-bundled"]
enabled = true

[plugins."unified-computer-use@openai-bundled"]
enabled = true

[plugins."visualize@openai-bundled"]
enabled = true

[plugins."computer-use@openai-bundled"]
enabled = true

[plugins."chrome@openai-bundled"]
enabled = true

[plugins."latex@openai-bundled"]
enabled = true

[plugins."documents@openai-primary-runtime"]
enabled = true

[plugins."pdf@openai-primary-runtime"]
enabled = true

[plugins."spreadsheets@openai-primary-runtime"]
enabled = true

[plugins."presentations@openai-primary-runtime"]
enabled = true

[plugins."template-creator@openai-primary-runtime"]
enabled = true

[plugins."ars-codex@ars-codex"]
enabled = true

[mcp_servers.node_repl]
args = []
command = '<CODEX_INSTALL_DIR>\app\resources\cua_node\bin\node_repl.exe'
env_vars = ["BROWSER_USE_ACCESS_EXECUTOR_ID", "BROWSER_USE_ACCESS_PIPE_PATH", "BROWSER_USE_ACCESS_VERIFYING_IDENTITY", "CODEX_WINDOWS_REGISTERED_CORE"]
startup_timeout_sec = 120

[mcp_servers.node_repl.env]
NODE_REPL_NATIVE_PIPE_CONNECT_TIMEOUT_MS = "1000"
NODE_REPL_NODE_MODULE_DIRS = '<CODEX_INSTALL_DIR>\app\resources\cua_node\bin\node_modules'
NODE_REPL_NODE_PATH = '<CODEX_INSTALL_DIR>\app\resources\cua_node\bin\node.exe'
NODE_REPL_TRUSTED_CODE_PATHS = '<CODEX_HOME>;<CODEX_INSTALL_DIR>\app\resources\cua_node\bin\node_modules'
CODEX_HOME = '<CODEX_HOME>'
BROWSER_USE_AVAILABLE_BACKENDS = "chrome,iab,mcpapps"
BROWSER_USE_TINYSKY_ENABLED = "1"
NODE_REPL_INSTRUCTIONS_USE_CASE_BROWSER = ""
NODE_REPL_INSTRUCTIONS_USE_CASE_CHROME = ""
BROWSER_USE_CODEX_APP_BUILD_FLAVOR = "prod"
BROWSER_USE_CODEX_APP_VERSION = "26.1120.50957"
NODE_REPL_TRUSTED_SERVICES = '{"browser":"<CODEX_HOME>/plugins/cache/openai-bundled/browser/26.1120.50957/scripts/browser-service.mjs","sky":"@oai/sky/service"}'
SKY_CUA_NATIVE_PIPE = "1"
SKY_CUA_NATIVE_PIPE_DIRECTORY = '\\.\pipe\codex-computer-use-<PIPE_ID>'
CODEX_CLI_PATH = '<CODEX_INSTALL_DIR>\app\resources\codex.exe'
NODE_REPL_UNTRUSTED_ENV_ALLOWLIST = "CODEX_WINDOWS_REGISTERED_CORE"
NODE_REPL_INSTRUCTIONS_USE_CASE_COMPUTER_USE = ""

[projects.'q:\workspace\2026spring2winter']
trust_level = "trusted"
```

重要说明：

- `notify`、`[marketplaces.*]`、`[mcp_servers.node_repl]` 及其环境变量属于本机 app-managed 配置，不复制旧值。
- `experimental_bearer_token` 当前以明文保存在本机配置中。本文档只保留占位符。
- `danger-full-access` 是当前机器的显式选择。
- 当前配置还包含一条当前任务生成的临时目录信任记录，未纳入上方快照，也不属于迁移项。
- `codex doctor` 报告 69 个内置 feature flags 启用、1 个覆盖项；配置中的用户覆盖项是 `memories`。
- `codex doctor` 的 MCP 检查显示 1 个显式配置服务器（`node_repl`）；`cua_repl` 与 `codex_app` 由插件注册，通过 `codex mcp list --json` 查看。

### 4.3 新电脑使用的便携 `config.toml` 模板

在新电脑上先启动 Codex，让它生成基础配置；然后编辑：

```text
%USERPROFILE%\.codex\config.toml
```

如果新文件已有内容，逐项合并下列设置，不要直接覆盖应用刚生成的 runtime、marketplace 或 MCP 段。把 `<OPENCODE_API_KEY>` 替换成有效的 provider token。

```toml
model_provider = "custom"
model = "deepseek-v4.1-flash"
model_reasoning_effort = "high"
model_catalog_json = "cc-switch-model-catalog.json"
sandbox_mode = "danger-full-access"

[desktop]
followUpQueueMode = "steer"
conversationDetailMode = "STEPS_COMMANDS"
ambient-suggestions-enabled = true
show-context-window-usage = true
composerPlainTextMode = true
enabled-reasoning-efforts = ["low", "medium", "high", "xhigh", "ultra", "persistent", "max"]
default-workspace-full-view = true
hotkey-window-projectless-default-enabled = true
toys-confetti-enabled = true
codeFontSize = 13
localeOverride = "zh-CN"
appearanceDarkCodeThemeId = "lobster"

[desktop.appearanceDarkChromeTheme]
accent = "#ff5c5c"
accentSource = "custom"
contrast = 60
ink = "#e4e4e7"
opaqueWindows = false
surface = "#111827"

[desktop.appearanceDarkChromeTheme.fonts]
code = '"Maple Mono NF CN"'
content = '"Maple Mono NF CN"'
ui = '"Maple Mono NF CN"'

[desktop.appearanceDarkChromeTheme.fonts.codeFace]
family = "Maple Mono NF CN"
fullName = "Maple Mono NF CN Bold"
postscriptName = "MapleMono-NF-CN-Bold"

[desktop.appearanceDarkChromeTheme.fonts.contentFace]
family = "Maple Mono NF CN"
fullName = "Maple Mono NF CN Medium"
postscriptName = "MapleMono-NF-CN-Medium"

[desktop.appearanceDarkChromeTheme.fonts.uiFace]
family = "Maple Mono NF CN"
fullName = "Maple Mono NF CN Medium"
postscriptName = "MapleMono-NF-CN-Medium"

[desktop.appearanceDarkChromeTheme.semanticColors]
diffAdded = "#22c55e"
diffRemoved = "#ff5c5c"
skill = "#3b82f6"

[model_providers.custom]
name = "opencode_go"
base_url = "https://opencode.ai/zen/go/v1"
wire_api = "responses"
requires_openai_auth = false
experimental_bearer_token = "<OPENCODE_API_KEY>"

[plugins."codex-app-tools@openai-bundled"]
enabled = true

[plugins."browser@openai-bundled"]
enabled = true

[plugins."unified-computer-use@openai-bundled"]
enabled = true

[plugins."chrome@openai-bundled"]
enabled = true

[plugins."visualize@openai-bundled"]
enabled = true

[plugins."computer-use@openai-bundled"]
enabled = true

[plugins."documents@openai-primary-runtime"]
enabled = true

[plugins."pdf@openai-primary-runtime"]
enabled = true

[plugins."spreadsheets@openai-primary-runtime"]
enabled = true

[plugins."presentations@openai-primary-runtime"]
enabled = true

[plugins."template-creator@openai-primary-runtime"]
enabled = true

[plugins."latex@openai-bundled"]
enabled = true

[plugins."ars-codex@ars-codex"]
enabled = true

[windows]
sandbox = "elevated"

[features]
memories = true

[memories]
generate_memories = true
use_memories = true

[agents]
default_subagent_model = "deepseek-v4.1-flash"
```

模板故意省略了以下内容：

- `notify` 和旧 CUA runtime 路径。
- `[marketplaces.*]` 的旧绝对路径。
- `[mcp_servers.node_repl]` 及其环境变量。
- `[projects.*]` 的旧工作区信任记录。
- 已废弃或会被当前版本忽略的 `disable_response_storage`。

这些设置应由新电脑的 Codex Desktop 在启动、登录、安装插件或显式信任项目时生成。

### 4.4 模型目录

保存到：

```text
%USERPROFILE%\.codex\cc-switch-model-catalog.json
```

内容如下。它是当前模型的覆盖目录：

```json
{
  "models": [
    {
      "additional_speed_tiers": [],
      "auto_compact_token_limit": 943718,
      "availability_nux": null,
      "base_instructions": "You are Codex, a coding agent. You and the user share the same workspace and collaborate to achieve the user's goals.",
      "context_window": 1048576,
      "default_reasoning_level": "high",
      "default_reasoning_summary": "none",
      "description": "deepseek-v4.1-flash",
      "display_name": "deepseek-v4.1-flash",
      "effective_context_window_percent": 95,
      "experimental_supported_tools": [],
      "input_modalities": [
        "text",
        "image"
      ],
      "max_context_window": 1048576,
      "priority": 1000,
      "service_tiers": [],
      "shell_type": "shell_command",
      "slug": "deepseek-v4.1-flash",
      "support_verbosity": false,
      "supported_in_api": true,
      "supported_reasoning_levels": [
        {
          "description": "Fast responses with lighter reasoning",
          "effort": "low"
        },
        {
          "description": "Greater reasoning depth for complex problems",
          "effort": "high"
        },
        {
          "description": "Maximum reasoning depth for the hardest problems",
          "effort": "max"
        }
      ],
      "supports_image_detail_original": false,
      "supports_parallel_tool_calls": false,
      "supports_reasoning_summaries": true,
      "supports_search_tool": false,
      "truncation_policy": {
        "limit": 10000,
        "mode": "bytes"
      },
      "upgrade": null,
      "visibility": "list"
    },
    {
      "additional_speed_tiers": [],
      "auto_compact_token_limit": 900000,
      "availability_nux": null,
      "base_instructions": "You are Codex, a coding agent. You and the user share the same workspace and collaborate to achieve the user's goals.",
      "context_window": 1000000,
      "default_reasoning_level": "high",
      "default_reasoning_summary": "none",
      "description": "qwen4-max",
      "display_name": "qwen4-max",
      "effective_context_window_percent": 95,
      "experimental_supported_tools": [],
      "input_modalities": [
        "text",
        "image"
      ],
      "max_context_window": 1000000,
      "priority": 1001,
      "service_tiers": [],
      "shell_type": "shell_command",
      "slug": "qwen4-max",
      "support_verbosity": false,
      "supported_in_api": true,
      "supported_reasoning_levels": [
        {
          "description": "Fast responses with lighter reasoning",
          "effort": "low"
        },
        {
          "description": "Greater reasoning depth for complex problems",
          "effort": "high"
        },
        {
          "description": "Extra high reasoning depth for complex problems",
          "effort": "xhigh"
        }
      ],
      "supports_image_detail_original": false,
      "supports_parallel_tool_calls": false,
      "supports_reasoning_summaries": true,
      "supports_search_tool": false,
      "truncation_policy": {
        "limit": 10000,
        "mode": "bytes"
      },
      "upgrade": null,
      "visibility": "list"
    }
  ]
}
```

当前机器上该目录由 CC Switch `4.0.30` 管理。新电脑可以选择：

- 方案 A：复制本 JSON，手动配置 provider token。
- 方案 B：安装 CC Switch，在 CC Switch 中重新添加相同 provider 和模型。

不要复制 CC Switch 的 SQLite 数据库或登录 stash。

---

## 5. 插件与 marketplace

### 5.1 三个 marketplace

| Marketplace | 当前根目录（旧机器） | 迁移方式 |
|---|---|---|
| `openai-primary-runtime` | `<USERPROFILE>\.cache\codex-runtimes\codex-primary-runtime\plugins\openai-primary-runtime` | Desktop 自动维护，不复制 |
| `openai-bundled` | `<CODEX_HOME>\.tmp\bundled-marketplaces\openai-bundled` | Desktop 自动维护，不复制 |
| `ars-codex` | `<CODEX_HOME>\.tmp\marketplaces\ars-codex`（Git 来源） | 优先 GitHub 重装；Windows 异常时使用本地 marketplace 回退 |

另外，`openai-api-curated` 会在某些环境中被自动发现，但当前没有从该 marketplace 安装的插件。它不是本次恢复的必要项。

### 5.2 13 个已启用插件

#### OpenAI Bundled（7 个）

| 插件 | 当前版本 | 用途 | 恢复方式 |
|---|---:|---|---|
| `codex-app-tools` | `26.1120.50957` | Desktop 工具/本地 MCP 服务 | Desktop Plugin Manager 或 `codex plugin add` |
| `browser` | `26.1120.50957` | 操作 Codex in-app browser、local web target | 同上 |
| `unified-computer-use` | `26.1120.50957` | 浏览器/桌面统一 CUA runtime | 同上，必须重启 Codex |
| `chrome` | `26.1120.50957` | 控制已有 Chrome 会话、标签和登录态 | 同上 |
| `computer-use` | `26.1120.50957` | Windows Desktop 原生应用控制 | 同上 |
| `latex` | `0.2.10` | LaTeX 编译、诊断和 TeX Live/Tectonic 辅助 | 同上 |
| `visualize` | `1.0.114` | 交互式图表、地图、模拟和可视化页面 | 同上 |

#### OpenAI Primary Runtime（5 个）

| 插件 | 当前版本 | 用途 | 恢复方式 |
|---|---:|---|---|
| `documents` | `26.1123.11515` | Word/文档创建和编辑 | Desktop Plugin Manager 或 `codex plugin add` |
| `pdf` | `26.1123.11515` | PDF 读取、生成、渲染和验证 | 同上 |
| `spreadsheets` | `26.1123.11515` | Excel/表格创建、分析和验证 | 同上 |
| `presentations` | `26.1123.11515` | PPT/演示文稿创建、编辑和渲染 | 同上 |
| `template-creator` | `26.1123.11515` | 从文档、表格、PPT、图片等创建模板 | 同上 |

#### ARS-Codex（1 个）

| 插件 | 当前版本 | 用途 | 恢复方式 |
|---|---:|---|---|
| `ars-codex` | `3.24.2` | 学术研究、写作、审稿、筛选和实验规划 | 从 GitHub marketplace 重装 |

### 5.3 安装命令

先确保 Codex Desktop 已完成首次启动，并让 CLI 可用：

```powershell
codex --version
```

安装 12 个内置插件：

```powershell
$plugins = @(
  'codex-app-tools@openai-bundled',
  'browser@openai-bundled',
  'unified-computer-use@openai-bundled',
  'chrome@openai-bundled',
  'computer-use@openai-bundled',
  'latex@openai-bundled',
  'visualize@openai-bundled',
  'documents@openai-primary-runtime',
  'pdf@openai-primary-runtime',
  'spreadsheets@openai-primary-runtime',
  'presentations@openai-primary-runtime',
  'template-creator@openai-primary-runtime'
)

foreach ($plugin in $plugins) {
  codex plugin add $plugin
}
```

如果某个插件已经安装，允许命令提示“已安装”，不要重复覆盖其缓存。安装完成后打开新对话，让插件重新注册技能和 MCP。

### 5.4 ARS-Codex 安装与 Windows 回退

优先使用上游 GitHub marketplace：

```powershell
codex plugin marketplace add Imbad0202/academic-research-skills-codex --ref main
codex plugin add ars-codex@ars-codex
```

以后更新：

```powershell
codex plugin marketplace upgrade ars-codex
codex plugin add ars-codex@ars-codex
```

如果 Windows 上出现 `os error 5`、`marketplace-upgrade-*` 残留目录或磁盘持续增长，先停止重复重试，并参考上游 `docs/windows-marketplace-recovery.md`。本机当前的 ARS 来源是 GitHub marketplace。Windows 更新异常时可以使用资源包中的本地 marketplace 备份：

```powershell
$codexHome = Join-Path $env:USERPROFILE '.codex'
$localMarketplace = Join-Path $codexHome 'local-marketplaces\academic-research-skills-codex'
$bundleLocal = Join-Path $bundleRoot 'academic-research-skills-codex'

New-Item -ItemType Directory -Path (Split-Path $localMarketplace) -Force | Out-Null
if (-not (Test-Path -LiteralPath $localMarketplace)) {
  Copy-Item -LiteralPath $bundleLocal -Destination $localMarketplace -Recurse -Force
}

codex plugin marketplace add $localMarketplace
codex plugin add ars-codex@ars-codex
```

本地 marketplace 只解决更新路径问题，不改变插件本身的技能内容。

---

## 6. 技能清单

### 6.1 用户技能：31 个

这些目录放在：

```text
%USERPROFILE%\.codex\skills\
```

| 技能 | 作用 | 当前来源/记录方式 |
|---|---|---|
| `answer-me-with-html` | 将回答做成单页视觉 HTML；仅在显式调用时使用 | GitHub `QingYunA/answer-me-with-html`；本机另有一份 `.agents` 副本 |
| `deep-research` | 深度文献调查、来源验证、MECE 综合 | 从原机复制；未记录可靠上游 |
| `domain-modeling` | 维护项目术语、词汇表和 ADR | 从原机复制；未记录可靠上游 |
| `figure-designer` | 科研论文核心图表的设计和审查建议 | 从原机复制；未记录可靠上游 |
| `grill-me` | 用连续追问压测计划或设计；入口技能 | 从原机复制；未记录可靠上游 |
| `grill-with-docs` | 压测设计并同步产出 ADR 和词汇表 | 从原机复制；未记录可靠上游 |
| `grilling` | 按设计树轮次追问并形成共同理解 | 从原机复制；未记录可靠上游 |
| `html-docs` | HTML 文档、教程、讲解视频和课程页面 | 从原机复制；未记录可靠上游 |
| `html-document-creator` | 分页式 HTML 手册、宣传册和受控导出 | GitHub `huzhe2003/html-document-creator`；从原机复制也可 |
| `humanizer` | 去除 AI 腔并保留原意 | 从原机复制；未记录可靠上游 |
| `i-have-adhd` | 面向 ADHD 读者的行动优先输出格式 | 从原机复制；未记录可靠上游 |
| `impeccable` | 前端界面设计、可用性/无障碍审查和设计系统整理 | GitHub `pbakaus/impeccable`；从原机复制也可 |
| `idea-evaluator` | 研究想法评估、风险审计和可行性判断 | 从原机复制；未记录可靠上游 |
| `manage-skills` | 通过 skills-manager-cli 管理采集、部署和源信息 | 从原机复制；未记录可靠上游 |
| `md2html` | 长 Markdown 转单页 HTML，含 Mermaid/主题 | GitHub `haidang1810/md2html`；从原机复制也可 |
| `nature-figure` | 科研绘图、多面板图、图形摘要和图形 QA | 从原机复制；未记录可靠上游 |
| `nature-paper-xray` | 单篇论文的深度结构还原和证据阅读 | 从原机复制；未记录可靠上游 |
| `nature-paper2word` | Markdown 论文转 Word，处理公式、交叉引用和参考文献 | 从原机复制；未记录可靠上游 |
| `nature-ref-verifier` | 参考文献逐字段多源核验 | 从原机复制；未记录可靠上游 |
| `nature-shared` | Nature 系列技能的共享支持包，不单独调用 | 必须与相关 Nature 技能一起复制 |
| `paper-polish` | 学术英文和中译英润色，保留原意并校准语气 | 从原机复制；未记录可靠上游 |
| `paper-spine` | 论文研究、写作、制图和审阅的编排入口 | PaperSpine v6.0.0-beta.2；由内置更新器管理 |
| `paper-spine-study` | 研究问题、证据组织和研究执行 | PaperSpine v6.0.0-beta.2 |
| `paper-spine-followwriting` | 依据真实结果和参考论文结构写作 | PaperSpine v6.0.0-beta.2 |
| `paper-spine-figures` | 依据真实研究证据设计、绘制和修订科研图 | PaperSpine v6.0.0-beta.2 |
| `paper-spine-review` | 审阅稿件、证据、引用和图件并验证修改 | PaperSpine v6.0.0-beta.2 |
| `paper-spine-deliver` | 渲染、检查并打包论文的可编辑交付件 | PaperSpine v6.0.0-beta.2 |
| `pre-submission-reviewer` | 投稿前的宏观逻辑、写作、语法、LaTeX 和图表审查 | 从原机复制；未记录可靠上游 |
| `prompt-master` | 为指定 AI 工具生成优化后的提示词 | 从原机复制；未记录可靠上游 |
| `taste-skill` | 网站与产品界面设计、前端实现和视觉质量检查 | GitHub `Leonxlnx/taste-skill`；从原机复制也可 |
| `tech-paper-template` | 技术论文骨架、逻辑链和贡献结构 | 从原机复制；未记录可靠上游 |

说明：

- `nature-shared` 是支持包，其他 Nature 技能可能通过相邻目录读取它。
- PaperSpine 六项来自受管理的 `PaperSpine v6.0.0-beta.2` 技能包；更新器元数据位于 `%USERPROFILE%\.codex\.paperspine-skills`。
- `answer-me-with-html` 同时存在于 `.codex\skills` 和 `.agents\skills`。迁移时保留两份可以复现当前发现状态。

### 6.2 已知来源的重装命令

使用系统自带的技能安装器安装 `answer-me-with-html`：

```powershell
$installer = Join-Path $env:USERPROFILE '.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py'
python $installer `
  --repo QingYunA/answer-me-with-html `
  --ref main `
  --path skills/answer-me-with-html `
  --method git
```

安装 `html-document-creator`：

```powershell
$dest = Join-Path $env:USERPROFILE '.codex\skills\html-document-creator'
if (-not (Test-Path -LiteralPath $dest)) {
  git clone https://github.com/huzhe2003/html-document-creator.git $dest
}
```

安装 `md2html`：

```powershell
$dest = Join-Path $env:USERPROFILE '.codex\skills\md2html'
if (-not (Test-Path -LiteralPath $dest)) {
  git clone https://github.com/haidang1810/md2html.git $dest
}
```

从原机复制仍然是最可靠的迁移方式，因为当前机器上有些技能没有记录上游仓库或版本。

### 6.3 `.agents` 注册信息

当前 `.agents/.skill-lock.json` 记录了一项技能：

```json
{
  "version": 3,
  "skills": {
    "answer-me-with-html": {
      "source": "QingYunA/answer-me-with-html",
      "sourceType": "github",
      "sourceUrl": "https://github.com/QingYunA/answer-me-with-html.git",
      "skillPath": "skills/answer-me-with-html/SKILL.md",
      "skillFolderHash": "193227a0df61d26c2c1ba7a8730daaa47de88ec1",
      "installMode": "copy",
      "installedAt": "2026-11-11T13:32:41.933Z",
      "updatedAt": "2026-11-19T02:19:00.741Z",
      "commit": "912bad4cb7ccdb3729262bf885f5280b3da941ee"
    }
  },
  "dismissed": {}
}
```

该文件只记录技能来源、安装方式和目录哈希，不包含用户对话。

---

### 6.4 系统技能：6 个

这些技能位于：

```text
%USERPROFILE%\.codex\skills\.system\
```

| 技能 | 作用 | 迁移方式 |
|---|---|---|
| `imagegen` | 生成/编辑位图图像 | Codex 自动维护 |
| `openai-docs` | OpenAI 产品和 Codex 文档查询 | Codex 自动维护 |
| `review-agent` | 审查代理相关能力 | Codex 自动维护 |
| `skill-creator` | 创建和更新 Codex 技能 | Codex 自动维护 |
| `skill-installer` | 从 GitHub/curated 列表安装技能 | Codex 自动维护 |
| `create-statusline` | 为 Codex CLI 构建和启用自定义 MCP 状态栏 | Codex 自动维护 |

不要复制旧机器的 `.system` 目录。新电脑安装 Codex 后让应用重新生成，避免把旧版本的说明和脚本带过去。

### 6.5 插件自带技能：14 个

| 插件 | 自带技能 |
|---|---|
| `browser` | `control-in-app-browser` |
| `chrome` | `control-chrome` |
| `computer-use` | `computer-use` |
| `latex` | `latex-compile`、`latex-doctor`、`texlive-runtime-installer` |
| `visualize` | `visualize` |
| `documents` | `documents` |
| `pdf` | `pdf` |
| `presentations` | `presentations` |
| `spreadsheets` | `spreadsheets`、`excel-live-control` |
| `template-creator` | `template-creator` |
| `ars-codex` | `academic-research-suite` |

`codex-app-tools` 和 `unified-computer-use` 主要通过 MCP/runtime 提供能力，不以独立 `SKILL.md` 形式注册。

调用示例（在新对话中测试）：

```text
Use $academic-research-suite to review this research plan.
Use $pdf to inspect a local PDF.
Use $latex-compile to compile a minimal TeX project.
```

---

## 7. MCP 与 CUA runtime

### 7.1 当前记录

通过 `codex mcp list --json` 观察到的记录如下。`codex doctor` 只统计 `config.toml` 中显式声明的 `node_repl`，插件注册项需单独查看：

| 名称 | 来源 | 当前状态 | 迁移处理 |
|---|---|---|---|
| `node_repl` | 旧机器 `config.toml` 中显式记录 | enabled | 不复制旧路径，让新电脑重新生成 |
| `cua_repl` | `unified-computer-use` 插件提供 | enabled | 安装并启用插件后重启 Codex |
| `codex_app` | `codex-app-tools` 插件提供 | disabled（CLI 视角） | 安装插件；若 Desktop 需要，在 Plugin Manager 中启用后打开新对话 |

当前 `node_repl` 依赖的 `CODEX_WINDOWS_REGISTERED_CORE` 在某些 `codex doctor` 调用中会显示未设置。该变量由 Desktop/CUA 环境注入，**不要手动填旧机器的值**；先重启 Desktop 或重新启用 CUA 插件，再检查。

### 7.2 迁移原则

- 不要复制 `mcp_servers.node_repl.command`、`NODE_REPL_NODE_PATH`、`NODE_REPL_NODE_MODULE_DIRS`、`CODEX_CLI_PATH`、`SKY_CUA_NATIVE_PIPE_DIRECTORY`。
- 这些值包含旧机器的 runtime 哈希、用户名、插件版本和管道名。
- 新电脑安装 `unified-computer-use`、`computer-use`、`browser`、`codex-app-tools` 后，重启 Codex Desktop，让应用重新生成路径。
- 检查：

```powershell
codex mcp list --json
```

如果出现旧路径，关闭 Codex，编辑 `%USERPROFILE%\.codex\config.toml`，删除旧的 `[mcp_servers.node_repl]` 及子表，再重新启动 Codex。不要通过复制旧 MCP 块来修复缺失。

---

## 8. Desktop 外观和字体

当前主题设置：

| 设置 | 值 |
|---|---|
| 深色主题 ID | `lobster` |
| accent | `#ff5c5c` |
| accent source | `custom` |
| surface | `#111827` |
| ink | `#e4e4e7` |
| contrast | `60` |
| opaque windows | `false` |
| diff added | `#22c55e` |
| diff removed | `#ff5c5c` |
| skill semantic color | `#3b82f6` |
| UI/content/code font | `Maple Mono NF CN` |
| code font size | `13` |
| locale | `zh-CN` |

可用的 reasoning effort 选项当前为：

```text
low, medium, high, xhigh, ultra, persistent, max
```

`deepseek-v4.1-flash` 在模型目录中声明 `low`、`high`、`max` 三档，默认用 `high`；`qwen4-max` 声明 `low`、`high`、`xhigh` 三档。`ultra`、`persistent` 是 Desktop 的可用选项，不代表自定义 provider 接受每个值；遇到 400 或配置拒绝时，改回当前模型声明的档位。

字体族来自当前 Windows 用户字体目录。安装 16 个 `MapleMono-NF-CN-*.ttf` 字体文件后，Codex 才能稳定显示主题指定的字重。

---

## 9. 外部依赖基线

| 依赖 | 当前状态 | Codex 中的用途 |
|---|---|---|
| Python | `3.14.10`，`%LOCALAPPDATA%\Programs\Python\Python314\python.exe` | 技能脚本、模型目录、部分文档处理 |
| Node.js | `26.13.1` | Desktop/CUA/浏览器工具和部分 skills |
| npm | `11.20.0` | Node 相关工具 |
| Git | `2.56.1.windows.1` | 插件 marketplace、技能安装、项目操作 |
| ripgrep | `15.2.0` | 文件搜索 |
| PowerShell | `7.6.9`，Primary Runtime 自带 | 本文档命令和部分 skills |
| CC Switch | `4.0.30` | 当前 provider/model catalog 管理 |
| OpenCode | `2.3.0`，可选 | 独立桌面应用，不是 Codex 运行必需 |
| R / Rscript | 未安装 | `nature-figure` 的 R 路线需要另行安装 |
| Pandoc | `3.14` | Markdown/文档转换 |
| LibreOffice | 未安装 | 某些 Office 转换/渲染的可选工具 |
| MiKTeX | `25.12`，系统 TeX | LaTeX 编译和诊断 |
| Tectonic | `0.17.0`，Primary Runtime 自带 | LaTeX 插件的便携编译后端 |

内置插件依赖由 Codex Primary Runtime 和 Desktop 自带 runtime 提供，通常不需要手动安装 Node 包。用户技能如果包含自己的 `requirements.txt`、Python 包或命令行工具，应在首次调用时运行该技能自带的依赖检查。

新电脑建议检查：

```powershell
python --version
node --version
npm --version
git --version
codex --version
```

如果 `codex` 不在 PATH 中，使用 Codex Desktop 的内置终端，或在应用设置中启用 CLI。不要从旧机器复制 CLI 可执行文件。

---

## 10. 本地项目和远程连接

### 10.1 Desktop 本地项目

当前 Desktop 记录了两个本地项目：

| 项目名称 | 路径 |
|---|---|
| `2026Spring2Winter` | `Q:\workspace\2026Spring2Winter` |
| `MasterGraduationProject` | `Q:\workspace\2026Spring2Winter\MasterGraduationProject` |

当前 `config.toml` 的稳定受信任工作区是：

```text
Q:\workspace\2026Spring2Winter
```

另有一条为当前任务生成的临时目录信任记录，不应迁移。新电脑应通过 Codex Desktop 重新打开项目并确认 trust 提示。

### 10.2 远程连接

当前快照中没有需要迁移的 SSH 连接别名。新电脑需要按需在 Codex Desktop 的远程连接界面重新发现或添加连接，并在系统 SSH 客户端中准备认证。不要复制主机地址、端口、私钥、agent forwarding 配置或任何登录凭据到本文件。

---

## 11. 验收和排错

### 11.1 配置检查

```powershell
codex --version
codex doctor
codex plugin list
codex mcp list --json
```

重点确认：

- `codex doctor` 的 `config.toml parse` 为 `ok`。
- 按目标机当前配置确认模型可用；本次未同步模型提供商设置。
- 没有旧机器的 runtime 哈希、用户名或管道路径。
- `model_catalog_json` 能找到新电脑上的 `cc-switch-model-catalog.json`。
- 插件总数和启用状态与第 5 节一致。
- MCP 路径由新电脑生成；`codex doctor` 的 MCP 环境缺失提示不应通过硬编码旧值来消除。

### 11.2 技能检查

```powershell
$skills = Join-Path $env:USERPROFILE '.codex\skills'
Get-ChildItem -LiteralPath $skills -Directory |
  Where-Object { $_.Name -ne '.system' } |
  Select-Object -ExpandProperty Name

$agentsSkill = Join-Path $env:USERPROFILE '.agents\skills\answer-me-with-html'
Test-Path -LiteralPath $agentsSkill
```

预期用户技能为 31 个目录，另有一个 `.system` 目录。如果 Names 中出现旧版本的重复目录，请先确认来源，不要直接删除仍在使用的副本。

### 11.3 插件和模型 smoke test

打开新对话，依次测试：

1. 选择一个普通项目，发送“只回复 OK”，确认 provider 鉴权正常。
2. 输入 `Use $academic-research-suite to outline a small literature review.`，确认 ARS 插件被发现。
3. 输入 `Use $pdf to inspect a local PDF.`，确认 Primary Runtime 插件被发现。
4. 输入 `Use $latex-compile to compile a minimal LaTeX document.`，确认 LaTeX 工具可用。
5. 如果需要浏览器或桌面控制，启用 Computer Use 插件后测试一次显式的浏览器/桌面任务。

### 11.4 常见问题

| 现象 | 优先检查 |
|---|---|
| 模型返回 401/403 | `<OPENCODE_API_KEY>` 是否替换；provider 的 `base_url` 和 `wire_api` 是否正确 |
| 模型目录不生效 | JSON 是否放在 `%USERPROFILE%\.codex`，文件名是否拼写一致 |
| 插件列表为空 | 是否先启动过一次 Codex Desktop；marketplace 是否由应用重新生成 |
| ARS 安装或更新失败 | 是否需要本地 marketplace 回退；是否有 `marketplace-upgrade-*` 残留 |
| MCP 启动失败 | 是否复制了旧 runtime 路径；删除旧 MCP 块并重启 Desktop |
| 主题字体不显示 | Maple Mono NF CN 是否安装到当前用户字体目录 |
| 技能不可见 | 技能目录层级是否正确、是否打开了新对话、`nature-shared` 是否仍在相邻目录 |
| reasoning effort 报 400 | 使用所选模型目录中声明的档位 |
| `codex doctor` 报 MCP env 变量缺失 | 先重启 Desktop/重新启用 CUA 插件；不要填旧机器值 |

---

## 12. 官方参考

- Codex 配置参考：<https://developers.openai.com/codex/config-reference/>
- Codex 高级配置与 hooks/MCP：<https://developers.openai.com/codex/config-advanced/>
- Codex 自定义、skills 与 MCP：<https://developers.openai.com/codex/concepts/customization>
- Codex Plugins 结构：<https://developers.openai.com/codex/plugins/build>
- ARS-Codex 仓库：<https://github.com/Imbad0202/academic-research-skills-codex>

---

## 13. 最终安全边界

这份文档可以安全地作为迁移清单保存，但它不是凭据保险箱。任何时候都不要把以下内容写入 `harness/codex.md` 或以未加密形式提交到 Git：

- `<OPENCODE_API_KEY>` 的真实值；
- `auth.json`、OAuth、Cookie 或 SSH 私钥；
- 旧机器的 hostname、IP、SSH identity、端口和登录凭据；
- `.codex-global-state.json`、会话、记忆、聊天、工作区私有文件和数据库；
- CC Switch 数据库中的 provider 记录。

如果迁移过程中发现 `config.toml` 曾把 token 写入过共享目录，建议在 provider 控制台轮换 token，而不是只删除文本。

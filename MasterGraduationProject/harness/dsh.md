# DeepSeek Harness (DSH) Windows 本地配置迁移手册

> 快照日期：2026-11-11（Asia/Shanghai）
> 源环境：Windows 10 专业版 22H2（19045）、DeepSeek Harness Desktop `0.2.2-rc.1`、内置 dsh CLI `0.2.2-rc.1`、profile `desktop`
> 目标环境：另一台 Windows 电脑
> 迁移范围：DSH profile（bundle 层 + 用户 patch 层）、模型 provider 目录、插件 bundle、技能、AGENTS 规则、外观字号和必要依赖
> 不迁移：登录凭据、API token、会话、附件、工作区索引、插件缓存和皮肤目录缓存

本文档是一个快照，不是"把整个 `%USERPROFILE%\.dsh` 目录原样复制过去"的教程。DSH 的 `dsh-runtimes`、`node_modules`、`.plugin-manager`、`.dsh-skin-market` 和 `sessions` 都包含本机哈希、绝对路径或私有数据，必须让新电脑重新生成；`.credentials.yaml` 里是明文密钥，任何情况下都不能进入迁移包。

---

## 0. 一页式迁移清单

推荐顺序：

1. 在新电脑安装 DeepSeek Harness Desktop，至少启动一次并完成登录，让应用创建 `%USERPROFILE%\.dsh`。
2. 在旧电脑运行"第 2 节"的导出命令，生成不含密钥的迁移资源包。
3. 在新电脑运行"第 3 节"的恢复命令，复制共享技能与 AGENTS 规则。
4. 按"第 4.3 节"把 `cordis.patch.yml` 的用户层逐条合并进去，不要直接覆盖应用刚生成的 profile。
5. 在应用内 **设置 → 插件** 重装 6 个第三方 bundle（`dsh-ppt`、`dsh-hyperframes`、`genui`、`dsh-skin-market`、`dsh-codex-effort-slider`、`dsh-answer-me-with-html`）。
6. 在 **设置 → 模型** 里重新填写 provider 凭据（`OPENCODE_GO_API_KEY`），凭据只在新电脑上录入。
7. 用 GUI 重新打开本地工作区；不要复制旧机器的 `storages\workspace.json` 或 `sessions`。
8. 运行"第 11 节"的验收命令。

最小验收标准：

- `dsh --version` 输出 `0.2.2-rc.1`（版本可不同，但要与桌面端一致）。
- `%USERPROFILE%\.dsh\profiles\desktop\package.json` 的 `dsh.profile.bundles` 有 8 项：`@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-web-app` 和 6 个第三方 bundle。
- `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml` 生效：默认 provider 为 `opencode-go`，模型 `deepseek-v4.1-flash`，`reasoningEffort: max`。
- 新会话的技能目录里能看到 `genui`、`dsh-ppt`、`hyperframes`、`office` 系列。
- 设置里的插件页显示 6 个第三方插件已启用且无加载错误。
- Web 界面的侧边栏（终端、文件、文件预览）可用。

---

## 1. 当前环境快照

| 项目 | 当前值 |
|---|---|
| 操作系统 | Windows 10 专业版 22H2，`10.0.19045`，64 位，中文系统 |
| 应用安装目录 | `%LOCALAPPDATA%\Programs\DeepSeek Harness` |
| 桌面端版本 | `0.2.2-rc.1`（文件版本 `0.2.2.0`） |
| dsh CLI | `0.2.2-rc.1` |
| DSH Home | `%USERPROFILE%\.dsh`（环境变量 `DSH_HOME`） |
| 当前 profile | `desktop`（环境变量 `DSH_PROFILE`） |
| profile 目录 | `%USERPROFILE%\.dsh\profiles\desktop`（`DSH_PROFILE_DIR`） |
| 另一个 profile | `web`，只有 `cordis.patch.yml`，由 CLI 启动 |
| 默认 shell | PowerShell（`pwsh`） |
| 默认模型 provider | `opencode-go`，由 `@deepseek-ai/dsh-llm-pi-ai` 提供 |
| 默认模型 | `deepseek-v4.1-flash`，`contextWindow` 1000000，`maxTokens` 384000，输入 text+image |
| 推理等级 | `max` |
| 凭据注入方式 | profile 里写 `apiKeyEnv: OPENCODE_GO_API_KEY`，真实密钥存于 `.credentials.yaml` 的 `refs` |
| 已启用 bundle | 8 个（2 个核心 + 6 个第三方） |
| 内置未启用 bundle | 19 个（实验/可选） |
| 仅目录可见的 bundle | 3 个（含 Windows 不支持的 CUA bundle） |
| 内置 office 技能 | 7 个，随应用安装 |
| bundle 自带技能 | 24 个（`dsh-hyperframes` 21、`genui` 1、`dsh-ppt` 1、`dsh-answer-me-with-html` 1） |
| 共享技能目录 | `%USERPROFILE%\.agents\skills`，1 个（`answer-me-with-html`） |
| 工作区数量 | 3 个 |
| 会话数量 | 16 个（只计数，不迁移） |
| 界面语言 | `zh-CN` |
| 界面字号 | 正文 15、代码 13、终端 14 |
| 应用更新通道 | `nightly`，`https://download.deepseek.com/dsh-desk/feeds/win-x64/` |
| 打包运行时 | Python 3.12.14、Node.js 24.21.0、pnpm 11.28.5 |
| 文件策略（本会话） | `danger-full-access`，且审批提示已关闭 |

### 1.1 快照的边界

- 应用版本、bundle 版本和 `@deepseek-ai/*` 包版本会随更新变化。本文档记录当前机器上的版本，不是要求新电脑钉住这些版本。
- 新电脑的用户名、`%USERPROFILE%`、Web 端口、`client-connection/browser-session` 密钥和 `dsh-runtimes` 内容都不同。
- `dsh-runtimes\dsh-primary-runtime` 是应用管理的运行时载荷（`payloadDigest` 会变），不应从旧电脑复制。
- 外观只有字号写在 profile 里；字体族由系统决定，本机没有在 patch 中覆盖字体，因此不涉及字体文件迁移。
- 本机当前把文件策略放宽到 `danger-full-access` 并关闭了审批提示。这能复现当前工作方式，但不是被推荐的安全默认值；新电脑应在知情后自行选择。DSH 的默认值是 `workspace-write`。

### 1.2 明确不迁移的内容

不要把下面这些内容放进迁移包，也不要提交到仓库：

- `%USERPROFILE%\.dsh\.credentials.yaml`：含 `secret` / `token` 明文和 `refs` 里的真实 API key。
- `%USERPROFILE%\.dsh\.anonymous-user-id`：本机匿名标识。
- `%USERPROFILE%\.dsh\sessions\**`：会话正文，`session.v4.jsonl.zstd` 是压缩后的完整对话。
- `%USERPROFILE%\.dsh\attachments\v1\**`：上传附件。
- `%USERPROFILE%\.dsh\storages\workspace.json`：工作区、会话归属和置顶/归档状态等本地私有元数据。
- `%USERPROFILE%\.dsh\dsh-runtimes\**`：应用管理的 Python/Node/pnpm 载荷。
- `%USERPROFILE%\.dsh\profiles\desktop\node_modules\**`、`.pnpm`、`pnpm-lock.yaml` 之外的安装产物。
- `%USERPROFILE%\.dsh\profiles\desktop\.plugin-manager\logs\**`：插件安装日志。
- `%USERPROFILE%\.dsh\profiles\desktop\.dsh-skin-market\catalog.json`：约 3.3 MB 的皮肤/插件市场缓存。
- `%USERPROFILE%\.dsh\profiles\desktop\stardustlc-plugin-update-cache.json`：更新检查缓存。
- `%APPDATA%\@deepseek-ai\dsh-desktop\**`：Electron 用户数据（`Preferences`、`IndexedDB`、`Local Storage`、`Cache`、`plugin-operations`、`logs`）。
- `%LOCALAPPDATA%\@deepseek-aidsh-desktop-updater\**`：更新器缓存。
- 任何个人对话、工作区文件和附件。

---

## 2. 旧电脑：生成迁移资源包

下面的命令只导出可迁移的用户资产，不复制 `.credentials.yaml`，也不会带上任何会话或缓存。请在旧电脑的 PowerShell 中运行。

```powershell
$ErrorActionPreference = 'Stop'

$dshHome    = Join-Path $env:USERPROFILE '.dsh'
$profileDir = Join-Path $dshHome 'profiles\desktop'
$agentsHome = Join-Path $env:USERPROFILE '.agents'
$stamp      = Get-Date -Format 'yyyyMMdd-HHmmss'
$bundleRoot = Join-Path ([Environment]::GetFolderPath('Desktop')) "dsh-migration-$stamp"

foreach ($sub in 'desktop-profile', 'web-profile', 'agents-skills', 'fonts') {
  New-Item -ItemType Directory -Path (Join-Path $bundleRoot $sub) -Force | Out-Null
}

# 1) profile 用户层：patch、bundle 清单、依赖版本快照
Copy-Item -LiteralPath (Join-Path $profileDir 'cordis.patch.yml')   -Destination (Join-Path $bundleRoot 'desktop-profile') -Force
Copy-Item -LiteralPath (Join-Path $profileDir 'package.json')       -Destination (Join-Path $bundleRoot 'desktop-profile') -Force
Copy-Item -LiteralPath (Join-Path $profileDir 'pnpm-lock.yaml')     -Destination (Join-Path $bundleRoot 'desktop-profile') -Force
Copy-Item -LiteralPath (Join-Path $profileDir 'pnpm-workspace.yaml') -Destination (Join-Path $bundleRoot 'desktop-profile') -Force

# 2) web profile 的用户层（本机多配了 deepseek-v4-pro / glm-5.3 / glm-5.3-flash）
Copy-Item -LiteralPath (Join-Path $dshHome 'profiles\web\cordis.patch.yml') -Destination (Join-Path $bundleRoot 'web-profile') -Force

# 3) 共享技能注册信息（.skill-lock.json 只记录来源和哈希，不是密钥）
$agentsSkill = Join-Path $agentsHome 'skills\answer-me-with-html'
if (Test-Path -LiteralPath $agentsSkill) {
  Copy-Item -LiteralPath $agentsSkill -Destination (Join-Path $bundleRoot 'agents-skills') -Recurse -Force
}
$skillLock = Join-Path $agentsHome '.skill-lock.json'
if (Test-Path -LiteralPath $skillLock) {
  Copy-Item -LiteralPath $skillLock -Destination $bundleRoot -Force
}

# 4) 工作区级 AGENTS 规则
$agentsFile = 'C:\workspace\2026Spring2Winter\AGENTS.md'
if (Test-Path -LiteralPath $agentsFile) {
  Copy-Item -LiteralPath $agentsFile -Destination $bundleRoot -Force
}

# 5) 迁移手册本身
$handbook = 'C:\workspace\2026Spring2Winter\MasterGraduationProject\harness\dsh.md'
if (Test-Path -LiteralPath $handbook) {
  Copy-Item -LiteralPath $handbook -Destination $bundleRoot -Force
}

# 6) 可选：HyperFrames 工程（这是用户内容，不是缓存；不需要时整段删除）
$hfProjects = Join-Path $dshHome 'data\dsh-hyperframes\projects'
if (Test-Path -LiteralPath $hfProjects) {
  Copy-Item -LiteralPath $hfProjects -Destination (Join-Path $bundleRoot 'hyperframes-projects') -Recurse -Force
}

# 7) 可选：字体。本机 profile 未覆盖字体族，只有字号，通常不需要带字体。
$fontSource = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
Get-ChildItem -LiteralPath $fontSource -Filter 'MapleMono-NF-CN-*.ttf' -ErrorAction SilentlyContinue |
  Copy-Item -Destination (Join-Path $bundleRoot 'fonts') -Force

$zipPath = "$bundleRoot.zip"
Compress-Archive -Path (Join-Path $bundleRoot '*') -DestinationPath $zipPath -Force
Write-Host "迁移资源包已生成：$zipPath"
```

检查点：

- `desktop-profile` 里有 `cordis.patch.yml`、`package.json`、`pnpm-lock.yaml`、`pnpm-workspace.yaml` 四个文件。
- `agents-skills\answer-me-with-html` 和根目录的 `.skill-lock.json` 存在。
- `AGENTS.md` 存在。
- `fonts` 目录为空不算错误；本机也没在 patch 里引用特定字体。

生成后自查，确认包里没有密钥和私有状态：

```powershell
$zipPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'dsh-migration-替换为时间戳.zip'
$tmp = Join-Path $env:TEMP ('dsh-zip-check-' + [guid]::NewGuid())
Expand-Archive -LiteralPath $zipPath -DestinationPath $tmp -Force
$forbidden = Get-ChildItem -LiteralPath $tmp -Recurse -File -Force |
  Where-Object { $_.Name -match '^\.credentials\.yaml$|^\.anonymous-user-id$|session\.v4\.jsonl\.zstd|^workspace\.json$|^catalog\.json$' }
if ($forbidden) { $forbidden.FullName; throw '迁移包包含禁止迁移的文件' } else { 'OK：未发现禁止迁移的文件' }
Remove-Item -LiteralPath $tmp -Recurse -Force
```

---

## 3. 新电脑：恢复基础资源

先安装 DeepSeek Harness Desktop 并启动一次，让应用创建新的 `%USERPROFILE%\.dsh` 和 `profiles\desktop`。以下命令中的 `$bundleRoot` 需要改成实际解压目录。

```powershell
$ErrorActionPreference = 'Stop'

$bundleRoot = Join-Path ([Environment]::GetFolderPath('Desktop')) 'dsh-migration-替换为时间戳'
$dshHome    = Join-Path $env:USERPROFILE '.dsh'
$profileDir = Join-Path $dshHome 'profiles\desktop'
$agentsHome = Join-Path $env:USERPROFILE '.agents'

if (-not (Test-Path -LiteralPath (Join-Path $profileDir 'cordis.patch.yml'))) {
  throw '请先启动一次 DeepSeek Harness Desktop，让应用生成 profiles\desktop'
}

# 共享技能与注册信息
New-Item -ItemType Directory -Path (Join-Path $agentsHome 'skills') -Force | Out-Null
$sourceSkill = Join-Path $bundleRoot 'agents-skills\answer-me-with-html'
if (Test-Path -LiteralPath $sourceSkill) {
  Copy-Item -LiteralPath $sourceSkill -Destination (Join-Path $agentsHome 'skills') -Recurse -Force
}
$sourceLock = Join-Path $bundleRoot '.skill-lock.json'
if (Test-Path -LiteralPath $sourceLock) {
  Copy-Item -LiteralPath $sourceLock -Destination $agentsHome -Force
}

# profile 目录留档：先备份应用生成的版本，再按第 4.3 节手工合并
$backupDir = Join-Path $env:TEMP ('dsh-profile-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $profileDir 'cordis.patch.yml') -Destination $backupDir -Force
Copy-Item -LiteralPath (Join-Path $profileDir 'package.json')     -Destination $backupDir -Force

Write-Host "共享技能：$agentsHome\skills"
Write-Host "profile 备份：$backupDir"
Write-Host "参考清单：$bundleRoot\desktop-profile"
```

### 3.1 AGENTS 规则

当前项目的规则不在项目目录中，而在 Git 工作区的父目录：

```text
C:\workspace\2026Spring2Winter\AGENTS.md
```

如果新电脑也采用相同的工作区布局，把资源包中的 `AGENTS.md` 放到相同位置。若工作区路径不同，应放到新工作区的最上层项目父目录，确保它覆盖所有需要该规则的仓库。

新电脑上的规则文件内容应为：

```markdown
# Answer format

- Do not create HTML pages by default.
- Use HTML only when the user invokes `@answer-me-with-html` or explicitly asks for an HTML reply.
- In all other cases, answer in plain Markdown or text.
- This rule overrides any skill's always-on or automatic page behavior.
```

这是工作区级规则，不是用户全局规则。不要把它复制到 `.dsh` 根目录，除非你明确希望所有项目都遵守同一条规则。

DSH 侧由 `@deepseek-ai/dsh-agent-instructions` 读取并用 `maxBytes: 65536` 截断。注意组合后的配置里这个行会出现 4 次：顶层那份是 `disabled: true`，真正生效的是 agent preset 内的三份。所以如果 AGENTS.md 没有被读进来，不要去 `cordis.patch.yml` 里"打开"顶层行——先确认文件层级和大小上限。

### 3.2 字体

本机 profile 只覆盖了字号（正文 15、代码 13、终端 14），没有覆盖字体族，所以字体文件不是迁移必需项。如果新电脑想复现旧机器的观感：

1. 打开资源包里的 `fonts` 目录，选中全部 `.ttf`，右键"为当前用户安装"。
2. 在 **设置 → 外观** 里选择字体族后再改字号。

字号是写在 profile 里的，字体族不是；只改字体族不会破坏 profile 校验。

---

## 4. 当前 DSH 配置

DSH 没有 `config.toml`。它的配置是**分层组合**出来的：profile 根 → bundle 层 → `cordis.patch.yml` 用户层 → `--patch` 覆盖层。这里只记录用户可控的部分。

### 4.1 核心设置摘要

| 配置项 | 当前值 | 迁移建议 |
|---|---|---|
| `DSH_HOME` | `%USERPROFILE%\.dsh` | 保留默认 |
| profile | `desktop` | 保留 |
| 默认 provider | `opencode-go`（`@deepseek-ai/dsh-llm-pi-ai`） | 保留名称，密钥重填 |
| 默认模型 | `deepseek-v4.1-flash` | 保留 |
| 上下文/输出上限 | 1000000 / 384000 | 保留 |
| 输入模态 | text、image | 保留 |
| `reasoningEffort` | `max` | 保留；也可按任务调低 |
| 凭据引用 | `apiKeyEnv: OPENCODE_GO_API_KEY` | 只迁移变量名，不迁移值 |
| 文件策略默认值 | `workspace-write`（由 `@deepseek-ai/dsh-sandbox-policy` 决定，可被 `DSH_PERMISSION_MODE` 覆盖） | 新电脑自行选择 |
| 本会话实测策略 | `danger-full-access`，审批关闭 | 高风险，按需保留 |
| 正文/代码/终端字号 | 15 / 13 / 14 | 保留 |
| 对话视图 | `transcriptView: detailed` | 保留 |
| 性能用量显示 | `performanceUsage: detailed` | 保留 |
| 账号面板 | `step: done`、`process: detailed`、`usage: detailed`、`developerTools: true` | 保留 |
| 界面语言 | `zh-CN`（`%APPDATA%\@deepseek-ai\dsh-desktop\desktop\locale-cache`） | 由应用重新写入，不迁移 |

### 4.2 当前 `cordis.patch.yml` 的参考快照

下面是 `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml` 的完整内容。它不含任何密钥（密钥在 `.credentials.yaml` 里），可以安全地进仓库，但**不要把它当作可直接覆盖的文件**——新电脑的 profile 可能已有别的 patch 条目，应当按 `id` 合并而不是整文件替换。

```yaml
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config:
    provider: opencode-go
    model: deepseek-v4.1-flash
    reasoningEffort: max
- id: ui-settings-account
  name: "@deepseek-ai/dsh-client-ui-settings-account"
  config:
    version: 1
    step: done
    purpose: both
    process: detailed
    completion: completed
    usage: detailed
    developerTools: true
- id: ui-chat
  name: "@deepseek-ai/dsh-client-ui-chat"
  config:
    transcriptView: detailed
    performanceUsage: detailed
- id: ui-settings
  name: "@deepseek-ai/dsh-client-ui-settings"
  config:
    enabled: true
- id: ui-theme
  name: "@deepseek-ai/dsh-client-ui-theme"
  config:
    fontSize: 15
    codeFontSize: 13
    terminalFontSize: 14
- id: llm-pi-ai
  name: "@deepseek-ai/dsh-llm-pi-ai"
  config:
    providers:
      opencode-go:
        models:
          - id: deepseek-v4.1-flash
            name: DeepSeek V4.1 Flash
            contextWindow: 1000000
            maxTokens: 384000
            input:
              - text
              - image
        apiKeyEnv: OPENCODE_GO_API_KEY
```

profile 根的 `cordis.yml` 始终是一个空数组，注释里也写明了"编辑 `cordis.patch.yml`，不要改这个文件"：

```yaml
# dsh profile root — an empty entry list. The tree is composed as patches:
# each bundle in package.json's dsh.profile.bundles, then cordis.patch.yml, then any
# --patch overlays. Edit cordis.patch.yml, not this file.
[]
```

`web` profile 的用户层多配了三个模型（本机用于对比不同后端）：

```yaml
- id: llm-pi-ai
  config:
    providers:
      opencode-go:
        models:
        - id: deepseek-v4-pro
          name: DeepSeek V4 Pro (New)
          contextWindow: 1000000
          maxTokens: 384000
          input:
          - text
        - id: deepseek-v4.1-flash
          name: DeepSeek V4.1 Flash
          contextWindow: 1000000
          maxTokens: 384000
          input:
          - text
          - image
        - id: glm-5.3
          name: GLM-5.3
          contextWindow: 1000000
          maxTokens: 131072
          input:
          - text
          - image
        - id: glm-5.3-flash
          name: GLM-5.3-Flash
          contextWindow: 1000000
          maxTokens: 131072
          input:
          - text
          - image
        apiKeyEnv: OPENCODE_GO_API_KEY
```

重要说明：

- patch 条目是"按 `id` 定向覆盖"的，`name` 要和该 id 对应的模块一致；写错 `name` 会导致该行加载失败，而不是静默忽略。
- patch 里允许 `!!js` 表达式（composed 配置里 `sandbox-policy.mode` 就是 `process.env.DSH_PERMISSION_MODE ?? 'workspace-write'`）。用户层尽量只用字面量，便于迁移时审查。
- 只改 `ui-theme` 的字号、`agent-default-model` 的模型、`llm-pi-ai` 的 provider 目录，是这套配置里最稳定的三处。其余 `ui-*` 条目是界面面板的展开状态，可以照抄也可以让应用重新生成。

### 4.3 新电脑使用的便携 `cordis.patch.yml` 模板

在新电脑上先启动一次应用，确认 `profiles\desktop\cordis.patch.yml` 已存在；然后**按 `id` 合并**下列条目（同一个 id 以你的值为准，新增 id 直接追加），不要整文件覆盖。

```yaml
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config:
    provider: opencode-go
    model: deepseek-v4.1-flash
    reasoningEffort: max
- id: ui-theme
  name: "@deepseek-ai/dsh-client-ui-theme"
  config:
    fontSize: 15
    codeFontSize: 13
    terminalFontSize: 14
- id: ui-chat
  name: "@deepseek-ai/dsh-client-ui-chat"
  config:
    transcriptView: detailed
    performanceUsage: detailed
- id: llm-pi-ai
  name: "@deepseek-ai/dsh-llm-pi-ai"
  config:
    providers:
      opencode-go:
        models:
          - id: deepseek-v4.1-flash
            name: DeepSeek V4.1 Flash
            contextWindow: 1000000
            maxTokens: 384000
            input:
              - text
              - image
        apiKeyEnv: OPENCODE_GO_API_KEY
```

模板故意省略了以下内容：

- `ui-settings-account` 面板状态：让应用重新初始化即可。
- `ui-settings.enabled`：默认已启用。
- 任何 `DSH_PERMISSION_MODE`、`sandbox-policy`、`approval` 覆盖：这些是安全相关项，应由新电脑显式选择，而不是从旧机器继承。
- `.credentials.yaml`、`storages`、`sessions`：见第 1.2 节。

保存后不要重启应用，先做一次"离线语法与合并校验"。`desktop` profile 不允许 CLI 启动，但可以把它的 patch 叠加到 `web` profile 上试组合：

```powershell
$dsh    = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
$patch  = Join-Path $env:USERPROFILE '.dsh\profiles\desktop\cordis.patch.yml'
$dump   = Join-Path $env:TEMP 'dsh-composed-check.txt'

& $dsh --profile web --patch $patch --dump-config 2>&1 | Out-File -FilePath $dump -Encoding utf8
"exit=$LASTEXITCODE"
Select-String -LiteralPath $dump -Pattern 'provider: opencode-go|reasoningEffort: max|fontSize' |
  ForEach-Object { "$($_.LineNumber): $($_.Line.Trim())" }
```

预期：退出码为 0，且能同时看到 `provider: opencode-go`、`reasoningEffort: max` 和 `fontSize: 15`。如果 CLI 报错，说明 YAML 语法或 `id`/`name` 对应关系有误，此时应用内也不会生效。

### 4.4 模型 provider 与凭据

DSH 把"provider 目录"和"密钥"彻底分开：

- **provider 目录**写在 profile 的用户层（`llm-pi-ai.config.providers`），是明文、可进仓库。
- **密钥**不写进 profile，只用 `apiKeyEnv: OPENCODE_GO_API_KEY` 声明变量名；真实值由 `@deepseek-ai/dsh-credentials-local` 保存在 `%USERPROFILE%\.dsh\.credentials.yaml`。

本机 `.credentials.yaml` 的结构（**值已全部脱敏，不要把真实文件内容贴进仓库**）：

```yaml
version: 1
records:
  client-connection/browser-session:      # 本地 Web 界面的浏览器会话授权
    kind: grant
    payload:
      version: 1
      secret: <BROWSER_SESSION_SECRET>
  deepseek-account-platform/device:       # 设备标识
    kind: grant
    payload:
      id: <DEVICE_ID>
  deepseek-account-platform/default:      # DeepSeek 账号登录态
    kind: grant
    payload:
      version: 1
      token: <ACCOUNT_TOKEN>
      issuer: https://platform.deepseek.com
refs:
  OPENCODE_GO_API_KEY: <OPENCODE_GO_API_KEY>
```

迁移要点：

- 新电脑在 **设置 → 模型** 里重新录入 key，让应用自己写 `refs`。
- 不要手工把旧 `refs` 粘到新文件里；设备标识和浏览器会话授权都与本机相关。
- `client-connection/browser-session` 丢了会导致本地 Web 界面直接返回 `401 未经授权`（本机用 `Invoke-WebRequest` 访问 `http://127.0.0.1:60694` 就是 401）。正确做法是从应用窗口打开界面，而不是手拼 URL。
- 如果怀疑旧机器的 `.credentials.yaml` 曾进入共享目录或压缩包，请在 provider 控制台轮换 key，而不是只删文件。

---

## 5. 插件与 bundle（DSH 特有）

这是 DSH 和 Codex 差别最大的地方，务必读完再动手。

### 5.1 三层结构：profile、bundle、patch

```text
%DSH_HOME%\profiles\<profile>\
├── cordis.yml            # profile 根：空数组 []，永远不要编辑
├── package.json          # 依赖 + dsh.profile.bundles（bundle 的加载顺序）
├── pnpm-workspace.yaml   # 该 profile 是一个独立 pnpm 工作区
├── pnpm-lock.yaml         # 依赖锁
├── cordis.patch.yml      # ★ 你的用户层：按 id 定向覆盖
├── node_modules\         # 安装产物，不迁移
├── .plugin-manager\      # 插件安装日志，不迁移
└── .dsh-skin-market\     # 皮肤市场缓存，不迁移
```

组合顺序是固定的：

1. `cordis.yml` 的空根；
2. `package.json` 里 `dsh.profile.bundles` 依次叠加的每个 bundle 层；
3. `cordis.patch.yml` 用户层；
4. 命令行 `--patch <path>` 的额外覆盖层（可重复）。

所以"装了一个插件"在 DSH 里意味着两件事：`node_modules` 里有这个包，**并且**它出现在 `dsh.profile.bundles` 里。只做前者不会生效。

bundle 里的每个"插件"本质上是一个 cordis 行（row）：`id` + `name`（npm 模块）+ `config`。同名的 row 在不同 profile 里重复出现是正常的——组合后的配置里 `skill-filesystem` 就出现了 4 次，每次指向不同的技能根。

### 5.2 本机启用的 8 个 bundle

| bundle | 版本 | 来源 | 作用 | 迁移方式 |
|---|---:|---|---|---|
| `@deepseek-ai/dsh-base` | `0.2.2-rc.1` | 应用内置 | 核心层：LLM、会话、沙箱、审批、工具、技能、goal、workflow、subagent、MCP 资源 | 随应用，不要复制 |
| `@deepseek-ai/dsh-web-app` | `0.2.2-rc.1` | 应用内置 | 浏览器面：HTTP/API、UI 组件、终端、文件树、schedule、插件管理器 | 随应用，不要复制 |
| `dsh-codex-effort-slider` | `1.1.4` | npm | 把推理等级选择换成一条可拖动的连续滑条 | 重装 |
| `dsh-skin-market` | `0.1.81` | npm | 皮肤/主题市场与生命周期管理 | 重装 |
| `@changfenhuang/dsh-genui` | `0.16.0` | npm | GenUI：`dsh-ui` 代码块内联渲染交互界面 | 重装 |
| `dsh-ppt` | `0.20.5` | npm | 演示文稿三件套：HTML 放映 + 可编辑 PPTX + JSON 工程 | 重装 |
| `dsh-hyperframes` | `0.11.5` | npm | HTML→视频工作台（23 个技能 + 工程/渲染工具） | 重装 |
| `dsh-answer-me-with-html` | `0.5.0` | npm | 只用技能、不加工具的 bundle：一页 HTML 回答 | 重装 |

`dsh.profile.bundles` 的实际顺序（顺序即叠加顺序）：

```json
{
  "name": "dsh-profile-desktop",
  "private": true,
  "dependencies": {
    "@changfenhuang/dsh-genui": "0.16.0",
    "dsh-answer-me-with-html": "0.5.0",
    "dsh-codex-effort-slider": "1.1.4",
    "dsh-hyperframes": "0.11.5",
    "dsh-ppt": "0.20.5",
    "dsh-skin-market": "0.1.81"
  },
  "dsh": {
    "profile": {
      "bundles": [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-web-app",
        "dsh-codex-effort-slider",
        "dsh-skin-market",
        "@changfenhuang/dsh-genui",
        "dsh-ppt",
        "dsh-hyperframes",
        "dsh-answer-me-with-html"
      ]
    }
  }
}
```

### 5.3 安装命令与两条路径的差别

**推荐：用应用内的 设置 → 插件。** 它会同时改 `dependencies`、`dsh.profile.bundles`，并用应用自带的 pnpm 安装，然后把结果写进 `.plugin-manager\logs`。

**命令行只改依赖，不改 bundle 清单**，所以下面的命令装完之后仍要手工把包名加进 `dsh.profile.bundles`，否则不会加载：

```powershell
$dsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'

& $dsh --version
& $dsh plugin --profile desktop list --depth 0     # 查看已装依赖
& $dsh plugin --profile desktop add dsh-ppt@0.20.5 # 只装包
```

注意几个 CLI 的边界：

- `dsh --profile desktop --dump-config` 会失败并提示 `profile "desktop" is managed exclusively by the Electron application`。**desktop profile 不能由 CLI 启动**，只能用桌面应用；第 4.3 节那个用 `web` 校验 patch 的办法是唯一可行的离线检查手段。
- `dsh plugin --profile desktop ...` 只是把参数转发给该 profile 目录下的 pnpm，所以 `list`/`add`/`remove`/`why` 都能用。
- `dsh --from-default-profile <name>` 会用随应用发布的模板重建一个 profile，出问题时比手改更快。
- CLI 默认不在 PATH 上（本机 `HKCU\Software\DeepSeekHarness\Command` 不存在，`where dsh` 找不到）。需要在应用设置里启用命令行，或直接使用上面的完整路径。

### 5.4 19 个内置但未启用的 bundle

这些包随应用发布，默认关闭。装之前请知情：实验包会改工具面或界面，出问题用 `--from-default-profile` 重建 profile。

| bundle | 类型 | 作用 |
|---|---|---|
| `@deepseek-ai/dsh-headless` | 运行模式 | 一次性任务：只跑 core Agent/Session，没有 Host、HTTP、浏览器层 |
| `@deepseek-ai/dsh-acp-app` | 运行模式 | ACP：JSON-RPC stdio + 进程生命周期 |
| `@deepseek-ai/dsh-sdk-app` | 运行模式 | SDK：stdio JSON-RPC 服务，附 `skill-office`、`present`、`schedule`、`ask-user` 工具 |
| `@deepseek-ai/dsh-sdk-minimal` | 运行模式 | 最小 SDK：JSON-RPC + 单个 DeepSeek 适配器 + 持久 shell |
| `@deepseek-ai/dsh-experimental-agent-team-profile` | 实验 | Agent Teams 协作、工具与 Web UI |
| `@deepseek-ai/dsh-experimental-inspector-profile` | 实验 | 会话原始日志与 Chat 节点检查器 |
| `@deepseek-ai/dsh-experimental-terminal-bundle` | 实验 | 让 shell 进程跨工具调用保活 |
| `@deepseek-ai/dsh-experimental-voice-input-bundle` | 实验 | 本地 SenseVoice 语音输入（首次使用下载运行时） |
| `@deepseek-ai/dsh-experimental-cot-translation-bundle` | 实验 | 推理过程的机器翻译 |
| `@deepseek-ai/dsh-experimental-auto-review` | 实验 | Auto 权限预设下的逐工具 LLM 授权审查 |
| `@deepseek-ai/dsh-experimental-session-search` | 实验 | 检索历史会话的工具 |
| `@deepseek-ai/dsh-experimental-session-titles-bundle` | 实验 | 每条人类消息到来时刷新会话标题 |
| `@deepseek-ai/dsh-experimental-tool-worktree` | 实验 | 创建并进入 Git worktree 的工具 |
| `@deepseek-ai/dsh-experimental-forge-bundle` | 实验 | Git 仓库的变更请求面板 + worktree 选项 |
| `@deepseek-ai/dsh-experimental-liveshare` | 实验 | 通过 Relay 分享会话（只读或有界写入） |
| `@deepseek-ai/dsh-experimental-plugin-market-bundle` | 实验 | 自定义插件索引的 Discover 浏览/安装 |
| `@deepseek-ai/dsh-experimental-ralph-bundle` | 实验 | 用全新 agent 重复执行显式要求的循环工作 |
| `@deepseek-ai/dsh-experimental-badge-skill-bundle` | 实验 | 让 agent 在产物里加 "powered by dsh" 徽标 |
| `@deepseek-ai/dsh-personalized-recommendations` | 可选 | 回答下方的个性化页面与插件推荐卡片 |

另有 3 个只在目录里出现、本机装不上：`@deepseek-ai/dsh-subagent-claude-code`、`@deepseek-ai/dsh-subagent-codex`（`availability: missing`），以及 `@deepseek-ai/dsh-cua-bundle`（报 `unsupported-platform`，Windows 上当前不可用）。

### 5.5 六个第三方插件的能力说明

#### `dsh-ppt` 0.20.5

- **工具面**：`ppt_create`、`ppt_edit`、`ppt_check`、`ppt_render`、`ppt_undo`、`ppt_data`、`ppt_themes`、`ppt_templates`。
- **产物**：一次生成三件套——独立 HTML 放映页、可编辑 PPTX、dsh-ppt JSON 工程；后续修改都基于 JSON 工程，能撤销。
- **渲染**：`ppt_render` 依赖 `@deepseek-ai/libreoffice-kit@0.1.5`（应用里已 unpack，win32-x64），输出逐页 PNG/PDF 并报告缺失字体；装不上时普通建卡流程仍可用。
- **技能**：`dsh-ppt`。
- **迁移要点**：工程文件是普通文件，跟着工作区走；插件本身重装即可。主题、模板是只读参考，不需要迁移。

#### `dsh-hyperframes` 0.11.5

- **工具面**：`hyperframes_project`（建/读受管理工程）、`hyperframes_render`（准备环境、预览、渲染 MP4、查询/取消任务）、`hyperframes_health`（校验技能文件与宿主注册状态）。
- **技能面**：这是本机技能最多的插件，21 个，覆盖 `hyperframes`（总入口）、`hyperframes-cli`、`hyperframes-registry`、`media-use`、`figma`、`slideshow`、`remotion-to-hyperframes`，以及 14 个兼容入口（见 6.2）。
- **数据**：工程在 `%DSH_HOME%\data\dsh-hyperframes\projects`，这是用户内容，可以迁移；但它不是缓存，删了就没了。
- **迁移要点**：首次准备渲染环境会下载依赖，所以新电脑第一次渲染一定比旧机器慢；`hyperframes_health` 可以用来确认技能是否重新注册成功。

#### `@changfenhuang/dsh-genui` 0.16.0

- **工具面**：`render_ui`（工具行卡片）、`validate_dsh_ui`（校验 ```dsh-ui 代码块 JSON）。
- **协议**：回答正文里的 ```dsh-ui 围栏 + 固定组件词表（布局/展示/图表/交互/高级五类）。组件带 `action` 时，交互会以 `[genui-action]` 回传，触发重渲染。
- **技能**：`genui`。
- **迁移要点**：组件词表和 schema 随版本变化。旧机器生成的页面不要跨版本复用；升级后以 `validate_dsh_ui` 的返回为准。

#### `dsh-skin-market` 0.1.81

- **作用**：原生皮肤市场与生命周期管理，浏览/安装社区主题。
- **缓存**：`%DSH_HOME%\profiles\desktop\.dsh-skin-market\catalog.json`（约 3.3 MB）是市场索引缓存，含大量社区包名、版本、integrity 和评分；**不要迁移**，首次打开市场会重建。
- **迁移要点**：已安装的皮肤包本身是普通依赖，会出现在 profile 的 `dependencies` 里；只迁 profile 清单，缓存让新机器重新拉。

#### `dsh-codex-effort-slider` 1.1.4

- **作用**：纯 UI 插件，把输入框工具行的推理等级档位换成一条连续滑条（Codex 风格）。
- **迁移要点**：不提供工具和技能。真正的默认等级仍由 `agent-default-model.config.reasoningEffort` 决定，滑条只是改运行时的值。

#### `dsh-answer-me-with-html` 0.5.0

- **作用**：只注册技能、不加工具的 bundle，回答复杂问题时产出一页视觉 HTML。
- **技能**：`answer-me-with-html`，在该 bundle 里通过第二个 `@deepseek-ai/dsh-skill-filesystem` 行（row id `answer-me-with-html-skill`）挂载自己的 `skills/` 目录。
- **迁移要点**：本机同时在 `%USERPROFILE%\.agents\skills\answer-me-with-html` 有一份共享副本。DSH 侧由 bundle 提供，bundle 是权威来源；共享副本保留无害，但在确认技能发现优先级之前不要删。

### 5.6 最容易误判的三点

1. **"装了包"不等于"启用了插件"**：`dependencies` 决定文件在不在，`dsh.profile.bundles` 决定加载不加载。
2. **`enabled: false` 不等于坏了**：很多行是条件启用，例如 base 层的 `tool-plugin-manager` 是 `disabled: !!js '!ctx.get('profileContext')'`，只有在应用/profile 上下文里才出现。看到 `enabled:false` 先看它的 `disabled` 表达式，不要急着改。
3. **`bash-sandbox` 在 Windows 上是禁用的**（`disabled: !!js process.platform === 'win32'`），实际生效的是 `pwsh-sandbox`。所以 Windows 上的沙箱问题会表现为 PowerShell 命令失败，而 bash 相关配置怎么改都没用。

---

## 6. 技能清单

DSH 的技能来自三个根，按优先级各自独立注册：

1. **应用自带技能**：随安装目录发布，例如 `resources\runtime\office-skills\*`。
2. **bundle 自带技能**：每个 bundle 通过自己的 `@deepseek-ai/dsh-skill-filesystem` 行声明 `skills/` 目录；另外核心层还有一个 `customSkillDirs` 指向 `@deepseek-ai/dsh-agent-preset/skills`。
3. **共享技能目录**：`%USERPROFILE%\.agents\skills`，由跨工具的技能安装器维护。

### 6.1 应用自带的 7 个 office 技能

位于安装目录 `resources\runtime\office-skills\`，随应用升级，不要复制：

| 技能 | 作用 |
|---|---|
| `office` | Office 文档工作流总入口，按任务路由到下面的细分技能 |
| `office-docx` | 创建、读取、编辑、校验 Word 文档 |
| `office-xlsx` | 读取、创建、编辑、校验 Excel 工作簿、数据与公式 |
| `office-pptx` | 创建、读取、编辑、校验 PowerPoint 演示文稿 |
| `office-render` | 用 LibreOffice Kit 渲染文档图片、检查视觉版式 |
| `office-export-pdf` | 把 Office 文档转成 PDF |
| `office-recalculate` | 刷新表格公式缓存并核验计算值 |

后三个依赖应用里的 `@deepseek-ai/libreoffice-kit@0.1.5`（win32-x64 已 unpack），不需要额外装系统 LibreOffice。

### 6.2 bundle 自带的 24 个技能

| bundle | 技能 | 数量 |
|---|---|---:|
| `dsh-hyperframes` | 真实技能：`hyperframes`、`hyperframes-cli`、`hyperframes-registry`、`media-use`、`figma`、`slideshow`、`remotion-to-hyperframes` | 7 |
| `dsh-hyperframes` | 兼容入口：`hyperframes-animation`、`hyperframes-audio`、`hyperframes-core`、`hyperframes-creative`、`hyperframes-keyframes`、`hyperframes-studio`、`motion-graphics`、`music-to-video`、`pr-to-video`、`product-launch-video`、`faceless-explainer`、`talking-head-recut`、`embedded-captions`、`general-video` | 14 |
| `dsh-ppt` | `dsh-ppt` | 1 |
| `@changfenhuang/dsh-genui` | `genui` | 1 |
| `dsh-answer-me-with-html` | `answer-me-with-html` | 1 |

那 14 个是**兼容入口**，SKILL.md 里明确写着"已退役技能 X 的入口，路由到当前官方技能"（大部分路由到 `hyperframes`，`hyperframes-audio` 路由到 `media-use`，`hyperframes-studio` 路由到 `hyperframes-cli`）。不要因为目录名"过时"就删掉它们——旧引用会命中这些入口。

`dsh-skin-market` 和 `dsh-codex-effort-slider` 不注册技能，它们是纯 UI 插件。

### 6.3 共享技能目录

```text
%USERPROFILE%\.agents\skills\
└── answer-me-with-html\
%USERPROFILE%\.agents\.skill-lock.json
```

`.skill-lock.json` 记录来源、安装方式和目录哈希，不是密钥，可以复制：

```json
{
  "version": 3,
  "skills": {
    "answer-me-with-html": {
      "source": "QingYunA/answer-me-with-html",
      "sourceType": "github",
      "sourceUrl": "https://github.com/QingYunA/answer-me-with-html.git",
      "skillPath": "skills/answer-me-with-html/SKILL.md",
      "skillFolderHash": "8007aad826a73cd28b6cbcb697cd1459a88b0bf0",
      "installMode": "copy",
      "installedAt": "2026-11-11T13:32:41.933Z",
      "updatedAt": "2026-11-11T13:32:41.933Z"
    }
  },
  "dismissed": {}
}
```

### 6.4 调用方式

在新会话里，技能既可以由模型通过 `skill` 工具加载，也可以由用户显式点名：

```text
Use the genui skill to render a comparison table.
用 dsh-ppt 把这份 Markdown 做成 12 页的汇报。
Use the hyperframes skill to make a 15-second title card.
```

验收时优先试这三个：`genui`（有没有 ```dsh-ui 渲染）、`dsh-ppt`（有没有 `ppt_create` 工具）、`office-docx`（有没有 Word 工作流）。三者分别覆盖"bundle 技能 + 工具"、"bundle 技能 + 多工具"、"应用自带技能"三种来源。

---

## 7. MCP 与工具面

### 7.1 本机没有配置任何 MCP server

这是与 Codex 手册最容易搞混的一点：**本机 DSH 没有 MCP server 配置**。`cordis.patch.yml` 里没有 MCP 段，composed 配置里只有 `@deepseek-ai/dsh-mcp-resources`（把 MCP 资源桥接进上下文的插件），没有 `mcp_servers` 之类的服务器清单。

所以：

- 不存在"从旧机器复制的 MCP 路径"这类问题，也没有 `codex mcp list` 的对应物。
- DSH 的能力来自 bundle 内的原生工具，而不是外挂 MCP 进程。
- 如果新电脑需要 MCP，应当在那个 profile 里新增对应插件行，并把配置写进 `cordis.patch.yml`——不要去找旧机器的路径。

### 7.2 本机可见的工具族

| 来源 | 工具 | 说明 |
|---|---|---|
| base | `pwsh`、`bash`、`read`、`write`、`edit`、`glob`、`grep` | 命令执行与文件读写；Windows 上 `bash` 沙箱禁用 |
| base | `todo_write`、`ask_user_question`、`present` | 计划、追问、交付文件声明 |
| base | `create_goal`、`get_goal`、`update_goal` | 跨轮次目标，自动续跑 |
| base | `subagent`、`subagent_fork`、`list_agents`、`send_message`、`interrupt_agent` | 子代理 |
| base | `workflow` | 用 JS 脚本编排大量子代理 |
| base | `web_fetch` | 抓取网页 |
| base | `skill`、`plugin_manager` | 技能加载、插件/ bundle 管理 |
| base | `job_list`、`job_output`、`job_kill` | 后台作业 |
| web-app | `schedule_create`、`schedule_edit`、`schedule_list`、`schedule_view` | 定时任务 |
| web-app | `working_directory` | 切换会话工作目录 |
| genui | `render_ui`、`validate_dsh_ui` | 交互界面渲染与校验 |
| dsh-ppt | `ppt_create`、`ppt_edit`、`ppt_check`、`ppt_render`、`ppt_undo`、`ppt_data`、`ppt_themes`、`ppt_templates` | 演示文稿 |
| dsh-hyperframes | `hyperframes_project`、`hyperframes_render`、`hyperframes_health` | 视频工程与渲染 |

### 7.3 迁移原则

- 不要复制任何工具路径、运行时路径或端口配置；它们由应用在启动时生成。
- `DSH_WEB_URL`（本机 `http://127.0.0.1:60694`）是每次启动重新分配的，不要写进任何配置。
- 工具面由 bundle 决定，所以"工具不见了"几乎总是"bundle 没启用"，而不是配置写错了。先看 设置 → 插件，再看 `cordis.patch.yml`。

---

## 8. 外观、字号与推理等级

### 8.1 写在 profile 里的外观项

| 设置 | 值 | 位置 |
|---|---|---|
| 正文字号 | `15` | `ui-theme.config.fontSize` |
| 代码字号 | `13` | `ui-theme.config.codeFontSize` |
| 终端字号 | `14` | `ui-theme.config.terminalFontSize` |
| 对话视图 | `detailed` | `ui-chat.config.transcriptView` |
| 性能用量 | `detailed` | `ui-chat.config.performanceUsage` |
| 账号面板步骤 | `done` | `ui-settings-account.config.step` |
| 账号面板用量 | `detailed` | `ui-settings-account.config.usage` |
| 开发者工具入口 | `true` | `ui-settings-account.config.developerTools` |

字体族不在 profile 里，由系统字体决定。皮肤/主题由 `dsh-skin-market` 管理，选择结果不在本文档记录的 profile 字段中（本机没有单独的皮肤选择文件），从旧机器复制市场缓存的 `catalog.json` 也复现不了选择——重新在市场里挑一次即可。

### 8.2 推理等级

当前 `reasoningEffort: max`，可用的档位由 provider 目录和 `dsh-codex-effort-slider` 共同决定。注意：

- `reasoningEffort` 的**默认值**写在 `agent-default-model` 里，是持久配置。
- **滑条**只是改运行时的值，重启后回到默认。
- 如果 provider 不接受某个档位（常见于自定义 provider），会返回 400 或配置拒绝；此时把 `agent-default-model.model` 对应的 `reasoningEffort` 改回 `max`、`high` 或更低的档位，再重启。

### 8.3 界面语言

`zh-CN`，记录在 `%APPDATA%\@deepseek-ai\dsh-desktop\desktop\locale-cache`（6 字节，就是 `zh-CN`）。这属于 Electron 用户数据，不迁移；新电脑在 设置 → 通用 里选一次即可。

---

## 9. 外部依赖基线

### 9.1 应用自带运行时（不要复制，重新生成）

`%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\`：

| 组件 | 版本 | 位置 |
|---|---|---|
| Python | `3.12.14` | `dependencies\python\python.exe` |
| Node.js | `24.21.0` | `dependencies\node\bin\node.exe` |
| pnpm | `11.28.5` | `dependencies\pnpm\bin\pnpm.mjs` |

Python 站点包（`dependencies\python\Lib\site-packages`）：

```text
numpy 2.3.5            pandas 3.0.1          python-dateutil 2.9.0.post0
six 1.17.0             tzdata 2025.2         python-docx 1.2.0
python-pptx 1.0.2      openpyxl 3.1.5        Pillow 12.3.0
lxml 6.1.3             XlsxWriter 3.2.9      typing_extensions 4.16.0
et_xmlfile 2.0.0
```

Office 渲染引擎：`@deepseek-ai/libreoffice-kit@0.1.5` + `@deepseek-ai/libreoffice-kit-win32-x64@0.1.5`，位于 `resources\app.asar.unpacked\dsh\node_modules\`，被 `ppt_render` 和 `office-render`/`office-export-pdf` 使用。

`runtime.json` 里还有 `payloadDigest` 和 `desktopVersion: 0.2.1-rc.5`，两者都是应用管理的标识，复制到新机器没有意义。

### 9.2 本机系统工具

| 依赖 | 当前状态 | 说明 |
|---|---|---|
| PowerShell | Windows 自带，`pwsh` | 本文档所有命令 |
| Node.js | `C:\Program Files\nodejs\node.exe` | 系统 Node，与内置运行时并存 |
| npm | `C:\Program Files\nodejs\npm.ps1` | 系统 npm |
| pnpm | 不在 PATH 上 | 插件安装用应用内置的那个（`dependencies\pnpm`） |
| Python | `%USERPROFILE%\.local\bin\python.exe` | 用户级 Python，与内置 3.12 并存 |
| Git | `C:\Program Files\Git\cmd\git.exe` | 仓库操作、技能安装 |
| ripgrep | 不在 PATH 上 | 文件搜索由内置实现提供，不依赖系统 `rg` |
| 系统 LibreOffice | 未使用 | Office 转换用内置 LibreOffice Kit |
| 系统 TeX / R / Pandoc | 未检查 | 本机工作流不需要；若某技能要求，另装并单独验证 |
| CC Switch | 用于 profile 同步 | 记录 `%USERPROFILE%\.dsh\.cc-switch-profile-sync.json`，内容为 `["web","desktop"]` |

新电脑建议检查：

```powershell
$dsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'
& $dsh --version
node --version
python --version
git --version
```

`dsh` 不在 PATH 上是默认状态，不代表安装失败。用完整路径，或在应用设置里启用命令行后再直接调用 `dsh`。

---

## 10. 本地工作区和会话

### 10.1 当前工作区

`%USERPROFILE%\.dsh\storages\workspace.json` 记录了 3 个工作区（**不要迁移这个文件**）：

| 工作区 | 路径 | 会话数 |
|---|---|---:|
| `MasterGraduationProject` | `C:\workspace\2026Spring2Winter\MasterGraduationProject` | 5 |
| `default-workspace` | `C:\Users\<user>\Documents\deepseek-harness\default-workspace` | 9 |
| `fluid_experiment` | `C:\workspace\fluid_experiment` | 2 |

新电脑应通过 GUI 重新打开这些目录并确认权限提示。工作区根路径变化时保留新路径，不要强行复制旧路径。

### 10.2 会话存储布局

```text
%USERPROFILE%\.dsh\sessions\--C-workspace-2026Spring2Winter-MasterGraduationProject--\
└── session-<uuid>\
    └── session.v4.jsonl.zstd
```

目录名是工作区路径的编码，文件是压缩后的 v4 JSONL。本机共 16 个会话。这些全部属于"私有历史"，不迁移；新电脑从空白开始。

### 10.3 附件

`%USERPROFILE%\.dsh\attachments\v1\` 存放上传附件。不迁移。

---

## 11. 验收与排错

### 11.1 版本与 profile 检查

```powershell
$dsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'

& $dsh --version
& $dsh --help
& $dsh plugin --profile desktop list --depth 0
```

重点确认：

- 版本与桌面端一致（本机都是 `0.2.2-rc.1`）。
- `plugin list` 能列出 6 个第三方依赖及其版本。
- `--help` 里能看到 `--profile`、`--from-default-profile`、`--patch`、`--dump-config`。

### 11.2 patch 合并检查（离线）

```powershell
$patch = Join-Path $env:USERPROFILE '.dsh\profiles\desktop\cordis.patch.yml'
$dump  = Join-Path $env:TEMP 'dsh-composed-check.txt'
& $dsh --profile web --patch $patch --dump-config 2>&1 | Out-File -FilePath $dump -Encoding utf8
"exit=$LASTEXITCODE"
Select-String -LiteralPath $dump -Pattern 'provider: opencode-go|reasoningEffort: max|fontSize: 15' |
  ForEach-Object { "$($_.LineNumber): $($_.Line.Trim())" }
```

预期三项都能命中。命中但应用里不生效，说明是 bundle 没启用，而不是 patch 有问题。

### 11.3 目录检查

```powershell
$profileDir = Join-Path $env:USERPROFILE '.dsh\profiles\desktop'
Get-Content -LiteralPath (Join-Path $profileDir 'package.json') -Raw
Get-Content -LiteralPath (Join-Path $profileDir 'cordis.yml') -Raw
Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE '.agents\skills') -Directory | Select-Object -ExpandProperty Name
```

预期：

- `package.json` 的 `dsh.profile.bundles` 有 8 项。
- `cordis.yml` 仍是空数组 `[]`。
- `.agents\skills` 下有 `answer-me-with-html`。

### 11.4 功能 smoke test

打开新会话，依次测试：

1. 普通项目里发"只回复 OK"，确认 provider 鉴权和默认模型正常。
2. 让模型渲染一个对比表格，确认 `genui` 生效（正文里应出现 ```dsh-ui 渲染块，而不是一段被丢弃的 JSON）。
3. 用 `dsh-ppt` 把一段 Markdown 做成 3 页，确认 `ppt_create` 与 `ppt_check` 可用。
4. 用 `office-docx` 生成一个最小 Word 文档，确认应用自带技能被发现。
5. 需要视频时再试 `hyperframes_project`（首次会下载渲染依赖，慢是正常的）。

### 11.5 常见问题

| 现象 | 优先检查 |
|---|---|
| 网页界面返回 `401 未经授权` | `.credentials.yaml` 里缺 `client-connection/browser-session`，或你是手拼 URL；从应用窗口打开 |
| `profile "desktop" is managed exclusively by the Electron application` | 正常现象：desktop profile 只能由应用启动，CLI 只能做 `plugin list/add` |
| 装了包但插件没生效 | 包名没加进 `dsh.profile.bundles`；或应用没重启 |
| 插件安装失败 | 应用内置 pnpm 是否可用；`.plugin-manager\logs` 里的 pnpm 日志 |
| 沙箱报 `SetNamedSecurityInfoW failed (Win32 5): grantWrite(<workspace>)` | Windows 文件权限挡住了沙箱授权：工作区目录缺 `WRITE_OWNER`。用沙箱 ACL 修复流程处理，不要关沙箱绕过 |
| 沙箱报其他拒绝 | Windows 上生效的是 `pwsh-sandbox`；`bash-sandbox` 本来就被禁用，改它没用 |
| 模型返回 401/403 | `refs` 里是否已有 `OPENCODE_GO_API_KEY`；`apiKeyEnv` 名字是否与 `refs` 键一致 |
| 模型返回 400 | `reasoningEffort` 档位不被 provider 接受，改回 `max`/`high` |
| 技能不可见 | 对应 bundle 是否启用；是否开了新会话；是否只复制了 `SKILL.md` 而漏了 `references/` |
| 主题/皮肤丢失 | 正常：皮肤选择不随 profile 迁移，重新在市场里选 |
| `catalog.json` 缺失 | 正常：皮肤市场首次打开时重建 |
| 工作区列表为空 | 正常：`storages\workspace.json` 不迁移，用 GUI 重新打开目录 |

---

## 12. 参考

- 应用内文档与更新通道：`resources\app-update.yml`（`channel: nightly`，`https://download.deepseek.com/dsh-desk/feeds/win-x64/`）
- dsh CLI 自带帮助：`dsh --help`、`dsh web --help`、`dsh plugin --help`、`dsh --dump-config-schema`
- bundle 与 row 的权威来源：应用内 设置 → 插件（对应 `plugin_manager` 的 `list_bundles` / `list_plugins`）
- 六个第三方 bundle 的 npm 包页：
  - <https://www.npmjs.com/package/dsh-ppt>
  - <https://www.npmjs.com/package/dsh-hyperframes>
  - <https://www.npmjs.com/package/dsh-skin-market>
  - <https://www.npmjs.com/package/dsh-codex-effort-slider>
  - <https://www.npmjs.com/package/dsh-answer-me-with-html>
  - <https://www.npmjs.com/package/@changfenhuang/dsh-genui>
- `answer-me-with-html` 上游：<https://github.com/QingYunA/answer-me-with-html>

---

## 13. 最终安全边界

这份文档可以安全地作为迁移清单保存，但它不是凭据保险箱。任何时候都不要把以下内容写入 `harness/dsh.md` 或以未加密形式提交到 Git：

- `.credentials.yaml` 的任何 `secret` / `token` / `refs` 真实值；
- `<OPENCODE_GO_API_KEY>` 的实际 key；
- `sessions\**\session.v4.jsonl.zstd`、`attachments`、`storages\workspace.json`；
- `%APPDATA%\@deepseek-ai\dsh-desktop\**`（含 `Preferences`、`IndexedDB`、`Local Storage`、`plugin-operations`）；
- 旧机器的 hostname、IP、端口、SSH identity 和登录凭据；
- `.anonymous-user-id`。

补充两条本机专属提醒：

1. **文件策略的放宽要单独记录**。本机为了排查工作区权限问题，把会话切到了 `danger-full-access` 并关闭了审批提示。这与 `cordis.patch.yml` 无关，也不会被写进 profile；但它意味着"能用"不等于"配置正确"。新电脑的默认值仍是 `workspace-write`。
2. **遇到 `grantWrite` 失败不要关沙箱**。正确顺序是：先确认路径和权限对象，用沙箱 ACL 修复流程补齐 `WRITE_OWNER`/`WRITE_DAC`，验证后再重试原操作；修复前会留下可回退的备份脚本。把沙箱关掉只会把问题推到以后。

如果迁移过程中发现 `.credentials.yaml` 曾进入共享目录或压缩包，请在 provider 控制台轮换 key，而不是只删除文本。

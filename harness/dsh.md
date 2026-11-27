# DeepSeek Harness (DSH) Windows 本地配置迁移手册

> 非模型配置快照日期：2026-11-27（Asia/Shanghai）；具体模型和 provider 内容保留为 2026-11-19 历史快照，不作为当前配置依据；差异见第 14 节
> 源环境：Windows 10 专业版 22H2（19045）、DeepSeek Harness Desktop `0.2.2-rc.5`、内置 dsh CLI `0.2.2-rc.5`、profile `desktop`
> 目标环境：另一台 Windows 电脑
> 迁移范围：DSH profile（`desktop` / `web` / `acp`，bundle 层 + 用户 patch 层）、模型 provider 目录、插件 bundle、技能（应用自带 / bundle / 用户级）、AGENTS 规则、外观字号和必要依赖
> 不迁移：登录凭据、API token、会话、附件、工作区索引、插件缓存、语音模型缓存和皮肤目录缓存

本文档是一个快照，不是"把整个 `%USERPROFILE%\.dsh` 目录原样复制过去"的教程。DSH 的 `resources\runtime`（以及遗留的 `.dsh\dsh-runtimes`）、`node_modules`、`.plugin-manager`、`.dsh-skin-market` 和 `sessions` 都包含本机哈希、绝对路径或私有数据，必须让新电脑重新生成；`.credentials.yaml` 里是明文密钥，任何情况下都不能进入迁移包。

---

## 0. 一页式迁移清单

推荐顺序：

1. 在新电脑安装 DeepSeek Harness Desktop，至少启动一次并完成登录，让应用创建 `%USERPROFILE%\.dsh`。
2. 在旧电脑运行"第 2 节"的导出命令，生成不含密钥的迁移资源包。
3. 在新电脑运行"第 3 节"的恢复命令，复制共享技能、用户级技能与 AGENTS 规则。
4. 按"第 4.3 节"把 `cordis.patch.yml` 的用户层逐条合并进去，不要直接覆盖应用刚生成的 profile。
5. 在应用内 **设置 → 插件** 重装 10 个第三方 bundle（`ds-bot`、`dsh-ppt`、`dsh-hyperframes`、`genui`、`dsh-skin-market`、`dsh-codex-effort-slider`、`dsh-answer-me-with-html`、`dsh-context`、`agentero-dsh`、`dsh-better-sidebar`）。
6. 在 **设置 → 模型** 中按新电脑实际需要配置模型与凭据；本文原有具体 provider 配置属于历史快照，不应直接套用。
7. 用 GUI 重新打开本地工作区；不要复制旧机器的 `storages\workspace.json` 或 `sessions`。旧机器的 `C:\workspace` 已迁到 `Q:\workspace`，盘符变化时按新路径重新添加。
8. 运行"第 11 节"的验收命令。

最小验收标准：

- `dsh --version` 输出 `0.2.2-rc.5`（版本可不同，但要与桌面端一致）。
- `%USERPROFILE%\.dsh\profiles\desktop\package.json` 的 `dsh.profile.bundles` 有 20 项：2 个核心 bundle、10 个第三方 bundle 和 8 个内置实验/可选 bundle。
- `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml` 中需要的界面配置已按 `id` 合并；模型自行配置。
- 新会话的技能目录里能看到 `genui`、`dsh-ppt`、`hyperframes`、`office` 系列、`dsh-doc`、`paper-spine` 系列。
- 设置里的插件页显示 10 个第三方插件已启用且无加载错误。
- 源 profile 持久默认预设为 `danger-full-access` / `never`；迁移模板不复制该宽松默认值，新电脑自行选择。`never` 表示需要审批的操作直接拒绝，不是自动批准。
- Web 界面的侧边栏（文件、Git、终端、文件预览）可用。

---

## 1. 当前环境快照

| 项目 | 当前值 |
|---|---|
| 操作系统 | Windows 10 专业版 22H2，`10.0.19045`，64 位，中文系统 |
| 应用安装目录 | `%LOCALAPPDATA%\Programs\DeepSeek Harness` |
| 桌面端版本 | `0.2.2-rc.5`（文件版本 `0.2.2.0`） |
| dsh CLI | `0.2.2-rc.5` |
| DSH Home | `%USERPROFILE%\.dsh`（环境变量 `DSH_HOME`） |
| 当前 profile | `desktop`（环境变量 `DSH_PROFILE`） |
| profile 目录 | `%USERPROFILE%\.dsh\profiles\desktop`（`DSH_PROFILE_DIR`） |
| 其他 profile | `web`，只有 `cordis.patch.yml`，由 CLI 启动；`acp`（2026-11-19 新增），bundle 为 `dsh-base` + `dsh-acp-app`，供 ACP 客户端接入 |
| 默认 shell | PowerShell（`pwsh`） |
| 默认模型 provider（2026-11-19 历史值） | `opencode-go`，由 `@deepseek-ai/dsh-llm-pi-ai` 提供 |
| 默认模型（2026-11-19 历史值） | `deepseek-v4.1-flash`，`contextWindow` 1000000，`maxTokens` 384000，输入 text+image |
| 推理等级 | `high`（上一版快照为 `max`） |
| 追加 provider（历史值） | `k8s-15`（OpenAI 兼容内网端点，模型 `qwen3.8-27b`）、`muze-ai`（OpenAI Responses 端点，模型 `gpt-6-luna` / `gpt-6.1-terra` / `gpt-6.2-sol` / `gpt-6.2-astra`） |
| 凭据引用（历史值） | profile 里写 `apiKeyEnv`：`OPENCODE_GO_API_KEY`、`K8S_15_API_KEY`、`MUZE_AI_API_KEY`，真实密钥存于 `.credentials.yaml` 的 `refs`（仅作历史格式参考） |
| profile bundle 清单 | 20 个（2 个核心 + 10 个第三方 + 8 个内置实验/可选包）；清单不单独证明所有行已成功加载 |
| 内置未启用 bundle | 14 个（12 个可选包，其中 CUA 在 Windows 不可用；2 个仅目录可见） |
| 应用自带 office 技能 | 5 个（`office`、`office-docx`、`office-pptx`、`office-xlsx`、`office-tools`），以当前会话技能目录为准，来源未逐一核验 |
| agent-preset 打包技能 | 1 个（`dsh-doc`） |
| bundle 自带技能 | 26 个（`dsh-hyperframes` 23、`dsh-ppt` 1、`genui` 1、`dsh-answer-me-with-html` 1）；另有 DS Bot 的技能，见第 6 节 |
| 用户级技能目录 | `%USERPROFILE%\.dsh\skills`，11 个（`humanizer`、`i-have-adhd`、`manage-skills`、`paper-spine` 系列 6 个、`ppt-master`、`prompt-master`） |
| 共享技能目录 | `%USERPROFILE%\.agents\skills`，1 个（`answer-me-with-html`） |
| 工作区数量 | 3 个（2026-11-19 历史统计，本次未核验） |
| 会话数量 | 2026-11-19 历史统计；本次未核验，不迁移会话 |
| 界面语言 | `zh-CN` |
| 界面字号 | 正文 15、代码 13、终端 14 |
| 应用更新通道 | `nightly`，`https://download.deepseek.com/dsh-desk/feeds/win-x64/` |
| 打包运行时 | Python 3.12.14、Node.js 24.21.0、pnpm 11.28.5 |
| 权限预设（本会话） | `danger-full-access`；源 profile 也持久设置了同名默认预设 |
| 文件策略（本会话） | `danger-full-access` |
| 审批策略（本会话） | `never`（本机 profile 默认预设也是 `never`；需要审批的动作直接拒绝、不弹窗） |
| Web 界面地址 | 每次启动重新分配，不作为配置迁移 |

### 1.1 快照的边界

- 应用版本、bundle 版本和 `@deepseek-ai/*` 包版本会随更新变化。本文档记录当前机器上的版本，不是要求新电脑钉住这些版本。
- 新电脑的用户名、`%USERPROFILE%`、Web 端口、`client-connection/browser-session` 密钥和运行时载荷内容都不同。
- 打包运行时现在是应用目录下的 `resources\runtime\primary-runtime`（`runtime.json` 里有 `payloadDigest` 和 `desktopVersion`），随应用升级重建；`%USERPROFILE%\.dsh\dsh-runtimes` 里那份是旧版遗留（`desktopVersion: 0.2.2-rc.3`），两份都不要复制。
- `acp` profile 是 `0.2.2-rc.5` 起提供的第三种运行 profile（ACP 自动化接入），没有 GUI 设置页；桌面端只加载 `desktop` profile。
- 外观只有字号写在 profile 里；字体族由系统决定，本机没有在 patch 中覆盖字体，因此不涉及字体文件迁移。
- 权限预设的**默认选择**可持久写入 profile；本机 `permission.config.defaultPreset` 是 `danger-full-access`，配套 sandbox `danger-full-access` + approval `never`。单个会话还可有自己的选择，与 profile 默认值区分。迁移模板不复制这个宽松默认值；新电脑应知情后自行选择。

### 1.2 明确不迁移的内容

不要把下面这些内容放进迁移包，也不要提交到仓库：

- `%USERPROFILE%\.dsh\.credentials.yaml`：含 `secret` / `token` 明文和 `refs` 里的真实 API key。
- `%USERPROFILE%\.dsh\.anonymous-user-id`：本机匿名标识。
- `%USERPROFILE%\.dsh\sessions\**`：会话正文，`session.v4.jsonl.zstd` 是压缩后的完整对话。
- `%USERPROFILE%\.dsh\attachments\v1\**`：上传附件。
- `%USERPROFILE%\.dsh\storages\workspace.json`：工作区、会话归属和置顶/归档状态等本地私有元数据。
- `%USERPROFILE%\.dsh\storages\session_projcache\**`：会话投影缓存（含每条会话的权限/用量/费用明细）。
- `%USERPROFILE%\.dsh\storages\dsh-context\**`：上下文面板的跨会话总览缓存（`overview-cache.v1.json`）。
- `%USERPROFILE%\.dsh\dsh-runtimes\**`：旧版运行时载荷（应用现已改用 `resources\runtime`），不要复制。
- `%USERPROFILE%\.dsh\speech-to-text\**`：本地语音输入模型（SenseVoice），首次使用时重新下载。
- `%USERPROFILE%\.dsh\.paperspine-skills\**`：`paper-spine` 技能管理器的版本锁与 edition 状态，重新安装即可。
- `%USERPROFILE%\.dsh\profiles\desktop\node_modules\**`、`.pnpm`、`pnpm-lock.yaml` 之外的安装产物。
- `%USERPROFILE%\.dsh\profiles\desktop\.plugin-manager\logs\**`：插件安装日志。
- `%USERPROFILE%\.dsh\profiles\desktop\.dsh-skin-market\catalog.json`：皮肤/插件市场索引缓存（首次打开市场时生成，本机当前没有该目录）；不要迁移。
- `%USERPROFILE%\.dsh\profiles\desktop\stardustlc-plugin-update-cache.json`：更新检查缓存。
- `%APPDATA%\@deepseek-ai\dsh-desktop\**`：Electron 用户数据（`Preferences`、`IndexedDB`、`Local Storage`、`Cache`、`plugin-operations`、`logs`）。
- `%LOCALAPPDATA%\@deepseek-aidsh-desktop-updater\**`：更新器缓存。
- `%LOCALAPPDATA%\Agentero\**`：Agentero 独立 CLI 的安装目录，新电脑重新安装 CLI 即可。
- 任何个人对话、工作区文件、Agentero vault 内容和附件。

---

## 2. 旧电脑：生成迁移资源包

下面的命令只导出可迁移的用户资产，不复制 `.credentials.yaml` 或原始 patch，也不会主动带上会话或缓存。技能与工程目录仍可能包含用户数据或秘密，压缩前必须自行检查。脚本在压缩前暂停，确认无误后才继续。请在旧电脑的 PowerShell 中运行。

```powershell
$ErrorActionPreference = 'Stop'

$dshHome    = Join-Path $env:USERPROFILE '.dsh'
$profileDir = Join-Path $dshHome 'profiles\desktop'
$agentsHome = Join-Path $env:USERPROFILE '.agents'
$stamp      = Get-Date -Format 'yyyyMMdd-HHmmss'
$bundleRoot = Join-Path ([Environment]::GetFolderPath('Desktop')) "dsh-migration-$stamp"

foreach ($sub in 'desktop-profile', 'web-profile', 'acp-profile', 'agents-skills', 'dsh-skills', 'fonts') {
  New-Item -ItemType Directory -Path (Join-Path $bundleRoot $sub) -Force | Out-Null
}

# 1) profile 用户层：patch、bundle 清单、依赖版本快照
# 不自动导出 patch：可能含 provider 地址、凭据或其他私人配置。
# 如需留档，先人工筛选、脱敏后再放入 desktop-profile。
Copy-Item -LiteralPath (Join-Path $profileDir 'package.json')       -Destination (Join-Path $bundleRoot 'desktop-profile') -Force
Copy-Item -LiteralPath (Join-Path $profileDir 'pnpm-lock.yaml')     -Destination (Join-Path $bundleRoot 'desktop-profile') -Force
Copy-Item -LiteralPath (Join-Path $profileDir 'pnpm-workspace.yaml') -Destination (Join-Path $bundleRoot 'desktop-profile') -Force

# 2) web / acp patch 同样不自动复制；如需迁移，先人工审查和脱敏。

# 3) 共享技能注册信息（.skill-lock.json 只记录来源和哈希，不是密钥）
$agentsSkill = Join-Path $agentsHome 'skills\answer-me-with-html'
if (Test-Path -LiteralPath $agentsSkill) {
  Copy-Item -LiteralPath $agentsSkill -Destination (Join-Path $bundleRoot 'agents-skills') -Recurse -Force
}
$skillLock = Join-Path $agentsHome '.skill-lock.json'
if (Test-Path -LiteralPath $skillLock) {
  Copy-Item -LiteralPath $skillLock -Destination $bundleRoot -Force
}

# 4) DSH 用户级技能（0.2.2-rc.5 起新增的技能根，纯 Markdown 与资源，可迁移）
$userSkills = Join-Path $dshHome 'skills'
if (Test-Path -LiteralPath $userSkills) {
  Copy-Item -Path (Join-Path $userSkills '*') -Destination (Join-Path $bundleRoot 'dsh-skills') -Recurse -Force
}

# 5) 工作区级 AGENTS 规则（本机工作区已从 C: 迁到 Q:，盘符按实际填写）
$agentsFile = 'Q:\workspace\2026Spring2Winter\AGENTS.md'
if (Test-Path -LiteralPath $agentsFile) {
  Copy-Item -LiteralPath $agentsFile -Destination $bundleRoot -Force
}

# 6) 迁移手册本身
$handbook = 'Q:\workspace\2026Spring2Winter\harness\dsh.md'
if (Test-Path -LiteralPath $handbook) {
  Copy-Item -LiteralPath $handbook -Destination $bundleRoot -Force
}

# 7) 可选：HyperFrames 工程（这是用户内容，不是缓存；不需要时整段删除）
$hfProjects = Join-Path $dshHome 'data\dsh-hyperframes\projects'
if (Test-Path -LiteralPath $hfProjects) {
  Copy-Item -LiteralPath $hfProjects -Destination (Join-Path $bundleRoot 'hyperframes-projects') -Recurse -Force
}

# 8) 可选：字体。本机 profile 未覆盖字体族，只有字号，通常不需要带字体。
$fontSource = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
Get-ChildItem -LiteralPath $fontSource -Filter 'MapleMono-NF-CN-*.ttf' -ErrorAction SilentlyContinue |
  Copy-Item -Destination (Join-Path $bundleRoot 'fonts') -Force

if ((Read-Host "请检查资源包无秘密、私有会话或不应迁移的内容，输入 YES 后压缩") -cne "YES") { throw "已取消压缩，请检查 $bundleRoot" }
$zipPath = "$bundleRoot.zip"
Compress-Archive -Path (Join-Path $bundleRoot '*') -DestinationPath $zipPath -Force
Write-Host "迁移资源包已生成：$zipPath"
```

检查点：

- `desktop-profile` 里有 `package.json`、`pnpm-lock.yaml`、`pnpm-workspace.yaml`；patch 默认不导出，只有人工审查并脱敏后才可放入迁移包。
- `web-profile` 和 `acp-profile` 默认留空；如需配置，同样先审查脱敏。
- `agents-skills\answer-me-with-html` 和根目录的 `.skill-lock.json` 存在。
- `dsh-skills` 里有 11 个技能目录（`paper-spine` 系列 6 个、`humanizer`、`i-have-adhd`、`manage-skills`、`ppt-master`、`prompt-master`）。
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

# DSH 用户级技能（技能根优先级 rank 400，见第 6 节）
$userSkillsSource = Join-Path $bundleRoot 'dsh-skills'
if (Test-Path -LiteralPath $userSkillsSource) {
  New-Item -ItemType Directory -Path (Join-Path $dshHome 'skills') -Force | Out-Null
  Copy-Item -Path (Join-Path $userSkillsSource '*') -Destination (Join-Path $dshHome 'skills') -Recurse -Force
}

# profile 目录留档：先备份应用生成的版本，再按第 4.3 节手工合并
$backupDir = Join-Path $env:TEMP ('dsh-profile-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $profileDir 'cordis.patch.yml') -Destination $backupDir -Force
Copy-Item -LiteralPath (Join-Path $profileDir 'package.json')     -Destination $backupDir -Force

Write-Host "共享技能：$agentsHome\skills"
Write-Host "用户级技能：$dshHome\skills"
Write-Host "profile 备份：$backupDir"
Write-Host "参考清单：$bundleRoot\desktop-profile"
```

### 3.1 AGENTS 规则

除下面的工作区规则外，本机还有 `%USERPROFILE%\.dsh\AGENTS.md` 用户级规则，包含论文协作与写作要求。它可影响用户级会话；迁移前先检查适用范围及隐私，按需单独备份，在目标机与现有规则合并，不要覆盖。上面的脚本只导出工作区规则，不自动导出用户级规则。

当前项目的规则不在项目目录中，而在 Git 工作区的父目录：

```text
Q:\workspace\2026Spring2Winter\AGENTS.md
```

本机工作区已从 `C:\workspace` 迁到 `Q:\workspace`（`C:\workspace` 现在不存在），盘符变化不影响规则层级，只影响路径。如果新电脑也采用相同的工作区布局，把资源包中的 `AGENTS.md` 放到相同位置。若工作区路径不同，应放到新工作区的最上层项目父目录，确保它覆盖所有需要该规则的仓库。

新电脑上的规则文件内容应为：

```markdown
# Answer format

- Do not create HTML pages by default.
- Use HTML only when the user invokes `@answer-me-with-html` or explicitly asks for an HTML reply.
- In all other cases, answer in plain Markdown or text.
- This rule overrides any skill's always-on or automatic page behavior.
```

这是工作区级规则，不是用户全局规则。不要把它复制到 `.dsh` 根目录，除非你明确希望所有项目都遵守同一条规则。

DSH 侧由 `@deepseek-ai/dsh-agent-instructions` 读取并用 `maxBytes: 65536` 截断。注意组合后的配置里这个行会出现 5 次：`dsh-base` 的 host 行被 `dsh-web-app` 用 `disabled: true` 关掉，真正生效的是 4 个 agent preset（`standard`、`ptc`、`cordis`、`minimal`）各带的一份。所以如果 AGENTS.md 没有被读进来，不要去 `cordis.patch.yml` 里"打开"顶层行——先确认文件层级和大小上限。

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
| profile | `desktop`（另有 `web`、`acp`） | 保留 |
| 默认 provider（2026-11-19 历史值） | `opencode-go`（`@deepseek-ai/dsh-llm-pi-ai`） | 保留名称，密钥重填 |
| 默认模型（2026-11-19 历史值） | `deepseek-v4.1-flash` | 保留 |
| 上下文/输出上限（历史值） | 1000000 / 384000 | 保留 |
| 输入模态（历史值） | text、image | 保留 |
| `reasoningEffort` | `high` | 保留；也可按任务调高到 `max` |
| 凭据引用（历史值） | `OPENCODE_GO_API_KEY`、`K8S_15_API_KEY`、`MUZE_AI_API_KEY` | 只迁移变量名，不迁移值 |
| 追加 provider（历史值） | `k8s-15`（OpenAI 兼容内网端点）、`muze-ai`（OpenAI Responses） | 地址、端口、密钥按新网络重填 |
| 源 profile 默认预设 | `danger-full-access`，sandbox `danger-full-access` + approval `never` | 不自动迁移；新电脑自行选择 |
| `never` 语义 | 需要审批的操作直接拒绝，不弹窗 | 不是自动批准 |
| 权限预设（本会话） | `danger-full-access` = sandbox `danger-full-access` + approval `never` | 会话级，不随 profile 迁移 |
| 正文/代码/终端字号 | 15 / 13 / 14 | 保留 |
| 对话视图 | `transcriptView: detailed` | 保留 |
| 性能用量显示 | `performanceUsage: detailed` | 保留 |
| 账号面板 | `step: done`、`process: detailed`、`usage: detailed`、`developerTools: true` | 保留 |
| 运行中回车 | `ui-conversation.config.busyEnter: steer` | 按需合并 |
| 界面语言 | `zh-CN`（`%APPDATA%\@deepseek-ai\dsh-desktop\desktop\locale-cache`） | 由应用重新写入，不迁移 |

### 4.2 当前 `cordis.patch.yml` 的参考快照

下面是 2026-11-19 的历史参考快照，尤其模型和 provider 已过期，**不是当前 profile 快照，也不应直接迁移模型配置**。当前非模型变更另见下文。它不含密钥（密钥在 `.credentials.yaml` 里），可以安全地进仓库，但有两处已脱敏：`k8s-15.baseURL` 的内网地址和 `agenteroBin` 里的用户名。**不要把它当作可直接覆盖的文件**——新电脑的 profile 可能已有别的 patch 条目，应当按 `id` 合并而不是整文件替换。

```yaml
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config:
    provider: opencode-go
    model: deepseek-v4.1-flash
    reasoningEffort: high
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
      k8s-15:
        displayName: k8s-15
        apiKeyEnv: K8S_15_API_KEY
        api: openai-completions
        baseURL: http://<K8S_15_HOST>:18080/v1   # 内网地址已脱敏
        models:
          - id: qwen3.8-27b
            name: qwen3.8-27b
            contextWindow: 65536
            maxTokens: 32768
            reasoningEfforts:
              off: null
              low: low
              medium: medium
              xhigh: xhigh
      muze-ai:
        displayName: Muze AI
        apiKeyEnv: MUZE_AI_API_KEY
        api: openai-responses
        baseURL: https://api.muzeai.top/v1
        models:
          - id: gpt-6-luna
            name: gpt-6-luna
            reasoningEfforts:
              off: null
              low: low
              medium: medium
              high: high
              xhigh: xhigh
              max: max
            contextWindow: 272000
            input:
              - text
              - image
          - id: gpt-6.1-terra
            name: gpt-6.1-terra
            reasoningEfforts:
              off: null
              low: low
              medium: medium
              high: high
              xhigh: xhigh
              max: max
            contextWindow: 272000
            input:
              - text
              - image
          - id: gpt-6.2-sol
            name: gpt-6.2-sol
            reasoningEfforts:
              low: low
              medium: medium
              high: high
              xhigh: xhigh
              max: max
            contextWindow: 272000
            input:
              - text
              - image
          - id: gpt-6.2-astra
            name: gpt-6.2-astra
            reasoningEfforts:
              low: low
              medium: medium
              high: high
              xhigh: xhigh
              max: max
            contextWindow: 272000
            input:
              - text
              - image
- id: agentero-host
  name: agentero-dsh-host
  config:
    vault: Q:\vault
    agenteroBin: C:\Users\<user>\AppData\Local\Agentero\cli\agentero.exe
    recentVaults:
      - Q:\vault
      - Q:\vault\paper
- id: better-sidebar
  name: dsh-better-sidebar
  config:
    agentOpenTools: true
```

profile 根的 `cordis.yml` 始终是一个空数组，注释里也写明了"编辑 `cordis.patch.yml`，不要改这个文件"：

```yaml
# dsh profile root — an empty entry list. The tree is composed as patches:
# each bundle in package.json's dsh.profile.bundles, then cordis.patch.yml, then any
# --patch overlays. Edit cordis.patch.yml, not this file.
[]
```

`web` profile 的用户层现在只保留 `opencode-go` 的 `deepseek-v4.1-flash`（上一版的 `deepseek-v4-pro`、`glm-5.3`、`glm-5.3-flash` 已移除）：

```yaml
- id: llm-pi-ai
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

2026-11-27 核查显示 `acp` 的用户层不再是空数组，含模型 provider 配置；根据本次范围不展开。

重要说明：

- patch 条目是"按 `id` 定向覆盖"的，`name` 要和该 id 对应的模块一致；写错 `name` 会导致该行加载失败，而不是静默忽略。
- patch 里允许 `!!js` 表达式（composed 配置里 `sandbox-policy.mode` 是 `process.env.DSH_PERMISSION_MODE ?? 'workspace-write'`，`user-approval.policy` 在 `DSH_PERMISSION_MODE=danger-full-access` 时取 `never`，其余取 `ask`）。用户层尽量只用字面量，便于迁移时审查。
- 2026-11-27 的用户 patch 包含 `permission` 行：`defaultPreset: danger-full-access`，并列出 `read-only`、`workspace-write`、`danger-full-access` 三套预设。可同时存在会话级选择；不要默认将此宽松预设迁移。
- 新增 `ui-conversation` 行，`busyEnter: steer`。
- 只改 `ui-theme` 的字号、`agent-default-model` 的模型与推理等级、`llm-pi-ai` 的 provider 目录，是这套配置里最稳定的三处。其余 `ui-*` 条目是界面面板的展开状态，可以照抄也可以让应用重新生成。
- `agentero-host` 和 `better-sidebar` 两行是 2026-11-19 新增插件的配置行：只有装了对应 bundle 才需要；`agentero-host` 的 `vault` / `agenteroBin` 是旧机器的绝对路径，迁移时按新机器重填。

### 4.3 新电脑使用的便携 `cordis.patch.yml` 模板

先启动应用，备份目标 profile 的 patch。按 `id` 合并以下**非模型**条目，不要整文件覆盖；插件配置只在安装对应 bundle 后使用。

```yaml
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
- id: ui-conversation
  name: "@deepseek-ai/dsh-client-ui-conversation"
  config:
    busyEnter: steer
- id: better-sidebar
  name: dsh-better-sidebar
  config:
    agentOpenTools: true
```

`agentero-host` 的 vault 与 CLI 路径依新机器填写。模型、provider 和密钥由目标机自行配置。源机器的 `permission.defaultPreset: danger-full-access` 有意省略，避免静默放宽权限；目标机如确需使用应手动选择。不要将只适用于 desktop 的插件 patch 套到缺少对应 bundle 的 web profile 来判断 desktop 是否有效；在目标应用内检查加载状态。

### 4.4 模型 provider 与凭据

**历史资料（2026-11-19）**：本节具体 provider、模型及凭据引用未经本次同步，不代表当前状态；新电脑按实际配置，不要照搬。

DSH 把"provider 目录"和"密钥"彻底分开：

- **provider 目录**写在 profile 的用户层（`llm-pi-ai.config.providers`），是明文、可进仓库。
- **密钥**不写进 profile，只用 `apiKeyEnv` 声明变量名；真实值由 `@deepseek-ai/dsh-credentials-local` 保存在 `%USERPROFILE%\.dsh\.credentials.yaml`。

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
  K8S_15_API_KEY: <K8S_15_API_KEY>
  MUZE_AI_API_KEY: <MUZE_AI_API_KEY>
```

迁移要点：

- 新电脑在 **设置 → 模型** 里为每个 provider 重新录入 key，让应用自己写 `refs`；只使用默认 `opencode-go` 时只需要 `OPENCODE_GO_API_KEY`。
- 不要手工把旧 `refs` 粘到新文件里；设备标识和浏览器会话授权都与本机相关。
- `k8s-15` 是内网端点，`muze-ai` 是第三方 OpenAI Responses 端点，两者的可用性取决于新机器的网络；不确定就不要把这两行 provider 配置带过去。
- `client-connection/browser-session` 丢了会导致本地 Web 界面直接返回 `401 未经授权`（用 `Invoke-WebRequest` 直接访问当次启动的端口就是 401）。正确做法是从应用窗口打开界面，而不是手拼 URL。
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

bundle 里的每个"插件"本质上是一个 cordis 行（row）：`id` + `name`（npm 模块）+ `config`。同名的 row 在不同 profile 里重复出现是正常的——组合后的配置里 `skill-filesystem` 会出现多次：每个 agent preset 各有一份本地技能发现行，各插件 bundle（`genui`、`dsh-hyperframes`、`dsh-ppt`、`dsh-answer-me-with-html`）再各自插入一份指向自己的 `skills/` 根。

### 5.2 desktop profile 清单中的 20 个 bundle

| bundle | 版本 | 来源 | 作用 | 迁移方式 |
|---|---:|---|---|---|
| `@deepseek-ai/dsh-base` | `0.2.2-rc.5` | 应用内置 | 核心层：LLM、会话、沙箱、审批、权限预设、工具、技能、goal、agent team、subagent、workflow、MCP 资源 | 随应用，不要复制 |
| `@deepseek-ai/dsh-web-app` | `0.2.2-rc.5` | 应用内置 | 浏览器面：HTTP/API、UI 组件、终端、文件树、schedule、插件管理器、office 技能 | 随应用，不要复制 |
| `dsh-codex-effort-slider` | `1.1.9` | npm | 把推理等级选择换成一条可拖动的连续滑条 | 重装 |
| `dsh-skin-market` | `0.1.83` | npm | 皮肤/主题市场与生命周期管理 | 重装 |
| `@changfenhuang/dsh-genui` | `0.17.0` | npm | GenUI：`dsh-ui` 代码块内联渲染交互界面 | 重装 |
| `dsh-hyperframes` | `0.14.0` | npm | HTML→视频工作台（23 个技能 + 工程/渲染工具） | 重装 |
| `dsh-answer-me-with-html` | `0.5.0` | npm | 只用技能、不加工具的 bundle：一页 HTML 回答 | 重装 |
| `dsh-context` | `0.87.1` | npm | 上下文洞察：Context 面板、Fleet 视图、`/context` 命令 | 重装 |
| `agentero-dsh` | `0.1.8` | npm | 把 Agentero 文献库 / 笔记 / PDF 阅读器接进 DSH，提供 5 个 `agentero_*` 工具 | 重装，另装 Agentero CLI |
| `dsh-ppt` | `0.36.0` | npm | 演示文稿三件套：HTML 放映 + 可编辑 PPTX + JSON 工程 | 重装 |
| `dsh-better-sidebar` | `0.32.1` | npm | 右侧栏增强：文件树、可编辑编辑器、Git、任务、侧边对话、`sidebar_open` 工具 | 重装，注意与宿主版本匹配 |
| `ds-bot` | `0.3.10`（依赖范围 `^0.3.10`） | npm | 长期 Bot、群聊、记忆及协作；bundle 还覆盖搜索配置与设置界面入口 | 重装；团队数据和凭据分开审查，默认不迁移 |
| `@deepseek-ai/dsh-experimental-voice-input-bundle` | `0.2.2-rc.5` | 应用内置 | 本地 SenseVoice 语音输入 | 随应用，开启即可 |
| `@deepseek-ai/dsh-experimental-plugin-market-bundle` | `0.2.2-rc.5` | 应用内置 | Discover 插件市场 | 随应用，开启即可 |
| `@deepseek-ai/dsh-experimental-auto-review` | `0.2.2-rc.5` | 应用内置 | Auto 权限预设下的逐工具 LLM 授权审查 | 随应用，开启即可 |
| `@deepseek-ai/dsh-experimental-forge-bundle` | `0.2.2-rc.5` | 应用内置 | Git 变更请求面板 + worktree 工具 | 随应用，开启即可 |
| `@deepseek-ai/dsh-personalized-recommendations` | `0.2.2-rc.5` | 应用内置 | 回答下方的个性化页面与插件推荐卡片 | 随应用，开启即可 |
| `@deepseek-ai/dsh-experimental-session-titles-bundle` | `0.2.2-rc.5` | 应用内置 | 每条人类消息到来时刷新会话标题 | 随应用，开启即可 |
| `@deepseek-ai/dsh-experimental-cot-translation-bundle` | `0.2.2-rc.5` | 应用内置 | 推理过程的机器翻译 | 随应用，开启即可 |
| `@deepseek-ai/dsh-experimental-inspector-profile` | `0.2.2-rc.5` | 应用内置 | 会话原始日志与 Chat 节点检查器 | 随应用，开启即可 |

`dsh.profile.bundles` 的实际顺序（顺序即叠加顺序）：

```json
{
  "name": "dsh-profile-desktop",
  "private": true,
  "dependencies": {
    "@changfenhuang/dsh-genui": "0.17.0",
    "agentero-dsh": "0.1.8",
    "ds-bot": "^0.3.10",
    "dsh-answer-me-with-html": "0.5.0",
    "dsh-better-sidebar": "^0.32.1",
    "dsh-codex-effort-slider": "1.1.9",
    "dsh-context": "0.87.1",
    "dsh-hyperframes": "0.14.0",
    "dsh-ppt": "0.36.0",
    "dsh-skin-market": "0.1.83"
  },
  "dsh": {
    "profile": {
      "bundles": [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-web-app",
        "dsh-answer-me-with-html",
        "agentero-dsh",
        "@deepseek-ai/dsh-experimental-voice-input-bundle",
        "@deepseek-ai/dsh-experimental-plugin-market-bundle",
        "@deepseek-ai/dsh-experimental-auto-review",
        "@deepseek-ai/dsh-experimental-forge-bundle",
        "@deepseek-ai/dsh-personalized-recommendations",
        "@deepseek-ai/dsh-experimental-session-titles-bundle",
        "@deepseek-ai/dsh-experimental-cot-translation-bundle",
        "@deepseek-ai/dsh-experimental-inspector-profile",
        "dsh-better-sidebar",
        "dsh-codex-effort-slider",
        "dsh-skin-market",
        "dsh-context",
        "@changfenhuang/dsh-genui",
        "dsh-hyperframes",
        "dsh-ppt",
        "ds-bot"
      ]
    }
  }
}
```

bundle 的叠加顺序以 `bundles` 数组为准（数组越靠后越晚叠加）：如果两个 bundle 覆盖同一个 row id，后出现者生效；`dependencies` 只决定包是否装进 `node_modules`，不决定加载顺序。

### 5.3 安装命令与两条路径的差别

**推荐：用应用内的 设置 → 插件。** 它会同时改 `dependencies`、`dsh.profile.bundles`，并用应用自带的 pnpm 安装，然后把结果写进 `.plugin-manager\logs`。

**命令行只改依赖，不改 bundle 清单**，所以下面的命令装完之后仍要手工把包名加进 `dsh.profile.bundles`，否则不会加载：

```powershell
$dsh = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd'

& $dsh --version
& $dsh plugin --profile desktop list --depth 0     # 查看已装依赖
& $dsh plugin --profile desktop add dsh-ppt@0.36.0 # 只装包
```

注意几个 CLI 的边界：

- `dsh --profile desktop --dump-config` 会失败并提示 `profile "desktop" is managed exclusively by the Electron application`。**desktop profile 不能由 CLI 启动**，只能用桌面应用；web 与 desktop 的 bundle 不同，不能用 web 的组合结果验证所有 desktop 插件行。
- `dsh plugin --profile desktop ...` 只是把参数转发给该 profile 目录下的 pnpm，所以 `list`/`add`/`remove`/`why` 都能用。
- `dsh --from-default-profile <name>` 会用随应用发布的模板重建一个 profile，出问题时比手改更快。
- CLI 默认不在 PATH 上（本机 `HKCU\Software\DeepSeekHarness\Command` 不存在，`where dsh` 找不到）。需要在应用设置里启用命令行，或直接使用上面的完整路径。

### 5.4 14 个内置但未启用的 bundle

这些包随应用发布，默认关闭。装之前请知情：实验包会改工具面或界面，出问题用 `--from-default-profile` 重建 profile。

| bundle | 类型 | 作用 |
|---|---|---|
| `@deepseek-ai/dsh-headless` | 运行模式 | 一次性任务：只跑 core Agent/Session，没有 Host、HTTP、浏览器层 |
| `@deepseek-ai/dsh-acp-app` | 运行模式 | ACP：JSON-RPC stdio + 进程生命周期（本机已在 `acp` profile 启用） |
| `@deepseek-ai/dsh-sdk-app` | 运行模式 | SDK：stdio JSON-RPC 服务，附 `skill-office`、`present`、`schedule`、`ask-user` 工具 |
| `@deepseek-ai/dsh-sdk-minimal` | 运行模式 | 最小 SDK：JSON-RPC + 单个 DeepSeek 适配器 + 持久 shell |
| `@deepseek-ai/dsh-experimental-terminal-bundle` | 实验 | 让 shell 进程跨工具调用保活（侧边栏终端） |
| `@deepseek-ai/dsh-experimental-liveshare` | 实验 | 通过 Relay 分享会话（只读或有界写入） |
| `@deepseek-ai/dsh-experimental-session-search` | 实验 | 检索历史会话的工具 |
| `@deepseek-ai/dsh-experimental-tool-worktree` | 实验 | 单独提供 worktree 模型工具（`forge-bundle` 里已包含一套，故本机未单独启用） |
| `@deepseek-ai/dsh-experimental-badge-skill-bundle` | 实验 | 让 agent 在产物里加 "powered by dsh" 徽标 |
| `@deepseek-ai/dsh-experimental-ralph-bundle` | 实验 | 用全新 agent 重复执行显式要求的循环工作 |
| `@deepseek-ai/dsh-cua-bundle` | 可选 | macOS Computer Use；Windows 上报 `unsupported-platform`，装不上 |
| `@deepseek-ai/dsh-deepseek-chat-import` | 可选 | 把 DeepSeek 网页版聊天导出导入成本地会话（0.2.2-rc.5 新增） |

另有 2 个只在目录里出现、本机装不上：`@deepseek-ai/dsh-subagent-claude-code`、`@deepseek-ai/dsh-subagent-codex`（`availability: missing`）。

`@deepseek-ai/dsh-experimental-agent-team-profile` 已不存在：agent team 的协作行已并入 `dsh-base`；`team_task_*` 在本次会话未暴露，实际可见性依会话而定。

### 5.5 十个第三方插件的能力说明

#### `ds-bot` 0.3.10

- 提供长期 Bot、群聊和记忆；插件 bundle 同时加入 `web-search-auto`，将 `web` 搜索设为 `auto`，并禁用原 `ui-settings-general` 行。安装顺序与其他搜索/设置插件可能相互影响。
- 默认团队数据位置为 `%DSH_HOME%\bot`，含用户内容；不纳入基础迁移包。凭据和连接器秘密不复制，确需迁移团队数据应先按官方文档单独审查和备份。当前普通会话未暴露 Bot 专用工具，不应据此声称所有 Bot 工具都可用。
- 当前会话可见 `ds-bot-manual`、`report-ds-bot-issue` 技能；与团队专用工具的可见性分别验证。

#### `dsh-ppt` 0.36.0

- **工具面**：`ppt_create`、`ppt_edit`、`ppt_check`、`ppt_render`、`ppt_undo`、`ppt_data`、`ppt_themes`、`ppt_templates`、`ppt_import`、`ppt_absorb`、`ppt_cite`、`ppt_from_office`、`ppt_remotion`。
- **产物**：一次生成三件套——独立 HTML 放映页、可编辑 PPTX、dsh-ppt JSON 工程；后续修改都基于 JSON 工程，能撤销。相较上次快照，本会话还可见文献引用、Office 导入和 Remotion 导出工具。
- **渲染**：`ppt_render` 依赖 `@deepseek-ai/libreoffice-kit@0.2.3`（应用里已 unpack，win32-x64），输出逐页 PNG/PDF 并报告缺失字体；装不上时普通建卡流程仍可用。
- **技能**：`dsh-ppt`。
- **迁移要点**：工程文件是普通文件，跟着工作区走；插件本身重装即可。主题、模板是只读参考，不需要迁移。从 0.20.x 升到 0.36.0 后旧工程建议先 `ppt_check` 再改。

#### `dsh-hyperframes` 0.14.0

- **工具面**：`hyperframes_project`（建/读受管理工程）、`hyperframes_render`（准备环境、预览、渲染 MP4、查询/取消任务）、`hyperframes_health`（校验技能文件与宿主注册状态）。
- **技能面**：这是本机技能最多的插件，23 个，覆盖 `hyperframes`（总入口）、`hyperframes-cli`、`hyperframes-registry`、`media-use`、`figma`、`slideshow`、`remotion-to-hyperframes`，以及 14 个兼容入口（见 6.2）。
- **数据**：工程在 `%DSH_HOME%\data\dsh-hyperframes\projects`，这是用户内容，可以迁移；但它不是缓存，删了就没了。
- **迁移要点**：首次准备渲染环境会下载依赖，所以新电脑第一次渲染一定比旧机器慢；`hyperframes_health` 可以用来确认技能是否重新注册成功。

#### `@changfenhuang/dsh-genui` 0.17.0

- **工具面**：`render_ui`（工具行卡片）、`validate_dsh_ui`（校验 ```dsh-ui 代码块 JSON）。
- **协议**：回答正文里的 ```dsh-ui 围栏 + 固定组件词表（布局/展示/图表/交互/高级五类）。组件带 `action` 时，交互会以 `[genui-action]` 回传，触发重渲染。
- **技能**：`genui`。
- **迁移要点**：组件词表和 schema 随版本变化。旧机器生成的页面不要跨版本复用；升级后以 `validate_dsh_ui` 的返回为准。

#### `dsh-skin-market` 0.1.83

- **作用**：原生皮肤市场与生命周期管理，浏览/安装社区主题。
- **缓存**：`%DSH_HOME%\profiles\desktop\.dsh-skin-market\catalog.json` 是市场索引缓存（首次打开市场时生成，本机当前没有该目录）；**不要迁移**，新机器首次打开会自动重建。
- **迁移要点**：已安装的皮肤包本身是普通依赖，会出现在 profile 的 `dependencies` 里；只迁 profile 清单，缓存让新机器重新拉。

#### `dsh-codex-effort-slider` 1.1.9

- **作用**：纯 UI 插件，把输入框工具行的推理等级档位换成一条连续滑条（Codex 风格）。
- **迁移要点**：不提供工具和技能。真正的默认等级仍由 `agent-default-model.config.reasoningEffort` 决定，滑条只是改运行时的值。

#### `dsh-answer-me-with-html` 0.5.0

- **作用**：只注册技能、不加工具的 bundle，回答复杂问题时产出一页视觉 HTML。
- **技能**：`answer-me-with-html`，在该 bundle 里通过第二个 `@deepseek-ai/dsh-skill-filesystem` 行（row id `answer-me-with-html-skill`）挂载自己的 `skills/` 目录。
- **迁移要点**：本机同时在 `%USERPROFILE%\.agents\skills\answer-me-with-html` 有一份共享副本。DSH 侧由 bundle 提供，bundle 是权威来源；共享副本保留无害，但在确认技能发现优先级之前不要删。

#### `dsh-context` 0.87.1

- **作用**：上下文洞察与生命周期管理。提供跨会话的 **Context 洞察页**（Token/成本 KPI、活动热力图、组成环形图、会话卡片）、Context / Fleet 侧边栏标签页、Context 面板和 `/context` 命令。
- **工具面**：不注册模型工具，纯 Host + Web UI 插件。
- **缓存**：`%DSH_HOME%\storages\dsh-context\overview-cache.v1.json` 是总览缓存，不迁移，首次使用重新统计。
- **迁移要点**：改 `dsh.profile.bundles` 后重启应用；面板数据来自本机会话，不需要也不应该从旧机器复制。

#### `agentero-dsh` 0.1.8

- **作用**：把 [Agentero](https://github.com/poco-ai/Agentero) 的文献库、笔记和 PDF 阅读器接进 DSH。
- **工具面**：`agentero_discover_arxiv`、`agentero_import_paper`、`agentero_list_papers`、`agentero_read_note`、`agentero_search_notes`。
- **配置**：`agentero-host` 行（`vault` 知识库根、`agenteroBin` CLI 路径、`recentVaults`）；`vault` 下是 `papers/`、`notes/` 和 `.agentero/catalog.sqlite`。
- **外部依赖**：Agentero CLI（本机 `%LOCALAPPDATA%\Agentero\cli\agentero.exe`），新电脑要重新安装。
- **迁移要点**：插件重装；vault 是用户内容，单独备份，不要塞进 DSH profile 迁移包。

#### `dsh-better-sidebar` 0.32.1

- **作用**：把右侧栏扩成双工作台——文件树（Git 着色、搜索、上传）、可编辑 CodeMirror/Markdown+Mermaid 预览、Source Control / Git Graph、任务管理、侧边对话、底部面板多终端。
- **工具面**：`sidebar_open`（让模型主动打开侧边栏并定位文件/设置页）。
- **配置**：`better-sidebar` 行（`agentOpenTools: true` 表示允许模型使用 `sidebar_open`）。
- **版本约束**：本机 0.32.1 要求 DSH `0.2.2-rc.2+`；升级宿主或该插件时保持两者匹配，否则会报版本拒绝错误。
- **迁移要点**：插件重装、配置行照抄；侧边栏布局是会话级 UI 状态，不迁移。

### 5.6 最容易误判的三点

1. **"装了包"不等于"启用了插件"**：`dependencies` 决定文件在不在，`dsh.profile.bundles` 决定加载不加载。
2. **`enabled: false` 不等于坏了**：很多行是条件启用，例如 base 层的 `tool-plugin-manager` 是 `disabled: !!js '!ctx.get('profileContext')'`，只有在应用/profile 上下文里才出现；`fs-observation-policy` 在 0.2.2-rc.5 里就是随包发布但 `disabled: true`（默认关闭），不是配置坏了。看到 `enabled:false` 先看它的 `disabled` 表达式，不要急着改。
3. **`bash-sandbox` 和 `tool-bash` 在 Windows 上都是禁用的**（`disabled: !!js process.platform === 'win32'`），实际生效的是 `pwsh-sandbox` 和 `pwsh`。所以 Windows 上的沙箱/命令问题会表现为 PowerShell 失败，而 bash 相关配置怎么改都没用。

---

## 6. 技能清单

DSH 的技能由 `@deepseek-ai/dsh-skill-filesystem` 等提供者按 rank 合并，rank 小者优先，同名技能就近覆盖。0.2.2-rc.5 的本地根顺序：

| rank | 来源 | 根 |
|---:|---|---|
| 100 | `project-dsh` | `<项目根>/.dsh/skills` |
| 200 | `project-agents` | `<项目根>/.agents/skills` |
| 300 | `custom` | `Config.customSkillDirs`（本机未配置） |
| 400 | `user-dsh` | `%USERPROFILE%\.dsh\skills` |
| 500 | `user-agents` | `%USERPROFILE%\.agents\skills` |
| 600 | `bundled` | `Config.bundledSkillDir`（应用/bundle 自带的技能包） |

项目根 = 最近的含 `.git` 的祖先目录；没有 `.git` 时用当前 cwd。除本地根外还有"打包技能提供者"：应用自带的 office 技能、`@deepseek-ai/dsh-agent-preset/skills` 里的 `dsh-doc`、`sandbox-windows-acl` 的 `diagnose-windows-sandbox-acl`，以及个性化推荐 bundle 里的 `personalized-pages` / `official-plugins`。

### 6.1 应用自带的 office 技能

当前会话可见以下 office 技能；其中 `office-tools` 的具体来源本次未单独核验，迁移后在新会话中检查：

| 技能 | 作用 |
|---|---|
| `office` | Office 文档工作流总入口，按任务路由到下面的创作技能，并说明渲染/转换/重算工具 |
| `office-docx` | 创建、读取、编辑、校验 Word 文档 |
| `office-xlsx` | 读取、创建、编辑、校验 Excel 工作簿、数据与公式 |
| `office-pptx` | 创建、读取、编辑、校验 PowerPoint 演示文稿 |
| `office-tools` | 离线检查与编辑 Office 文件包 |

0.2.2-rc.5 把上一版的 `office-render`、`office-export-pdf`、`office-recalculate` 三个独立技能合并进了 `office` 路由：**加载 `office` 技能后**，`office_render`、`office_convert`、`office_recalculate` 三个工具从下一步开始可用（未加载时不在工具列表里，这是"渐进加载"/条件工具，不是故障）。渲染依赖应用里的 `@deepseek-ai/libreoffice-kit@0.2.3`（win32-x64 已 unpack），不需要装系统 LibreOffice。Python 环境说明会指向 `load_workspace_dependencies`。

### 6.2 bundle 自带技能

| bundle | 技能 | 数量 |
|---|---|---:|
| `dsh-hyperframes` | 真实技能：`hyperframes`、`hyperframes-cli`、`hyperframes-registry`、`media-use`、`figma`、`slideshow`、`remotion-to-hyperframes`、`reverse-any-video`、`style-sampling` | 9 |
| `dsh-hyperframes` | 兼容入口：`hyperframes-animation`、`hyperframes-audio`、`hyperframes-core`、`hyperframes-creative`、`hyperframes-keyframes`、`hyperframes-studio`、`motion-graphics`、`music-to-video`、`pr-to-video`、`product-launch-video`、`faceless-explainer`、`talking-head-recut`、`embedded-captions`、`general-video` | 14 |
| `dsh-ppt` | `dsh-ppt` | 1 |
| `@changfenhuang/dsh-genui` | `genui` | 1 |
| `dsh-answer-me-with-html` | `answer-me-with-html` | 1 |

上述 14 个是**兼容入口**，SKILL.md 里明确写着"已退役技能 X 的入口，路由到当前官方技能"（大部分路由到 `hyperframes`，`hyperframes-audio` 路由到 `media-use`，`hyperframes-studio` 路由到 `hyperframes-cli`）。不要因为目录名"过时"就删掉它们——旧引用会命中这些入口。

`dsh-skin-market`、`dsh-codex-effort-slider`、`dsh-context`、`agentero-dsh`、`dsh-better-sidebar` 不注册技能（前两个是纯 UI 插件，后三个走面板/工具）。`dsh-doc` 由 agent-preset 打包提供，不在上面的统计里。当前会话另可见 `ds-bot-manual`、`report-ds-bot-issue` 和 `goal-grill`；其发现来源未逐一核验，以会话目录为准。

### 6.3 用户级技能目录（0.2.2-rc.5 新增）

```text
%USERPROFILE%\.dsh\skills\
├── humanizer\
├── i-have-adhd\
├── manage-skills\
├── paper-spine\
├── paper-spine-deliver\
├── paper-spine-figures\
├── paper-spine-followwriting\
├── paper-spine-review\
├── paper-spine-study\
├── ppt-master\
└── prompt-master\
```

这些是用户级技能目录，可能包含 Markdown 和资源；来源与内容须在迁移前逐项检查，不应假定没有私有数据。rank 400，优先级高于 `.agents\skills`（500），低于项目内技能根。迁移时整目录复制即可；`paper-spine` 系列的版本锁在 `%USERPROFILE%\.dsh\.paperspine-skills\`，不迁移，新机器重新安装/更新。

### 6.4 共享技能目录

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

### 6.5 调用方式

在新会话里，技能既可以由模型通过 `skill` 工具加载，也可以由用户显式点名：

```text
Use the genui skill to render a comparison table.
用 dsh-ppt 把这份 Markdown 做成 12 页的汇报。
Use the dsh-doc skill to check how this DSH version handles approvals.
用 paper-spine 继续改这篇论文的讨论部分。
```

验收时优先试这几个：`genui`（有没有 ```dsh-ui 渲染）、`dsh-ppt`（有没有 `ppt_create` 工具）、`office-docx`（有没有 Word 工作流）、`dsh-doc`（有没有 DSH 文档查询）、`paper-spine`（用户级技能是否被发现）。它们分别覆盖"bundle 技能 + 工具"、"bundle 技能 + 多工具"、"应用自带技能"、"agent-preset 打包技能"、"用户级技能"五种来源。

---

## 7. MCP 与工具面

### 7.1 本机没有配置任何 MCP server

这是与 Codex 手册最容易搞混的一点：**本机 DSH 没有配置任何 MCP server**。`cordis.patch.yml` 里没有 MCP 段，composed 配置里只有 `@deepseek-ai/dsh-mcp-resources`（把 MCP 资源桥接进上下文的插件）和 `dsh-web-app` 的 `mcp-manager`（设置里的 MCP 管理页），没有 `mcp_servers` 之类的服务器清单。

所以：

- 不存在"从旧机器复制的 MCP 路径"这类问题，也没有 `codex mcp list` 的对应物。
- DSH 的能力来自 bundle 内的原生工具，而不是外挂 MCP 进程。
- 如果新电脑需要 MCP，应当在那台机器的 设置 → MCP 里添加（或在该 profile 里新增对应插件行），不要去找旧机器的路径。

### 7.2 本机可见的工具族

下表按 2026-11-27 的当前会话工具目录整理（工具面随 bundle 和条件加载变化，以新会话实际目录为准）。

| 来源 | 工具 | 说明 |
|---|---|---|
| base | `pwsh`、`read`、`write`、`edit`、`glob`、`grep`、`read_image` | 命令执行与文件读写；Windows 上 `tool-bash` 被禁用，没有 `bash` 工具 |
| base | `todo_write`、`ask_user_question`、`present` | 计划、追问、交付文件声明 |
| base | `create_goal`、`get_goal`、`update_goal` | 跨轮次目标，自动续跑 |
| base | `subagent`、`subagent_fork`、`list_agents`、`list_subagent_models`、`send_message`、`wait_agent` | 子代理；`interrupt_agent` 在 rc.5 包里仍有定义，但当前 preset 组合未暴露到本会话目录，以实际会话工具列表为准 |
| Agent Team | 本次普通会话未列出 `team_task_*` | 是否可见取决于运行环境与会话 |
| base | `workflow` | 用 JS 脚本编排大量子代理 |
| base | `web_search`、`web_fetch` | 网页搜索与抓取 |
| base | `skill`、`plugin_manager` | 技能加载、插件/ bundle 管理 |
| base | `job_list`、`job_output`、`job_kill` | 后台作业 |
| base | `working_directory` | 切换会话工作目录 |
| base | `load_workspace_dependencies` | 返回内置 Python / 库路径，office 技能依赖它 |
| web-app | `schedule_create`、`schedule_edit`、`schedule_list`、`schedule_view` | 定时任务 |
| web-app | `office_render`、`office_convert`、`office_recalculate` | **条件工具**：加载 `office` 技能后才出现 |
| genui | `render_ui`、`validate_dsh_ui` | 交互界面渲染与校验 |
| dsh-ppt | `ppt_create`、`ppt_edit`、`ppt_check`、`ppt_render`、`ppt_undo`、`ppt_data`、`ppt_themes`、`ppt_templates`、`ppt_import`、`ppt_absorb`、`ppt_cite`、`ppt_from_office`、`ppt_remotion` | 演示文稿、外部 PPTX 导入、母版骨架吸收 |
| dsh-hyperframes | `hyperframes_project`、`hyperframes_render`、`hyperframes_health` | 视频工程与渲染 |
| agentero-dsh | `agentero_discover_arxiv`、`agentero_import_paper`、`agentero_list_papers`、`agentero_read_note`、`agentero_search_notes` | 文献库、笔记、arXiv 导入 |
| dsh-better-sidebar | `sidebar_open` | 让模型主动打开侧边栏并定位文件/设置页 |
| forge | `create_worktree` | 新建并进入 Git worktree |

### 7.3 迁移原则

- 不要复制任何工具路径、运行时路径或端口配置；它们由应用在启动时生成。
- `DSH_WEB_URL` 是每次启动重新分配的，不要写进迁移配置。
- 工具面由 bundle 决定，所以"工具不见了"可能与 bundle、条件加载、配置或当前会话有关。先看 设置 → 插件，再看 `cordis.patch.yml`。

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

当前 `reasoningEffort: high`（上一版快照是 `max`），可用的档位由 provider 目录和 `dsh-codex-effort-slider` 共同决定。注意：

- `reasoningEffort` 的**默认值**写在 `agent-default-model` 里，是持久配置。
- **滑条**只是改运行时的值，重启后回到默认。
- 如果 provider 不接受某个档位（常见于自定义 provider），会返回 400 或配置拒绝；此时把 `agent-default-model` 的 `reasoningEffort` 改回 `high` 或更低的档位，再重启。`k8s-15` 的 `qwen3.8-27b` 只声明了 `off` / `low` / `medium` / `xhigh`，没有 `high`/`max`，切换模型时要同时换档位。

### 8.3 界面语言

`zh-CN`，记录在 `%APPDATA%\@deepseek-ai\dsh-desktop\desktop\locale-cache`（6 字节，就是 `zh-CN`）。这属于 Electron 用户数据，不迁移；新电脑在 设置 → 通用 里选一次即可。

---

## 9. 外部依赖基线

### 9.1 应用自带运行时（不要复制，重新生成）

`resources\runtime\primary-runtime\`（在应用安装目录下，随应用升级重建）：

| 组件 | 版本 | 位置 |
|---|---|---|
| Python | `3.12.14` | `dependencies\python\python.exe` |
| Node.js | `24.21.0` | `dependencies\node\bin\node.exe` |
| pnpm | `11.28.5` | `dependencies\pnpm\bin\pnpm.mjs` |

同一目录的 `runtime.json` 记录 `desktopVersion: 0.2.2-rc.5`、`payloadDigest`、Python 包清单和 Node/pnpm 版本；`resources\runtime\versions.json` 另存 Node 与 pnpm 版本。`%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\` 是旧版遗留（`desktopVersion: 0.2.2-rc.3`），两份都不要复制。

Python 站点包（`dependencies\python\Lib\site-packages`）：

```text
numpy 2.3.5            pandas 3.0.1          python-dateutil 2.9.0.post0
six 1.17.0             tzdata 2025.2         python-docx 1.2.0
python-pptx 1.0.2      openpyxl 3.1.5        Pillow 12.3.0
lxml 6.1.3             XlsxWriter 3.2.9      typing_extensions 4.16.0
et_xmlfile 2.0.0
```

Office 渲染引擎：`@deepseek-ai/libreoffice-kit@0.2.3` + `@deepseek-ai/libreoffice-kit-win32-x64@0.2.3`，位于 `resources\app.asar.unpacked\dsh\node_modules\`，被 `ppt_render` 和 office 技能的条件工具（`office_render` / `office_convert` / `office_recalculate`）使用。

0.2.2-rc.5 的 unpacked 目录里还多了语音输入用的 `sherpa-onnx-win-x64` 和终端用的 `node-pty` 等原生模块；语音模型本身在 `%USERPROFILE%\.dsh\speech-to-text\sensevoice\`，首次使用时下载。

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
| CC Switch | 用于 profile 同步 | 记录 `%USERPROFILE%\.dsh\.cc-switch-profile-sync.json`，内容为 `["web","desktop"]`（不含新增的 `acp`） |
| Agentero CLI | `%LOCALAPPDATA%\Agentero\cli\agentero.exe` | 供 `agentero-dsh` 读取文献库；新电脑重新安装 CLI 后由 `agentero-host` 配置行指向 |

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

2026-11-19 时 `%USERPROFILE%\.dsh\storages\workspace.json` 记录了 3 个工作区（本次未核验）（**不要迁移这个文件**）：

| 工作区 | 路径 | 会话数 |
|---|---|---:|
| `MasterGraduationProject` | `Q:\workspace\2026Spring2Winter\MasterGraduationProject` | 10 |
| `2026Spring2Winter` | `Q:\workspace\2026Spring2Winter` | 2 |
| `default-workspace` | `C:\Users\<user>\Documents\deepseek-harness\default-workspace` | 15 |

工作区路径从上一版的 `C:\workspace\...` 变成了 `Q:\workspace\...`（`C:\workspace` 已不存在）；工作区条目是按路径重新添加的，不是简单改盘符。此外 `Q:\vault`（Agentero 知识库）和 Agentero 的 agent cwd 也各有会话目录，但不在这 3 个 GUI 工作区里。

新电脑应通过 GUI 重新打开这些目录并确认权限提示。工作区根路径变化时保留新路径，不要强行复制旧路径。

### 10.2 会话存储布局

```text
%USERPROFILE%\.dsh\sessions\--Q-workspace-2026Spring2Winter-MasterGraduationProject--\
└── session-<uuid>\
    └── session.v4.jsonl.zstd
```

目录名是工作区路径的编码，文件是压缩后的 v4 JSONL。2026-11-19 时有 52 个会话目录（本次未核验）（分布在 5 个路径桶里：`default-workspace` 16、`MasterGraduationProject` 30、`2026Spring2Winter` 2、`Q:\vault` 2、Agentero agent cwd 2）。这些全部属于"私有历史"，不迁移；新电脑从空白开始。

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

- 版本与桌面端一致（本机都是 `0.2.2-rc.5`）。
- `plugin list` 能列出 10 个第三方依赖及其版本；清单不代表每行成功加载，还需在插件页核实。
- `--help` 里能看到 `--profile`、`--from-default-profile`、`--patch`、`--dump-config`。

### 11.2 patch 合并检查

检查目标应用的设置和插件页面，确认 `ui-theme`、`ui-chat`、`ui-conversation` 与按需安装的插件配置生效；检查报错并开启新会话。desktop 与 web 所加载的 bundle 不同，不能用 web 的组合结果证明 desktop 的所有插件行有效。不要将包含私人配置的完整 dump 写入共享目录。

### 11.3 目录检查

```powershell
$profileDir = Join-Path $env:USERPROFILE '.dsh\profiles\desktop'
Get-Content -LiteralPath (Join-Path $profileDir 'package.json') -Raw
Get-Content -LiteralPath (Join-Path $profileDir 'cordis.yml') -Raw
Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE '.agents\skills') -Directory | Select-Object -ExpandProperty Name
Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE '.dsh\skills') -Directory | Select-Object -ExpandProperty Name
```

预期：

- `package.json` 的 `dsh.profile.bundles` 有 20 项。
- `cordis.yml` 仍是空数组 `[]`。
- `.agents\skills` 下有 `answer-me-with-html`。
- `.dsh\skills` 下有 `paper-spine` 系列（6 个）以及 `humanizer`、`i-have-adhd`、`manage-skills`、`ppt-master`、`prompt-master`。

### 11.4 功能 smoke test

打开新会话，依次测试：

1. 普通项目里发"只回复 OK"，确认 provider 鉴权和默认模型正常。
2. 让模型渲染一个对比表格，确认 `genui` 生效（正文里应出现 ```dsh-ui 渲染块，而不是一段被丢弃的 JSON）。
3. 用 `dsh-ppt` 把一段 Markdown 做成 3 页，确认 `ppt_create`、`ppt_check` 可用。
4. 用 `office-docx` 生成一个最小 Word 文档，确认应用自带技能被发现；再让它渲染预览，确认 `office_render` 在加载 office 技能后出现。
5. 问一句 DSH 自身功能问题，确认 `dsh-doc` 技能可加载。
6. 打开右侧栏的文件/上下文面板，确认 `dsh-better-sidebar`、`dsh-context` 生效。
7. 需要视频时再试 `hyperframes_project`（首次会下载渲染依赖，慢是正常的）。

### 11.5 常见问题

| 现象 | 优先检查 |
|---|---|
| 网页界面返回 `401 未经授权` | `.credentials.yaml` 里缺 `client-connection/browser-session`，或你是手拼 URL；从应用窗口打开 |
| `profile "desktop" is managed exclusively by the Electron application` | 正常现象：desktop profile 只能由应用启动，CLI 只能做 `plugin list/add` |
| 装了包但插件没生效 | 包名没加进 `dsh.profile.bundles`；或应用没重启 |
| 插件安装失败 | 应用内置 pnpm 是否可用；`.plugin-manager\logs` 里的 pnpm 日志 |
| 沙箱报 `SetNamedSecurityInfoW failed (Win32 5): grantWrite(<workspace>)` | Windows 文件权限挡住了沙箱授权：工作区目录缺 `WRITE_OWNER`。用沙箱 ACL 修复流程处理，不要关沙箱绕过 |
| 沙箱报其他拒绝 | Windows 上生效的是 `pwsh-sandbox`；`bash-sandbox` 和 `tool-bash` 本来就被禁用，改它没用 |
| 需要审批的动作没有弹窗、直接被拒绝 | 当前会话的审批策略是 `never`（`danger-full-access` 预设会同时写入 `never`）。这是"直接拒绝、不询问"的语义；切回 `workspace-write` 预设（= workspace-write + `ask`）才会弹窗。approval 没有独立 UI 开关，它是预设的一部分 |
| 模型返回 401/403 | `refs` 里是否已有对应 `apiKeyEnv`（`OPENCODE_GO_API_KEY` / `K8S_15_API_KEY` / `MUZE_AI_API_KEY`）；`apiKeyEnv` 名字是否与 `refs` 键一致 |
| 模型返回 400 | `reasoningEffort` 档位不被 provider 接受：默认 `high`，改回 `high` 或更低；`k8s-15` 的 `qwen3.8-27b` 只有 `off`/`low`/`medium`/`xhigh` |
| 技能不可见 | 对应 bundle 是否启用；是否开了新会话；是否只复制了 `SKILL.md` 而漏了 `references/`；用户级技能是否放进了 `%USERPROFILE%\.dsh\skills`（rank 400） |
| 主题/皮肤丢失 | 正常：皮肤选择不随 profile 迁移，重新在市场里选 |
| `catalog.json` 缺失 | 正常：皮肤市场首次打开时重建 |
| 工作区列表为空 | 正常：`storages\workspace.json` 不迁移，用 GUI 重新打开目录 |
| 语音输入按钮不可用 | `voice-input` bundle 是否启用；首次使用要下载 SenseVoice 运行时（`%USERPROFILE%\.dsh\speech-to-text`）；检查系统麦克风权限 |
| 右侧栏报版本拒绝/白屏 | `dsh-better-sidebar` 与宿主版本不匹配：0.32.1 要求 DSH `0.2.2-rc.2+`；升级宿主或改钉对应插件版本后硬刷新 |
| Context 面板数字为空或很旧 | `dsh-context` 的 `storages\dsh-context\overview-cache.v1.json` 是本地缓存，重启应用或重新打开面板让它重建 |
| `acp` profile 打不开 GUI | 正常：`acp` 是自动化接入 profile（`dsh-base` + `dsh-acp-app`），不是桌面 UI；桌面端只加载 `desktop` |

---

## 12. 参考

- 应用内文档与更新通道：`resources\app-update.yml`（`channel: nightly`，`https://download.deepseek.com/dsh-desk/feeds/win-x64/`）
- 版本升级指南：应用内 `docs\upgrade-guide\<版本目录>\`（0.2.2-rc.1 ～ rc.5 的破坏性变更都在这里）
- dsh CLI 自带帮助：`dsh --help`、`dsh web --help`、`dsh plugin --help`、`dsh --dump-config-schema`
- bundle 与 row 的权威来源：应用内 设置 → 插件（对应 `plugin_manager` 的 `list_bundles` / `list_plugins`）
- 十个第三方 bundle 的 npm 包页：
  - <https://www.npmjs.com/package/ds-bot>
  - <https://www.npmjs.com/package/dsh-ppt>
  - <https://www.npmjs.com/package/dsh-hyperframes>
  - <https://www.npmjs.com/package/dsh-skin-market>
  - <https://www.npmjs.com/package/dsh-codex-effort-slider>
  - <https://www.npmjs.com/package/dsh-answer-me-with-html>
  - <https://www.npmjs.com/package/@changfenhuang/dsh-genui>
  - <https://www.npmjs.com/package/dsh-context>
  - <https://www.npmjs.com/package/agentero-dsh>
  - <https://www.npmjs.com/package/dsh-better-sidebar>
- `answer-me-with-html` 上游：<https://github.com/QingYunA/answer-me-with-html>
- Agentero 上游：<https://github.com/poco-ai/Agentero>

---

## 13. 最终安全边界

这份文档可以安全地作为迁移清单保存，但它不是凭据保险箱。任何时候都不要把以下内容写入 `harness/dsh.md` 或以未加密形式提交到 Git：

- `.credentials.yaml` 的任何 `secret` / `token` / `refs` 真实值；
- `OPENCODE_GO_API_KEY`、`K8S_15_API_KEY`、`MUZE_AI_API_KEY` 的实际 key；
- `k8s-15` 等内网 provider 的真实 host / IP / 端口（第 4.2 节已用 `<K8S_15_HOST>` 占位）；
- `sessions\**\session.v4.jsonl.zstd`、`attachments`、`storages\workspace.json`、`storages\session_projcache`；
- `%APPDATA%\@deepseek-ai\dsh-desktop\**`（含 `Preferences`、`IndexedDB`、`Local Storage`、`plugin-operations`）；
- 旧机器的 hostname、IP、端口、SSH identity 和登录凭据；
- `.anonymous-user-id`。

补充三条本机专属提醒：

1. **源 profile 默认预设是 `danger-full-access` + `never`**。这既是持久默认配置，也可能被会话单独选择覆盖；不在新电脑上自动复现。`never` 表示需要审批的动作直接被拒绝。
2. **遇到 `grantWrite` 失败不要关沙箱绕过**。使用 Windows 沙箱 ACL 诊断流程，并先确认实际路径和权限。
3. **Agentero vault 与 DS Bot 团队数据是用户内容**，不属于基础 profile 迁移包；按需单独审查、备份。

如果迁移过程中发现 `.credentials.yaml` 曾进入共享目录或压缩包，请在 provider 控制台轮换 key，而不是只删除文本。

---

## 14. 与 2026-11-19 快照的非模型差异

本次核对日期为 2026-11-27。模型和 provider 未同步；工作区、会话等易变历史统计未重新核验。

- desktop profile 的 bundle 清单从 19 项变为 20 项，新增 `ds-bot`；bundle 顺序也已调整，见第 5.2 节。清单本身不证明各行加载成功。
- 第三方依赖变化：`dsh-ppt` 0.25.0 → 0.36.0、`dsh-hyperframes` 0.11.5 → 0.14.0、`@changfenhuang/dsh-genui` 0.16.0 → 0.17.0、`dsh-context` 0.84.0 → 0.87.1、`dsh-skin-market` 0.1.81 → 0.1.83、`dsh-codex-effort-slider` 1.1.4 → 1.1.9；`ds-bot` 当前安装 0.3.10。
- HyperFrames 技能目录增加 `reverse-any-video`、`style-sampling`，目前共 23 个；当前会话另可见 `office-tools`、`ds-bot-manual`、`report-ds-bot-issue`、`goal-grill`。
- 用户 patch 新增 `ui-conversation.busyEnter: steer`，并持久设置 `permission.defaultPreset: danger-full-access`；前者按需迁移，后者不在迁移模板中自动复制。
- 用户级 `%USERPROFILE%\.dsh\AGENTS.md` 与工作区 `AGENTS.md` 同时存在；脚本只导出后者，前者需按需审查。
- `acp` 用户 patch 已非空；其模型内容不在本次同步范围。
- 修正技能复制脚本中的通配符用法，原始 patch 不再自动导出，避免携带未审查的私人配置。

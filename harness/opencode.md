# OpenCode Windows 本地配置迁移手册

> 快照日期：2026-11-11（Asia/Shanghai）  
> 源环境：Windows 10 Pro 22H2、OpenCode Desktop `2.2.7`、内置 OpenCode CLI `2.2.7`  
> 目标环境：另一台 Windows 电脑  
> 迁移范围：OpenCode V2 配置、模型与提供商连接方式、CLI/TUI 设置、技能、AGENTS 规则、agents/commands/plugins/MCP 配置、Code Mode 相关设置和必要依赖  
> 不迁移：登录凭据、API token、会话、项目数据库、日志、shell 历史、快照、缓存和其他私有状态

本文档是一个可复现的快照，不是“把 `%USERPROFILE%\.config\opencode` 整个目录压缩过去”的教程。OpenCode 的配置、凭据、会话和项目状态分散在多个目录；其中 `opencode.db` 同时保存凭据和聊天记录，`service.json` 保存本机后台服务的连接密码，桌面应用的 Local Storage 保存窗口和草稿状态。这些都必须由新电脑重新生成。真正需要迁移的是 `opencode.json(c)`、`cli.json`、`AGENTS.md`、`skills/`，以及你自己新增的 agents、commands、plugins 和 themes。

配套的 Codex 版本见 `harness/codex.md`；两份文档不要混用字段和目录。

---

## 0. 一页式迁移清单

推荐顺序：

1. 在新电脑安装 OpenCode Desktop，至少启动一次，完成首次引导。
2. 用 `/connect` 连接 **OpenCode Go**，再用 `/models` 选择 `DeepSeek V4.1 Flash`，确认模型可用。
3. 在旧电脑运行“第 3 节”的导出脚本，生成不包含 `opencode.db`、`service.json` 和桌面状态的迁移包。
4. 在新电脑运行“第 4 节”的恢复脚本，复制技能、AGENTS 规则和可选配置。
5. 按“第 5 节”创建 `~/.config/opencode/opencode.jsonc`。本机原本没有这个文件，模板只需要少量字段，不要照搬 Codex 的 TOML。
6. 如果要复现 TUI 主题、键位或通知，再创建 `~/.config/opencode/cli.json`；本机当前没有这个文件，全部使用默认值。
7. 不要复制 `service.json`、`opencode.db`、`%APPDATA%\ai.opencode.desktop` 下的 Local Storage、Cookies、草稿和日志。
8. 打开新会话，运行第 11 节的验收命令，确认配置、技能、模型和后台服务均正常。

最小验收标准：

- `opencode debug paths` 能输出 `config`、`data`、`state`、`db` 等路径，且指向新电脑的用户目录。
- `opencode debug config` 至少列出 `~/.config/opencode` 这个配置源；如果新建了 `opencode.jsonc`，该目录仍应出现。
- `opencode auth list` 显示 `OpenCode Go  OpenCode Go  stored`。
- `opencode models` 的输出包含 `opencode-go/deepseek-v4.1-flash`。
- `opencode mcp list` 显示 `No MCP servers configured`，除非你有意新增 MCP。
- `opencode plugin list` 显示 `No plugins found`；`opencode plugin list --builtin` 仍能看到约 92 个内置插件。
- `~/.config/opencode/skills` 下有 25 个目录：24 个可调用技能加 1 个 `_shared` 支持包。
- `~/.config/opencode/AGENTS.md` 与工作区根目录的 `AGENTS.md` 内容一致。
- 新会话发送“只回复 OK”能正常返回；再用 `@tech-paper-template` 或 `@citation-management` 测试一次技能加载。

> 下面的 `opencode ...` 是通用写法；本机没有把 CLI 加到 PATH，实际执行时用第 2.8 节的 `$cli` 变量，或写 `& $cli ...`。

> 说明：OpenCode 没有 Codex 的 `doctor` 这种统一诊断命令。对应的检查工具是 `opencode debug paths`、`opencode debug config`、`opencode debug agents`、`opencode service status`、`opencode mcp list`、`opencode plugin list` 和 `opencode api get /api/info`。

---

## 1. 当前环境快照

| 项目 | 当前值 |
|---|---|
| 操作系统 | Windows 10.0.19045，64 位，中文系统 |
| OpenCode Desktop | `2.2.7`（文件版本 `2.2.7.0`） |
| 内置 OpenCode CLI | `2.2.7` |
| Desktop 安装目录 | `%LOCALAPPDATA%\Programs\ai.opencode.desktop` |
| Desktop 附带的 CLI | `%APPDATA%\ai.opencode.desktop\cli\2.2.7-x64\opencode-cli.exe` |
| `opencode` 是否在 PATH | 否；本机 `where.exe opencode` 没有结果 |
| 配置目录 | `%USERPROFILE%\.config\opencode` |
| 数据目录 | `%USERPROFILE%\.local\share\opencode` |
| 状态目录 | `%USERPROFILE%\.local\state\opencode` |
| 缓存目录 | `%USERPROFILE%\.cache\opencode` |
| 临时目录 | `%LOCALAPPDATA%\Temp\opencode` |
| 全局配置 | 只有 `AGENTS.md`、`service.json`、`skills/`；没有 `opencode.json(c)` |
| CLI 配置 | 没有 `cli.json`；TUI 使用默认主题和默认键位 |
| 全局 AGENTS 规则 | `%USERPROFILE%\.config\opencode\AGENTS.md`，283 字节 |
| 工作区 AGENTS 规则 | `C:\workspace\2026Spring2Winter\AGENTS.md`，与全局文件哈希相同 |
| 默认/最近使用的 agent | `build` |
| 默认/最近使用的模型 | `opencode-go/deepseek-v4.1-flash`，variant `max` |
| 提供商 | 内置 `OpenCode Go`（provider ID `opencode-go`） |
| 认证方式 | `opencode auth list` 显示 `OpenCode Go  stored`；凭据不在配置文件中 |
| 可用模型 | `opencode-go` 目录下 24 个模型；另有 `opencode/*` 免费模型 |
| 用户插件 | 0 个 |
| 内置插件 | 92 个 |
| MCP 服务器 | 0 个 |
| 用户技能 | 25 个目录，24 个可调用技能 + `_shared`；919 个文件，约 31.8 MB |
| `.agents` 兼容技能 | `answer-me-with-html` 一份，另有 `.skill-lock.json` |
| Code Mode | 启用；工具目录含 `execute`、`browser`、`opencode` 命名空间 |
| 后台服务 | 2.2.7，本机 `http://127.0.0.1:28894`，PID 会变化 |
| 数据库 | `opencode.db` 约 44 MB，另有 WAL/SHM 文件 |
| 默认 shell | PowerShell |
| 可选依赖 | Python 3.14.10、Node.js 26.13.0、npm 11.20.0、Git 2.56.0.windows.4 |
| 未安装 | R/Rscript、Pandoc、LibreOffice、系统 TeX（Tectonic/latexmk） |

### 1.1 快照的边界

- Desktop 和 CLI 版本会随更新变化。本文档记录的是 2026-11-11 的版本，不要求新电脑固定使用 `2.2.7`，但建议先让 Desktop 和它附带的 CLI 保持一致。
- `%APPDATA%\ai.opencode.desktop\cli\<版本>-x64\opencode-cli.exe` 的路径包含版本号；升级后路径会变化。不要把这个绝对路径写死到脚本或插件里。
- `opencode.db` 保存会话、消息、项目记录、权限审批，以及 `credential`/`account` 表中的凭据。它不是“设置文件”，不能作为配置迁移。
- `service.json` 保存后台服务的连接密码、PID 和端口。两台机器的服务实例不同，复制会导致客户端连到错误的进程。
- OpenCode 没有 Codex 那种 OS 级 sandbox。它的 `permissions` 是工具级规则，`shell` 仍以当前 Windows 用户权限执行。不要把“默认 allow”误认为安全隔离。
- 桌面应用的窗口位置、主题、字体、草稿、Cookies、Local Storage 和日志属于 Electron 本地状态，不是 `opencode.json` 的一部分；需要在新电脑重新设置。
- 当前 `build` agent 的内置策略把 `browser` 和 `skill: browser` 设为 `deny`。浏览器工具虽然出现在 Code Mode 目录中，实际调用仍受权限约束；需要浏览器时再显式放开。

### 1.2 明确不迁移的内容

不要把下面这些内容放进迁移包，也不要提交到仓库：

- `%USERPROFILE%\.local\share\opencode\opencode.db`、`opencode.db-wal`、`opencode.db-shm`。
- `opencode.db` 中的 `credential`、`account`、`control_account` 表，以及任何 OAuth/API 凭据。
- `%USERPROFILE%\.config\opencode\service.json`。
- `%USERPROFILE%\.local\state\opencode\service.json`。
- `%USERPROFILE%\.local\share\opencode\log\`、`shell\`、`snapshot\`、`tool-output\`、`repos\`。
- `%USERPROFILE%\.cache\opencode\bin\` 下的自动下载工具（例如 `rg.exe`）。
- `%APPDATA%\ai.opencode.desktop` 下的 `Local Storage`、`Session Storage`、`Network\Cookies`、`Cache`、`Code Cache`、`GPUCache`、`logs`、`drafts.sqlite`、`window-state-*.json`、`opencode.settings`。
- 任何 `.env`、SSH 私钥、Cookie、OAuth token、API key、代理密码。
- 旧机器的项目数据库、会话、附件、工作区私有文件。
- 旧机器的 `opencode-cli.exe` 二进制；它由 Desktop 管理，升级后应使用新版本。
- `.agents\.skill-lock.json` 不是密钥，可以复制；但不要把它和 `opencode.db` 混在一起。

---

## 2. OpenCode 特有的机制（迁移前必读）

这一节解释为什么不能把 Codex 的迁移经验直接套过来。OpenCode V2 的配置形状、扩展方式和运行架构都与 Codex 不同。

### 2.1 配置是 JSON/JSONC，不是 TOML

本文档按 OpenCode V2 编写。OpenCode 使用 `opencode.json` 或 `opencode.jsonc`，支持注释和尾逗号。建议保留 schema：

```jsonc
{
  "$schema": "https://opencode.ai/config.json"
}
```

V2 的字段名与 V1 有明显差异。迁移时不要使用旧的 V1 字段：

| V1 旧写法 | V2 新写法 |
|---|---|
| `permission` | `permissions` |
| `bash` | `shell` |
| `task` | `subagent` |
| `mcp.<name>` | `mcp.servers.<name>` |
| `agent` | `agents` |
| `command` | `commands` |
| `plugin` | `plugins` |

如果看到旧字段，先查 V2 文档再改，不要凭记忆替换。schema 可能仍然接受某些 V1 字段，但不要因为“能解析”就继续使用它们。

Codex 和 OpenCode 的技能都是 `SKILL.md` 目录，技能正文和脚本通常可以复用；但 Codex 的 `config.toml`、插件 marketplace、MCP 配置和 agent/command 定义不能直接搬到 OpenCode。迁移技能时按 OpenCode 的目录和 ID 规则重新放置，不要复制整个 `.codex` 目录。

### 2.2 配置有全局、项目、系统三层

| 层级 | 位置 | 说明 |
|---|---|---|
| 全局 | `~/.config/opencode/opencode.json(c)` | 对当前用户的所有项目生效 |
| 项目 | `<项目>/opencode.json(c)` 或 `<项目>/.opencode/opencode.json(c)` | 从当前目录向上搜索到文件系统根 |
| 系统 | Windows `%ProgramData%\opencode` | 机器级配置；可加载 `agents/`、`commands/`、`skills/`、`plugins/`；本机为空 |

合并顺序从低到高：全局 → 较远祖先项目 → 较近项目。所有 `.opencode/opencode.json(c)` 覆盖所有直接的 `opencode.json(c)`，系统配置最高。配置保存后会自动重载，不需要重启 OpenCode；要强制重载可以用 `opencode reload`。

本机没有项目级配置，也没有系统级配置，只有一个全局配置目录。因此迁移时只需要处理 `~/.config/opencode`。

### 2.3 `opencode.json` 和 `cli.json` 是两套设置

| 文件 | 作用 | 位置 |
|---|---|---|
| `opencode.json(c)` | 服务端/项目配置：模型、agent、权限、MCP、插件、技能来源、指令 | 全局或项目 |
| `cli.json` | 终端客户端设置：主题、键位、会话显示、通知、diff 视图 | 只有全局，`~/.config/opencode/cli.json` |

`cli.json` 没有项目级文件，也不能放进 `opencode.json`。如果你只迁移了 `opencode.json`，TUI 主题和键位不会跟着走；反过来，只迁移 `cli.json` 也不会恢复模型和权限。本机 `cli.json` 不存在，说明 TUI 全部使用默认值。

### 2.4 五种扩展方式，不要混淆

| 机制 | 作用 | 典型位置 | 调用方式 |
|---|---|---|---|
| Skill | 可复用的任务说明和脚本 | `~/.config/opencode/skills/<id>/SKILL.md` | 模型通过 `skill` 工具加载，或用户写 `@<id>` |
| Agent | 一套模型、系统提示和权限配置 | `~/.config/opencode/agents/<name>.md` 或 `agents` 配置 | 主 agent 或 `subagent` 工具 |
| Command | 斜杠命令的提示模板 | `~/.config/opencode/commands/<name>.md` 或 `commands` 配置 | `/name` |
| Plugin | 用代码扩展工具、钩子、TUI 或桌面 UI | npm 包或本地目录 | 自动加载 |
| MCP server | 外部工具/资源服务器 | `mcp.servers` 配置 | 工具名 `<server>_<tool>`，默认经 Code Mode 暴露 |

本机只有 Skill 和内置能力；没有自定义 agent、command、plugin 或 MCP。迁移的重点因此是技能和 `AGENTS.md`。

### 2.5 Skill 的发现顺序和 ID 规则

OpenCode 自动搜索：

| 范围 | 来源 |
|---|---|
| 全局 | `~/.config/opencode/skills` |
| 全局兼容 | `~/.claude/skills`、`~/.agents/skills` |
| 项目 | `.opencode/skills` |
| 项目兼容 | `.claude/skills`、`.agents/skills` |

每个来源可以是：

```text
skills/
├── review.md
└── git-release/
    └── SKILL.md
```

- 根目录的 `*.md` 是一个技能。
- 只有文件名恰好为 `SKILL.md` 的嵌套文件才算技能；`skills/teams/release/SKILL.md` 的 ID 是 `release`。
- 一个包含 `SKILL.md` 的目录就是一个技能，OpenCode 不会继续在该目录里面找更多技能。
- 隐藏目录、`node_modules` 和超过六层的嵌套会被跳过。
- 技能 ID 由路径决定，区分大小写；frontmatter 的 `name` 只是显示名。
- 没有 `description` 的技能不会出现在模型的可调用列表里；`metadata.opencode/autoinvoke: false` 可以让它只支持显式加载。
- 在 Codex 里常见 `$skill-name` 的写法；OpenCode 的显式调用写法是 `@skill-id`，ID 来自目录名，不是 frontmatter 的 `name`。模型内部则通过 `skill` 工具按 ID 加载。

优先级从低到高：

```text
内置技能
< ~/.claude/skills
< ~/.agents/skills
< ~/.config/opencode/skills
< 项目 .opencode/skills
< opencode.json 中显式 skills 数组
```

这解释了一个本机现象：`answer-me-with-html` 同时存在于 `~/.config/opencode/skills` 和 `~/.agents/skills`，但 `~/.config/opencode/skills` 的副本优先级更高，实际加载的是它，而不是 `.agents` 下更新的副本。迁移前应先决定保留哪一份（见第 4.3 节）。

### 2.6 权限是工具级规则，不是 OS sandbox

OpenCode 的 `permissions` 是“动作 + 资源 + 效果”的有序规则：

```jsonc
{
  "permissions": [
    { "action": "shell", "resource": "*", "effect": "ask" },
    { "action": "shell", "resource": "git status *", "effect": "allow" },
    { "action": "shell", "resource": "git push *", "effect": "deny" }
  ]
}
```

- 最后一条匹配的规则生效。
- 效果有 `allow`、`ask`、`deny`。
- 没有规则匹配时默认 `ask`。
- Windows 上路径匹配不区分大小写，反斜杠会规范化为斜杠。
- `shell` 仍然以当前 Windows 用户的文件系统、进程和网络权限运行；OpenCode 没有 Codex 那种可切换的 OS sandbox 模式。
- 默认基础策略允许所有动作，只对 `*.env`、`*.env.*` 读取要求确认，`*.env.example` 允许读取。
- `external_directory` 默认没有 ask 规则，所以项目外的读写通常不会弹确认；需要更严的策略时，自己追加 `ask` 或 `deny`。

本机没有自定义 `permissions`，所以运行的是默认策略。迁移模板会保持这一点，并在第 5.4 节给出可选的收紧方案。在权限提示里选择“Allow always”会把项目级允许规则写入本机数据库，而不是写入 `opencode.json`；迁移不会带走这些已保存的审批。新电脑需要重新确认，或者把它们显式写进配置。

### 2.7 MCP 默认走 Code Mode

OpenCode V2 的 MCP 配置在 `mcp.servers` 下：

```jsonc
{
  "mcp": {
    "servers": {
      "context7": {
        "type": "remote",
        "url": "https://mcp.context7.com/mcp"
      }
    }
  }
}
```

- 远程 MCP 默认使用 OAuth；需要登录时在 TUI 运行 `/mcps`，不要用 shell 里的 `opencode mcp auth` 做交互式登录（授权链接可能被后台输出吞掉）。
- 本地 MCP 用 `type: "local"` 和 `command` 数组。
- `codemode` 默认 `true`：MCP 工具不会直接铺在模型的原生工具列表里，而是通过 Code Mode 的 `execute` 工具按 `<server>_<tool>` 暴露。
- 如果某个服务器必须使用原生工具列表，设置 `"codemode": false`。
- `execute` 权限被 deny 时，Code Mode 和只能通过它访问的工具都会消失。

本机没有配置 MCP，`opencode mcp list` 的输出是 `No MCP servers configured`。因此迁移包不需要包含 MCP 配置，也不存在旧机器 MCP 路径需要清理。

### 2.8 后台服务与 Desktop 附带的 CLI

OpenCode 采用客户端/服务端架构：

- TUI、Desktop、Web 客户端连接同一个用户级后台服务。
- 服务拥有会话、配置、插件、权限和工具执行。
- `opencode service status` 查看服务 URL；`opencode service restart` 只在服务卡死时使用，不要用它来“应用配置”。
- `opencode --standalone` 启动一个私有服务；`opencode --server <url>` 连接指定服务。
- `service.json` 保存本机服务密码；`~/.local/state/opencode/service.json` 还保存 PID、URL/端口和版本。它们属于运行时状态，不是配置。

本机 Desktop 把 CLI 放在 `%APPDATA%\ai.opencode.desktop\cli\2.2.7-x64\opencode-cli.exe`，并且没有把 `opencode` 加到 PATH。迁移后不要复制这个二进制；让新电脑的 Desktop 重新生成对应版本的 CLI。Desktop 还会注入 `OPENCODE_CLIENT=desktop`、`OPENCODE_TERMINAL=1`、`OPENCODE_EXPERIMENTAL_FILEWATCHER=true` 等运行时变量；这些不是配置项，不要写进 `opencode.json`。若要在 PowerShell 里方便地调用，可以设置一个临时变量：

```powershell
$cli = Get-ChildItem (Join-Path $env:APPDATA 'ai.opencode.desktop\cli') `
  -Filter 'opencode-cli.exe' -Recurse -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName
& $cli --version
```

### 2.9 模型选择是“会话级”的，凭据在数据库里

- `opencode.json` 的 `model` 只设置新工作的默认 provider/model；根级 `model` 目前不会保留 `#variant`。
- `/models` 选择的是当前会话的模型，不会改写配置文件。
- variant（例如 `low`、`high`、`max`）要在会话、agent、command 或 `opencode run --model ...#max` 中指定。
- OpenCode Go 的凭据由 `/connect` 写入本机数据库（本机可见 `credential`/`account` 表），不在 `opencode.json` 中，也不在 `auth.json` 中。
- `opencode auth list` 只显示提供商和“stored”状态，不显示 token。
- 新电脑必须重新 `/connect`；复制 `opencode.db` 既会把会话和项目带过去，也可能因环境差异导致凭据不可用。

本机最近会话的模型是 `opencode-go/deepseek-v4.1-flash`，variant 为 `max`；这不是写在配置文件里的默认值，而是会话记录中的选择。迁移后要重新选一次，或在配置里固定默认模型。

### 2.10 `AGENTS.md` 是主要的项目规则文件

OpenCode V2 自动发现的项目规则文件是 `AGENTS.md`，不会把 `CLAUDE.md` 当作回退；此外可以用 `instructions` 追加文件。加载顺序是：

```text
~/.config/opencode/AGENTS.md
→ 当前工作区向上的各级 AGENTS.md（最近的最后加载）
→ 配置中 instructions 数组追加的文件
```

子目录里的 `AGENTS.md` 会在 agent 读到该区域时再加载。全局规则和项目规则是合并关系，不是覆盖关系；冲突时不会自动解决。

本机的全局 `AGENTS.md` 和工作区根目录 `AGENTS.md` 内容完全相同，都是“默认不要生成 HTML，只有显式调用 `@answer-me-with-html` 或用户要求 HTML 时才生成”。迁移时两份都要处理：全局文件放到新电脑的 `~/.config/opencode/AGENTS.md`，工作区文件放到新工作区的最上层项目父目录。

### 2.11 配置文件与数据库的边界

| 内容 | 位置 | 是否可迁移 |
|---|---|---|
| 模型默认值、权限、MCP、插件、技能来源 | `opencode.json(c)` | 可以，手工复制或按模板重建 |
| TUI 主题、键位、通知 | `cli.json` | 可以 |
| 技能 | `skills/` | 可以 |
| 全局/项目规则 | `AGENTS.md` | 可以 |
| 自定义 agent/command | `agents/`、`commands/` | 可以 |
| 自定义 plugin | `plugins/` 或 npm 包 | 可以，但建议重装 npm 包 |
| 凭据 | `opencode.db` 的 `credential` 表 | 不迁移 |
| 会话、消息、项目记录 | `opencode.db` | 不迁移 |
| 后台服务连接信息 | `service.json` | 不迁移 |
| 窗口、主题、草稿、Cookies | `%APPDATA%\ai.opencode.desktop` | 不迁移 |
| 日志、shell 输出、快照、工具输出 | `~/.local/share/opencode` 子目录 | 不迁移 |

---

## 3. 旧电脑：生成迁移资源包

下面的脚本只导出可迁移的用户资产，不复制 `opencode.db`、`service.json` 和桌面状态。请在旧电脑的 PowerShell 中运行。如果先把脚本保存成 `.ps1` 文件，请使用 UTF-8 编码；中文注释在 ANSI 代码页下可能被错误解码，甚至吞掉下一行。

```powershell
$ErrorActionPreference = 'Stop'

$configHome = Join-Path $env:USERPROFILE '.config\opencode'
$agentsHome = Join-Path $env:USERPROFILE '.agents'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$bundleRoot = Join-Path ([Environment]::GetFolderPath('Desktop')) "opencode-migration-$stamp"

$configOut = Join-Path $bundleRoot 'config'
$skillsOut = Join-Path $configOut 'skills'
$compatOut = Join-Path $bundleRoot 'agents-compat'
$snapshotOut = Join-Path $bundleRoot 'snapshot'

New-Item -ItemType Directory -Path $configOut -Force | Out-Null
New-Item -ItemType Directory -Path $skillsOut -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $compatOut 'skills') -Force | Out-Null
New-Item -ItemType Directory -Path $snapshotOut -Force | Out-Null

# 1. 可迁移的配置文件
foreach ($name in @('opencode.json', 'opencode.jsonc', 'cli.json', 'AGENTS.md')) {
  $source = Join-Path $configHome $name
  if (Test-Path -LiteralPath $source) {
    Copy-Item -LiteralPath $source -Destination $configOut -Force
  }
}

# 2. 可迁移的目录：agents、commands、plugins、themes
foreach ($name in @('agents', 'commands', 'plugins', 'themes')) {
  $source = Join-Path $configHome $name
  if (Test-Path -LiteralPath $source) {
    Copy-Item -LiteralPath $source -Destination $configOut -Recurse -Force
  }
}

# 3. 全部用户技能，包含 _shared 支持包和 markdown-to-word 的 node_modules
$skillsSource = Join-Path $configHome 'skills'
if (Test-Path -LiteralPath $skillsSource) {
  Get-ChildItem -LiteralPath $skillsSource -Directory |
    ForEach-Object {
      Copy-Item -LiteralPath $_.FullName `
        -Destination $skillsOut -Recurse -Force
    }
}

# 4. .agents 兼容技能和安装记录
$compatSkill = Join-Path $agentsHome 'skills\answer-me-with-html'
if (Test-Path -LiteralPath $compatSkill) {
  Copy-Item -LiteralPath $compatSkill `
    -Destination (Join-Path $compatOut 'skills') -Recurse -Force
}
$skillLock = Join-Path $agentsHome '.skill-lock.json'
if (Test-Path -LiteralPath $skillLock) {
  Copy-Item -LiteralPath $skillLock -Destination $compatOut -Force
}

# 5. 工作区规则
$workspaceAgents = 'C:\workspace\2026Spring2Winter\AGENTS.md'
if (Test-Path -LiteralPath $workspaceAgents) {
  Copy-Item -LiteralPath $workspaceAgents `
    -Destination (Join-Path $bundleRoot 'workspace-AGENTS.md') -Force
}

# 6. 本手册
$handbook = 'C:\workspace\2026Spring2Winter\harness\opencode.md'
if (Test-Path -LiteralPath $handbook) {
  Copy-Item -LiteralPath $handbook -Destination $bundleRoot -Force
}

# 7. 只读快照：版本、路径、配置源、agent、认证提供商、MCP、插件、模型
$cli = Get-ChildItem (Join-Path $env:APPDATA 'ai.opencode.desktop\cli') `
  -Filter 'opencode-cli.exe' -Recurse -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName

if ($cli) {
  & $cli --version              | Out-File -Encoding utf8 (Join-Path $snapshotOut 'version.txt')
  & $cli debug paths            | Out-File -Encoding utf8 (Join-Path $snapshotOut 'paths.txt')
  & $cli debug config           | Out-File -Encoding utf8 (Join-Path $snapshotOut 'config-sources.json')
  & $cli debug agents           | Out-File -Encoding utf8 (Join-Path $snapshotOut 'agents.json')
  & $cli auth list              | Out-File -Encoding utf8 (Join-Path $snapshotOut 'auth.txt')
  & $cli mcp list               | Out-File -Encoding utf8 (Join-Path $snapshotOut 'mcp.txt')
  & $cli plugin list            | Out-File -Encoding utf8 (Join-Path $snapshotOut 'plugins.txt')
  & $cli plugin list --builtin  | Out-File -Encoding utf8 (Join-Path $snapshotOut 'builtin-plugins.txt')
  & $cli models                 | Out-File -Encoding utf8 (Join-Path $snapshotOut 'models.txt')
}
else {
  'opencode CLI not found; only files were exported.' |
    Out-File -Encoding utf8 (Join-Path $snapshotOut 'cli-missing.txt')
}

$zipPath = "$bundleRoot.zip"
Compress-Archive -Path (Join-Path $bundleRoot '*') -DestinationPath $zipPath -Force
Write-Host "迁移资源包已生成：$zipPath"
```

检查点：

- `config\skills` 中应有 25 个目录，其中包含 `_shared`。
- `config\skills\markdown-to-word` 会包含 `node_modules`，这是该技能自带的 Node 依赖，压缩前约 27.4 MB；本次实测压缩包约 10 MB。
- `agents-compat\skills\answer-me-with-html` 和 `agents-compat\.skill-lock.json` 应存在。
- `config\AGENTS.md` 和 `workspace-AGENTS.md` 应存在。
- `snapshot\` 中应有 `version.txt`、`paths.txt`、`config-sources.json`、`agents.json`、`auth.txt`、`mcp.txt`、`plugins.txt`、`builtin-plugins.txt`、`models.txt`。
- 压缩包中不应有 `opencode.db`、`opencode.db-wal`、`opencode.db-shm`、`service.json`、`log`、`shell`、`snapshot`、`tool-output`、`repos`、`drafts.sqlite`、`Cookies` 或 `Local Storage`。
- 脚本不会复制 `%APPDATA%\ai.opencode.desktop` 和 `%LOCALAPPDATA%\Programs\ai.opencode.desktop`。
- 本机没有项目级 `opencode.json(c)`；如果某个项目有自己的 `.opencode/opencode.json(c)`，需要在旧电脑单独收集。
- 如果 `opencode.jsonc` 的 `instructions` 或 `references` 指向仓库外的文件，脚本不会自动收集；按配置里的路径单独复制。

迁移包的结构大致如下：

```text
opencode-migration-<时间戳>/
├── config/
│   ├── opencode.jsonc        # 如果旧机器有
│   ├── cli.json              # 如果旧机器有
│   ├── AGENTS.md
│   └── skills/               # 25 个目录，包含 _shared
├── agents-compat/
│   ├── skills/answer-me-with-html/
│   └── .skill-lock.json
├── workspace-AGENTS.md
├── snapshot/
└── opencode.md
```

### 3.1 迁移包不包含什么

即使脚本只复制“用户资产”，也请再检查一次压缩包：

- 没有 `service.json`。它包含本机服务密码，复制后新电脑会连到旧端口或旧 PID。
- 没有 `opencode.db`。它包含凭据、会话和项目记录，属于私有状态。
- 没有 `auth list` 之外的任何认证信息。`auth.txt` 只有提供商名称和 `stored` 状态。
- 没有桌面应用的 Local Storage、Cookies、草稿和日志。
- 没有 `.env`、SSH 私钥、代理配置、API key。

`snapshot\` 里的 `paths.txt` 和 `agents.json` 会包含本机用户目录和 agent 提示，属于个人信息；不要把整个迁移包提交到公共仓库。如果确实需要保留会话记录供个人查阅，应单独做加密备份，不要放进这个迁移包，也不要在新电脑恢复 `opencode.db`。

---

## 4. 新电脑：恢复基础资源

先安装 OpenCode Desktop 并启动一次，让应用创建新的 `%USERPROFILE%\.config\opencode`、`%USERPROFILE%\.local\share\opencode` 和 `%LOCALAPPDATA%\Temp\opencode`。然后完成 OpenCode Go 连接：

```text
/connect
# 选择 OpenCode Go，粘贴 API key
/models
# 选择 DeepSeek V4.1 Flash
```

如果只需要最新模型、不需要固定 `max` variant，选择模型即可；如果要复现旧机器的推理强度，再在模型选择器里切到 `max`，或在命令行使用 `opencode run --model opencode-go/deepseek-v4.1-flash#max`。

### 4.1 恢复脚本

把资源包解压到桌面，将下面的 `$bundleRoot` 改成实际目录。脚本不会覆盖 `service.json`，因为根本不会复制它。

```powershell
$ErrorActionPreference = 'Stop'

$bundleRoot = Join-Path ([Environment]::GetFolderPath('Desktop')) 'opencode-migration-替换为时间戳'
$configHome = Join-Path $env:USERPROFILE '.config\opencode'
$agentsHome = Join-Path $env:USERPROFILE '.agents'

New-Item -ItemType Directory -Path $configHome -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $configHome 'skills') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $agentsHome 'skills') -Force | Out-Null

# 1. 配置文件
foreach ($name in @('opencode.json', 'opencode.jsonc', 'cli.json', 'AGENTS.md')) {
  $source = Join-Path $bundleRoot "config\$name"
  if (Test-Path -LiteralPath $source) {
    Copy-Item -LiteralPath $source -Destination $configHome -Force
  }
}

# 2. agents、commands、plugins、themes
foreach ($name in @('agents', 'commands', 'plugins', 'themes')) {
  $source = Join-Path $bundleRoot "config\$name"
  if (Test-Path -LiteralPath $source) {
    $dest = Join-Path $configHome $name
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
    Get-ChildItem -LiteralPath $source -Force |
      Copy-Item -Destination $dest -Recurse -Force
  }
}

# 3. 技能，包含 _shared
$skillsSource = Join-Path $bundleRoot 'config\skills'
if (Test-Path -LiteralPath $skillsSource) {
  Get-ChildItem -LiteralPath $skillsSource -Directory |
    ForEach-Object {
      Copy-Item -LiteralPath $_.FullName `
        -Destination (Join-Path $configHome 'skills') -Recurse -Force
    }
}

# 4. .agents 兼容技能和安装记录
$compatSkill = Join-Path $bundleRoot 'agents-compat\skills\answer-me-with-html'
if (Test-Path -LiteralPath $compatSkill) {
  Copy-Item -LiteralPath $compatSkill `
    -Destination (Join-Path $agentsHome 'skills') -Recurse -Force
}
$skillLock = Join-Path $bundleRoot 'agents-compat\.skill-lock.json'
if (Test-Path -LiteralPath $skillLock) {
  Copy-Item -LiteralPath $skillLock -Destination $agentsHome -Force
}

# 5. 工作区规则：按新电脑的工作区布局放置
$workspaceAgents = Join-Path $bundleRoot 'workspace-AGENTS.md'
if (Test-Path -LiteralPath $workspaceAgents) {
  $workspaceAgentsDest = 'C:\workspace\2026Spring2Winter\AGENTS.md'
  New-Item -ItemType Directory -Path (Split-Path $workspaceAgentsDest) -Force | Out-Null
  Copy-Item -LiteralPath $workspaceAgents `
    -Destination $workspaceAgentsDest -Force
}

Write-Host "配置目录：$configHome"
Write-Host "技能目录：$(Join-Path $configHome 'skills')"
```

如果新电脑的工作区不是 `C:\workspace\2026Spring2Winter`，把最后一条 `Copy-Item` 的目标改成新工作区最上层项目父目录，确保它覆盖需要该规则的所有仓库。

### 4.2 不要复制 `service.json`

启动 Desktop 后，下面两个文件会由应用重新生成：

```text
%USERPROFILE%\.config\opencode\service.json
%USERPROFILE%\.local\state\opencode\service.json
```

`~/.config/opencode/service.json` 主要保存服务密码；`~/.local/state/opencode/service.json` 还保存 PID、URL/端口和版本。迁移后如果发现客户端连不上服务，正确做法是关闭 OpenCode，删除这两个 `service.json`，再重新启动 Desktop；不要从旧机器复制，也不要把旧值手工填进去。

### 4.3 技能目录的两种处理方式

本机 `answer-me-with-html` 同时存在两份：

| 位置 | 大小 | 修改时间 | 优先级 |
|---|---:|---|---|
| `~/.config/opencode/skills/answer-me-with-html/SKILL.md` | 24,598 字节 | 2026-10-26 | 较高 |
| `~/.agents/skills/answer-me-with-html/SKILL.md` | 27,012 字节 | 2026-11-11 | 较低 |

`.config` 的副本较旧，但优先级更高，所以 OpenCode 实际加载的是旧版。迁移时不要盲目保留两份：

- 方案 A（推荐）：先比较两份 `SKILL.md` 的差异，确认 `.agents` 下较新的内容确实是你想要的，再把它同步到 `.config` 副本，最后只保留一份。
- 方案 B：删除 `~/.config/opencode/skills/answer-me-with-html`，让 `.agents` 的副本生效；但这样会改变技能来源和优先级，需确认新会话能发现它。
- 方案 C：保留两份，明确知道 `.config` 胜出；这只适合你确实想固定旧版的情况。

无论选哪种，`_shared` 都必须保留在 `~/.config/opencode/skills/_shared`，因为 `nature-paper2ppt`、`nature-reader` 等技能会通过相对路径读取它。

---

## 5. 配置模板

> 下面的 PowerShell 示例假设已经按第 2.8 节定义了 `$cli` 变量。

### 5.1 全局 `opencode.jsonc`

本机没有这个文件，模型是靠会话选择和 OpenCode Go 的认证状态生效的。为了让新电脑的新会话有确定的默认模型，建议创建：

```jsonc
{
  "$schema": "https://opencode.ai/config.json",

  // 默认模型。provider 和 model ID 必须与 opencode models 的输出一致。
  "model": "opencode-go/deepseek-v4.1-flash",

  // 默认主 agent。本机使用 build。
  "default_agent": "build"
}
```

保存到：

```text
%USERPROFILE%\.config\opencode\opencode.jsonc
```

说明：

- 根级 `model` 只保留 provider/model，不保留 `#variant`。旧机器的 `max` 是会话级选择；需要固定时，在会话里选 `max`，或在 agent/command 的 `model` 中写 `opencode-go/deepseek-v4.1-flash#max`。
- 不需要把技能目录写进 `skills` 数组。`~/.config/opencode/skills` 是自动发现路径，重复声明反而会增加优先级和重复 ID 的风险。
- 不需要把 `AGENTS.md` 写进 `instructions`。全局 `~/.config/opencode/AGENTS.md` 和项目根目录的 `AGENTS.md` 会自动加载。
- 不要在这个文件里写 API key。OpenCode Go 用 `/connect` 存储凭据；自定义 provider 用 `{env:VAR}` 或 `{file:...}` 引用。
- 如果新电脑安装的是更新版本，模型 ID 可能变化。先运行 `opencode models`，确认输出中确实有 `opencode-go/deepseek-v4.1-flash`，再写进配置。

### 5.2 模型与 variant

本机可用的 `opencode-go` 模型包括：

| 模型 | 说明 | variant |
|---|---|---|
| `opencode-go/deepseek-v4.1-flash` | 当前默认，DeepSeek V4.1 Flash 1017 | `low`、`high`、`max` |
| `opencode-go/kimi-k3.1-pro` | Kimi K3.1 Pro | `low`、`high`、`max` |
| `opencode-go/minimax-m3.1-flash` | MiniMax M3.1 Flash | `low`、`medium`、`high`、`xhigh`、`max` |
| `opencode-go/gemini-4-argon` | Gemini 4 Argon | `low`、`medium`、`high` |
| `opencode-go/claude-haiku-5-5` | Claude Haiku 5.5 | `none`、`low`、`medium`、`high`、`xhigh`、`max` |

完整列表以 `opencode models` 为准。选择 variant 的方式：

```powershell
# 单次运行
& $cli run --model "opencode-go/deepseek-v4.1-flash#max" "只回复 OK"
```

在 TUI 中，用 `/models` 选择模型，再用 `Ctrl+T`（默认 `variant.cycle`）切换 variant。会话的模型选择不会写回 `opencode.json`。

### 5.3 可选的 `cli.json`

本机没有 `cli.json`，所以 TUI 使用默认主题 `opencode`、默认键位和默认会话显示。只有在你确实要固定外观或键位时才创建：

```json
{
  "$schema": "https://opencode.ai/v2/cli.json",
  "theme": {
    "name": "opencode",
    "mode": "system"
  },
  "session": {
    "thinking": "hide"
  },
  "terminal": {
    "title": true
  }
}
```

保存到：

```text
%USERPROFILE%\.config\opencode\cli.json
```

注意：

- `cli.json` 只影响终端客户端（TUI/Mini），不影响 Desktop 的窗口、字体和面板。
- `cli.json` 没有项目级文件；不要把它放进 `.opencode`。
- 如果设置了 `XDG_CONFIG_HOME`，路径会变成 `$XDG_CONFIG_HOME\opencode\cli.json`。本机没有设置这个变量，所以使用 `%USERPROFILE%\.config\opencode`。
- 主题文件放在 `~/.config/opencode/themes/*.json`；文件名就是主题名。迁移自定义主题时复制这个目录，不要复制 `cli.json` 里的绝对路径（如果有）。
- 键位写在 `keybinds` 下；默认 leader 是 `ctrl+x`。改键前先查完整的键位 ID，不要猜命令名。

### 5.4 权限：保持默认还是收紧

本机没有配置 `permissions`，所以使用内置基础策略：

```jsonc
[
  { "action": "*", "resource": "*", "effect": "allow" },
  { "action": "read", "resource": "*.env", "effect": "ask" },
  { "action": "read", "resource": "*.env.*", "effect": "ask" },
  { "action": "read", "resource": "*.env.example", "effect": "allow" }
]
```

这意味着 shell、编辑、网络和外部目录默认都不会被拦截。OpenCode 没有 Codex 那种 OS sandbox 模式；权限只是工具调用前的规则，不能限制 shell 进程的实际权限。

如果新电脑需要更保守的默认值，把下面的 `permissions` 数组合并进现有配置（不要覆盖 `model`）：

```jsonc
{
  "permissions": [
    { "action": "shell", "resource": "*", "effect": "ask" },
    { "action": "shell", "resource": "git status *", "effect": "allow" },
    { "action": "shell", "resource": "git diff *", "effect": "allow" },
    { "action": "shell", "resource": "git push *", "effect": "deny" },
    { "action": "external_directory", "resource": "*", "effect": "ask" }
  ]
}
```

这只是可选加固，不是旧机器的现状。规则按顺序匹配，最后一条匹配的生效；agent 级规则会追加在全局规则之后。`execute` 被 deny 时，Code Mode 以及只能通过它访问的工具都会失效。

### 5.5 MCP 模板

本机没有 MCP 服务器。如果新电脑要新增，推荐用 CLI 写入配置，避免破坏其他字段：

```powershell
& $cli mcp add context7 --global --url https://mcp.context7.com/mcp
& $cli mcp list
```

等价的 JSON：

```jsonc
{
  "mcp": {
    "servers": {
      "context7": {
        "type": "remote",
        "url": "https://mcp.context7.com/mcp"
      }
    }
  }
}
```

本地服务器：

```jsonc
{
  "mcp": {
    "servers": {
      "everything": {
        "type": "local",
        "command": ["npx", "-y", "@modelcontextprotocol/server-everything"],
        "environment": {
          "LOG_LEVEL": "info"
        }
      }
    }
  }
}
```

要点：

- 远程 MCP 默认 OAuth。需要登录时用 `/mcps`，不要用 shell 里的 `opencode mcp auth` 做交互式流程。
- `codemode` 默认 `true`；MCP 工具通过 `execute` 里的 `tools.<server>.<tool>` 使用。要恢复原生工具列表才设 `false`。
- 不要把 MCP 的 OAuth token 写进 `opencode.json`；凭据由 OpenCode 存在配置之外。
- 如果服务器只用 API key，设 `"oauth": false`，并在 `headers` 里用 `{env:MCP_API_KEY}` 这类引用，不要写明文。
- 删除服务器时删掉对应的 `mcp.servers.<name>`，不是删整个 `mcp` 对象。

### 5.6 插件模板

本机 `opencode plugin list` 显示 `No plugins found`，只有 92 个内置插件。插件不是 Codex 的 marketplace 模型，而是 npm 包、Git 包或本地目录：

```jsonc
{
  "plugins": [
    "opencode-acme-plugin@1.2.0",
    "./plugins/local",
    {
      "package": "@acme/opencode-plugin",
      "options": {
        "strict": true
      }
    }
  ]
}
```

管理命令：

```powershell
& $cli plugin add opencode-acme-plugin@1.2.0
& $cli plugin list
& $cli plugin check
& $cli plugin update
& $cli plugin remove opencode-acme-plugin@1.2.0
```

说明：

- 项目级插件也可以放在 `.opencode/plugins/` 下，OpenCode 会发现直接的 `.ts`/`.js` 文件和包目录。
- 全局插件放在 `~/.config/opencode/plugins/`。
- TUI 专用插件写在 `cli.json` 的 `plugins` 数组；`opencode.json` 的插件是服务端/桌面插件。
- 插件缓存和依赖由 OpenCode 安装，不要从旧机器复制插件的 `node_modules` 或缓存；本地插件目录和技能自带的依赖（如 `markdown-to-word/node_modules`）除外。
- 本机没有用户插件，所以迁移包里的 `plugins` 目录通常为空。

### 5.7 自定义 provider（备选）

当前使用的是内置 OpenCode Go，不需要自定义 provider 块。如果以后要接一个 OpenAI-compatible 网关，可以这样写，并把 key 放在环境变量里：

```jsonc
{
  "providers": {
    "acme": {
      "name": "Acme",
      "env": ["ACME_API_KEY"],
      "package": "@opencode/ai/providers/openai-compatible",
      "settings": {
        "baseURL": "https://llm.acme.example/v1"
      },
      "models": {
        "qwen3-coder": {
          "name": "Qwen 3 Coder"
        }
      }
    }
  },
  "model": "acme/qwen3-coder"
}
```

这不是本机现状。迁移时不要为了“看起来完整”而添加一个没有凭据的 provider，否则模型选择器会出现不可用条目。

---

## 6. 技能清单

### 6.1 用户技能：25 个目录

这些目录位于：

```text
%USERPROFILE%\.config\opencode\skills\
```

其中 24 个是可调用技能，`_shared` 是支持包，不是独立技能。

| 技能 ID | 作用 | 来源/迁移 |
|---|---|---|
| `answer-me-with-html` | 把回答做成单页视觉 HTML；仅在显式调用时使用 | GitHub `QingYunA/answer-me-with-html`；`.agents` 也有一份 |
| `citation-management` | OpenAlex/PubMed/Google Scholar 检索、元数据核验、BibTeX | 未记录可靠上游；从原机复制 |
| `docx-thesis-format` | 浙江大学工硕论文 Word 格式检测与修复（Node.js） | 未记录可靠上游；从原机复制 |
| `exploratory-data-analysis` | 有边界的本地 EDA：CSV/TSV/JSON、可选 HDF5/FASTA/图像 | 未记录可靠上游；从原机复制 |
| `html-docs` | HTML 文档、课程、讲解视频、发布到 html-docs.com | 未记录可靠上游；从原机复制 |
| `html-document-creator` | 分页式 HTML 手册/宣传册、16:9、受控 PDF 导出 | GitHub `huzhe2003/html-document-creator`；从原机复制也可 |
| `idea-evaluator` | 研究想法五维评估、可行性、致命缺陷审计 | 未记录可靠上游；从原机复制 |
| `intro-drafter` | 论文 Introduction 六段式草稿、贡献对齐 | 未记录可靠上游；从原机复制 |
| `literature-review` | 系统/范围/叙述性文献综述、筛选和证据综合 | 未记录可靠上游；从原机复制 |
| `markdown-to-word` | Markdown + LaTeX 数学/表格/图片转 Word（浙大格式） | 未记录可靠上游；从原机复制；含 `node_modules` |
| `matplotlib` | Matplotlib 科学绘图、定制、PNG/PDF/SVG 导出 | 未记录可靠上游；从原机复制 |
| `md2html` | 长 Markdown 转单页 HTML，含 Mermaid、时间线、目录 | GitHub `haidang1810/md2html`；从原机复制也可 |
| `nature-paper2ppt` | 论文转中文 Nature 风格 PPTX，含讲者备注和自审 | 未记录可靠上游；版本 2.0.0；从原机复制 |
| `nature-reader` | 论文中英对照、图表就位、来源锚点的 Markdown 阅读器 | 未记录可靠上游；版本 2.0.0；从原机复制 |
| `nature-response` | Nature 系审稿意见逐点回复、rebuttal 信 | 未记录可靠上游；版本 1.0.0；从原机复制 |
| `paper-lookup` | 18 个学术 API 的论文、引用、全文、OA 状态检索 | 未记录可靠上游；从原机复制 |
| `paper-polish` | 学术英文润色、中译英、去 AI 腔、保留原意 | 未记录可靠上游；从原机复制 |
| `paper-writer` | 从作者材料起草论文段落或整稿 | 未记录可靠上游；从原机复制 |
| `pre-submission-reviewer` | 投稿前宏观逻辑、写作、语法、LaTeX、图表审查 | 未记录可靠上游；从原机复制 |
| `research-lookup` | 用 Parallel Search/Extract/Research 收集当前证据 | 未记录可靠上游；从原机复制 |
| `scientific-visualization` | 出版级图表设计、可访问性、色彩/对比度审查 | 未记录可靠上游；从原机复制 |
| `statistical-analysis` | 统计检验选择、假设检查、效应量、APA 报告 | 未记录可靠上游；从原机复制 |
| `statistical-power` | 样本量、统计功效、MDE、功效曲线、模拟 | 未记录可靠上游；从原机复制 |
| `tech-paper-template` | 技术论文骨架、逻辑链、贡献结构 | 未记录可靠上游；从原机复制 |
| `_shared` | Nature 系列技能的共享术语表、伦理、论文类型等 | 支持包；必须与相关技能一起复制 |

说明：

- `_shared` 没有 `SKILL.md`，所以不会出现在模型的可调用技能列表里；它通过相对路径被 `nature-paper2ppt`、`nature-reader` 等技能读取。不要单独删除它。
- `markdown-to-word` 目录约 27.4 MB、605 个文件，主要是自带的 `node_modules`；压缩包会明显变小，但解压后应保留完整目录。
- 不建议只复制单个 Nature 技能。若要使用自然科学校验工作流，应保留 `nature-paper2ppt`、`nature-reader`、`nature-response` 和 `_shared`。
- 技能 ID 由目录名决定，大小写敏感。不要把目录改成中文名或带空格的名称，否则提示词里的 `@id` 会失效。
- 技能正文不会在每轮对话中全部注入；OpenCode 只广告 `description`，模型需要时再通过 `skill` 工具加载。支持文件也是按需读取，不会自动全部载入。

### 6.2 已知来源的重装命令

`answer-me-with-html`：

```powershell
$dest = Join-Path $env:USERPROFILE '.config\opencode\skills\answer-me-with-html'
git clone https://github.com/QingYunA/answer-me-with-html.git $dest
```

`html-document-creator`：

```powershell
$dest = Join-Path $env:USERPROFILE '.config\opencode\skills\html-document-creator'
if (-not (Test-Path -LiteralPath $dest)) {
  git clone https://github.com/huzhe2003/html-document-creator.git $dest
}
```

`md2html`：

```powershell
$dest = Join-Path $env:USERPROFILE '.config\opencode\skills\md2html'
if (-not (Test-Path -LiteralPath $dest)) {
  git clone https://github.com/haidang1810/md2html.git $dest
}
```

其余技能没有记录可靠的上游仓库或版本号，从原机复制仍然是最可靠的迁移方式。不要凭技能名称猜测 GitHub 仓库。

### 6.3 `.agents` 的安装记录

`%USERPROFILE%\.agents\.skill-lock.json` 记录了 `answer-me-with-html` 的来源和安装方式：

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

这个文件不是密钥，可以复制。它只记录来源、安装方式和目录哈希，不包含对话或凭据。注意：它记录的是 `.agents` 副本，而 OpenCode 当前优先加载的是 `.config` 副本；两者不一致的问题见第 4.3 节。

### 6.4 技能验收

```powershell
$skills = Join-Path $env:USERPROFILE '.config\opencode\skills'
Get-ChildItem -LiteralPath $skills -Directory |
  Select-Object -ExpandProperty Name |
  Sort-Object

(Get-ChildItem -LiteralPath $skills -Directory).Count
```

预期是 25 个目录。再确认支持包：

```powershell
Test-Path (Join-Path $skills '_shared\core\terminology-ledger.md')
Test-Path (Join-Path $skills 'markdown-to-word\node_modules')
```

在 TUI 中测试技能加载：

```text
@tech-paper-template 给我一个技术论文骨架，只列标题层级。
```

或者：

```text
@citation-management 说明你能查哪些数据库，不要真的检索。
```

如果技能没有出现，先检查文件是否叫 `SKILL.md`、是否有 `description`、目录名是否和 `@id` 一致，再检查是否有更高优先级的同名技能覆盖了它。

---

## 7. Agents、Commands、Plugins、MCP 与 Code Mode

### 7.1 内置 agent

`opencode debug agents` 显示本机有 7 个 agent：

| Agent | 模式 | 用途 |
|---|---|---|
| `build` | primary | 默认编码 agent；本机当前使用它 |
| `plan` | primary | 只读探索和计划；除 `~/.opencode/plan` 外拒绝编辑 |
| `general` | subagent | 研究、多步骤任务；不能启动子 agent，不能提问 |
| `explore` | subagent | 代码/网络搜索；只读，不允许编辑和子 agent |
| `compaction` | primary（hidden） | 上下文压缩，不供用户选择 |
| `title` | primary（hidden） | 生成会话标题 |
| `summary` | primary（hidden） | 生成会话摘要 |

本机没有自定义 agent。`build` 的权限策略里有一条 `browser` deny 和 `skill: browser` deny；浏览器工具虽然注册在 Code Mode 目录中，实际能否调用仍以权限规则为准。如果新电脑需要浏览器任务，在 `agents.build.permissions` 中追加 allow，而不是删除权限系统。

### 7.2 添加自定义 agent

全局 agent 放在：

```text
%USERPROFILE%\.config\opencode\agents\<name>.md
```

示例：只读 reviewer。

```md
---
description: Reviews changes for correctness and regressions
mode: subagent
model: opencode-go/deepseek-v4.1-flash#high
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
---

Review the current changes. List findings in severity order with file and line references.
```

调用方式：

```text
Use the reviewer subagent to review my current changes.
```

要点：

- `mode` 可以是 `primary`、`subagent` 或 `all`；不写时新自定义 agent 默认 `primary`。
- 子 agent 使用自己的权限，不是父 agent 权限的子集。
- `description` 很重要；模型靠它决定是否启动这个子 agent。
- Markdown 的正文就是 `system` 提示；不要在 frontmatter 里再写 `system`。
- 如果自定义 agent 要使用某个模型 variant，写 `provider/model#variant`。

### 7.3 添加自定义 command

全局 command 放在：

```text
%USERPROFILE%\.config\opencode\commands\<name>.md
```

示例：

```md
---
description: Review code for correctness
agent: plan
---

Review $ARGUMENTS. Report bugs first.
```

运行：

```text
/review src/auth.ts
```

要点：

- `$ARGUMENTS` 是完整参数串；`$1`、`$2` 是位置参数。
- `!` 加反引号可以插入 shell 输出，但 shell 块在命令展开时执行，不受 agent 工具权限流程控制；只对可信模板使用。
- `subagent: true` 可以让命令在后台子会话运行。
- 命令和 agent 都可以覆盖模型，但命令的 `model` 优先级最高。

### 7.4 本机的 plugin 和 MCP 状态

```text
用户插件：0
内置插件：92
MCP 服务器：0
```

本机也没有显式配置 `formatter`、`lsp`、`references`、`worktree` 或 `share`，这些段落不需要进入迁移包。迁移包不需要恢复任何 plugin 或 MCP 配置。新电脑装好 OpenCode 后，内置插件会随 Desktop/CLI 一起提供；`opencode plugin list --builtin` 可以看到它们。

如果以后新增：

- 插件用 `opencode plugin add` 安装，或把本地插件目录写进 `plugins` 数组。
- MCP 用 `opencode mcp add --global` 写入全局配置，或手工编辑 `mcp.servers`。
- 不要把旧机器的 `node_modules`、插件缓存、MCP 路径或 OAuth token 复制过来。

### 7.5 Code Mode 是什么

OpenCode V2 的 Code Mode 把大量工具收进一个 `execute` 工具，而不是把所有工具都铺在模型的原生工具列表里。模型在 `execute` 里：

1. 用 `search({ namespace })` 查找工具；
2. 用 `tools.<namespace>.<tool>({ ... })` 调用；
3. 只把需要的结果带回对话。

这样做的目的是减少工具定义占用的上下文，尤其是 MCP 服务器很多时。

本机当前的工具面：

| 命名空间 | 内容 | 说明 |
|---|---|---|
| `execute` | Code Mode 宿主 | 运行脚本、调用 `tools.*`、`search` |
| `browser` | 45 个浏览器工具 | 打开页面、点击、填表、截图、控制台/网络日志 |
| `opencode` | 8 个 OpenCode 工具 | 会话、worktree、模型、MCP 资源等 |
| MCP | 无 | 本机没有配置 MCP |

注意：

- `execute` 不是普通 shell；它是 Code Mode 的运行时。写 `tools.opencode.models(...)` 这类调用时，必须使用目录里的精确工具名。
- MCP 服务器默认 `codemode: true`，工具会出现在 `tools.<server>.<tool>` 下；设 `codemode: false` 才会回到原生工具列表。
- `execute` 权限被 deny 时，Code Mode 和只能通过它访问的工具都会不可用；但普通 shell 仍受 `shell` 权限约束。
- 如果某个技能或插件文档假设“工具直接叫 `read_file`”，在 Code Mode 下要先确认它是否被包在 `tools.*` 里。

### 7.6 子 agent 和后台任务

- 子 agent 在独立子会话中运行，拥有全新上下文；父 agent 通过 `subagent` 权限决定能启动哪些 agent。
- 子 agent 默认深度为 1，不能再启动子 agent；需要更深时设置 `experimental.subagent_depth`。
- 命令的 `subagent: true` 会在后台子会话运行，父会话继续可用。
- 子 agent 的结果或失败会回到父会话。
- 后台任务、子 agent 和会话标签都会增加资源占用；迁移后如果发现服务变慢，先检查是否有遗留的子会话或后台命令。

---

## 8. 外观、主题和字体

### 8.1 TUI 外观

本机没有 `cli.json`，所以 TUI 使用：

| 设置 | 当前值 |
|---|---|
| 主题 | 默认 `opencode` |
| 模式 | 跟随终端（`system`） |
| leader 键 | `ctrl+x` |
| 键位覆盖 | 无 |
| 会话思考显示 | 默认 |
| 终端标题更新 | 默认 |

如果要迁移 TUI 外观，复制或创建 `~/.config/opencode/cli.json`。主题名、模式和键位都在这个文件里，不在 `opencode.json`。

### 8.2 自定义主题

主题文件放在：

```text
%USERPROFILE%\.config\opencode\themes\
```

文件名就是主题名，例如 `my-theme.json` 对应 `my-theme`。只读取 `.json` 文件；项目级主题放在 `.opencode/themes/`，同名主题会覆盖全局主题。加主题后如果 `/themes` 里没有立即出现，重启 OpenCode 再选择。

如果旧机器有 `themes/` 目录，导出脚本会复制它；如果没有，不要为了迁移而创建空目录。

### 8.3 字体不是 OpenCode 配置

OpenCode 没有 Codex 的 `[desktop.appearanceDarkChromeTheme.fonts]` 这类字体配置。终端字体由终端程序（Windows Terminal、WezTerm、Alacritty 等）决定；Desktop 的界面字体不在 OpenCode 配置中，本文不把它列为可迁移项。迁移 Codex 时安装的 Maple Mono NF CN 不会自动影响 OpenCode。

如果希望新电脑的 TUI 使用同一字体：

1. 在终端程序里设置字体，而不是改 `opencode.json`。
2. 确认终端支持真彩色；否则主题颜色会退化。
3. 如果使用 Desktop 的内置终端，检查 Desktop 的终端设置，不要把字体路径写进 OpenCode 配置。

### 8.4 Desktop 的窗口和面板状态

Desktop 的窗口位置、主题、面板宽度、草稿、最近打开的项目和 Cookies 存在：

```text
%APPDATA%\ai.opencode.desktop\
```

这些不是可移植配置。新电脑第一次启动后会生成新的窗口状态；不要复制 `Local Storage`、`Session Storage`、`Network\Cookies`、`drafts.sqlite` 或 `window-state-*.json`。桌面主题和布局在新电脑上重新设置即可。

---

## 9. 外部依赖基线

| 依赖 | 当前状态 | 在 OpenCode 中的用途 |
|---|---|---|
| Python | `3.14.10` | 技能脚本、文献/统计/绘图工作流 |
| Node.js | `26.13.0` | JS 技能、插件、Desktop 工具 |
| npm | `11.20.0` | 插件和 Node 依赖 |
| Git | `2.56.0.windows.4` | 技能安装、项目操作、插件 Git 源 |
| PowerShell | Windows 自带 | 本文档所有命令 |
| ripgrep | OpenCode 自带 `~/.cache/opencode/bin/rg.exe` | 文件搜索 |
| R / Rscript | 未安装 | 某些绘图技能的 R 路线需要另行安装 |
| Pandoc | 未安装 | 某些文档转换的可选工具 |
| LibreOffice | 未安装 | 某些 Office 转换/渲染的可选工具 |
| 系统 TeX | 未安装 | LaTeX 相关技能可能需要自带工具链或自行安装 |

检查命令：

```powershell
python --version
node --version
npm --version
git --version
```

注意：

- `markdown-to-word` 自带 `node_modules`（约 27.4 MB），不要因为“迁移包太大”删掉它；删掉后该技能可能无法直接运行。
- Python 技能通常在首次调用时检查依赖。`citation-management` 需要 `requests`，Google Scholar 还需要 `scholarly`；`statistical-power` 需要 `statsmodels`、`scipy`、`numpy`、`pandas`、`matplotlib`；`statistical-analysis` 需要 Python 3.12+ 的隔离环境。按技能自己的 `compatibility` 字段准备。
- `paper-lookup` 需要网络和 `curl`，脚本只用 Python 标准库；`research-lookup` 需要 `parallel-web-tools` CLI 0.9.3。
- `opencode` 不在 PATH 中。要么每次用 `$cli` 变量，要么在新电脑上创建一个指向 `%APPDATA%\ai.opencode.desktop\cli\<版本>-x64\opencode-cli.exe` 的包装脚本；不要把版本号写死到长期使用的脚本里。
- 不要从旧机器复制 `opencode-cli.exe`、`rg.exe` 或 `node_modules` 以外的缓存；让新电脑的 Desktop 和 npm 重新生成。

---

## 10. 本地项目、会话和快照

### 10.1 项目记录

`opencode.db` 的 `project` 表记录了本机打开过的项目根目录，包括：

```text
C:\workspace\2026Spring2Winter
C:\workspace\community.wiki
C:\workspace\deepseek-harness
C:\workspace\open_code_default_workspace
C:\Users\48520
C:\Users\48520\IdeaProjects\flink-jobs
C:\Users\48520\.answer-me-with-html\pages
```

这些是数据库记录，不是配置文件。新电脑不需要、也不应该复制它们；打开项目时 OpenCode 会重新记录路径。工作区路径变化时保留新路径，不要强行复现旧路径。

### 10.2 会话和消息

会话、消息、工具调用、权限审批、子会话、快照和撤销记录都在 `opencode.db` 及其关联表中。迁移这些内容会同时带走：

- 个人对话和工作区内容；
- 旧机器的模型选择和 agent 状态；
- 可能包含敏感信息的工具输出；
- 与旧项目路径绑定的快照。

因此本手册不迁移 `opencode.db`。如果确实需要保留历史，做加密归档并单独保存，不要放进团队仓库或迁移包。

### 10.3 快照和 worktree

OpenCode 的撤销/快照数据和 worktree 记录也在数据目录/数据库中。新电脑不需要恢复旧的快照；在新项目里重新创建 worktree 即可。`opencode` 的 worktree 目录可以通过 `worktree.directory` 配置，但本机没有自定义，使用默认值。

### 10.4 共享链接

如果旧机器创建过会话分享链接，链接本身不是配置，也不应该作为迁移资产。新电脑需要重新分享；不要把带 token 的分享 URL 写进文档。

---

## 11. 验收和排错

### 11.1 配置检查

先定义 CLI 变量：

```powershell
$cli = Get-ChildItem (Join-Path $env:APPDATA 'ai.opencode.desktop\cli') `
  -Filter 'opencode-cli.exe' -Recurse -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName

& $cli --version
& $cli debug paths
& $cli debug config
& $cli service status
& $cli api get /api/info
```

重点确认：

- `debug paths` 的 `config` 指向 `C:\Users\<新用户>\.config\opencode`，`data` 指向新电脑的 `.local\share\opencode`。
- `debug config` 至少包含 `~/.config/opencode`；它只列配置源，不返回合并后的完整配置，这是正常行为。
- `service status` 返回一个本机 URL（例如 `http://127.0.0.1:<端口>`），不是旧机器的端口。
- `api get /api/info` 返回版本、PID、hostname 和 URL；hostname 应该是新电脑。
- 输出中不应出现旧机器的 runtime 路径、旧用户名或旧端口。

### 11.2 认证和模型检查

```powershell
& $cli auth list
& $cli models | Select-String 'deepseek-v4.1-flash|kimi-k3.1-pro'
```

预期：

```text
OpenCode Go  OpenCode Go  stored
opencode-go/deepseek-v4.1-flash
opencode-go/kimi-k3.1-pro
```

`auth list` 只显示提供商和存储状态，不显示 key。如果没有 `stored`，在 TUI 运行 `/connect`，选择 OpenCode Go 重新登录。

### 11.3 技能、插件和 MCP 检查

```powershell
$skills = Join-Path $env:USERPROFILE '.config\opencode\skills'
(Get-ChildItem -LiteralPath $skills -Directory).Count
Get-ChildItem -LiteralPath $skills -Directory | Select-Object -ExpandProperty Name

& $cli plugin list
& $cli plugin list --builtin
& $cli mcp list
```

预期：

- 技能目录 25 个。
- `plugin list` 为 `No plugins found`。
- `plugin list --builtin` 有约 92 个内置插件。
- `mcp list` 为 `No MCP servers configured`，除非你有意新增。

### 11.4 Smoke test

1. 新建会话，发送“只回复 OK”，确认 OpenCode Go 鉴权和默认模型正常。
2. 发送 `@tech-paper-template 给我一个技术论文骨架，只列标题层级。`，确认技能能被发现和加载。
3. 发送 `@citation-management 说明你能查哪些数据库，不要真的检索。`，确认技能正文和支持文件可读。
4. 如果要验证 variant，运行：

```powershell
& $cli run --model "opencode-go/deepseek-v4.1-flash#max" "只回复 OK"
```

5. 如果要验证浏览器，先确认 `build` 的 `browser` 权限不是 deny；当前本机默认是 deny，需要时再放开。

### 11.5 常见问题

| 现象 | 优先检查 |
|---|---|
| `opencode` 不是可识别的命令 | 本机没有把 CLI 加到 PATH；用 `$cli` 变量或完整路径 |
| `auth list` 为空或模型返回 401 | 是否在新电脑 `/connect` OpenCode Go；是否选对 provider |
| `Model unavailable` | 模型 ID 是否与 `opencode models` 完全一致；provider 是否可用；根配置是否写错 |
| 配置保存后没生效 | `debug config` 是否包含该文件；JSONC 是否有语法错误；运行 `opencode reload` |
| `debug config` 只有目录 | 这是正常输出；它列的是配置源，不是合并结果 |
| 技能不出现 | 文件是否叫 `SKILL.md`；是否有 `description`；目录名是否等于 `@id`；是否被更高优先级同名技能覆盖 |
| `answer-me-with-html` 内容不对 | `.config` 副本优先于 `.agents` 副本；见第 4.3 节 |
| Nature 技能报找不到文件 | `_shared` 是否在 `~/.config/opencode/skills/_shared`；相对路径是否完整 |
| 插件没有加载 | `plugin list` 是否有记录；插件是否在 `opencode.json` 或 `cli.json` 的正确数组中；服务是否重启 |
| MCP 需要登录 | 用 `/mcps` 完成 OAuth；不要在 shell 里跑交互式 `opencode mcp auth` |
| MCP 工具名不对 | 默认 Code Mode；工具在 `tools.<server>.<tool>`，不是原生工具名 |
| 服务连不上 | `service status`；删除两个 `service.json` 后重启 Desktop；不要复制旧文件 |
| 数据库被锁 | 关闭 Desktop 后再备份/检查；不要只复制 `opencode.db-wal` |
| Desktop 主题/字体没迁移 | Desktop 外观是本地状态，不是 `opencode.json`；在新电脑重新设置 |
| 升级后 CLI 路径失效 | 重新用 `Get-ChildItem ...\cli` 找最新 `opencode-cli.exe` |
| 浏览器任务被拒绝 | `debug agents` 查看 `build` 的 `browser` 权限；需要时追加 allow |
| `execute` 不可用 | 检查是否有 `execute` deny；Code Mode 被禁用会影响所有 `tools.*` |
| 迁移包太大 | `markdown-to-word/node_modules` 是主要体积；保留它，压缩后传输 |
| 保存的 `.ps1` 无法运行 | 用 `Set-ExecutionPolicy -Scope Process Bypass`，或直接把代码块粘贴到 PowerShell |
| 脚本里的中文注释导致下一行丢失 | 用 UTF-8 保存 `.ps1`；不要用 ANSI/GBK 代码页 |

### 11.6 如果必须手工排查服务

```powershell
& $cli service status
& $cli service restart
& $cli api get /api/info
```

`service restart` 只用于服务卡死或升级后不健康，不要用它代替配置重载。配置改动优先用 `/reload` 或 `opencode reload`。

---

## 12. 官方参考

- OpenCode 配置：<https://opencode.ai/docs/config>
- 技能：<https://opencode.ai/docs/skills>
- Agents：<https://opencode.ai/docs/agents>
- Commands：<https://opencode.ai/docs/commands>
- 权限：<https://opencode.ai/docs/permissions>
- Providers：<https://opencode.ai/docs/providers>
- Models 和 variant：<https://opencode.ai/docs/models>
- MCP：<https://opencode.ai/docs/mcp-servers>
- Plugins：<https://opencode.ai/docs/plugins>
- 指令/AGENTS.md：<https://opencode.ai/docs/instructions>
- CLI 设置：<https://opencode.ai/docs/cli/config>
- CLI 主题：<https://opencode.ai/docs/cli/theme>
- CLI 键位：<https://opencode.ai/docs/cli/keybinds>
- 故障排查：<https://opencode.ai/docs/troubleshooting>
- V1 到 V2 迁移：<https://opencode.ai/docs/migrate-v1>

---

## 13. 最终安全边界

这份文档可以安全地作为迁移清单保存，但它不是凭据保险箱。任何时候都不要把以下内容写入 `harness/opencode.md` 或以未加密形式提交到 Git：

- OpenCode Go 的 API key、OAuth token、Cookie；
- `opencode.db` 中的 `credential`、`account`、`control_account` 记录；
- `service.json` 中的服务密码、PID、端口；
- `.env`、SSH 私钥、代理密码；
- 会话内容、工具输出、附件、工作区私有文件；
- Desktop 的 `Local Storage`、`Cookies`、`drafts.sqlite`；
- 带 token 的分享链接；
- 旧机器的 hostname、IP、SSH 配置和登录凭据。

如果迁移过程中发现 key 曾经写入共享目录、聊天记录或 Git 历史，建议在提供商控制台轮换 key，而不是只删除文本。删除 `opencode.db` 中的记录也不能保证已经复制出去的 token 失效。

---

## 14. 最小迁移摘要

如果只想记住一件事：

```text
安装 OpenCode Desktop
→ /connect OpenCode Go
→ 复制 ~/.config/opencode/skills 和 AGENTS.md
→ 创建只含 model/default_agent 的 opencode.jsonc
→ 不复制 opencode.db、service.json、Desktop Local Storage
→ 用 debug paths / auth list / models / mcp list / plugin list 验收
```

OpenCode 的迁移重点是“配置文件 + 技能 + 规则”，不是“整个用户目录”。凭据、会话和运行时状态应由新电脑重新生成。








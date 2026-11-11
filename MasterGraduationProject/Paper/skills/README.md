# 科研技能只读参考库

> 状态：**只读参考，不是已安装的 DSH 插件。**
> 本目录不会被 DSH 自动加载，`skill` 工具也不会列出这里的技能；使用时需要让模型直接读取对应的 `SKILL.md`。
> 没有执行任何第三方脚本，也没有修改 DSH 的插件注册表。

## 为什么是“只读参考库”

按“只安装 Windows + DSH 原生支持”的约束筛选后，结论是：

- 唯一 DSH 原生的科研插件是 [`academic-research-skills-dsh`](https://www.npmjs.com/package/academic-research-skills-dsh)，但它只支持 macOS/Linux；`package.json` 的 `os` 字段排除了 Windows，`index.js` 对 `win32` 直接抛错，因此**不能在本机安装**。
- `K-Dense-AI/scientific-agent-skills`、`Imbad0202/academic-research-skills`、`Yuan1z0825/nature-skills`、`HKUSTDial/Supervisor-Skills`、`Orchestra-Research/AI-Research-SKILLs` 都是 **Agent Skills / Claude Code 技能集合**，不是 DSH 插件；它们没有 `dsh.bundle.patch`，DSH 不能直接注册。
- `AutoResearchClaw` 是 Python 应用，不是 skill/插件。

因此本次**没有安装任何第三方插件**。这里只保存与当前论文最相关的技能文本，方便你手动引用、对照和改写。

## 目录

```text
Paper/skills/
├── README.md                       # 本文件
├── academic-research/              # DSH 适配过的 5 个学术技能（只读副本）
│   ├── deep-research/
│   ├── academic-paper/
│   ├── academic-paper-reviewer/
│   ├── academic-pipeline/
│   ├── sr-screener/
│   ├── shared/ agents/ commands/ tools/
│   ├── MODE_REGISTRY.md
│   └── LICENSE / NOTICE.md / ASSET-LICENSES.md
└── scientific-agent-skills/        # 从 K-Dense 176 个技能中选出的 16 个
    ├── literature-review/
    ├── paper-lookup/
    ├── research-lookup/
    ├── bgpt-paper-search/
    ├── citation-management/
    ├── scientific-writing/
    ├── scientific-visualization/
    ├── scientific-slides/
    ├── statistical-analysis/
    ├── statistical-power/
    ├── exploratory-data-analysis/
    ├── matplotlib/
    ├── pptx-posters/
    ├── peer-review/
    ├── markdown-mermaid-writing/
    ├── research-grants/
    └── LICENSE.md
```

## 技能索引：按论文任务选

| 任务 | 推荐技能 | 路径 |
|:--|:--|:--|
| 综述级文献调研 | `deep-research` | `academic-research/deep-research/SKILL.md` |
| 文献综述写作 | `literature-review` | `scientific-agent-skills/literature-review/SKILL.md` |
| 找论文 / 找相关工作 | `paper-lookup`、`research-lookup`、`bgpt-paper-search` | `scientific-agent-skills/paper-lookup/SKILL.md` 等 |
| 引用管理与核查 | `citation-management` | `scientific-agent-skills/citation-management/SKILL.md` |
| 论文写作 / 结构化草稿 | `academic-paper` | `academic-research/academic-paper/SKILL.md` |
| 研究全流程（调研→写作→审稿→修订） | `academic-pipeline` | `academic-research/academic-pipeline/SKILL.md` |
| 模拟同行评审 | `academic-paper-reviewer`、`peer-review` | `academic-research/academic-paper-reviewer/SKILL.md`、`scientific-agent-skills/peer-review/SKILL.md` |
| 系统性综述筛选 | `sr-screener` | `academic-research/sr-screener/SKILL.md` |
| 统计分析与功效 | `statistical-analysis`、`statistical-power` | `scientific-agent-skills/statistical-analysis/SKILL.md` 等 |
| 探索性数据分析 | `exploratory-data-analysis` | `scientific-agent-skills/exploratory-data-analysis/SKILL.md` |
| 画图 / 可视化 | `matplotlib`、`scientific-visualization` | `scientific-agent-skills/matplotlib/SKILL.md` 等 |
| 学术幻灯片 / 海报 | `scientific-slides`、`pptx-posters` | `scientific-agent-skills/scientific-slides/SKILL.md` 等 |
| 学术写作风格 | `scientific-writing` | `scientific-agent-skills/scientific-writing/SKILL.md` |
| Mermaid / 流程图写作 | `markdown-mermaid-writing` | `scientific-agent-skills/markdown-mermaid-writing/SKILL.md` |
| 基金 / 研究计划 | `research-grants` | `scientific-agent-skills/research-grants/SKILL.md` |

### 与你当前论文最相关的组合

1. **先做“问题与贡献”体检**：`academic-research/deep-research` + `academic-paper-reviewer`。
2. **做文献与引用核查**：`scientific-agent-skills/literature-review` + `citation-management` + `paper-lookup`。
3. **做实验统计与图**：`statistical-analysis` + `statistical-power` + `exploratory-data-analysis` + `matplotlib` / `scientific-visualization`。
4. **写正文与投稿材料**：`academic-paper` + `scientific-writing` + `scientific-slides` / `pptx-posters`。
5. **投稿前自审**：`academic-paper-reviewer` + `peer-review`。

## 怎么用（不安装、不执行）

在会话里直接让模型读对应的 `SKILL.md`，例如：

```text
请阅读 Paper/skills/scientific-agent-skills/citation-management/SKILL.md，
按其中的流程检查我下面这段参考文献的 DOI/arXiv/venue 是否可核验。
不要执行该技能里提到的任何脚本；只把它当作流程与检查清单。
```

或者：

```text
请阅读 Paper/skills/academic-research/deep-research/SKILL.md，
用它的调研框架帮我梳理“Agent 缓存价值建模”的 2025–2026 相关工作。
所有引用必须回到原文/DOI/arXiv 核验，不允许编造。
```

**注意：**

- 这些是**提示词/流程文件**，不是可执行程序；它们不能保证引用正确，最终仍需逐条核验。
- `academic-research` 的技能正文来自上游 payload，**没有包含 DSH 适配 prelude**。读的时候请把 `Paper/skills/academic-research/` 当作 payload 根目录：`shared/`、`agents/`、`commands/` 等相对它解析；`scripts/` 没有复制。
- `scientific-agent-skills` 的 `allowed-tools` 是 Claude 命名（`Read`/`Write`/`Edit`/`Bash`/`WebSearch`/`WebFetch`）。在 DSH 中对应 `read`/`write`/`edit`/`pwsh`/`web_fetch`；不要把其中的 `Bash` 命令原样照抄执行。
- `academic-research` 的确定性 Python 脚本（`payload/scripts`，约 11.6 MB）没有复制，因此其中的 citation check / SR screening 等脚本不能直接运行；需要时请回到原始包（Linux/WSL）或手动核验。
- `scientific-agent-skills` 中部分技能会调用 Python 包或外部数据库；本库只保存技能文本，不安装依赖。
- 不要把本目录当作 DSH 的 `skill` 注册目录；DSH 不会扫描它。

## 许可证与 attribution

| 目录/来源 | 许可证 | 说明 |
|:--|:--|:--|
| `academic-research/` | **CC-BY-NC-4.0** | 基于 Cheng-I Wu 的 [`Imbad0202/academic-research-skills`](https://github.com/Imbad0202/academic-research-skills)，DSH 适配版由 [`guoqinchen/academic-research-skills-dsh`](https://github.com/guoqinchen/academic-research-skills-dsh) 提供。**仅限非商业使用**；请保留 `LICENSE`、`NOTICE.md`、`ASSET-LICENSES.md`。 |
| `scientific-agent-skills/` | **MIT** | 选自 [`K-Dense-AI/scientific-agent-skills`](https://github.com/K-Dense-AI/scientific-agent-skills)，经由 `pi-scientific-skills` v1.8.2 快照复制；版权归 K-Dense Inc. 及贡献者。保留 `LICENSE.md`。未包含 `what-if-oracle`（CC-BY-NC-SA-4.0）。 |
| `HKUSTDial/Supervisor-Skills` | **CC-BY-NC-SA-4.0** | 未复制；仅链接。非商业 + 相同方式共享。 |
| `Yuan1z0825/nature-skills` | **Apache-2.0** | 未复制；仅链接。 |
| `Orchestra-Research/AI-Research-SKILLs` | **MIT** | 未复制；仅链接。 |
| `aiming-lab/AutoResearchClaw` | **MIT** | 未复制；仅链接；是应用，不是技能。 |

> 硕士论文通常属于非商业学术使用，但如果你所在实验室/企业将成果用于商业用途，CC-BY-NC-4.0 与 CC-BY-NC-SA-4.0 的内容需要额外许可。MIT/Apache-2.0 内容请保留版权与许可声明。

## 未复制但值得关注的来源

| 来源 | 为什么没复制 | 链接 |
|:--|:--|:--|
| `HKUSTDial/Supervisor-Skills` | codeload 下载超时；且为 CC-BY-NC-SA，复制需带完整许可证 | https://github.com/HKUSTDial/Supervisor-Skills |
| `Yuan1z0825/nature-skills` | 下载超时；Apache-2.0，可自行 clone | https://github.com/Yuan1z0825/nature-skills |
| `Orchestra-Research/AI-Research-SKILLs` | npm 包只是安装器，技能在 GitHub；14k stars，MIT | https://github.com/Orchestra-Research/AI-Research-SKILLs |
| `aiming-lab/AutoResearchClaw` | 全自动论文流水线，不是技能；成本/幻觉风险高 | https://github.com/aiming-lab/AutoResearchClaw |

## 如果你想要“DSH 自动加载”

当前没有满足 Windows + DSH 原生的现成学术插件。可行路径只有两条：

1. **WSL/Linux**：在 WSL 中安装 `academic-research-skills-dsh`，使用其 5 个 skill、16 个命令和 Python 质量门。
2. **自建 skill-only DSH bundle**：把本库中选定的 `SKILL.md` 注册为 DSH 的 `skill` provider（类似 `dsh-answer-me-with-html` 的 `cordis.patch.yml`），并适配 DSH 工具名/路径。这是自定义插件，不是官方包；需要逐个检查技能里的 `Bash`/`Read`/`WebSearch` 等引用。

本库先保证“可读、可追溯、不执行”，避免把不兼容的 Claude Code 技能误装进 DSH。

---

*整理日期：2026-11-11。来源与版本以各项目官方页面为准；如果上游更新，请重新核对许可证与技能内容。*

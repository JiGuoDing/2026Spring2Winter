---
template: doc
theme: auto
lang: zh
title: Agent Workflow Memory：把可复用工作流写进 Agent 记忆
subtitle: ICML 2025 · plan / resp
source: ICML 2025, PMLR 267, 2025, 15 pp.
outline: right
---

问题是网页 Agent 每次任务都从固定示例出发，不能从过去的成功轨迹中提炼可复用套路；AWM 用 LM 从成功轨迹归纳“工作流”并写回记忆，在 WebArena 与 Mind2Web 上显著提升成功率，对第一章最有用的是 `resp/plan` 类缓存对象的写入与复用机制。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Agent Workflow Memory |
| 作者 | Zora Zhiruo Wang, Jiayuan Mao, Daniel Fried, Graham Neubig |
| 机构 | Carnegie Mellon University；Massachusetts Institute of Technology |
| 发表 | Proceedings of the 42nd International Conference on Machine Learning (ICML), Vancouver, 2025；PMLR 267 |
| 正式版本 | ICML 2025 会议论文，PDF 15 页（正文 8 页，余为附录） |
| arXiv / DOI | DOI 论文未给出；arXiv 编号论文未给出 |
| 本地原文 | `paper_source/AWM_ICML2025.pdf`（15 页） |
| 代码/数据 | https://github.com/zorazrw/agent-workflow-memory；WebArena、Mind2Web |
| 版本边界 | ICML 2025 正式版；实验模型为 GPT-4o / GPT-4 / GPT-3.5-turbo，温度 0 |

## B 问题与动机

当前 Agent 大多把固定示例放进上下文，或做 in-context learning。这能在与示例相似的动作序列上奏效，但任务上下文或环境一变就缺乏鲁棒性。更根本的是，Agent 逐个任务求解，不从过去的成功与失败中学习，因而不会随时间适应。

论文借鉴人类从经验中抽象“任务套路”的能力，提出 Agent Workflow Memory（AWM）：从 Agent 轨迹中归纳可复用的工作流，写入记忆，在后续任务中按需提供。工作流不是完整示例，而是抽象出的子过程，因此更容易跨任务、跨网站复用。

## C 方法机制

工作流由两部分组成。其一是自然语言描述 `d`，概括这个工作流要达成什么目标；其二是工作流轨迹，由若干步 `p = (环境状态描述, 推理过程, 可执行动作)` 组成。动作是环境上的可执行程序，例如 `click('126')`、`fill('145', {location})`、`stop()`。

归纳模块 `I` 用 LM 从一条或多条经验 `E` 中抽取常见子过程，得到 `I(E) → W`。提示词刻意要求“细粒度子任务”而非整条任务指令，并把示例特有值抽象成占位符，例如把 “dry cat food” 换成 `{product-name}`，以提升泛化。归纳结果按双空行切分，分别存入工作流记忆。

使用方式有两种。离线模式先从训练样例归纳出 `W_offline`，测试时把整套工作流放入记忆，所有测试共用。在线模式只给测试查询，Agent 按流式方式处理：解一个任务，得到轨迹 `e_t`；用 LM 评估器判断是否成功；成功则归纳 `I(e_t) → {w_t}`，把 `{w_t}` 并入记忆 `M_t`，再处理下一个任务。失败轨迹不写入，避免污染记忆。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| WebArena 主结果 | 812 个任务、5 个网站；GPT-4o；在线模式 | AWM 总成功率 35.5%，BrowserGym 23.5%，SteP（人工工作流）33.0% | 比 BrowserGym 高 12.0 个百分点、相对提升 51.1%；比人工工作流高 7.6% 相对 |
| WebArena 效率 | 同上，统计平均步数 | AWM 5.9 步；BrowserGym 7.9 步；AutoEval 46.7 步 | 比 BrowserGym 少约 2.0 步，比 AutoEval 少 40.8 步 |
| 跨模板 | 每个模板只抽一个样例，避免同模板泄漏 | AWM 33.2%，BrowserGym ax-tree 20.5% | 收益不只是“记住同模板答案” |
| Mind2Web 离线 | 跨任务 split；GPT-3.5/GPT-4 | 步级成功率相对提升 24.6%；GPT-4 下 AWM 45.1% vs MindAct 36.2% | 抽象工作流比完整示例更少偏置 |
| 在线泛化 | 跨任务、跨网站、跨域 | 步级成功率分别提升 7.4–8.9、3.6–3.8、14.0–16.9 绝对点 | 分布差距越大，在线归纳越有优势 |
| 学习曲线 | WebArena map split | 前约 40 个样例快速上升，之后趋稳；与基线差距可达 22.5 个百分点 | 几十个样例就能学到核心工作流 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 对应 `resp` 与 `plan`：成功轨迹归纳出的工作流模板、子目标序列、可执行动作片段；它不是原始回答，而是“可复用计划” |
| 价值建模 | 价值来自“未来被复用的概率 × 复用后成功率提升 − 记忆占用”。论文的可观测代理是工作流被复用的频率、跨任务/跨网站的成功率增益、以及平均步数下降 |
| 生命周期 | 写入条件是“评估器判定成功”；在线模式持续追加；论文没有淘汰、合并、版本失效或 TTL，记忆只增不减 |
| Flink 映射 | `MapState<workflowId, Workflow>` 存描述与步骤；`ValueState<version>` 做更新；timer 做冷热衰减；checkpoint 保存记忆快照；RocksDB compaction 合并近似工作流 |
| 可写缺口 | 论文只写不删，记忆会随任务流无限增长；没有“何时该忘”的策略。第一章可补 `resp/plan` 缓存的准入—合并—淘汰生命周期，并把“复用收益/维护成本”写成可计算价值 |

## F 局限与边界

实验只覆盖网页导航（WebArena、Mind2Web），没有工具调用链、代码 Agent 或多模态环境。模型依赖 GPT-4 级能力，开源小模型未验证。论文报告的是成功率与步数，没有 token 成本、延迟、显存或金额。工作流记忆的规模增长、检索开销、冲突消解都未分析；也没有隐私与多租户隔离讨论。在线模式依赖 LM 评估器判断成功，评估器误差会直接变成错误工作流入库。论文没有单独的 Limitations 小节，以上为证据边界。

## G 引用信息

```bibtex
@inproceedings{wang2025awm,
  title     = {Agent Workflow Memory},
  author    = {Wang, Zora Zhiruo and Mao, Jiayuan and Fried, Daniel and Neubig, Graham},
  booktitle = {Proceedings of the 42nd International Conference on Machine Learning (ICML)},
  series    = {PMLR},
  volume    = {267},
  year      = {2025},
  publisher = {PMLR}
}
```

来源页面：PDF 第 1 页标题、作者、摘要与 ICML 版权页；第 2–3 页问题定义与工作流表示；第 3–5 页归纳与在线/离线流程；第 5–8 页实验与结论。

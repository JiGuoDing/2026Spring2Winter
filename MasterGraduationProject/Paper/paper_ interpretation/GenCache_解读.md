---
template: doc
theme: auto
lang: zh
title: GenCache：缓存“生成回答的程序”，而不缓存回答
subtitle: NeurIPS 2025 · resp
source: Sarthak Chakraborty et al., "Generative Caching for Structurally Similar Prompts and Responses," NeurIPS 2025, pp. 5172–5199, arXiv:2511.17565v1.
outline: right
---

GenCache 针对“结构相似、参数不同”的提示：它不在命中时返回旧回答，而是离线用 LLM 从若干样例中归纳出一个 Python 程序，命中时执行程序、按新参数生成回答。它把缓存对象从“答案”提升为“答案的生成规则”。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Generative Caching for Structurally Similar Prompts and Responses |
| 作者 | Sarthak Chakraborty、Suman Nath、Xuchao Zhang、Chetan Bansal、Indranil Gupta |
| 机构 | University of Illinois at Urbana-Champaign；Microsoft Research |
| 发表 | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） |
| 正式版本 | NeurIPS 2025 会议论文；正式 proceedings pp. 5172–5199，DOI 10.52202/085713-0162 |
| arXiv / DOI | arXiv:2511.17565v1（2025-11-14）；DOI 10.52202/085713-0162 |
| 本地原文 | `paper_source/GenCache_NeurIPS2025.pdf` |
| 代码/数据 | `github.com/sarthak-chakraborty/GenCache`；FLASH 事故数据来自 Microsoft，未公开 |
| 版本边界 | 本地 PDF 为 NeurIPS 2025 版本；论文中的 FLASH 数据只覆盖 298 个事故、5 类场景，不能外推到全部云运维负载 |

## B 问题与动机

现有缓存有两类：

- 精确匹配：要求 prompt 完全相同，无法处理参数变化。
- 语义缓存：按嵌入相似度返回旧回答，但会忽略“关键差异”。例如同一模板下价格、地区、商品名不同，旧回答不能直接复用。

论文定义第三类结构：**结构相似（structurally similar）**。提示可以写成 `a1 · x · a2`，回答可以写成 `b1 · f(x) · b2`；`a1,a2,b1,b2` 是固定短语，`f(x)` 是从新请求中抽取参数的变换。三个条件是：

1. 结构规律：提示不是精确或语义相似，而是遵循稳定格式。
2. 受控变化：只有少量但重要的参数变化。
3. 回答模式可预测：回答格式稳定，但内容随参数变化，且与参数相关。

典型场景是 SRE 告警诊断、Web 导航、客服工单等可重复工作流。GenCache 明确不适用于高多样性的自由聊天，那类场景语义缓存更合适。

## C 方法机制

**运行时流程。**

```text
新 prompt P
  → 找最近簇（prompt 相似度 + response 相似度）
  → 用簇的 regex 验证 P 是否符合结构
  → 若命中：执行缓存程序，做 sanity check，返回生成结果
  → 若未命中：调 LLM 生成回答，存入簇数据库
  → 簇内样例足够后，后台生成程序并验证，存入 cache store
```

**聚类。** 每个 prompt 用 SentenceTransformer 编码；回答通常是 JSON，作者对每个 value 分别编码，得到回答嵌入数组。簇分配要求 prompt 相似度 `s_p > T_p` 且 response 相似度 `s_r > T_r`，再在交集中选 `s_p + s_r` 最大的簇。默认 `T_p=0.8`、`T_r=0.75`。簇是在线创建的，不限制数量。

**程序生成。** 当簇内样例数达到 `κ`（默认 4）时，后台调用 CodeGenLLM（GPT-4o），把样例作为 in-context 示例，要求它归纳出“从 prompt 抽取参数 → 构造回答”的 Python 程序。程序通常用 regex 抽取关键词，再套回答模板；要包含异常处理，regex 不匹配时返回 `{null}`。每个簇最多保留 `3κ` 个样例，避免 prompt 无限增长。

**程序验证。** 另一个 LLM（ValidLLM）在本地执行程序，把生成结果与样例逐条比较，检查内容与格式；返回每条样例的 0/1 与理由。若匹配比例低于 `β`（默认 50%），用 reflection 把理由反馈给 CodeGenLLM 重试；每个簇最多重试 `γ`（默认 30）次。通过后程序才进入 cache store。

**缓存管理。** 每个程序通常小于 5 KB，总缓存只有几十 MB。缓存满时按 LRU 淘汰程序，但保留对应簇；簇数据库几百 MB，实验中用量低于 20 MB。每个簇最多 3κ 个 prompt-response 对；命中时不再存 prompt。程序在新请求上失败时，可为该簇重新生成，重试次数仍受 `γ` 限制。

**反馈。** GenCache-feedback 在检测到负命中时删除对应程序、保留簇，以便之后重新生成。它把“下游验证”变成缓存失效信号。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 主命中率 | 10,000 条合成 WebShop 提示；Param-Only 与 Param-w-Synonym；基线 ExactCache、GPTCache（all-MiniLM-L6-v2，阈值 0.95） | Param-Only：GenCache 命中 97.81%，负命中 1.97%；GPTCache 命中 90.92%，负命中 100%。Param-w-Synonym：GenCache 命中 83.66%，负命中 7.84%；GPTCache 命中 88.71%，负命中 100% | GPTCache 的高命中全是错的：数据没有重复 prompt，任何语义命中都不应发生 |
| ExactCache | 哈希精确匹配 | 两个数据集命中率均为 0 | 说明负载确实没有重复 prompt |
| 命中路径延迟 | 10,000 条提示的平均拆解 | 命中总延迟约 0.176 s；未命中 LLM 调用约 3.520 s；未命中缓存查询 0.056 s；数据库写入 0.075 s | 命中省掉的是秒级 LLM 调用，缓存本身是毫秒级 |
| Token 成本 | 每次 2,000 条提示、跑 5 次，扫 κ | 相比无缓存至少省 35% token，最高省 73%（κ=2） | 程序生成有一次性成本，命中后摊薄 |
| FLASH 云运维 | 298 个事故、5 类场景；top-1 场景占 69%，top-2 占 93% | GenCache+Exact 命中 54.7%（其中 Exact 贡献 31.1%），Exact 单独 34.4%；执行时间 39.91 s vs 53.45 s；536 次缓存生成调用中仅 10.4%（56/536）产出可复用缓存；298 个事故中 3 个（1%）因错误缓存导致失败 | 真实 Agent 工作流里，缓存生成的成功率很低，但一旦成功，复用收益明显 |
| Laser Web 导航 | 200 条 WebShop 请求；只对 action 选择启用 GenCache，rationale 不缓存 | 命中 37.2%（Exact 贡献 12.8%）vs Exact 5.7%；执行时间 5.02 s vs 5.16 s；100 次生成调用中 34% 成功；失败原因：5.5% 返回错误商品，11% 格式错误 | 只缓存“结构化动作”，不缓存自由推理，是它有效的关键 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `resp` 的变体：存的不是固定回答，而是“从结构化 prompt 生成回答的程序 + 结构 regex”。命中时执行程序，得到与新参数匹配的回答 |
| 价值建模 | 复用收益 = 省掉的 LLM 调用；成本 = CodeGenLLM + ValidLLM + 重试 + 程序执行。价值随复用次数摊薄，因此“何时值得生成程序”是一个典型的摊销决策。论文用固定 `κ=4` 和 LRU，没有显式算这笔账；负命中是质量风险 |
| 生命周期 | 写入：簇内样例达到 κ 且程序通过验证；保留：LRU；驱逐：删程序、保留簇；刷新：失败后重新生成，或用反馈删除；TTL/预取：无。它把“簇”与“程序”拆成两层生命周期，这一点对第一章很有用 |
| Flink 映射 | 以簇 id 为 key：`MapState` 存簇心、样例、程序、regex、验证统计；程序生成/验证走 side output + 异步算子；timer 触发“样例够了就生成”；`State TTL` 管理程序有效期；checkpoint 保存簇与程序。程序执行本身是 UDF，不放进状态 |
| 可写缺口 | 固定 `κ=4` 只回答“样例够不够”，不回答“这个簇值不值得生成程序”。可写“按预期复用次数、生成/验证成本、负命中风险计算摊销价值，再决定写入/保留/淘汰”；这能把 GenCache 的写路径纳入第一章的价值模型 |

## F 局限与边界

- 只适用于结构相似、可重复、动作可逆的工作流；自由聊天、结构差异大的任务不适用。作者明确把“非可逆 Agent 工作流”列为局限。
- 没有正确性保证。程序可能过拟合样例、regex 误匹配、分支覆盖不足；论文用 ValidLLM 和 regex 校验降低风险，但不能消除。
- 负命中率在 Param-w-Synonym 上为 7.84%；在 FLASH 上有 1% 的失败。作者建议配合严格 guardrail 和下游回滚。
- 评测以合成数据为主，FLASH 只有 298 个事故、一个组织；Laser 只有 200 条请求。代码生成与验证都依赖 GPT-4o，成本与模型版本绑定。
- 缓存管理只有 LRU 和固定 κ，没有 TTL、预取、容量-价值联合优化；也没有流处理、checkpoint、扩缩容实验。
- 程序生成成功率在 FLASH 上只有 10.4%，说明“写入成本”可能远高于命中收益；论文没有给出按簇的 ROI 分析。

## G 引用信息

```bibtex
@inproceedings{chakraborty2025gencache,
  title     = {Generative Caching for Structurally Similar Prompts and Responses},
  author    = {Chakraborty, Sarthak and Nath, Suman and Zhang, Xuchao and Bansal, Chetan and Gupta, Indranil},
  booktitle = {39th Conference on Neural Information Processing Systems (NeurIPS)},
  pages     = {5172--5199},
  year      = {2025},
  doi       = {10.52202/085713-0162}
}
```

来源页面：NeurIPS 2025 论文页；arXiv `https://arxiv.org/abs/2511.17565`；DOI `https://doi.org/10.52202/085713-0162`；代码 `https://github.com/sarthak-chakraborty/GenCache`；本地 PDF `paper_source/GenCache_NeurIPS2025.pdf`。

---
template: doc
theme: auto
lang: zh
title: APC：缓存 Agent 的计划模板，而不是最终回答
subtitle: NeurIPS 2025 · plan / resp
source: Qizheng Zhang, Michael Wornow, Kunle Olukotun, "Agentic Plan Caching: Test-Time Memory for Fast and Cost-Efficient LLM Agents," NeurIPS 2025.
outline: right
---

APC 把 Agent 执行日志压缩成“计划模板”，用关键词而不是语义相似度检索；命中后由小模型把模板适配成当前任务的计划，未命中才调用大模型重新规划。它缓存的是计划阶段的结构，不是最终答案。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Agentic Plan Caching: Test-Time Memory for Fast and Cost-Efficient LLM Agents |
| 作者 | Qizheng Zhang、Michael Wornow、Kunle Olukotun（NeurIPS 2025 版）；arXiv v2 增加 Gerry Wan |
| 机构 | Stanford University |
| 发表 | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） |
| 正式版本 | NeurIPS 2025 会议论文；论文未印页码与 DOI |
| arXiv / DOI | arXiv:2506.14852v2（2026-01-26）；论文未印 DOI |
| 本地原文 | `paper_source/AgenticPlanCaching_NeurIPS2025.pdf` |
| 代码/数据 | 作者称发表后开源数据与代码，但论文未给仓库链接；本批未发现可核验实现 |
| 版本边界 | 本地 PDF 为 NeurIPS 版本（3 位作者）；arXiv v2 增加 Gerry Wan，并含更多附录。引用会议版时不要误加第四作者 |

## B 问题与动机

许多 Agent 采用 Plan-Act 循环：规划器拆解任务，执行器调用工具/环境，再把结果交回规划器。规划阶段常用 chain-of-thought、推理模型，消耗大量 token，是成本大头。

现有两类缓存都不适合：

- **Context caching / KV cache**：缓存模型内部状态，与具体模型绑定，跨模型不可迁移。
- **语义缓存**：缓存 `(输入, 输出)` 对，假设输出只由输入 prompt 决定。但 Agent 的输出依赖外部数据与环境上下文，同一个高层查询在不同数据上会产生不同计划。

论文的例子：同一个“总结数据集关键统计量”的请求，计划结构相似，但具体步骤取决于数据集特征；Web/GUI 导航中“删除顶部评论”的动作序列相似，但坐标和滚动量不同。

因此需要一种“任务级”缓存：抽出计划中可复用的结构，命中后按当前上下文适配，而不是直接复用旧输出。

## C 方法机制

**关键词检索。** 新请求先由轻量模型（GPT-4o-mini）抽取一个能表达高层意图的关键词，例如“compute the average of all numbers listed in an external document” → “mean calculation”。缓存是 `(keyword, plan template)` 对，按关键词精确匹配。

作者比较了查询级语义相似度与关键词匹配：语义相似度会过度关注实体名、公司名等上下文细节，阈值难设，假阳性/假阴性都高；关键词更接近“是否会得到相似计划”。因此 APC 选择精确匹配，牺牲召回换精度，也避免模糊搜索的延迟。

**命中路径。** 命中后，小规划模型（LLaMa-3.1-8B）把模板适配成当前任务的计划，注入用户信息、环境变量等上下文；计划再交给 Actor 执行。小模型不重新做完整推理，只做“模板 + 上下文”的适配。

**未命中路径。** 大规划模型（GPT-4o）从请求生成计划，Actor 执行；任务成功且输出正确后，系统从执行日志生成模板：

1. 规则过滤器抽取关键信息，丢掉冗长推理。
2. 轻量 LLM 过滤器去掉实体名、数值等上下文特定元素，得到泛化模板与关键词。

**缓存管理。** 使用 LRU 淘汰；缓存容量可调。论文发现容量超过唯一任务关键词数量后，继续增大收益很小。冷启动阶段命中率低、成本高；若已知目标负载，可用离线样本预热。若命中率持续很低，系统会自动关闭缓存。

**与现有缓存的关系。** APC 不替代 KV cache 或语义缓存；它作用在“计划”这一层，可与它们组合。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 工作负载 | FinanceBench、QASPER、TabMWP、AIME 2024/2025、GAIA；Minion 与 Open Deep Research 两种 Plan-Act 架构 | — | 覆盖长上下文数据推理、数学、开放域 Agent |
| 模型 | GPT-4o 作大规划器；LLaMa-3.1-8B 作小规划器与 Actor；GPT-4o-mini 作关键词抽取与模板生成 | — | 成本按 OpenAI / TogetherAI API 价格计 |
| 主结果 | 与 Accuracy-Optimal（无缓存、始终大模型）、Cost-Optimal（始终小模型）、语义缓存（阈值 80/85/90%）、Full-History Caching 对比 | 平均成本降低 50.31%，延迟降低 27.28%，保留 96.61% 的应用性能 | “保留性能”是相对 Accuracy-Optimal，不是绝对无损 |
| 语义缓存 | 查询级相似度命中，直接复用旧回答 | 低阈值省成本但假阳性高，性能明显下降 | 作者用案例说明“语义相似 ≠ 计划可复用” |
| Full-History | 缓存完整执行日志，作为小模型 in-context 示例 | FinanceBench 准确率 72.00% vs APC 85.50%；成本 $1.99 vs $1.86 | 未过滤的长日志反而更贵、更差 |
| GAIA | Open Deep Research，GPT-4o + GPT-4o-mini | 成本 $69.02 → $16.27（−76.42%）；准确率 37.58% → 36.97%（−0.61 个百分点） | 异构任务多、关键词复用少，仍有大幅成本收益 |
| 开销 | 关键词抽取 + 缓存生成 | 平均占总成本 1.04%；零命中 worst case 为 1.31% | 写路径很便宜，这是 APC 的相对优势 |
| 延迟 | FinanceBench 100 条查询，命中率 46% | 端到端 1959.24 s（Accuracy-Optimal）→ 1424.82 s；APC 的 Plan 1011.82 s、Act 131.44 s、关键词 42.29 s、缓存生成 215.80 s | 主要延迟来自计划阶段；缓存生成是主要额外开销，平均 3.99 s/条 |
| 容量 | FinanceBench，LRU，缓存 1–100 条 | 100 条时命中率 46%、成本 $1.86、准确率 85.50%、总延迟 1424.82 s | 超过唯一关键词数后收益递减 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `plan/resp`：结构化的计划模板，按关键词索引。它不是最终回答，也不是原始执行日志；是“可适配的计划骨架” |
| 价值建模 | 复用收益主要是省掉大规划模型的 token。FinanceBench 成本中，大规划模型占 94.17%；缓存生成只占 1.15%。复用概率近似“关键词重复率”；风险是模板不适用于当前数据上下文。APC 用“保留 96.61% 性能”做经验约束，没有形式化质量模型 |
| 生命周期 | 写入：任务成功且输出正确后，从日志抽取模板；保留：LRU；驱逐：容量满时 LRU；刷新：只有新 miss 才生成新模板，没有 TTL；预取：无。冷启动明显，命中率低时可关闭缓存 |
| Flink 映射 | 以关键词为 key：`MapState<keyword, {template, keyword, stats}>`；模板生成是后台异步任务，可用 timer 或 side output 触发；`State TTL` 给模板设置有效期；checkpoint 保存模板与命中统计；计划适配作为 UDF，不进入状态 |
| 可写缺口 | 模板没有 TTL，也不区分“数据依赖”的时效。同一个关键词在不同数据快照、不同工具版本下可能需要不同计划；APC 只做关键词精确匹配，没有失效传播。可写“数据依赖计划的有效期与版本化”，把计划模板的失效纳入生命周期 |

## F 局限与边界

- 关键词精确匹配牺牲召回：同一意图换一种说法就可能 miss。论文用假阳性/假阴性分析支持这个选择，但没有给出召回率上界。
- 计划模板可能过拟合历史执行；数据依赖的步骤（文件路径、坐标、数值）需要小模型适配，适配失败时没有回滚机制。
- 冷启动是固有限制：缓存为空时成本/延迟更高。论文用 LRU 和“低命中率自动关闭”缓解，但没有预热策略的实验。
- 没有 TTL、版本、失效机制；LRU 只按最近使用，不理解计划的价值或时效。
- 评测用 GPT-4o 作评判，成本按 API 价格计算；没有生产多租户、故障恢复、流处理实验。
- 代码/数据只承诺开源，未给链接；复现需要重建 Minion / Open Deep Research 的提示与模板抽取流程。

## G 引用信息

```bibtex
@inproceedings{zhang2025apc,
  title     = {Agentic Plan Caching: Test-Time Memory for Fast and Cost-Efficient LLM Agents},
  author    = {Zhang, Qizheng and Wornow, Michael and Olukotun, Kunle},
  booktitle = {39th Conference on Neural Information Processing Systems (NeurIPS)},
  year      = {2025},
  note      = {arXiv:2506.14852v2}
}
```

来源页面：NeurIPS 2025 论文页；arXiv `https://arxiv.org/abs/2506.14852`；本地 PDF `paper_source/AgenticPlanCaching_NeurIPS2025.pdf`。

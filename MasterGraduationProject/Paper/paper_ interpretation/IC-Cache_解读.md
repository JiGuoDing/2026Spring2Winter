---
template: doc
theme: auto
lang: zh
title: IC-Cache：把历史问答当作上下文示例来“缓存能力”
subtitle: SOSP 2025 · resp
source: Yifan Yu et al., "IC-Cache: Efficient Large Language Model Serving via In-context Caching," SOSP 2025, 24 pages, DOI 10.1145/3731569.3764829.
outline: right
---

IC-Cache 不直接返回历史回答，而是把历史“请求—回答”对当作 in-context 示例，喂给更小的模型，让小模型模仿大模型的推理与格式。缓存命中不等于跳过推理，而是“用示例换模型档位”：把请求从小模型身上跑出大模型的质量。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | IC-Cache: Efficient Large Language Model Serving via In-context Caching |
| 作者 | Yifan Yu、Yu Gan、Nikhil Sarda、Lillian Tsai、Jiaming Shen、Yanqi Zhou、Arvind Krishnamurthy、Fan Lai、Henry M. Levy、David E. Culler |
| 机构 | University of Illinois at Urbana-Champaign；Google；University of Washington |
| 发表 | ACM SIGOPS 31st Symposium on Operating Systems Principles（SOSP 2025），2025-10-13 至 10-16，Seoul |
| 正式版本 | ACM  proceedings，24 页，DOI 10.1145/3731569.3764829，ACM ISBN 979-8-4007-1870-0/25/10 |
| arXiv / DOI | arXiv:2501.12689v3（2025-09-04）；DOI 10.1145/3731569.3764829 |
| 本地原文 | `paper_source/IC-Cache_arXiv2501.12689.pdf` |
| 代码/数据 | 未发现公开代码；实现约 3,000 行，支持 vLLM、HuggingFace Runtime、LangChain |
| 版本边界 | 本地 PDF 为 arXiv v3，页眉标注 SOSP '25；正式版 24 页。实验覆盖数百万条公开请求，但不是生产 trace |

## B 问题与动机

论文对四个开源用户请求数据集的分析显示，超过 70% 的请求在历史请求中有语义相似的对应对手。直接复用历史回答有两个问题：

- 精确匹配命中率低。
- 语义相似匹配会因上下文不匹配而显著降低质量。

作者的选择不是“复用答案”，而是“复用示例”。随着 1B–10B 的长上下文小模型出现，可以把大模型历史上的高质量请求—回答对作为 in-context examples，前置到新请求里，让小模型模仿大模型的组合能力（例如推理）。这样可以把请求从昂贵的大模型卸载到小模型，同时尽量不损质量。

这带来三个系统问题：

1. 如何在海量示例中挑出真正高 utility 的示例。
2. 如何按请求质量与当前负载，在大小模型之间路由。
3. 如何在分布漂移、容量与隐私约束下管理示例缓存。

## C 方法机制

**Example Selector：两阶段选例。**

- 第一阶段用嵌入相似度做轻量召回。离线用 K-Means 把示例聚成 `k` 组，论文取 `k = √n`，以平衡“找最近质心”和“组内搜索”的成本。
- 第二阶段用一个轻量 proxy model 估计“这条示例对当前请求的端到端 helpfulness”。proxy model 很小（论文举例 TinyBert 小于 Qwen2.5-7B 的 0.2%），异步更新。
- 选例数量由动态 utility 阈值决定：低于阈值的示例被过滤；系统周期性采样请求，比较不同阈值下的平均效率增益，选全局最优阈值。

论文指出，语义相关性与其真实 helpfulness 只有弱相关（Figure 7 的 Pearson 相关系数在 0.044–0.224 之间），所以不能只按相似度选例。

**Request Router：上下文多臂老虎机。**

- 每个 arm 是一个候选模型，例如“小模型 + 示例”或“大模型 + 无示例”。
- 上下文包含请求问题与已选示例。
- 奖励同时考虑响应质量和系统负载；路由器用 EMA 跟踪服务负载，当负载低于阈值时优先质量，高于阈值时优先卸载。
- 用 bandit 而不是静态分类器，是为了在线适应请求分布、示例 utility、模型版本和可用模型集合的变化。

**Example Manager：示例生命周期。**

- **Cost-aware replay**：同一请求多次生成，选最好的回答作为示例；离线（低峰期）执行。示例被复用数百次时，摊销开销约 1%；系统只对潜在收益高于 replay 成本的示例做 replay。
- **容量管理**：把示例缓存视为一维背包问题，每个示例有权重（明文长度）和价值（可实现的效率增益，即成功卸载次数）；用移动平均与每小时 0.9 的衰减因子跟踪近期价值，周期性求解，淘汰低 utility 示例。
- **隐私**：访问控制，只允许在指定用户域内共享；客户端用 spaCy 去除 PII；可选地用 DP 合成示例替代真实示例。

**实现。** Example Retriever 用 GPU FAISS；Router 用 Jax 实现 contextual bandit 与 prioritized replay buffer；各组件独立进程、gRPC 通信、可水平扩展；每个组件周期性 checkpoint，故障时绕过并直接走推理后端。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 平台 | 16×NVIDIA A100；请求到达跟随 Microsoft LLM serving trace 的 30 分钟片段 | — | 负载是真实 trace 缩放，不是合成 Poisson |
| 模型 | Gemini-1.5-Pro / Flash；DeepSeek-R1、Qwen2.5、Gemma-2、Phi-3 | — | 同时覆盖闭源与开源、不同规模 |
| 数据 | Alpaca、LMSys-Chat-1M、OpenOrca、MS MARCO、Natural Questions、WMT-16、Nl2bash、Math500 | 合计数百万条请求 | 覆盖对话、问答、翻译、代码、数学推理 |
| 端到端 | 与无 IC-Cache、RouteLLM、LongRAG、Semantic Caching 对比 | 吞吐 1.4–5.9×，延迟降低 28%–71%，质量不降 | 这是摘要级 headline，具体值随模型/数据集变化 |
| 与 RouteLLM 比 | 在线负载 | 质量高 9.0%，延迟与吞吐可比 | 路由感知负载是差异点 |
| 质量—效率前沿 | Gemma-2-2B vs 27B；归一化吞吐 | NQ 上目标 50% win rate 时吞吐 2.3×；固定 6× 大模型吞吐时质量高 4%–16%；MS MARCO 上 2B 的 win rate 超过 50%，即超过 27B | 小模型 + 示例可以跨规模胜出，但只在部分数据上 |
| 与语义缓存组合 | 不同缓存命中率下 | 最多 28% 质量提升，或同质量下 4.1× 效率 | IC-Cache 把“语义缓存命中但质量下降”的响应转成示例，而不是直接返回 |
| 与 SFT / RAG 组合 | NQ / MS MARCO | 分别再提升 17.8% 与 9.8% | 与后训练、检索增强互补 |
| 组件消融 | 去掉 Router / Retriever | 完整系统在质量—吞吐前沿上更好；MS MARCO 上最高 60% win rate、2× 吞吐；Alpaca 上 2.8× 吞吐无质量下降 | 选例与路由都必要 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `resp` 的一种特殊形态：历史请求—回答对，但命中后不作为答案直接返回，而是作为 in-context example 前置到新请求。它缓存的是“能力/示范”，不是“结论” |
| 价值建模 | 复用收益 = 把请求卸载到小模型后省下的成本/延迟 + 质量提升；成本 = 示例占用的上下文 token + 检索/proxy 打分 + replay。价值不是命中率，而是“单位成本下的成功卸载次数”。论文用 utility、potential gain、背包价值三个层次表达这一点 |
| 生命周期 | 写入：请求完成后进入示例池；保留：按 utility 与容量；驱逐：一维背包 + 0.9/小时衰减；刷新：cost-aware replay 重新生成更好的示例；TTL/预取：无显式 TTL，衰减相当于软过期 |
| Flink 映射 | 示例池用 keyed `MapState<exampleId, {prompt, response, embedding, utility, size}>`；utility 的 EMA 与衰减用 `ValueState`；timer 触发周期性背包重算与 replay；模型注册表/负载用 broadcast state；checkpoint 保存示例池与路由器统计。示例检索索引（FAISS）作为可重建数据面 |
| 可写缺口 | 示例价值用固定 0.9/小时衰减，未与模型版本、负载档位、领域漂移联合。可写“示例生命周期随模型版本切换重估”：同一示例在小模型升级后可能从高价值变低价值，论文的重放与衰减没有显式建模这一点 |

## F 局限与边界

- 质量评估主要依赖 LLM-as-a-judge（DeepSeek-R1 / Gemini-1.5-Pro 作 autorater），不是人工全量标注；论文报告了与人类偏好的一致性，但仍有评分偏差。
- 隐私方案是访问控制 + PII 清洗 + 可选 DP 合成，不是端到端的形式化隐私保证；示例仍可能泄露敏感信息。
- 没有形式化质量/错误率保证；“不损质量”是实验结论，不是约束。
- 示例池的价值假设是“历史示例可迁移”；在快速漂移、强个性化或模型能力变化时，旧示例可能失效。固定衰减因子是启发式。
- 评测覆盖数百万请求，但仍是公开数据集与模拟 trace；没有生产多租户、故障恢复、扩缩容实验。
- 未发现公开代码；3,000 行实现与 Jax bandit、FAISS 索引的细节不足以直接复现。

## G 引用信息

```bibtex
@inproceedings{yu2025iccache,
  title     = {IC-Cache: Efficient Large Language Model Serving via In-context Caching},
  author    = {Yu, Yifan and Gan, Yu and Sarda, Nikhil and Tsai, Lillian and Shen, Jiaming and Zhou, Yanqi and Krishnamurthy, Arvind and Lai, Fan and Levy, Henry M. and Culler, David E.},
  booktitle = {ACM SIGOPS 31st Symposium on Operating Systems Principles (SOSP)},
  year      = {2025},
  doi       = {10.1145/3731569.3764829}
}
```

来源页面：DOI `https://doi.org/10.1145/3731569.3764829`；arXiv `https://arxiv.org/abs/2501.12689`；本地 PDF `paper_source/IC-Cache_arXiv2501.12689.pdf`。

---
template: doc
theme: auto
lang: zh
title: SmartCache：跨会话语义复用的价值与代价
subtitle: NeurIPS 2025 · ctx/resp
source: NeurIPS 2025（第 39 届 Conference on Neural Information Processing Systems）
outline: right
---

多轮对话里，不同用户会问语义相同但措辞不同的问题；前缀缓存只认精确 token，普通语义缓存又忽略上下文和 KV 状态。SmartCache 用语义森林组织对话轮次，用注意力分数判断话题切换，并用 STEP 策略管理 KV 块的生命周期。对第一章最有用的是，它把“语义命中”与“上下文匹配”同时放进了复用条件。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | SmartCache: Context-aware Semantic Cache for Efficient Multi-turn LLM Inference |
| 作者 | Chengye Yu, Tianyu Wang, Zili Shao, Song Jiang |
| 机构 | The Chinese University of Hong Kong；Shenzhen University；University of Texas at Arlington |
| 发表 | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） |
| 正式版本 | NeurIPS 2025；页码论文未给出 |
| arXiv / DOI | 论文未给出 arXiv 编号；DOI 论文未给出 |
| 本地原文 | `paper_source/SmartCache_NeurIPS2025.pdf` |
| 代码/数据 | 未发现代码链接；实验使用 CoQA dev 与 SQuAD2.0 dev，模型为 Qwen2.5-1.5B、Llama-3.1-8B、Mistral-7B |
| 版本边界 | 本地 PDF 为 NeurIPS 2025 排版版；无 arXiv 版本可对照 |

## B 问题与动机

多用户、多轮对话中存在语义冗余。不同会话的用户可能问“什么是 PyTorch？”和“介绍一下 PyTorch”，答案几乎相同；系统却各自跑一遍完整推理，各自保存一份 KV。

前缀缓存（vLLM APC、RadixAttention）只按精确 token 前缀匹配。措辞一变，缓存就 miss；它主要加速 prefill，对逐 token 解码帮助有限。

普通语义缓存（如 GPTCache）按 query embedding 做平面检索，有两个问题。第一，忽略上下文：用户问“怎么用它？”，如果只按当前 query 检索，可能命中另一个上下文中“它”指代不同对象的答案。第二，与推理状态解耦：命中只返回文本，不更新 LLM 的 KV；下一次 miss 仍要重新处理整段历史。

论文的目标是同时做到：语义相似可复用、上下文不匹配不复用、复用能落到 KV 块上。

## C 方法机制

**语义树与语义森林。** 每个会话轮次（query-response 对）是一个语义节点。一个新会话的首问成为某棵语义树的根；后续问题在父节点下建子节点。同一主题的多个会话可以共享一棵树。森林的根节点 embedding 放在全局向量索引；每个节点只在自己的子节点向量索引里检索，检索空间被上下文限定。

**语义节点。** 节点保存 query embedding、缓存的 response、子节点向量索引，以及一个指向 KV 块的间接映射表。KV 本身仍在 LLM 侧，节点只保存“逻辑 token→上下文→物理块”的映射。

**上下文切换。** 会话进行中可能换话题。SmartCache 在 query prefill 时读取注意力分数：上下文相关的 query 对历史 token 的注意力明显更高；独立 query 的注意力更低。论文用每个模型离线标定的阈值判断；因为注意力分数在 prefill 中已经算过，额外开销可忽略。若判定为独立 query，会话切换到另一棵语义树或新建树。

**两级映射。** 原分页 KV 只有“会话逻辑 token→物理块”的 block table。SmartCache 增加两层：per-session context table（逻辑 token→上下文）和 per-context block table（上下文→物理块），由语义节点维护。多个会话引用同一语义节点时，共享同一批物理块，不需要复制 KV。

**STEP 驱逐。** 每个语义节点的驱逐紧迫度为：

`S_evict = α·SDS + β·SAS`

`SDS = 1 / Depth(N)`，`SAS = 1 / #Session(N)`。SDS 对应“语义深度”，SAS 对应“会话亲和度”：被更少活跃会话共享的节点更应被驱逐。论文附录取 `α=0.6`、`β=0.4`。

**预取。** 当会话推进到节点 `N`，按子节点流行度预取：

`AF(C_i) = #sessions accessed C_i after N / #sessions reached N`

统计在预定义时间窗内做，因为热点话题会变。流行度高的子节点提前搬到 GPU。

**写入。** 缓存 miss 时，LLM 正常生成，新节点加入森林；命中时直接复用 response 和 KV 块。语义相似度阈值设为 0.75，embedding 用 BGE-M3（1024 维），向量检索用 faiss 的 L2 距离。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 资源效率 | RTX 4090 24GB、256GB DDR4、Xeon Silver 4310、PCIe 4.0×16；CoQA/SQuAD2.0；3 个模型 | KV 内存比 PrefixCache 最多降 59.1%，比 GPTCache 最多降 56.0%；TTFT 比 PrefixCache 降 78.0%，比 GPTCache 降 71.7% | 语义命中减少了重复 prefill，也减少了重复 KV 副本 |
| 答案质量 | 0-shot；Qwen2.5-1.5B 在 CoQA | F1 比 GPTCache 高 39.9%，ROUGE-L 高 39.1%；ExactMatch 24.9 vs 16.8 | 上下文约束减少了“语义相似但答非所问”的假命中 |
| STEP | 1500 个会话；Llama-3.1-8B；GPU KV 预算 4GB；Zipf/Uniform/Pareto | 重用距离比 LRU 高 29.9%，比 LFU 高 25.7%（偏斜负载）；均匀负载下高 18.2%/15.9% | STEP 让“还会被访问”的节点活得更久 |
| 并发 | Mistral-7B；CoQA；1–64 并发 | 64 并发时相对基线 TTFT 加速 7.9× | 命中绕过完整推理，降低了有效 batch |
| 开销 | Mistral-7B；CoQA | 新 query 端到端 210.37ms 中，SmartCache 增加 18.54ms，约 8.8%；GPU 显存增加约 7.1%（主要是 embedding 模型）；CPU 内存约 28.05MB | 开销主要来自 embedding 生成，检索/插入/森林维护都较小 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx` + `resp`。对象是“语义节点”：一轮 query-response 加上它引用的 KV 块；节点可跨会话共享，因此缓存键不是 sessionId，而是“语义路径 + 上下文节点”。 |
| 价值建模 | 复用条件包含语义相似度和上下文匹配，天然带“复用风险”：上下文不匹配就拒绝。驱逐价值用 `SDS`（深度）和 `SAS`（会话亲和度），预取价值用子节点流行度。答案质量用 F1/ROUGE-L/ExactMatch 度量，可作为“质量约束”的实证。 |
| 生命周期 | 写入：miss 时新建节点并缓存 response/KV；共享：两级映射让多会话引用同一节点；驱逐：按 `S_evict`；预取：按 `AF` 预取子节点；失效：话题切换时改挂到其他树，没有 TTL/版本失效。 |
| Flink 映射 | `MapState<semanticNodeId, NodeMeta>` 存 embedding 引用、depth、session 集合、block 引用；`ValueState` 存时间窗内的访问计数；`TimerService` 触发 STEP 打分与子节点预取；`checkpoint` 保存森林结构；全局向量索引放外部（Flink 不做 ANN 检索）。 |
| 可写缺口 | 价值函数只有深度和会话数，没有重算成本、存储字节成本、加载成本；没有 TTL/版本失效；跨用户共享带来隐私风险。可写“语义价值 + 成本 + 隐私约束”的复合模型，并把 `SDS` 的方向歧义修正为可复现的公式。 |

## F 局限与边界

论文在结论中明确两个限制。第一，跨用户共享 response 有隐私风险；论文建议内容脱敏、访问控制、隐私过滤，但没有实现完整方案。第二，扩展到更多服务需要多实例部署，论文留作未来工作。

实验只用了 CoQA 与 SQuAD2.0，每个故事构造 1 个原始会话 + 2 个相似会话，平均 5 轮；真实多租户、长会话、话题频繁切换没有覆盖。

语义相似度阈值 0.75、注意力阈值、STEP 的 `α/β` 都是离线选定；换模型/领域需要重新标定。论文附录说明注意力阈值按模型离线 profile，但没有给出在线自适应方法。

`SDS = 1/Depth(N)` 与正文“deeper nodes are prioritized to be evicted”方向不一致：按公式，浅层节点得分更高、更应被驱逐；按文字，深层节点更应被驱逐。复现时需要核对实现，这也是一个可写的“公式与语义对齐”缺口。

实验硬件是单张 RTX 4090 24GB，模型最大 8B；没有 70B、多卡、生产 trace。论文未给出代码链接。

## G 引用信息

Yu, Chengye, Tianyu Wang, Zili Shao, and Song Jiang. “SmartCache: Context-aware Semantic Cache for Efficient Multi-turn LLM Inference.” In *Advances in Neural Information Processing Systems (NeurIPS 2025)*. 2025.

```bibtex
@inproceedings{yu2025smartcache,
  title     = {SmartCache: Context-aware Semantic Cache for Efficient Multi-turn LLM Inference},
  author    = {Yu, Chengye and Wang, Tianyu and Shao, Zili and Jiang, Song},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS 2025)},
  year      = {2025}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 4–8 页设计；第 8–10 页实验；第 10 页结论与限制；附录 A.3 给出 STEP 系数。

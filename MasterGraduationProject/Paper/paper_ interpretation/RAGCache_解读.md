---
template: doc
theme: auto
lang: zh
title: RAGCache：按文档顺序组织的多级 KV 知识树
subtitle: ACM TOCS 2025 · rag
source: ACM Transactions on Computer Systems, 2025, Vol. 44, No. 1, Article 2；arXiv:2404.12457v2
outline: right
---

RAG 的预填充被长文档拖慢，RAGCache 把每个文档的 KV 张量按检索顺序组织成知识树，并用前缀感知的 PGDSF 在 GPU/主机内存间做分层缓存。对第一章最有用的，是它把“复用收益/存储成本”写成了一个可计算的优先级。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | RAGCache: Efficient Knowledge Caching for Retrieval-Augmented Generation |
| 作者 | Chao Jin, Zili Zhang, Xuanlin Jiang, Fangyue Liu, Xin Liu, Xuanzhe Liu, Xin Jin |
| 机构 | 北京大学（1）；ByteDance Inc.（2） |
| 发表 | ACM Transactions on Computer Systems（TOCS），2025，Vol. 44，No. 1，Article 2 |
| 正式版本 | ACM TOCS 2025；抽取文本为 arXiv v2，TOCS 的页码与 DOI 未在文本中出现 |
| arXiv / DOI | arXiv:2404.12457v2 [cs.DC]，25 Apr 2024；DOI 论文未给出 |
| 本地原文 | `paper_source/RAGCache_arXiv2404.12457.pdf` |
| 代码/数据 | 未发现代码链接；Wikipedia 派生文档集、MMLU、Natural Questions 为公开数据 |
| 版本边界 | 本文数字均取自 arXiv v2；TOCS 排版版可能有差异 |

## B 问题与动机

RAG 请求由“检索文档 + 原问题”拼接而成，输入长度远大于原问题。论文举例：原请求 100 token，检索文档合计 1000 token，额外计算与内存开销超过 10 倍。

预填充是主要瓶颈。在 LLaMA2-7B 与单张 A10G 上，输入超过 4000 token 时推理时间接近 1 秒；文档平均长度 3718 token，而 MMLU 请求平均 348 token。

现有系统只解决了一部分问题。vLLM 用 PagedAttention 管理单请求内的 KV 块；SGLang 在 GPU 内复用跨请求的 KV。两者都没有利用 RAG 的检索模式，且 GPU 容量装不下大量长文档 KV。

论文给出两个机会。第一，同一文档会在多个请求中重复出现，文档 KV 可以跨请求共享。第二，检索分布高度倾斜：MMLU 中前 3% 的文档被 60% 的请求引用。

两个设计难点。其一是顺序敏感：`[D1,D2]` 与 `[D2,D1]` 的 KV 不同，不能交换文档顺序，否则生成质量会受影响。其二是流水线空转：向量检索在 CPU、生成在 GPU，串行执行会让 GPU 等待。

## C 方法机制

**知识树。** 根节点是共享的 system prompt，每条根到叶的路径表示一个文档序列，节点保存该文档的 KV 张量地址。不同请求的路径可以共享节点。前缀匹配沿路径向下，遇到不存在的子节点即停止，复杂度为 O(h)，h 为树高。

**PGDSF 替换策略。** 每个节点的优先级为：

`Priority = Clock + Frequency × Cost / Size`

Clock 表示访问新近度，GPU 与主机内存各维护一个逻辑时钟；Frequency 是时间窗内的检索次数；Size 是文档 token 数；Cost 是计算该文档 KV 的时间。优先级低的节点先被驱逐。

**前缀感知的成本估计。** 同一个文档在不同前缀下的重算成本不同。RAGCache 不用单次测量的成本，而是对“未缓存 token 的重算时间/新增 token 数”做多请求平均：

`Cost/Size = (1/m) Σ Cost_i / NewSize_i`

Cost_i 由离线 profiler 在不同“已缓存/未缓存 token 长度”下测得，再用双线性插值估计。这样成本会随文档大小摊销，避免大文档被系统性低估。

**分层与驱逐。** 节点优先放 GPU；访问较少的放主机内存；更少的直接释放。驱逐从叶子开始，保证被保留的前缀仍然完整。GPU 故障时，系统在主机内存复制部分高频上层节点，并用超时重试请求。

**缓存感知重排。** 在高请求率下，把共享前缀的请求排在一起，减少抖动，同时保留公平性以避免饥饿。

**动态推测流水线。** 向量检索分阶段返回候选文档；若候选发生变化且待处理请求数低于 `max_prefill_bs`，就提前启动一次推测生成。最终结果一致则直接返回，否则丢弃并重算。论文用 G/G/1 队列给出最优策略的条件。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 总体性能 | MMLU/NQ，Mistral-7B、LLaMA2-7B，最大 batch=4 | TTFT 比 vLLM 低 1.2–4×，比 SGLang 低 1.1–3.5×；吞吐高 1.3–2.1× / 1.2–1.8× | 分层缓存对两种注意力机制都有效 |
| top-k 变化 | top-1/3/5 | TTFT 比 vLLM 低 1.7–3.1×，比 SGLang 低 1.2–2.5× | 文档排列数随 k 阶乘增长，但热文档仍可复用 |
| 大模型 | Mixtral-8×7B、LLaMA2-70B，2×H800 | 比 vLLM 低 1.4–2.1×，比 SGLang 低 1.2–2.6×；TTFT 保持在 1.4 秒以下 | 显存变大后 SGLang 变强，但多级缓存仍占优 |
| 替换策略消融 | 主机内存 8–128 GiB，请求率 0.8 req/s | 命中率比 GDSF 高 1.02–1.32×，比 LRU 高 1.06–1.62×，比 LFU 高 1.06–1.75×；TTFT 低 1.05–1.29× | 大小、频率、重算成本三项都参与时有稳定收益 |
| 重排消融 | 请求率 2.5 / 1.4 req/s，窗口 32 | TTFT 降低 1.2–2.1× | 只在队列饱和时起作用 |
| 推测流水线 | 检索比例 12.5%–100% | TTFT 最多降低 1.6×；非重叠检索时间减少 1.5–4.3× | 把 CPU 检索藏到 GPU 预填充后面 |

调度开销在 0.5–2 req/s 下为 0.872–0.906 ms，相对秒级 TTFT 可忽略。

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `rag`。对象是“被检索文档的 KV 张量”，不是文档文本；同一文档在不同前缀下是不同副本，缓存键必须带顺序路径。 |
| 价值建模 | `Priority = Clock + Frequency × Cost / Size` 同时给出复用收益（Cost 为前缀感知重算时间）、未来复用概率（Frequency）与存储成本（Size）；精确 KV 使复用风险为 0，因此没有质量约束项。可作为第一章“收益侧”的基线。 |
| 生命周期 | 覆盖写入/准入（检索命中即建节点）、分层放置（GPU/主机）、驱逐（叶节点最低优先级）、未命中重算；没有 TTL，也没有文档更新后的失效。 |
| Flink 映射 | 知识树元数据可放 `MapState<docId, NodeMeta>`，每个节点的 clock/priority 放 `ValueState`；KV 张量本身外置到 GPU/主机缓存服务，Flink 只做准入与驱逐决策；`timer` 推进逻辑时钟，`checkpoint` 保存树结构与频次。 |
| 可写缺口 | 价值函数没有“新鲜度/版本”和“验证成本”。可把 key 扩为 `(docId, version)`，把 Cost 改为“重算 + 传输 + 失效验证”，并加入质量风险项；这是第一章可以直接写的增量。 |

## F 局限与边界

实验以单机单卡 A10G 或双卡 H800 为主，工作负载是 1 小时、Poisson 到达的 MMLU/NQ 请求，top-k 不超过 5。没有覆盖文档更新、多租户隔离、跨节点共享。

价值模型依赖离线 profiler 和双线性插值。GPU 型号、模型结构、batch 大小变化后，Cost 需要重新标定；论文没有给出在线校准方法。

缓存的是精确 KV，因此不改变生成质量，也就没有“复用风险”这一维。对第一章而言，它适合做“收益侧”的基线，不适合直接回答“过期答案是否可复用”。

论文未给出 TOCS 版的页码与 DOI，也未发现开源代码链接。上述数字均来自 arXiv v2。

## G 引用信息

Jin, Chao, Zili Zhang, Xuanlin Jiang, Fangyue Liu, Xin Liu, Xuanzhe Liu, and Xin Jin. “RAGCache: Efficient Knowledge Caching for Retrieval-Augmented Generation.” ACM Transactions on Computer Systems 44, no. 1 (2025): Article 2. arXiv:2404.12457v2.

```bibtex
@article{jin2025ragcache,
  title   = {RAGCache: Efficient Knowledge Caching for Retrieval-Augmented Generation},
  author  = {Jin, Chao and Zhang, Zili and Jiang, Xuanlin and Liu, Fangyue and Liu, Xin and Liu, Xuanzhe and Jin, Xin},
  journal = {ACM Transactions on Computer Systems},
  volume  = {44},
  number  = {1},
  pages   = {Article 2},
  year    = {2025},
  note    = {arXiv:2404.12457v2}
}
```

来源页面：arXiv 摘要页 `arXiv:2404.12457`；本地抽取文本第 1–13 页。

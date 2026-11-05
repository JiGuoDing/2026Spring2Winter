---
template: doc
theme: auto
lang: zh
title: ContextPilot：上下文块对齐与去重
subtitle: MLSys 2026 · rag
outline: right
source: MLSys 2026；arXiv:2511.03475v4
---

ContextPilot 不改 KV 结构，而是把检索到的上下文块重新排序、去重并加注释，让更多内容落在前缀缓存的命中路径上。对第一章最有用的，是它把“缓存命中率”当成可以主动构造的目标，而不是被动等待相同前缀。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | ContextPilot: Fast Long-Context Inference via Context Reuse |
| 作者 | Yinsicheng Jiang, Yeqi Huang, Liang Cheng, Cheng Deng, Xuan Sun, Luo Mai |
| 机构 | University of Edinburgh |
| 发表 | Proceedings of the 9th MLSys Conference，Bellevue, WA, USA，2026 |
| 正式版本 | MLSys 2026；页码未在抽取文本中给出 |
| arXiv / DOI | arXiv:2511.03475v4 [cs.LG]，6 May 2026；DOI 论文未给出 |
| 本地原文 | `paper_source/ContextPilot_MLSys2026.pdf` |
| 代码/数据 | https://github.com/EfficientContext/ContextPilot；QASPER、MultihopRAG、NarrativeQA、MT-RAG 为公开数据 |
| 版本边界 | 数字来自 arXiv v4；MLSys 正式版可能有差异 |

## B 问题与动机

长上下文推理的预填充瓶颈越来越突出。论文的 trace 显示，推理引擎经常处理 20k–130k 个预填充 token；32B dense 模型在单张 H100 上需要 3–10 秒。

精确前缀匹配的命中率很低。MultihopRAG + Qwen3-32B 的 KV 缓存命中率只有 4.6%，NarrativeQA + Llama3.3-70B 只有 5.5%。原因是同一批文档在不同请求中的顺序经常变化，空白或 token 的微小差异也会让匹配失败。

近似 KV 匹配能提高命中，但会掉质量。论文测得在多个模型和数据集上，近似匹配会让准确率下降 9–11%，从约 60% 降到约 50%。

论文的观察是：真实长上下文负载存在大量重叠。MultihopRAG、NarrativeQA、QASPER 中分别有 79.2%、57.4%、49.6% 的问题来自前 20% 最常访问的文档；MT-RAG 中任意一轮平均有 40% 的检索文档与更早的轮次重叠。

## C 方法机制

**上下文索引。** 用一棵树跟踪前缀缓存状态。每个节点保存：上下文块 ID 集合、从根到该节点的搜索路径、访问频次、创建时的聚类距离。构建用层次聚类：先算上下文两两距离，反复合并最近的一对，生成一个“共享前缀”的虚拟节点。构建复杂度 O(N²)，N 为上下文数；2000 个上下文在 CPU 上 8 秒、GPU 上 0.82 秒。

**距离函数。** 不仅看共享文档数，还看共享文档的位置是否一致：

`d_ij = 1 − |S_ij| / max(|C_i|, |C_j|) + α × Σ|p_i(k) − p_j(k)| / |S_ij|`

其中 `S_ij` 是共享文档集合，`p_i(k)` 是文档 k 在上下文 i 中的位置，α 取 0.001–0.01，保证重叠数量仍是主导项。

**对齐。** 对新请求，沿索引找到最长共享前缀，把匹配到的块放到前面，其余块保持原相对顺序。目标是让更多请求共享同一段前缀。搜索复杂度 O(|C| log n)，实测约 0.068 ms/请求；对齐约 0.047 ms/请求。

**调度。** 仅对齐还不够，执行顺序也会影响缓存。调度器按搜索路径的第一个元素分组，同组内按路径长度降序执行，让长前缀先进入缓存，避免短前缀把长前缀挤掉。分组 O(N)，组内排序 O(N log N)。

**注释。** 重排会改变相关性顺序，可能触发 lost-in-the-middle。ContextPilot 在 prompt 中加入简短注释，说明原始相关性排序和去重块的位置，让模型按语义而非位置理解上下文。论文的 DEmO 复现显示，新模型对顺序本身不敏感，注释主要补偿剩余扰动。

**去重。** 多轮对话中，重复块用位置注释替代，指向历史中的首次出现。细粒度重复用内容定义分块：在满足 `HASH(line) mod M = 0` 的行边界切分，保证插入/删除不会整体移位；相同子块用哈希识别，只保留首次出现。

**索引更新。** 推理引擎驱逐缓存时，把 request ID 发给 ContextPilot；ContextPilot 通过 request→node 映射删除对应节点，并递归剪掉空父节点。更新复杂度 O(h)。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 多会话 RAG | QASPER/MultihopRAG/NarrativeQA，Qwen3-4B/32B、Llama3.3-70B，top-k=15 | MultihopRAG 最高比 LMCache/Radix/CacheBlend 快 3.08×/2.05×/2.13×；NarrativeQA、QASPER 为 1.3–1.6× | 对齐把“部分重叠”变成“可命中前缀” |
| 多轮 RAG | MT-RAG，Qwen3-4B、Llama3.1-8B、Qwen3-30B | TTFT 比 LMCache 快 3.45×/3.35×/3.09×；比 Radix 最高 2.00×，比 CacheBlend 最高 1.55× | 去重对多轮重复最有效 |
| 混合并发 | Qwen3-4B，2–32 会话 | 2 会话：3.38×/1.92×/1.67×；32 会话：2.65×/1.49×/1.20×（对 LMCache/Radix/CacheBlend） | 并发升高后收益收窄但仍为正 |
| 大 MoE | DeepSeek-R1 671B，16–32×H20 | MultihopRAG 命中率 5%→60%，NarrativeQA 6%→38%；吞吐 1.81×/1.52× | 方法可扩展到多节点大模型 |
| 组件拆分 | MultihopRAG，SGLang/Qwen3-32B | 命中率 8.49%→20.56%（+对齐）→33.97%（+调度），约 4× | 对齐与调度各自有增量 |
| 真实 Agent | OpenClaw + SGLang，RTX 5090 | 文档分析：prompt token −24.4%、P99 −52.7%、预填充 −63.6%、墙钟 −20.7% | 端到端有效，但 coding 任务墙钟只降 12.4% |
| 边缘设备 | Llama-3.2-1B，llama.cpp | M3 MacBook Air：3.31 s→1.38 s（2.41×）；Jetson AGX Orin：2.12 s→1.41 s（1.50×） | 上下文缩减直接转化为墙钟收益 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx` 与 `rag` 的边界。对象是“外部上下文块”（检索文档、块、记忆条目），不是 KV 本身；它把块序列当作可重排、可去重的逻辑缓存单元。 |
| 价值建模 | 价值用共享前缀长度/命中率隐式表示；风险是重排/去重带来的顺序扰动（0.1–3.3% 精度损失）；未来复用概率来自跨会话、多轮的重叠统计。可作为“逻辑层复用价值”的参考。 |
| 生命周期 | 索引构建、请求到达时对齐、调度时排序、多轮去重、缓存驱逐时同步删除；没有 TTL，也没有内容版本失效。 |
| Flink 映射 | 按会话 key 建 `MapState<blockId, BlockMeta>` 与 `ValueState<SearchPath>`；`timer` 按轮次窗口触发重新对齐；跨会话索引可用 broadcast state 或外部索引服务；`checkpoint` 保存树与路径。 |
| 可写缺口 | 缓存键主要按 block ID 组织，未把内容哈希/文档版本纳入复用判定；文档更新后仍可能按旧块复用，注释也救不了事实变化。可把 key 扩为 `(blockId, contentHash, version)`，并用 `timer` 做过期重对齐；这是第一章可写的生命周期缺口。 |

## F 局限与边界

多会话实验是离线模式：所有上下文预先取好、索引预先构建，再做大 batch 推理；在线多轮和 Mem0 才是增量模式。两种模式的收益不能直接互换。

Mem0 + LoCoMo 上存在精度权衡：k=100 时 TTFT 从 0.101 s 降到 0.055 s（1.83×），准确率从 0.437 降到 0.420；k=20 时准确率从 0.440 升到 0.460。说明对齐并不总是提升质量。

索引构建是 O(N²)，100k 上下文虽能在 12 分钟内完成，但仍是离线成本。每请求开销约 0.7 ms，相对秒级预填充很小。

论文没有单独的 Limitations 章节；上述边界来自实验设置与结果本身。它没有验证文档内容更新、跨租户隔离、以及强一致性要求下的复用。

## G 引用信息

Jiang, Yinsicheng, Yeqi Huang, Liang Cheng, Cheng Deng, Xuan Sun, and Luo Mai. “ContextPilot: Fast Long-Context Inference via Context Reuse.” In Proceedings of the 9th MLSys Conference, 2026. arXiv:2511.03475v4.

```bibtex
@inproceedings{jiang2026contextpilot,
  title     = {ContextPilot: Fast Long-Context Inference via Context Reuse},
  author    = {Jiang, Yinsicheng and Huang, Yeqi and Cheng, Liang and Deng, Cheng and Sun, Xuan and Mai, Luo},
  booktitle = {Proceedings of the 9th MLSys Conference},
  year      = {2026},
  note      = {arXiv:2511.03475v4}
}
```

来源页面：arXiv 摘要页 `arXiv:2511.03475`；MLSys 2026 论文首页；本地抽取文本第 1–13 页。

---
template: doc
theme: auto
lang: zh
title: Cache-Craft：块级 KV 缓存的可复用性判定与选择性重算
subtitle: SIGMOD 2025 · rag
source: ACM SIGMOD 2025；arXiv:2502.15734v1
outline: right
---

RAG 的块级 KV 缓存不能像前缀缓存那样直接拼接，Cache-Craft 用注意力统计判断“这个块的 KV 被外部上下文污染了多少”，只重算少量关键 token，并给缓存变体打上可复用性分数。对第一章最有用的，是它把“复用风险”变成了可估计的 token 级重算预算。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Cache-Craft: Managing Chunk-Caches for Efficient Retrieval-Augmented Generation |
| 作者 | Shubham Agarwal, Sai Sundaresan, Subrata Mitra, Debabrata Mahapatra, Archit Gupta, Rounak Sharma, Nirmal Joshua Kapu, Tong Yu, Shiv Saini |
| 机构 | Adobe Research（1）；IIT Bombay（2）；IIT Kanpur（3） |
| 发表 | ACM SIGMOD 2025 |
| 正式版本 | SIGMOD 2025；抽取文本为 arXiv v1 预印本，正式版页码与 DOI 未在文本中出现 |
| arXiv / DOI | arXiv:2502.15734v1 [cs.DC]，5 Feb 2025；DOI 论文未给出 |
| 本地原文 | `paper_source/CacheCraft_arXiv2502.15734.pdf` |
| 代码/数据 | 论文称“plan to open-source”，未给出链接；Sys-X/Sys-Y 为生产负载，未公开 |
| 版本边界 | 数字来自 arXiv v1；SIGMOD 正式版可能有排版与数字差异 |

## B 问题与动机

RAG 的输入以检索块为主，回答很短。预填充因此成为主要成本。论文测得 LLaMA-3-70B 在 4×A100-80GB 上处理 32k token、batch=8 时，预填充可达 76 秒；在 Sys-X 中预填充占总推理时间最多 77%。

前缀缓存对 RAG 几乎无效。检索块的内容和顺序随问题变化，精确前缀匹配只覆盖 8% 的请求和 18% 的预填充 token。

重复仍然大量存在。Sys-X 中 75% 的检索块被重复处理，一个月超过 12B token；按 LLaMA-3-70B、8×A100 估算，需要 9600 GPU 小时，约 5 万美元。

直接复用块 KV 会掉质量。块的 KV 是在旧前缀下算出来的，换了上下文就缺少跨块注意力；论文测得 5 个块都从不同旧请求复用时，F1 下降 50%。

## C 方法机制

**两阶段。** 离线阶段为知识库中的块预计算 KV，并记录元数据；在线阶段为新请求选择可复用的块缓存，必要时重算少量 token。

**可复用性判定。** 对块 `c` 定义两个注意力指标：`inter` 是块内 token 对前缀块的累计注意力，`intra` 是块内 token 对块内前文的累计注意力。二者逐层平均后得到比值；比值越高，说明该块的 KV 越依赖外部上下文。

`CCI`（Cache Context Impact）由该比值经 sigmoid 归一化得到。CCI 高表示块高度依赖外部上下文，复用风险高；CCI 低表示块更“自包含”，更适合复用。

仅有 CCI 不够，还要看新旧前缀的重合程度。论文定义前缀重合分数 `P`，并用归一化 Kendall τ 计算顺序惩罚 `P_ord`，得到调整后的重合分数 `P_adj`。顺序不同会降低复用价值，因为 RoPE 位置和因果注意力都变了。

**选择性重算。** 复用块缓存时，按式 `CFO = β × CCI × (1 − P_adj)` 估计需要重算的 token 比例。CFO 越高，重算越多；`β` 是缩放系数，在验证集上按“最小化期望 CFO、同时满足 F1 ≥ F1_desired”选取。实际只重算对前缀注意力最高的 top-N 个 token，而不是整块。

**自适应提前终止。** 在逐层重算时，监控每个块对当前问题的累计注意力。若“重点块”集合连续若干层不变，就停止对非重点块的重算。论文称该策略减少约 55% 的 token 重算，质量基本不变。

**缓存变体与驱逐。** 每个块可存多个变体，每个变体记录 CCI、前缀和需要重算的 token 下标。系统按 `CCI × (1 − P_adj)` 选代价最低的变体。每次命中把该变体的 `frequency-reuse` 增加 `1/CFO`；缓存满时周期性驱逐该值最低的变体。

**分层预取。** 缓存按 GPU、CPU、SSD 分层；GPU 处理第 `l` 层时，异步预取第 `l+1` 层的块缓存。预取深度由层计算时间与加载时间之比决定，避免 SSD 加载拖慢预填充。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 生产负载总体 | Sys-X，LLaMA-3-8B/70B，vLLM+ORCA | 比前缀缓存减少 51% 的冗余计算；重算 20% token 时 ROUGE 0.87，Full-Cache 为 0.59 | 块级复用能把“几乎不可复用”变成可用 |
| 连续批处理 | Sys-X，重算 30% token | 8B：吞吐 1.6×、端到端时延 2.1×；70B：吞吐 1.6×、时延 2× | 保持 90% 基线 ROUGE F1 的前提下仍有收益 |
| 质量-重算曲线 | 2WikiMQA、MuSiQue、SQuAD、DROP、XSUM、CNN | 重算 20% 提升 ROUGE 约 30%，30% 提升约 42%；30% 时接近 Full-Recomp 的 1–5% 以内 | 重算比例是质量旋钮，不是固定常数 |
| 用户研究 | 250 人，2WikiMQA/SQuAD，各 500 题 | Cache-Craft 71.2%/78.9%，Full-Recomp 76.9%/83.7%，Full-Cache 29.8%/53.1% | 与完全重算的体感差距很小 |
| 设计消融 | 2WikiMQA，LLaMA-3-8B | 去掉缩放系数后重算升到 54%；去掉 focus 升到 70%；缩放系数取 0.5/1/2/3 时 ROUGE 为 0.825/0.896/0.94/0.953 | 前缀匹配与重点块筛选都在省算力 |
| 缓存加载 | CPU/SSD→GPU，Sys-X | CPU 0.03 s，SSD 0.59 s；异步后 SSD 0.27 s；逐层预取后 0.12 s | 分层缓存的关键是把加载藏在计算后面 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `rag`。对象是“块级 KV 缓存的一个变体”，同一块在不同前缀下可有多个副本；元数据包含 CCI、前缀、需重算 token 下标。 |
| 价值建模 | 用 CCI 度量复用风险，`1−P_adj` 度量前缀错位，CFO 把风险折成重算成本；`frequency-reuse += 1/CFO` 近似未来复用概率。可作为第一章“复用风险”的基线。 |
| 生命周期 | 离线写入；在线按变体选择；容量按 `K×V` 控制；周期性按频率复用值驱逐；GPU/CPU/SSD 分层与逐层预取；没有文档版本失效。 |
| Flink 映射 | `MapState<chunkHash, List<VariantMeta>>` 保存变体，`ValueState<Float>` 保存 `frequency-reuse`；`timer` 周期性触发驱逐；KV 张量放外部分层存储，`checkpoint` 保存元数据。 |
| 可写缺口 | 缓存键不含文档版本，知识库更新后旧变体仍可能被选中；质量预算按全局 β 设定，不能按请求类型调整。可把 key 扩为 `(chunkHash, docVersion)`，把 β 做成按 SLO 调整的在线参数。 |

## F 局限与边界

生产负载 Sys-X/Sys-Y 来自作者所在组织的真实系统，trace 未公开；公开数据集上的块切分、top-k、warm-up 设置与生产不完全一致。

缓存容量实验主要用 100 个块、每块 5 个变体，LLaMA-3-8B 约 0.05 TB；这不能代表大规模知识库的驱逐行为。

方法假设知识库相对静态。论文没有评估文档更新后的失效、跨租户复用、以及缓存变体长期漂移。

质量评估以 ROUGE-L F1、Jaccard 和用户研究为主，不是严格的事实一致性审计。30% 重算在部分数据集上仍是常用设置，说明“少重算”并非无条件成立。

论文未给出 SIGMOD 正式版页码/DOI，也未给出代码仓库链接。

## G 引用信息

Agarwal, Shubham, Sai Sundaresan, Subrata Mitra, Debabrata Mahapatra, Archit Gupta, Rounak Sharma, Nirmal Joshua Kapu, Tong Yu, and Shiv Saini. “Cache-Craft: Managing Chunk-Caches for Efficient Retrieval-Augmented Generation.” In Proceedings of ACM SIGMOD 2025. arXiv:2502.15734v1.

```bibtex
@inproceedings{agarwal2025cachecraft,
  title     = {Cache-Craft: Managing Chunk-Caches for Efficient Retrieval-Augmented Generation},
  author    = {Agarwal, Shubham and Sundaresan, Sai and Mitra, Subrata and Mahapatra, Debabrata and Gupta, Archit and Sharma, Rounak and Kapu, Nirmal Joshua and Yu, Tong and Saini, Shiv},
  booktitle = {Proceedings of the ACM SIGMOD International Conference on Management of Data},
  year      = {2025},
  note      = {arXiv:2502.15734v1}
}
```

来源页面：arXiv 摘要页 `arXiv:2502.15734`；本地抽取文本第 1–13 页。

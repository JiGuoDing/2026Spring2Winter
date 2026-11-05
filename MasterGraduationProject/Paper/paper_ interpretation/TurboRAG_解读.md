---
template: doc
theme: auto
lang: zh
title: TurboRAG：离线块级 KV 预计算与位置重排
subtitle: EMNLP 2025 · rag
source: EMNLP 2025, pp. 6588–6601
outline: right
---

TurboRAG 把 RAG 的预填充拆成“离线算好每个文档块的 KV”与“在线拼接并只算 query”，用独立注意力掩码和重排后的 RoPE 位置保持质量。对第一章最有用的，是它给出了“全量预计算”这一极端策略的成本上界与存储代价。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | TurboRAG: Accelerating Retrieval-Augmented Generation with Precomputed KV Caches for Chunked Text |
| 作者 | Songshuo Lu, Hua Wang, Yutian Rong, Zhi Chen, Yaohua Tang |
| 机构 | Moore Threads AI（摩尔线程） |
| 发表 | EMNLP 2025，pp. 6588–6601 |
| 正式版本 | ACL Anthology 版，2025 年 11 月 4–9 日 |
| arXiv / DOI | 论文未给出 arXiv 编号；DOI 论文未给出 |
| 本地原文 | `paper_source/TurboRAG_EMNLP2025.pdf` |
| 代码/数据 | 论文称“将开源修改后的实现”，抽取文本未给出链接；训练数据为公开数据组合 |
| 版本边界 | 数字来自 EMNLP 2025 正式版；模型为 Qwen2-7B，另测 LLaMA-3.1-8B |

## B 问题与动机

传统 RAG 把检索到的 k 个块拼成一个长序列再做预填充。这带来三个问题：重复块每次都要重算 KV；拼接后注意力随长度二次增长；长上下文挤占显存，限制 batch。

论文的两个观察支撑“块级独立”。第一，跨块注意力很稀疏，大多数文档主要关注自身内容；把块间注意力完全屏蔽，query 对各块的注意力分布仍集中在相关文档上。第二，RoPE 只依赖相对位置偏移，不依赖绝对下标；只要保持 pairwise 距离，旋转相位就一致。

因此可以把“整段预填充”改成“离线逐块预填充 + 在线拼接”。难点是：直接拼接会得到重复的位置 ID（composite positions），破坏相对偏移；同时独立注意力掩码与训练时的因果掩码不一致，会导致精度下降。

## C 方法机制

**离线阶段。** 对知识库中的每个文档块单独做预填充，保存该块的 K/V 张量。文档嵌入仍用 BERT 类模型建向量索引。

**在线阶段。** 检索 top-k 块，取出对应 KV，按请求中的文档顺序拼接；对 query 单独做预填充，再进入解码。

**独立注意力。** 块间注意力全部置零，块内保持因果掩码；解码时 query、答案与所有文档之间仍可互相注意。这样每个块的 KV 只由块内前缀决定，才能离线计算。

**位置重排。** 若直接拼接，每个块的 K 都从位置 0 开始，得到 `[0..l, 0..l, ...]` 的重复位置。TurboRAG 把第 i 个块的位置改成 `[(i−1)l, il−1]`，得到单调递增的全局位置；由于 RoPE 只看相对偏移，只需用新位置重新施加旋转，不必重算 K。

**轻量 SFT。** 用与推理时相同的独立掩码和位置重排方式微调模型，使模型见过这种 KV 布局。训练以 Qwen2-7B 为基座，32×A100 80GB，batch 256，学习率 1e-5，AdamW，约 888 GPU 小时，按论文估算一次性成本低于 3000 美元。

**复杂度。** 在线只计算 query 的 KV，文档部分的 KV 全部来自缓存；论文称在线计算量（TFLOPs）降低约 98.46%。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| LongBench 多文档 QA | Qwen2-7B，A100 80GB，FlashAttention2 | 平均 TTFT 从 1165 ms 降到 134 ms，8.6×；MuSiQue 从 1610 ms 降到 171 ms，9.4× | 文档越长，离线缓存的收益越大 |
| RGB 精度 | 中英文，噪声比 0.2–0.8，top-5 | Naïve 95.3/98.2；TurboRAG-reordered 微调后 95.7/96.8；无微调 92.3/92.9 | 重排位置比复合位置稳，微调后差距很小 |
| 批处理扩展 | 固定召回 8192 token，query 128，batch 1–8 | batch=8：Naïve 5812 ms，Turbo 1429 ms，4.1×；不计 H2D 为 177 ms，32.8× | 跨 CPU→GPU 传输是主要剩余开销 |
| 计算量 | 同上 | TFLOPs 从 1090.93 降到 16.78，约 98.46% | 省的是预填充算力，不是解码 |
| 短文档 | 200 token/块，召回 5 块 | batch=1 仍有约 2× 加速；短文档另有 2.42× 的记录 | 块短时传输占比上升，收益收窄 |
| 通用能力回归 | OpenCompass，MMLU/TriviaQA/GSM-8K/MATH/HumanEval/AlpacaEval | 与 Naïve 的差值在 −0.94 到 +1.16 之间 | 独立掩码微调没有明显损伤通用能力 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `rag`。对象是“每个文档块的 KV”，一块一份，没有变体、没有前缀区分；键是块 ID，值是 K/V 张量。 |
| 价值建模 | 价值模型是退化的“全命中”：固定语料下每个块都预计算，收益等于省掉的预填充 FLOPs；存储成本可精确算出，512-token 块在 Qwen2-7B 上约 28 MB。质量风险靠位置重排与 SFT 控制，但不进入缓存决策。可作为第一章“收益上界/成本下界”的参照。 |
| 生命周期 | 只有“离线写入”和“在线读取”。没有准入、驱逐、TTL、刷新；论文把版本化缓存、增量离线管线、回退在线预填充列为未来工作。 |
| Flink 映射 | 不适合直接做在线缓存管理；可把离线预计算做成 Flink 批作业，`MapState<chunkId, CacheMeta>` 保存块 ID、版本、存储位置，在线算子只做查表与拼接。 |
| 可写缺口 | 动态知识库下的失效与版本管理完全空缺，也没有容量约束下的准入/驱逐。第一章可以把“全量预计算”作为基线，加入 `(chunkId, version)` 键、按价值/成本淘汰、以及文档更新后的增量重算。 |

## F 局限与边界

存储代价被论文明确承认：1M 个 512-token 块约需 28 TB；10^4–10^5 个段落的常见部署为 0.3–3 TB，8-bit 量化后 40–400 GB。这是“用空间换延迟”的极端点。

需要微调模型，限制了直接用于新模型的能力；论文把“减少或消除微调依赖”列为未来工作。

实验以 Qwen2-7B 为主，另有 LLaMA-3.1-8B 的一致性验证；没有覆盖多租户、跨节点共享、文档更新频率高的场景。

“100% 命中”只对固定语料成立。真实开放域 RAG 的知识库会变，块会新增、删除、改写；论文没有给出这些条件下的命中率与失效成本。

## G 引用信息

Lu, Songshuo, Hua Wang, Yutian Rong, Zhi Chen, and Yaohua Tang. “TurboRAG: Accelerating Retrieval-Augmented Generation with Precomputed KV Caches for Chunked Text.” In Proceedings of EMNLP 2025, pp. 6588–6601.

```bibtex
@inproceedings{lu2025turborag,
  title     = {TurboRAG: Accelerating Retrieval-Augmented Generation with Precomputed KV Caches for Chunked Text},
  author    = {Lu, Songshuo and Wang, Hua and Rong, Yutian and Chen, Zhi and Tang, Yaohua},
  booktitle = {Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing},
  pages     = {6588--6601},
  year      = {2025}
}
```

来源页面：ACL Anthology EMNLP 2025，pp. 6588–6601；本地抽取文本第 1–14 页。

---
template: doc
theme: auto
lang: zh
title: CacheBlend：跨块 KV 融合的选择性重算
subtitle: EuroSys 2025 · rag
outline: right
source: EuroSys 2025, pp. 94–109；arXiv:2405.16444v3
---

CacheBlend 不要求复用块一定在输入前缀，而是把多个块的预计算 KV 拼起来，再按“KV 偏差”选少量 token 逐层重算，补回跨块注意力。对第一章最有用的，是它把“缓存修复”做成了一个可调的质量-延迟旋钮。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion |
| 作者 | Jiayi Yao, Hanchen Li, Yuhan Liu, Siddhant Ray, Yihua Cheng, Qizheng Zhang, Kuntai Du, Shan Lu, Junchen Jiang |
| 机构 | University of Chicago；CUHK Shenzhen；Stanford University；Microsoft Research |
| 发表 | EuroSys 2025（第 20 届欧洲计算机系统会议），Rotterdam，pp. 94–109；Best Paper |
| 正式版本 | ACM EuroSys 2025，16 页；DOI 10.1145/3689031.3696098 |
| arXiv / DOI | arXiv:2405.16444v3 [cs.LG]，3 Apr 2025；DOI 10.1145/3689031.3696098 |
| 本地原文 | `paper_source/CacheBlend_arXiv2405.16444.pdf` |
| 代码/数据 | https://github.com/LMCache/LMCache；2WikiMQA、Musique、SAMSum、MultiNews 为公开数据 |
| 版本边界 | 数字取自 arXiv v3；与 EuroSys 正式版可能存在排版差异；Best Paper 称号来自会议信息 |

## B 问题与动机

RAG 输入通常包含多个检索块。预填充要处理全部 token，4K 上下文在单张 A40 上，Llama-34B 约 3 秒、Llama-70B 约 6 秒。

前缀缓存只能复用第一个块。后面的块不是前缀，KV 不能被直接复用，因此多块 RAG 的加速很有限。

全量 KV 复用（如 PromptCache）把每个块的 KV 独立算好，再按位置拼起来。它忽略了块间的 cross-attention，而 cross-attention 对多跳问答、跨文档汇总很关键；论文测得 F1 会明显下降。

目标不是“要不要复用”，而是“怎样在复用大部分 KV 的同时，把跨块注意力补回来”。论文把它表述为：让融合后的前向注意力矩阵尽量接近完整预填充的结果。

## C 方法机制

**逐层选择性重算。** 对每一层，只对一小部分 token 重新计算 K/V，其余 token 直接使用预计算值。重算比例 r 决定额外计算量：r% 的 token 对应约 r% 的完整预填充计算。

**选哪些 token。** 定义 KV 偏差：某层某 token 的 KV 与完整预填充 KV 的绝对差。再定义注意力偏差：该层前向注意力矩阵与完整版本的 L2 距离。论文的观察是，优先重算 KV 偏差最高的 token，注意力偏差下降最快。

这些 token 称为 HKVD（High-KV-Deviation）token。由于无法事先知道完整 KV，论文利用“相邻层的 HKVD 高度相关”这一性质，做逐层过滤：第一层全算，选出比例略高于 r 的候选；后续层只在候选里重算并继续收窄。这样不需要每层都全量预填充。

**重算与加载流水线。** 第 l 层的选择性重算只依赖第 l−1 层的 KV 偏差，因此可以在加载第 l+1 层 KV 的同时重算第 l 层。只要单层重算时间不超过单层加载时间，重算就不会增加 TTFT。

**控制器。** 给定存储设备和上下文长度，控制器用离线 profiler 估计 `T_recompute(r%, LLM, L)` 与 `T_load(LLM, L, device)`，选择使二者接近的 r，并取 `max(r, r*)`，其中 `r*` 是保证质量的最小比例，论文经验值为 15%。

同时，控制器在“不增加延迟”的约束下选择最便宜的存储设备：只要 `T_recompute(15%) ≥ T_load(device)`，该设备就可接受。

**缓存管理。** 输入按块切分并哈希，哈希命中则取 KV；新块的 KV 由 fusor 生成后写入。存储满时按 LRU 驱逐。论文只考虑单层存储设备（CPU RAM 或 SSD），没有做多层。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 总体 | 4 数据集、3 模型（Mistral-7B、Yi-34B、Llama-70B） | TTFT 比完整重算低 2.2–3.3×，吞吐高 2.8–5×；质量下降不超过 0.02 | 多块 RAG 也能接近前缀缓存的速度 |
| 与全量复用对比 | 同上 | F1/Rouge-L 从 0.15 提升到 0.35；比完整重算只低 0.01–0.03 | 补回 cross-attention 是质量提升的来源 |
| 重算比例 | Yi-34B，5%–18% | 质量损失最多 0.002；TTFT 比完整重算低 4.1–6.6×，比前缀缓存低 3.4–6.1× | r 是可调旋钮，不是越大越好 |
| 流水线可行性 | Llama-7B，4K 上下文 | 重算 15% 每层 3 ms，NVMe 加载每层 16 ms | 加载能完全遮住重算 |
| 流水线边界 | Llama-70B | 重算 15% 每层 7 ms，加载每层 4 ms | 大模型上加载遮不住重算，需要控制器降 r 或换设备 |
| 存储介质 | RAM vs 较慢 SSD | 两种介质都保持低 TTFT；慢盘上差距变小 | 收益从“算”转向“等 I/O” |
| RAG 方法对比 | MapReduce / MapRerank | 比 MapReduce TTFT 低 2–5×且 F1 更高 | 比“先摘要再回答”更适合多块场景 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `rag`。对象是“块 KV + 位置修正信息 + 每层 HKVD token 集合”；同一块只有一份缓存，读时按当前前缀做局部修复。 |
| 价值建模 | 把复用收益拆成省掉的预填充、选择性重算成本、KV 加载成本；质量风险由注意力偏差/重算比例约束；未来复用概率由哈希命中与请求分布隐式决定。可作为第一章“修复成本”维度的核心参考。 |
| 生命周期 | 完整预填充后写入；哈希查找；命中时读时修复；LRU 驱逐；按 `T_load ≤ T_recompute` 选存储层；没有 TTL、没有文档版本失效。 |
| Flink 映射 | `MapState<chunkHash, CacheMeta>` 保存位置、大小、最后访问；`ValueState<Double>` 保存该模型/上下文的推荐 r；`timer` 驱动 LRU 淘汰；KV 本体放外部存储，`checkpoint` 只保存元数据。 |
| 可写缺口 | LRU 只看新近度，不区分重算成本与新鲜度。可把驱逐分数改为 `(省预填充 − 修复成本 − 加载成本)/大小`，并在 key 中加入文档版本；这能把 CacheBlend 的读时修复扩展成生命周期策略。 |

## F 局限与边界

方法只适用于 transformer；Mamba、Griffin 等架构未验证。论文也未测试不同量化设置下的表现。

实验在 vLLM 上实现，未集成 DistServe、StableGen 等更新的 serving engine；跨计算节点共享 KV 也未研究。

质量评估以 F1、Rouge-L 和 6 个 512-token 块的 RAG 场景为主；没有覆盖超长文档、文档更新、多租户隔离。

“Best Paper”是会议层面的荣誉，不改变论文的证据边界：它证明的是多块 KV 融合的可行性，不是所有 RAG 负载都能获得同样的 2.2–3.3×。

## G 引用信息

Yao, Jiayi, Hanchen Li, Yuhan Liu, Siddhant Ray, Yihua Cheng, Qizheng Zhang, Kuntai Du, Shan Lu, and Junchen Jiang. “CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion.” In Proceedings of the 20th European Conference on Computer Systems (EuroSys ’25), pp. 94–109. ACM, 2025. https://doi.org/10.1145/3689031.3696098.

```bibtex
@inproceedings{yao2025cacheblend,
  title     = {CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion},
  author    = {Yao, Jiayi and Li, Hanchen and Liu, Yuhan and Ray, Siddhant and Cheng, Yihua and Zhang, Qizheng and Du, Kuntai and Lu, Shan and Jiang, Junchen},
  booktitle = {Proceedings of the 20th European Conference on Computer Systems (EuroSys '25)},
  pages     = {94--109},
  year      = {2025},
  doi       = {10.1145/3689031.3696098}
}
```

来源页面：ACM EuroSys 2025 论文首页与 DOI 页；本地抽取文本第 1–15 页。

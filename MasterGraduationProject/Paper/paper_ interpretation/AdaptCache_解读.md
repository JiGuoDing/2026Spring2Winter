---
template: doc
theme: auto
lang: zh
title: AdaptCache：按条目自适应压缩与放置的分层 KV 缓存
subtitle: SOSP 2025 BigMem Workshop · ctx
source: arXiv:2509.00105v2 [cs.OS], 2026-01-15, 3 pp.; SOSP 2025 BigMem Workshop
outline: right
---

问题是分层 KV 缓存把大部分命中压到慢速 SSD，导致加载延迟高；AdaptCache 为每个 KV 条目同时选择压缩算法、压缩率和 DRAM/SSD 放置，用“频率 × 质量—延迟效用”的边际增益做贪心决策，对第一章最有用的是一个可落地的条目级价值函数。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | AdaptCache: KV Cache Native Storage Hierarchy for Low-Delay and High-Quality Language Model Serving |
| 作者 | Shaoting Feng\*, Hanchen Li\*, Kuntai Du, Zhuohan Gu, Yuhan Liu, Jiayi Yao, Siddhant Ray, Samuel Shen, Yihua Cheng, Ganesh Ananthanarayanan, Junchen Jiang（\* 同等贡献） |
| 机构 | University of Chicago；Microsoft |
| 发表 | SOSP 2025 BigMem Workshop（按任务清单；论文正文未标注会议信息） |
| 正式版本 | arXiv v2，2026-01-15；workshop 正式版页码与 DOI 论文未给出 |
| arXiv / DOI | arXiv:2509.00105v2 [cs.OS]；DOI 论文未给出 |
| 本地原文 | `paper_source/AdaptCache_arXiv2509.00105.pdf`（3 页） |
| 代码/数据 | 未发现公开代码；6 个 LongBench 数据集，1,100 个上下文 |
| 版本边界 | 3 页 preliminary results；单张 A100（100 GB DRAM、400 GB SSD）；Llama-3.1-8B-Instruct |

## B–D 问题、方法与实验

**问题。** LLM 应用反复复用聊天历史与文档，最直接的办法是存 KV 并在新请求命中时加载。但 KV 总量超过 GPU 与 CPU 容量，只能把大部分条目放到 SSD；SSD 加载慢，命中率再高也换不来低延迟。论文给了一个量级：两个 H100 节点（各 80GB）+ 150GB CPU 内存，Llama-3.1-70B-Instruct 只能存约 500K token，约等于 30 个用户的聊天历史；Agent 应用一次运行可产生数百万 token，对应 KV 约 3TB。

**核心主张。** 不要对所有 KV 用同一套压缩算法与压缩率。压缩算法要随内容变：只在开头/结尾重要的文本适合 token dropping，持续提供新信息的文本适合量化。压缩率与放置要随内容和复用频率变：高频且易压缩的条目放 DRAM、用高压缩率；低频且难压缩的条目放 SSD、用低压缩率。

**方法。** 系统分三部分。estimator 离线测量各存储设备的传输延迟、解压开销，并从每个数据集抽 10 个条目、用 GPT-4o 生成问题，拟合“质量—压缩率”曲线；未来命中频率用历史命中频率估计。policy optimizer 为每个条目计算效用：

`Utility(i) = Freq(i) × (α × Quality(i, M_i, R_i) − size(i, M_i, R_i) / Bandwidth)`

其中 `M_i` 是压缩算法，`R_i` 是压缩率。全局目标是最大化总效用，本质是多选择背包（MCKP），论文称其 NP-hard，采用贪心近似并达到线性规划最优性。新条目到来时，对“进一步压缩或驱逐”计算单位空间节省带来的边际效用损失，选择损失最小的动作。executor 执行压缩与放置。

**实验。** 1,100 个上下文覆盖摘要、问答、代码三类任务；请求到达用泊松分布合成；磁盘读吞吐 1 GB/s。对比无压缩、KIVI+LRU、StreamingLLM+LRU、纯 prefill。

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 同质量比延迟 | 三类任务，对比最强固定压缩基线 | 延迟节省 1.43–2.4× | 自适应压缩/放置比固定策略更会利用 DRAM |
| 同延迟比质量 | 同上 | 质量提升 6%–55% | 质量收益随任务与压缩率变化，均值不能代表全部 |
| 对比 prefill/无压缩 | 允许 15% 质量下降 | TTFT 降低 56% | 复用 + 压缩优于重新计算 |
| 对比 KIVI | 同质量 | TTFT 降低 69% | 固定 2-bit 量化不是最优 |
| 对比 StreamingLLM | 同 TTFT | 质量提升 15%–89% | 固定 token dropping 在长上下文上损失大 |
| 命中率案例 | 代码任务，KIVI 2-bit | KIVI 的 DRAM 命中率 38%；AdaptCache 在四组延迟/质量权重下为 81%、56%、44%、11% | 权重越偏延迟，越激进压缩以换取 DRAM 命中 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 面向 `ctx` 的 KV 条目；条目是“一次写入、可被后续请求命中”的最小单位，和第一章的会话状态块可以一一对应 |
| 价值建模 | 这是本批最接近“价值函数”的论文：`Freq × (α·Quality − size/Bandwidth)` 同时含未来复用概率、质量、存储成本与加载成本；边际效用损失可直接作为准入/压缩/驱逐的统一判据 |
| 生命周期 | 写入时决定压缩算法与放置；驻留期间可再次压缩或下沉；容量不足时按边际效用损失驱逐；没有 TTL、刷新与失效机制 |
| Flink 映射 | 每个条目一个 `ValueState<EntryStat>`（freq、quality、compression、tier、lastAccess）；`MapState<entryId, EntryStat>` 做全局索引；用 timer 做频率衰减；checkpoint 保存效用参数；compaction 合并小条目 |
| 可写缺口 | 效用里没有“复用风险”和“租户隔离”，也没有 TTL/版本失效；质量曲线是离线小样本拟合。第一章可把它扩展成 `ctx/rag/resp` 共用的多目标效用，加入风险惩罚与验证成本，并在 Flink 状态后端实现 |

## F 局限与边界

论文只有 3 页，属于 preliminary results：没有超出 3 页篇幅的实现细节，没有端到端吞吐、CPU 开销、压缩/解压 CPU 时间。质量曲线每个数据集只抽 10 个条目，且用 GPT-4o 生成问题，存在分布偏差。实验是单张 A100、固定磁盘 1 GB/s，没有多租户并发、没有网络存储、没有安全维度。效用是贪心近似，作者明确说“不保证最优”。TTL、版本失效、跨对象（rag/resp）复用都未覆盖。

## G 引用信息

```bibtex
@misc{feng2026adaptcache,
  title  = {AdaptCache: KV Cache Native Storage Hierarchy for Low-Delay and High-Quality Language Model Serving},
  author = {Feng, Shaoting and Li, Hanchen and Du, Kuntai and Gu, Zhuohan and Liu, Yuhan and
            Yao, Jiayi and Ray, Siddhant and Shen, Samuel and Cheng, Yihua and
            Ananthanarayanan, Ganesh and Jiang, Junchen},
  year   = {2026},
  eprint = {2509.00105},
  archivePrefix = {arXiv},
  primaryClass  = {cs.OS},
  note   = {arXiv v2, 15 Jan 2026; SOSP 2025 BigMem Workshop}
}
```

来源页面：PDF 第 1 页标题、作者、摘要与引言；第 2 页效用定义与贪心算法；第 2–3 页实验设置与结果。

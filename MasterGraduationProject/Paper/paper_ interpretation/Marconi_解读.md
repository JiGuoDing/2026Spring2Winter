---
template: doc
theme: auto
lang: zh
title: Marconi：以 FLOP/Byte 给前缀缓存定价
subtitle: MLSys 2025 · ctx
source: MLSys 2025；Outstanding Paper Honorable Mention（任务说明）
outline: right
---

混合模型（Attention + SSM）的 SSM 状态只能原地更新，无法回滚成前缀，导致前缀缓存只能精确命中，且每个序列产生大量又大又稀有的状态。Marconi 用“重用场景分类”做准入，用 `recency + α·FLOP efficiency` 做驱逐。对第一章最有用的是，它把“单位存储换多少计算”写成了显式价值密度。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Marconi: Prefix Caching for the Era of Hybrid LLMs |
| 作者 | Rui Pan, Zhuang Wang, Zhen Jia, Can Karakus, Luca Zancato, Tri Dao, Yida Wang, Ravi Netravali |
| 机构 | Princeton University；AWS |
| 发表 | 8th Conference on Machine Learning and Systems（MLSys 2025），Santa Clara |
| 正式版本 | MLSys 2025；页码论文未给出；Outstanding Paper Honorable Mention（任务说明，正文未标注） |
| arXiv / DOI | 论文未给出 arXiv 编号；DOI 论文未给出 |
| 本地原文 | `paper_source/Marconi_MLSys2025.pdf` |
| 代码/数据 | https://github.com/ruipeterpan/marconi；LMSys、ShareGPT、SWE-Bench 轨迹 |
| 版本边界 | 本地 PDF 为 MLSys 2025 排版版；实验模型为 7B Hybrid 与 Jamba-1.5-Mini |

## B 问题与动机

混合模型把少量 Attention 层和多数 SSM（状态空间模型）层交替堆叠，兼顾长上下文效率与注意力召回。SSM 层把历史压缩成固定大小的循环状态，计算和内存随序列长度线性甚至常数增长。

问题在缓存。SSM 状态是原地更新的：处理完 `1...q` 后，状态只代表 `1...q`，不能回滚成 `1...p`（`p<q`）。因此前缀缓存不能像 Transformer 那样切片 KV，只能精确匹配整个前缀。

为了支持任意前缀复用，系统必须每隔一段 token 保存一个检查点。细粒度检查点会产生大量条目：每个条目包含该位置的全部 KV 和 SSM 状态。SSM 状态通常比单个 token 的 KV 大 10–100 倍；一个 7B 模型、10K token 的序列，状态总量可达 17.4GB，是同规模 Transformer 的 3.3 倍。

更糟的是命中稀疏。论文实测，块大小 32 时，25.0% 的 KV 块会被后续请求复用，但只有 0.4% 的 SSM 状态被复用，相差 65.3 倍。大量 SSM 状态占着缓存却从不命中，造成 thrashing。

所以存在一个两难：要最大化复用机会，就得细粒度检查点；细粒度检查点又会产生大而稀疏的条目，把缓存撑爆。论文要设计一套准入和驱逐策略，在这个两难中取平衡。

## C 方法机制

**统一 radix tree。** Marconi 用一棵 radix tree 同时管理 KV 和 SSM 状态。边表示一段 token 序列，边上存这段 token 的 KV，以及“该边最后一个 token 之前所有 token”的 SSM 状态。节点表示序列的分叉点。只有 KV 和 SSM 同时存在，前缀才能复用；缺一层就不算命中。

**准入分类。** 论文把可复用前缀分成两类：

- 纯输入（purely input）：system prompt、指令、few-shot 示例、长文档问答等，跨很多请求共享。
- 输入+输出（input and output）：多轮对话历史、Agent 与环境的交互轨迹，前缀包含上一轮生成的内容。

对纯输入，Marconi 在 prefill 前做“推测插入”：把新请求的输入 token 插入 radix tree，看是否会产生新的中间节点。若会，说明这是一个共享前缀的分叉点，就在 prefill 过程中保存该前缀的 SSM 状态。

对输入+输出，Marconi 只保存“最后一个解码 token”的 SSM 状态，因为对话通常从上一轮结尾继续，而不是从中间分支。

这样，每个序列最多准入两个 SSM 状态（一个分支点、一个最后 token），而不是每个块一个。代价是纯输入前缀要到第三次出现才能复用：第一次生成，第二次识别并检查点，第三次才命中。论文认为这类前缀通常被很多请求共享，少一次命中影响不大。

**驱逐价值。** 论文定义 FLOP efficiency：

`flop_efficiency = Total FLOPs across layers / Memory consumption of all states`

分子是复用该前缀能省下的 Attention、SSM、MLP 计算量，分母是该条目所有状态（KV + SSM）的内存。传统前缀缓存只看 recency，因为 Transformer 的 KV 大小与计算节省大致成正比；混合模型里 SSM 状态大小固定，与序列长度/计算节省无关，所以 recency 不够。

驱逐效用为：

`S(n) = recency(n) + α · flop_efficiency(n)`

`recency` 和 `flop_efficiency` 都归一化到 (0,1)。驱逐时每次删掉 `S` 最小的节点，直到腾出足够空间。`α=0` 退化为 LRU；`α` 越大越看重计算节省。

**α 的自适应。** 启动时 `α=0`，第一次驱逐后进入 bootstrap：继续用 LRU，同时记录 5–15 倍于“首次驱逐前请求数”的请求。然后并行网格搜索 `α`，用回放请求评估命中率，通常几秒完成，最后选命中率最高的 `α`。

**实现细节。** 驱逐时不仅考虑叶子，也考虑“只有一个孩子”的中间节点；多孩子节点代表多个请求共享的前缀，不应优先驱逐。中间节点被驱逐时，SSM 状态释放，KV 被孩子节点吸收。命中时只更新被访问节点的 recency，不更新祖先，因为祖先的 KV 会被孩子覆盖。

**检查点方式。** 支持 chunked state passing 的模型，直接物化倒数第二个 chunk 的状态；不支持者用两遍 prefill：第一遍预填充到目标前缀，第二遍从该状态继续。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 命中率 | 7B Hybrid（4 Attention/24 SSM/28 MLP）；LMSys、ShareGPT、SWE-Bench；对比 vLLM+ | token 命中率平均提升 4.5×、7.3×、34.4× | 序列越长、SSM 占比越高，细粒度检查点的浪费越大，Marconi 的准入越有效 |
| P95 TTFT | 同上 | 相对无前缀缓存降低 36.9%、73.2%、46.8%（281.4ms、106.3ms、617.0ms）；相对 vLLM+ 多降 36.1%、71.1%、46.8% | 命中率转化为尾延迟；SWE-Bench 绝对收益最大 |
| FLOP-aware 驱逐 | 与 SGLang+（相同准入、LRU 驱逐）对比 | token 命中率提升 19.0%–219.7%；SWE-Bench 上从 16.4% 到 32.7%（+99.4%） | 在相同准入下，按 FLOP/byte 驱逐比 LRU 更有效 |
| 长短序列权衡 | SWE-Bench；按输入长度分桶 | 小于 7K token 的序列命中率最多降 3.0%；大于 7K token 最多升 25.5%；总体 FLOP 节省提升 90.3%；P5 TTFT 差 6.3%（2.1ms），P50/P95 降 13.4%/22.0% | 这是有意的取舍：牺牲短序列命中率，换长序列的计算节省 |
| 缓存竞争 | 60–140GB 缓存 | 命中率提升 24.3%、51.5%、68.3%、30.0%、10.0% | 中等竞争时驱逐决策最关键；无竞争时大家都够用 |
| 层比例 | Attention:SSM 从 1:2 到 1:4 到 1:8 | 相对 vLLM+/SGLang+ 的提升从 13.5%/5.8% 到 66.6%/26.0% 到 2.6×/59.7% | SSM 越多，状态越大，Marconi 的价值越高 |
| SSM 维度 | 16（Mamba1）到 128（Mamba2） | 相对 vLLM+ 的提升从 5.7× 到 35.4× | 状态维度越大，准入过滤越重要 |
| 到达模式 | 会话到达 0.5–2/s；请求间隔 5–10s | 命中率从 48.7% 降到 43.0%；相对 SGLang+ 从 1.4× 升到 1.6× | 竞争越强，FLOP-aware 的相对收益越大 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx`。对象是“前缀缓存条目”，同时包含 Attention 层的 KV 和 SSM 层的循环状态；条目按序列前缀组织在 radix tree 中。它不是单纯的 KV 块，而是“多层状态联合体”。 |
| 价值建模 | 两层价值：准入用“重用场景分类”估计未来复用概率（纯输入 vs 输入+输出）；驱逐用 `FLOP efficiency = 可省 FLOPs / 状态字节`，再与 recency 加权。`S = recency + α·FLOP/byte` 是第一章“单位存储换多少计算”的直接公式。 |
| 生命周期 | 准入：推测插入识别分叉点，只保存分支点和最后 token 的 SSM；保留：radix tree 节点；驱逐：按 `S` 从小到大；失效：没有 TTL，靠 recency 和容量压力；刷新：无显式刷新，模型/前缀变化需重建。 |
| Flink 映射 | `MapState<nodeId, NodeMeta>` 存 recency、FLOP efficiency、状态字节、子节点数；`ValueState` 存全局 `α`；`TimerService` 衰减 recency；优先队列（`MapState` + 堆）做驱逐；`BroadcastState` 放模型层成本表；`checkpoint` 保存 radix tree。 |
| 可写缺口 | 价值函数只有计算节省和 recency，没有质量风险、验证成本、租户公平性；FLOP/byte 依赖具体模型与硬件成本表；没有 TTL/版本失效；只覆盖 Hybrid LLM 的前缀缓存。可写“计算节省 + 存储成本 + 质量约束”的通用价值模型，并把 SSM 的特殊性抽象成“状态类型”。 |

## F 局限与边界

论文没有单独的 Limitations 小节。实验模型是 7B Hybrid（4/24/28 层）和 Jamba-1.5-Mini（12B active/52B total，状态维度 128），硬件是 8×A100-40GB 或 4×A100-40GB；没有覆盖更大的 Hybrid 模型和多节点。

前缀复用是精确匹配，不改变输出质量；论文不评估语义近似复用，也没有“复用风险”这一维。

FLOP efficiency 依赖模型层组成、状态维度、硬件吞吐；换模型/GPU 需要重新计算成本表。`α` 的网格搜索虽然只要几秒，但在负载漂移时可能需要重新搜索。

SSM 检查点依赖模型支持 chunked state passing，否则要用两遍 prefill；这会增加实现复杂度和部分计算开销。

缓存容量实验在 60–140GB，命中率提升在低竞争时只有 10.0%；小缓存或极大缓存下收益会变小。

论文未给出 arXiv 编号；“Outstanding Paper Honorable Mention”来自任务说明，正文未标注。

## G 引用信息

Pan, Rui, Zhuang Wang, Zhen Jia, Can Karakus, Luca Zancato, Tri Dao, Yida Wang, and Ravi Netravali. “Marconi: Prefix Caching for the Era of Hybrid LLMs.” In *Proceedings of the 8th Conference on Machine Learning and Systems (MLSys 2025)*. 2025.

```bibtex
@inproceedings{pan2025marconi,
  title     = {Marconi: Prefix Caching for the Era of Hybrid LLMs},
  author    = {Pan, Rui and Wang, Zhuang and Jia, Zhen and Karakus, Can and Zancato, Luca and Dao, Tri and Wang, Yida and Netravali, Ravi},
  booktitle = {Proceedings of the 8th Conference on Machine Learning and Systems (MLSys 2025)},
  year      = {2025}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 2–5 页问题与设计；第 5–8 页准入/驱逐；第 8–12 页实验；第 12 页结论。

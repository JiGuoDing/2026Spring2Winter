---
template: doc
theme: auto
lang: zh
title: SCBench：以 KV 缓存生命周期评估长上下文方法
subtitle: ICLR 2025 · ctx（共享上下文）
source: ICLR 2025, pp. 1–31
outline: right
---

问题是以往长上下文评测只跑单请求，忽略了 KV 缓存被多轮、多请求复用的真实生命周期；SCBench 用 12 个任务、两种共享模式把生成—压缩—检索—加载四阶段拆开评测，对第一章最有用的是“复用质量随任务可压缩性与轮次变化”这一约束。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | SCBench: A KV Cache-Centric Analysis of Long-Context Methods |
| 作者 | Yucheng Li†, Huiqiang Jiang‡, Qianhui Wu, Xufang Luo, Surin Ahn, Chengruidong Zhang, Amir H. Abdi, Dongsheng Li, Jianfeng Gao, Yuqing Yang, Lili Qiu |
| 机构 | Microsoft Corporation；†University of Surrey（Microsoft 实习期间完成）；‡通讯作者 |
| 发表 | International Conference on Learning Representations (ICLR) 2025 |
| 正式版本 | ICLR 2025 会议论文，pp. 1–31（PDF 含附录） |
| arXiv / DOI | DOI 论文未给出；arXiv 编号论文未给出；项目页 https://aka.ms/SCBench |
| 本地原文 | `paper_source/SCBench_ICLR2025.pdf`（31 页） |
| 代码/数据 | https://aka.ms/SCBench；数据来自 RULER、InfiniteBench、RepoQA、LongBench 等改造 |
| 版本边界 | ICLR 2025 camera-ready；评测截至该版本，未覆盖 2025 年后的新方法 |

## B 问题与动机

长上下文模型支持 128K 到 10M token，但 prefill 计算与 KV 显存开销很高。现有优化围绕 KV 缓存展开：稀疏注意力、KV 丢弃、量化、检索、加载、提示压缩。问题在于这些方法大多只在单请求 benchmark 上评测，而真实应用会复用同一段上下文：多轮对话、多步推理、仓库级代码任务都要求后续查询命中同一批 KV。

前缀缓存已经在 vLLM、SGLang 与多家 LLM 服务商中落地，说明“跨请求复用”不是假设。另一条动机是查询条件压缩：不少方法在压缩时依赖当前 query，一旦后续 query 变了，压缩结果就可能失效。论文举 Mamba 为例，按当前查询压缩历史信息会妨碍回答后续问题。

## C 方法机制

SCBench 把长上下文方法放进四个 KV 生命周期阶段。生成阶段即 prefill，包括稀疏注意力、SSM/混合架构、提示压缩。压缩阶段在生成后裁剪或量化 KV，包括 StreamingLLM、SnapKV、KIVI。检索阶段按请求前缀从缓存池取回 KV 块，代表是 CacheBlend。加载阶段在解码时按需把部分 KV 从显存/DRAM/SSD 拉到片上，代表是 Quest、RetrievalAttention。

评测覆盖 12 个任务、四类能力：字符串检索（KV、前后缀、多跳）、语义检索（RepoQA、长文 QA）、全局信息（many-shot ICL、摘要、数组统计）、多任务（RepoQA+NIAH、摘要+KV 检索）。两种共享模式分别是多轮模式（同一会话内缓存）与多请求模式（跨会话缓存）。

论文还提出 Tri-shape：在 A-shape 的 sink token 与局部窗口之外，再保留最后一段 query 区域，形成三角稀疏模式；训练免费，目的是改善首轮与多请求表现。评测方法共 13 个、8 个类别，模型 8 个：Llama-3.1-8B/70B、Qwen2.5-72B/32B、Llama-3-8B-262K、GLM-4-9B-1M、Codestral Mamba 7B、Jamba-1.5-Mini。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 主实验 | 4×A100，BF16 贪心解码；8 个模型；13 个方法；931 个会话、4,853 个查询，平均 5 轮 | Llama-3.1-8B 多轮平均分：Full 48.7、MInference 42.5、CacheBlend 49.3、KIVI 32.0、StreamingLLM 15.5；多请求平均分：Full 37.2、StreamingLLM 14.5、SnapKV 15.2 | 子 O(n) 内存在首轮可用，后续轮次明显掉分；O(n) 内存方法更稳 |
| 压缩率 | 压缩率从 1 降到 1/32 | 子 O(n) 方法在 1/4 压缩率附近出现陡降；KIVI、RetrievalAttention 等保持 O(n) 内存的方法在更高压缩率下仍较高 | “省显存”与“可复用”存在非线性拐点 |
| 查询条件 | 同一方法分别给 query 与不给 query | 无 query 时 SnapKV 在语义检索从 19.0 降到 9.7；Tri-shape 在字符串检索从 12.1 降到 7.8；MInference 相对稳（28.1 对 28.9） | 依赖 query 的压缩难以直接用于共享上下文 |
| 任务类型 | 四类能力分开统计 | 稀疏 KV 方法在全局信息任务较好；精确字符串检索需要 O(n) 内存 | 质量约束要按任务类型设置，不能只看平均分 |

论文的核心结论是：解码阶段保持 O(n) 内存、编码阶段用稀疏计算，能在多请求下接近全注意力；把稀疏模式延伸到解码会显著掉分；动态稀疏比静态模式更有表达力；长生成还会出现注意力分布漂移（OOD），连 O(n) 方法也会退化。

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 主要对应 `ctx` 与 `rag`：共享的长文档、代码仓库、对话历史都是可复用上下文；论文把“缓存块”而非“整段提示”作为复用单位 |
| 价值建模 | 复用质量不是常量。它取决于任务可压缩性（随机 KV、前后缀检索不可压缩；摘要、NIAH 可压缩）、轮次（首轮 vs 后续）、以及压缩是否依赖 query。可写成质量约束 `Q(reuse) ≥ Q_min(task, turn)` |
| 生命周期 | 四阶段正好对应写入/生成、压缩、检索/复用、加载；查询条件压缩的缓存在 query 变化后应失效，属于“刷新/失效”而非普通 TTL |
| Flink 映射 | 以 `sessionId` 或 `contextId` keyBy，`MapState<blockId, KVRef>` 保存块级引用；新 query 到达时用 timer/水位触发 query-conditioned 缓存失效；checkpoint 保存块索引；RocksDB compaction 合并小 KV 块 |
| 可写缺口 | 论文只测准确率，不测延迟、显存、成本，也没有给出缓存策略。第一章可把“任务可压缩性 + 轮次 + 是否 query-aware”变成价值函数中的质量约束，并在 Flink 中实现按 query 失效的块级状态 |

## F 局限与边界

评测是 accuracy 导向，没有端到端延迟、吞吐、显存或费用数据；因此它证明“哪些方法在多轮下会掉分”，但不能直接回答“缓存值不值得留”。8 个模型中 6 个是 Transformer，SSM/混合架构只覆盖 Codestral Mamba 与 Jamba 两个。任务虽多，仍以构造型长上下文为主，真实 Agent 工具调用链未覆盖。查询条件实验只选 3 个方法（SnapKV、Tri-shape、MInference），不能代表所有压缩方法。长生成的分布漂移被指出，但论文没有给出修复机制。

## G 引用信息

```bibtex
@inproceedings{li2025scbench,
  title     = {SCBench: A KV Cache-Centric Analysis of Long-Context Methods},
  author    = {Li, Yucheng and Jiang, Huiqiang and Wu, Qianhui and Luo, Xufang and Ahn, Surin and
               Zhang, Chengruidong and Abdi, Amir H. and Li, Dongsheng and Gao, Jianfeng and
               Yang, Yuqing and Qiu, Lili},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2025},
  pages     = {1--31},
  url       = {https://aka.ms/SCBench}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 3–6 页四阶段分类与任务；第 8–10 页主结果与分析；第 10 页结论。

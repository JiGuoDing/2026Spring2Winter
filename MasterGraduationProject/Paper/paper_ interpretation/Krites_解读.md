---
template: doc
theme: auto
lang: zh
title: Krites：静态层与动态层之间的异步验证提升
subtitle: arXiv 2026 · resp
source: Asmit Kumar Singh et al., "Asynchronous Verified Semantic Caching for Tiered LLM Architectures," arXiv:2602.13165v2, 2026.
outline: right
---

Krites 不改变在线命中规则，而是在静态缓存“差一点就命中”的灰色区间里异步调用 LLM 判官；判官批准后，把离线审核过的静态回答写进动态缓存，形成指向高质量静态答案的可变指针。它把“验证”从关键路径挪走，用写入换未来的静态复用。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Asynchronous Verified Semantic Caching for Tiered LLM Architectures |
| 作者 | Asmit Kumar Singh、Haozhe Wang、Santosh Attaluri、Tak Chiam、Weihua Zhu |
| 机构 | Apple（作者单位均标为 Apple, USA） |
| 发表 | arXiv 预印本，2026；本地 PDF 无正式会议/期刊信息 |
| 正式版本 | 未发现正式 proceedings 版本；本地 PDF 共 7 页 |
| arXiv / DOI | arXiv:2602.13165v2 [cs.IR]（2026-03-12）；论文未印 DOI |
| 本地原文 | `paper_source/Krites_arXiv2602.13165.pdf` |
| 代码/数据 | 复用 vCache 的 SemCacheLMArena 与 SemCacheSearchQueries；未发现 Krites 自身代码或 artifact |
| 版本边界 | 摘要写“up to 3.9 times”，正文与 Table 1 写 +136%（对话）与 +290%（搜索）。3.9× 与 +290% 是同一相对增益的不同表述，不能同时套到两个负载上 |

## B 问题与动机

生产环境的语义缓存常是两层：

- 静态层：离线从日志挖掘、经较大模型/安全审核/人工评估 curated 的回答。质量高、稳定，但更新慢。
- 动态层：在线写入，吸收长尾流量和短期热点。

两层通常各用一个全局相似度阈值。阈值收紧会漏掉安全的复用机会；阈值放松会把语义不正确的结果返回给用户。

作者把“静态相似度略低于静态阈值”的区间称为灰色区间。这里的查询往往与静态问题等价，只是措辞不同；仅凭嵌入几何无法可靠区分“改写”与“不同意图”。

一个自然的方案是把 LLM 判官放在服务路径上，逐条验证边界请求；但这会给交互式负载增加延迟和算力，抵消缓存的主要收益。Krites 的问题是：能否保持关键路径不变，只用离路径验证把灰色区间里的静态答案安全地提升出来？

## C 方法机制

**服务路径不变。** 明显命中由静态层直接返回；否则查动态层；再否则调用 Agent 后端并把结果写回动态层。Krites 只在静态相似度落入灰色区间时增加一个后台任务。

**灰色区间。** 设静态阈值为 `τ_static`，下界为 `τ_min < τ_static`：

```text
gray(q) = 1[ τ_min ≤ sim(q, q_static) < τ_static ]
```

低于 `τ_min` 的候选被视为明显不可互换，不送判官。实验中取 `τ_min = 0`，即所有未命中静态阈值的静态候选都可进入验证。

**异步验证与提升。** 后台工作池执行 `VerifyAndPromote(q, q_static, r_static)`：

1. 取静态回答 `r_static`。
2. 调二元判官 `J(q, q_static, r_static)`，按严格 rubric 检查意图、实体/约束（名称、地点、时间、数量）、时效/个性化要求，输出单 token `APPROVE/REJECT`，温度 0。
3. 若批准，把 `(q, r_static)` upsert 进动态缓存。这就是 auxiliary overwrite：动态层成为指向静态答案的可变指针层。

之后相同查询或邻近改写命中这个动态键时，系统直接从动态层返回 curated 静态回答。判官调用率由灰色区间频率决定，受 `τ_min` 控制；`τ_min` 越低，覆盖越大，判官成本越高。

**工程细节。** 工作池包含队列与限流、对同一 `(q, q_static)` 对的去重、失败重试与退避。动态层原有 LRU/TTL 不变；提升项与普通动态项一样会被淘汰，不 pin 住。若淘汰后同一查询再次出现，会重新走基线路径，可能再次触发验证。

**评测中的判官。** 主实验不跑真实 LLM 判官，而是用 benchmark 的等价类作为 oracle：同一等价类就批准。这样把“策略”与“判官实现”解耦。另用 Claude Opus 4.5 在 100 对人审灰色区间样本上做真实性检查。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 数据与切分 | SemCacheLMArena 约 60k、SemCacheSearchQueries 约 150k；每数据集固定种子打乱，前 20% 作历史前缀，后 80% 作在线评测流 | 静态层只从历史前缀构建；动态层从空开始 | 避免静态构建泄漏到评测 |
| 静态层构建 | 选取累计覆盖历史请求 60% 的最小等价类集合；每类取历史前缀中最短 prompt 作唯一代表 | 静态层规模由覆盖率决定 | 静态层是“精选集合”，不是全量日志 |
| 基线 | GPTCache 式单阈值；阈值取 vCache Pareto 分析中错误率约 1%–2% 的配置 | 基线是强静态策略，不是弱默认值 | 增益不是靠放松阈值换来的 |
| 静态来源服务比例 | 直接静态命中 + 验证提升后的动态命中 | SemCacheLMArena：8.2% → 19.4%，+136.5%；SemCacheSearchQueries：2.2% → 8.6%，+290.3% | 提升的是“curated 答案覆盖”，不是总命中率 |
| 总命中率 | 同一服务路径 | 与基线相同 | 设计使然：Krites 不改变在线命中决策 |
| 关键路径延迟 | 同一请求触发验证 | 不增加 | 验证完全离路径；论文未给端到端延迟数值 |
| 判官真实性 | Claude Opus 4.5，100 对人审灰色区间样本 | 99/100 与人工接受/拒绝一致 | 只说明该样本上的可行性，不是普适精度 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `resp`：静态层 curated 的历史回答。与普通 resp 缓存不同，Krites 复用的是“回答 + 它的可信来源”，动态层只存指向静态答案的指针 |
| 价值建模 | 静态回答带质量/安全溢价；一次提升的期望收益约为 `p_approve × 后续复用次数`，成本是判官算力。论文只给出这个收益框架，没有具体 ROI 数字。误批准会给后续命中带来错误，作者给出上界 `ε · p_prom`（ε 为判官假批准率，`p_prom` 为提升命中流量占比） |
| 生命周期 | 写入：异步判官批准后 upsert 到动态层；保留/驱逐：继承动态层 LRU/TTL；刷新：不刷新静态层；失效：无显式版本机制；预取：无。核心动作是“提升（promotion）”，不是“预取” |
| Flink 映射 | 静态层用 broadcast state（只读、可版本化）；动态层用 keyed `MapState<queryKey, pointer>`；灰色区间请求走 side output 到异步验证算子；`State TTL` 或 timer 处理动态指针过期；checkpoint 要同时保存待验证队列与已提升指针，否则恢复后会重复判官调用或丢失提升 |
| 可写缺口 | 论文没有定义“待验证/已提升”的状态机，也没有处理静态条目版本变化。可写“把 promotion 做成可恢复状态，并在静态层版本更新时使旧指针失效”；这正好落在第一章的写入/失效生命周期上 |

## F 局限与边界

- 主结果是 trace-driven 模拟，判官用 benchmark 等价类 oracle；真实判官的假批准/假拒绝会改变收益。99/100 只是 100 对样本上的检查。
- 只提升静态答案，不改变静态层内容；静态层本身陈旧、错误或版本更新时，Krites 没有失效传播机制。
- 总命中率不变，收益体现在“静态来源占比”和答案质量/安全性上；论文没有给端到端延迟、吞吐或成本的绝对值。
- 没有形式化错误率保证；`ε · p_prom` 是上界框架，不是可部署的校准流程。
- 摘要的 3.9× 与正文 +136%/+290% 口径不一致；引用时应以 Table 1 为准。
- 只在两个 vCache benchmark 上评测，没有代码/artifact；静态层按历史流量 60% 构建，未扫其他覆盖率。

## G 引用信息

```bibtex
@article{singh2026krites,
  title   = {Asynchronous Verified Semantic Caching for Tiered LLM Architectures},
  author  = {Singh, Asmit Kumar and Wang, Haozhe and Attaluri, Santosh and Chiam, Tak and Zhu, Weihua},
  journal = {arXiv preprint arXiv:2602.13165},
  year    = {2026},
  note    = {v2, 12 Mar 2026}
}
```

来源页面：arXiv 摘要页 `https://arxiv.org/abs/2602.13165`；本地 PDF `paper_source/Krites_arXiv2602.13165.pdf`。

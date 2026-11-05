---
template: doc
theme: auto
lang: zh
title: FreshCache：按新鲜度风险分层的语义缓存
subtitle: arXiv 2026 · rag
outline: right
source: arXiv:2607.04281v1
---

FreshCache 把开放网页 RAG 的缓存复用写成“过期概率是否低于预算”的决策，按答案、URL 列表、页面内容三层分别设误差预算。对第一章最有用的，是它把“复用风险”从相似度阈值变成了可校准的时间风险。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Risk-Constrained Freshness-Aware Semantic Caching for Open-Web Retrieval-Augmented LLMs |
| 作者 | Muhammad Mansoor, Tahir Ahmad, Yeo-Chan Yoon |
| 机构 | Jeju National University, Jeju, Republic of Korea |
| 发表 | arXiv 预印本，2026 |
| 正式版本 | 未见会议/期刊正式版；抽取文本为 arXiv v1 |
| arXiv / DOI | arXiv:2607.04281v1 [cs.CL]，5 Jul 2026；DOI 论文未给出 |
| 本地原文 | `paper_source/FreshCache_arXiv2607.04281.pdf` |
| 代码/数据 | 未发现代码或数据链接；FreshCache-Bench 由 SealQA、FreshQA、TemporalAlignQA 与模板化韩语查询构建 |
| 版本边界 | 所有数字来自 arXiv v1；未经同行评审的正式版校验 |

## B 问题与动机

开放网页 RAG 的每条查询要调用搜索 API、抓取网页、再调用 LLM，延迟常超过 3 秒。语义缓存可以跳过重复流程，但现有方法大多只看向量相似度，不建模网页内容的时间变化。

固定 TTL 陷入两难：太短，缓存效率低；太长，过期答案损伤信任。不同查询的过期速度差异极大：国家首都可复用数月，实时比分几分钟就过期。

论文把复用决策改写为风险约束的时间推断：不仅要问“问题是否相似”，还要问“给定内容类型、条目年龄和缓存层级，这条结果过期的概率是多少，是否低于该层的误差预算”。

三层对应 RAG 管线的三个产物：L1 最终答案，L2 检索到的 URL 列表，L3 原始页面内容。每层有独立预算，因此可以在 L1 风险过高时退到 L2，仍省掉搜索；L2 也不安全时再退到 L3 做条件 GET。

## C 方法机制

**新鲜度分类。** 查询分为五类：TIMELESS、SLOW、MEDIUM、FAST、REAL_TIME。每类有不同半衰期，由 1h、12h、24h、7 天的快照变化率用最大似然拟合：

| 类别 | 半衰期 |
|:--|:--|
| TIMELESS | 22 天 |
| SLOW | 16 天 |
| MEDIUM | 15 小时 |
| FAST | 3 小时 |
| REAL_TIME | 30 秒 |

REAL_TIME 永不进入 L1/L2 缓存。

**规则风险模型。** 内容过期概率按指数衰减：

`P_content(f, Δt) = 1 − exp(−(ln 2 / h_f) × Δt)`

答案层和 URL 层比原始内容更抽象、聚合后更容易过期，因此乘上层系数：answer 1.5、url-list 1.2、content 1.0。最终 `P(stale) = 1 − (1 − P_content)^m_tier`。

**学习风险模型。** 25 维特征：新鲜度类别 one-hot、对数归一化缓存年龄、域名经验波动率、9 类答案类型、时间关键词、实体波动、query-query 余弦相似度、词法/实体重叠。三层隐藏层 [64, 32, 16]，LayerNorm、ReLU、dropout 0.3，sigmoid 输出。用 8.14 的正类权重处理 10.9% 正样本率，温度缩放 T=1.4672；Brier 0.098，ECE 0.140。

**复用判定。** 对每个候选条目，同时满足相似度阈值和风险预算才复用：`sim(q,q') ≥ τ_tier` 且 `P(stale | q', tier, age) ≤ ε_tier`。L1 的 ε=0.10、τ=0.40；L2 的 ε=0.20、τ=0.35；L3 的 ε=0.35。

L1 命中约 5 ms 返回；L2 命中跳过搜索但仍抓页面、重新生成答案；L3 命中只省单页抓取。若风险在 L3 预算与上界之间，发条件 GET，用 ETag/Last-Modified 把概率判断变成二值验证。

**实体过滤。** L1 还做 spaCy 实体匹配：任一 query 含有对方没有的实体就拒绝。20 个对抗样本中，单靠余弦会把 20 个都判为命中，实体过滤挡掉 15 个。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 主结果 | 24h 窗口，31,201 条 query，727 个 stale URL，BGE-M3 | MLP：0.1% 过期、97% 搜索节省；规则版：3.3%、98% | 在同一边界上同时压过期率与省搜索 |
| 基线对比 | 同上 | SemanticTTL 14.9%/72%；vCache 7.2%/47%；SCALM 5.2%/96%；TieredTTL 23.1%/99% | 只加层不加风险门，过期率反而最高 |
| 消融：风险门 | 去掉时间门，只留类别 TTL | 过期率从 14.9% 降到 3.3%，降 11.6 个百分点 | 收益主要来自时间风险门，不是分层本身 |
| 消融：MLP | 规则 vs 25 维 MLP | 过期率再降 3.2 个百分点；MEDIUM 新增 3,918 次 L1 命中且 0.0% 过期 | 学习模型能区分同类别内的稳定条目 |
| 真实变化审计 | 396 个哈希变化对，LLM judge | 仅 34.3% 的变化影响答案正确性；真实答案级过期约 0.034% | 哈希过期率是保守上界 |
| 时延 | 模拟 + 真实网页微基准 | L1 5 ms vs LLM 2500 ms；诚实的生产中位时延降幅约 80% | 99.8% 的中位降幅被复述命中夸大 |
| 条件 GET | 149 个 URL 的真实测试 | 模拟 150 ms，真实平均 565 ms；仅 11.3% 返回 304 | L3 验证在开放网上比设想弱 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 同时覆盖 `resp` 与 `rag`。L1 是最终回答（resp），L2 是 URL 列表（rag 的检索结果），L3 是页面内容（rag 的文档块）。这是第一章三类对象少见的统一分层样例。 |
| 价值建模 | 价值是省下的搜索/生成成本，风险是过期概率；论文没有显式的未来复用概率项，只用年龄与新鲜度类别推断过期风险，存储与验证成本也未进入目标函数。可作为第一章“复用风险 + 质量约束”的核心公式。 |
| 生命周期 | 未命中时写入；读时按风险门决定是否复用；L1→L2→L3 降级；条件 GET 刷新；REAL_TIME 直接绕过；没有容量约束下的准入/驱逐。 |
| Flink 映射 | 按归一化 query 建 `ValueState<CacheEntry>`（答案、URL、时间戳、层级）；`MapState<urlHash, ContentEntry>` 存内容；`timer` 在风险超过 ε 时触发复核；条件 GET 走 side output；`checkpoint` 保存条目与时间戳。 |
| 可写缺口 | 没有容量/驱逐模型，ε 是部署时固定的，未与请求率、存储成本联合优化。可把 ε 变成按 SLO 和负载调整的拉格朗日乘子，并给条目加 `U = 省成本 − λ·过期风险 − 存储成本` 的准入分数；这是第一章可直接写的缺口。 |

## F 局限与边界

规则模型在 1 小时窗口相对 SemanticTTL 提升很小，主要靠 MLP 补足；MLP 的特征在 FreshCache-Bench 的域名波动分布上训练，迁移到 EvolvingQA、DailyQA 时命中率明显下降。

主评估窗口是 24 小时，1 小时为辅；7 天只用于拟合半衰期，不是主评估点。

模拟的 p50 时延节省被复述 query 的 L1 命中夸大，论文自己给出更诚实的约 80%。条件 GET 在真实网页上只有 11.3% 返回 304，L3 验证的收益有限。

哈希过期是保守代理：396 个变化对中只有 34.3% 影响答案，真实答案级过期约 0.034%。但这也意味着不同方法的相对排序仍可用，绝对数值不能直接当生产错误率。

论文未给出代码/数据链接，FreshCache-Bench 未声明公开。

## G 引用信息

Mansoor, Muhammad, Tahir Ahmad, and Yeo-Chan Yoon. “Risk-Constrained Freshness-Aware Semantic Caching for Open-Web Retrieval-Augmented LLMs.” arXiv:2607.04281v1, 2026.

```bibtex
@article{mansoor2026freshcache,
  title   = {Risk-Constrained Freshness-Aware Semantic Caching for Open-Web Retrieval-Augmented LLMs},
  author  = {Mansoor, Muhammad and Ahmad, Tahir and Yoon, Yeo-Chan},
  journal = {arXiv preprint arXiv:2607.04281},
  year    = {2026},
  note    = {v1, 5 Jul 2026}
}
```

来源页面：arXiv 摘要页 `arXiv:2607.04281`；本地抽取文本第 1–13 页。

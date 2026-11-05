---
template: doc
theme: auto
lang: zh
title: Cortex：把远端工具知识做成可验证的语义缓存
subtitle: NSDI 2026 · resp + rag
source: Chaoyi Ruan et al., "Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching," NSDI 2026, pp. 2407–2421.
outline: right
---

Cortex 缓存的不是 token KV，也不是整段回答，而是 Agent 发往远端搜索、RAG 或数据服务的“工具查询 → 知识结果”。它用 ANN 召回候选、用 0.6B 语义判官验证，再叠加 TTL、成本感知淘汰和 Markov 预取；这是本批论文中生命周期最完整的一篇。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching |
| 作者 | Chaoyi Ruan、Chao Bi、Kaiwen Zheng、Ziji Shi、Xinyi Wan、Jialin Li |
| 机构 | National University of Singapore；University of Science and Technology of China；University of Toronto；Sea AI Lab |
| 发表 | 23rd USENIX Symposium on Networked Systems Design and Implementation（NSDI 2026），2026-05-04 至 05-06，Renton, WA |
| 正式版本 | USENIX Association  proceedings，pp. 2407–2421，ISBN 978-1-939133-54-0 |
| arXiv / DOI | arXiv:2509.17360v2（2026-02-03）；USENIX 正式版未印会议 DOI |
| 本地原文 | `paper_source/Cortex.pdf` |
| 代码/数据 | 截至调研未发现可核验的官方代码、trace 或 checkpoint；论文只给高层实现 |
| 版本边界 | arXiv v1 题名为 *Asteria: Semantic-Aware Cross-Region Caching for Agentic LLM Tool Access*，系统名 Asteria、索引名 Sine；v2 改为 Cortex / Seri。正式 PDF 与 v2 正文基本一致，仅多 USENIX 封面与版式 |

## B 问题与动机

Agent 的循环是“思考 → 生成工具查询 → 跨区调用搜索/RAG/API → 观察 → 继续思考”。远端访问位于推理关键路径。

论文测得 Search-R1-7B 在单张 H100 上，外部检索约占端到端执行时间的 40%–50%。跨区网络本身还有 100–300 ms 延迟；实验中的 Google Cloud Search API 每次请求平均 300–500 ms。批量请求可以提高 GPU 利用率，但不能消除单条请求等待远端结果的时延下界。

作者观察到的可缓存性来自两类局部性：

- 搜索兴趣呈头部集中，少数热点主题占据大部分访问；突发新闻会产生短时间相关查询。
- 代码 Agent 在同一仓库的多个 issue 中反复读取核心文件。

因此 Cortex 选择在“外部知识结果”这一层做语义复用，而不是复用完整 LLM 回答。

## C 方法机制

**Semantic Element（SE）。** 缓存项包含：

```text
SE = {
  key:        agent tool query / action,
  value:      remote tool response,
  embedding:  E(key),
  metadata:   { frequency, cost, latency, size,
                staticity, expiration_time }
}
```

`staticity` 由语义判官给出 1–10 的稳定性评分；`expiration_time` 是 TTL。论文没有给出 `staticity → TTL` 的映射公式，TTL 在实现上仍是用户配置。

**Seri 两阶段检索。** 第一阶段用 Faiss ANN 按余弦相似度召回候选：

```text
C(q) = { i | cos(E(q), E(q_i)) ≥ τ_sim }
```

第二阶段由 0.6B 语义判官判断旧结果能否回答新查询。下面的命中条件由 §4.1–§4.3 合并而来。它不是论文原样给出的单行公式：

```text
hit(q,i) = 1[i ∈ C(q)] · 1[S_lsm(q, r_i) ≥ τ_lsm] · 1[now < expiration_time_i]
```

论文示例取 `τ_sim = 0.9`、`τ_lsm = 0.9`。ANN 只负责召回，最终是否命中由判官决定；这样可拒绝“词面相近但答案不能复用”的假阳性。

**LCFU 淘汰。** 先删除 TTL 过期项；超容量时按分数从低到高淘汰，直到用量不超过容量：

```text
score(se) = log(Freq+1) · log(Cost·10^3+1) · log(Latency+1)
            · log(Staticity+1) / Size
```

它的意图不是最大化命中率，而是保留“更常用、回源更贵/更慢、更稳定、单位大小收益更高”的对象。Table 6 中 LCFU 命中率 0.86，低于 LFU 的 0.89。LCFU 吞吐 2.35 req/s，高于 LFU 的 2.16 req/s。

**一阶 Markov 预取。** 用已确认命中的查询序列估计 `P(q_next | q_current)`，超过置信阈值就异步回源并写入缓存。预取项初始 `frequency=0`，未被真实请求使用时会因低 LCFU 分数较早被淘汰。

**周期阈值重校准。** 固定 `τ_lsm` 会随负载漂移失效。Cortex 每分钟抽取约 5 条近期请求，离开关键路径回源取 ground truth，用目标 precision（示例 0.99）重新选阈值。论文称相对不重校准版本吞吐只降 2%。

**Agent/Judge 共置。** 用 CUDA MPS 将单 GPU 计算大致按 80%/20% 分给 Agent 与判官；判官队列严格让位于 Agent。判官拥塞时请求退化为 miss，走远端回源。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| Skewed search | 4 个数据集（Zilliz-GPT、HotpotQA、Musique、2Wiki），每个约 250 问、10 个簇，合计 1000 问，Zipf-0.99；对比无缓存与精确匹配缓存 | Musique 上相对精确匹配缓存最高 3.6× 吞吐；Cortex 命中率 >85%，精确匹配 <20%；端到端时延最高降 4× | 高命中来自作者构造的语义局部性，不是任意流量 |
| Trend-driven | 4 个主题的 12 小时 Google Trends 映射到 HotpotQA，压缩成 10 分钟 | 相对无缓存最高 3.8× 吞吐，命中率近 95% | 突发流量下 LCFU 会优先淘汰过时热点 |
| 代码 Agent | SWE-Bench Oracle 的 `sqlfluff` 子集 | 吞吐 +20%，命中率近 45% | 只报告一个仓库子集，未给 issue 清单 |
| 并发扩展 | Musique，cache ratio 0.4；请求速率 8 | Cortex 4.89 req/s，精确匹配 1.09，无缓存 0.86；即 4.5× / 5.7× | 基线受远端检索约束，增加并发只扩大排队 |
| 单请求拆解 | 低并发，隔离限流影响 | 总时延 1.08 s → 0.61 s；远端检索 0.48 s；缓存查询 0.02 s，判官 0.03 s | 本地开销约 0.05 s，远小于省掉的远端 0.48 s |
| API 调用与重试 | 同一任务 | 调用约 1300 → 103（−92%）；重试率 25% → 0.50% | 收益的一大来源是避开限流 |
| 限流消融 | 自部署 RAG，300 ms；对比无限流/有限流 | 无限流 1.5×；有限流 4.16×（正文写 4.2×） | headline 的 3.6×/5.7× 不能脱离限流条件 |
| 成本 | Musique 峰值负载 | 无缓存 / 判官独占 GPU / 共置：总成本 $82.5 / $158.5 / $76.64；吞吐 0.87 / 4.74 / 4.89 req/s | 共置把“多一张 GPU”的成本压回去 |
| 正确性消融 | 5 个 QA 数据集的最终 Exact Match | ANN-only 在 StrategyQA 上 0.69，完整 Cortex 回到 0.79；无缓存 0.79 | 这是最终答案质量，不是判官的 precision/recall |
| 淘汰策略 | HotpotQA | LRU / LFU / LCFU 命中率 0.88 / 0.89 / 0.86；吞吐 2.14 / 2.16 / 2.35 req/s | 命中率不是目标，避免的回源成本才是 |
| 共置开销 | Dedicated-2GPU vs MPS 80/20 | 2.89 vs 2.72 req/s；p99 6601 vs 7230 ms（+9.5%） | 保留约 94% 吞吐 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `rag`：工具查询与远端知识结果。命中后只省一次远端调用，Agent 仍要继续推理；这与“命中后直接返回完整回答”的 `resp` 不同，不能混用一个命中率 |
| 价值建模 | 复用收益 = 避免的远端延迟 + API 费用 + 限流/重试损失；成本 = 缓存查询 + 判官 + 存储。LCFU 用 `Frequency × Cost × Latency × Staticity / Size` 近似“每字节可避免代价”，是一个可解释的工程价值函数；但它没有在线估计，也没有形式化质量约束 |
| 生命周期 | 写入：ANN + 判官 + TTL；保留：TTL；驱逐：LCFU；刷新：周期回源重校准 `τ_lsm`；预取：一阶 Markov。五类动作齐全，适合作为第一章生命周期分类的“完整样例” |
| Flink 映射 | 以工具查询簇为 key：`MapState` 存 SE（结果、嵌入、频次、成本、时延、staticity、过期时间）；`State TTL` 或 timer 处理过期；side output 承载预取与回源校准；broadcast state 下发 `τ_sim/τ_lsm`；checkpoint 保存频次、TTL、校准样本。向量索引作为可重建数据面，不进入 checkpoint |
| 可写缺口 | LCFU 的权重和 `staticity → TTL` 映射都是静态手工设定，没有用观测到的“回源节省/陈旧命中率”在线校准。可写“每个 SE 的价值与 TTL 由在线收益估计共同决定”，把价值建模和失效策略连起来；Cortex 只给了固定公式 |

## F 局限与边界

- “不损害正确性”只是 5 个 QA 数据集上最终 Exact Match 基本不降的经验结果；没有形式化错误率保证，也没有判官本身的 precision/recall 曲线。
- 负载是作者构造的：Zipf-0.99、按簇重采样、12 小时 Trends 压缩成 10 分钟。低复用或强个性化流量下，3.6×/5.7× 不一定成立。
- 只测读取型 search/RAG；写操作、支付、权限敏感结果、强时效数据没有实验。`staticity` 与真实失效时间的关系无法从论文重建。
- 正式稿有几处实现层面的断裂：Algorithm 1 构造的 `D_annotated` 后续未使用；Algorithm 2 的 `items.PopFirst()` 未定义排序；§4.2 文字称有 target precision 约束，公式未印出。按字面无法直接复现。
- Table 7 表题写 H100，§6.6 正文写 single A100；共置硬件无法唯一确定。LCFU 的 `Cost·10^3` 还是手工单位缩放，换单位会改变排序。
- 没有公开代码/trace；主性能基线只有无缓存和精确匹配，ANN-only 只用于质量消融。

## G 引用信息

```bibtex
@inproceedings{ruan2026cortex,
  title     = {Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching},
  author    = {Ruan, Chaoyi and Bi, Chao and Zheng, Kaiwen and Shi, Ziji and Wan, Xinyi and Li, Jialin},
  booktitle = {23rd USENIX Symposium on Networked Systems Design and Implementation (NSDI)},
  pages     = {2407--2421},
  year      = {2026},
  publisher = {USENIX Association},
  note      = {arXiv:2509.17360v2}
}
```

更详细的长报告见同目录的 `Cortex调研报告.md`。

来源页面：USENIX 论文页 `https://www.usenix.org/conference/nsdi26/presentation/ruan-cortex`；正式 PDF `https://www.usenix.org/system/files/nsdi26-ruan-cortex.pdf`；arXiv `https://arxiv.org/abs/2509.17360`。

---
template: doc
theme: auto
lang: zh
title: Semantic Caching for Low-Cost LLM Serving：从离线集合优化到在线自适应
subtitle: INFOCOM 2026 · resp · 语义缓存集合选择与未知参数学习
source: Xutong Liu, Baran Atalar, Xiangxiang Dai, Jinhang Zuo, Siwei Wang, John C. S. Lui, Wei Chen, Carlee Joe-Wong, "Semantic Caching for Low-Cost LLM Serving: From Offline Learning to Online Adaptation," INFOCOM 2026, arXiv:2508.07675v3.
outline: right
mode: light
---

这篇论文研究“缓存哪些查询”。它保留语义相似检索，但与 vCache 的逐条目质量门控不同。核心对象是一个容量为 $k$ 的全局缓存集合。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Semantic Caching for Low-Cost LLM Serving: From Offline Learning to Online Adaptation |
| 作者 | Xutong Liu、Baran Atalar、Xiangxiang Dai、Jinhang Zuo、Siwei Wang、John C. S. Lui、Wei Chen、Carlee Joe-Wong |
| 机构 | University of Washington；Carnegie Mellon University；CUHK；CityU Hong Kong；Microsoft Research |
| 发表 | IEEE INFOCOM 2026 |
| 公开版本 | arXiv:2508.07675v3，2026-02-13 |
| DOI | [10.1109/INFOCOM59046.2026.11571467](https://doi.org/10.1109/INFOCOM59046.2026.11571467) |
| 缓存对象 | `resp`：查询及其完整 LLM 回答 |
| 核心问题 | 在查询概率和回源成本未知时，选择至多 $k$ 个查询进入语义缓存 |
| 方法族 | Reverse Greedy；CUCB-SC；CLCB-SC-LS |
| 实验边界 | 仅有合成数据；主要设置 $m=20$、$k=5$；未给真实部署 trace |
| 代码 | 本次检索未发现论文给出的可核验官方实现 |

**一句话定位：** 它把语义缓存写成一个带失配代价的集合优化问题，再用离线或在线学习估计未知参数。

## B 系统模型

系统有 $m$ 个不同查询：

$$
\mathcal{Q}=\{q_1,\ldots,q_m\}.
$$

每个查询有两个未知量：

- $p(q)$：到达概率，且 $\sum_q p(q)=1$。
- $c(q)$：调用 LLM 的期望成本，归一化到 $[0,1]$。

缓存集合为：

$$
\mathcal{M}\subseteq\mathcal{Q},\qquad |\mathcal{M}|\le k.
$$

查询 $q$ 到达后，系统有两种动作：

- 调用 LLM：支付 $c(q)$。
- 复用最近缓存项：支付失配成本 $d(q,\mathcal{M})$。

```flow LR
(Query q) -> [Nearest cached u]
[Nearest cached u] -> {c(q) <= d(q,u)?}
{c(q) <= d(q,u)?} -> [Call LLM]: yes
{c(q) <= d(q,u)?} -> [Reuse response]: no
[Call LLM] -> (Fresh answer)
[Reuse response] -> (Mismatch loss)
```

其中：

$$
d(q,\mathcal{M})=\min_{u\in\mathcal{M}}d(q,u).
$$

系统采用最优即时动作：

$$
\min\{c(q),d(q,\mathcal{M})\}.
$$

期望损失是：

$$
\ell(\mathcal{M};\boldsymbol p,\boldsymbol c,d)
=\sum_{q\in\mathcal{Q}}p(q)\min\{c(q),d(q,\mathcal{M})\}.
$$

优化目标是：

$$
\mathcal{M}^{*}=\arg\min_{\mathcal{M}\subseteq\mathcal{Q},|\mathcal{M}|\le k}\ell(\mathcal{M};\boldsymbol p,\boldsymbol c,d).
$$

**关键区别：** $d$ 是“复用旧回答的效用损失”，不是“回答正确的概率”。论文默认距离可以代表失配代价。

### B.1 两个特例

| 设定 | 距离定义 | 退化结果 |
|:--|:--|:--|
| Exact-match cache | 只有同一查询距离为 0 | 传统精确匹配缓存 |
| Bipartite coverage | 阈值内距离为 0，否则为 1 | 查询覆盖问题 |
| 一般语义缓存 | 任意度量 $d(q,u)$ | 带软失配代价的集合优化 |

Bipartite coverage 特例用于证明 NP-hardness。

## C 已知参数：Reverse Greedy

即使 $p$ 和 $c$ 全部已知，最优缓存仍很难求。

论文证明：

> 该优化问题是 NP-hard。

原因可从阈值距离特例看出：它等价于二部图上的最大顶点覆盖类问题。

### C.1 损失函数性质

论文证明 $\ell(\mathcal{M})$：

- 对集合 $\mathcal{M}$ 单调不增。
- 对集合 $\mathcal{M}$ 超模（supermodular）。

直观含义：

- 加入更多缓存项，损失不会上升。
- 缓存越大，新增一项带来的边际损失下降越小。

这适合反向贪心，而不是普通前向贪心。

### C.2 算法过程

```flow LR
(All queries cached) -> [Evaluate removal loss]
[Evaluate removal loss] -> [Remove least useful]
[Remove least useful] -> {Size > k?}
{Size > k?} -> [Repeat removal]: yes
{Size > k?} -> (Return cache): no
```

算法从 $\mathcal{Q}$ 开始。每轮删除一个查询：

$$
q_i=\arg\min_{q\in\mathcal{M}_{i-1}}
\ell(\mathcal{M}_{i-1}\setminus\{q\}).
$$

直到剩余 $k$ 项。

### C.3 近似保证

设曲率为：

$$
c=1-\min_{q\in\mathcal{Q}}
\frac{\ell(\mathcal{Q}\setminus\{q\})-\ell(\mathcal{Q})}
{\ell(\varnothing)-\ell(\{q\})}.
$$

令：

$$
\beta=\frac{c}{1-c}.
$$

Reverse Greedy 返回的 $\mathcal{M}$ 满足：

$$
\ell(\mathcal{M})
\le \frac{e^{\beta}-1}{\beta}\ell(\mathcal{M}^{*}).
$$

当曲率 $c=0$ 时，损失近似可加，比值为 1。曲率越大，保证越松。

> 注意：这里不是常见的 $1-1/e$ 子模最大化保证。目标函数是超模最小化，界依赖曲率。

## D 离线学习：CUCB-SC

离线场景有一批历史数据：

$$
\mathcal{D}=\{(\mathcal{M}_t,q_t,C_t)\}_{t=1}^{n}.
$$

反馈是不完整的：

- 每次查询都会观察 $q_t$，因此可估计 $p(q)$。
- 只有调用 LLM 时才观察 $C_t(q)$。
- 缓存命中时没有真实服务成本。

论文定义成本反馈概率：

$$
\nu(q)=\Pr[C_t\neq\varnothing\mid q_t=q].
$$

若某查询总被缓存，它的 $c(q)$ 就缺少样本。$\nu(q)$ 很小会放大估计误差。

### D.1 为什么用 UCB

CUCB-SC 用成本上置信界：

$$
\bar c(q)=\hat c(q)+
\sqrt{\frac{\log(6mn/\delta)}{2N_c(q)}}.
$$

这里是“悲观”估计：

- 成本估高。
- 不确定查询会被视为更贵。
- 可避免因低估成本而错误缓存。

注意：成本越高，越不值得缓存；所以上界在损失最小化语境下是保守选择。

### D.2 算法流程

```flow LR
(Logs) -> [Estimate p]
(Logs) -> [Estimate c UCB]
[Estimate p] -> (Reverse Greedy)
[Estimate c UCB] -> (Reverse Greedy)
(Reverse Greedy) -> [Cache of size k]
[Cache of size k] -> [Fetch answers]
```

### D.3 离线子最优界

定理给出近似误差：

$$
\operatorname{SubOpt}(\hat{\mathcal{M}})
\le
4\sqrt{
\frac{2\sum_{q\in\mathcal{Q}}\frac{1}{\nu(q)}
\log(\frac{6mn}{\delta})}{n}
}.
$$

因此：

- 随样本量 $n$ 增加，误差按 $\tilde O(\sqrt{m/n})$ 下降。
- 成本反馈越稀缺，即 $\nu(q)$ 越小，误差越大。
- 查询种类 $m$ 越多，估计难度越高。

## E 在线学习：CLCB-SC-LS

在线场景中，系统边服务边学习。缓存更新有切换成本。

### E.1 在线遗憾

令每轮缓存为 $\mathcal{M}_t$。新增缓存项需要调用 LLM 填充答案。

带切换成本的遗憾为：

$$
\operatorname{Reg}(T)=
\mathbb{E}\left[
\sum_{t=1}^{T}\ell(\mathcal{M}_t)
+\sum_{q\in\mathcal{M}_t\setminus\mathcal{M}_{t-1}}c(q)
\right]
-\sum_{t=1}^{T}\alpha\ell(\mathcal{M}^{*}).
$$

$\alpha$ 是 Reverse Greedy 的近似因子。

不能每轮重建缓存。否则切换成本会线性增长。

### E.2 低切换机制

CLCB-SC-LS 为成本估计和到达概率估计分别设置阶段。

只有观测数跨过阈值才触发缓存更新：

```timeline v
1 | 查询到达 | 记录 q_t
2 | 判断阶段 | 成本反馈或到达样本是否足够
3 | 触发切换 | 用当前估计重建缓存
4 | 填充新项 | 对新缓存项调用 LLM
5 | LCB 比较 | 判断调用 LLM 还是复用
6 | 更新统计 | 观察到成本时才更新 c 估计
7 | 进入下一轮 | 保持缓存直到下次阶段切换
```

阶段阈值随累计观测增长。这样切换次数被压到次线性规模。

### E.3 为什么用 LCB

在线算法使用成本下置信界：

$$
\underline c_t(q)=\hat c_t(q)-
\sqrt{\frac{2\log(4mT/\delta)}{N_{c,t}(q)}}.
$$

这是“乐观”估计：

- 成本估低。
- LLM 调用看起来更便宜。
- 不确定查询更可能被真实查询，从而获得成本反馈。

当：

$$
\underline c_t(q_t)<d(q_t,\mathcal{M}_t)
$$

时调用 LLM。否则复用缓存。

### E.4 切换次数

论文证明：

$$
\mathbb{E}\left[\sum_{q\in\mathcal{Q}}\tau_q(T)\right]
=O(m\log\log T),
$$

$$
\mathbb{E}[\tau_p(T)]=O(\log\log T).
$$

$\tau_q$ 是查询成本阶段数。$\tau_p$ 是全局到达概率阶段数。

阶段式更新让缓存切换为 $O(m\log\log T)$，而不是每轮都切换。

## F 理论保证总表

| 信息设定 | 算法 | 主要结果 | 解释 |
|:--|:--|:--|:--|
| Oracle | Reverse Greedy | 曲率相关近似比 | 参数已知仍 NP-hard |
| Offline | CUCB-SC | $\tilde O(\sqrt{m/n})$ 子最优界 | 依赖成本反馈率 $1/\nu(q)$ |
| Online | CLCB-SC-LS | $\tilde O(\sqrt{mT}\log\log T)$ regret | 切换次数 $O(m\log\log T)$ |
| Exact-match 特例 | 同上 | 改进或匹配已有界 | 恢复经典精确缓存问题 |

在线遗憾对 $T$ 次线性。平均遗憾会随轮数增加趋近于零。

## G 实验证据

### G.1 实验设置

| 项 | 设置 |
|:--|:--|
| 数据 | ChatGPT 生成的合成查询 |
| 查询数 | 主要 $m=20$ |
| 缓存容量 | 离线主要 $k=5$ |
| 查询分布 | 均匀分布 |
| 成本 | 查询 token 数，min-max 归一化后加高斯噪声 |
| Embedding | Sentence Transformer，384 维 |
| 距离 | 归一化欧氏距离 |
| 重复次数 | 10 个随机种子 |
| 基线 | LFU、Epsilon Greedy、CUCB/CLCB 变体 |

### G.2 主要结果

| 实验 | 结果 |
|:--|:--|
| Reverse Greedy vs Brute Force | $m=20$ 时几乎完全重合 |
| Offline | CUCB-SC 和 CLCB-SC 优于 Epsilon Greedy |
| Online regret | 相比最强 Epsilon Greedy 至少改善 11.75% |
| $k/m$ 消融 | 最佳观测改善扩大到 54.04% |
| 切换次数 | 最多减少 90.91% |
| 运行时间 | 最多减少 85.40% |

### G.3 如何读这些数字

结果支持：

- Reverse Greedy 在小规模合成缓存上非常有竞争力。
- 低切换设计没有明显破坏在线遗憾。
- 阶段更新降低运行和切换开销。

结果不支持：

- 在真实 LLM 生产流量上同样有效。
- 在倾斜分布、无限查询集或多模态查询上同样有效。
- 在 freshness、权限和事实正确性约束下同样安全。

```callout warn 实验边界
实验只有 m=20 个合成查询，成本用查询 token 数近似，查询均匀到达。它验证了算法方向，不是生产 trace 复现。
```

## H 评价、边界与第一章用法

### H.1 主要贡献

- 把语义缓存写成统一的集合优化问题。
- 显式加入失配成本，连接语义复用和回源成本。
- 同时覆盖 Oracle、Offline、Online 三种信息设定。
- 给出近似、子最优和 regret 三类保证。
- 在线算法显式控制缓存切换成本。

### H.2 与 vCache / MVR-cache 的关系

| 维度 | vCache / MVR-cache | 本文 |
|:--|:--|:--|
| 决策对象 | 单条缓存的命中与错误率 | 全局缓存集合 $\mathcal{M}$ |
| 相似度作用 | 估计正确复用概率 | 充当失配成本 $d$ |
| 主要保证 | 正确率上界 | 近似比、子最优界、regret |
| 容量 | 不处理 | 固定基数 $k$ |
| 在线学习 | 阈值与观测 | 查询概率与 LLM 成本 |
| 成本模型 | 基本不计 | 显式最小化期望成本 |
| 失效与新鲜度 | 不处理 | 不处理 |
| 多租户与 ACL | 不处理 | 不处理 |

两者可以组合：

```flow LR
(Prompt) -> (MVR / verifier)
(MVR / verifier) -> [Calibrated reuse risk]
[Calibrated reuse risk] -> (Set optimizer)
(Set optimizer) -> [Cache budget k]
[Cache budget k] -> (Flink state)
```

### H.3 关键限制

| 限制 | 影响 |
|:--|:--|
| 查询空间有限且已知 | 新查询只在预定集合 $\mathcal{Q}$ 内学习；不处理开放世界 |
| 查询分布和成本平稳 | 未建模突发、趋势、热点漂移 |
| 距离即失配损失 | embedding 距离未校准为真实答案错误率 |
| 只约束基数 $k$ | 未处理文档大小、token 数、分层层级和存储字节 |
| 同质缓存项 | 无法表达摘要、RAG 证据、工具结果等异构状态 |
| 无 TTL / 刷新 | 不处理知识过时和版本失效 |
| 无多租户公平性 | 不处理权限、隔离和租户预算 |
| 合成实验规模小 | 对真实 Agent 负载的外部有效性有限 |
| 无官方实现 | 复现需要自行实现 Reverse Greedy 和置信界 |

### H.4 对第一章最有价值的连接

这篇论文可以直接支撑第一章的“集合层价值优化”：

1. **把缓存选择写成预算问题**：目标不是单条命中率，而是整组缓存的期望损失。
2. **显式分离收益和风险**：回源成本 $c(q)$ 与失配损失 $d(q,\mathcal{M})$ 竞争。
3. **把未观测反馈计入学习成本**：缓存命中时不观察真实成本，会形成反馈偏差。
4. **把切换成本纳入控制器**：扩容、驱逐和重建不是免费的。
5. **提供离线到在线的过渡模板**：历史日志先冷启动，线上再用低切换算法校准。

### H.5 论文尚未解决、适合扩展的地方

- 用校准后的 `q_wrong × L_answer` 替换原始 embedding 距离。
- 把固定 $k$ 扩展为多级别、异构字节预算。
- 把平稳分布扩展为负载漂移和概念漂移。
- 把有限查询集扩展到连续 embedding 或开放世界。
- 把成本 $c(q)$ 从 token 数扩展为 GPU-ms、检索调用和 SLO 违约损失。
- 把 TTL、文档版本、ACL 和依赖失效纳入集合优化。
- 把离线日志估计和在线反馈组合成混合控制策略。

```callout tip 第一章建议
把这篇论文当作“缓存集合层”的理论基线。MVR/vCache 负责判断单条缓存是否可信。Reverse Greedy 负责在容量 k 下选择保留对象。Flink 生命周期研究再补足版本、新鲜度、迁移和负载价格。
```

### H.6 最终判断

这篇论文是语义缓存理论化的重要基线。它的优点是把语义复用写成可证明的集合优化和在线学习问题。

它的局限也很清楚：距离代理、有限查询空间、平稳假设和合成实验。这些局限正好为第一章的“校准风险 + 依赖感知生命周期 + 流式状态”留下空间。

**原始材料：** [arXiv:2508.07675](https://arxiv.org/abs/2508.07675) · [INFOCOM DOI](https://doi.org/10.1109/INFOCOM59046.2026.11571467) · 后续连续空间工作：[Continuous Semantic Caching](https://arxiv.org/abs/2604.20021)
---
template: doc
theme: auto
lang: zh
title: vCache：为每个缓存条目学习可验证阈值
subtitle: ICLR 2026 · resp
source: Luis Gaspar Schroeder et al., "vCache: Verified Semantic Prompt Caching," ICLR 2026, arXiv:2502.03771v5.
outline: right
---

vCache 把“语义缓存该不该命中”从全局静态阈值，改成逐条目的随机化决策。每个缓存回答在线学习一组 sigmoid 参数，并受用户给定的错误率上限约束。悲观置信带把“探索多少次”折算成可证明的质量约束。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | vCache: Verified Semantic Prompt Caching |
| 作者 | Luis Gaspar Schroeder、Aditya Desai、Alejandro Cuadron、Kyle Chu、Shu Liu、Mark Zhao、Stephan Krusche、Alfons Kemper、Matei Zaharia、Joseph E. Gonzalez |
| 机构 | University of California, Berkeley；Technical University of Munich；ETH Zurich；Stanford University |
| 发表 | ICLR 2026（International Conference on Learning Representations） |
| 正式版本 | ICLR 2026 会议论文；本地 PDF 页眉标注 “Published as a conference paper at ICLR 2026”，正文无页码 |
| arXiv / DOI | arXiv:2502.03771v5（2026-02-21）；论文未印 DOI |
| 本地原文 | `paper_source/vCache.pdf` |
| 代码/数据 | `github.com/vcache-project/vCache`；`huggingface.co/vCache`（4 个语义缓存 benchmark） |
| 版本边界 | v5 的 §5 正文写 Llama-3-8B-Instruct / GPT-4o-mini，Figure 4/5 图注出现 Llama 3.1-8B / GPT-4.1-nano；§3 概述与 Algorithm 1 对“是否总是入库”的写法也不完全一致。本文以正文和算法为准 |

## B 问题与动机

语义缓存把请求嵌入后取最近邻，用相似度与阈值比较决定命中。工业系统普遍使用一个全局静态阈值，例如 0.8。

论文指出三个问题：

1. 静态阈值没有形式化正确性保证，生产环境无法承诺错误率。
2. 正确命中与错误命中的相似度分布高度重叠。作者在 SemCacheClassification 的 45k 样本上观察到这一点，因此固定阈值要么错误率高，要么被迫设得极高。
3. 不同缓存条目的“安全阈值”差异很大，一个全局阈值无法同时照顾所有条目。

作者的目标是：用户给定最大错误率 δ，系统在正确率不低于 1−δ 的约束下最大化命中率；且不依赖预训练、不绑定嵌入模型。

## C 方法机制

**缓存条目。** 每个缓存项保存三元组 `(E(x), r(x), O(x))`。`O(x)` 是该条目被当作最近邻时积累的观测集：

```text
O(x_i) = { (s(x_j), c(x_j)) | nn(x_j) = x_i }
s(x)   = sim(E(x), E(nn(x)))
c(x)   = 1[ r(nn(x)) == r(x) ]
```

也就是说，每个条目自己积累一份“相似度 → 是否正确”的局部经验。

**概率模型。** 对每个条目假设正确概率随相似度单调上升，用 sigmoid 拟合：

```text
Pr(c=1 | s) = L(s, t, γ) = 1 / (1 + exp(-γ(s - t)))
```

`t` 是条目专属决策边界，`γ` 控制陡峭度。参数用该条目的观测集做二元交叉熵最大似然估计，不需要额外训练。

**错误率约束。** 把“最终正确”拆成“探索（必然正确）”与“命中且命中正确”两个互斥事件，可解出满足 δ 所需的最小探索概率：

```text
Pr(explore | x) ≥ τ(s) = ((1-δ) - Pr(c=1)) / (1 - Pr(c=1))
```

缓存越可能答对，允许的探索越少；越没把握，越要回源推理。

**悲观置信带。** 有限样本下点估计不可靠。vCache 取参数 `(1-ε)` 置信带上的悲观值 `t'(ε)`、`γ'(ε)`，再对 ε 取最紧的探索概率上界 `τ̂`。这样样本不确定性被折算成更多的探索次数。

**随机化决策。** 采样 `u ~ Uniform(0,1)`；若 `u ≤ τ̂` 则探索并调用 LLM，否则命中并返回缓存回答。按置信带的构造可以推断：冷启动时观测少、置信带宽，探索概率会被推高，系统倾向多探索；观测累积后 `τ̂` 下降，命中率上升。论文没有单独给冷启动实验，这是对方法的推断。

**保证。** 在请求 i.i.d.、真实正确概率属于 sigmoid 族的假设下，作者证明对任意请求的边缘正确概率不低于 `1-δ`。这是概率保证，不是对单条请求的条件保证。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 保证是否兑现 | 3 个嵌入模型（GteLargeENv1-5、E5-large-v2、OpenAI text-embedding-3-small）× 2 个 LLM（Llama-3-8B-Instruct、GPT-4o-mini）；HNSW + 余弦相似度 | 各 δ 档位下实际错误率均低于设定上限；命中率随样本数持续上升 | 在线学习生效；保证是统计意义上的 |
| 与静态阈值比较 | 4 个 benchmark：SemCacheLMArena 60k、SemCacheClassification 45k、SemCacheSearchQueries 150k、SemCacheCombo 27.5k；基线 GPTCache、GPTCache + 微调嵌入、vCache、vCache + 微调嵌入 | 在 SemCacheLMArena 上最高 26× 更低错误率、12.5× 更高命中率，平均延迟更低 | 作者报告的是 Pareto 前沿上的最好点，不是所有配置 |
| 低错误率区间 | SemCacheClassification，δ 扫描 | δ > 1.5% 时 vCache 优于所有基线；δ < 1.5% 时更保守 | 作者明确把保守性归因于“优先正确性”的设计 |
| 静态基线的行为 | 同样本流下观察 GPTCache | GPTCache 错误率随样本数上升，且未完全收敛 | 作者据此认为静态阈值的结果可能还被高估 |

指标定义：错误率 `FP/n`，命中率 `(TP+FP)/n`；随机化策略用 Wallis 二项置信界给出 95% 置信区间。

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `resp`：完整历史回答，按嵌入近邻复用。条目元数据不是简单 TTL，而是“相似度—正确性”观测集 `O` |
| 价值建模 | 复用收益是省一次 LLM 推理；复用风险是错误命中。vCache 用“给定相似度时的正确概率”和 δ 把风险变成硬约束，阈值相当于每个条目的“准入价格”。它没有把存储、检索、验证成本写进目标 |
| 生命周期 | 写入：未命中且新回答与旧回答不同才入库；保留：无 TTL；驱逐：论文未给出；刷新：每次探索回写 `(s,c)` 并在线更新 `t,γ`；预取：无。冷启动天然保守 |
| Flink 映射 | 以缓存条目 id 为 key：`ValueState` 存 `t,γ,样本数`，`ListState` 或 `MapState` 存观测 `(s,c)`；timer 触发周期重拟合；checkpoint 保存观测与参数；向量索引作为外部可重建数据面，按 key 重新分配。这样“阈值学习状态”本身可恢复 |
| 可写缺口 | δ 只约束正确率，不约束容量与检索税。可写“在缓存条目数 ≤ S 的约束下，最大化受 δ 保护的期望收益”，把准入阈值与淘汰策略放进同一个优化问题；这是 vCache 明确没有回答的部分 |

## F 局限与边界

- 长回答的等价性依赖 LLM-as-a-judge，多一次模型调用；分类任务才用字符串匹配。作者称判定可异步执行、只输出一个 token，但成本并非为零。
- 定理依赖 i.i.d. 请求与 sigmoid 族两条假设；负载漂移或真实曲线偏离 sigmoid 时，保证不再成立。论文没有漂移检测或重校准机制。
- 只做单机、单轮、静态向量库；没有容量上限、TTL、淘汰、预取，也没有 checkpoint、扩缩容、背压等流处理语义。
- “保证”是边缘概率，不是对某条请求在某个上下文下的条件保证；观测只在探索时获得，存在探索偏置。
- 没有把命中路径的检索延迟、嵌入成本、GPU 预算纳入优化；因此不能直接回答“这条缓存值不值得占内存”。

## G 引用信息

```bibtex
@inproceedings{schroeder2026vcache,
  title     = {vCache: Verified Semantic Prompt Caching},
  author    = {Schroeder, Luis Gaspar and Desai, Aditya and Cuadron, Alejandro and Chu, Kyle and Liu, Shu and Zhao, Mark and Krusche, Stephan and Kemper, Alfons and Zaharia, Matei and Gonzalez, Joseph E.},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2026},
  note      = {arXiv:2502.03771v5}
}
```

来源页面：本地 PDF `paper_source/vCache.pdf`；arXiv 摘要页 `https://arxiv.org/abs/2502.03771`；代码 `https://github.com/vcache-project/vCache`；benchmark `https://huggingface.co/vCache`。

更详细的长报告见同目录的 `vCache调研报告.md`。

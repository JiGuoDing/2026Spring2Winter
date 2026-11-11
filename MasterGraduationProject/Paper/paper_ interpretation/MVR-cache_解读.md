---
template: doc
theme: auto
lang: zh
title: MVR-cache：把语义缓存相似度升级为学习式多向量
subtitle: ICML 2026 · resp · 学习式 Prompt 分段 + 对称 MaxSim
source: Ali Noshad, Zishan Zheng, Yinjun Wu, "MVR-cache: Optimizing Semantic Caching via Multi-Vector Retrieval and Learned Prompt Segmentation," ICML 2026, arXiv:2605.24914v1.
outline: right
mode: light
---

MVR-cache 不改 vCache 的错误率门控。它把输入相似度从“整句单向量余弦”换成“学习式分段 + 对称 MaxSim”。目标是在同一个错误率上界下，识别出更多真正可复用的回答。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | MVR-cache: Optimizing Semantic Caching via Multi-Vector Retrieval and Learned Prompt Segmentation |
| 作者 | Ali Noshad、Zishan Zheng、Yinjun Wu |
| 机构 | 北京大学计算机学院；中国人民大学信息学院 |
| 发表 | ICML 2026 Regular |
| 公开版本 | arXiv:2605.24914v1，2026-05-24 |
| 代码 | [PKU-SDS-lab/MVR-Cache](https://github.com/PKU-SDS-lab/MVR-Cache) |
| 缓存对象 | `resp`：历史 Prompt 与对应完整回答 |
| 核心方法 | 学习 Prompt 分段；每段独立嵌入；对称 MaxSim 检索；复用 vCache 的阈值与探索策略 |
| 数据与模型 | SemCacheSearchQueries、SemCacheClassification、PromptBench、QNLI；BGE + GPT-4o-mini |
| 版本边界 | 摘要写提升最高 37%；引言写 25%；结果部分说明 37% 属于 always-cache 协议 |

**一句话定位：** MVR-cache 升级的是 vCache 匹配器。它没有引入新的替换策略，也没有引入新的回答验证器。

## B 问题不在阈值，而在相似度

vCache 已经解决“相似度到正确性”的映射。它在线学习每个缓存回答的阈值和探索概率。

但 vCache 的输入仍是 **整句一个向量**。单向量容易把主题相似误判为回答等价。

```flow LR
(Positive review) -> (Single-vector cosine)
(Single-vector cosine) -> [Negative review]: topic similar
[Negative review] -> [Different response]: wrong neighbor
(Positive review) -> (Learned segmentation)
(Learned segmentation) -> [True equivalent]: high SMaxSim
```

论文给出的例子是同一部犯罪剧的两条评论：

- 两条评论都包含 crime、drama 等高权重词。
- 整句余弦相似度高，但情绪相反。
- 两者的 LLM 回答不同，因此不能复用。

MVR-cache 希望把“决定回答是否等价”的局部片段单独嵌入。这样，正向评论更可能匹配到另一条正向评论。

> 研究目标：保持用户给定的错误率上界 $\delta$，提高缓存命中率。

## C 推理流程

```flow LR
(New prompt) -> [Punctuation candidates]
[Punctuation candidates] -> (Policy Θ)
(Policy Θ) -> [Segment embeddings]
[Segment embeddings] -> [(HNSW Top-20)]
[(HNSW Top-20)] -> {SMaxSim rerank}
{SMaxSim rerank} -> (vCache gate)
(vCache gate) -> [Reuse response]: hit
(vCache gate) -> [LLM inference]: explore
```

推理分两步检索：

1. 用整句单向量 HNSW 粗召回 Top-20。
2. 用学习式多向量 SMaxSim 对候选重排。

粗召回不要求单向量 Top-1 正确。正确候选进入 Top-20 即可。

论文报告，Top-20 两阶段检索的最近邻召回接近全量多向量扫描，但避免了全库 MaxSim 扫描的高开销。

**在线计算路径：**

- 候选切分点仅取标点和终止位置。
- 分段模型选择边界。
- 每段用共享 BGE 编码器生成向量。
- 对称 SMaxSim 给出最终相似度。
- 相似度送入 vCache，计算探索概率 $\tau$。

## D 分段模型

```tree
Segmentation model Θ | 约 500-600 MB
  BERT encoder Θ1 | token states
  MLP Θ2 | pointer states
  LSTM Θ3 | prompt context
  Attention Θ4 | masked to valid split positions
  Recurrent selection | append selected state
  Stop token | end segmentation
```

模型是轻量 pointer network：

- BERT 编码完整 Prompt。
- 单层 MLP 生成每个 token 的 pointer state。
- 单层 LSTM 聚合为上下文状态。
- Attention 只在合法标点位置上分配概率。
- 选中一个边界后，屏蔽该位置及之前的位置。
- 重复选择，直到输出 stop token。

候选集与输出长度都可变。不同 Prompt 可切出不同数量的段。

| 数据集 | 最少段数 | 最多段数 | 平均段数 |
|:--|--:|--:|--:|
| SemCacheSearchQueries | 1 | 4 | 1.01 |
| SemCacheClassification | 1 | 93 | 2.64 |
| QNLI | 1 | 149 | 5.31 |
| PromptBench | 1 | 262 | 7.67 |

短搜索查询几乎不切分。长 Prompt 会被切成更多段。这说明策略在自适应粒度，而不是固定长度分块。

**为什么不用 token 级 ColBERT 分段？**

论文认为 token 级过细，可能损害检索。它选择更粗的语义段，并让分段策略直接服务缓存命中目标。

## E 训练目标与理论保证

### E.1 对称 MaxSim

普通 MaxSim 是单向的：

$$
\operatorname{MaxSim}(x,x_i)=\sum_t \max_s \operatorname{sim}(\mathcal{E}(x^{(t)}),\mathcal{E}(x_i^{(s)}))
$$

它保证新 Prompt 的每段都能在旧 Prompt 中找到相似段。它不保证反向覆盖。

MVR-cache 使用双向归一化平均：

$$
\operatorname{SMaxSim}_{\Theta}(x_i,x_j)=\frac{1}{2}\left[\frac{1}{|x_i|}\operatorname{MaxSim}(x_i,x_j)+\frac{1}{|x_j|}\operatorname{MaxSim}(x_j,x_i)\right]
$$

这使长 Prompt 与短 Prompt 的分数更可比，也避免“局部部分匹配”获得过高分数。

### E.2 训练目标

训练标签是两条 Prompt 的 LLM 回答是否相同。

目标是最小化 SMaxSim 与回答等价标签之间的 BCE：

$$
\min_{\Theta}\sum_i\sum_{nn_{\Theta}(x_j)=x_i}
\ell_{\mathrm{BCE}}
\left(\mathcal{L}(\operatorname{SMaxSim}_{\Theta}(x_i,x_j);t_i,\gamma_i),c_j\right)
$$

这里：

- $t_i$ 是缓存条目 $x_i$ 的相似度阈值。
- $\gamma_i$ 控制正确概率曲线陡峭度。
- $c_j$ 是回答等价标签。
- `nn` 是当前分段策略下的最近邻映射。

### E.3 为什么用 RL

分段输出是离散位置集合：

- 组合空间随 Prompt 长度指数增长。
- 分段边界不可直接反向传播。
- 缓存命中率本身不可微。

因此论文把训练写成 RL4CO：

```timeline v
1 | 采样 anchor Prompt | 选一个缓存条目及其当前邻居
2 | 采样分段动作 | 从策略 πΘ 生成边界集合
3 | 计算 SMaxSim | 得到相似度与 BCE
4 | 构造奖励 | 奖励等于负 BCE 和
5 | REINFORCE 更新 | 优化分段策略 Θ
6 | 更新 ti 与 γi | 冻结 Θ 后重拟合 vCache 参数
7 | 周期重建邻居 | 每 K 步刷新最近邻映射
```

邻居映射不是每步重建，而是每 $K$ 步刷新。这样避免全库重编码，但会引入一定陈旧性。

### E.4 保证依赖什么

理论结论并不只说“换多向量就更好”。它依赖以下条件：

| 条件 | 含义 | 边界 |
|:--|:--|:--|
| 相似度条件分布为高斯 | 正类和负类各有均值、共同方差 | 论文附录做经验验证，但不是普遍事实 |
| 类别先验均衡 | 正负样本各 50% | 主文假设；Lemma 用重加权 BCE 扩展到不均衡 |
| 模型设定正确 | 后验可写成 logistic/sigmoid | vCache 家族的共同前提 |
| 回答标签可靠 | 相同标签代表可安全复用 | 精确字符串匹配不等同语义等价 |
| 请求分布稳定 | vCache 的统计保证可迁移 | 未处理分布漂移和模型版本变化 |

因此应表述为：

> 在论文假设下，优化该训练目标可以提高同一 $\delta$ 下的缓存命中率，并保留 vCache 的统计正确性保证。

不能表述为：

> MVR-cache 对任意数据、任意模型都保证质量不降。

## F 实验证据

### F.1 实验设置

| 项 | 设置 |
|:--|:--|
| 基线 | vCache、ColBERT + vCache、POQD + vCache |
| 默认协议 | cache-on-miss；另有 always-cache |
| 嵌入 | BGE-base |
| LLM | GPT-4o-mini |
| 主实验错误率上界 | $\delta=0.01$ |
| 训练集 | 每数据集约 3K 条带标签 Prompt |
| 测试规模 | 29K–150K Prompt，按数据集不同 |

四种任务覆盖：

- 电商评论分类。
- Web 搜索查询。
- 问答扰动 Prompt。
- QNLI 自然语言推理式问答。

### F.2 命中率与错误率

主结果是：

- 在相同 $\delta$ 下，累计命中率高于 vCache。
- 实际错误率逐步上升，但最终仍低于用户给定上界。
- always-cache 的 SemCacheSearchQueries 中，命中率提升最高 37%。

需要保留协议条件：

| 协议 | 可报告结论 |
|:--|:--|
| cache-on-miss | 默认协议；命中改变后续缓存增长 |
| always-cache | 所有 Prompt 都入库；用于隔离匹配质量 |
| 37% 提升 | 只属于 always-cache 搜索结果 |
| 引言 25% | 未说明协议，不能与 37% 混用 |

### F.3 累计端到端时延

| 数据集 | MVR-cache / min | vCache / min | 端到端下降 |
|:--|--:|--:|--:|
| SemCacheClassification | 383.32 | 408.49 | 6.16% |
| SemCacheSearchQueries | 6345.61 | 6361.52 | 0.25% |
| PromptBench | 1866.58 | 1870.57 | 0.21% |
| QNLI | 1504.43 | 1536.00 | 2.06% |

MVR-cache 的收益来自少调用 LLM，而不是因为它让单次检索更快。

### F.4 在线非 LLM 开销

```chart bar horizontal unit=ms
| MVR-cache | vCache
SemCacheClassification | 55.35 | 25.20
SemCacheSearchQueries | 60.35 | 23.20
PromptBench | 54.35 | 25.30
QNLI | 55.35 | 20.30
```

MVR-cache 的非 LLM 开销约为 vCache 的 2–3 倍。单次 LLM 调用为 1.2–4.3 秒，因此它仍可被命中收益摊薄。

对高 QPS、多租户缓存服务，新增开销仍应进入价值模型，不能默认免费。

### F.5 训练标签与泛化

- 3K 训练样本已足够，继续增加数据收益很小。
- PromptBench 训练的模型迁移到 QNLI 后，仍优于基线。
- GPT-4o-mini 作为弱标签器，可避免 80.4% 的 GPT-4 标签调用。
- 弱标签与 GPT-4 标签在抽样上的 agreement 为 97.1%。

不要把这些结果外推为“跨领域无条件泛化”。论文只验证了一个 OOD 方向。

## G 与 vCache 的关系

| 维度 | vCache | MVR-cache |
|:--|:--|:--|
| 核心贡献 | 逐条目阈值与错误率保证 | 学习式多向量相似度 |
| 相似度 | 单向量余弦 | 对称分段 MaxSim |
| 阈值学习 | 在线 | 复用 vCache，并随分段联合校准 |
| 训练 | 无额外离线训练 | 每数据集离线训练分段模型 |
| 命中决策 | vCache | 完全复用 vCache |
| 错误保证 | 统计保证 | 继承并依赖额外分布假设 |
| 容量与淘汰 | 不处理 | 不处理 |
| TTL 与刷新 | 不处理 | 不处理 |
| 多租户与隔离 | 不处理 | 不处理 |
| 在线开销 | 约 20–25 ms | 约 54–60 ms |
| 显存 | 仅嵌入与索引 | 额外 500–600 MB 分段模型 |

**最重要的接口关系：**

```flow LR
(Prompt) -> (MVR segmenter)
(MVR segmenter) -> (SMaxSim score)
(SMaxSim score) -> (vCache policy)
(vCache policy) -> [Reuse]: hit
(vCache policy) -> [LLM]: explore
```

MVR-cache 是 plug-in scorer。它不拥有缓存生命周期。

## H 评价、边界与第一章用法

### H.1 主要优点

- **问题定位准确**：先修相似度，再谈阈值。
- **与 vCache 正交**：可直接替换分数，保留原有质量门控。
- **对称评分合理**：比单向 MaxSim 更适合回答等价判断。
- **在线模型轻量**：分段模型 500–600 MB，分段约 22–28 ms。
- **数据效率较好**：3K 标签已能训练可用策略。
- **结果口径清楚**：同错误率上界下比较命中率与端到端时延。

### H.2 关键风险

| 风险 | 影响 |
|:--|:--|
| 回答标签来自精确字符串匹配 | 语义相同但文本不同的回答会被标成负例 |
| 标签绑定具体 LLM | 换模型或模型版本后，回答等价关系会变化 |
| 每数据集单独训练 | 新业务冷启动需要标签和训练 |
| 分段模型额外显存 | 500–600 MB 对多租户服务并非零成本 |
| 分段与嵌入增加 CPU/GPU 开销 | 高 QPS 下管理税会放大 |
| 理论依赖正态、均衡等假设 | 不能视作任意分布的硬保证 |
| 无容量、淘汰、TTL、刷新 | 只解决“谁最像”，不解决“值不值得留” |
| 无多租户 ACL 与缓存安全 | 跨租户语义命中仍需额外隔离 |
| 多轮只做拼接式设想 | 未做真实多轮会话实验 |
| OOD 只测 PromptBench → QNLI | 不能证明广泛跨域泛化 |

### H.3 对第一章的用法

建议把 MVR-cache 放在 `resp` 层的“匹配器”位置，而不是“策略器”位置。

1. **作为 vCache 强基线**：固定同一 $\delta$，比较有效命中率。
2. **作为 `q_wrong` 的输入**：SMaxSim 是校准正确概率的分数，不是正确性本身。
3. **作为 key 设计参考**：缓存 key 可以是多粒度语义段，不必是整句单向量。
4. **作为管理税来源**：把分段、嵌入、重排、显存和标签成本计入净值。
5. **作为正交组件**：继续在你的生命周期策略外挂容量、TTL、刷新和淘汰。

```callout tip 第一章可写的研究切口
MVR-cache 已经把“相似度是否更准”做好。第一章不必重复训练分段器。更值得研究的是：同一错误率预算下，如何把匹配质量、管理税、容量和缓存净值联合优化。
```

### H.4 最终判断

MVR-cache 的主要贡献是 **相似度函数**，不是完整缓存系统。

它说明：

- 语义缓存的第一瓶颈可能不是阈值，而是表示粒度。
- 多向量匹配能在不改变错误率上界的情况下增加命中。
- 匹配提升会带来分段、嵌入、显存和标签成本。

对毕业设计第一章而言，最合适的定位是：

> 将 MVR-cache 作为 `resp` 层的高质量匹配基线和 `q_wrong` 校准输入；在其外层研究依赖感知的生命周期、负载价格和净收益控制。

**原始材料：** [arXiv:2605.24914](https://arxiv.org/abs/2605.24914) · [代码](https://github.com/PKU-SDS-lab/MVR-Cache) · [ICML 2026](https://icml.cc/virtual/2026/poster/63545)
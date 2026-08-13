# IntentKV 调研报告 —— Cross-Turn Intent-Aware KV Cache Pruning for Agent Inference

> 调研日期：2026-08-13
> 调研对象：**IntentKV: Cross-Turn Intent-Aware KV Cache Pruning for Agent Inference**，arXiv:2606.09916v1
> 调研方式：通读 arXiv v1 的摘要、HTML/PDF、TeX 源码及附录；仅使用论文作者提交的原始材料。
> 与本课题的关系：它是“多轮 Agent 会话 KV 生命周期管理”的直接相关工作，但**不是**语义库、RAG 或语义响应缓存论文。它最适合放入本课题的“引擎内 KV 数据面基线/相关工作”，不能替代“Flink 流处理层的语义记忆 × SLO × 推理资源联合优化”。

## 0. 先给结论

IntentKV 解决的是：多轮 Agent 会话中，早期的工具结果、搜索证据和推理痕迹会不断累积，常规“只看当前 prompt”的 KV pruning 会在后续轮次错误丢掉又变得重要的 token；而传统紧凑（compaction）又会改变 KV 的物理位置和 RoPE 相位，使 prefix/radix cache 不能复用。

它的解法有两半：

```text
跨轮 QueryMemory（决定“留谁”）
  + 零初始化的学习残差（补正启发式）
  + dead-slot slot-map 重定向（决定“怎么删而不破坏 prefix identity”）
  = 保留会话级 KV 复用、压缩每轮 decode 所读的 KV
```

论文在 BrowseComp-Plus（BCP）上报告：8k KV 预算下，Qwen3-8B / Qwen2.5-14B 的平均峰值请求 token 分别下降 23.9% / 30.7%；在 Qwen2.5-14B 上、所有方法都完成的 100 条最长 BCP 查询子集里，最坏原始 KV read 从 411M 降到 31M（92.6%），最坏峰值请求 token 从 92.3k 降到 20.5k（77.8%）。这些是**论文作者报告的实验结果**，尚非独立复现结果。【P1 摘要；§4.3，表 3】

对毕业设计的关键判断是：

1. 它证明了“跨轮意图/查询状态”确实能改善 KV 留存，比纯最近窗口或单轮 query 打分更贴近 Agent 负载；
2. 它的决策变量是一个**部署时固定的全局 KV budget `C`**，没有 SLO 机会约束、排队/批处理/并行度联合优化，也没有动态预算选择；
3. 它的 QueryMemory 是**会话内、token/KV 级的短期状态**，不做 embedding 检索、文档摄取、答案短路或跨用户语义复用，因此不能被称为“语义库优化”；
4. 本课题可以把它作为下层 KV 数据面的强基线，并把上层创新放在：`会话/语义价值预测 → SLO 感知的 (p,b,M_kv,S_sem,阈值) 联合规划 → Flink 可恢复状态与执行`。

---

## 1. 论文身份、版本与同名消歧

| 项 | 核验结果 |
|---|---|
| 标题 | *IntentKV: Cross-Turn Intent-Aware KV Cache Pruning for Agent Inference* |
| 作者 | Junjie Li、Jiong Lou、Jie Li（Shanghai Jiao Tong University） |
| 公开版本 | arXiv:2606.09916 **v1**，2026-06-06 15:54:48 UTC |
| 分类 | cs.LG（primary）、cs.AI |
| 发表状态 | 截至本次核验，arXiv 页面只显示 v1；TeX 源码头部写的是 “EMNLP 2026 submission”。这只能说明投稿意图，**不能表述为 EMNLP 已录用**。 |
| 原始论文 | [arXiv 摘要页](https://arxiv.org/abs/2606.09916) · [HTML](https://arxiv.org/html/2606.09916v1) · [PDF](https://arxiv.org/pdf/2606.09916) · [TeX source](https://arxiv.org/src/2606.09916) |
| 精确实现代码 | 本次核验中，arXiv 页面、论文正文和提交的 TeX 源码均未给出本论文的代码仓库链接，故**没有已验证的官方实现**可作为复现依据。 |

### 1.1 同名 GitHub 仓库不能混用

GitHub 上存在 [`linkezh/IntentKV`](https://github.com/linkezh/IntentKV)，但其 README 明确写的是另一篇论文 *Question Tells You Where the Answer Is: Intention-aware KV Cache for Long-Context LLM Inference*，作者为 Liang Zhao 等，且标注 ACL 2026；与本报告对象的标题、作者、问题设定均不同。因此，**不要把这个仓库当作 arXiv:2606.09916 的代码**。这是同名碰撞，而非本论文的已验证实现。【P2】

### 1.2 证据边界

- **P1（论文事实）**：上表所列 arXiv v1 的正文、附录、表格和 TeX 源码；本报告中“论文报告/作者称”均指 P1。
- **P2（同名消歧）**：该 GitHub 仓库自身 README，仅用来证明它是不同论文，不用其内容解释 P1。
- **本调研分析**：以“分析/建议/风险”明确标记，不把它写成作者实验结论。

---

## 2. 它究竟解决什么：不是“语义库”，而是跨轮 KV 留存

### 2.1 目标瓶颈

多轮 Agent 会把很短的用户问题扩展成工具调用、检索页面、工具结果和中间推理组成的长轨迹。每生成一个 token，注意力都会读取历史 KV；轨迹越长，KV 显存与 decode 侧 KV read bandwidth 越可能成为瓶颈。论文的核心观察是：第一轮里对当前 prompt 不重要的证据，在后续工具调用或新问题出现后可能重新重要，因此单轮、prompt-local 的 KV score 会“过时”。【P1 §1，图 1】

它针对的对象是每一层的 **K/V token 行**，而非文档、检索 chunk、历史答案或完整请求。即使 IntentKV 命中/保留成功，模型仍要执行推理；它节省的是 prefill/decode 注意力中的 KV 工作量，不是像语义缓存那样直接复用整条回答。

| 概念 | 复用单位 | 是否检索外部知识 | 是否可直接跳过 LLM | IntentKV 是否属于它 |
|---|---|---:|---:|---:|
| RAG / 语义库 | 文档、chunk、实体或事实 | 是 | 通常否 | 否 |
| 输出侧语义缓存 | 历史请求—响应 | 可选 | 是 | 否 |
| Prefix / Radix cache | 精确相同前缀的 KV | 否 | 只省 prefill | 相关、且要保持兼容 |
| **IntentKV** | **会话历史中的 K/V token** | **否** | **否** | **是** |

因此，论文名中的 `Intent` 指的是“跨轮当前问题/动作所表达的意图”，在技术上表现为 query 向量的会话级累计；它不是 embedding 语义空间中的意图分类，也不是长期语义知识库。

### 2.2 与常规 KV pruning 的两个差异

1. **从单 query 到多 query 留存。** StreamingLLM 的近期窗口、SnapKV 的 prompt 尾部 query attention、H2O 的 heavy hitter 等方法主要依赖单次 prompt 的信号。IntentKV 把每轮可行动的 query、工具/函数消息等编码进一个会话状态，再评分所有历史 token。【P1 §1、§2】
2. **从“紧凑搬迁”到“原位掩蔽”。** 传统 pruning 常把留下的 K/V copy 到连续位置；这会改变 slot identity / RoPE phase，从而与后续跨请求 prefix/radix reuse 冲突。IntentKV 保留幸存行的位置，只让被丢弃位置指向一个不可见的 sentinel slot。【P1 §3.4】

---

## 3. 方法拆解

### 3.1 问题形式化与保护集合

IntentKV 在一次请求 prefill 后、序列长度 `N` 超过预算 `C` 时触发。它总是保留系统前缀和最新的“可行动 query span”（最新 user、tool 或 function message），只在其他历史 token 中选 top-k：

```math
F = [0, π) ∪ [q_s, q_e)
C* = max(0, C - |F|)
H = [0, N) \ F
K* = F ∪ argtop_{K ⊆ H, |K| = C*} Σ_{j∈K} s_j
```

其中 `s_j` 是历史位置 `j` 的保留分数。`C` 是“可压缩历史”的 nominal budget，而非把 prompt + 输出硬截为 `C`；当前 query 与系统 prompt 被强制保留。【P1 §3.1，Eq. (1)】

### 3.2 QueryMemory：把跨轮问题累积成一个 query 状态

对每个 session，论文维护与一行 post-RoPE query 形状相同的 `M_t ∈ R^{L×H_q×D}`：

```math
M_t = exp(-λ) · M_{t-1} + Enc(q_t)
```

`Enc(q_t)` 是当前可行动 query span 的 post-RoPE Q 向量平均；每次更新后沿 head 维做单位归一化，防止轮数增长导致 softmax 坍缩。论文附录中固定 `λ = 0.5`，并以 LRU 最多保存 1,024 个 session memory。【P1 §3.2，Eq. (2)；附录 Experimental Details】

对每个候选历史 token `j`，先以 `M_t` 对该 token 的 K 向量进行每层/头 attention，再求和得到 rule score：

```math
a_{l,h,j} = softmax_{i∈H}( M_t[l,h] · K[l,h,j] / √D )
rule_j = Σ_{l,h} a_{l,h,j}
```

相较 SnapKV 用尾部 `W` 个 Q 行评分，作者称它把单事件评分复杂度从 `O(W·L·H_q·N)` 降到 `O(L·H_q·N)`，同时纳入早前轮次意图。【P1 §3.2，Eq. (3)】

### 3.3 可学习残差：保留启发式的安全起点

纯 rule scorer 是 Phase-1；可学习版在其上叠加一个残差：

```math
s_j = rule_j + α · MLP(φ_j ⊕ c_j)
```

- `φ_j` 拼接历史 K 的层/头均值、`M_t` 均值、两者逐元素乘积和 `rule_j`；
- `c_j` 是候选 token 特征对当前 query K-vectors 的多头 cross-attention 读出（4 heads、128 width）；
- 两层 GELU MLP 的输出层权重与 bias 均从 0 初始化，`α=1`。于是训练第 0 天 `s_j = rule_j`，但梯度仍能流动；对 `D=128`，该 head 有 214,274 个可训练参数。【P1 §3.3，Eq. (4)–(6)】

这一设计的含义是：学习器不是从随机分数开始取代规则，而是只学习“规则没覆盖的残差”。这降低了训练失败时的回归风险，但不构成正确性、SLO 或语义等价性保证。

### 3.4 训练标签：未来动作 grounding，而非人工语义标注

基础 LLM 冻结。训练时从部署模型抓取 post-RoPE Q/K；对每个 `(session, turn)`，扫描**未来 5 次工具调用**，若历史 token 的内容与未来 tool argument 出现字面子串匹配，则记为正例；当前 query / 特殊模板 token 不参与损失。损失由 BCE、hard-negative pairwise ranking、保留概率正则和 QueryMemory 范数正则组成。【P1 §3.5，Eq. (7)】

这个监督的优点是便宜且和未来动作直接相关；但它衡量的是可被字面匹配的未来工具参数，而不是“所有对最终答案语义上有用的上下文”。论文也明确说明没有匹配证据的行会被丢弃，而不是用 recency proxy 回填。【P1 §3.5】

### 3.5 dead-slot：删 token 而不搬 K/V 行

布局层是 IntentKV 对工程系统最关键的贡献之一：

```text
被驱逐位置 j
  不复制幸存 K/V，也不改 token id、序列长度、RoPE phase
  只执行：slot_map[j] ← sentinel_dead_slot

sentinel 的 K = -1e4 · 1，V = 0
  → softmax 权重数值上为 0，等价于硬 mask
```

幸存 K/V 仍留在原来的 physical slot，后续相同前缀仍可匹配 radix tree。释放真实 slot 时还需检查它是否属于 radix-protected prefix、是否是 sentinel、是否仍被保留位置或 sibling request alias；否则会损坏其他请求的 KV 读取。【P1 §3.4，Eq. (6)】

论文声称这一做法不需要修改 FlashInfer / FA3 attention kernel；但它**仍需要**接入 paged allocator、每请求 slot map、prefix/radix alias 管理。因而对“把 vLLM 当黑盒远端服务”的 Flink 方案来说，不能直接假定可无成本部署。

---

## 4. 实验设置与作者报告的结果

### 4.1 评测设置

| 维度 | 论文设置 |
|---|---|
| 模型 | Qwen3-8B-Instruct、Qwen2.5-14B-Instruct（均为 Neox-RoPE GQA） |
| 服务栈 | 单张 80 GiB A100；SGLang + radix prefix cache；确定性解码 `T=0`；每 query 最多 32 次 tool-use turn |
| 主 benchmark | BrowseComp-Plus（BCP）830 个 deep-research 查询，固定约 100k 文档语料；每 query 的 retriever 缓存固定，以避免检索漂移干扰 |
| 训练 | strict-cleaned ToolBench 多轮 trace；每 epoch reservoir sample 3k（Qwen3）/5k（Qwen2.5）例，2 epoch；4×80 GiB A100，约 40 / 55 分钟；仅训练 FP32 residual head |
| 预算 | `C ∈ {8192, 16384}`，每次 pruning event 应用于可压缩历史；触发大小 512 token、tail window `W=32` |
| 对照 | Full-cache、StreamingLLM、SnapKV、H2O、TrimKV |
| 质量指标 | `Compl`（正常完成率）、`Raw=Correct/Completed`、`True Acc=Correct/Total=Raw×Compl`；由 Qwen3-32B judge 判定 |
| 系统指标 | `PT`、Eff. Live KV、Raw KV Reads、Eff. KV Reads、wall-clock、radix prefix-hit rate |

【P1 §4.1；附录 Experimental Details】

有两个读表注意点：

1. 论文定义的 `PT` 是某条轨迹的**未压缩请求长度最大值**，称为 memory-footprint upper bound；实际参与 attention 的是 `Eff. Live KV`。不能把 `PT` 等同于真实 GPU KV 驻留量。
2. `True Acc` 把 OOM、overflow、turn cap、错误和空输出均计错。因此，压缩方法的“准确率变化”同时包含答案质量与能否跑完整条 Agent 轨迹的影响。【P1 §4.1】

### 4.2 主结果：严格 8k 预算下的质量

| 模型 / 预算 | Full-cache ceiling | 最强启发式 | IntentKV-learn | 应如何解读 |
|---|---:|---:|---:|---|
| Qwen3-8B / 8k | 15.06 True（Full 在 16k 列给出） | StreamingLLM 11.81 | **14.10**，Compl 84.58% | 比 Full 低 0.96 point；比 StreamingLLM 高 2.29 point |
| Qwen3-8B / 16k | 15.06 | StreamingLLM 14.46 | **14.94** | 距 Full 0.12 point |
| Qwen2.5-14B / 8k | 20.60 | StreamingLLM 8.19 | **18.55**，Compl 90.36% | 比 Full 低 2.05 point；比最强启发式高 10.36 point |
| Qwen2.5-14B / 16k | 20.60 | **StreamingLLM 16.14** | 14.58 | IntentKV 在这一列**不是最佳**；作者解释为平均约 17k 的轨迹在 16k 时较少真正触发 pruning |

【P1 §4.2，表 1】

所以更精确的表述应是：“IntentKV 在作者的**紧 KV budget**设定中保持了较高的 BCP True Accuracy 与 completion”，而不是泛化为“所有模型和预算下都优于现有方法”。

### 4.3 主结果：KV read、wall time 与 prefix reuse

论文报告的部分系统指标如下（数字为各自 cohort 均值，lower is better）：

| 配置 | IntentKV-learn | 有代表性的对照 | 论文的解释 |
|---|---:|---:|---|
| Qwen3-8B / 8k | Wall **140.4 s**；Raw KV reads **31.6M**；Eff. reads 39.8M | H2O 281.4 s / 77.2M；SnapKV 279.2 s / 77.1M | 更紧的 live KV，加上可保留 prefix reuse 的布局 |
| Qwen3-8B / 16k | Wall **139.2 s**；Raw reads **32.0M** | Full 131.4 s / 32.2M；H2O 244.7 s / 65.5M | 距 Full wall time 约 5.9%，但低于 H2O 43.1% |
| Qwen2.5-14B / 8k | Wall **104.0 s**；Raw reads **26.7M**；Eff. reads **21.0M** | StreamingLLM 275.3 s / 68.3M；H2O 373.1 s / 93.6M | 作者认为意图感知选出了更小的 live working set |
| Prefix-hit | 8k **20.7%**；16k **26.0%** | 紧凑 baseline 报告 0–3% | 归因于不改 slot / RoPE 的 dead-slot layout |

【P1 §4.3，表 2】

在“最原始 Full-cache `PT_max` 最大、且三种方法均完成”的 100 条 BCP 查询子集里，Qwen2.5-14B 的 Full-cache 为 `PT_max=92.3k`、`Raw KV Reads_max=411M`，IntentKV-8k 为 `20.5k`、`31M`，分别下降 77.8% 与 92.6%；对应 True Acc 为 20.60 与 18.55。【P1 §4.3，表 3】

这很好地展示了长尾 KV 压力的潜在收益，但该 cohort 按“所有方法均完成”筛选，不能直接代表全体 830 请求，特别不能替代线上 P95/P99、到达率、排队和 SLO 统计。

### 4.4 消融：QueryMemory 是主要信号，学习 head 是补正项

在 Qwen3-8B/BCP 中：

- 用当前 query `Enc(q_t)` 替代跨轮 `M_t`，True Acc 在 16k 从 14.94 降至 11.81（−3.13 point），8k 从 14.10 降至 12.77（−1.33）；
- 去掉 cross-attention，16k / 8k 分别下降 0.24 / 0.49 point；
- 关闭 residual 则回到 rule scorer：16k 比 full-learn 低 0.60 point，但在 8k **高** 0.60 point（14.70 vs. 14.10）。

【P1 §4.4；附录表 4】

这说明论文真正的核心是**跨轮 QueryMemory**，而不是“小网络必然更强”；残差的收益依赖于预算压力。对本课题而言，若只抽取一个可复用思想，应优先抽取“跨轮状态比单轮 prompt-local 特征更合适”，而非直接照搬训练 head。

---

## 5. 论文明确承认的边界与本调研的风险判断

### 5.1 作者明确写出的局限

1. `C` 为部署时固定、所有请求共用的全局 budget；无法按轨迹的早期信号动态选预算，短查询也可能承担无谓 eviction 开销，长尾查询又只能走同一条压缩曲线；
2. 残差 head 只在 strict-cleaned ToolBench、future-action substring 标签上训练，远离工具型 Agent 的负载预期收益会更小；单轮输入退化到 heuristic；
3. 只验证 Qwen3-8B / Qwen2.5-14B，未验证 ≥70B；其余采样的开源模型在 BCP harness 中未能可靠自主工具调用；
4. dead-slot 目前要求 fp16/bf16 KV pools。

【P1 Limitations】

### 5.2 本调研的补充判断（不是论文作者结论）

| 风险或空白 | 依据 | 对毕设的含义 |
|---|---|---|
| **缺少 SLO 问题定义** | 论文优化固定 `C` 下的 BCP quality/KV read/wall time；未给 arrival process、queue、P95/P99、违约概率、GPU cost 或重配决策 | 这正是本课题把 `C/M_kv` 与 `p,b`、TTL、语义记忆参数做机会约束联合优化的空间 |
| **不是流处理状态系统** | 附录虽描述 session key、LRU 1,024 和并发 key 隔离，但未讨论 checkpoint、exactly-once、backpressure、rescale 或 session state recovery | 不能把其 QueryMemory 等同于 Flink Operator/Keyed State；本课题可研究控制面状态持久化与恢复 |
| **弱监督并不等于语义相关性** | 标签仅靠未来五次工具参数的字面子串；无匹配行会删掉 | 对工具 argument 很有效的 signal 未必覆盖自然语言答案、RAG 证据或语义库条目；需要单独度量错误复用/陈旧复用 |
| **只覆盖单个 Agentic benchmark 主场景** | 主结果是 BCP；附录 FRAMES 做了函数调用改造、固定工具、加入 distractor、最少动作约束等 stress profile | FRAMES 结果是“BCP 风格的 FRAMES 改造”，不应当直接表述为原生 FRAMES 的泛化结果 |
| **系统对照的 substrate 文本有歧义** | 附录 Experimental Details 说主比较中 compact baseline eviction 后关闭 radix reuse，而 IntentKV 用 dead-slot；但 FRAMES 附录又说所有 compressor 共用 dead-slot，并称同样适用于 BCP main table | 这是 v1 内部可复核的叙述不一致；在没有代码/作者澄清前，不能精确分离“更好 scorer”与“更好 layout”的贡献 |
| **死槽并非纯上层改造** | 方法要接入 paged allocator、slot map、alias-aware deallocation | 如果 InferTuner 仍把 vLLM/SGLang 当远端黑盒，直接实现该层会越过既定工程边界；可作为后端增强或离线 baseline，而非首要必做项 |

关于最后但一项：论文也专门在 layout ablation 中称，将 SnapKV/H2O 放到 dead-slot substrate 后可节省 44–46% wall time、39–47% Raw KV Reads【P1 §4.3】。这更说明 scorer 与 layout 是两个独立轴，实验表格的 substrate 必须在复现实验中统一。

---

## 6. 与“面向 SLO 的流式 Agent 推理系统 + 语义记忆”的关系

### 6.1 清晰的层级对照

| 维度 | IntentKV | 当前毕业设计应坚持的定位 |
|---|---|---|
| 主要层级 | 推理引擎内部 / paged KV cache 数据面 | Flink 流处理编排与控制层 |
| 状态粒度 | 单 session 的 query summary + 每 token K/V 留存 | session state、语义记忆条目、负载分布、配置与控制状态 |
| 复用范围 | 同一会话内历史的精确 token/KV | 会话内 KV + 跨会话语义复用/知识检索（若纳入语义记忆） |
| 核心决策 | 固定 `C` 下选哪些 KV token 留下 | `p,b,M_kv,TTL,S_sem,阈值/质量预算、摄取策略` 的联合决策 |
| 质量目标 | BCP True Acc、完成率 | 端到端 JCT/TTFT 的 P95/P99 与 SLO 达成率；若短路复用还要有正确性/新鲜度约束 |
| 系统语义 | 维护 slot map 与 prefix alias | checkpoint、恢复、rescale、背压、异步外部推理、控制/数据面分离 |
| 语义库 | 没有 embedding/ANN/RAG/答案缓存 | 可作为上层状态化语义记忆，但需显式计入 Memory Tax |

一句话：**IntentKV 回答“同一 Agent 会话里，哪些 KV token 值得留”；本课题应回答“在动态流量与 SLO 下，整个 Flink 管线该给 KV 与语义记忆多少资源、何时留/删/恢复、并行度和批次如何协同”。**

### 6.2 三层状态的合理组合

若要把它融入当前题目，推荐明确区分而不是把它们混称“语义库”：

```text
L1  引擎数据面：KV cache / IntentKV-like pruning
    - 精确 token 前缀、速度最快、易失；决定哪些已算 KV 仍参与 attention

L2  Flink 控制面：会话档案、QueryMemory、驻留预算、路由与恢复元数据
    - keyed/operator state；可 checkpoint、rescale、故障后重建 L1

L3  语义记忆面：请求-响应或文档-证据的 embedding/index/version/freshness
    - 可跨会话复用或 RAG；有 embedding/ANN/judge/摄取的 Memory Tax
```

这样既能吸收 IntentKV 的“跨轮意图变化”洞见，又不会把 KV pruning 误包装成语义库。尤其是 L1 与 L3 的失败模式不同：L1 的错误是上下文压缩造成回答质量下降；L3 若短路复用，还会有语义误命中、权限和陈旧知识风险。

### 6.3 可借鉴的部分

1. **将 QueryMemory 作为会话行为预测的一类特征。** 当前 StateFetcher 的会话档案可记录近轮 query/tool 类型、上下文增长和 `M_t` 的低维摘要。它可帮助预测“下轮是否仍会访问早期前缀”或“KV 重算节省”，而非直接把论文 head 原样搬进 Flink。
2. **将 `C` 变为上层规划器的输出，而不是固定超参。** 对会话 `s`，可由流式控制器选 `C_s(t)` / `M_kv,s(t)`；若语义记忆也启用，则共同考虑 `S_sem`、embedding/ANN/judge 延迟和 `p,b`。这正对应论文 Limitations 留出的动态 budget 空白。
3. **控制面/数据面分离。** IntentKV 的 slot map 与 K/V 是后端数据面；Flink 持久化的应是 session id、预算、收益估计、QueryMemory/统计摘要和重建指令。故障后允许 L1 KV 重 prefill，而不应把巨型 KV 原样塞进 checkpoint。
4. **实验时把 scorer 与 layout 拆开。** 至少做 `current-query score`、`cross-turn QueryMemory score`、`learned residual（若可）` 三类 retention policy；并在相同 dead-slot/compaction substrate、相同 prefix-cache 开关下对比，避免把 layout 收益误判为“意图建模收益”。

### 6.4 不宜直接拿来当创新点的部分

- “维护跨轮 QueryMemory 做 KV pruning”已经是 IntentKV 的主张，不能作为本论文的新增算法核心；
- “dead slot 保持 prefix cache identity”也是其明确系统贡献，若直接复现只能作为后端基线/工程实现；
- 不应声称 IntentKV 验证了“语义库优化”，因为它没有 ANN、embedding、RAG、答案复用、文档版本或新鲜度机制；
- 不应将其 BCP wall-clock 结果直接外推为 Flink 端到端 P99 或 SLO 达成率。

---

## 7. 可形成的差异化研究问题

若毕业设计仍以“面向 SLO 的流式 Agent 推理系统”为主，IntentKV 最适合被吸收为以下问题的底层证据，而不是变成题目的全部：

```math
min  GPU_cost(p) + KV_cost(M_kv) + SemanticMemoryTax(S_sem, k, ingest)

s.t. P(JCT <= SLO_JCT) >= 1 - ε_1
     P(TTFT <= SLO_TTFT) >= 1 - ε_2
     P(semantic_error_or_staleness) <= δ
```

其中：

- IntentKV 提供 `KV_cost(M_kv)` 中“会话级留存价值会随跨轮 intent 变化”的依据；
- vCache / Cortex 等提供 L3 语义记忆的质量、检索与复用问题；
- Flink 控制器负责根据当前到达率、队列、会话轮间隔分布、`Memory Tax` 与 GPU profile，决定 `(p,b,M_kv,S_sem,τ,δ)`；
- L2 的 checkpoint/rescale 语义是引擎内 IntentKV 没覆盖的执行层创新。

一个相对稳妥的三点闭环可以是：

| 层 | 研究点 | 与 IntentKV 的关系 |
|---|---|---|
| 感知 | 会话/语义复用价值、KV 留存收益与 Memory Tax 的在线分布预测 | 用跨轮 query/tool 特征，吸收 QueryMemory 思路，但预测的是收益/风险分布 |
| 决策 | SLO 感知的 `p,b,M_kv,S_sem,τ` 联合配置 | 直接攻击其固定全局 `C` 的局限；不把 budget 当常数 |
| 执行 | Flink 状态化会话控制、语义记忆维护、可恢复路由 | 将 L1 易失 KV 与 L2 可恢复控制状态分离；可选接入后端 pruning |

---

## 8. 面向当前平台的实验建议

### 8.1 不建议一开始复现完整 IntentKV-learn

原因不是方法无价值，而是它要求：抓取 post-RoPE Q/K、训练 future-action residual、修改/接入 paged slot map、处理 radix sibling alias，同时论文的精确代码尚未验证公开。对 2–4 GPU、约 4 个月的毕业设计，这应是**可选后端增强**，不是第一里程碑。

更稳的递进路径：

1. 在现有会话 trace / 合成器上先实现或模拟三种 **留存策略**：无跨轮状态（current-query / recency）、QueryMemory-style rule、oracle；
2. 把每种策略产生的 `KV reuse / prefill saved / effective live KV` profile 输入现有配置规划器，扫描 `M_kv`、`p`、`b` 与负载；
3. 落地 Flink 的会话控制面状态、checkpoint 恢复和重建开销；
4. 在此基础上，再决定是否有后端权限/代码时接入 dead-slot 或 SGLang hook；
5. 语义记忆作为另一层实验，单独报告 embedding、ANN、judge、摄取、失效带来的 Memory Tax，不能和 L1 KV 指标混算。

### 8.2 建议的基线与指标

| 类别 | 应至少包含 |
|---|---|
| KV retention baseline | Full / 无 pruning、recency/StreamingLLM 型、current-query-only、QueryMemory-rule；若能实现，再加 learnable residual |
| Layout control | compact+无 prefix reuse 与 dead-slot+prefix reuse 分开报告；同一 scorer 在两种 substrate 均测，避免归因混淆 |
| 流处理控制 baseline | 固定 `(p,b,M_kv)`、只调 `(p,b)`、只调 `M_kv`、完整联合控制 |
| 语义记忆 baseline | 无语义记忆、精确缓存、静态语义阈值、质量校准语义准入（若做） |
| 端到端指标 | 会话 JCT / 跨轮 TTFT 的均值、P95、P99、SLO 达成率、GPU-hours、吞吐、队列长度与重配开销 |
| 状态语义 | checkpoint 后状态完整性、恢复首轮重 prefill、rescale 迁移量、控制面与 KV 数据面的重建时间 |
| 正确性 | Agent task 完成率与答案质量；如短路复用，还要单报 semantic error / staleness / 权限隔离错误率 |

---

## 9. 可直接写入综述的表述

> IntentKV 将多轮 Agent 的 KV 缓存压缩建模为跨轮 query retention：通过衰减累计的 QueryMemory 评估历史 token 对会话后续意图的价值，并以 slot-map 到 sentinel dead slot 的原位重定向保持 prefix/radix cache 的可复用性。该工作验证了跨轮上下文对 KV 留存决策的重要性，但采用部署时固定的全局 KV budget，未建模流量、队列、SLO、配置重规划或流处理状态容错；同时其优化对象为会话内 token-level KV，而非跨会话语义知识/响应复用。因此，本课题在 Flink 控制层联合优化会话 KV 驻留、语义记忆资源和推理配置，可与其引擎内机制形成上下层互补，而非重复。
> ——论文事实部分见 P1 §3–§5；“本课题”定位为本调研分析。

---

## 10. 主要来源

- **P1**：Junjie Li, Jiong Lou, Jie Li. [*IntentKV: Cross-Turn Intent-Aware KV Cache Pruning for Agent Inference*](https://arxiv.org/abs/2606.09916), arXiv:2606.09916v1, 2026-06-06. 技术主证据：§3 Method、§4 Experiments、Limitations、Appendix。
- **P2**：[linkezh/IntentKV README](https://raw.githubusercontent.com/linkezh/IntentKV/main/README.md)，仅用于同名仓库消歧；其标题和作者与 P1 不同，不是 P1 的实现来源。

> 调研声明：本报告未使用博客、新闻或二手解读。所有涉及 IntentKV 方法、设置、数值和局限的事实均回溯到 P1；未找到 P1 的经验证公开代码，故本报告不对可复现性作超出论文材料的承诺。

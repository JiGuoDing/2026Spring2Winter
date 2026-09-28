> 日期：2026-09-23（修订）
> 背景：导师反馈当前缓存内容单薄（"上下文/RAG知识/历史回答"三类），需深度探索 Agent 执行会话中还有哪些值得缓存的内容。
> 硬约束：①不能涉及工具调用（推理时延预测要求）；②缓存对象必须具体到表示与复用边界；③推理时延可预测性须说明省略/新增哪个阶段及可观测特征；④Flink 控制面定位（控制面状态持久容错 / 数据面缓存易失可重建，此为工程推荐而非用户硬约束）。
> 本版修订：纠正 prefill bound 性质、vLLM APC 机制、RAG 块复用条件、Flink checkpoint 语义边界、移除工具型规划缓存、摘要与 KV 非必然正反馈、删除绝对化断言。所有引用论文经独立核验，证据台账见第 2 节。

---

## 0. 本版主要修订点

| # | 修订前（v1 问题） | 修订后（v2） |
|---|---|---|
| 1 | 断言 prefill "memory-bandwidth bound / 近线性 / 最可预测" | prefill 在典型长度（>500 token）下为 compute-bound，attention 为 O(n²)；时延模型需实测标定，不能断言近线性 |
| 2 | 将 vLLM APC 与 SGLang radix 树混用 | vLLM APC 是基于链哈希（chain hash）的块级去重；SGLang 用 RadixAttention（radix 树）。两者机制不同 |
| 3 | RAG 文档块"按内容哈希精确复用" | 内容哈希 alone 不足以保证 KV 可复用——需相同前序上下文、位置编码、模型配置；否则需 CacheBlend 式选择性重算（5–18% token）。本课题只做严格前缀精确复用，RAG 块近似复用列为未来工作 |
| 4 | Flink checkpoint "重放意图让 vLLM 重算"暗示 exactly-once | Flink checkpoint 仅保证其管理的状态语义；外部 vLLM 的 KV 驻留、pin、TTL 不在 Flink 事务边界内。恢复时 vLLM 侧状态可能已丢失，需重算或从外部 KV 池取回，这是 at-least-once 语义的重建，不是 exactly-once 重放 |
| 5 | Keyed State / Operator State 混用 | 按 key（session_id）分区的状态用 Keyed State；算子级全局元数据用 Operator State。本文明确区分 |
| 6 | "不改 vLLM 内核"列为硬约束 | 这是工程推荐（降低实现复杂度），非用户明确约束。若近似复用等特性需要引擎改动，可标注为"需引擎配合"的可选方向 |
| 7 | 推荐 AgentReuse 式计划缓存（含 tool_name） | AgentReuse 为工具型 Agent（计划含 tool_name，执行用工具），违反约束①。移除直接推荐，仅保留"纯 LLM 固定 DAG"（文本提纲/事实提取/审校规则）作为条件性候选 |
| 8 | 摘要+KV "形成正反馈" | 摘要改写会改变 prompt 文本，可能破坏后续轮次的前缀 KV 命中（哈希不匹配），需重建 KV。重建成本与质量损失是核心权衡，非必然正反馈 |
| 9 | "跨会话摘要必然失败" | AgentMemBench 实测 CBS 在 LoCoMo 长程 Recall@5 低，但这是特定基准+特定配置的结果，不能泛化为"必然失败"。改为条件性判断 |
| 10 | 以缓存类别数量衡量贡献 | 改为统一生命周期框架 + 边际净收益/字节/算力预算 + 质量约束 + 可测试研究问题 |

---

## 1. 分析框架：Agent 执行管线分解

当前设计的三类缓存（上下文/RAG知识/历史回答）只覆盖了管线的输入侧和输出侧。将一次 Agent 轮次的执行管线展开（排除工具调用段）：

```
用户输入
  → [意图分类/路由]          ← 辅助推理（LLM 或轻量模型），输入输出极短
  → [任务规划/分解]          ← 辅助推理（LLM），仅纯LLM DAG 适用
  → [上下文组装]
      ├─ 系统提示词          ← 静态，跨会话共享
      ├─ 对话历史            ← 会话内累积，可能被压缩
      ├─ RAG 检索文档        ← 外部知识，位置敏感
      └─ Few-shot 示例       ← 同类任务共享
  → [Prefill: 计算 K/V]      ← compute-bound（典型长度），attention O(n²)
  → [Decode: 逐 token 生成]  ← memory-bandwidth bound
  → [输出解析/结构化]        ← 可能是 LLM 调用
```

方括号内的每个环节都可能产生可复用的中间产物。以下按研究价值排序分析。

---

## 2. 文献证据台账

所有论文经 general_search + web.fetch 独立核验（2026-09-23）。标**【实测】**= 原文报告的实验数据；**【推导】**= 基于论文结论的逻辑推导；**【假设】**= 待实验验证。

| 简称 | 准确题名 | arXiv / 出处 | 版本/日期 | 关键实测数字 | 核验状态 |
|---|---|---|---|---|---|
| Mooncake | Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | arXiv 2407.00079；USENIX FAST'25 Best Paper | v3, 2024-07 | 真实负载多处理 75% 请求；模拟长上下文场景最高 525% 吞吐（非真实负载） | ✅ 已核验 |
| vLLM×Mooncake | Serving Agentic Workloads at Scale with vLLM x Mooncake | vLLM blog, [https://vllm-project.github.io/2026/05/06/mooncake-store.html](https://vllm-project.github.io/2026/05/06/mooncake-store.html) | 2026-05-06 | 12×GB200，agentic trace：命中 1.7%→92.2%，吞吐 3.8×，P50 TTFT ↓46×，E2E ↓8.6× | ✅ 已核验 |
| 控制面综述 | From Inference Engine to Inference Control Plane: Connecting vLLM, llm-d, and the Evolution of Efficient Distributed LLM Serving | arXiv 2609.23130 | v1, 2026-09 | 定义 vLLM=执行引擎，llm-d/NVIDIA Dynamo=控制面；转述 llm-d 路由 P50 E2E ↓43%、TTFT ↓70% | ✅ 已核验 |
| PrefixPlace | PrefixPlace: Provable Prefix Key–Value Placement for Large Language Model Serving under Heterogeneous Compute and Transfer Costs | arXiv 2608.01655 | v1, 2026-08 | epoch 级放置规划器，RAG replay 上 materialization-cost 比 vLLM-APC 省 40.3%；432 实例达最优 99.84% | ✅ 已核验 |
| vLLM APC | Automatic Prefix Caching | vLLM 官方 stable 文档 [https://docs.vllm.ai/en/stable/design/prefix_caching/](https://docs.vllm.ai/en/stable/design/prefix_caching/) | stable（2026-09 核验） | 哈希组件 = parent hash + block tokens + extra hashes（LoRA ID、多模态输入哈希、cache_salt）；仅缓存完整块（full blocks）；引用计数 + 自由队列 LRU 淘汰；非 radix 树 | ✅ 已核验（一手官方文档） |
| CacheBlend | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | arXiv 2405.16444v3, [https://arxiv.org/html/2405.16444v3/](https://arxiv.org/html/2405.16444v3/) | v3, 2024-05 | 多文本拼接时非前缀位置 KV 融合需选择性重算（cross-attention 影响大的 token，5–18%）恢复 cross-attention | ✅ 已核验 |
| Mem0 | Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory | arXiv 2504.19413, [https://export.arxiv.org/pdf/2504.19413](https://export.arxiv.org/pdf/2504.19413) | 2025-04 | extract→consolidate→retrieve 流水线；多会话对话压缩为紧凑记忆；LOCOMO 基准 p95 时延降 91%；ADD-only 提取（新事实追加不覆盖），staleness 软重排 | ✅ 已核验 |
| Continuum | Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live | arXiv 2511.02230；Berkeley EECS-2026-234 | v2, 2025-11 | TTL 专为"生成工具调用的请求"设计，pin KV 等待工具返回；static-TTL 比 FCFS 降 mean JCT 26.7% | ✅ 已核验 |
| DPM | Stateless Decision Memory for Enterprise AI Agents | arXiv 2604.20158 | 2026-04 | 20× 压缩比下事实精度 0.907 vs 增量摘要 0.392（+0.515, p=0.0014）；tight budget 快 7.4×，moderate 快 14.9×（1 次 call vs 82–96 次） | ✅ 已核验（原文 Table 1/2） |
| CrystalMem | CrystalMem: Elastic Memory for Self-Evolving LLM Agents via Knowledge Crystallization | arXiv 2608.00303 | v1, 2026-08 | 四档 fidelity 降级 + verified recrystallization；7 环境 17 方法 6 backbone 最高恢复能力 | ✅ 已核验（recrystallization p50 586ms 为子代理报告，原文未直接确认，标**【待补】**） |
| AgentMemBench | AgentMemBench: A Systematic Benchmark for Evaluating Long-Term Memory Management Strategies in Conversational AI Agents | arXiv 2608.00009 | 2026-08 | CBS（压缩摘要）为基准策略之一；LoCoMo 长程 CBS Recall@5 0.005 vs dense retrieval 0.573（子代理报告，**【待补原文确认】**） | ⚠️ 部分待补 |
| StateMem | Can Agent Memory Systems Track Evolving State? | arXiv 2608.19652 | v1, 2026-08 | supersession 跟踪使 current-state accuracy 从 0.205→0.363（1.8×），DeepSeek-V4；234 多会话场景 | ✅ 已核验 |
| AgentReuse | A Plan Reuse Mechanism for LLM-Driven Agent | arXiv 2512.21309；计算机研究与发展 | v1, 2025-12 | 93% 有效计划复用率，F1=0.9718；**但计划含 tool_name，执行用工具**，属工具型 Agent，违反约束① | ✅ 已核验（因工具属性排除直接推荐） |
| ReasonCache | （推理 KV 复用） | arXiv 2507.21433 | 2024-07 | 跨生成相似推理步 KV 块复用，吞吐最高 +89.2% | ✅ 已核验（引擎内工作，非控制面增量） |
| SPORK | （推测工具调用） | arXiv 2607.03333 | 2026-07 | 分叉 probe 预测工具名 74.6–99.6% 准确率，提前派发工具执行——**属工具调用推测，排除** | ✅ 已核验（排除） |
| HotPrefix | （前缀热度追踪） | SIGMOD'26, ACM 3749168 | 2026 | 前缀树节点热度动态追踪 + 选择性准入 | ✅ 已核验 |
| Strata/Contextra | （分层 KV + cache-aware 调度） | OSDI'26, Stanford MAST | 2026 | 比 vLLM+LMCache TTFT ↓5× | ✅ 已核验 |

---

## 3. 候选缓存对象（按研究价值排序）

### 3.1 会话前缀 KV 计算状态的生命周期管理（首要候选）

#### 缓存对象定义

缓存的不是"对话历史文本"，而是对话历史在 **prefill 阶段计算出来的 K/V 张量块**。按复用范围和变化频率分层：

| 层 | 表示 | 粒度 | 复用范围 | 变化频率 |
|---|---|---|---|---|
| L0 系统提示词 | 系统提示 token 序列 → KV blocks（链哈希索引） | 0.5k–4k token | 全集群跨会话共享 | 几乎不变 |
| L1 Few-shot / 知识模板 | 同类任务示例 → KV blocks | 1k–8k token | 同类任务跨会话共享 | 低频 |
| L2 RAG 文档段 | (系统提示+文档) → KV blob | 单段 256–1k token | 严格前缀精确复用；近似复用需 CacheBlend | 中频 |
| L3 会话历史 | (L0+L1+L2+既往轮次) → KV blocks | 随轮增长，长会话 50k–200k token | 仅同一会话跨轮共享 | 每轮增长 |

**关键区分**：缓存文本只省输入 token 费用，prefill 仍需重算；缓存 K/V 张量直接跳过对应长度的 prefill 计算。vLLM×Mooncake 实测 agentic trace 上命中从 1.7%→92.2%，P50 TTFT 降低 46×**【实测，vLLM blog 2026-05-06】**——此收益来自 KV 复用而非文本复用。

**vLLM APC 机制澄清（一手官方文档）**：vLLM stable 文档（[https://docs.vllm.ai/en/stable/design/prefix_caching/](https://docs.vllm.ai/en/stable/design/prefix_caching/)）明确其哈希组件为三部分：① parent hash（前序块的哈希，形成链式结构）；② block tokens（本块的 token IDs）；③ extra hashes（LoRA ID、多模态输入哈希、cache_salt 等）。仅缓存完整块（full blocks，默认 16 token/块），不缓存部分块。淘汰策略为引用计数 + 自由队列 LRU。这与 SGLang 的 RadixAttention（radix 树）是不同实现——vLLM 是哈希表索引，SGLang 是前缀树。Flink 控制面管理的是"哪些前缀应驻留"的策略，不替代 vLLM 的块哈希匹配机制。

#### 复用边界与失效机制

- **L0/L1**：精确复用，要求 token 级完全一致（含模型版本、tokenizer revision、LoRA ID、cache_salt）。失效条件：prompt 模板改版、模型换版。用内容哈希+模型版本号管理。
- **L3**：会话内精确复用。第 k+1 轮 prompt = 第 k 轮完整 transcript + 新用户轮。失效条件：会话关闭/空闲超时。
- **L2（重要限制）**：RAG 文档的 KV 块**不能仅按文档内容哈希任意复用**。因为 KV 张量依赖于前序上下文（cross-attention 是位置敏感的）——同一段文档出现在不同前序上下文之后，其 KV 值不同。要在非前缀位置复用文档 KV，需 CacheBlend 式选择性重算（重算 5–18% token 修复 cross-attention 偏差）**【实测，CacheBlend arXiv 2405.16444】**，这需要引擎内核配合。**本课题只做严格前缀精确复用（文档出现在固定前缀位置），将非前缀 RAG KV 融合列为未来工作。**
- 失效检测：链哈希自动处理——任何前缀 token 变化导致后续所有块哈希变化，无需逐 token 比对。

#### 时延可预测性分析（修订）

- **命中后省略阶段**：prefill 中对应命中前缀长度的计算。
- **prefill 的 bound 性质**：在典型 prompt 长度（>500 token）下，prefill 是 **compute-bound**——大矩阵乘法和 attention 计算（O(n²)）使算术强度随序列长度增长，瓶颈在张量核而非 HBM 带宽【NVIDIA blog 2026-07；Microscale Academy；DEV.to 技术分析】。仅在极短 prompt（<500 token）下因固定开销可能呈现 memory-bound 表象。
- **时延与长度的关系**：attention 计算为 O(n²)，FFN 为 O(n)，因此 prefill 时延**不是严格线性**，而是随长度超线性增长（在 attention 占主导的长上下文下更明显）。NVIDIA 明确指出 "Prefill latency scales quadratically with input sequence length"【NVIDIA blog 2026-07-31】。实际曲线需在目标硬件+模型上实测标定。
- **可观测特征**：命中前缀的 token 数/块数、模型层数、KV head 数、batch 大小。这些可观测，但时延-长度关系需实测拟合，不能断言近线性。
- **缓存查找开销**：vLLM 块哈希查表为哈希表操作，理论 O(1) 平均但实际有常数开销和并发锁竞争；Flink 控制面元数据查找在 RocksDB 状态后端上为亚毫秒~毫秒级，**需实测确认，不能无测量断言可忽略**。
- **诚实边界**：llm-d 实测对 decode-bound 的推理负载，前缀路由收益接近零【arXiv 2609.23130 转述】。本维度收益在 prefill 占比高的长上下文/agentic 负载上成立，不能泛化到所有负载。

#### Flink 层可行性（修订）

- **控制面存什么**：
  - **Keyed State**（按 session_id 分区）：会话级前缀元数据 `{内容哈希根, token_length, num_blocks, 持有worker, 最近使用watermark, TTL截止时间}`。这是按 key 分区的状态，支持 exactly-once checkpoint。
  - **Operator State**（算子级）：全局前缀目录 `{prefix_hash → {length, ref_count, worker_list, tier}}`，用于跨会话前缀（L0/L1）的全局视图。
  - 均为 KB 级元数据，可 checkpoint 到状态后端。
- **数据面存什么**：vLLM-APC 管理的 FP16 K/V blocks，易失可重建。
- **是否需改 vLLM**：精确前缀复用**不需要改内核**（工程推荐，非硬约束）。Flink 通过路由把持该前缀的请求导向对应 worker 实现亲和性。若需近似 RAG KV 融合（CacheBlend 式）或逐块 pin 控制，则需引擎配合，列为可选方向。
- **checkpoint/恢复语义（关键修订）**：
  - Flink checkpoint 保证的是**Flink 管理的元数据**的 exactly-once 语义。
  - **外部 vLLM 的 KV 驻留状态不在 Flink 事务边界内**。故障恢复时，Flink 恢复元数据（"会话 S 应有前缀 P，长 L"），但 vLLM worker 上的 KV 块可能已因 worker 重启/驱逐而丢失。
  - 恢复路径：Flink 指示 vLLM 从 token transcript 重算 KV，或从外部 KV 池（Mooncake/LMCache）取回。这是**基于元数据的 at-least-once 重建**，不是 exactly-once 重放。
  - 需区分：**路由决策可控**（Flink 决定请求发往哪个 worker）vs **KV 驻留保证待验证**（vLLM 是否提供 pin/优先级 API 使 Flink 能强制保留特定前缀，需确认 vLLM 版本的 API 能力）。

#### 与现有三类缓存的区别

| 现有缓存 | 缓存什么 | 本候选 | 本质区别 |
|---|---|---|---|
| 上下文 | 对话历史**文本**（messages 数组） | 历史的 **K/V 计算结果**（张量块） | 文本省 token 费但 prefill 照跑；KV 直接跳过 prefill 计算 |
| RAG知识 | 检索文档**文本/embedding** | (系统提示+文档)的 **KV blob**，严格前缀位置 | 文本缓存不省 prefill；KV blob 省 prefill 但位置受限 |
| 历史回答 | 最终输出**文本**，命中跳过整段推理 | 前缀 KV，命中只跳过 prefill，仍生成新回答 | 粒度不同：答案 vs 张量；短路程度不同 |

#### 研究价值与可测试研究问题

**研究问题**：在多轮 agentic 负载上，由 Flink 控制面以可恢复元数据管理前缀生命周期（哪些前缀驻留、驻留多久、路由到哪），与 vLLM 全局 LRU + 离线放置（PrefixPlace）相比，能否在 cache-goodput、故障恢复时延、SLO 满足率上取得可测量的改善？

**可测试假设**：
- H1：对"长会话前缀 + 全局系统前缀"混合场景，分层差异化驻留（L0 钉住/L3 按会话 TTL/L2 严格前缀）的 goodput 优于 vLLM 全局 LRU。**【假设，需在 agentic trace 上实测】**
- H2：Flink 控制面元数据的 checkpoint 恢复时间 < 从 transcript 全量重算 KV 的时间，且恢复后 SLO 满足率下降可量化。**【假设，需实测】**
- H3：在线路由决策式 `T_transfer + T_queue(j) < min(T_queue(i), T_recompute)` 在会话增长场景下优于 PrefixPlace 离线 epoch 规划的重新规划间隔。**【假设，需对比实验】**

**必须避开的已有工作**：vLLM-APC（引擎内前缀缓存）、Continuum（工具等待 TTL，不适用于无工具场景）、IntentKV（引擎内跨轮剪枝）、PrefixPlace（离线放置）、llm-d（无状态 prefix-aware 路由）、Mooncake（分布式 KV 池）。本课题增量在**会话生命周期建模 + 控制面元数据恢复 + 在线流式路由决策**。

---

### 3.2 对话历史压缩状态：摘要块 + 结构化事实/约束（高优先级）

#### 缓存对象定义

当对话历史因超出上下文窗口被驱逐时，对驱逐段做 LLM 压缩，产出两类互补的中间表示：

**(a) 摘要文本块（summary segment）**
```
SummaryBlock {
  session_id, chunk_id, chunk_token_count,
  summary_text, summary_token_count,    // 受预算约束
  content_hash, model_version,
  fidelity_level,  // full / compressed / skeletal（借鉴 CrystalMem 四档，trace 档可选）
  created_at, supersession_refs  // 指向被替代的旧块
}
```

**(b) 结构化状态变量/约束（structured state variables）**
```
StateVariable {
  session_id, variable_name, current_value,
  value_history: [{value, valid_from_turn, superseded_by}],  // supersession 链
  confidence, source_turn_id,
  constraint_type  // fact / preference / constraint / goal
}
```

摘要块保留**叙事连贯性**（"之前聊了什么"），结构化变量保留**可查询的事实/约束**（"用户当前偏好是什么"）。两者互补而非替代。

#### 复用边界与失效机制

- **摘要块精确复用**：同一会话内，被驱逐 chunk 已生成过 summary；后续轮次拼接 prompt 时直接用缓存 summary。对话历史 append-only，chunk 内容不变，content_hash 可校验。
- **摘要块近似复用（有损）**：摘要保留语义但丢弃精确 token。文献明确三类信息丢失【Beyond Context Window, arXiv 2603.04814】：① temporal marker（日期/时序）；② implicit coreference；③ ephemeral update（更新未传播到摘要）。
- **结构化变量失效**：supersession 机制——新轮次提供新值时，旧值移入 value_history 并标记 stale。StateMem 证明显式 supersession 跟踪使 current-state accuracy 从 0.205→0.363（1.8×）**【实测，arXiv 2608.19652】**。
- **模型版本升级**：所有缓存块标记 model_version，升级后需重新压缩或标记为低置信度。

#### 与前缀 KV 的交互：核心张力（推荐研究问题，非既定创新）

**这不是已证明的创新点，而是一个需要实验回答的研究问题。** 摘要改写与前缀 KV 命中之间存在内在张力：

- 当对话历史被摘要替代后，prompt 文本发生变化（原始轮次 → 摘要文本），导致**后续轮次的前缀链哈希全部变化**，vLLM APC 中基于旧文本的 KV 块不再命中，需要重新 prefill 计算新前缀的 KV。
- 因此，压缩决策的真实成本 = 压缩 LLM 调用时延 + **因前缀变化导致的 KV 重建成本**（后续轮次的 prefill 增量）。
- 收益 = 缩短 prompt 长度减少的后续 prefill/decode 计算 + 省略的未来重压缩调用。
- 净收益为正的条件需要实测标定，不能假设"摘要缩短上下文→KV 更小→命中率上升"的正反馈。实际上，摘要改写可能**降低**短期 KV 命中率（因为前缀变了），只是在更长时间尺度上因上下文更短而减少 KV 总量。
- **冻结摘要块设计**：一旦某 chunk 被压缩为 summary 并注入 prompt，后续轮次的前缀就包含该 summary 文本。如果 summary 内容不变（冻结），则后续轮次仍可共享"系统提示+summary+近期轮次"的前缀。如果 summary 需要更新（recrystallization），则前缀再次变化。CrystalMem 的 verified recrystallization 机制处理了这一点【arXiv 2608.00303】，但 recrystallization 的触发条件和成本需实测。

#### 时延可预测性分析

- **命中后省略阶段**：一次 LLM 压缩调用（compression call）。
- **可观测特征**：输入长度=原始 chunk token 数（可观测），输出长度=摘要 token 数（由预算约束，是上限而非精确已知——max_tokens 是生成上限，实际输出长度可能更短，需用历史分布估计）。
- **压缩调用的时延**：标准 prefill+decode，落在现有"排队+推理"预测模型的**同一类分布**内，但不是"正好完全覆盖"——因为压缩调用的输入/输出长度分布与主推理调用不同，需要单独标定参数。
- **DPM 对比基线说明**：DPM 的对比基线是**增量滚动摘要**（每来一个事件就调一次 LLM 更新摘要，82–96 次 call），不是"每轮从头重算旧摘要"。DPM 快 7.4×（tight）/14.9×（moderate）是因为它只在决策时做 1 次 projection**【实测，DPM Table 2】**。本课题的摘要块缓存应对比的合理基线是**增量摘要**（业界标准做法），而非"不缓存、每次全量重算"——后者过于宽松。
- **缓存查找开销**：Flink Keyed State 按 session_id+chunk_id 查找，亚毫秒~毫秒级，需实测。

#### Flink 层可行性

- **Keyed State**（按 session_id）：ListState<SummaryBlock> + MapState<var_name, StateVariable>。维护压缩块生命周期（生成、fidelity 降级、失效标记、supersession 链）。
- 数据面无变化。vLLM 只看到拼接后的 prompt 文本，不知道 summary 是缓存的。
- checkpoint 后 SummaryBlock 和 StateVariable 随 Keyed State 持久化，故障恢复后不需重新压缩（但 vLLM 侧 KV 需重建，见 3.1 恢复语义）。
- 结构化变量天然适配 Flink 的 keyed state + process function 范式：每轮对话作为事件流，增量更新相关变量（类似 CDC → materialized view）。

#### 与现有三类缓存的区别

- **vs 上下文（KV prefix cache）**：本候选缓存的是 LLM 压缩产出的**文本块/结构化变量**，不是 KV tensor；生命周期独立于具体 prompt prefix；由 Flink 控制面管理。两者可叠加但有交互（见上文）。
- **vs RAG 知识**：来源是**本会话的对话历史**，不是外部文档；经过 LLM 语义压缩/提取，不是原文 embedding。
- **vs 历史回答（语义缓存）**：历史回答是请求级 question→answer 映射，命中后短路整个推理；本候选是**会话级中间表示**（chunk→summary / event→state variable），不短路推理（仍需基于压缩表示+当前 query 生成回答）。

#### 研究价值与可测试研究问题

**研究问题**：在 Flink 控制面，对话历史的压缩表示（摘要块+结构化变量）的生成时机、fidelity 等级、复用策略，如何在推理时延 SLO 约束下与前缀 KV 生命周期联合优化，使边际净收益（省略的压缩调用 + 缩短的推理时延 - KV 重建成本 - 质量损失）最大化？

**可测试假设**：
- H1：在长会话（>20 轮）场景下，摘要块缓存 + 增量摘要基线相比，端到端时延降低可测量，且回答质量下降在可接受阈值内。**【假设，需用 LongMemEval/LoCoMo 类基准实测】**
- H2：结构化变量（supersession 跟踪）在事实/约束型查询上的准确率优于纯摘要块，且额外存储开销 < 会话总 token 的 5%。**【假设，StateMem 提供部分证据但需在本系统架构下验证】**
- H3：压缩触发时机由时延预测驱动（预测排队时延超阈值时主动压缩）优于固定窗口触发（每 N 轮压缩一次）。**【假设，需对比实验】**

**文献证据**：
- DPM：20× 压缩比下事实精度 +0.515（vs 增量摘要），tight budget 快 7.4×**【实测，arXiv 2604.20158 Table 1/2】**
- Mem0：extract→consolidate→retrieve 流水线，LOCOMO 基准 p95 时延降 91%；ADD-only 提取保留历史，staleness 软重排而非硬删除**【实测，arXiv 2504.19413】**
- StateMem：supersession 跟踪 current-state accuracy 1.8×**【实测，arXiv 2608.19652】**
- CrystalMem：四档 fidelity + recrystallization，7 环境最高恢复能力**【实测，arXiv 2608.00303】**
- AgentMemBench：CBS 在 LoCoMo 长程 Recall@5 低（具体数字**【待补原文确认】**），说明纯摘要在超长程有局限——但这是特定基准结果，不能泛化为"跨会话摘要必然失败"

**与现有"上下文"缓存的包含关系（坦承）**：摘要块和结构化变量在内容上与现有"上下文"缓存有包含关系——它们都是对话历史的衍生表示，不是完全独立的新信息源。其价值不在于"发现了新的缓存类别"，而在于：①明确了表示形式（固定格式摘要 vs 自由文本、带 supersession 链的结构化变量 vs 原始 messages）；②量化了重复生成成本（每次压缩/提取都是一次 LLM 调用，DPM 实测 82–96 次 vs 1 次）；③将压缩/提取的触发时机从规则驱动变为时延预测驱动。因此不应生硬声称每个都是全新缓存类别，而应定位为"上下文表示的精细化管理"。

---

### 3.3 纯 LLM 固定 DAG 的中间产物缓存（条件性候选）

#### 适用条件

仅当 Agent 架构包含**显式的、纯 LLM 的多步推理 DAG**（不含工具调用）时适用。例如：
- 文本提纲生成 → 分段扩写 → 审校润色（写作 Agent）
- 事实提取 → 冲突检测 → 一致性校验（分析 Agent）
- 代码审查规则应用 → 问题分类 → 修复建议（代码审查 Agent，不含执行）

**不适用**：含工具调用的规划（如 AgentReuse 的订票/查天气计划，含 tool_name），违反约束①。

#### 缓存对象定义

```
PureLLMPlanTemplate {
  task_type, template_embedding,
  steps: [{step_type: "outline"|"extract"|"review",
           prompt_template_id,
           estimated_input_tokens, estimated_output_tokens_range}],
  complexity_tier, model_used
}
```

缓存的是**步骤结构 + 每步的 prompt 模板引用**，不是具体执行结果。命中时实例化模板（填充当前输入的参数槽位），跳过"规划结构生成"这一步 LLM 调用。

#### 复用边界

- **精确复用**：任务类型相同 + 去除具体内容后的语义相似度 > 阈值。直接复用步骤结构，仅替换输入内容。
- **部分复用**：前 N 步结构相同，后续步骤不同。可复用前 N 步的 prompt 模板和 KV 前缀。
- **失效条件**：任务类型定义变更、prompt 模板改版、模型升级。

#### 时延可预测性

- **命中后省略**：一次"规划结构生成"LLM 调用。
- **可观测特征**：规划调用的输入长度（任务描述）、输出长度范围（步骤数×每步描述长度，由 complexity_tier 分档估计）。
- **输出长度说明**：max_tokens 是生成上限，实际输出长度可变。需用历史分档数据估计期望输出长度和方差，不能当作已知常数。
- **缓存查找**：模板嵌入检索 + 参数槽位提取，开销需实测。

#### 为什么条件性

- 并非所有 Agent 架构都有显式规划阶段。ReAct 式 Agent 的"规划"是逐步生成的（每步推理后决定下一步），不存在一次性的计划结构可缓存。
- 纯 LLM DAG 的适用场景（写作、分析、审查）比工具型 Agent 窄。
- 文献中 AgentReuse（93% 复用率）的数字来自工具型 Agent（SMP 数据集，23 个含工具的意图类目），**不能直接迁移到纯 LLM 场景**。纯 LLM 规划缓存的复用率需独立测量**【假设】**。

#### 研究价值

如果目标系统定位包含纯 LLM 多步推理场景（如文档分析、内容生成），此候选可作为补充维度。核心研究问题：步骤结构缓存的命中率与任务多样性的关系，以及部分复用时 KV 前缀的增量复用。否则不建议作为主要贡献。

---

### 3.4 意图分类/路由决策（辅助层，不独立成章）

- 缓存对象：意图分类结果 `(intent_label, route_target, confidence)` + 分类模型版本。
- 节省：一次分类调用（BERT/SetFit 2–10ms，LLM 分类 50–100ms）。绝对节省量小。
- 时延可预测性：输入极短（10–50 tokens）、输出极短（1–3 tokens），时延方差小，但仍需实测标定，不能断言"近乎常数"。
- 价值：作为 3.3（纯 LLM DAG 缓存）的前置层——意图分类缩小模板检索空间。W5H2（arXiv 2602.18922）的五级级联架构提供了分类+缓存的工程参考，但其实测的 97.5% 成本降低基于假设流量分布【建模推算，非真实生产测量】。
- 不建议独立深化。

---

## 4. 不建议独立深化的方向

| 方向 | 排除/降级理由 |
|---|---|
| **跨会话摘要作为独立维度** | AgentMemBench 显示 CBS 在 LoCoMo 长程 Recall@5 低（**【待补原文确认】**），但这是特定基准结果。更适合作为 3.2 摘要块的终态产物（会话结束时的 digest），而非独立缓存维度。不能断言"必然失败"。 |
| **CoT 推理前缀 KV 复用** | ReasonCache（arXiv 2507.21433）已做跨生成相似推理步 KV 块复用（吞吐 +89.2%**【实测】**），属引擎内工作。且推理负载多为 decode-bound，前缀复用收益有限。建议并入 3.1 的 L1 知识层（worked-example 前缀放置），不单独立机制。 |
| **推测性预解码下一轮内容** | 开放对话中下一条用户输入未知，无法准确预解码。要么退化为引擎内 speculative decoding（需 draft 模型），要么变成工具调用推测（SPORK，属约束①排除区）。排除。 |
| **Few-shot 示例选择结果缓存** | 选择本身只需 embedding+向量检索（~5ms 量级），已较便宜。更大价值在 KV 缓存复用（AdapShot），属数据面优化。 |
| **Prompt 模板实例化缓存** | 确定性字符串操作，不需要 LLM 调用，不存在"省略推理阶段"。与 3.1 的 L0/L1 前缀重叠。 |
| **安全审核/内容过滤缓存** | 每个输入内容不同，复用价值低；审核模型通常轻量，即使不缓存开销也小。 |
| **KV 级压缩（LiveMem/KV Compaction/SeDeM）** | 需改 vLLM 内核或模型结构；部分工作（如 2608.00902）明确压缩 tool response 段，违反约束①。只能作对比基线。 |
| **工具型计划缓存（AgentReuse 式）** | 计划含 tool_name，执行依赖工具调用结果，违反约束①。AgentReuse 的 93% 复用率数字不能迁移。排除直接推荐。 |

---

## 5. 时延可预测性统一分析（修订版）

| 缓存对象 | 省略的阶段 | 该阶段时延的可观测特征 | bound 性质 | 与现有预测模型的关系 | 缓存查找开销 |
|---|---|---|---|---|---|
| **前缀 KV（3.1）** | prefill 中命中长度的计算 | 命中前缀 token 数、batch 大小、模型配置 | **compute-bound**（典型长度），attention O(n²)，非严格线性 | 需实测标定 prefill 时延-长度曲线；不是"正好覆盖" | 哈希表 O(1) 平均但有锁竞争，需实测 |
| **摘要块（3.2a）** | LLM 压缩调用 | 输入=chunk 长度，输出=摘要预算（上限非精确值） | 同主推理（prefill compute-bound + decode memory-bound） | 同分布族但参数不同，需单独标定 | Flink state 查找，需实测 |
| **结构化变量（3.2b）** | LLM 提取调用 | 输入=turn 长度，输出=facts 固定格式 | 同上 | 同上 | 同上 |
| **纯LLM DAG（3.3）** | 规划结构生成调用 | 输入=任务描述，输出=步骤数×描述（分档估计） | 同上 | 需扩展：命中=常数级查找，未命中=规划调用（二元分支） | 嵌入检索，需实测 |
| **意图分类（3.4）** | 分类调用 | 输入/输出极短，方差小 | 短输入可能 memory-bound 表象 | 方差最小但仍需标定 | 模板哈希查找 |

**核心结论**：
1. 没有任何缓存对象的时延是"正好完全落在现有模型内"的——都需要在目标硬件+模型上实测标定参数。
2. prefill 是 compute-bound 且 attention O(n²)，不能断言近线性或"最可预测"。
3. 缓存命中/未命中造成的二元分支（查找开销 vs 完整推理调用）是时延预测模型需要处理的结构性问题，不是"无需改预测器"。
4. max_tokens 是生成上限，实际输出长度需用历史分布估计，不能当作已知值。

---

## 6. 统一研究框架与推荐

### 6.1 不以缓存类别数量衡量贡献

v1 的核心问题之一是把"发现了 N 个新缓存类别"当作贡献。硕士系统论文的贡献应体现在：

1. **统一的生命周期管理框架**：将前缀 KV 元数据、摘要块、结构化变量纳入同一套 Flink keyed state 生命周期模型（创建→驻留→降级→失效→恢复），而非各自为政的缓存条目。
2. **边际净收益模型**：每个缓存决策（驻留/压缩/路由/淘汰）的收益 = 省略的计算时延 - 缓存管理开销 - 质量损失 - KV 重建成本。以**边际净收益/字节/算力预算**为决策依据，而非命中率。
3. **质量约束**：缓存复用不能以不可接受的回答质量下降为代价。需要可测量的质量门控（如摘要的事实精度、压缩的信息损失率）。
4. **时延模型的可测试扩展**：缓存引入的二元分支（命中/未命中）和前缀变化导致的 KV 重建，如何纳入时延预测模型并通过实验验证预测精度。

### 6.2 推荐的核心研究组合

**核心：跨轮语义状态（摘要块+结构化变量）与前缀计算状态（KV）的联合生命周期管理**

这不是两个独立缓存的简单叠加，而是一个有内在张力的研究问题：

- **语义状态侧**（3.2）：为了控制上下文长度，需要对对话历史做压缩/提取，产生摘要块和结构化变量。这改变了 prompt 文本。
- **计算状态侧**（3.1）：为了省略 prefill，需要复用前缀 KV。这要求 prompt 文本保持不变（链哈希精确匹配）。
- **张力**：压缩改写 prompt → 前缀哈希变化 → 已有 KV 失效 → 需重建 prefill。压缩的收益（缩短上下文、省略压缩调用）与 KV 重建的成本之间需要联合优化。

**推荐的核心研究问题**：在 Flink 控制面，如何联合管理语义状态的压缩时机/粒度与计算状态的前缀驻留/路由，使边际净收益（省略的 prefill + 省略的压缩调用 - KV 重建成本 - 质量损失）在时延 SLO 约束下最大化？

两者都有已核验的文献证据支撑（vLLM×Mooncake 46× TTFT；DPM +0.515 精度/7.4× 加速；Mem0 p95 ↓91%；StateMem 1.8×），且都适配 Flink keyed state 模型。

**条件性补充：纯 LLM DAG 中间产物缓存（3.3）**

仅当目标系统定位包含纯 LLM 多步推理场景时加入。否则不做。

### 6.3 可测试的核心研究问题（优先级排序）

1. **RQ1（最高）**：在多轮 agentic trace 上，Flink 控制面管理的前缀生命周期（分层驻留+在线路由+checkpoint 恢复）与 vLLM 全局 LRU + PrefixPlace 离线放置相比，goodput 和 SLO 满足率的差异是多少？恢复时延的量化是多少？
2. **RQ2（高）**：对话历史压缩（摘要块+结构化变量）与前缀 KV 生命周期联合优化时，压缩触发时机和 fidelity 等级如何影响端到端时延和回答质量？KV 重建成本占总收益的比例是多少？
3. **RQ3（中）**：缓存命中/未命中的二元分支如何影响时延预测精度？能否建立一个考虑缓存状态的时延预测模型，使 P95 预测误差 < X%？
4. **RQ4（条件性）**：纯 LLM DAG 场景下，步骤结构缓存的命中率与任务多样性的关系？部分复用时 KV 前缀增量复用的收益？

### 6.4 对 prototype.md 缓存部分的具体修改建议（不改原文，仅建议）

将笼统的"Agent 上下文"细化为两个独立维度：

| 维度 | 缓存对象 | 省略的阶段 | 层次 |
|---|---|---|---|
| 前缀 KV 计算状态 | 系统提示/历史/严格前缀RAG的 K/V 张量块 | prefill 中命中长度 | 控制面元数据 + 数据面张量 |
| 上下文压缩状态 | 对话历史 chunk 的摘要文本块 + 结构化事实/约束变量 | LLM 压缩/提取调用 | 控制面 |

原有的"RAG 知识/语义库"和"历史回答（语义缓存短路）"保留。RAG 知识缓存需注明：严格前缀位置的 KV 复用归前缀 KV 维度；非前缀位置的 RAG KV 融合需 CacheBlend 式引擎配合，列为未来工作。

---

## 7. 剩余缺口与待验证项

| # | 缺口 | 说明 | 建议 |
|---|---|---|---|
| 1 | AgentMemBench CBS Recall@5 具体数字 | 子代理报告 0.005，但未从原文确认 | 需 fetch arXiv 2608.00009 原文 Table 确认 |
| 2 | CrystalMem recrystallization p50 586ms | 子代理报告，未从原文直接确认 | 需 fetch 原文确认 |
| 3 | vLLM pin/优先级驻留 API | Flink 能否强制 vLLM 保留特定前缀，取决于 vLLM 版本的 API 能力 | 需查 vLLM 文档确认是否有 `--enable-prefix-caching` 之外的 pin 控制 |
| 4 | prefill 时延-长度曲线 | 需在目标硬件（如 A100/L20）+ 目标模型（如 Qwen2.5-7B/14B）上实测 | 实验阶段标定 |
| 5 | 纯 LLM DAG 缓存复用率 | AgentReuse 数字来自工具型 Agent，纯 LLM 场景无数据 | 需在目标工作负载上预实验测量 |
| 6 | Flink state 查找实际开销 | 不能断言 O(1) 可忽略 | 需在 RocksDB 状态后端实测 |
| 7 | 摘要压缩导致的 KV 重建成本量化 | 理论分析存在，但无实测数字 | 需实验测量：压缩后首轮 prefill 增量 vs 未压缩 |
| 8 | llm-d 路由的具体实现细节 | arXiv 2609.23130 是综述，llm-d 原始论文（Mitra et al. 2026）需定位 | 需检索原始论文 |

---

## 附录：引用 URL 映射

| 引用 | URL |
|---|---|
| Mooncake (arXiv) | [https://arxiv.org/abs/2407.00079](https://arxiv.org/abs/2407.00079) |
| Mooncake (FAST'25) | [https://www.usenix.org/conference/fast25/presentation/qin](https://www.usenix.org/conference/fast25/presentation/qin) |
| vLLM×Mooncake blog | [https://vllm-project.github.io/2026/05/06/mooncake-store.html](https://vllm-project.github.io/2026/05/06/mooncake-store.html) |
| 控制面综述 | [https://arxiv.org/abs/2609.23130](https://arxiv.org/abs/2609.23130) |
| PrefixPlace | [https://arxiv.org/abs/2608.01655](https://arxiv.org/abs/2608.01655) |
| vLLM APC 文档（stable） | [https://docs.vllm.ai/en/stable/design/prefix_caching/](https://docs.vllm.ai/en/stable/design/prefix_caching/) |
| CacheBlend v3 | [https://arxiv.org/html/2405.16444v3/](https://arxiv.org/html/2405.16444v3/) |
| Mem0 | [https://arxiv.org/abs/2504.19413](https://arxiv.org/abs/2504.19413) |
| Continuum | [https://arxiv.org/abs/2511.02230](https://arxiv.org/abs/2511.02230) |
| DPM | [https://arxiv.org/abs/2604.20158](https://arxiv.org/abs/2604.20158) |
| CrystalMem | [https://arxiv.org/abs/2608.00303](https://arxiv.org/abs/2608.00303) |
| AgentMemBench | [https://arxiv.org/abs/2608.00009](https://arxiv.org/abs/2608.00009) |
| StateMem | [https://arxiv.org/abs/2608.19652](https://arxiv.org/abs/2608.19652) |
| AgentReuse | [https://arxiv.org/abs/2512.21309](https://arxiv.org/abs/2512.21309) |
| ReasonCache | [https://arxiv.org/abs/2507.21433](https://arxiv.org/abs/2507.21433) |
| SPORK | [https://arxiv.org/abs/2607.03333](https://arxiv.org/abs/2607.03333) |
| NVIDIA prefill 分析 | [https://developer.nvidia.com/blog/co-designing-ai-model-attention-for-fast-interactive-long-context-inference/](https://developer.nvidia.com/blog/co-designing-ai-model-attention-for-fast-interactive-long-context-inference/) |
| W5H2 | [https://arxiv.org/abs/2602.18922](https://arxiv.org/abs/2602.18922) |
| Beyond Context Window | [https://arxiv.org/abs/2603.04814](https://arxiv.org/abs/2603.04814) |

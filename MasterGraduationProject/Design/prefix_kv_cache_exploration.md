# 多轮 Agent 推理资源管理：前缀 KV 与推理中间状态缓存探索

> 目的：回应导师"缓存内容单薄（只有上下文/RAG 知识/历史回答三类）"的反馈。聚焦 **LLM 推理过程中产生、可跨轮/跨会话复用的中间计算状态**。
> 硬约束：①不涉及工具调用结果；②缓存对象必须具体到 representation + reuse boundary；③推理时延可预测（说明省略了哪个阶段、可观测特征）；④Flink 控制面可管 vs 需改引擎内核要分清（控制面状态持久容错 / 数据面缓存易失可重建）。
> 核验基准：以下论文均经 general_search/web.fetch 独立核验（2026-09-23），未编造论文或数字；标【假设】者为待验证。

---

## 0. 文献核验总表（先立证据地基）

| 论文 | arXiv / 出处 | 核验结论 | 关键实测数字 | 与本课题关系 |
|---|---|---|---|---|
| Mooncake | arXiv 2407.00079；FAST'25 Best Paper | 真实，KV 中心拆解式架构 | 全局缓存命中率比本地高 2.36×；真实负载多处理 75% 请求；最高 525% 吞吐 | 全局 KV 池 + Conductor 调度——控制面最强基线 |
| vLLM × Mooncake | vLLM blog 2026-05-06；arXiv 2609.23130 转述 | 真实，agentic trace | **缓存命中 1.7%→92.2%；吞吐 3.8×；P50 TTFT ↓46×；E2E ↓8.6×**（12×GB200）；blog 称 94.2% | 证明"会话状态复用主导 agentic 成本" |
| Control Plane Synthesis | arXiv 2609.23130 | 真实，系统综述+研究议程 | 定义 vLLM=执行引擎，llm-d/NVIDIA Dynamo=控制面 | **本课题 framing 的直接出处** |
| llm-d 路由 | 同上转述 Mitra et al. 2026 | 真实 | prefix/token-aware 路由：code 负载 46k vs 16k tok/s(2.9×)；预测时延路由 P50 E2E ↓43%、TTFT ↓70% | 控制面路由已存在——必须区分 |
| llm-d GLM-5.2 研究 | 同上转述 Ayoub et al. 2026 | 真实 | 219 个 Claude Code 会话，主 agent 请求中位 **195k 输入 token / 317 输出**；**96% 主轮复用≥90% 输入**；缓存后首轮 TTFT 快 2.8× | 会话级前缀复用的现实证据 |
| PrefixPlace | arXiv 2608.01655 | 真实，epoch 级前缀放置规划器 | 432 实例达最优 99.84%；RAG replay materialization-cost 比 vLLM-APC **省 40.3%**；5万节点/16 worker 12.3s | **"放哪个 worker"已离线可证明解决——增量不能重 claim** |
| PEEK | arXiv 2607.02525 | 真实，队列感知 KV 调度 | pending queue 上增量 radix 树，最长前缀匹配，"集群先锋先入队" | 队列-前缀联合调度已做（引擎内调度层） |
| HotPrefix | SIGMOD'26（ACM 3749168） | 真实 | 前缀树节点热度动态追踪 + 选择性准入 | 热度/驻留策略已做 |
| Continuum | arXiv 2511.02230；Berkeley EECS-2026-234 | 真实 | AGENTSERVESIM(2606.09613) 转述：static-TTL 比 FCFS 降 mean JCT 26.7%、命中率 +8.5pp | **TTL 是为"等待工具结果"设计的**——约束①要排除 |
| IntentKV | Semantic Scholar，2026-06 | 真实 | 跨轮意图感知 KV 剪枝，紧凑预算下几乎无损 | 引擎内跨轮剪枝，已做 |
| Strata / Contextra | OSDI'26；Stanford MAST | 真实（同一工作两名） | 比 vLLM+LMCache **TTFT ↓5×**；GPU 辅助 I/O + cache-aware 调度 | 分层(GPU→DRAM→SSD) KV + Cache Controller |
| PTStore | arXiv 2607.22648（JHU/Argonne） | 真实，CDN 式分布式前缀复制 | 节点聚合 host 内存+本地 SSD，服务本地远端 GPU | 分布式前缀复制 |
| Irminsul | arXiv 2605.05696 | 真实 | SGLang radix + CDC 段内容哈希 + δ-rotation（MLA 模型） | 段级内容寻址表示（引擎内、模型相关） |
| HYPIC | arXiv 2607.01299 | 真实 | 混合注意力模型的位置无关缓存，段累计转移算子 | 线性注意力层的缓存表示（引擎内、模型相关） |
| SparseX | arXiv 2606.01751（含字节作者） | 真实 | 段级复用 + Sparse-KV 单次前向校正 | 非严格前缀的近似复用需引擎校正 |
| SwiftCache | arXiv 2606.16135 | 真实 | 跨模型 NVLink 共享空闲显存；**TTFT ↓69%**，上下文 ~4× | 同机跨模型共享（非跨会话） |
| RKSC | arXiv 2606.09937（ICML'26） | 真实 | 单请求多分支隐藏状态余弦相似共享，3.008× 加速 | **请求内**分支共享，非跨会话 |
| ReasonCache | arXiv 2507.21433 | 真实 | 推理模型相似推理步 KV 块复用，**吞吐最高 +89.2%** | 跨生成的推理 KV 复用——候选2已被引擎做掉 |
| SPORK | arXiv 2607.03333（清华） | 真实 | 分叉 probe 预测**工具名** 74.6–99.6% 准确率，提前派发工具；GAIA P95 ↓18% | **纠偏：这是工具调用推测，属约束①排除区，不是推理 KV 缓存** |
| Speculative Pre-Positioning | arXiv 2606.29565 | 真实 | 目标模型自身前向把会话"解码到下一决策点"，下轮只付 delta；置信门触发则单次词表扫描零 decode | 候选3核心（具体收益数字【待补】） |
| DualDecoder | arXiv 2607.26475 | 真实 | 输出/推测 token 共 batch，0.035 vs 0.069ms(-49%) | decode 步融合，非跨轮预解码 |
| vLLM-APC / RadixAttention | PrefixPlace 文中作为 baseline | 真实，引擎自带 | 严格 token 前缀 LRU | 已存在，勿当新发现 |

**纠偏提示（防止误引）**：导师/agent-hint 把 SPORK 归为"推理 forking"，实际它是**推测工具调用名并提前执行**——与工具调用强耦合，正是本课题约束①要排除的对象，不能写进"推理中间状态缓存"的贡献里。

---

## 候选 1：分层前缀 KV 缓存管理（核心候选，建议深化）

### 1. 缓存对象定义
把一次推理 prompt 的前缀按"复用范围/变化频率"拆成四层，分别以 **KV 张量块（block）** 为表示单位：

| 层 | 表示 | 粒度/大小量级 | 管线位置 | 复用范围 |
|---|---|---|---|---|
| L0 系统提示词 | 系统提示词 token 序列 → KV blocks（FP16，每 token ≈ 2×num_layers×num_kv_heads×head_dim 字节） | 通常 0.5k–4k token；KV 约 几十–几百 MB（7B~70B 量级） | prefill 起点，最先算 | 全集群跨会话共享，几乎不变 |
| L1 Few-shot 模板 | 同类任务的示例 token 序列 → KV blocks | 1k–8k token | 系统提示词之后 | 同类任务跨会话共享 |
| L2 RAG 文档段 | (系统提示词 + 检索文档) → KV blocks，**key 用文档内容哈希** | 单段 256–1k token；多段拼接可达 4k–16k | 用户 query 之前 | 相似查询近似共享 |
| L3 会话历史 | (L0+L1+L2 + 既往 user/assistant 轮次) → KV blocks | 随轮次单调增长，长会话可达 50k–200k token（llm-d 实测中位 195k） | 随轮次累积 | **仅同一会话跨轮共享** |

**关键区分**：缓存的不是"上下文文本（messages 数组）"，而是这些文本在 prefill 阶段算出来的 **K/V 张量**。缓存文本只省输入 token 费用，prefill 仍要重算；缓存 KV 直接跳过对应长度的 prefill 计算。

### 2. 复用边界
- **L0/L1：精确复用**。要求 token 级完全一致（含模型版本、tokenizer revision）。命中即整段复用。失效条件：prompt 模板改版、模型换版。
- **L3：会话内精确复用**。第 k+1 轮 prompt = 第 k 轮完整 transcript + 新用户轮。前缀 = 整段历史。跨会话不复用。
- **L2：近似复用是难点**。两条相似 query 检索到相似但不完全相同的文档 → 严格前缀**不命中**。要跨会话复用 RAG 的 KV，需要：(a) 按文档内容哈希把"系统提示+该文档"的 KV 作为独立 blob 缓存，新 query 命中同哈希文档即路由到持有该 blob 的 worker；(b) 文档部分重叠的"近似复用"需要 SparseX/Irminsul 式段级校正——那是引擎内核工作，本课题**只做 (a) 的精确 blob 复用，把 (b) 列为未来工作**。
- 失效/有效条件：哈希一致且模型/精度/位置编码/并行布局兼容（PrefixPlace 明确列了这四个兼容性过滤条件）才有效。

### 3. 失效机制
- L0/L1：内容哈希（tokenized 序列哈希）+ 模型版本号。版本化管理，旧版本随 TTL 淘汰。
- L3：按 (session_id, turn) 版本化；会话关闭/空闲超时（TTL）失效。Flink 可用 keyed state TTL + 会话窗口。
- L2：文档 chunk 内容哈希；索引重建/embedding 版本升级时失效。
- 不需要逐 token 内容比对——用前缀哈希树（vLLM-APC 的 radix 树已提供）即可定位最长匹配前缀。

### 4. 时延可预测性分析
- **命中后省略阶段**：**prefill**。命中长度 L 的前缀，即跳过 L 个 token 的 prefill 计算（attention 与 K/V 写出）。
- **该阶段时延由什么决定**：prefill 在长上下文下是 memory-bandwidth bound，经验上 TTFT 与输入 token 数近似线性（Orca/DistServe 结论；PrefixPlace 把每 chunk 的重算代价建模为 w_m(b) 直接查表，不假设线性但实测近线性）。**可观测特征 = 命中前缀长度（token 数 / block 数）**。增量 prefill 只处理 delta 长度，时延与 delta 线性。这是全管线**可预测性最强**的阶段。
- **部分命中**：前缀长到 L 就停，只重算 L 之后的 delta——增量可预测。
- **缓存查找/管理开销**：radix 树最长前缀匹配是 O(prefix_len)，微秒级；元数据查表在 Flink keyed state 上是 O(1)。相对 prefill 的毫秒~百毫秒级开销可忽略。
- **诚实边界**：llm-d 实测发现对 **decode-bound 的推理负载**，路由几乎无收益（因为瓶颈在 decode 吞吐而非 prefill）。所以本维度的收益在 **prefill-bound 的长上下文/agentic 负载**上成立，不能泛化到 decode-bound 推理负载。

### 5. Flink 层可行性
- **Flink 控制面存什么（元数据，KB 级，可 checkpoint）**：按 prefix_key 作 keyed state → `{内容哈希, token_length, num_blocks, 字节数, 持有 worker, 所在层级(HBM/DRAM/SSD), 最近使用 watermark, 预估复用次数, TTL 截止时间}`。这是**小元数据**，可 exactly-once 持久化到状态后端（RocksDB/S3）。
- **数据面 vLLM 存什么（实际 KV 张量，易失可重建）**：FP16 K/V blocks。vLLM-APC / SGLang RadixAttention 已提供 radix 前缀缓存。
- **是否需改 vLLM 内核**：**精确前缀复用不需要**。Flink 只做"驻留哪些前缀 + 亲和路由"的策略，并通过路由（把持该前缀的请求路由到对应 worker）+ pin/配置 实现驻留。**近似 RAG 复用需要引擎改动**（SparseX/Irminsul），本课题显式排除。
- **亲和路由如何配合**：Flink 按 prefix_key 一致性哈希 → 固定 worker，即 llm-d 的 prefix-aware routing。增量是 Flink 用事件时间 keyed state 维护"哪个 session 在哪个 worker 有未完成的历史前缀"，并在请求到达时做路由决策式：
  `T_transfer(S,i,j) + T_queue(j) < min(T_queue(i), T_recompute(S,j))`
  （式 1，来自 arXiv 2609.23130：路由到持有前缀的 worker / 等待 / 跨 worker 传 KV / 就地重算，四选一）。
- **checkpoint/恢复语义（本课题最硬的增量）**：Flink checkpoint 的是**前缀复用意图日志**（"存在前缀 P，长 L，属会话 S，应驻留 worker m"），**不 checkpoint 张量本身**。故障恢复时 Flink exactly-once 重放意图，指示 vLLM "你的驻留目标应为 {L0 系统前缀, 会话 S 历史前缀}"，vLLM 从 token transcript 重算或从 Mooncake 层取回 KV。这正是"控制面状态持久容错 / 数据面缓存易失可重建"的干净分离。RaidServe 做的是引擎内主动 KV 备份；本课题做的是控制面意图的 exactly-once 恢复，层次不同。

### 6. 与现有三类缓存的区别（为什么不是"上下文"换名）
- 现有"上下文缓存"= 缓存对话历史**文本**，省的是 token 费用与 prompt 拼接，**prefill 照跑**。
- 本候选 = 缓存对话历史的 **prefill K/V 计算结果**，省的是 prefill 计算与 TTFT。量级差：Mooncake 实测 46× TTFT 改善，来自 KV 复用而非文本复用。
- RAG 知识缓存现有做法通常是"缓存检索到的文档文本/embedding"；本候选是缓存"系统提示+文档"的 **KV blob**，且按内容哈希 key、跨会话路由。
- 历史回答缓存 = 缓存最终输出文本（语义缓存），命中直接返回答案，跳过**整段推理**；本候选命中只跳过前缀 prefill，仍要生成新回答。三者粒度不同：文本 vs KV 张量 vs 答案。

### 7. 文献证据
- Mooncake/vLLM×Mooncake：agentic trace 命中 1.7%→92.2%、TTFT ↓46×（vLLM blog 2026-05-06）。
- llm-d GLM-5.2：96% 主轮复用≥90% 输入，缓存轮 TTFT 快 2.8×（arXiv 2609.23130 转述 Ayoub et al. 2026）。
- PrefixPlace：放置优化在 RAG replay 上 materialization-cost 比 vLLM-APC 省 40.3%。
- HotPrefix：前缀热度动态追踪证明"热度感知驻留"优于纯 LRU。
- LPC（NeurIPS'25）：学习式插入/淘汰优于 LRU——支撑"分层差异化 TTL/淘汰"。
- 【假设/待验证】本课题的"分层差异化管理优于 vLLM 单层 LRU"是推论，需在多轮 agentic trace 上实测：把 L0 钉死、L3 按会话 TTL、L2 按内容哈希，对比 vLLM 全局 LRU 的 goodput。

### 8. 研究价值评估
- **研究问题**：在多轮 agentic 工作负载上，把前缀按"会话生命周期"分层、由 Flink 控制面以可恢复元数据管理、与在线路由/放置联合优化，能否在 cache-goodput 与故障恢复上优于"全局 LRU + 离线放置"？
- **可能创新点**（必须诚实）：
  1. **会话级、事件时间的前缀生命周期模型**（L0 跨会话钉住 / L3 随轮单调增长+会话 TTL / L2 内容哈希 blob），并证明 vLLM 单层 LRU 对"会话长前缀 + 全局系统前缀"混合场景次优。
  2. **控制面元数据 exactly-once 恢复 vs 数据面 KV 易失可重建**的故障容错叙事。
  3. **在线/流式的前缀-路由 crossover 预测器**，对标 PrefixPlace 的离线 epoch 规划——增量是连续、会话增长感知、带恢复语义，而非重解放置优化。
- **定位必须打这两个靶子**：vs llm-d（它是无状态请求路由器，不把多轮会话生命周期当一等 keyed state，也没有 exactly-once）；vs PrefixPlace（它是离线批次、可证明近似，但无在线事件时间与会话恢复）。

---

## 候选 2：推理思维链 / 推理前缀缓存（建议降级，并入候选1的知识层）

### 1. 缓存对象定义（收紧后）
原设想"缓存相似问题的 CoT 推理前缀"。收紧为两层：
- (2a) **已验证 worked-example 前缀**：把某类推理题（如某代数变换类）的一个已验证解题过程，作为 few-shot 前缀的 KV blob 缓存。这**本质是候选1的 L1/L2 知识层**。
- (2b) **跨会话 CoT-KV 复用**：把模型在问题 A 上的中间推理 KV 复用到相似问题 B。

### 2. 复用边界 / 3. 失效机制
- (2a)：精确前缀，同候选1 L1。
- (2b)：**只能近似复用**。不同问题的推理 token 序列不会 token 级相同。要复用 KV 需 (i) 贪心解码+相同前缀才偶发精确命中（脆弱），或 (ii) 隐藏状态余弦相似做近似共享（RKSC 路线）——这是**请求内多分支**技术（self-consistency 同题多解共享前缀），RKSC 实测 3.008×。ReasonCache（arXiv 2507.21433）已做跨生成相似推理步 KV 块复用，吞吐 +89.2%。

### 4. 时延可预测性
- 推理负载是 **decode-bound**（llm-d 实测路由在推理负载上 near-parity）。复用推理前缀只省 prefill，而推理瓶颈在 decode 吞吐。把长 CoT 当 prompt 注入本身又是长 prefill，收益有限。
- decode token 不能跨会话缓存（会破坏正确性/分布）。
- 结论：**与"时延可预测"主线不契合**——最可预测的是 prefill 长度，而推理瓶颈在不可跨会话缓存的 decode。

### 5. Flink 可行性 / 6. 与现有区别
- (2b) 的跨会话近似 KV 复用需要引擎内核改动（隐藏状态相似度、部分校正），质量风险高，不满足"控制面可管、不动引擎"。
- Flink 能做的只剩 (2a)：按任务类型聚类相似请求，把 curated worked-example 前缀路由到驻留 worker——这就是候选1的"知识层前缀放置"，不是独立新机制。

### 7. 文献证据 / 8. 研究价值
- RKSC（ICML'26）：请求内分支语义共享 3×；ReasonCache：跨生成推理 KV 复用 +89.2%；Retrieval-of-Thought：把推理步当**文本**存向量库检索（非 KV）。
- **判断**：作为独立缓存维度研究价值**中低**。跨会话 CoT-KV 复用已被 ReasonCache 在引擎层做掉，且是近似、质量风险、decode-bound 不契合可预测性主线。**建议并入候选1的 L1/L2 知识层**，只 claim"推理任务聚类的 worked-example 前缀放置"，不再单独立机制。

---

## 候选 3：预计算 / 预解码状态缓存（建议做 3a，排除 3b）

### 拆分
- **(3a) 空闲时段的会话级分层预热（idle-time session warming）**：两轮之间 GPU 空闲时，预测会话 S 何时恢复，提前把其历史前缀从 DRAM/SSD 层预取回 HBM。
- **(3b) 推测性预解码下一轮内容（speculative content pre-decode）**：在空闲时把会话"解码到下一决策点"。

### 1. 缓存对象定义
- (3a)：对象是**已经存在的 L3 会话前缀 KV 的"层级位置"**——在空闲窗口把它从冷层（DRAM/SSD）搬到热层（HBM）。不是新计算，是数据移动。
- (3b)：Speculative Pre-Positioning（arXiv 2606.29565）：用目标模型自身前向（无 draft 模型）把会话推进到下一决策点，下轮只付 delta；置信门触发则用缓存输出分布做单次词表扫描、零 decode。

### 2. 复用边界 / 3. 失效
- (3a)：安全、无损。只要会话 S 恢复就命中；不恢复则浪费一次搬运（可按恢复概率取舍）。
- (3b)：**硬伤**——开放对话中下一条用户输入在用户打字前是未知的，无法准确"预解码下一轮输入"。它要么 (i) 属于 speculative decoding（需 draft 模型，引擎内，TransKV 路线），要么 (ii) 预测的是工具调用/动作（SPORK 路线，**约束①排除**）。对纯 chat 不成立。

### 4. 时延可预测性
- (3a) 是**数据移动时间**：搬运 Z 字节、有效 KV goodput r，`t = Z / r`（PrefixPlace 式 1: `f_m(b) = Z_b / r_m`），**高度可预测**。把它藏在空闲时间后，恢复时的 tier-restore 时延被隐藏。可观测特征：前缀字节数 × 实测层间 goodput × 预测恢复 watermark。
- (3b) 的推测路径可预测性差（接受率随内容波动），且已属引擎内 decode 推测。

### 5. Flink 可行性
- **Flink 控制面**：按会话 keyed state 维护"轮次间隔分布"（过去 N 次 inter-arrival），用事件时间 timer 在 `预测恢复时刻 − tier-restore 时长` 触发"预热"控制事件。这是 Flink 天然的事件时间定时器能力。
- **数据面**：Mooncake/Strata 已支持层间 I/O 重叠，Flink 只需下发"提前取回"指令，**不需改 vLLM 内核**。
- (3b) 需引擎内核（decode 推测/输出分布缓存），排除。

### 6/7. 与现有区别 / 文献证据
- Strata 已有"cache-aware 调度重叠 I/O 与 decode"，Mooncake 已有 tier 重叠。本课题增量是**把"何时恢复"的会话级预测（Flink 事件时间）与"放在哪一层"（PrefixPlace 放置）耦合成"何时搬回 HBM"**。
- Speculative Pre-Positioning 证明"off critical path"的思路成立，但其内容推测部分超出本课题范围。

### 8. 研究价值
- 中等。(3a) 是候选1的自然第二维：候选1 决定**缓存什么(what)+放哪(where)**，(3a) 决定**何时(when)** 搬回热层。组合成"what/where/when"。增量 over Mooncake/Strata 是"会话恢复时刻预测驱动的预热"，需实测证明比盲目 I/O 重叠省更多恢复时延。

---

## 结论：最值得深化的 1–2 个候选与组合

### 首选深化：候选 1（分层前缀 KV，会话生命周期 + 控制/数据面分离）
理由：
1. **最具体**：四层前缀 × KV block 表示 × 每层明确 reuse boundary / 失效 / 兼容条件。
2. **最契合时延可预测主线**：prefill 与命中前缀长度近线性，是全管线最可预测阶段；llm-d/Mooncake 实测 Tailwind 级收益（46× TTFT、96% 复用）。
3. **最 Flink 原生**：会话 = keyed by session_id 的事件时间状态；TTL/会话窗口/exactly-once checkpoint 是 Flink 一等公民。
4. **差异化清晰且诚实**：不与 vLLM-APC（引擎内前缀缓存）、Continuum（工具等待 TTL）、IntentKV（引擎内剪枝）、PrefixPlace（离线放置）、llm-d（无状态路由）抢功；增量在"会话生命周期建模 + 控制面元数据恢复 + 在线 crossover 预测"。

### 次选深化：候选 3a（空闲时段会话级分层预热）
理由：与候选1共享同一套控制面元数据与恢复哲学，补"when"维度；时延可预测（数据移动时间）、不动引擎、有 Flink 事件时间定时器的独特抓手。作为论文第二个缓存维度，体量合适、风险低。

### 降级：候选 2 并入候选1的 L1/L2 知识层
不单独立机制。跨会话 CoT-KV 复用已被 ReasonCache 在引擎层做掉，近似且 decode-bound，不契合可预测性主线。只保留"推理任务聚类 → worked-example 前缀放置"这一安全切片。

### 论文组合叙事（一句话）
> **"Flink 托管的多轮 Agent 前缀状态：what（分层会话前缀 KV）/ where（在线放置+亲和路由，对标 PrefixPlace 离线版）/ when（空闲时段会话恢复预测驱动的分层预热），以持久控制面元数据 + 易失可重建的数据面 KV，实现多轮 agentic 推理的可恢复、可预测缓存管理。"**

三个维度共用一套元数据模型与 exactly-once 恢复语义，构成连贯论文主线，而非三个零散缓存条目。

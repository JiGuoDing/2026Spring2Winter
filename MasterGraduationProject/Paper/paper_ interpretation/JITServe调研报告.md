# JITServe 调研报告 —— SLO-aware LLM Serving with Imprecise Request Information

> 调研日期：2026-08-13  
> 调研对象：JITServe，NSDI 2026 正式 proceedings 版本（pp. 825–848）  
> 证据边界：仅使用 USENIX 正式论文/页面、arXiv 原文、作者公开的官方代码与模型资产，以及本仓库 Design 资料；未采用二手解读  
> 页码约定：下文“PDF 第 n 页”均指 [USENIX 正式 PDF](https://www.usenix.org/system/files/nsdi26-zhang-wei.pdf) 的文件页码（含第 1 页 USENIX 封面），不是 proceedings 印刷页码  
> 本地论文：[JITServe.pdf](../paper_source/JITServe.pdf)

---

## 0. 一句话结论（TL;DR）

JITServe 的核心不是“把每个请求尽快跑完”，而是：在输出长度、后续依赖都不精确的情况下，先用**保守上界**分配“刚好能赶上 SLO”的生成带宽，再随着 token 和调用图逐步显露而持续收紧估计；最后用 **GMAX（Grouped Margin Goodput Maximization）**同时决定“优先服务谁”和“哪些长度相近的请求一起成批”，把剩余容量留给更多请求。

论文覆盖三类 SLO：流式交互的 TTFT/TBT、完整响应的 deadline，以及多次 LLM/tool 调用组成的 compound request。作者报告，相比现有系统，JITServe 的 service goodput 提升 **1.4×–6.3×**，或在维持同等 goodput 时节省 **28.5%–83.2%** 资源（官方 PDF 第 2、3、10 页，摘要、§1、§6）。但后一组“资源节省”只作为汇总结果反复出现，正式版没有给出独立的资源缩放曲线或逐基线推导，引用时应保留这一证据边界。

对本毕业项目最重要的判断是：**JITServe 不是“纯单轮请求”系统**——它明确支持 agentic/deep-research 式多调用依赖图；真正的差异在于，它没有管理长生命周期会话的跨轮 KV 驻留/TTL、Flink keyed state/checkpoint，也没有联合优化 Flink operator 并行度、上游批次与会话驻留预算。因此，当前选题仍有清晰空间，但应修正项目旧资料中“JITServe 均面向单轮独立请求”的过强表述。

---

## 1. 论文基本信息与版本关系

| 项 | 内容 |
|---|---|
| 标题 | *JITServe: SLO-aware LLM Serving with Imprecise Request Information* |
| 作者 | Wei Zhang*, Zhiyu Wu*, Yi Mu, Rui Ning, Banruo Liu, Nikhil Sarda, Myungjin Lee, Fan Lai（*共同一作） |
| 机构 | UIUC、Google、Cisco Research；Rui Ning 标注为 unaffiliated |
| 会议 | 23rd USENIX Symposium on Networked Systems Design and Implementation（NSDI 2026） |
| 出版信息 | USENIX Association，May 2026，Renton, WA，pp. 825–848，ISBN 978-1-939133-54-0 |
| 正式页面 | [USENIX paper page](https://www.usenix.org/conference/nsdi26/presentation/zhang-wei) |
| 正式 PDF | [nsdi26-zhang-wei.pdf](https://www.usenix.org/system/files/nsdi26-zhang-wei.pdf) |
| arXiv | [2504.20068](https://arxiv.org/abs/2504.20068)：v1 2025-04-24；当前可见 v3 更新于 2025-12-22 |
| 官方代码 | [UIUC-MLSys/JITServe](https://github.com/UIUC-MLSys/JITServe)；本次核验 HEAD 为 [`84584a1`](https://github.com/UIUC-MLSys/JITServe/tree/84584a119b892cf90c65e2b3f5bac67250d39d27) |
| QRF 资产 | [En-2863/jitserve-qrf-length-predictor](https://huggingface.co/En-2863/jitserve-qrf-length-predictor) |
| Artifact 状态 | USENIX 正式页展示 **Available** 与 **Functional** 两枚 artifact badge |
| 其他官方材料 | [Slides](https://www.usenix.org/system/files/nsdi26_slides-zhang-wei.pdf)；[Presentation video](https://www.youtube.com/watch?v=2wSboHoW2H4) |

### 1.1 本报告采用哪个版本

本报告以 **USENIX 正式 proceedings PDF** 为主。正式 PDF 共 25 个文件页面：第 1 页为 USENIX 封面，正文、参考文献和附录对应 proceedings pp. 825–848。arXiv v3 共 22 页，是较早的预印本。

正式版相较 arXiv v3 至少补充或明确了：SLOs-Serve 基线、§7 Discussions、用户调研的 bootstrap 置信区间与卡方检验、扩展理论附录，以及正式 artifact/代码入口。两版的核心系统设计和 headline 结果一致。下文如无特别说明，均指正式版。

---

## 2. 问题背景：为什么“越快越好”不是正确目标

### 2.1 三类请求对应三类 SLO

| 请求类型 | 典型场景 | 真正关心的 SLO | JITServe 的 goodput 定义 | 来源 |
|---|---|---|---|---|
| Latency-sensitive | 对话、流式代码、实时语音 | TTFT、TBT | 第 i 个 token 若在 `TTFT_SLO + i × TBT_SLO` 前生成，则计入 goodput | PDF 第 4–5 页，§2.1、§3 |
| Deadline-sensitive | tool trigger、批处理、AIOps | 完整响应的 E2EL/TTLT | 截止时间前完成，则输入+输出 token 全计入；否则为 0 | PDF 第 4–5 页，§2.1、§3 |
| Compound | deep research、multi-agent、test-time scaling | 多个依赖调用整体的 E2EL | 最后一个子请求在总 deadline 前结束，则所有子请求 token 计入；否则为 0 | PDF 第 4–5 页，§2.1、§3 |

这一定义把“服务吞吐量”改成“**按时交付的有效吞吐量**”。一个 deadline 很宽松的任务即使提前很多完成，也不会带来额外应用价值；占用的算力反而可能让紧急请求违约。

作者用超过 550 名用户/开发者的匿名调查和两家大型服务提供方访谈支撑“同一应用内也有不同 SLO 偏好”。例如代码生成中，38.1% 偏好实时流式、30.5% 偏好快速完整返回、31.4% 视上下文而定（PDF 第 3–4 页，§2.1、Table 1）。正式版附录还给出 1,000 次 bootstrap 的 95% 置信区间及按 workload 的卡方检验（PDF 第 19 页，Appendix A，Tables 3–4）。

### 2.2 两类不确定性

1. **输出长度不确定**：即使拿到完整 prompt，自预测和 BERT/Llama3 预测器仍会明显偏离真实长度；低估会导致 SLO 违约，高估则会过度预留带宽（PDF 第 4–6 页，Figure 2(b)、§4.1）。
2. **执行依赖不确定**：deep research、reasoning、multi-agent 的 LLM/tool 调用数和 DAG 会在运行中展开，后续 prompt 甚至尚未生成，无法到达时一次性精确规划（PDF 第 3–4、6–7 页，Figures 2(a)、6，§2.2、§4.1）。

### 2.3 现有调度目标为何失配

SJF/LTR 倾向短任务，Autellix/PLAS 优化 compound request 的平均完成时间，Sarathi-Serve 主要改善 TTFT/TBT，vLLM 默认 FCFS。这些目标都可能让大量请求错过各自 SLO，即使平均时延或总吞吐看起来更好。论文附录用对抗序列证明 EDF 和 SJF 相对 goodput-optimal oracle 都没有常数竞争比（PDF 第 20–21 页，Theorems E.1–E.2）。

---

## 3. 系统总览

JITServe 作为 vLLM 上的一层 SLO-aware middleware，主链路是：

```text
请求 + SLO
   │
   ▼
Request Analyzer
  ├─ QRF：预测输出长度高分位上界，并随生成持续更新
  └─ Pattern Graph：匹配历史调用图，估计后续依赖与阶段 deadline
   │
   ▼
SLO-aware Scheduler / GMAX
  ├─ 估算每个请求在当前 frame 的最低服务带宽
  ├─ 按 margin goodput / bandwidth 排序
  ├─ 在高优候选中按长度相近组成 batch
  └─ 仅在收益超过 KV 恢复/重算成本时抢占
   │
   ▼
vLLM runtime + SLO Tracker
  └─ 回传实际 token 速度和生成进度，触发下一轮精化
```

对应官方 PDF 第 6 页 Figure 4。JITServe 的“JIT”指 **just enough, just in time**：不一开始把所有资源塞给最紧急任务，而是在每个调度 frame 中给它恰好足以守住 SLO 的份额，把多余容量留给其他任务。

---

## 4. 核心设计详解

### 4.1 输出长度：高分位上界 + 生成中精化

JITServe 不追求一个看似精确的点估计，而用 Quantile Regression Forest（QRF）预测输出长度的高分位上界：

- 上界低估会违约；高估会浪费容量，因此先保守、后逐步放松；
- 每生成一段 token，就把新 token 追加到输入并重新预测；论文示例是**每 50 token**更新一次（PDF 第 6 页，§4.1）；
- 正式实验的 QRF 使用 **300 棵树、最大深度 150**（PDF 第 10 页，§6.1）；
- 官方 artifact 的 `prediction.py` 明确使用 `quantiles=[0.95]`，即 P95 预测；这一具体分位数没有在正文写出；
- 单次 QRF 预测约 **7 ms**，论文称比微调 BERT 预测器快 **7×**（PDF 第 6 页，Figure 5(a)）。

直觉是：已经生成 300 token 后，“还会生成多少”通常比只看原始 prompt 时更容易估；即使初始上界偏保守，后续也能把占用的虚拟带宽还回去。

### 4.2 Compound request：增量 Pattern Graph 匹配

对多调用工作流，JITServe 把一次已完成任务保存为 pattern graph：

- LLM 节点记录输入/输出长度和模型身份；
- tool 节点记录执行耗时和工具身份；
- 边记录调用依赖；节点/边属性通过 Gaussian kernel 计算相似度；
- 新任务每展开一个阶段就扩展 partial graph，并剪掉前缀结构已不匹配的历史图。

匹配到最相似的历史图后，JITServe 将总 deadline `D` 按历史累计耗时比例分解。设阶段 s 之前（含 s）的累计耗时为 `t_≤s`，历史图总耗时为 `t_total`：

```text
φ(s) = t_≤s / t_total
D_s  = φ(s) × D
```

这里 `D_s` 是到阶段 s 为止的累计 sub-deadline，而不是给每一阶段平均切一刀。作者比较了只按当前阶段耗时等替代方案，累计比例误差更低（PDF 第 7、19 页，§4.1、Appendix B、Figure 22）。

工程上，历史图先用 K-medoids 聚类；低复用图的频率每小时乘 0.9 衰减并被淘汰。单图通常小于 **0.2 KB**；500 张历史图时匹配延迟仍低于 **5 ms**（PDF 第 7 页，Figure 7、§4.1）。

### 4.3 最低带宽建模

对请求 r，论文先估算剩余生成时间：

```text
t_gen(r) = len_rem(r) × v_token(r)
bw(r)    = t_gen(r) / t_rem(r)
```

- `len_rem(r)`：剩余输出长度的保守上界；
- `t_rem(r)`：距离 deadline 的剩余时间；
- `v_token(r)`：论文文字称“per-token generation speed”，但公式按乘法使用，量纲上更像“每 token 耗时”，这是一个记号表述不够严谨之处。

调度被切成长度为 `Δ` 的 frame：

```text
bw_Δ(r)      = [t_gen(r) / t_rem(r)] × Δ
goodput_Δ(r) = [goodput(r) / t_rem(r)] × Δ
Priority(r)  = goodput_Δ(r) / bw_Δ(r)
             = goodput(r) / t_gen(r)
```

也就是优先选择“单位预计生成时间能贡献更多有效 goodput”的请求。对 latency-sensitive 请求，TBT 本身直接给出逐 token 所需带宽；对 compound 请求，当前阶段的所有子请求合并计算剩余长度和带宽（PDF 第 8 页，Algorithm 1、§4.2）。

### 4.4 GMAX：先保 goodput，再保 batch 效率

只按 Priority 取前 B 个请求，可能把长度差异很大的序列塞进同一 batch，造成 padding/执行不齐。GMAX 因此分两步：

1. 取第 B 高优先级 `Priority(r_(B))`，只保留满足 `Priority(r) ≥ p × Priority(r_(B))` 的候选；论文举例 `p=0.95`；
2. 候选按输入长度排序，用大小为 B 的滑窗枚举连续组，选择组内 Priority 之和最大的 batch。

`p` 小，候选更多、长度更容易齐，但可能混入低价值请求；`p` 大，goodput 更有保障，但批内长度可能更不齐。系统在线探索并调整 p（PDF 第 9 页，§4.2）。调度复杂度为 `O(N log N)`，论文报告队列中数千请求仍可在 **20 ms** 内完成调度（PDF 第 9 页，Figure 9）。

### 4.5 抢占、扩展与公平

- **代价感知抢占**：KV 从 DRAM 恢复受 I/O 带宽约束，重算受 GPU FLOPs 约束。JITServe 估算 `goodput_loss = stall_duration × token_generation_speed`，只有新请求收益超过损失才抢占；调度 frame 示例为 **50 decoding steps，约 300 ms**，抢占相关开销报告为 **<1%**（PDF 第 9 页，§4.2）。
- **多副本**：为一个请求随机采样 K 个模型副本，创建带副本特定 priority 的 dummy copies；选中后删除其余副本，复杂度额外 `O(K)`（PDF 第 9 页，§4.3）。
- **公平扩展**：可将优先级改为 `(1-f)×Priority(r) + f×Fair(r)`；这是扩展接口，不是主实验中完整验证的公平算法（PDF 第 9–10 页，§4.3）。

### 4.6 理论保证，以及正式版中的公式矛盾

论文证明 goodput-optimal 调度即使知道未来也为 NP-hard（PDF 第 20 页，Theorem D.1）。正文 Theorem 4.1 声称：

```text
G_GMAX(R) ≥ (1 / 8.56) × G*(R)
```

即在线 GMAX 至少取得离线 oracle goodput 的约 11.7%（PDF 第 9 页）。这个下界很松，但意义在于有常数竞争保证，而 EDF/SJF 在论文构造下可任意差。

不过，正式附录存在一处需要作者澄清的代数/记号矛盾：

1. Appendix E 的 Eq. 43 已把 `δ/(1+δ)` 包进 `B(δ,α,β,γ)`，并数值求得无 GMAX 时约 `1/8.13`（PDF 第 24 页）；
2. Eq. 51 又写成 `p × δ/(1+δ) × B(...)`，看起来把同一因子重复乘了一次（PDF 第 25 页）；
3. 紧接着报告的 `1/8.557` 实际上与 `p=0.95` 时的 `p × (1/8.13)` 一致，而不与印刷的 Eq. 51 一致。

因此，正文的 `1/8.56` 很可能对应“GMAX 额外损失一个 p 因子”的意图，但 Eq. 51 的排版公式不能按字面与数值结果同时成立。本报告不替作者修公式；引用理论保证时应注明这处正式版内部不一致。

---

## 5. 实现

论文称在 vLLM 上新增约 **2,800 行代码**，保留 OpenAI 风格 API，并继承 chunked prefill 与 prefix caching（PDF 第 10 页，§5）。API 增加 `deadline`、`target_tbt`、`target_ttft`、`waiting_time` 等 SLO 参数；超过最大等待时间仍未被调度的请求会被丢弃，防止过载扩散。

论文架构中，QRF 和 pattern matcher 在独立异步进程中，通过 gRPC 与控制面交换少量元数据；监控 daemon 负责组件存活与周期 checkpoint（PDF 第 10 页，§5）。官方仓库则 vendoring 了 vLLM commit `32176fe`，要求先安装仓库内 `third_party/vllm/`，不能直接使用 PyPI 最新 vLLM。

需要注意：本次核验的代码 HEAD 与正式论文存在实现漂移。比如论文写 gRPC，而当前 `prediction.py` 是绑定 `localhost:65433` 的 TCP socket；论文讨论 all-or-nothing goodput，当前 `policy.py` 还有 `penalty_factor` 控制的软衰减 reward。它们说明 artifact 实现比论文伪代码更具体、也可能处在不同整理阶段，**不能据此断言论文实验错误**，但复现时必须固定 commit 并记录“论文概念—代码类/参数”的映射。

---

## 6. 实验设置与核心结果

### 6.1 实验设置

| 项 | 设置 | 来源 |
|---|---|---|
| 模型 | Llama-3.1-8B、Qwen2.5-14B、Qwen3-30B-MoE-A3B、Llama-3.1-70B | PDF 第 10 页，§6.1 |
| 硬件 | 16 × NVIDIA A100 | PDF 第 10 页，§6.1 |
| 应用 | Chatbot、Math Reasoning、Deep Research、Agentic Code Generation | PDF 第 10 页，§6.1、Table 2 |
| 数据 | Alpaca、LMSys-chat、Search Arena 等；到达过程使用缩放后的 Microsoft LLM serving trace，另做 Poisson 消融 | PDF 第 10 页，§6.1 |
| 请求规模 | 每次运行 >10K 请求，在线窗口至少 1 小时 | PDF 第 10 页，§6.1 |
| 默认混合 | latency : deadline : compound = 1:1:1 | PDF 第 10 页，§6.1 |
| SLO | 约 2s TTFT、100ms TBT；deadline 请求 E2EL 20s；compound 为 `20s × stage 数` | PDF 第 10 页，§6.1 |
| SLO 来源 | 1K 次 DeepSeek API 调用的 P95 时延 | PDF 第 10 页，§6.1 |
| QRF | 300 trees，max depth 150 | PDF 第 10 页，§6.1 |
| 重复次数 | 所有结果取 5 次独立运行平均 | PDF 第 11 页，Metrics |
| 基线 | Autellix、LTR、vLLM、Sarathi-Serve；正式版另含 SLOs-Serve | PDF 第 10–11、13 页，§6.1、§6.4 |

这里的“真实”主要指真实数据集、用户偏好与到达 trace 的组合；三类请求标签、混合比例和 SLO 仍经过实验构造，并不是一条原样采集的端到端生产混合 trace。

### 6.2 核心定量结果

| 结论 | 数值 | 论文位置 |
|---|---:|---|
| headline service goodput | 相比现有设计 **1.4×–6.3×** | PDF 第 2、3、10 页，摘要、§1、§6 |
| headline 等 goodput 资源节省 | **28.5%–83.2%** | PDF 第 2、3、10 页，摘要、§1、§6 |
| 1 小时 token goodput | 比 LTR **1.3×–1.7×**；比 Autellix **5.3×–6.1×** | PDF 第 11 页，Figure 11、§6.2 |
| request-level goodput | 比 LTR **2.3×–4.5×** | PDF 第 11 页，Figure 12、§6.2 |
| 与 perfect-information oracle 差距 | 仅 **3%–9%** | PDF 第 11 页，Figure 13、§6.2 |
| 原始 serving throughput | 达 Sarathi-Serve 的 **96%–98%** | PDF 第 11–12 页，Figure 14、§6.2 |
| 多副本扩展 | 比 Sarathi-Serve **1.34×–2.42×** | PDF 第 13 页，Figure 18、§6.4 |
| SLO 松紧敏感性 | request/token goodput 均高 **2.3×–2.8×** | PDF 第 13 页，Figure 19、§6.4 |
| workload mix | 33% latency + 66% deadline 时提升 **1.8×**；纯 latency 时比 Sarathi **1.72×** | PDF 第 13 页，Figure 20、§6.4 |

### 6.3 消融：预测器和 GMAX 都有贡献

Figure 17 给出的单组消融值如下（PDF 第 12 页）：

| 变体 | Request goodput (req/s) | Token goodput (token/s) |
|---|---:|---:|
| JITServe*（精确信息 oracle） | 3.23 | 7808 |
| 完整 JITServe | 3.17 | 7637 |
| 去掉 Request Analyzer | 2.91 | 6893 |
| 去掉 GMAX，改用 SJF | 2.70 | 6080 |
| Sarathi-Serve | 1.35 | 4540 |

这组结果说明收益不是单独来自 QRF，也不是单独来自调度：预测器把“不精确信息”转成可用上界，GMAX 再把上界转成调度动作。完整系统与 oracle 的差距在该配置下很小，但该单组柱状图不能替代不同漂移强度下的置信区间分析。

### 6.4 如何谨慎理解这些数字

1. **1.4×–6.3× 是跨模型/基线/负载的范围，不是任意场景固定提升。** 论文自己也显示 LTR 在 deadline-sensitive 平均 E2EL 上可能很强，只是在混合 SLO 下整体 goodput 退化（PDF 第 12 页，§6.3）。
2. **28.5%–83.2% 不能从正式版图表直接重算。** 正式版三处重复该汇总值，但没有独立资源缩放图或逐基线换算表；应作为作者报告值，而非本报告复算值。
3. **“近 oracle”依赖评测分布。** Figure 13 的 3%–9% 很强，但作者在 §7 也承认持续分布漂移或 pattern matching 失败时可能要重训或启用 fallback（PDF 第 11、13 页）。
4. **JITServe 不是每个传统时延指标的冠军。** Figure 16 中，它的 latency-sensitive TBT P95 为 104.9 ms，略高于约 100 ms 的目标；deadline-sensitive E2EL P50 为 4.0 s，也慢于 LTR 的 2.6 s。它赢的是三类流量合并后的有效 goodput，而不是让每项 P50/P95 都最小（PDF 第 10、12 页，§6.1、Figure 16）。

---

## 7. 局限性与批判

### 7.1 作者明确承认的局限

1. **all-or-nothing goodput 过硬**：deadline 晚一点点就从全部价值掉到 0，不能表达 near-miss 的部分效用。作者建议未来用 soft deadline/graded utility；GMAX 理论上可接受抽象 goodput 函数（PDF 第 13 页，§7）。
2. **分布漂移与预测错误**：初始保守、在线修正和 frame 重调度能恢复一次性误判，但持续漂移仍可能需要重训 predictor 或显式 fallback（PDF 第 13 页，§7）。
3. **异构 GPU profiling 不完整**：当前只在部署前离线测 I/O 带宽，线上监控轻量 iteration time；复杂的多节点、混合 GPU 环境可能需要选择性运行时 profiling（PDF 第 13–14 页，§7）。

### 7.2 本调研补充的批评

1. **对 Agentic 的覆盖是“请求内调用图”，不是“长生命周期会话状态”。** Pattern graph 解决同一 compound task 的调用依赖与 deadline 分摊，但没有建模轮间空闲期、跨轮 KV 复用收益、TTL、会话恢复和 checkpoint。这既是边界，也是本课题的空间。
2. **QRF 上界不是经过校准的覆盖保证。** 官方代码固定 P95，但论文没有报告预测区间的经验 coverage、不同漂移下的 under-coverage 或在线 conformal 校准；Figure 5 主要展示预测比值轨迹。
3. **pattern graph 假设结构重复。** 500 张历史图时延很低，但节点/边主要依赖长度、耗时和身份，而非任务语义；遇到新工具、新 DAG 或多租户分布切换，匹配质量可能骤降。
4. **token goodput 可能偏向长请求。** deadline/compound 请求按输入+输出 token 计价值，长请求一旦可按时完成就贡献更多；公平扩展只在设计层说明，主实验没有完整的多租户公平性评估。
5. **外部有效性有限。** 主实验是 16×A100、四类构造 workload 和缩放 trace；没有跨 GPU 世代、广域多节点、Flink 背压/排队链路或长期会话 KV 生命周期实验。
6. **artifact 文档仍有断裂。** USENIX 给了 Available/Functional badge，但当前 HEAD 的 README 指向不存在的 `scripts/benchmark_mixed.sh`，`traces/README.md` 也有过时路径；`pyproject.toml` 没列运行依赖，且未发现项目自身测试。复现前必须先做路径和依赖审计。

### 7.3 论文内部和论文—代码不一致

| 位置 | 不一致 | 处理建议 |
|---|---|---|
| Appendix E Eq. 43 vs Eq. 51 | `δ/(1+δ)` 疑似重复；正文 1/8.56 与 Eq. 51 字面不同时成立 | 引用定理时注明，等待作者勘误 |
| §6.4 SLO tightness 段 | 文字写 “Figure 21”，实际应对应 Figure 19；Figure 21 是 SLOs-Serve 对比 | 按图题和上下文读作 Figure 19 |
| Table 1 vs Appendix Table 3 | Real-time translation 的 Real-Time 点估计为 36.2%，但 bootstrap 95% CI 为 26.0%–34.8%，点估计落在区间外 | 用户调研该行需作者核对 |
| Appendix D 的归约 | Multiple Knapsack 反向证明写总 goodput 至少为 `C`，上下文目标量应为 `Ψ` | 视为符号笔误，不据此扩展结论 |
| Appendix E.1 EDF 反例 | `B_i` 的 SLO 在定义处写成统一的 `T+δ`，随后推导却按随 i 增长的 deadline 使用 | EDF 非竞争性结论的印刷证明需勘误 |
| Algorithm 1 vs §4.2 正文 | 伪代码 bandwidth 写 `len_rem / remaining_time`，正文写 `t_gen / t_rem`；两者量纲不同，且伪代码未完整展示 frame 最低带宽如何强制兑现 | 复现以固定 commit 的实际 scheduler 为准 |
| 正文 §5 vs artifact HEAD | 正文写 gRPC；`prediction.py` 用 localhost TCP socket | 固定 commit，记录实现映射 |
| 正文 all-or-nothing vs artifact HEAD | `policy.py` 保留 `penalty_factor` 软衰减 reward | 不据此判实验错误；复现时明确启用的 policy/参数 |
| 正文 QRF | 只写 high-quantile | 官方代码实际为 P95 |

---

## 8. 与相关工作的定位

| 工作/类别 | 主要优化对象 | JITServe 相对定位 | 来源 |
|---|---|---|---|
| vLLM / Orca | throughput、continuous batching、KV 内存 | JITServe 架在 vLLM 上，用应用 SLO 重排请求 | PDF 第 10、14 页，§5、§8 |
| Sarathi-Serve / DistServe / Splitwise | prefill/decode、TTFT/TBT | 更偏 latency-sensitive；JITServe 同时处理 deadline/compound | PDF 第 5、10–14 页 |
| Autellix | compound program 的 LAS/平均 E2EL | JITServe 不只处理 compound，还统一三类 SLO，并显式用不精确信息 | PDF 第 5、10–12 页 |
| LTR / S3 / TetriInfer / u-Serve | 输出长度预测或 SJF 排序 | JITServe 用高分位上界、生成中精化，而非一次性点估计/分桶 | PDF 第 6、14 页 |
| Parrot | 暴露 LLM program 的依赖 | JITServe 进一步从历史 pattern graph 推断尚未显露的依赖并分摊 deadline | PDF 第 7、14 页 |
| SLOs-Serve | 多 SLO + dynamic programming | JITServe 用近似 GMAX 降低搜索成本，高负载下更可扩展 | PDF 第 11、13 页，Figure 21 |
| AdaServe | 自定义 SLO + 细粒度 speculative decoding | 二者互补；JITServe 负责更广的跨请求编排 | PDF 第 14 页，§8 |
| 经典 cluster/network scheduler | 相对稳定的 job/stage、fairness/utilization | JITServe 面向 token 级进展、变长和未知依赖 | PDF 第 14 页，§8 |

JITServe 的独特点不是单一预测器或单一优先级公式，而是把三件事绑在一起：**不确定信息的保守估计、运行时精化、goodput 与 batch 效率的联合调度**。

---

## 9. 对当前毕业项目的潜在启发

本节只依据本仓库的 [毕业设计选题研究全记录](../../Design/design_prototype/毕业设计选题研究全记录.md) 中已记录的 InferTuner 基底和锁定选题，不假设尚未实现的能力。

### 9.1 先校正两个项目资料表述

1. 项目资料把 “Tempo” 标成 `arXiv 2504.20068`，但该编号实际是 **JITServe**。Tempo 的编号需要另行核验；本报告不替未经一手来源核验的 Tempo 条目补号。
2. “ELIS/Tempo/JITServe 均面向单轮独立请求”对 JITServe 不准确。JITServe 明确处理 compound、multi-agent、deep research 多调用图。更准确的差异是：**JITServe 管请求/任务内 DAG 的 token 调度；本课题管跨轮会话状态在 Flink 管线中的持久驻留、迁移与联合配置。**

### 9.2 可直接借鉴的机制

1. **把现有 token/时延预测器改为运行时精化接口**：项目已有 GBDT 特征 `post_token_num`，可沿用 JITServe“每若干 token 重估剩余量”的闭环。不要直接照搬固定 50 token，应测“精化收益 vs 预测 RPC/重排开销”。
2. **QRF + conformal 的分工**：QRF 给长度分位数，项目既定 conformal 校准负责让覆盖率在漂移下可测、可纠偏。这正好补 JITServe 没有报告 coverage guarantee 的空白。
3. **把 `bw=t_gen/t_rem` 作为快时间尺度需求信号**：InferTuner 当前主要联合选择 `(p,b,TTL,M_kv)`；可让 GMAX 风格的 frame-level bandwidth 成为内环，分钟/漂移触发的 Flink 配置优化作为外环。
4. **Pattern graph 可作为会话行为预测的一个 baseline**：对结构重复的 agent workflow，用历史工具/LLM 阶段图预测剩余轮数和阶段 deadline；再与项目计划的“工具类型×轮次分桶/QRF”比较，而不是直接宣称 pattern graph 能预测开放式会话。
5. **把抢占代价扩展为 KV 驻留机会成本**：JITServe 已显式比较抢占收益与 KV reload/recompute 损失；本课题可以进一步加入“继续占用到下一轮”的显存时间成本和跨轮命中概率。
6. **复用其 goodput 作为对照指标，但新增会话指标**：保留 token/request goodput，另报会话 JCT、跨轮 TTFT、驻留命中/误驻留、GPU 时数，避免单一 token goodput 偏向长请求。

### 9.3 清晰的差异化边界

| 维度 | JITServe | 当前毕业项目（仓库已锁定方向） |
|---|---|---|
| 系统层 | vLLM 内/近端 middleware 调度 | Flink operator/pipeline 控制层 |
| 工作单元 | 单请求 + compound task 内多调用 DAG | 长生命周期 session 的多轮请求 |
| 在线状态 | 输出上界、pattern graph、SLO tracker | keyed session profile、轮间隔/剩余轮数/上下文增长、驻留表 |
| KV 关注点 | 单次抢占的 reload/recompute 成本 | 跨轮 KV 驻留 TTL、预算、命中、迁移和故障恢复 |
| 决策变量 | batch 组成、抢占、模型副本 | `(p,b,TTL,M_kv)` 联合配置 + 会话亲和/驻留门控 |
| 容错 | 控制面元数据 checkpoint（论文概述） | Flink checkpoint 下的 keyed/operator state 一致性 |
| 目标 | 异构 SLO 下 token/request goodput | 会话 JCT/轮 TTFT 机会约束下最小 GPU 成本，并兼顾复用 |

因此，“无需避让 JITServe”的结论可以保留，但论文中不应把它弱化成纯单轮工作。更有说服力的表述是：**JITServe 已覆盖不精确信息下的请求级 SLO 调度；本课题把不确定性对象提升为会话行为分布，把控制层提升到有状态流处理，并把 KV 生命周期与 operator 配置联合起来。**

### 9.4 建议加入的对照与消融

1. `FCFS/vLLM`；
2. `JITServe-style`：P95 长度上界 + frame-level GMAX，但无会话驻留；
3. `Session-only`：会话亲和 + 固定 TTL，无运行时精化；
4. `Ours w/o calibration`：去掉 conformal/漂移校准；
5. `Ours w/o joint optimization`：固定 `(p,b)`，只做驻留；
6. `Oracle`：知道真实轮间隔、剩余轮数与输出长度。

这样能回答：收益究竟来自 JITServe 已有的“token 级在线精化”，还是来自本课题新增的“跨轮状态 + Flink 联合控制”。

---

## 10. 复现建议

### 10.1 建议分三层，不要一上来追完整 Figure 11

**层 1：CPU/单卡 artifact 冒烟**

1. 固定官方 HEAD `84584a119b892cf90c65e2b3f5bac67250d39d27`；
2. Python 按 README 用 3.10+，CUDA 12+；记录驱动、PyTorch、GPU、模型 revision；
3. 按 `assets/README.md` 下载 QRF model/vectorizer；
4. 安装 `third_party/vllm/` 的 vendored snapshot，再 `pip install -e .` 安装 JITServe；
5. 单独启动 `python jitserve/request_analyzer/prediction.py`，验证 P95 预测路径和 localhost 端口；
6. 用少量 trace 检查三类请求的 SLO 字段、goodput 计算和日志，不先追性能数字。

**层 2：单模型、缩小 workload 的机制复现**

1. 从 Llama-3.1-8B + 200 请求开始；
2. 对比 FCFS、Sarathi-style、JITServe、JITServe w/o analyzer、w/o GMAX；
3. 固定随机种子，至少 5 次，报告均值与置信区间；
4. 先复现 Figure 17 的排序关系，再扫 RPS 做 Figure 15 趋势；
5. 同时记录预测 coverage、重预测次数、调度耗时、KV 抢占/恢复字节数，补足原论文未展开的诊断指标。

**层 3：与本项目结合**

1. 将 JITServe-style 逻辑作为 vLLM backend 内基线，不改它的目标；
2. 在 Flink 外层加入会话 keyBy、驻留表和 `(p,b,TTL,M_kv)` 决策；
3. 公开同一份 session trace 的转换脚本，确保各基线看到相同 arrival、SLO 和模型输出长度；
4. A6000/H20 与论文 A100 不同，主张应以相对趋势和机制消融为主，不宣称复现论文绝对吞吐。

### 10.2 当前 artifact 的具体复现风险

1. 根 README 指示的 `scripts/benchmark_mixed.sh` 在核验 commit 中不存在；实际可见的是 `benchmark_e2e.sh`、`benchmark_e2e_burst.sh` 等。应先人工检查参数，不要照抄 README。
2. `traces/README.md` 的部分示例路径使用 `benchmarks/`，实际目录是 `benchmark/trace/tools/`；某些 deep-research shell 脚本还引用仓库未包含的旧数据路径。
3. `pyproject.toml` 的 dependencies 为空，但代码实际导入 numpy、pandas、torch、transformers、fastapi、aiohttp、joblib 等；必须自行冻结完整环境。
4. 仓库顶层没有发现 JITServe 自身的自动化测试；建议先增加纯 CPU 的 priority、goodput、trace parser 和 graph matcher 单测。
5. 个别脚本含疑似硬编码 credential 的字符串。不要复制或提交该值；改为使用自己的环境变量，并建议维护者清理/轮换。
6. 正文、README、代码对 transport、reward 和脚本名存在漂移。复现报告必须给 commit、命令、配置文件 diff 和原始日志，不能只写“按官方 README”。

---

## 11. 一手来源清单

1. USENIX 正式页面：<https://www.usenix.org/conference/nsdi26/presentation/zhang-wei>
2. USENIX 正式 proceedings PDF：<https://www.usenix.org/system/files/nsdi26-zhang-wei.pdf>
3. NSDI 2026 Technical Sessions：<https://www.usenix.org/conference/nsdi26/technical-sessions>
4. arXiv abstract / version history：<https://arxiv.org/abs/2504.20068>
5. arXiv v3 PDF：<https://arxiv.org/pdf/2504.20068v3>
6. 作者官方代码：<https://github.com/UIUC-MLSys/JITServe>
7. 本次核验代码 commit：<https://github.com/UIUC-MLSys/JITServe/tree/84584a119b892cf90c65e2b3f5bac67250d39d27>
8. 作者提供的 QRF 资产：<https://huggingface.co/En-2863/jitserve-qrf-length-predictor>
9. USENIX 官方 slides：<https://www.usenix.org/system/files/nsdi26_slides-zhang-wei.pdf>
10. USENIX 页面嵌入的 presentation video：<https://www.youtube.com/watch?v=2wSboHoW2H4>

> 调研声明：报告中的系统机制、公式、实验数字和作者自述局限均已回到正式论文逐页核对；项目启发只引用仓库现有 Design 资料。`28.5%–83.2%` 资源节省的逐实验推导、Appendix E 的竞争比公式矛盾，以及论文与 artifact HEAD 的实现漂移，均已明确标注为证据不足或待作者澄清之处。

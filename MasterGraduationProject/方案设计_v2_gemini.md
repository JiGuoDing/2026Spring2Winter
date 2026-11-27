# 第一章异质缓存设计方案修订蓝图与修改计划书（v2 · 提交 Codex 复审版）

> **文档定位**：本蓝图逐项吸纳了 Codex 评审报告（`第一章_设计方案评审_交给Gemini迭代.md`）中的全部 P0 与 P1 反例意见，锚定《第一章_改后初稿_第二版.md》第 1.1 节的两个研究问题，交付一份**可计算、可验证、经受反例回放检验的修订版算法蓝图与实验改动清单**。待 Codex 复审确认无剩余反例后，再据此落地修改论文正文。

---

## 1. 问题映射与模块取舍（主贡献 / 必要支撑 / 可选扩展）

本节保持 §1.1 的两个研究问题不变，不拆分第三个问题，不引入虚构贯穿案例；保持 §1.1 已落稿的逻辑容量动因克制表述（“可能增加……”），不将其宣称为已测物理瓶颈；严格保留四类对象范围、`act` 只读限制，以及**系统已知版本 $\mathcal{G}_t$** 与**外部真实生效版本 $\mathcal{G}_t^{\mathrm{true}}$** 的区分。

| §1.1 研究问题 | 对应模型与算法 | 主指标与关键对照 | 模块定位 |
| :--- | :--- | :--- | :--- |
| **问题一（前半）**：计入读取、校验、适配与回退耗时后，如何估计四类对象未来时间净节省？ | **完整路径之差模型** $\Delta T(q \mid M,\pi,\mathcal{G}_t)$ + 条目级初筛估值（含 `plan` 互斥分支期望返工） | 动机实验 (a)；C2/C4 窗口累计时间净节省、P95 时延、安全复用率 | **主贡献**（路径去重口径）+ **必要支撑**（条目初筛与 `plan` 互斥分支） |
| **问题一（后半）**：语义回答候选自身反馈不足时，如何权衡当前复用与误用风险？ | **Algorithm 1（`OnlineReuse`）**：硬有效性检查 + 版本兼容的同簇反馈借用 + 经验风险门控 | C1：开关簇借用、开关平滑、固定阈值与逐条目门控基线；分别报全请求误复用率、已复用中误用率、相对无缓存正确率下降 | **主贡献**（版本感知簇内借用）+ **可选扩展**（伪计数平滑，不称保守上界） |
| **问题二（前半）**：活跃缓存规模受限时，如何按集合边际收益决定跨类型准入与淘汰？ | **Algorithm 2（`SetMarginalSchedule`）**：静态集合目标 $S_t(M,H)$ + 全量参照 / 有条件增量求值 + 逐轮边际密度贪心淘汰 | C2：独立净收益估值 vs. 集合边际估值；全量求值 vs. 增量求值一致性；LRU / LFU / GDSF / 调优固定配额 | **主贡献**（核心算法贡献） |
| **问题二（后半）**：外部证据更新后，如何定位单轮 `rag → resp` 影响、选择修复方式并防旧版写回？ | **Algorithm 3（`UpdateMaintenance`）**：保守重检/影响筛查 → 是否主动维护（对比按需生成）→ 局部修复 vs. 完整重生成代价路由 → 原子版本条件提交 | C3：按需生成、主动完整重生成、主动局部修复、直接改写；定向覆盖 5 类边界用例 | **主贡献**（影响筛查、代价路由与原子条件提交） |
| **扩展与工程开关** | 广义代价（时延+费用加权）、`act` 下游扇出 $d_i$ 调度偏好、`resp` 静态层/动态层（Krites 思路） | 均作为独立开关消融报告，同步汇报未加权的真实路径时间净节省 | **可选扩展**（不承担首版主创新主张，不污染主目标量纲） |

---

## 2. 可执行的数学定义与三段统一伪代码

### 2.1 信息可见性、预算口径与主优化目标

#### （1）三套信息口径严格隔离
1. **在线策略可见信息（Online Observable）**：当前请求 $q$、历史已到达请求与执行耗时记录、系统已收到的更新通知所维护的已知版本图 $\mathcal{G}_t$、旁路判官对已触发样本给出的明确标注。
2. **构造真值信息（Oracle / Ground Truth）**：题库 `cluster_id`、`gold_fact_spans`、`truth.value`、`labels/safe_reuse.jsonl` 标签，**严禁**作为任何在线策略的输入。
3. **离线评测真值（Evaluation Oracle）**：按数据外部实际生效版本 $\mathcal{G}_t^{\mathrm{true}}$ 与独立参考查询/规则判定回答正确率、安全复用率与过期误用（分别统计“已知失效后复用”与“通知前过期误用”）。

#### （2）主模型：给定状态与策略下的静态集合容量选择目标
首版不宣称联合求解动态控制问题，而是将形式化主目标限定在**给定当前系统已知版本状态 $\mathcal{G}_t$ 与在线复用规则 $\pi$，在逻辑容量预算下比较缓存组合 $M$ 的窗口累计路径时间净节省**：

$$
\Delta T(q \mid M, \pi, \mathcal{G}_t) = T_0(q) - T_\pi(q \mid M, \mathcal{G}_t), \qquad
S_t(M, H) = \sum_{q \in Q_{\mathrm{rep}}} w_q(H)\,\mathbb{E}\!\left[\Delta T(q \mid M, \pi, \mathcal{G}_t)\right]
$$

* **口径与单位**：
  - $T_0(q)$ 与 $T_\pi(q \mid M, \mathcal{G}_t)$ 在同一请求、同一可见版本 $\mathcal{G}_t$ 与评测条件下比较，单位统一为**时间（ms 或 s）**；**推理费用独立报告**（广义时间-费用加权代价仅作可选扩展，不混入主目标）。
  - $T_\pi$ 完整计入实际落在该请求路径上的缓存探测、硬有效性检查、补检、适配、返工与回退耗时（含 `resp` 未被采纳时已产生的前期开销）；当 `resp` 通过检查并返回时，未执行的中间阶段不单独记功；不假定 `plan → rag → act` 为所有请求的固定串行顺序。
  - $w_q(H)$ 为代表性请求样本 $q \in Q_{\mathrm{rep}}$ 在未来预测窗口 $H$ 内的预计请求量权重（$H$ 为估值窗口，不是 TTL）；处理随机门控时取条件期望或在成对比较中固定同组随机数。
  - 后台判官、调度与主动修复开销按其实际资源/时延口径单独核算，避免与前台路径重复扣费。
* **约束归属（修正 P0-1 错位）**：
  - **活跃逻辑容量约束**：$\sum_{i \in M_{\mathrm{budget}}} c_i \le B$，其中 `resp`/`act`/`plan` 各计 1 单位，`rag` 按所含证据块数计。**明确计费边界**：所有驻留于活跃缓存的条目（含处于“暂停待判定”状态的条目，直至恢复或清理）均计入 $M_{\mathrm{budget}}$；若启用 `resp` 静态层扩展，离线静态回答池单列静态配额，而验证后写入动态层的请求映射计入动态预算 $B$。
  - **硬有效性约束**：权限、时效、依赖版本与状态约束施加在**当前请求 $q$ 实际选用的每个条目**上，而非施加给整个驻留集合 $M$（不同租户/权限的合法条目可安全共存于 $M$ 中）。
* **难度与理论边界**：
  - 固定 $\mathcal{G}_t$ 与 $\pi$，令各候选条目服务互不重叠的请求子集、净节省为正价值、$c_i$ 为重量，该静态子问题直接包含 **0–1 背包问题**，故一般容量选择问题为 **NP-hard**。
  - 不对一般路径集合目标声称次模性或近似比保证（反例：若证据块 $A, B$ 缺一不可，单有 $B$ 无法跳过检索，有 $A$ 后再加 $B$ 才省检索，此时边际增益递增而非次模）。

#### （3）条目级估值与集合评分的分工（含 `plan` 互斥分支）
* **分工**：条目级估值仅用于离线候选初筛与启发式排序，**绝不替代** Algorithm 2 中的集合反事实差值 $S_t((M\setminus E)\cup\{i\}, H) - S_t(M, H)$。
* **`plan` 互斥分支期望模型**：设某计划模板被尝试复用时，落入三个**互斥且概率和为 1** 的分支——(A) 适配前失败（概率 $p_{\mathrm{pre}}$，净增检查与适配回退耗时 $f_{\mathrm{pre}}$）；(B) 进入执行且顺利完成（概率 $(1-p_{\mathrm{pre}})q_i$，净节省 $\Delta t_{\mathrm{ok}}$）；(C) 进入执行但中途返工或重规划（概率 $(1-p_{\mathrm{pre}})(1-q_i)$，净增返工耗时 $f_{\mathrm{rework}}$）。单次尝试的期望时间净节省为：
  $$
  \mathbb{E}[\Delta t_{\mathrm{plan}}] = (1 - p_{\mathrm{pre}})\Bigl(q_i\,\Delta t_{\mathrm{ok}} - (1 - q_i)\,f_{\mathrm{rework}}\Bigr) - p_{\mathrm{pre}}\,f_{\mathrm{pre}}
  $$
  其中 $q_i$ 的分母严格为“已进入模板执行的次数（B+C）”，与适配前失败（A）互斥，杜绝同一失败重复扣费。
* **`act` 扇出定位**：下游不同工具数 $d_i$ 仅作为需求预测特征或诊断量；不在主路径目标上乘以无量纲扇出倍率（避免虚增毫秒或放大负收益）。

---

### 2.2 三段修正后的统一伪代码

#### Algorithm 1：`OnlineReuse`（在线复用决策与经验风险门控）

> **口径声明**：本算法的概率门控 $r = \max(\varepsilon, 1 - \delta/\tilde{p}_i)$ 针对的是候选分组下**联合事件概率 $P(\mathrm{Reuse}\cap\mathrm{Err})$ 的经验点估计**，**不控制条件错误率 $P(\mathrm{Err}\mid\mathrm{Reuse})$，也不提供实际误用率 $\le \delta$ 的理论保证**。伪计数平滑 $(\alpha_0, \beta_0)$ 称为**带伪计数平滑的经验风险估计**（$\alpha_0=\beta_0=0$ 时退化为无平滑版），在 C1 中与无平滑版对照验证。

```text
Algorithm 1: OnlineReuse(q, M, G_t, δ, ε, N_min, α_0, β_0, rng)
Input : 请求 q；缓存集合 M；系统已知版本图 G_t；门控参数 δ, ε, N_min；可选平滑 (α_0, β_0)；随机数源 rng
Output: 回答 y；本次实际执行路径轨迹 trace

1:  // 1) 优先尝试精确匹配 resp；若复核失败不提前返回，继续走后续流程
2:  c_exact ← LookupExactResp(M, q)
3:  if c_exact ≠ ∅ and not c_exact.suspended and HardValid(c_exact, q, G_t) then
4:      if ReCheckVersionBeforeUse(c_exact, G_t) then
5:          return (c_exact.resp, TraceExactHit(c_exact))
6:
7:  // 2) 语义召回 resp 候选（硬检查不通过的候选不进入风险标注与门控）
8:  c_sem ← Top1SemanticResp(M, q)
9:  valid_sem ← (c_sem ≠ ∅ and not c_sem.suspended and HardValid(c_sem, q, G_t))
10: if valid_sem then
11:     b ← SimBucket(sim(q, c_sem))
12:     (e_i, n_i, p_c, m) ← FetchCompatFeedback(c_sem, b, q.perm, G_t)
13:         // 仅借用同簇、同桶 b、权限相容、相关证据版本一致的近期明确标注；m ≤ m_max
14:     if n_i + m ≥ N_min then
15:         p_tilde ← (e_i + m * p_c + α_0) / (n_i + m + α_0 + β_0)
16:         r ← ε if p_tilde ≤ δ else max(ε, 1 - δ / p_tilde)
17:         if rng.uniform(0, 1) > r and ReCheckVersionBeforeUse(c_sem, G_t) then
18:             return (c_sem.resp, TraceSemHit(c_sem))
19:
20: // 3) resp 未复用：仅执行当前请求 q 实际需要的阶段，按需复用 plan / rag / act
21: (y, new_objs, trace) ← ExecuteRequiredPath(q, M, G_t)
22:     // 内部对所需对象逐一查缓存 + HardValid + 使用前复核 G_t；失败回退计入 trace
23:
24: // 4) 旁路异步判官（不阻塞响应）与准入提交
25: if valid_sem then
26:     AsyncJudge(q, c_sem, c_sem.version, EvidenceAt(G_t), y)
27:         // 依据候选版本与当时证据独立判定；无法判定样本不计入明确标注 (e_i, n_i)
28: for each obj in new_objs do
29:     SetMarginalSchedule(obj, M, B, Q_rep, G_t)   // 调用 Algorithm 2
30: return (y, trace)
```

---

#### Algorithm 2：`SetMarginalSchedule`（集合边际准入与逐轮边际密度淘汰）

> **求值与等价性声明**：以全量参照求值 `EvalDeltaFull` 为精确定义；仅当局部集合 $Q_{\mathrm{aff}}(i, E)$ 满足**完备可达超集条件**（保证对任意 $q \in Q_{\mathrm{rep}} \setminus Q_{\mathrm{aff}}$，其期望路径差 $\Delta T(q \mid M') - \Delta T(q \mid M) = 0$，完整覆盖跨簇召回、备用候选接替、删 `resp` 后暴露的中间阶段及索引排序变动）时，增量求值才与全量等价。若无法证明完备，则默认回退全量求值，或显式标记为**近似增量模式**并在 C2 中报告误差与替换分歧率。

```text
Algorithm 2: SetMarginalSchedule(i, M, B, Q_rep, G_t, mode)
Input : 候选条目 i（占用 c_i）；当前缓存 M（含暂停条目）；预算 B；代表性窗口 Q_rep；已知版本图 G_t；mode ∈ {EXACT_FULL, PROVABLE_INC, APPROX_INC}
Output: 更新后的缓存集合 M；布尔值 accepted

1:  // 1) 单条目合法性与预算底线检查
2:  if c_i > B or not EntryAdmissible(i, G_t) then
3:      return (M, False)
4:
5:  // 2) 优先清理已确认失效且无需维护的条目（构建临时集合，暂不提交修改）
6:  E_dead ← { j ∈ M : j.confirmed_dead }
7:  M_work ← M \ E_dead
8:  E_evict ← ∅
9:
10: // 3) 空间不足时：逐轮重算边际损失的贪心淘汰（处理互为替代条目）
11: while UsedBudget(M_work) + c_i > B do
12:     // 逐轮在当前剩余集合 M_work 上评估移除单条 j 的边际损失（而非静态一次排序）
13:     for each j ∈ M_work do
14:         loss_j ← EvalRemoveLoss(j, M_work, Q_rep, G_t, mode)
15:     j_star ← argmin_{j ∈ M_work} (loss_j / c_j)
16:     E_evict ← E_evict ∪ { j_star }
17:     M_work ← M_work \ { j_star }
18:
19: // 4) 比较替换前后的完整集合目标差 ΔS
20: E_total ← E_dead ∪ E_evict
21: M_cand ← (M \ E_total) ∪ { i }
22: if mode == EXACT_FULL then
23:     ΔS ← S_t(M_cand, Q_rep, H) - S_t(M, Q_rep, H)
24: else
25:     Q_aff ← ReachableSuperset(Q_rep, i, E_total, M, G_t, mode)
26:         // 若 mode==PROVABLE_INC 且无法保证覆盖跨簇/备用接替/索引变动，自动回退 Q_rep
27:     ΔS ← S_t(M_cand, Q_aff, H) - S_t(M, Q_aff, H)
28:
29: // 5) 原子替换：仅当 ΔS > 0 且满足预算时提交；拒绝时不误删 E_evict
30: if ΔS > 0 and UsedBudget(M_cand) ≤ B then
31:     AtomicReplace(M, remove=E_total, add=i)
32:     return (M_cand, True)
33: else
34:     if E_dead ≠ ∅ then AtomicRemove(M, E_dead)   // 仅清理已确认死条目，保留 E_evict
35:     return (M \ E_dead, False)
```

* **复杂度分解（诚实拆项，不泛称单一大 O）**：单次调用开销由四部分组成——① 候选与倒排索引维护开销 $T_{\mathrm{idx}}$；② 受影响请求集合查找开销 $T_{\mathrm{lookup}}$；③ 单次路径重放成本 $T_{\mathrm{eval}}(|Q|)$；④ 若淘汰 $|E_{\mathrm{evict}}|$ 条条目，逐轮重算边际损失的循环开销（可通过缓存未受上一轮删除影响的条目损失做局部增量刷新，并在 C2 中与静态一次排序及全量参照实测对比）。

---

#### Algorithm 3：`UpdateMaintenance`（三阶段解耦更新维护与原子版本条件提交）

> **核心解耦原则**：严格拆开 **(1) 是否受影响（含新入 Top-k 筛查）→ (2) 是否值得主动维护（对比“按需生成”基线，绝不用低价值直接删除未变有效回答）→ (3) 怎样修（全主张核验 + 失败回退 + 原子事务提交）**。

```text
Algorithm 3: UpdateMaintenance(u, M, B, Q_rep, G_t)
Input : 外部更新事件 u（新增/修改/删除文档或索引切换）；缓存集合 M；预算 B；Q_rep；已知版本图 G_t
Output: 更新后的缓存集合 M 与版本图 G_t

1:  // 阶段 1：更新已知版本图，并按更新类型确定需筛查的 resp 集合 A
2:  ApplyUpdateToGraph(G_t, u)
3:  if u.can_enter_topk then
4:      // 新增文档、修改旧结果集外文档或索引切换：保守覆盖可能受影响查询范围（防漏检）
5:      A ← CandidateQueriesByDomainOrAllResp(M, u)
6:  else
7:      // 仅已有依赖删除/局部数值修改且不改变外部文档排序：反向索引精准定位
8:      A ← ReverseIndexLookupResp(M, G_t, u)
9:  SuspendReuse(A)   // 暂停 A 中未判定条目的在线复用（暂停期间仍占预算）
10:
11: for each i ∈ A do
12:     v_snap ← SnapshotVersion(G_t, i)
13:
14:     // 阶段 2：确定性重检以确认“是否真正受影响”（低价值绝不替代影响判断）
15:     (new_topk, diff_evidence) ← DeterministicReRetrieve(i.query, v_snap)
16:     if EvidenceAndBasisUnchanged(i, new_topk, diff_evidence) then
17:         // 仅在版本仍一致时条件恢复并立即结束当条处理；否则按新快照重试
18:         if AtomicResumeIfVersionMatch(i, v_snap, G_t) then
19:             continue
20:         else
21:             EnqueueRetry(i); continue
22:
23:     // 至此已确认条目 i 依赖失效，标记为失效态
24:     MarkConfirmedInvalid(i)
25:
26:     // 阶段 3：决策“是否值得主动维护”（对比基线：保持失效，下次请求按需生成并重新准入）
27:     ΔGain_proactive ← EstProactiveNetBenefit(i, M, Q_rep, G_t)
28:     (mode_repair, E_cost_repair) ← SelectRepairRoute(i, diff_evidence, G_t)
29:         // 内部先检可定位性与证据充分性（ρ_i 仅作特征）；
30:         // 比较 E[C_local] = C_revise + C_verify + p_fb * C_fallback 与 C_full（共同开销只计一次）
31:     if ΔGain_proactive ≤ E_cost_repair then
32:         // 不值得主动修：释放其无效占位，留待下次请求按需生成
33:         AtomicDropInvalid(M, i)
34:         continue
35:
36:     // 阶段 4：执行修复 + 全主张核验 + 失败回退
37:     if mode_repair == LOCAL_REPAIR then
38:         y_cand ← LocalRepair(i, diff_evidence, new_topk)
39:         ok ← VerifyAllClaims(y_cand, new_topk)   // 核验修改及保留的全部主张
40:         if not ok then
41:             y_cand ← FullRegenerate(i.query, new_topk)
42:             ok ← VerifyAllClaims(y_cand, new_topk)
43:     else
44:         y_cand ← FullRegenerate(i.query, new_topk)
45:         ok ← VerifyAllClaims(y_cand, new_topk)
46:
47:     if not ok then
48:         AtomicDropInvalid(M, i); continue   // 仍未通过核验，不入缓存
49:
50:     // 阶段 5：同一原子事务完成“版本校验 + Alg.2 准入淘汰 + 依赖索引与缓存写入”
51:     new_entry ← BuildEntry(y_cand, new_topk, v_snap)
52:     status ← AtomicCommitWithVersionAndBudget(new_entry, old=i, v_snap, M, B, Q_rep, G_t)
53:         // 事务内部：先验证 G_t.ver == v_snap；若不匹配则中止事务（不执行任何淘汰与写入），返回 STALE；
54:         // 若匹配则运行 Alg.2 决定准入/替换，并原子写入新条目与依赖反向索引。
55:     if status == STALE then
56:         EnqueueRetry(i)
```

---

## 3. 七个指定反例的逐条推演回放

| 编号 | 反例场景 | 触发的精确分支 | 应观察到的输出与行为 | 算法成立所需的显式假设 |
| :--- | :--- | :--- | :--- | :--- |
| **CE-1** | 候选分组真实错误率 $p=20\%$，设 $\delta=1\%, \varepsilon=5\%$；以及 $e_i=0, N_{\min}=100, \mathrm{Beta}(1,1)$ | Alg.1 L14–18：$r = \max(0.05, 1 - 0.01/0.20) = 0.95$（放行 $5\%$）；零错误平滑后 $\tilde{p}_i = 1/102 \approx 0.98\% \le 1\%$，取 $r = \varepsilon = 5\%$ | 第一例中**全请求联合误用为 $1\%$**，但**已复用回答中的条件误用率仍为 $20\%$**；第二例平滑不会自动提高重生成率。系统**不宣称**控制条件误用率，三口径分开报告 | 仅在把 $\delta$ 定义为分组内联合风险点估计目标、并以独立真值在 C1 实测检验时表述成立；若需条件风险上界须另行设计置信上界规则 |
| **CE-2** | 簇 A 新回答 $i$ 能被簇 B 请求 $q_B$ 语义召回，使 $q_B$ 耗时从 100 降至 20（真实增量 80） | Alg.2 L22–27：若 `mode=EXACT_FULL` 或 `PROVABLE_INC`（无法证明仅同簇完备，自动回退 `Q_rep` 或使用跨簇相似度超集），覆盖 $q_B$ | 精确算出 $\Delta S$ 包含 80 的增益；若强行跑“仅同簇” `APPROX_INC`，则漏算 80 并在 C2 一致性审计中显式记为误差/错过替换 | 增量求值精确等价的充要条件是 $Q_{\mathrm{aff}}$ 为真实可达超集（覆盖跨簇召回、备用接替与中间阶段暴露） |
| **CE-3** | 两条互为替代的条目 $a, b$ 覆盖同一段耗时 10 的工作，需腾出 2 单位空间 | Alg.2 L11–17：第 1 轮单删 $a$ 或 $b$ 的损失均为 0，选删 $a$；第 2 轮在剩余集合 $M_{\mathrm{work}}\setminus\{a\}$ 上**重算**删 $b$ 的损失，此时损失升为 10 | 逐轮重算能准确识别第 2 条删 $b$ 的真实代价为 10，避免像静态单次排序那样误以为连删 $a, b$ 总损失为 0 | 需要 `while` 循环内每轮基于更新后的 `M_work` 刷新受影响条目损失；若改静态单次排序须诚实标注为近似启发式 |
| **CE-4** | 原 Top-1 为旧文档 D1；新文档 D2 到来并超越 D1 成为新 Top-1（旧回答无指向 D2 的边） | Alg.3 L3–5：`u.can_enter_topk == True`，走保守筛查集合 $A$ 并暂停复用 $\rightarrow$ L15 确定性重检发现 `new_topk` 变为含 D2 | 旧回答被成功捕获并标记失效，不会因为旧反向索引返回空集而漏检 | 依赖更新事件正确标注 `can_enter_topk`（新增/修改非引用文档/索引切换一律置 True）以及确定性重检覆盖相应查询域 |
| **CE-5** | 局部修复尝试成本 60、核验失败（$p_{\mathrm{fb}}=50\%$），回退完整重生成成本 100 | Alg.3 L28–30 先算局部期望代价 $60 + 0.5\times 100 = 110 > 100$，直接路由 `FULL_REGEN`；若实际走了 `LOCAL_REPAIR` 且 L39 `VerifyAllClaims` 返回 False，则走 L40–42 回退完整重生成 | 若事前预测准确则直接短路走完整重生成省去 60；若进入局部修复后核验失败，则回退完整重生成并**把首次局部尝试与回退重生成成本合并计入总修复成本** | 事前路由依赖 $\hat{p}_{\mathrm{fb}}$ 估计的合理性；事后兜底依赖 `VerifyAllClaims` 核验修改及保留的全部主张 |
| **CE-6** | 修复进行期间（L37–48）收到针对同一依赖的第二次更新 $u_2$ | Alg.3 L52–56：`AtomicCommitWithVersionAndBudget` 检测到 `G_t.ver != v_snap`，立即中止事务并返回 `STALE` $\rightarrow$ L56 入队重试 | 旧候选被丢弃，**不执行任何容量淘汰与缓存写入**，旧回答继续保持暂停不可复用，按新版本重新定位 | 依赖原子事务保证版本检查、容量变更、索引与缓存写入不可分割；保证范围限定于**系统已收到通知的版本** |
| **CE-7** | 低热度回答 $i$ 因某文档更新被纳入待筛查集合 $A$，但重检后发现其 Top-k 证据与回答依据均未变化 | Alg.3 L15–19：`EvidenceAndBasisUnchanged` 为 True $\rightarrow$ L18 `AtomicResumeIfVersionMatch` 恢复复用并 `continue` 退出 | 有效回答被保留并恢复复用，**不会因为“低热度/低价值”被提前误删**，避免了不必要重算 | 严格执行“先确定性确认受影响，再对已确认失效条目评估是否主动维护”的先后顺序 |

---

## 4. 实验改动清单（基于仓库真实状态，不宣称“100% 兼容”）

> **仓库真实标定状态对齐**：以当前仓库文件为准——`dataset/events/real_calibration_300.csv` 已包含 300 行阶段计时与 Token 计数（需先同步替换 `exp_motivation/data/real_calibration_300.csv` 中仅含 `t_act_ms` 的旧副本）；`dataset/costs/path_costs.csv` 中 `partial_repair/rewrite` 当前注明取自 **`plan` 的 P50 代理值**，**不能直接充当局部修复实测**；`dataset/labels/safe_reuse.jsonl` 当前未覆盖“外部已生效但系统未收到通知”的延迟窗口负例。

| 实验 | 可复用输入 | 必须新增的对照或定向用例 | 待标定路径 | 本实验台无法验证的主张（须诚实申明） |
| :--- | :--- | :--- | :--- | :--- |
| **动机实验 / 图 1-1** | `request_stream.jsonl`、`update_events.jsonl`、`docs_versioned.jsonl`、`real_calibration_300.csv`（同步后） | (a) 拆开重复机会、实际采用与路径净节省；(b) 同容量/同替换规则下比固定 TTL 与版本感知；(c) 同一缓存状态、同一“更新×回答”单位下比文档级失效与主张级真实影响 | 缓存读取、硬校验、补检、适配及失败回退的真实耗时配对 | 阶段耗时占比不能直接等同应用层净节省；不含真实生产并发排队效应 |
| **C1（当前复用）** | 主请求流、更新流、独立评测真值 | 固定召回/硬检查/判官，增设**簇借用开关**与**伪计数平滑开关**对照；按实测事件密度确定更新后窗口（不硬写“500 请求”）；禁用题库 `cluster_id` 作为在线分簇真值 | 实际语义召回、LLM 分簇（若启用）与旁路判官调用的真实时延与费用 | 不验证实际误用率 $\le \delta$ 的理论保证；不用题库预设簇号证明 LLM 分簇精度 |
| **C2（准入淘汰）** | 主基准与 `long_01,02.jsonl` 长流；LRU/LFU/GDSF 基线 | 同预算同前置规则下新增：**独立净收益估值 vs. 集合边际估值**、**全量求值 vs. 增量求值一致率与误差**、**静态单次排序 vs. 逐轮重算损失**、**调优固定配额基线**；若保留静态层/`act` 扇出，加独立开关对照 | 集合重放、倒排索引维护与受影响查找的真实调度耗时；若讨论逻辑规模对检索时延影响，需单独测索引规模-延迟曲线 | 主逻辑容量不等价于物理字节存储开销；不声称在线启发式具备理论近似比 |
| **C3（更新维护）** | 40 次更新事件（含 6 条 `codebook_revision` 负对照）及补充更新率流 | 基线必须包含**按需生成**、主动完整重生成、主动局部修复、直接改写；必跑 **5 个定向用例**：旧依赖删改、**新证据入 Top-k**、无关更新、局部核验失败回退、修复期间连续两次更新 | **必须补配对实测**：真实局部改写、完整重生成、全主张核验与失败回退的时延与 Token（替换原 `plan` P50 代理行） | `events/README` 的 ~73% 低主张比例不是修复成功率；同事件下多条回答不可当独立样本 |
| **C4（系统整体）** | 主基准混合流、无缓存基线、关键消融项 | 新增**强组合基线**：支持四类对象、具相同硬检查、用独立净收益保留、失效后按需生成的完整组合；分别报告前台净时间节省、P95、总推理费用（含后台判官与修复）及 goodput | 全链路后台维护与判官调用的统一计费与耗时汇总 | 无排队论与后台资源竞争建模时，goodput 仅解释为给定到达流下满足质量与 SLO 的请求速率，不解释为服务吞吐上限；通知前过期窗口若未补边界用例，不用零违规推断无风险 |

---

## 5. 后续正文修改顺序（待本蓝图通过 Codex 复审后执行）

1. **先跑定向反例单元测试与关键路径补标定**（尤其是 C3 局部修复/核验实测与 Alg.2 全量 vs. 增量一致率检验），确认无机制假设落空；
2. 再按本蓝图依次更新 `第一章_改后初稿_第二版.md` 的 **1.2.1（主目标与定义）→ 1.2.2–1.2.3（Alg.1）→ 1.3.1–1.3.2（Alg.2/3 与更新后流程图）→ 1.4（对照与标定状态对齐）→ 导语与 1.5（同步收束）**；
3. 严守已定稿的 **1.0 节、1.1 节及参考文献 `[1]–[35]`** 零破坏。

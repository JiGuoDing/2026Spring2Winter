# 第一章异质缓存设计方案定型蓝图（v5 · 设计封版）

> **封版声明**：本版（`v5`）为第一章算法设计的**正式封版定型稿**，用于直接指导小规模原型代码实现、动机实验与 C1–C4 实验评估。**到此停止纯纸面蓝图迭代**；待原型跑通核心定向单测并产出真实实验数据后，再依据本版与实测结果一次性修订论文 §1.2–§1.4 正文。

---

## 0. 科研主线守则与本轮讨论核心结论（防偏离红线）

> **时刻提醒（面向所有后续执行 Agent 与改稿环节）**：本课题是**流式智能体应用层异质缓存策略与生命周期管理**的学术研究（1.4 节采用单机顺序事件回放器评测，不涉及分布式在线引擎部署）。**绝不能把算法策略论文写成高并发分布式数据库 MVCC 事务内核说明书**，以免淹没核心科研创新，重蹈“像代码技术文档、不像科研论文”的覆辙。

### 0.1 本章不可偏离的三大科研主线
1. **四类异质对象的专属价值建模与路径级集合边际调度**：四类固定分池（`resp`/`rag`/`act`/`plan`）各自保留专属价值特征，通过上游 `resp` 短路联动下游残余需求，在同类子池内按完整路径之差与候选感知淘汰解决跨类型重复计费和语义覆盖冗余。
2. **版本感知的簇内反馈借用与经验风险门控**：在外部更新导致的稀疏反馈期，借用同簇同版本兼容标注加速新版本有效命中恢复。
3. **单轮 `rag → resp` 细粒度依赖维护与选择性局部修复**：在确定性重检基础上，区分未变恢复、按需生成与主动局部修复，结合在线双检核验与版本条件提交控制演化期成本与一致性。

### 0.2 对 Codex v4 审阅意见的“两刀切”采纳结论
* **坚决采纳的 3 个真洞见（直接提升算法与实验严密性，几乎零复杂度成本）**：
  1. **基准对齐（P0-1）**：准入比较 `EvalDelta(M_yes, M_no)` 必须拿“接纳候选后的状态 `M_yes`”与“**同样清完已确认死条目后的不接纳状态 `M_no`**”对比，避免把清理死条目的收益误算给新候选；修复写回时将旧条目提前作为必移除项传入规划，不在评分后追加删除。
  2. **快照冻结与总账防重（P0-2）**：成对比较冻结同一批 `Q_rep`、权重、其余三池状态与随机数，约定 `EvalDelta(after, before)` 正数代表节省；各池边际仅用于类内决策，C4 系统总收益按每条请求的完整路径严格只计一次。
  3. **在线信息隔离（P1-2）**：`DualVerify` 的必答完整性检查只能从**请求显式要求的实体、字段和时间范围**结合当前可见证据提取，严禁读取题库 `gold_fact_spans` 或任何评测真值。
* **果断砍掉的 3 类过度并发工程设计（防止论文 toxic 化）**：
  1. **不引入多版本并发锁状态机**：在模型层显式声明**顺序事件处理语义**（与 1.4 节离线回放器完全一致）——每个请求或更新事件按到达顺序原子推进状态；修复写回仅保留简洁的**单版本条件提交（校验 `doc_version`）**，不再引入 `(entry_id, entry_gen, update_epoch, pool_rev)` 四层并发代次与域屏障关闭状态机。
  2. **不设计分布式并发预算预留协议**：主动维护的后台预算在首版采用简单的**每窗调用次数 / Token 上限**即可，不在论文中展开并发预留-结算锁机制。
  3. **不陷入微秒级异步入队锁开销拆分**：前台计时按实际发生路径记录，后台判官与维护开销按模型调用/检索口径独立统计并汇总入总成本。

---

## 1. 架构定型：四类固定分池 + 路径联动

* **固定分池与预算口径**：缓存划分为四个独立子池 $M = (M_{\mathrm{resp}}, M_{\mathrm{rag}}, M_{\mathrm{act}}, M_{\mathrm{plan}})$，对应预先给定的活跃逻辑索引预算向量 $(B_{\mathrm{resp}}, B_{\mathrm{rag}}, B_{\mathrm{act}}, B_{\mathrm{plan}})$（`resp`/`act`/`plan` 按条目计，`rag` 按证据块计；暂停条目在恢复或清理前计入所在子池预算）。**本文不优化池间配额分配，不同种类对象之间不直接比较大小**（正文相应表述将统一修正为“池内集合边际调度 + 跨池路径联动”）。
* **跨池联动与总账边界**：`resp` 短路会直接改变下游中间阶段的实际到达需求；各池内部估值均基于包含其余三池在内的完整请求路径计算，但各池边际仅用于池内准入淘汰决策，**不将四池边际简单相加**；C4 端到端系统总收益按每条请求的完整实际路径只计一次。
* **可选扩展归位**：广义时延-费用加权代价、`resp` 静态层双层提升（Krites 思路）、伪计数平滑与 `act` 扇出排序偏好均作为可选开关扩展，不承担首版主创新主张，不污染主模型时间量纲。

---

## 2. 主目标、只读路径求值器与四类子池专属建模

### 2.1 冻结状态主目标与 `EvalDelta` 规范
首版主目标**冻结当前系统已知版本状态 $\mathcal{G}_t$**（窗口 $H$ 仅用于预测请求量权重 $w_q(H)$；推理费用独立报告；外部真实生效版本 $\mathcal{G}_t^{\mathrm{true}}$ 仅用于离线评测）。给定代表性请求集 $Q_{\mathrm{rep}}$ 与固定在线策略 $\pi$，一次成对比较冻结同一批 `Q_rep`、权重、其余三池状态、反馈与成对随机数，定义：

$$
\Delta T(q \mid M, \pi, \mathcal{G}_t) = T_0(q) - T_\pi(q \mid M, \mathcal{G}_t), \qquad
S_t(M, H) = \sum_{q \in Q_{\mathrm{rep}}} w_q(H)\,\mathbb{E}\!\left[\Delta T(q \mid M, \pi, \mathcal{G}_t)\right]
$$

* **统一差值符号**：`EvalDelta(M_after, M_before)` 定义为各请求“变更前前台耗时 $-$ 变更后前台耗时”的加权期望（即 $S_t(M_{\mathrm{after}}, H) - S_t(M_{\mathrm{before}}, H)$），**正数代表时间净节省**；按同一口径，移除条目 $j$ 的边际损失为 `EvalDelta(M_work, M_work \ {j})`。
* **只读路径求值器 `EvalPath`**：在临时集合视图上只读重放召回、校验、短路与回退（不修改任何在线状态），输出 `(path_taken, fg_time_ms, cost_source, resolvable)`。被 `resp` 跳过的中间阶段不单独记功；未执行备选路径的耗时必须来自配对标定、可重放阶段或显式估计，缺数时返回 `UNRESOLVABLE` 并跳过该次准入，**绝不默认为 0**。
* **全量参照与理论边界**：首版以在完整 `Q_rep` 上求和作为参照（不依赖未经证明完备的局部剪枝；若后续做增量剪枝，仅当可证明集外请求成对时差为零时等价，否则标为近似并报误差）。固定版本与策略时，静态容量选择包含 **0–1 背包**（NP-hard）；因互补证据块可破坏次模性，**不对在线启发式声称近似比保证**。

### 2.2 四类子池各自的专属价值建模（同类只跟同类比）
1. **`resp` 子池（集合边际覆盖价值）**：基于在线观测特征分簇（严禁读取题库 `cluster_id`），簇预计请求量按代表样本数均分权重（如 100 次 / 5 样本 = 各 20）；仅当加入条目不改变实际路径分布与前台成本时，边际收益才为零。
2. **`rag` 子池（来源版本感知的证据覆盖价值）**：在冻结的当前已知版本 $\mathcal{G}_t$ 下，按请求所需证据覆盖情况回放**免检索 / 补检 / 回退完整检索**三种路径（区分无候选与探测后回退，不靠单来源边际存活率硬推联合有效率）。
3. **`plan` 子池（互斥三分支执行质量模型）**：按相对正常从头规划的有符号时差划分为三个互斥穷尽分支——(A) 未进入模板执行（含适配失败，概率 $p_{\mathrm{pre}}$，时差 $-f_{\mathrm{pre}}$）；(B) 进入执行顺利完成（概率 $(1-p_{\mathrm{pre}})q_i$，时差 $\Delta t_{\mathrm{ok}}$）；(C) 进入执行发生返工/超时（概率 $(1-p_{\mathrm{pre}})(1-q_i)$，时差 $\Delta t_{\mathrm{rework}}$）；$q_i$ 分母严格为进入执行次数（B+C），无返工但答错单列质量指标。
4. **`act` 子池（只读状态依赖 + 下游扇出 $d_i$ 特征）**：限只读调用、调用签名精确匹配，区分固定快照与最新状态调用；下游扇出 $d_i$ 作为类内需求/排序特征独立做消融检验，不乘到毫秒收益上、不跨类比较。

---

## 3. 清爽版三段核心算法伪代码（顺序事件语义）

### Algorithm 1：`OnlineReuse`（在线复用与版本感知簇借用门控）

> **口径声明**：随机门控 $r=\max(\varepsilon, 1-\delta/\tilde{p}_i)$ 针对的是该候选分组内的**联合误用概率点估计**（如分组内 1% × 分组占比 40% = 全流贡献 0.4%），不控制条件错误率，不作风险上界保证；分别报告全流误复用率、复用中误用率与相对无缓存正确率变化。

```text
Algorithm 1: OnlineReuse(q, M, G_t, δ, ε, N_min, α_0, β_0, rng)
1:  // 1) 精确匹配 resp；复核失败不提前退出，继续向下
2:  c_exact ← LookupExactResp(M.resp, q)
3:  if c_exact ≠ ∅ and not c_exact.suspended and HardValid(c_exact, q, G_t) then
4:      return (c_exact.resp, TraceExactHit(c_exact))
5:
6:  // 2) 语义召回 resp（硬校验或暂停未通过者不进风险标注）
7:  c_sem ← Top1SemanticResp(M.resp, q)
8:  valid_sem ← (c_sem ≠ ∅ and not c_sem.suspended and HardValid(c_sem, q, G_t))
9:  if valid_sem then
10:     b ← SimBucket(sim(q, c_sem))
11:     (e_i, n_i, p_c, m) ← FetchCompatFeedback(c_sem, b, q.perm, q.time_window, G_t)
12:         // 仅借用同簇、同桶、权限与时间窗相容、证据版本一致的近期明确标注；m ≤ m_max
13:     if n_i + m ≥ N_min then
14:         p_tilde ← (e_i + m * p_c + α_0) / (n_i + m + α_0 + β_0)
15:         r ← ε if p_tilde ≤ δ else max(ε, 1 - δ / p_tilde)
16:         if rng.uniform(0, 1) > r then
17:             return (c_sem.resp, TraceSemHit(c_sem))
18:
19: // 3) 未复用 resp：仅执行 q 实际需要的阶段，按需复用 plan / rag / act 子池
20: (y, new_objs, trace) ← ExecuteRequiredPath(q, M, G_t)
21:
22: // 4) 旁路判官（绑定不可变候选与当时证据快照）与后置准入调度
23: if valid_sem then
24:     RecordJudgeFeedback(q, SnapshotPayload(c_sem), EvidenceAt(G_t))
25:         // 区分版本不相容与语义答错；无法判定不记入明确标注
26: for each (pool_k, obj) in new_objs do
27:     SetMarginalSchedule(pool_k, obj, forced_remove=∅, M, B[pool_k], Q_rep, G_t, rng)
28: return (y, trace)
```

---

### Algorithm 2：`SetMarginalSchedule`（同条件基准 + 候选感知逐轮淘汰）

> **核心修正（采纳 P0-1 & P0-2 & 18→19）**：① 明确定义同条件基准 `M_no`（清理已确认死条目后的状态）与接纳状态 `M_yes`（含新候选与必移除项 `forced_remove`），用 `EvalDelta(M_yes, M_no) > 0` 判定，彻底避免把清理收益记给候选或评分后再追加删除；② 候选感知逐轮淘汰解决 18→19 直接替代反例。

```text
Algorithm 2: SetMarginalSchedule(pool_k, i, forced_remove, M, B_k, Q_rep, G_t, rng)
Input : 目标子池 pool_k；新候选 i（占用 c_i）；必移除项 forced_remove（修复写回时为旧条目）；当前缓存 M；预算 B_k
Output: 布尔值 accepted

1:  if c_i > B_k or not EntryAdmissible(i, G_t) then return False
2:
3:  // 1) 构造同条件不接纳基准 M_no（先清理已确认失效的死条目）
4:  E_dead ← { j ∈ M[pool_k] : j.confirmed_dead }
5:  M_no ← M[pool_k] \ E_dead
6:
7:  // 2) 构造接纳临时集 M_yes：纳入并保护候选 i，提前移除 E_dead 与 forced_remove
8:  M_yes ← (M_no \ forced_remove) ∪ { i }
9:  while UsedBudget(M_yes) > B_k do
10:     best_j ← None; best_density ← +∞
11:     for each j ∈ M_yes \ { i } do
12:         // 冻结同一 Q_rep、其余三池状态与 rng，计算移除 j 的边际损失
13:         (loss_j, ok) ← EvalDelta(M_yes, M_yes \ { j }, Q_rep, M, G_t, rng)
14:         if not ok then ApplyDeadClean(M, pool_k, E_dead); return False
15:         if (loss_j / c_j) < best_density then
16:             best_density ← loss_j / c_j; best_j ← j
17:     M_yes ← M_yes \ { best_j }
18:
19: // 3) 同条件比较接纳与不接纳的完整路径差 ΔS
20: (ΔS, ok) ← EvalDelta(M_yes, M_no, Q_rep, M, G_t, rng)
21: if ok and ΔS > 0 and UsedBudget(M_yes) ≤ B_k then
22:     M[pool_k] ← M_yes; UpdateDependencyIndex(pool_k, M_yes)
23:     return True
24: else
25:     ApplyDeadClean(M, pool_k, E_dead)   // 仅清理死条目，绝不误删有效邻居
26:     return False
```

---

### Algorithm 3：`UpdateMaintenance`（保守重检、在线双检核验与单版本条件提交）

> **核心收束（采纳 P0-1/P0-4/P1-2，卸掉并发锁包袱）**：在顺序事件处理语义下，更新到达即同步推进 $\mathcal{G}_t$ 并暂停待筛查范围；未变直接恢复；确认失效后按热度门槛与简单窗口限额决定是否主动修；`DualVerify` 仅从请求显式实体/字段/时间范围提取必答项（不碰题库金标）；提交时传入旧条目作为 `forced_remove` 并核对 `doc_version` 一致。

```text
Algorithm 3: UpdateMaintenance(u, M, B_resp, Q_rep, G_t, hot_thresh, win_limit, rng)
1:  // 阶段 1：推进已知版本图并确定筛查范围（检索打分不能证对无关文档不变时走安全域保守重检）
2:  ApplyUpdate(G_t, u); v_cur ← G_t.ver
3:  if RetrieverScoreInvariantToUnrelatedDocs(u) then
4:      A ← ReverseIndexLookupResp(M.resp, G_t, u)
5:  else
6:      A ← SafeDomainOrAllResp(M.resp, u)
7:  SuspendReuse(A)
8:
9:  for each i ∈ A do
10:     // 阶段 2：确定性重检确认是否受影响（绝不因低热度误删未变有效缓存）
11:     (new_topk, diff_ev) ← DeterministicReRetrieve(i.query, v_cur)
12:     if EvidenceAndBasisUnchanged(i, new_topk, diff_ev) then
13:         ResumeAndRefreshMeta(i, new_topk, v_cur)
14:         continue
15:
16:     MarkConfirmedInvalid(i)
17:
18:     // 阶段 3：是否主动维护（对照按需生成并准入基线；采用热度门槛 + 窗口调用/Token 上限）
19:     if EstHeat(i, Q_rep) < hot_thresh or win_limit.exceeded() then
20:         DropInvalid(M.resp, i); continue
21:
22:     // 阶段 4：选择性局部修复 vs. 完整重生成 + 在线双检核验
23:     req_items ← ExtractOnlineRequiredItems(i.query, new_topk)   // 仅用请求显式实体/字段/时间窗，禁读金标
24:     route ← SelectRepairRoute(i, diff_ev, new_topk)
25:         // 比较 E[C_local] = C_revise + C_verify + p_fb * (C_regen + C_verify) 与 C_regen + C_verify
26:     if route == LOCAL_REPAIR then
27:         y_cand ← LocalRepair(i, diff_ev, new_topk)
28:         ok ← DualVerify(y_cand, req_items, new_topk)    // 忠实性 ∧ 必答完整性双检
29:         if not ok then
30:             y_cand ← FullRegenerate(i.query, new_topk)
31:             ok ← DualVerify(y_cand, req_items, new_topk)    // 计入二次核验成本
32:     else
33:         y_cand ← FullRegenerate(i.query, new_topk)
34:         ok ← DualVerify(y_cand, req_items, new_topk)
35:
36:     if not ok then DropInvalid(M.resp, i); continue
37:
38:     // 阶段 5：单版本条件提交 + 传入旧条目 i 作为 forced_remove 统一走 Alg.2 准入
39:     if G_t.ver ≠ v_cur then DropInvalid(M.resp, i); continue   // 版本已变则丢弃旧候选
40:     new_entry ← BuildEntry(y_cand, new_topk, v_cur)
41:     ok_admit ← SetMarginalSchedule(resp, new_entry, forced_remove={i}, M, B_resp, Q_rep, G_t, rng)
42:     if not ok_admit then DropInvalid(M.resp, i)
```

---

## 4. 下一步直接进原型：5 项精简定向单测与实验落地要点

### 4.1 原型优先跑通的 5 个核心定向单测
1. **同条件基准与强制替换（P0-1）**：105 / 100 / 102 ms 用例只清理死条目、拒绝候选；18→19 候选感知替换成功；修复写回传入 `forced_remove={i}` 后不误删有效邻居。
2. **完整路径求值与缺数回退（P0-2）**：删 20 ms 命中 `resp` 后，准确区分 35 ms 中间缓存路径与 100 ms 无缓存路径；缺少备选路径成本时返回 `UNRESOLVABLE` 而不填 0。
3. **新文档入 Top-k 与低热度未变恢复**：BM25 或新文档 D2 排第一时，保守域重检捕获旧回答；低热度但内容未变条目经 `ResumeAndRefreshMeta` 恢复复用，不被误删。
4. **局部核验双检防漏答（P1-2）**：删掉难修主张但剩余句子有依据的修复候选被 `DualVerify` 拒绝并回退完整重生成，且完整计入二次生成与核验成本。
5. **两次相容请求的按需基线对齐**：在事件回放中区分首次生成完成并准入前后的时间点，主动维护仅计入缩短首次请求前台路径的收益，不记成省两次生成。

### 4.2 实验 C1–C4 关键对齐项与补标定
* **C1**：固定召回、硬校验与判官，分别开关同簇借用与伪计数平滑，报实际可借比例与三类误差口径。
* **C2**：明确各子池 10% / 25% / 50% 的参考分母（固定绝对配额向量、不跨池借用）；同时做两组清晰对比——① **池内独立估值 vs. 池内集合边际估值**，② **下游估值是否纳入 `resp` 短路联动**的独立消融，并对照 LRU / LFU / GDSF。
* **C3**：拆成“主动完整重生成 vs. 按需”与“局部修复 vs. 完整重生成”两组配对对照；**必须补测真实局部改写、完整重生成、双检核验与回退的时延和 Token**（替换 `dataset/costs/path_costs.csv` 第 196 行 `plan` P50 代理行）。
* **C4**：保留具备四类对象、相同硬校验与失效后按需生成的强组合基线；系统总收益按每条请求的完整路径只计一次，前台净节省、P95、正确率、总费用与后台代价分开报告。

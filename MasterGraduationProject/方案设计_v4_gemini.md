# 第一章异质缓存设计方案修订蓝图（v4）

> **状态声明**：本稿为算法蓝图修订版（`v4`），针对 Codex `v3` 复审意见完成了架构定型与三段伪代码重写。文中定向用例为**待实现验证的验收标准**，当前尚未运行代码测试，亦未修改论文 §1.2–§1.4 正文；待本蓝图通过复审并跑通定向单测与关键路径补标定后，再执行正文改写。

---

## 1. 架构定型与问题映射：四类分池 + 残余需求联动

### 1.1 核心架构裁决：为什么不同类对象不直接比大小

本版正式确立**“四类子池各自独立预算（类内专属价值竞争）+ 上游短路后的残余需求流联动”**架构：

* **类内比大小，跨类不硬比**：缓存划分为四个独立子池 $M = (M_{\mathrm{resp}}, M_{\mathrm{rag}}, M_{\mathrm{act}}, M_{\mathrm{plan}})$，分别受各自活跃逻辑索引预算 $(B_{\mathrm{resp}}, B_{\mathrm{rag}}, B_{\mathrm{act}}, B_{\mathrm{plan}})$ 约束（`resp`/`act`/`plan` 按条目计，`rag` 按证据块计；暂停待判定条目在恢复或清理前仍计入所在子池预算；若启用 `resp` 静态层扩展，离线静态池单列静态配额，动态映射计入 $B_{\mathrm{resp}}$）。四类对象只在同类子池内部竞争准入与淘汰，彻底消除“拿 `act` 扇出与 `resp` 毫秒强行混加”或“1 个 `act` 换 1 个 `rag` 块”的跨类换算争议。
* **跨类联动靠“残余需求流”杜绝重复计费**：`resp` 子池面向全量代表性请求 $Q_{\mathrm{rep}}$；`plan`、`rag`、`act` 三个子池仅面向**未被 `resp` 缓存短路、实际到达对应阶段**的残余请求流 $Q_{\mathrm{rep}}^{(k)}$。当 `resp` 命中短路整条路径时，下游中间子池自然不计功。

### 1.2 问题映射与模块定位

| §1.1 研究问题 | 对应模型与算法 | 主指标与关键对照 | 模块定位 |
| :--- | :--- | :--- | :--- |
| **问题一（前半）**：四类对象各自如何建模价值并计量扣除隐性开销后的净节省？ | **四类子池专属价值建模**（冻结当前已知版本 $\mathcal{G}_t$）+ 只读路径求值器 `EvalPath` | 动机实验 (a)；各子池路径时间净节省、P95 时延、安全复用率 | **主贡献**（四类专属建模 + 残余需求路径去重） |
| **问题一（后半）**：语义回答候选自身反馈不足时，如何权衡当前复用与误用？ | **Alg.1 (`OnlineReuse`)**：硬校验 + 版本兼容同簇反馈借用 + 经验风险门控 | C1：开关簇借用、开关伪计数平滑；分别报全流误复用率、复用中误用率、相对无缓存正确率变化 | **主贡献**（版本感知簇借用）+ **可选扩展**（伪计数平滑，不作风险上界保证） |
| **问题二（前半）**：各子池活跃规模受限时，如何按集合边际收益决定准入淘汰？ | **Alg.2 (`PlanReplacement` + `AtomicCommit`)**：子池集合目标 $S_t^{(k)}$ + 候选感知逐轮淘汰 + 全量参照 / 有条件增量 | C2：独立估值 vs. 集合估值；全量 vs. 增量一致率；LRU / LFU / GDSF；各子池 10%/25%/50% 容量曲线 | **主贡献**（核心调度算法） |
| **问题二（后半）**：外部证据更新后，如何筛查单轮 `rag → resp` 影响、决策修复并防旧版写回？ | **Alg.3 (`UpdateMaintenance`)**：原子更新屏障 + 保守重检（未变恢复）+ 热度/预算主动维护 + 局部修复双检核验 + 唯一 `AtomicCommit` | C3：两组配对对照（主动完整重生成 vs. 按需；局部修复 vs. 完整重生成）；7 项定向验收用例 | **主贡献**（屏障筛查、双检核验与原子条件提交） |
| **扩展开关** | 广义时延-费用加权代价、`resp` 静态层双层提升（Krites 思路） | 独立开关消融，主模型保持纯时间净节省、费用独立报告 | **可选扩展**（不承担首版主创新主张） |

---

## 2. 共享接口规范与四类子池专属价值定义

### 2.1 三套信息口径与一致性语义

* **信息严格隔离**：在线策略仅可见历史请求、已到达更新构建的系统已知版本图 $\mathcal{G}_t$ 及旁路判官对已触发样本的明确标注；严禁读取题库 `cluster_id`、`gold_fact_spans`、`truth.value` 或评测标签。外部真实生效版本 $\mathcal{G}_t^{\mathrm{true}}$ 仅用于离线评测（分开统计“已知失效后复用”与“通知前过期误用”）。
* **读取与更新可见性语义（回应 P0-2）**：采用**请求级可见版本快照 + 临用复核**语义——请求进入时读取当前最新已发布的系统状态快照 $(\mathcal{G}_t, \mathrm{barriers}_t)$；外部更新到达时，必须通过原子操作 **`PublishUpdateAndBarrier(u)`** 将新版本图 $\mathcal{G}_{t'}$ 与对应的粗粒度待判定屏障**同时**对新请求生效，绝不先发布新版本再挂屏障。任何已进入新版本可见态的请求均无法绕过对应屏障。

### 2.2 两大共享接口（读写彻底解耦，回应 P0-1 & P0-3）

#### 共享接口 A：`EvalPath(q, M_view, G_snap, π, rng)`（纯只读路径求值器）
* **输入**：代表性请求 $q$；临时只读缓存集合视图 $M_{\mathrm{view}}$；冻结的系统已知版本快照 $\mathcal{G}_{\mathrm{snap}}$ 与反馈快照；固定在线策略 $\pi$；成对比较共用的随机数序列 `rng`。
* **输出**：`(path_taken, fg_time_ms, cost_source, resolvable)`——被采用的路径、前台耗时、成本来源标记（`PAIRED_CAL` 配对标定 / `REPLAYED_STAGE` 可重放阶段 / `EXPLICIT_EST` 显式估计）、是否可判定。
* **约束与缺数处理**：
  1. 严格只读，不修改在线反馈、索引、缓存或准入状态；在 $M_{\mathrm{view}}$ 内部重新模拟召回与排序（如删除命中的 `resp` 后，自动检查 `M_view` 中剩余的 `plan`/`rag`/`act` 能否命中，从而精确区分 20→35 ms 与 20→100 ms）；
  2. 被 `resp` 跳过的中间阶段不单独记功；探测或校验后未采用的开销仍计入 `fg_time_ms`；
  3. 当未执行路径缺少必要实测或标定数据时，走显式声明的回退估计，或在无法可靠估计时置 `resolvable = False` 并跳过该次准入，**绝不默认为 0**。

#### 共享接口 B：`AtomicCommit(ops, expected_ver, expected_pool_rev, expected_gens, pool_k, B_k)`（全系统唯一写入口）
* **职责**：所有缓存写入、淘汰、恢复、标记失效、清理以及依赖反向索引更新，均必须通过本接口执行；重放、重检与 LLM 调用严禁进入提交临界区。
* **原子校验条件（全部满足才提交，任一失败零副作用返回 `CONFLICT/STALE/OVER_BUDGET`）**：
  1. `G_t.ver == expected_ver`（相关依赖版本未变）；
  2. `PoolRev(pool_k) == expected_pool_rev`（目标子池修订号未变）；
  3. 对 `ops` 涉及的每个条目 $j$，`CurrentGen(j) == expected_gens[j]`（条目代次匹配，防止旧修复按 key 误删新写入条目）；
  4. 提交后子池占用总逻辑单位 $\le B_k$。
* **原子动作**：一次性提交缓存增删改、更新依赖反向索引，并递增 `PoolRev(pool_k)` 与新写入条目的 `entry_gen`。

### 2.3 主目标与四类子池专属价值建模（冻结当前状态 $\mathcal{G}_t$，回应 P0-1 & P1）

首版主目标**冻结当前已知状态 $\mathcal{G}_t$**（窗口 $H$ 仅用于预测请求量权重 $w_q(H)$；未来版本存活概率仅作条目初筛或后续扩展，不与冻结 $\mathcal{G}_t$ 混在同一主目标中）。在子池 $k$ 内，代表性请求 $q$ 的路径时间净节省为 $\Delta T(q \mid M, \pi, \mathcal{G}_t) = T_0(q) - T_\pi(q \mid M, \mathcal{G}_t)$，子池窗口累计路径时间净节省为：

$$
S_t^{(k)}(M_k, H) = \sum_{q \in Q_{\mathrm{rep}}^{(k)}} w_q(H)\,\mathbb{E}\!\left[\Delta T(q \mid M, \pi, \mathcal{G}_t)\right]
$$

其中 $Q_{\mathrm{rep}}^{(\mathrm{resp})} = Q_{\mathrm{rep}}$，而 $Q_{\mathrm{rep}}^{(k)}\;(k\in\{\mathrm{rag},\mathrm{act},\mathrm{plan}\})$ 为当前 $M_{\mathrm{resp}}$ 未短路、实际到达阶段 $k$ 的残余请求集。四类子池各自的专属价值建模如下（同类只跟同类比，绝不跨类相加）：

1. **`resp` 子池（集合边际覆盖价值）**：
   - 在线聚类仅基于已观测请求特征（严禁使用题库 `cluster_id`）；簇级预计请求量按代表样本数量分配（如预测簇到达 100 次、有 5 个等权代表样本，则每个样本赋权 $w_q(H)=20$，而非各赋 100）。
   - 仅当**加入新条目不改变实际路径分布和前台成本**时，边际收益才为零（不再误写为“已有安全覆盖即零增量”，因新条目可能将校验耗时从 20 ms 降至 5 ms 或增至 25 ms）。
2. **`rag` 子池（来源版本感知的证据覆盖价值）**：
   - 在冻结的当前已知版本 $\mathcal{G}_t$ 下，直接按请求所需证据覆盖情况回放三种路径：**覆盖充分免检索**、**缺口可定位补检**、**无法确认回退完整检索**（不要求缓存集合内所有块均有效，且区分无候选与探测后回退）。
   - 不由单来源边际存活率直接推算多来源联合有效概率；$\min(H,\tau)/H$ 仅作为有效时长比例用于条目初筛说明，不混入主目标。
3. **`plan` 子池（互斥三分支执行质量模型）**：
   - 将一次模板复用尝试划分为三个穷尽、互斥的分支（基准均为相对正常从头规划的有符号时差 $\Delta t$，允许返工后仍比从头快的情形）：
     - **(A) 未进入模板执行（含适配/前置检查失败）**：概率 $p_{\mathrm{pre}}$，相对时差 $-f_{\mathrm{pre}}$；
     - **(B) 进入执行且顺利完成（无返工/重规划）**：概率 $(1-p_{\mathrm{pre}})q_i$，相对时差 $\Delta t_{\mathrm{ok}}$；
     - **(C) 进入执行但发生返工/重规划/超时失败**：概率 $(1-p_{\mathrm{pre}})(1-q_i)$，相对时差 $\Delta t_{\mathrm{rework}}$（可负可正）；无返工但结果错误计入独立任务质量指标，不混入时间。
   - 单次尝试期望时间差：$\mathbb{E}[\Delta t_{\mathrm{plan}}] = (1-p_{\mathrm{pre}})\bigl(q_i\,\Delta t_{\mathrm{ok}} + (1-q_i)\,\Delta t_{\mathrm{rework}}\bigr) - p_{\mathrm{pre}}\,f_{\mathrm{pre}}$；$q_i$ 分母严格为进入执行次数（B+C），杜绝重复扣费。
4. **`act` 子池（只读状态依赖 + 下游扇出 $d_i$ 专属价值）**：
   - 仅限只读调用、调用签名精确匹配，区分**绑定固定快照**与**要求最新状态**两类调用。
   - 在 `act` 子池内部，基础时间净节省为主体；下游不同工具数（扇出 $d_i$）作为**类内特征**用于辅助预测到达/签名匹配权重，或在 `act` 子池内作为可选排序偏好项（**不乘到毫秒收益上、不预设扇出越大需求必然越高、不参与跨类比较**），实验单独评估其增量并同步报告未加权真实路径时间节省。

---

## 3. 重写后的三段统一伪代码

### Algorithm 1：`OnlineReuse`（前台在线复用与经验风险门控）

> **口径声明**：随机门控 $r=\max(\varepsilon, 1-\delta/\tilde{p}_i)$ 针对的是该候选分组内的**联合误用概率点估计**（若该分组占全流 40%、分组内联合误用 1%，则对全流贡献 0.4%，而非全流 1%），**不控制条件错误率，不作实际风险上界保证**。伪计数平滑 $(\alpha_0,\beta_0)$ 为可选扩展（$\alpha_0=\beta_0=0$ 为无平滑基线）。调度准入采用**异步入队**，不占前台延迟且不在后台重复扣除。

```text
Algorithm 1: OnlineReuse(q, CacheState, δ, ε, N_min, α_0, β_0, rng)
Input : 请求 q；共享状态快照 CacheState = (M, G_t, barriers_t)；门控参数；rng
Output: 回答 y；本次前台执行轨迹 trace

1:  // 读取同一份原子发布的请求快照（含版本图与待判定屏障）
2:  (M_snap, G_snap, B_snap) ← AtomicReadSnapshot(CacheState)
3:
4:  // 1) 精确匹配 resp：若命中但临用复核失败，不提前返回，继续走语义/执行流程
5:  c_exact ← LookupExactResp(M_snap.resp, q)
6:  if c_exact ≠ ∅ and not IsBarred(c_exact, B_snap) and HardValid(c_exact, q, G_snap) then
7:      if ReCheckBeforeUse(c_exact, CacheState) then
8:          return (c_exact.resp, TraceExactHit(c_exact))
9:
10: // 2) 语义召回 resp（硬校验或屏障未通过者不进入风险标注与门控）
11: c_sem ← Top1SemanticResp(M_snap.resp, q)
12: valid_sem ← (c_sem ≠ ∅ and not IsBarred(c_sem, B_snap) and HardValid(c_sem, q, G_snap))
13: if valid_sem then
14:     b ← SimBucket(sim(q, c_sem))
15:     (e_i, n_i, p_c, m) ← FetchCompatFeedback(c_sem, b, q.perm, q.time_window, G_snap)
16:         // 仅借用同簇、同桶 b、权限与时间窗相容、证据版本一致的近期明确标注；m ≤ m_max
17:     if n_i + m ≥ N_min then
18:         p_tilde ← (e_i + m * p_c + α_0) / (n_i + m + α_0 + β_0)
19:         r ← ε if p_tilde ≤ δ else max(ε, 1 - δ / p_tilde)
20:         if rng.uniform(0, 1) > r and ReCheckBeforeUse(c_sem, CacheState) then
21:             return (c_sem.resp, TraceSemHit(c_sem))
22:
23: // 3) 未复用 resp：仅执行 q 实际需要的阶段，按需查 plan / rag / act 子池
24: (y, new_objs, trace) ← ExecuteRequiredPath(q, M_snap, G_snap, B_snap, CacheState)
25:
26: // 4) 旁路异步判官 + 异步入队调度（不阻塞前台返回）
27: if valid_sem then
28:     EnqueueAsyncJudge(q, c_sem.id, c_sem.gen, c_sem.version, EvidenceAt(G_snap))
29:         // 依据候选版本与当时证据独立判定；区分版本不相容与语义答错；无法判定不入标注
30: for each (pool_k, obj) in new_objs do
31:     EnqueueAsyncAdmit(pool_k, obj, G_snap.ver)
32: return (y, trace)
```

---

### Algorithm 2：`PlanReplacement` + `AtomicCommit`（只读候选感知规划 + 唯一原子提交）

> **核心升级（回应 P0-1, P0-3, P1）**：① 拆分为纯只读 `PlanReplacement` 与全局唯一 `AtomicCommit`；② 采用**候选感知逐轮淘汰**（先把新候选 $i$ 纳入并保护在临时子池 $M_{\mathrm{work}} \cup \{i\}$ 中，再逐轮重算移除其余条目的边际损失，解决 18→19 直接替代反例，仍诚实标为启发式、不宣称全局最优或近似比）；③ 明确受影响超集 $Q_{\mathrm{aff}}$ 是逐请求不漏算的**充分条件**，无法证明完备时回退 `EXACT_FULL`。

```text
Algorithm 2: AdmitToPool(pool_k, i, CacheState, Q_rep_k, B_k, mode, rng)
Input : 目标子池 pool_k；新候选 i（占用 c_i）；CacheState；残余代表集 Q_rep_k；预算 B_k；mode ∈ {EXACT_FULL, PROVABLE_INC, APPROX_INC}
Output: 布尔值 committed

1:  if c_i > B_k then return False
2:  for attempt = 1 to MAX_RETRY do
3:      // A) 读取只读快照，完全在临界区外规划替换方案
4:      (M_snap, G_snap, rev_k) ← AtomicReadPoolSnapshot(CacheState, pool_k)
5:      if not EntryAdmissible(i, G_snap) then return False
6:
7:      plan ← PlanReplacement(pool_k, i, M_snap, G_snap, Q_rep_k, B_k, mode, rng)
8:      if plan.status ∈ {UNRESOLVABLE, REJECT} then
9:          if plan.E_dead ≠ ∅ then
10:             AtomicCommit(remove=plan.E_dead, add=∅, G_snap.ver, rev_k, Gens(plan.E_dead), pool_k, B_k)
11:         return False
12:
13:     // B) 经由全局唯一入口原子提交（校验版本、修订号、所有涉及条目代次与预算）
14:     res ← AtomicCommit(remove=plan.E_total, add=i, G_snap.ver, rev_k, Gens(plan.E_total), pool_k, B_k)
15:     if res == OK then return True
16:     if res == STALE_VERSION then return False    // 新候选自身依赖已过期，放弃准入
17:     // 若 res == REV_CONFLICT，循环重试一次
18: return False

Function PlanReplacement(pool_k, i, M_snap, G_snap, Q_rep_k, B_k, mode, rng):
19: E_dead ← { j ∈ M_snap[pool_k] : j.confirmed_dead }
20: // 候选感知淘汰：先将 i 纳入临时子池并锁定保护（不参与被淘汰），再逐轮挑删谁损失最小
21: M_base ← M_snap[pool_k] \ E_dead
22: M_work ← M_base ∪ { i }
23: E_evict ← ∅
24: while UsedBudget(M_work) > B_k do
25:     best_j ← None; best_density ← +∞
26:     for each j ∈ M_work \ { i } do
27:         (loss_j, ok) ← EvalDelta(M_work, M_work \ { j }, Q_rep_k, M_snap, G_snap, mode, rng)
28:         if not ok then return Plan(status=UNRESOLVABLE, E_dead=E_dead)
29:         if (loss_j / c_j) < best_density then
30:             best_density ← loss_j / c_j; best_j ← j
31:     E_evict ← E_evict ∪ { best_j }
32:     M_work ← M_work \ { best_j }
33:
34: E_total ← E_dead ∪ E_evict
35: // 与原集合 M_snap[pool_k] 比较完整集合收益差 ΔS（共用同一份 rng 与权重）
36: (ΔS, ok) ← EvalDelta(M_work, M_snap[pool_k], Q_rep_k, M_snap, G_snap, mode, rng)
37: if not ok then return Plan(status=UNRESOLVABLE, E_dead=E_dead)
38: if ΔS > 0 and UsedBudget(M_work) ≤ B_k then
39:     return Plan(status=ACCEPT, E_dead=E_dead, E_total=E_total, ΔS=ΔS)
40: return Plan(status=REJECT, E_dead=E_dead)
```

---

### Algorithm 3：`UpdateMaintenance`（原子屏障、保守重检、双检核验与唯一提交）

> **核心升级（回应 P0-2, P0-3, P0-4）**：① 版本图与粗粒度待判定屏障**原子生效**；② 仅当检索打分对无关文档严格不变时走窄查，否则按安全域保守重检；③ 未变条目校验**代次与版本**后恢复并刷新元数据，绝不误删；④ 是否主动维护首版采用**验证集标定的热度门槛 + 后台预算**（严格对照按需生成基线）；⑤ 核验改为**忠实性 ∧ 必答完整性双检**，记全局部失败回退后的二次核验成本；⑥ 最终通过**`PlanReplacement` + 唯一 `AtomicCommit`** 原子落盘，失败零副作用。

```text
Algorithm 3: UpdateMaintenance(u, CacheState, Q_rep_resp, B_resp, hot_thresh, bg_budget)
Input : 更新事件 u；CacheState；代表集 Q_rep_resp；预算 B_resp；热度门槛 hot_thresh；后台预算 bg_budget

1:  // 阶段 1：原子发布新版本图与待判定屏障（杜绝更新发布与暂停间的并发漏检窗口）
2:  if RetrieverScoreInvariantToUnrelatedDocs(u) then
3:      scope ← ReverseIndexLookupResp(CacheState, u)      // 仅在严格可证不变时窄查
4:  else
5:      scope ← SafeDomainOrAllResp(CacheState, u)         // BM25/新入 Top-k/索引切换走保守域筛查
6:  (v_pub, targets) ← PublishUpdateAndBarrier(CacheState, u, scope)
7:      // targets 记录每个待判定条目的 (id, gen) 对，防止后续误操作同 key 新代次
8:
9:  for each (i_id, i_gen) ∈ targets do
10:     // 阶段 2：确定性重检确认“是否受影响”（绝不因低热度跳过影响判定直接删除）
11:     (new_topk, diff_ev) ← DeterministicReRetrieve(i_id.query, v_pub)
12:     if EvidenceAndBasisUnchanged(i_id, new_topk, diff_ev) then
13:         // 校验代次与版本相容后原子恢复，并刷新有效性元数据；然后立即结束当条
14:         res ← AtomicCommit(op=RESUME_AND_REFRESH_META(i_id, new_topk),
15:                            expected_ver=v_pub, expected_gens={i_id: i_gen}, pool_k=resp)
16:         if res == STALE_VERSION then EnqueueRetry(i_id)
17:         continue
18:
19:     // 确认受影响失效：按代次标记失效（若期间已被新代次覆盖则无副作用跳过）
20:     if AtomicCommit(op=MARK_INVALID(i_id), expected_gens={i_id: i_gen}, pool_k=resp) ≠ OK then
21:         continue
22:
23:     // 阶段 3：决策“是否主动维护”（对照基线：失效后释放占位，首次相容请求按需生成并准入）
24:     if EstHeat(i_id, Q_rep_resp) < hot_thresh or bg_budget.exhausted() then
25:         AtomicCommit(op=DROP_INVALID(i_id), expected_gens={i_id: i_gen}, pool_k=resp)
26:         continue
27:
28:     // 阶段 4：决定“如何修”并执行全量双检核验（忠实性 ∧ 必答完整性）
29:     route ← SelectRepairRoute(i_id, diff_ev, new_topk)
30:         // 先查可定位性与证据充分性（ρ_i 仅作特征）；
31:         // 比较 E[C_local] = C_revise + C_verify + p_fb * (C_regen + C_verify) 与 C_regen + C_verify
32:     if route == LOCAL_REPAIR then
33:         y_cand ← LocalRepair(i_id, diff_ev, new_topk)
34:         ok ← DualVerify(y_cand, i_id.query, new_topk)   // 双检：全部主张有依据 ∧ 必答内容无遗漏
35:         if not ok then
36:             y_cand ← FullRegenerate(i_id.query, new_topk)
37:             ok ← DualVerify(y_cand, i_id.query, new_topk)   // 计入二次核验成本
38:     else
39:         y_cand ← FullRegenerate(i_id.query, new_topk)
40:         ok ← DualVerify(y_cand, i_id.query, new_topk)
41:
42:     if not ok then
43:         AtomicCommit(op=DROP_INVALID(i_id), expected_gens={i_id: i_gen}, pool_k=resp)
44:         continue
45:
46:     // 阶段 5：临界区外只读规划 + 唯一原子提交（版本、修订号、代次、容量同刻校验）
47:     new_entry ← BuildEntry(y_cand, new_topk, v_pub)
48:     (M_snap, G_snap, rev_resp) ← AtomicReadPoolSnapshot(CacheState, resp)
49:     if G_snap.ver ≠ v_pub then EnqueueRetry(i_id); continue
50:     plan ← PlanReplacement(resp, new_entry, M_snap, G_snap, Q_rep_resp, B_resp, mode, rng)
51:     if plan.status == ACCEPT then
52:         res ← AtomicCommit(remove=plan.E_total ∪ {(i_id, i_gen)}, add=new_entry,
53:                            expected_ver=v_pub, expected_pool_rev=rev_resp,
54:                            expected_gens=Gens(plan.E_total) ∪ {i_id: i_gen}, pool_k=resp, B_k=B_resp)
55:         if res == STALE_VERSION then EnqueueRetry(i_id)
56:         else if res == REV_CONFLICT then EnqueueReplan(new_entry, v_pub)
57:     else
58:         AtomicCommit(op=DROP_INVALID(i_id), expected_gens={i_id: i_gen}, pool_k=resp)
```

---

## 4. 逐项修订对照表（回应 Codex v3 复审）

| 复审编号 | 新稿位置 | 核心改法 | 对应反例或实验 | 当前证据状态 |
| :--- | :--- | :--- | :--- | :--- |
| **P0-1** | §2.2 接口 A、§2.3 | 主目标冻结当前 $\mathcal{G}_t$；定义只读 `EvalPath` 及缺数回退；CE-2 改为“充分条件” | 删 20 ms `resp` 区分 35 ms vs. 100 ms；C2 | 纸面定义完成，待单测实现 |
| **P0-2** | §2.1、Alg.3 L1–17 | 版本图与待判定屏障通过 `PublishUpdateAndBarrier` 原子生效；不能证打分不变时走安全域保守重检；按代次恢复并刷新元数据 | 更新与在线读取交错；BM25 / 新入 Top-k | 纸面伪代码完成，待单测实现 |
| **P0-3** | §2.2 接口 B、Alg.1 L30–31、Alg.2、Alg.3 L47–58 | Alg.2 拆为只读 `PlanReplacement` + 全局唯一 `AtomicCommit`（验版本、修订号、代次、容量）；Alg.1 改为异步入队调度 | 并发抢容量、旧修复晚于新写入不误删 | 纸面伪代码完成，待单测实现 |
| **P0-4** | Alg.3 L23–44 | 主动维护改热度门槛 + 后台预算对照按需基线；局部核验升级为 `DualVerify`（忠实性 ∧ 必答完整性），显式计入二次核验成本 | 两次相容请求基线；遗漏必答内容判失败；C3 | 纸面伪代码完成，待单测与 C3 补标定 |
| **P1-`resp`/`rag`** | §2.3 (1)(2) | `resp` 按路径分布与成本不变判零增量，簇权重按样本均分（100/5=20）；`rag` 按当前版本直接回放覆盖，不由边际推联合 | C2 权重校准；`rag` 覆盖分支 | 纸面定义完成，待实现核验 |
| **P1-`plan`/`act`** | §2.3 (3)(4)、§1.1 | `plan` 互斥三分支改有符号相对时差并明晰失败归属；`act` 分池内建模、区分固定快照/最新状态、扇出仅作待验特征 | C4 消融；分池独立预算 | 纸面定义完成，待实现核验 |
| **P1-Alg.2 & CE-1** | Alg.2 L20–32、Alg.1 声明 | 引入**候选感知逐轮淘汰**（先纳入并保护 $i$ 再选淘汰项）；CE-1 明确分组内 1% × 40% 占比 = 全流 0.4% | 18→19 直接替代反例；C1 三风险口径 | 纸面伪代码完成，待单测实现 |
| **实验标定纠偏** | §5.2 | 删除“旧副本 `real_calibration_300.csv` 待同步”过时表述；保留 `partial_repair/rewrite` 代理行待补配对实测说明 | 仓库文件 SHA-256 核对；C3 成本分解 | 已对齐仓库文件，待补 C3 真实配对标定 |

---

## 5. 定向验收用例与实验状态清单

### 5.1 七项定向验收标准（待代码实现后逐条跑通）

| 用例编号 | 定向场景 | 最低验收条件（须在实现单测中通过） |
| :--- | :--- | :--- |
| **T-1** | 删除命中的 `resp` 后暴露中间阶段 | `EvalPath` 在同一快照下准确区分 20→35 ms 与 20→100 ms，输出可追溯的 `cost_source`；缺数时走回退估计或返回 `UNRESOLVABLE`，绝不默认 0 |
| **T-2** | 候选能替代旧条目（18→19 反例） | 容量 $B_{\mathrm{resp}}=2$，原 `{a(10), b(8)}`，候选 `i` 覆盖 `a` 且 +1；`PlanReplacement` 在 `{a, b, i}`（保护 `i`）上选删 `a`（损失 0），成功达成 `{b, i}=19` |
| **T-3** | 增量漏掉跨簇或备用候选 | 无法证明可达超集完备时自动回退 `EXACT_FULL`；运行 `APPROX_INC` 时能显式记录与全量参照的误差及准入分歧 |
| **T-4** | 更新发布与在线读取交错 / 新入 Top-k | `PublishUpdateAndBarrier` 后进入新快照的请求绝不绕过屏障；BM25 或新文档 D2 排第一时，保守域筛查成功捕获旧回答 |
| **T-5** | 并发抢剩余容量 / 旧修复晚于新写入 | `AtomicCommit` 保证不超预算、旧修复按代次失败不误删同 key 新条目、校验失败零淘汰且缓存与反向索引保持一致 |
| **T-6** | 两次相容请求与按需基线对比 | 按需基线允许第 1 次生成准入、第 2 次命中；主动维护收益仅计入缩短第 1 次前台关键路径，绝不记成省两次生成 |
| **T-7** | 局部修复遗漏原问题必答内容 / 低热度未变 | `DualVerify` 拒绝“删掉难修主张但余句有依据”的修复候选并回退重生成；低热度但未受影响的条目经 L14 恢复复用，绝不误删 |

### 5.2 仓库标定状态与实验补齐项

* **已核实一致**：`dataset/events/real_calibration_300.csv` 与 `exp_motivation/data/real_calibration_300.csv` 的 SHA-256 一致，均含 300 行阶段计时与 Token 计数。
* **必须补齐的实测与对照**：
  1. **C3 配对实测**：替换 `dataset/costs/path_costs.csv` 第 196 行取自 `plan` P50 的代理值，补测真实局部改写、完整重生成、全量双检核验与失败回退的时间及 Token；C3 拆为“主动完整重生成 vs. 按需”与“局部修复 vs. 完整重生成”两组配对对照，不把同一更新下的多条回答当独立样本。
  2. **C1 / C2 / C4 对照对齐**：C1 分别开关簇借用与伪计数平滑并报实际可借比例；C2 在四类子池各自 10%/25%/50% 容量下对照独立估值、集合估值、全量 vs. 增量及 LRU/LFU/GDSF；C4 保留具备四类对象、相同硬检查且失效后按需生成的强组合基线，前台净节省、P95、正确率、总费用与后台代价分开报告。
  3. **诚实边界声明**：约 73% 低主张影响比例仅作数据构造统计而非局部修复成功率；未补通知前过期用例时不以零观测推断无风险；未建模资源争用时不把 goodput 解释为服务吞吐上限；未核实的扩展更新率流标为待构造。

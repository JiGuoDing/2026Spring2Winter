# 路径条件、成本来源与事件时序最小规范（v0.4.0）

> 本规范闭合交接文档与 v5 设计稿中的两项前置约束：
> 1. **备选路径可求值性**：不从 20 ms 命中日志反推未走过的路径，逐路径写清触发条件、可见输入、成本来源与缺数处理（缺数返回 `UNRESOLVABLE`，严禁补 0）；
> 2. **事件时序统一口径**：顺序事件回放中区分外部真实生效时刻、系统通知到达时刻与同步/后台修复可见时点。

---

## 一、路径条件与成本来源表（`EvalPath` 契约）

| 路径 ID | 对象 | 触发条件（仅用在线可见字段） | 执行步骤与计账项 | 成本来源（`measured` / `assumed` / `pending`） | 缺数处理 |
|---|---|---|---|---|---|
| `resp_exact_hit` | `resp` | 规范化键精确匹配 ∧ 未暂停 ∧ `HardValid(perm, time_window, sys_ver)` 通过 | 精确查找 + 依赖版本/权限/块哈希校验 | `costs/path_costs.csv`: `exact_hit/key_hit_then_check`（`measured=1`，p50 0.0084 ms） | 必可得 |
| `resp_sem_hit` | `resp` | 精确未命中 ∧ `Top1SemanticResp >= 0.88` ∧ 未暂停 ∧ `HardValid` 通过 ∧ 风险门控抽样决定复用 | 句向量召回 + 硬校验 + 风险门控判定 | `costs/path_costs.csv`: `semantic_hit/recall_then_check`（`measured=1`，p50 1.41 ms） | 必可得 |
| `resp_miss_or_fallback` | `resp` | 精确/语义未命中，或硬校验失败，或风险门控决定重生成 | 探测失败额外开销 + 下游实际所需阶段（`plan`/`rag`/`act`/`resp`） | 探测额外开销：`costs/fallback_costs.csv`（`measured=1`）；下游生成：`events/real_calibration_300.csv`（`measured`）或按请求匹配标定分布 | 无配对成本时返回 `UNRESOLVABLE` |
| `rag_reuse_hit` | `rag` | 同查询/检索配置且缓存证据块在当前已知索引版本下全有效（首版受限复用） | 缓存检索 + 逐块版本与权限核对 | `costs/path_costs.csv`: `validity_check/check`（`measured=1`，p50 0.0081 ms） | 不可先跑完整检索再记为省掉 |
| `rag_fallback_retrieve` | `rag` | `rag` 缓存缺失，或有效块覆盖不足 / 含过期块 | 校验失败开销 + 完整 BM25 检索与拼装 | 校验失败：`costs/fallback_costs.csv`；检索：`costs/path_costs.csv` `full_regen/retrieve`（`measured=1`，p50 1.42 ms）或标定实测 `t_rag_ms`（p50 6.16 ms） | 多部署敏感性见 `costs/tool_cost_model.json`（`assumed`） |
| `act_reuse_hit` | `act` | 只读调用签名（`act_key` + 参数 + 访问范围）精确匹配 ∧ 数据快照/状态版本一致 ∧ 权限相容 | 签名查找 + 有效性校验 | `costs/path_costs.csv`: `exact_hit/key_hit_then_check`（`measured=1`，p50 0.0084 ms） | 必可得 |
| `act_exec_or_fallback` | `act` | `act` 未命中或状态过期 | （若命中过期计校验回退开销）+ 执行只读 SQL（可选挂载 `events/tool_failures.jsonl` 模拟重试） | 本地实测：`costs/path_costs.csv` `act/execute_sql`（`measured=1`，p50 1.16 ms）；远程/重试画像：`costs/tool_cost_model.json`（`assumed`） | 实测与假设分表报告 |
| `plan_reuse_hit` | `plan` | 模板匹配 ∧ 前置条件/工具可用性/权限通过 ∧ 适配成功 | 模板查表 + 适配校验（跳过从头规划模型调用） | 适配失败/返工未实测前标 `pending`；成功跳过规划节省的参考值来自 `real_calibration_300.csv` 的 `t_plan_ms`（p50 49.7 s）与 30 对 `branch_pairs.jsonl` | 若需比较 `plan` 返工分支且未标定，返回 `UNRESOLVABLE` |
| `plan_full_generate` | `plan` | 无可用模板或适配失败回退 | 规划模型调用 | `events/real_calibration_300.csv` `t_plan_ms`（`measured`） | 必可得 |
| `repair_local` | `resp` | 更新事件确认受影响 ∧ 路由选择 `LOCAL_REPAIR` | 定位 + 确定性重检 + 局部改写 + 在线双检（若双检失败则追加 `FullRegen + DualVerify`） | 定位：`costs/path_costs.csv` `partial_repair/locate*`（`measured=1`）；改写与双检：**必须由 `run_repair_calibration.py` 实测回填**（未回填前标 `pending`，禁用 `plan` P50 代理写结论） | 未实测前返回 `UNRESOLVABLE` |
| `repair_full_regen` | `resp` | 更新事件确认受影响 ∧ 路由选择 `FULL_REGEN` 或局部修复双检失败回退 | 完整重检 + 完整重生成 + 在线双检 | 重检：`full_regen/retrieve`；生成：`full_regen/generate`（`measured=backfill`，p50 98.6 s）及 `run_repair_calibration.py` 配对实测 | 与 `repair_local` 严格同样本配对 |

> **总账防重规则**：任一条请求从到达到返回只按实际执行路径计一次前台耗时；被 `resp` 短路跳过的下游阶段（`plan`/`rag`/`act`）不单独记为本次请求的节省。

---

## 二、顺序事件回放时序表

| 时刻 / 字段 | 可见性 | 语义与回放处理规则 |
|---|---|---|
| `update_events.effective_at`（= `docs_versioned.updated_at`） | **仅离线评测可见** | 外部文档新版本在真实世界生效的时刻；离线 `view_judge(..., "truth")` 据此判定答案客观上是否过期。**在线策略严禁读取。** |
| `update_events.timestamp`（`notified_at`） | **在线可见** | 更新通知到达缓存系统的时刻（`>= effective_at`，中位延迟 1.61 h）。系统仅在此刻推进已知版本图 $\mathcal{G}_t$ 并触发暂停/重检。 |
| `request_stream.timestamp` | **在线可见** | 请求到达时刻。与 `update_events.timestamp` 按升序归并；同一时刻优先处理已到达的更新通知再处理请求。 |
| 同步前台操作（查找、硬校验、风险门控、未命中生成、同步准入） | **计入前台时延** | 凡阻塞响应返回的操作均计入单请求前台时延 `fg_time_ms`。 |
| 旁路/后台操作（未复用时的判官标注、主动维护修复） | **独立计入后台成本与总开销** | 后台任务须显式记录 `(start_ts, finish_ts, visible_ts, source_ver)`：在 `finish_ts` 之前到达的请求**不可读到**该修复结果；若提交时 `G_t.ver != source_ver`，丢弃过时结果。首版 C3 先在同一触发时点配对比较「局部修复 vs. 完整重生成」，主动维护 vs. 按需单独对照。 |

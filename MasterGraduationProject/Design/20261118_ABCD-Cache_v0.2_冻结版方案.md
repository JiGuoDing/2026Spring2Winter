# ABCD-Cache v0.2（冻结版方案）

> v0.1 经 5 路审计后重写：需求覆盖审计（93 项需求，63 项缺失，38 项 P0）、ABCD 全量实测审计、同类基准对比审计、评测/冻结审计、事件语义审计。
> 结论：v0.1 的"素材层"多数成立，但**范围、契约、口径**三处必须重构；本版是准备冻结的 v1.0 契约草案。
> 原始 ABCD 数据不改动；所有派生层可追溯、可重算、可扩展。

---

## 0. 审计结论：v0.1 为什么不完善

### 0.1 三类根本问题

| 类别 | 发现 | 后果 |
|---|---|---|
| **范围错配** | ABCD 的 action 输出 47.8% 是恒定回执、52.2% 是参数回显、**0% 携带状态真值**；10 个动作（26.4% 调用）是写操作。它没有"只读工具结果"，act 不能按 v0.1 从动作日志抽取 | E1/E2 的 act 结论从根上不成立；必须重定义 act 或移到 ToolBench |
| **数据现实** | 仅 **23.5%** 会话可规则化、45.0% 需人工标注、31.5% 应排除；`purchase_date` 只覆盖 20.8% 且与 gold 脱钩（规则-gold 一致率 75.1%，guest 超 30 天仍有 47.7% 被批准）；10 个姓名不是 10 个客户（3,391 account_id / 5,123 order_id）；静态库与候选池跨 split 泄漏严重（act 76.5%、plan 80.1%、resp 41.8%、rag 100%） | 阈值型版本实验样本仅 13 个会话；用官方 split 建静态库=白送；租户/权限模型必须合成 |
| **契约缺失** | v0.1 只有"事件壳、对象、账本"，没有实验契约：冻结候选、静态库构建、claim→evidence、双时间轴、幂等键、成本分项、预注册、版本迁移、失败注入 | 实验 B/D/E 无法开跑；指标无法复算；冻结后任何补字段都触发重跑 |

### 0.2 审计数字（全部本地实算）

| 项 | 数值 |
|---|---|
| 会话 / 轮次 | 10,042 / 220,983 |
| 客户触发请求 / agent 应答 lookup | 89,372 / 95,129（1.064/请求；48,740 个 agent 轮不是客户触发） |
| action 调用 / plan lookup / rag（严格） | 36,482 / 10,042 / 5,870（宽口径 13,159，与 act 重叠） |
| 唯一事件总量（互斥分区） | **141,653** |
| 动作语义 | 只读 17 个/24,849 次（68.1%）；写 10 个/9,616 次（26.4%）；信息 3 个/2,017 次（5.5%） |
| 规则化分桶 | A 可规则化 14 意图/2,358 会话（23.5%）；B 人工 29/4,519（45.0%）；C 排除 12/3,165（31.5%） |
| 最优首批 flow | shipping_issue（1,020，A 48%+missing）、order_issue（1,040，A 61%）、account_access（1,048，A 100%）；合计 3,108 会话（30.9%） |
| 阈值型编辑（bronze 90→60） | 仅 **13 个会话**，原始 gold 翻转 0 |
| 流程型编辑 | 245–1,023 会话，gold 序列 100% 改变 |
| E5 可用样本 | 单事件 118–434 个缓存答案；**6 主事件池化≈1,644** |
| 20/80 切分下精确命中 | act 76.4%（虚高）/ plan 72.0% / resp 30.5% |
| 候选池 history-only 过滤 | 平均保留 65.5/100（p5=58），无 turn 清零 |

---

## 1. v0.2 的范围：T1 支持什么、不支持什么

### 1.1 支持矩阵

| 对象 | T1 支持方式 | 依赖 | 明确边界 |
|---|---|---|---|
| `plan` | 从 55 意图/96 题面抽取参数化动作模板；2,438 个 (意图,序列)；流程型编辑 100% 使计划失效 | 规则引擎 + 金标序列（guidelines + `kb.json`） | 只对 A/B 桶 flow 做真值；FAQ/排障不进 plan 评测 |
| `rag` | 916 条政策条款（255 动作 + 110 instruction + 551 subtext）；按版本生效区间管理；聚焦"证据是否仍支持当前动作" | 政策版本 + 权限 | **FAQ 答案不在数据中**（select-faq 只回显 id）→ FAQ 类不做 rag 真值；检索空间小，只报版本有效性 |
| `resp` | 客服回复模板（58,707 个去词化模板）；按意图/下一步/状态指纹缓存；政策派生槽值 → claim | 规则引擎生成 claim 映射 | 短回复、单主张；寒暄/自由表述无证据；质量需 rubric + 人工审计 |
| `act` | **不是从 ABCD 动作日志抽**，而是由模拟器生成"策略/状态谓词查询"对象：`check_return_eligibility`、`lookup_order_state`、`check_membership_privilege` 等；key=工具+规范化参数+租户/权限域+状态版本+政策版本；value=资格/状态答案 | 规则引擎 + 状态机 + 合成工具注册表 | **构造对象，必须声明**；ABCD 的真实动作只作为"需求发生时刻"的来源 |
| `act`（真实工具） | 放到 **T3 扩展轨**：ToolBench/StableToolBench + AgentBench DBBench | 外部数据集 | 不与 T1 混报；只做外部效度与真实成本校准 |

### 1.2 明确不支持（必须从别处补）

| 缺口 | 补法 | 在论文中的定位 |
|---|---|---|
| 真实请求到达过程 | Chutes 一年 trace | T1 只提供逻辑时间线；到达形状借 Chutes |
| 真实文档版本事件 | FiscalQA Pro、ChurnBench | T1 的政策版本是构造；外部效度轨 |
| 语义答案等价（resp） | vCache SemCache | T2 轨；T1 的 resp 只做模板级 |
| 真实权限/RBAC | 合成（SSC 不公开） | 明确 limitations |
| 真实工具结果 | ToolBench/DBBench | T3 轨 |

> **论文定位（必须这样写）**：T1 不是"新采集数据集"，而是"客服政策场景下的可复现缓存实验台"；它的独有价值是**四类对象共时钟 + 逐请求反事实 + 可重算账本**，不是"更真实的数据"。

---

## 2. 数据事实纠偏（写进论文/数据卡）

| v0.1 说法 | 实测纠正 |
|---|---|
| 请求 = agent 处理步 = 95,129 | 客户触发请求 89,372；95,129 是 resp lookup 次数（1.064/请求）；48,740 个 agent 轮非客户触发 |
| lookup 合计 154,577 | rag 12,924 是 act 36,482 的子集，双计；互斥后唯一事件 141,653（act 23,558 + rag 12,924 + resp 95,129 + plan 10,042） |
| 无参数调用 31% "全局可复用" | 其中相当部分是写动作/信息动作；只读动作需白名单；真实可复用上界要按 KeySpec 重算 |
| 10 个虚构客户 → 20 租户 | 10 个**随机姓名标签**，3,391 个 account_id、5,123 个 order_id；email 跨 split 重叠 88 个；租户必须按会话合成 |
| 有 purchase_date 就能做时效 | 仅 20.8% 会话有；且与 gold 决策脱钩（规则-gold 75.1%）→ 阈值标签必须合成并声明 |
| product_defect 作为首批 | 应降级为 case study（receipt 缺失、日期脱钩、阈值编辑仅 13 会话）；首批改为 shipping_issue / order_issue / account_access |
| utterances.json 是真人改写池 | 是 95,288 条候选句排序池（非改写对）；R2 只能用 LLM 改写 + 人工抽检 |
| resp 模板 58,657 | 58,707（归一化口径需写死） |
| 政策条款约 303 | 916 条（255 动作 + 110 instruction + 551 subtext）；FAQ 答案缺失 |

---

## 3. T1 数据模型 v1.0（契约层）

### 3.1 三层结构

```text
契约层（冻结，semver 1.x）
  event envelope / IDs / visibility / time model / version chain /
  label semantics / metric registry / split protocol / cost op enum / replay order
内容层（v1.0 冻结；minor 只允许 additive）
  raw ABCD / policy v1 docs / rules / object templates / static library /
  candidates / labels / cost calibration / entity map
实例层（不冻结，按 config 生成）
  scenario.yaml：arrival, regime, repeat λ, update schedule, ACL events,
  capacity/budget, fault injection, seed
  每个实例 = manifest hash；实验 pin 实例 ID
```

**关键原则：数据集是"生成器 + 冻结实例"，不是一份静态 CSV。** 以后加实验 = 加 scenario 配置或扩展轨，不改契约层。

### 3.2 时间模型

```text
EventEnvelope {
  event_id, event_type, schema_version,
  t_event,        // 业务发生/生效（客观真值）
  t_notify,       // 系统收到（ONLINE 可见起点）
  t_process,      // 回放逻辑时刻
  clock_domain, timeline_map_id,
  stream_seq, order_key=(t_process, stream_seq),
  causal_parents[], dedup_key, delivery{dup_index},
  source{producer,seed,builder_version},
  visibility ∈ {ORACLE, ONLINE, PROVENANCE}
}
```

- 业务钟：ABCD 日期（2019-07…2020-03）→ 虚拟 8 周时间线的显式映射；`purchase_date` 只对 product_defect/shipping 有值，其余 flow 的"当前逻辑日"由 anchor 规则给出。
- 陈旧暴露双口径：客观（`t_event`）为主、可用（`t_notify`）为稳健列。
- 首版退化断言：`t_event ≤ t_notify ≤ t_process`、同 target 通知序=版本序、无重复投递；三条成立时"按处理时间排序"是严格退化，可外推到延迟/乱序扩展。

### 3.3 请求与对象（互斥分区）

| 对象 | 数量 | 说明 |
|---|---|---|
| request（客户触发） | 89,372 | 含 turn_idx/session/tenant/role/text/context_ref/observable_state_ref/regime/split |
| resp lookup | 95,129 | 每个 agent 应答一次 |
| act（构造的谓词查询） | 由模拟器按需求生成，目标约 30–60k | 覆盖策略/状态查询；与 ABCD 动作日志的"需求时刻"对齐 |
| rag lookup | 5,870（严格） | search-faq/select-faq/ask-the-oracle 等政策检索 |
| plan lookup | 10,042 | 每会话一次 + 重规划 |
| 事件总量 | 约 30–40 万（含 decision/bg/update） | Flink 回放规模 |

### 3.4 act 的重定义（本版最重要的范围决策）

**T1-act = 模拟器提供的只读策略/状态查询**，不是 ABCD 动作回执：

```text
tool_registry:
  check_return_eligibility(member_level, purchase_age_days, packaging, policy_version) -> {eligible, deadline, reason}
  lookup_order_state(order_id) -> {status, shipped_at, delivered_at}
  check_membership_privilege(level, action, policy_version) -> {allowed, limits}
  lookup_refund_status(refund_id) -> {state, method, eta}
  ...
```

- key = `(tenant/scope, tool_id, tool_version, normalized_params, state_version, policy_version)`；
- value = 由规则引擎/状态机生成的资格或状态答案；
- 依赖 = 状态谓词 + 政策版本；`verify_then_reuse` = 重读状态/版本并判谓词（不是 LLM 判官）；
- 需求来源 = ABCD 动作日志中"何时需要该查询"；结果来源 = 构造（声明）；
- 与 T3（ToolBench 真实工具）分开报告：T1 测"策略/状态谓词缓存"，T3 测"真实工具结果缓存"。

> 理由：ABCD 的动作输出信息量≈0（回执/回显），无法支撑 act 价值建模；硬抽取会得到"命中率很高但收益为零"的假象。与其如此，不如把 act 明确定义为"状态/资格查询"，用规则引擎生成有真值的结果——这恰好符合论文对 act"只读工具结果 + 状态检查"的建模。

### 3.5 政策版本

```text
doc_id（稳定条款身份，不含路径）
lineage_id, version(int), prev_version, supersedes, superseded_by,
status ∈ {active, staged, retired, deleted(tombstone)},
effective_from, effective_to, lead_time,
content_hash, change_type ∈ {add, modify, delete, rechunk, migrate, acl_only},
change_diff_ref, flow_membership[],
acl{version, roles, tenants}, rule_engine_version, audit{reviewer,kappa_ref}
```

- 一次更新 = 新增不可变版本；删除 = tombstone；连续更新 = CAS 提交 + 过期候选丢弃；
- 证据 ID 与版本分离：`{doc_id, chunk_id, version, content_hash}`；
- 6 类编辑：阈值型、流程型、权限型、文档型、参数型、无效果型（用于 change≠harm）。

### 3.6 状态、实体与权限

- 状态机（订单/会员/退款）白名单转移表；派生谓词（退货资格/会员特权）由规则引擎按 `(state, policy_version)` 计算，不建独立状态字段；
- 实体重映射：online 窗口的 name/username/email/phone/order_id 确定性双射到与 history 不相交的命名空间；warm/cold 两层分别报告；
- 租户按会话合成（不是 10 个客户）；ACL 事件 2 轮；`data_scope ∈ {global, tenant, user}`；
- 论文声明：权限维度为合成。

### 3.7 静态库、候选冻结与切分

- **主切分**：时间序 20/80（2,008 历史 / 8,034 在线），与 Krites/SemCache 口径可比；ABCD 官方 8,034/1,004/1,004 只作"复制臂"；另设 7 个 hold-out 子流（1,320 会话，13.1%）做冷启动。
- **候选冻结**：95,129 个 resp 请求 × top-k（history-only 后平均 65.5/100），存 `candidates.parquet`；检索配置/index 版本/hash/tie-break 全部冻结；所有策略同候选。
- **静态库**：只从历史构建；与任何未来会话答案 50-char shingle 重叠=0；E4 灰区与 ΔQ 配对质量单独存表。
- **泄漏检查**：候选池 44.53% test/dev 文本必须过滤；静态库 train→test 泄漏（act 76.5%/plan 80.1%/resp 41.8%/rag 100%）必须消除。

### 3.8 claim、证据与依赖

```text
RespObject {resp_id, version, query_fp, template_id, slot_bindings,
            index_snapshot{retriever_cfg, index_gen, topk[]}, content_created_ts, ...}
Claim {claim_id, resp_id, version, span, claim_type ∈ {fact, slot_fill, numeric,
       derived, procedural, refusal}, evidence_refs[{doc_id,chunk,version,hash}],
       multi_evidence, repairability{repairable|not, reason_code, labeler},
       support ∈ {supported, contradicted, insufficient}}
DepEdge {edge_id, from, to, mode ∈ {HARD, SOFT, NONE}, hard_condition, soft_weight}
```

- 规则引擎在产出 gold action 时同步落 `slot_binding → clause_version`（claim 的主要来源）；
- 寒暄/自由表述无证据 → `no_evidence`；多证据/跨句推理 → 不可局部修复；
- `repairability` 用规则+人工双参考产生，在线 LLM 只做判断，不参与真值。

### 3.9 标签与账本

```text
Label {
  label_id, req_id, candidate_id, candidate_version, protocol_version,
  oracle_basis{clock, t_eval, versions[], state_versions[]},
  safe, reason ∈ {safe, entity_mismatch, policy_superseded, stale_state,
                  acl_denied, insufficient_evidence, irrelevant,
                  data_scope_mismatch, tool_version_mismatch},
  change_kind ∈ {none, content_only, answer_affecting}, harm,
  error_class ∈ {none, reasoning, freshness, acl},
  t_retrieve, correct_at_T, correct_at_t_retrieve,
  hit_type ∈ {exact, signature, semantic, promoted_static},
  stale_exposure{start_t, end_t, serve_count},
  attribution ∈ {object, action, session},
  gold{action, values, evidence[], plan, state},
  cost_split{cache_side, baseline_side, offline_eval}
}
```

- oracle 独立离线进程；标签只用于评测，在线不可读；
- 双参考：`t_retrieve` 与 `T` 各解一次真值 → 分离 freshness error / reasoning error；
- 三命中分离：similarity / correct / fresh；`hit_type × is_paraphrase` 分层报；
- 账本 k=3–5 标注（约 28–48 万行），100 候选池只存文件不逐条标注。

### 3.10 成本与分支重放

- CostOp：lookup / acl_check / version_check / state_check / predicate_check / recheck_all / index_rebuild / repair_llm / verify_judge / regen / evict / background_slot_s；
- 单价表：硬件 + 单价 + 日期 + 模型 digest；`cost_source ∈ {measured, table}`；
- **两臂**：Arm-O（recompute = gold/规则期望，测安全与质量上界）、Arm-R（recompute = 固定模型真实生成，测成本/时延）；
- 配对单元 = 决策步；`initial_state_hash/model_digest/prompt_hash/index_version` 两分支相同；
- 命中分支至少对抽样任务真实生成，否则只能报"估计值"。

### 3.11 更新事件日程（预注册，8 周逻辑时间）

| ID | 时间 | 类型 | 目标 | 2 周窗口缓存答案 | 目的 |
|---|---|---|---|---|---|
| P1 | W3.0 | 流程型 | manage_account | 301 | E5 主 |
| D1 | W3.3 | 文档型 | storewide_query | 406 | E5 主 |
| A1 | W3.6 | ACL 撤销 | checkout 相关 | — | 权限失效 |
| P2 | W4.0 | 流程型 | order_issue | 219 | E5 主 |
| T1 | W4.3 | 阈值型 | product_defect+shipping | ~125 flips | case study |
| M1 | W4.6 | 连续更新 | shipping_issue | ~50–100 | 机制 |
| N1 | W4.8 | 无效果型 | storewide_query | 0 | change≠harm |
| P3 | W5.0 | 流程型 | purchase_dispute | 164 | E5 主 |
| D2 | W5.3 | 文档型 | single_item_query | 434 | E5 主 |
| M2 | W5.6 | 连续更新 | subscription | ~50–80 | 机制 |
| P4 | W6.0 | 流程型 | shipping_issue | 120 | E5 主 |
| N2 | W6.2 | 无效果型 | single_item_query | 0 | change≠harm |
| T2 | W6.3 | 阈值型 | shipping_issue | ~60 flips | 细粒度 |
| A2 | W6.6 | ACL 恢复 | 主管角色 | — | 权限恢复 |
| M3 | W6.7 | 连续更新 | troubleshoot | ~20–50 | 机制（低样本） |

- 主结论用 **6 个主事件（P1–P4 + D1–D2）池化 ≈1,644 个缓存答案**；单事件只报描述；
- 事件时间独立 seed ±2h；W6.7 后 clean-out；
- 事件只发布 doc/version/diff/effective_from，不发布受影响列表（那是被测方法的输出）。

### 3.12 排除与人工标注

| 处理 | 内容 | 规模 |
|---|---|---|
| 排除出 plan/action 真值 | 8 个 FAQ 意图 + 4 个排障意图 | 3,165 会话（31.5%）；可作 resp/rag 背景轨 |
| 人工标注 P0 | oracle 隐变量（12 子流程，可从 gold 反推 75.4%） | 1,696 会话（16.9%） |
| 人工标注 P0 | 退货 receipt 条件 | 538 会话 |
| 人工标注 P1 | 客户自述等待天数（missing） | 261 会话 |
| 人工标注 P1 | 订阅状态（amount/date/active） | 555 会话 |
| 人工标注 P1 | FAQ 答案文本（若要做 rag 真值） | 1,641 条 select-faq |
| 标签审计 | 动作级抽样 | 200–300 |

---

## 4. 评测协议（冻结）

### 4.1 切分

1. 主协议：时间序 20/80（2,008/8,034），冻结 hash；
2. 复制臂：ABCD 官方 8,034/1,004/1,004（单独报告，不与主协议混）；
3. 冷启动层：7 个 hold-out 子流（1,320 会话），history 中 0 次；
4. 实体层：warm（原值）/cold（重映射）两臂。

### 4.2 统计功效

- E2：8,034 在线会话，配对 MDE ≈1.4–1.8%（含 12 检验 Holm）；不是瓶颈。
- E5：6 事件池化 n≈1,644，MDE（Holm）≈2.7–4.7pp；单事件 118–434 → 只描述。
- 质量非劣效：margin 3pp 需 687 判定项；judge 抽 25% 时 margin 4pp。
- κ：双人标注 **600–800 条**（95% CI 半宽 ±0.05），分层按对象类型 × 风险原因 × 事件类型。

### 4.3 其他固定项

- warm-up：绝对收益主数字丢弃前 1,600 在线会话；相对配对差值可用全量；报告十分位曲线；
- seeds：到达/事件 ≥10；策略 ≥3；LLM ≥3；
- 预注册：primary endpoint/MDE/n/事件数/多重比较族/停止规则，hash 进 manifest；
- 公平性：所有基线共享同一 hard gate hash、同一候选、同一成本表；负对照（shuffled dependency / no-update / random invalidation）必须显著差；
- oracle 上界两臂：oracle validity / oracle dependency；报告与本文方法的 gap；
- Flink：10 个失败注入用例（崩溃/重复/迟到/版本倒序/修复中再更新/扩缩容/后台重复/空闲期）。

---

## 5. 冻结与演进机制（避免"以后又改数据"）

### 5.1 语义版本

- **MAJOR**：改切分/键定义/标签语义/成本单位/事件语义 → 必须重跑旧实验；
- **MINOR**：加字段/对象/事件，旧实验可忽略 → 只做 additive；
- **PATCH**：不改语义的修复 → 必须重跑校验并记录。

### 5.2 冻结门（v1.0 发布前全部通过）

| 门 | 检查 | 判据 |
|---|---|---|
| G0 契约 | event schema/IDs/visibility/时间/版本/label/metric/cost/split 写死 | 缺项=0 |
| G1 数据真实性 | 请求/对象/lookup 数量与实测一致；口径表无冲突 | 7 项核心数字全等 |
| G2 泄漏 | 切分互斥、实体重映射、候选 history-only、静态库 shingle=0、gold 不进在线 | 泄漏计数=0 |
| G3 规则引擎 | 覆盖首批 flow；与 gold 一致率报告；200 条审计 κ≥0.8 | 通过 |
| G4 标签 | oracle 独立；双参考；三命中分离；change_kind/harm 可算 | 100% 行有版本；重算一致 |
| G5 候选/静态库 | 冻结文件可复现；灰区/ΔQ 表完整 | hash 一致；样本量达标 |
| G6 功效 | 每主事件≥150 缓存答案；6 事件池化；MDE 达标 | 通过 |
| G7 回放/恢复 | 事件幂等、checkpoint、10 类失败注入 | 通过 |
| G8 复现 | manifest/复现卡/seed/成本表/许可 | 齐全 |

### 5.3 预存"以后加不回来"的产物

- 每请求上下文快照、候选清单与分数（全量 9.5M 槽，history-only 过滤后存储）；
- 全部政策版本与 diff、状态事件、ACL 事件；
- 每 (request, candidate) 标签（k=3–5 为主，另存全候选索引）；
- 分支日志（Arm-O/Arm-R）、成本分项、后台任务事件；
- 外部效度映射字段（ChurnBench/FiscalQA/SemCache/Chutes 的桥接列）。

### 5.4 扩展轨（不改 T1 契约）

| 轨 | 内容 | 作用 |
|---|---|---|
| T2 | vCache SemCache（resp 语义缓存） | 外部效度；E4 口径对齐 |
| T3 | ToolBench/DBBench（真实工具结果） | act 真实工具轨 |
| T4 | ChurnBench + FiscalQA Pro（真实版本事件） | E5 外部效度 |
| T5 | Chutes（真实到达/容量） | E2/E3 系统层 |

---

## 6. 修订后的路线

| 阶段 | 内容 | 时间 | 产出 |
|---|---|---|---|
| M0 | 契约层 + 时间锚 + KeySpec + 切分 + 候选过滤 + manifest | 1 周 | schema v1.0、split、candidate、manifest |
| M1 | shipping/order/account 三 flow 规则引擎 + 标签 + 200 条审计 | 2 周 | 规则库、gold、ledger v1 |
| M2 | 静态库 + claim/证据 + T1-act 构造 + 6 事件日程 | 2 周 | objects、labels、events |
| M3 | 分支重放 + 成本标定 + Flink 契约 + 失败注入 | 1–2 周 | `replay/`、`flink/`、cost profile |
| M4 | 冻结 v1.0 + 统计校验 + 数据卡 | 1 周 | `v1.0` 发布包 |

总计约 6–7 周（比 v0.1 多 2–3 周），但换来的是"不用重造数据"的确定性。

---

## 7. 论文中必须写清的边界

1. T1 是**构造的实验台**，不是自然数据集；所有构造字段与偏差量化；
2. act 在 T1 中是**策略/状态谓词查询**（构造），真实工具结果在 T3 外部轨；
3. T1 的阈值型版本事件是**合成标签**（原始 gold 不可见），只作 case study；主结论用流程型事件；
4. 权限/租户为合成；
5. 与 ChurnBench/FiscalQA/SemCache 只做外部效度与排序相关性，不做"同一数字平移"；
6. 四类对象共时钟 + 逐请求反事实 + 可重算账本，是本文相对现有基准的增量。

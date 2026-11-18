# 自建实验数据集设计方案（暂名 StreamCache-Bench v0.1）

> 定位：不是"新采集的自然数据集"，而是**基于公开数据构造的、可复现的流式智能体缓存实验基准**——一套统一的请求/对象/版本/标签事件流 + 可重算真值的账本 + 构造脚本。
> 目标：支撑第一章 E1–E6 全部实验（四类对象、三种动作、生命周期、依赖更新、流式实现），且每个构造字段可审计、每个自由度可消融。
> 依据：2026-11-18 的 22 个候选数据集核查结论（见同目录《20261118_第一章数据集选型与实验映射分析.md》）。

---

## 0. 结论

**可行，且建议做。** 推荐路线是"一个主场景 + 三条数据轨道 + 一个账本"：

- **主场景**：客服政策（基于 ABCD）——覆盖 resp/rag/act/plan 四类对象，动作级真值最干净，政策版本注入最自然，恰好对应你 1.3.2 的例子；
- **轨道 R（resp 语义缓存）**：vCache SemCache（等价类真值）；
- **轨道 A（act 工具）**：ToolBench/StableToolBench（+ DBBench 作低成本执行环境）；
- **轨道 L（到达/生命周期）**：Chutes 一年 trace 的到达形状与容量参数；
- **外部效度轨道**：ChurnBench（受控版本更新 + ledger 真值）、FiscalQA Pro（真实版本事件）。

工作量：MVP 2–3 周，完整 v1.0 约 6–8 周（不含实验本身）。

**关键定位问题**：不要在论文里宣称"我们提出了一个新数据集/新基准"就完事——那会被问"凭什么是基准"。正确写法是：**"公开数据无法同时提供流式到达、四类对象、版本演化与可验证真值；本文给出一套可复现的构造协议与事件流账本，把构造偏差量化并消融。"** 这样评审可以质疑数据不真实，但无法质疑你没测量它有多不真实。

---

## 1. 需求 → 数据包对应物

| 你的要求 | 数据包中的对应物 | 真值来源 | 校验方式 |
|---|---|---|---|
| 请求按时间到达（流式） | `request_stream`（ts/session/tenant/regime） | Chutes 到达形状缩放 + 合成热点 regime | 到达 CV、KS 检验、日/周周期 |
| 四类缓存对象 | `cache_entry`（type=resp/rag/act/plan） | ABCD 动作与政策；SemCache 等价类；ToolBench 工具结果；ABCD 子流程模板 | 字段完整性 + 抽样审计 |
| 三种动作 | `decision`（reuse/verify_then_reuse/recompute）+ 成本档 | 标注 `safe/unsafe` + 成本 profile | 错误复用率、成本分项 |
| 缓存价值（时延/质量/后台） | `cost_profile` + `quality_label` + 后台预算配置 | 实测小样本 + judge + 审计 | 估值 vs 实测偏差 |
| 生命周期（准入/保留/淘汰） | 条目 `size/age/demand/deps/acl` + 容量与预算旋钮 | 由事件流重放产生 | 容量扫描、churn |
| 来源版本更新/依赖传播 | `doc_registry` + `update_event` + `dep_edge` | 政策规则重算、ChurnBench ledger、FiscalQA 版本区间 | 失效 P/R、陈旧暴露 |
| 权限/租户 | 合成 `tenant/role/acl` + `acl_change` 事件 | 构造（论文声明） | 越权复用率 |
| 可自动/半自动质量真值 | `label`：动作/证据/回答三层 | 规则引擎、等价类、qrels、人类偏好、judge | 人工审计 κ |
| 可复现 | 构造脚本 + 固定 seed + 数据 hash + append-only ledger | — | 他人可重建 |

---

## 2. 总体架构：三层 + 一包

```
到达层（T）  Chutes/FreeInference/Mooncake 的 inter-arrival 形状
              ↓ 缩放、regime 切换、session 绑定
内容层（C）  ABCD（主）/ SemCache（resp 轨）/ ToolBench（act 轨）
              ↓ 对象抽取、近重复注入、成本校准
版本层（V）  ABCD 政策编辑（主）/ ChurnBench（受控）/ FiscalQA（真实版本外部效度）
              ↓ doc_registry + update_event + dep_edge
账本层（L）  每个请求 × 每个候选对象的 safe/unsafe 标签 + 金标动作/证据 + 原因
```

一个数据包 = `sources/`（原始下载）+ `build/`（构造脚本）+ `out/`（事件流与账本）+ `eval/`（基线、指标、统计校验）。

---

## 3. 主场景：ABCD-政策流（覆盖 E1/E2/E5 主体）

### 3.1 请求流生成

1. **会话切分**：按 `convo_id` 分组，60% 历史（构建静态库与统计）/ 20% 验证 / 20% 测试；测试答案不得进入静态库。
2. **到达时间**：从 Chutes 取 1–2 周 `started_at` 的 inter-arrival 序列，整体缩放到目标 QPS（如峰值 5 req/s），保留突发形状；每个会话的首请求按目标速率到达，后续轮次按会话内思考时间（从会话长度统计拟合，指数/对数正态）推进。
3. **热点 regime**：3 个阶段（常态 / 促销或故障 / 政策变更期），每个阶段的 subflow 需求服从不同参数的 Zipf；切换时刻固定；报告 Jaccard/JS 漂移。
4. **租户与权限**：`tenant_id` 按会话分组（20 个），`role` ∈ {一线客服, 资深客服, 主管}；政策文档按角色加 `acl_scope`；插入 ACL 变更事件（角色撤销/租户迁移）测越权复用。

### 3.2 四类对象怎么从 ABCD 来

| 对象 | 从 ABCD 抽取 | key | value | 依赖 |
|---|---|---|---|---|
| `resp` | 客服回复模板（`delexed` 句 + 槽值；`utterances.json` 提供近义表达） | 意图 + 槽值规范化 + 政策版本 | 回复模板/文本 | 政策版本 + 订单/会员状态 |
| `rag` | 政策文件 `guidelines.json` 拆成条款级文档（55 子流程 + FAQ + 动作说明，约 120–150 条），展开为自然段，加干扰文档至 400–600 块 | 查询意图 + 实体 | 条款块（带 doc/version/effective_from） | 来源版本 + 权限 |
| `act` | 账户/订单/商品查询动作（30 个动作中可只读的部分；scenario 提供参数与确定性返回） | 工具名 + 规范化参数 + 数据快照版本 | 查询结果（JSON） | 业务数据快照（可注入订单状态变化） |
| `plan` | 子流程（55 个）展开为参数化步骤模板（步骤、工具、前置条件、槽位） | 任务类型 + 阶段 + 槽位类型 | 计划模板 | 政策版本 + 会员/订单前置条件 |

### 3.3 政策文档与版本

- 每个子流程一个 `doc_id`，原始政策为 v1；按受控规则生成 v2–v5，每版带 `effective_from`；
- 编辑类型（四种，覆盖"语义最小改动"到"结构重组"）：
  1. 数值阈值：退货窗口 90→60 天、升级费 $20→$30、免运费取消；
  2. 分支增删：新增"金卡每季度限 2 次免费退货"；
  3. 权限条件：`gold members always get extension` → `only if ≤2 days late`；
  4. 条款迁移：把某动作从 `product_defect` 移到 `purchase_dispute`。
- 用**规则引擎**对 `(scenario, 政策版本)` 重算应执行动作序列与槽值 → 新版本下的金标；抽样 200 例双人审计报 κ。
- 记录 `dep_edge`：`doc_version → rag chunk → resp claim → plan step`，以及 `doc_version → act 结果（如"是否可退"）`。

### 3.4 act 的状态版本

- `scenario` 本身提供确定性的账户/订单/商品字段；把"订单状态变化"（未发货→已发货→已签收→已退）作为 `update_event` 注入，产生数据版本 v1..vk；
- act 缓存复用条件 = 工具名 + 规范化参数 + 数据版本一致；动态数据（如会员状态）走 `verify_then_reuse` 分支；
- 记录每次调用的实测耗时（本地 mock/脚本），作为 `cost_profile`。

### 3.5 近重复注入

- **天然重复（R0）**：同一 subflow + 同槽值组合的会话天然出现；FAQ 池有固定问法；
- **簇内重采样（R1）**：只改重复次数，不改相似度结构；
- **受控改写（R2）**：用 `utterances.json` 的真人改写池优先，不足时用 LLM 改写（记录模型/prompt），按 λ∈{0,10,25,50}% 注入；
- 三道防线：注入对相似度不得高于天然对中位数；换 1–2 个改写模型重跑；保留 λ=0 臂作下界。

### 3.6 标签账本

每个 `(请求, 候选对象)` 生成一条标签：

```json
{"req_id":"r000123","object_id":"resp_0451","type":"resp",
 "safe":0,"reason":"policy_superseded","detail":"return_window 90→60",
 "gold_action":"deny_return","gold_evidence":["policy_gold_07_v3"],
 "quality":2,"stale_age_s":86400}
```

`reason` 枚举：`safe / entity_mismatch / policy_superseded / stale_version / acl_denied / insufficient_evidence / irrelevant`。这样错误复用可分解，论文能报每类风险的比例与代价。

---

## 4. 轨道 R：resp 语义缓存（基于 SemCache）

- 内容：SemCacheLMArena（约 6 万，3,500 语义类）+ SemCacheSearchQueries（约 15 万）；
- 到达：Chutes 形状缩放；
- 真值：类 ID 等价（等价类 oracle）+ LLM judge 抽样校准；
- 用途：E1（语义潜在命中率、错误率—命中率曲线）、E4（静态层 20%/80% 切分、灰区、异步验证提升，复刻 Krites 口径）；
- 边界：无文档版本/权限，只做 resp 层，不与主场景混报。

---

## 5. 轨道 A：act 工具（基于 ToolBench）

- 内容：ToolBench 的 `toolenv` 本地 API server（或 StableToolBench 虚拟 API）；
- 对象：工具名 + 规范化参数 + 返回；按 `api.py`/HTTP method 分只读/写；
- 真值：ToolEval pass/win（抽样）+ 参数级精确匹配；
- 版本：用 schema 哈希/快照日期当工具版本；注入"参数不变但返回变化"的更新事件测 `verify_then_reuse`；
- 用途：E1（act 精确重复率、只读比例、复用收益上界）、E2（act 容量实验）、TicToc 只作 verify 决策标签源。

---

## 6. 轨道 L：到达与生命周期（基于 Chutes）

- 从 91 GB parquet 抽 1–2 周子集（DuckDB 列查询），保留 `started_at/completed_at/it/ot/ct/ttft/user/model/instance`；
- 生成"容量—TTL—后台预算"扫描参数（工作集 25%/50%/75%）；
- 用途：E2 的容量/淘汰/churn、E3 的吞吐/P95/P99 与 Flink 恢复；**只报系统层结论，不报语义正确性**。

---

## 7. 外部效度轨道

| 轨道 | 数据 | 用途 | 边界 |
|---|---|---|---|
| V1 版本更新受控 | ChurnBench（MIT，docker） | 验证失效/刷新策略；ledger 双参考（freshness vs reasoning error） | 合成企业域，无权限 |
| V2 真实版本事件 | FiscalQA Pro（209 题，法语税法） | 真实"条文—版本—生效区间"上复核结论 | 法域窄、无请求流 |
| V3 证据支持 | RAGTruth（词级幻觉标签） | E1 错误命中代价、主张核验 | 无时间/版本 |
| V4 计划 | ABCD 子流程 + ToolBench DFSDT +（可选）τ²-bench | plan 模板复用与回退 | 无生产流 |

---

## 8. 事件流 schema（统一、可回放）

```text
request       : req_id, ts, session_id, tenant_id, role, text, history_len, regime
lookup        : req_id, object_type, candidate_id, score, key
cache_entry   : object_id, type, key, content_ref, size_bytes, created_ts,
                deps[{doc_id,version}|{snapshot}], acl_scope, age_policy
decision      : req_id, object_id, action(reuse|verify_then_reuse|recompute),
                verify_cost_ms, total_ms, outcome
update        : update_id, ts, type(policy|record|acl), target_id, from_v, to_v
label         : req_id, object_id, safe, reason, gold_action, gold_evidence, quality
cost_profile  : object_type, op, p50/p95_ms, tokens, measured_on
```

所有事件只追加；任意时刻的状态由 `request/update/decision` 按 ts 重放得到；标签不参与在线决策。

---

## 9. 规模与切分（建议）

| 项 | 目标 |
|---|---|
| 会话 | 10,042（ABCD 全量），历史 60% / 验证 20% / 测试 20% |
| 请求 | 约 8–12 万（按平均轮数估算），LLM 触达实验抽 2–3 万 |
| 文档 | 55 子流程 + FAQ + 动作说明 ≈ 120–150 条，扩展到 400–600 块；5 个版本 |
| 更新事件 | 4 轮政策更新（每轮 3–8 文档）+ 2 轮业务数据变化 + 2 轮 ACL 变更 |
| regime | 3 个热点阶段；每个阶段稳定 ≥ 1 周逻辑时间 |
| 种子 | 3–5 个；固定切分 |
| 磁盘 | 原始 ABCD 37 MB + SemCache 若干百 MB + Chutes 子集数 GB；可控 |

---

## 10. 构造协议参数（全部作为实验自变量）

- `lambda_inj`（重复注入比例）：0/10/25/50%；
- `update_rate`（每文档每周更新次数）：低/中/高；
- `regime_interval`（热点切换间隔）：短/中/长；
- `ttl`：取自实证网格 {30s, 3h, 15h, 1d, 7d, 14d, 28d}；
- `capacity`：工作集 25%/50%/75%；
- `background_budget`：每窗口 judge 调用配额（0/小/中/大）；
- 质量门：δ（错误率上限）与 λ_Q/λ_B 权重。

**预注册**：所有主结论的参数只在验证集确定，测试集只跑一次；`lambda_inj=0` 臂必报。

---

## 11. 质量与效度检验

1. **统计对齐**：把构造流与来源逐项对比——平均 RPS/CV、会话长度分布、精确重复率、语义潜在命中率@τ、top-1%/10% 覆盖率、文档更新率、命中时年龄分布；报相对误差/KS 距离。
2. **人工审计**：按灰区分层抽 200–500 条，双人标注，报 κ；judge 与生成器分离。
3. **双参考真值**：动作/证据/新鲜度分别有规则真值与 judge 真值，报两者差异。
4. **消融臂**：无注入 / 无更新 / 无权限 / oracle-judge / 真实 judge，用于量化构造带来的效应。
5. **防泄漏**：按会话/任务族切分；测试请求的答案与后续版本不得进入历史；静态库只从历史构建。

---

## 12. 发布与许可

- **发布**：构造脚本、schema、ledger、派生标签、统计报告、固定 seed 与 hash；
- **不发布**：受第三方许可限制的原始内容（如 ShareChat NC、MiroVerse NC 等）；ABCD（MIT）、ToolBench（Apache-2.0）、SemCache（核对 HF 条款）、Chutes（CC BY 4.0）、FiscalQA（CC-BY-4.0）、ChurnBench（MIT）可按各自条款再分发或只给下载脚本;
- 论文中逐项声明：哪些字段来自源数据、哪些是构造、哪些是标注。

---

## 13. 阶段计划

| 阶段 | 内容 | 时间 | 产出 |
|---|---|---|---|
| MVP-1 | ABCD 政策流：文档/版本/请求/对象/标签/账本 | 2–3 周 | `out/v0.1` 可跑 E1/E2/E5 |
| MVP-2 | Chutes 到达 + regime + 权限 + 轨道 R（SemCache） | 2 周 | 可跑 E2/E3/E4 |
| MVP-3 | 轨道 A（ToolBench/DBBench）+ 外部效度（ChurnBench/FiscalQA）+ 统计校验 | 2–3 周 | 冻结 v1.0 + 报告 |
| 维护 | 修 bug、补文档、兼容 Flink 回放器 | 持续 | — |

**轻量版（若时间不足）**：只做 MVP-1 + Chutes 到达（约 4 周），ToolBench 只做离线统计，ChurnBench/FiscalQA 只做校准实验；仍可支撑六组实验，但 act 轨保真度下降，需在 limitations 说明。

---

## 14. 风险与论文写法

| 风险 | 论文中的处理 |
|---|---|
| 构造数据外部效度 | 用 FiscalQA/ChurnBench 做外部效度；明确"构造"标签；报统计偏差 |
| 规则引擎真值错误 | 抽样审计 + κ；规则与 judge 双参考 |
| 自造重复偏置 | λ=0 臂、相似度分布对齐、多生成器 |
| 政策库小、检索饱和 | 展开自然段 + 干扰文档；报检索难度分布 |
| 评审质疑"为你的方法定制" | 协议先冻结、参数验证集确定、报 oracle 上界与负结果区间 |
| 工作量 | 先 MVP-1，按实验进度增量冻结；不要一次性追完整版 |

---

## 15. 与已有数据集的关系

- **被包进来**：ABCD（主场景）、SemCache（resp 轨）、ToolBench（act 轨）、Chutes（到达轨）；
- **只作外部效度/校准**：ChurnBench、FiscalQA Pro、RAGTruth、TicToc、AgentSim ATC、Search Arena；
- **不进入数据包**：PasarBench（不存在）、AitW、AgentBank、Nemotron/MiroVerse/Ko-Agent（SFT 样本池）、ShareChat（NC）、UserSim（工具）。

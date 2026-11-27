# events/：动机实验的输入流（v0.3.0）

四类产物 + 两条辅助流，全部由 `build.py` 确定性生成（`common/seeds.py` 取随机、`common/io.py` 写盘、
`common/ids.py` 出 ID）。只有 `real_calibration_300.template.csv` 由 `calibrate.py` 实测生成。

| 文件 | 行数 | 说明 |
|---|---|---|
| `docs_versioned.jsonl` | 6000 | `knowledge/docs.jsonl` 的 `docs_versioned` 投影，内容逐行不变 |
| `request_stream.jsonl` | 3000 | 主请求流（= `streams/seed42.jsonl`，逐字节相同），带 `cluster_id` |
| `request_context.jsonl` | 3000 | 主请求流 sidecar：源题、语义簇、改写序号、租户、复用标记、权限负例标记 |
| `update_events.jsonl` | 40 | 主更新：双时间戳；6 条 `negative_control` 负对照 |
| `act_plan_pool.json` | 100 act / 60 plan | 只读工具池与计划模板池 |
| `streams/seed42…46.jsonl` | 各 3000 | 5 个种子副本，热点迁移时刻 9/7/10/8/11 时 |
| `streams/long_01,02.jsonl` | 各 5000 | 长流，跨度仍是 00:00–18:00，迁移 5 时 / 13 时 |
| `calibration_sample.jsonl` | 300 | 校准抽样清单（req_id / timestamp / snapshot / task_id） |
| `real_calibration_300.template.csv` | 300 | 只有 `t_act_ms` 是实测，其余列留空待作者回填 |
| `CALIBRATION.md` | — | 哪些列是 measured、其余列怎么回填 |

## 请求流的结构

- **题**：200 题 × 3 种中文改写（同题不同说法，内容与口径一致）= 600 种文本，全部出现。
- **簇**：40 个语义簇（`cls_*`），取自 `tasks.jsonl`；同题的所有改写、7 条流与 sidecar 都带同一
  `cluster_id`，供 1.2.2 的簇内反馈借用与同簇难负例使用。
- **主张**：`gold_fact_spans` 逐条取自该题 `truth.claims` 的主张层真值（每题 1–5 条，
  全流分布 1:485 / 2:803 / 3:771 / 4:602 / 5:339），`gold_doc_ids` 取该题证据文档并集。
  1288 条请求（42.9%）带 1–2 条主张、1712 条（57.1%）带 3–5 条，直接决定 ρ 的分母。
- **到达**：18 小时按小时配额铺开（`HOUR_WEIGHTS`，不是均匀分布）；前 6 小时热点组 A 占该时段
  59.93%，6:00–9:00 为迁移过渡窗，第 9 小时后热点组 B；其余请求来自 120 道长尾题（按覆盖牌堆
  + Zipf 混合抽取，保证 120 题都出现）。
- **复用**：同一题的到达会优先复用已有的（改写, 租户）组合，标记复用率 35.8%，用于构造安全复用样本。
- **快照**：`< 06:00`→`v0`、`06:00–12:00`→`v1`、`≥ 12:00`→`v2`，`as_of` 即该快照生效时刻，
  不存在未来快照泄漏（`selfcheck.py` 与 `verify.py --stage P4` 都校验）。
- **对象类型**：单表口径题 `["rag","resp"]`、连接执行题 `["act","resp"]`、
  嵌套多步题 `["plan","rag","act","resp"]`。`plan_id` / `act_key` 按题确定性选取，同题恒定。

## 租户与权限负例怎么落地

`request_stream.schema.json` 是冻结契约，没有 tenant 字段，因此三个租户只能通过 `permission`
落地，完整映射写在 `request_context.jsonl`：

| 租户 | 占比 | 请求 `permission` |
|---|---|---|
| `tenant_public` | ~40% | 沿用题目 `permission` |
| `tenant_staff` | ~35% | 沿用题目 `permission` |
| `tenant_restricted` | ~25% | 一律 `restricted` |

`permission_negative = (请求 permission ≠ 该请求 gold 文档的最高 permission)`，共 1603 条。
其中 `tenant_restricted` 请求 public/staff 文档构成「越域/过度限制」负例。
**不存在的类型**：请求权限低于其 gold 文档的「硬拒绝」样本 —— 因为题目的 `permission` 恒等于
其证据文档的最高权限（`selfcheck` 校验过），在不改 tasks 的前提下造不出这类样本。

## 更新事件：双时间戳、局部修复比例与负对照

实验 E 要观测「证据更新 → 缓存回答失效 → 局部修复」，因此更新要命中两层证据：

- **R1 文档级**：`doc_id` 至少被 1 条请求的 `gold_doc_ids` 引用 —— 缓存里得先有这份证据；
- **R2 主张级**：至少一个 `changed_chunk_id` 被某条请求的 `gold_fact_spans` 引用 ——
  被推翻的必须是某个具体主张，才谈得上局部修复。

**双时间戳**（v0.2.0）：`effective_at` 恒等于该 `(doc_id, new_ver)` 在 `docs_versioned.jsonl` 中的
`updated_at`（06:00 / 12:00），`timestamp` 是系统接收/通知时刻，`notification_delay_s =
timestamp − effective_at`。40 条延迟落在 **0.033–3.000 h，中位 1.612 h**（参考 0.03–3.08 h / 1.6 h），
对应 1.3.2 的「通知窗口」与 1.4.1「已知过期为 0、窗口内静默过期可观测」的区分。

**局部修复比例 ρ**（v0.2.0）：受影响 (更新, 请求) 对中，ρ = 命中主张数 / 该请求主张总数；
ρ<0.5 记局部修复、ρ≥0.5 记大改。当前 **1102 对：局部修复 805（73.05%）、大改 297（26.95%）**，
落在 params 的 [0.65, 0.75]。单块更新下单个请求最多命中 1 条主张，ρ 的分母即该请求主张数：
主张数 3–5 的请求被命中即局部修复（805 对），1–2 条的请求被命中即大改（39 + 258 对）。
其中 **15 条更新的变更块被 ≥2 条不同主张引用**（最多 18 条），保留“命中多主张”的大改样本。

**影响面**：文档级影响 34/40 条更新（累计 2791 条受影响请求）；主张级影响 30/40 条
（累计 1102 对、去重 874 条请求）；**事件之后仍有后续请求的：文档级 34 条、主张级 29 条**。

### codebook_revision 的 6 条是「无关更新」负对照组，不是缺陷

请求流只引用字段卡 / 白皮书 / 指标卡，**从不引用 note**（码表说明 / 血缘说明），而码表说明全部是
note。因此 `codebook_revision` 在冻结的 `tasks` 与请求流下不可能命中任何请求。这 6 条**刻意保留为
`negative_control: true` 的负对照**，用来检验失效策略的**误触发率**：策略不应因为一条与所有缓存条目
无关的码表更新而让任何缓存失效。它们 `answer_impact` 一律 `unchanged`、文档级影响为 0。
其余 34 条必须命中真实请求，任何一条非负对照更新零影响都视为构造失败（`verify.py` 与
`selfcheck.py` 各自校验：非负对照零影响必须为 0，负对照上限 8 条）。

名额分配（按“有命中的候选数”自动分配，非人工指定）：
`schema_change 14 / metric_revision 8 / data_row_change 6 / lineage_switch 6 / codebook_revision 6`。

### 类别与 answer_impact 的判定

类别看「变更块讲的是什么」：指标卡→`metric_revision`；白皮书结构→`schema_change`；
白皮书关联说明/血缘说明→`lineage_switch`；note 码表说明→`codebook_revision`；其余→`data_row_change`。
`answer_impact`：变更块被某请求主张引用→`changed`（30 条）；仅文档级影响、或负对照→`unchanged`（10 条）。

### 时间

事件不得早于 `effective_at`，且尽量落在「首条引用之后、最后一条引用之前」，保证更新之后还有请求可被
失效。40 条落在 **06:03–15:00**（跨 8.9 小时、覆盖 8 个小时、单小时最多 7 条），`u0001…u0040`
按时间升序重排。只使用 `modify_number / modify_text / delete_chunk` 三类记录
（`add_chunk` 的新增块不在 `old_ver` 里，无法通过“变更块属于 old_ver”的引用校验）。

## act / plan 池（v0.2.0 异质性）

- **act**：100 个只读工具（`tool_001…tool_100`），`act_cost` 按工具类型分档（0.02–0.77）。
  `downstream_tools` 由 `contracts/lineage.json` 的血缘图推导：该 act 读的每张表的**全部下游表**
  上可执行的工具都算它的下游工具；查询类 act 另外登记**直接消费同一张表的连接工具**；
  去重排序后最多 4 个（不把整条血缘链无限展开）。
  结果：**非空 80/100 = 80%**，0/1/2/3+ 四档 = **20 / 20 / 7 / 53**。
- **plan**：60 个计划模板（`plan_01…plan_60`），3–6 步（16/16/15/13），
  `completion_rate` 按步骤数落进 `params.act_plan.plan_completion_by_steps` 的分层区间，
  均值 **3 步 0.936 / 4 步 0.850 / 5 步 0.844 / 6 步 0.750**（随复杂度单调下降）。

## 校准模板

`real_calibration_300.template.csv` 的 300 个 `req_id` 来自 `calibration_sample.jsonl`（先保证 200 题
各一条，再补 100 条不同快照/改写）。v0.2.0 重建后 req_id 序列未变，因此**保留原文件与已实测的
`t_act_ms`**（本机真实执行 gold_sql 的中位数，见 `CALIBRATION.md`），其余五列继续留空等作者回填。

## 复现

```bash
python dataset/events/build.py        # 生成全部构造产物 + MANIFEST（不改已实测 CSV）
python dataset/events/calibrate.py    # 只有在 req_id 集合变化时才需重测（会改 CSV 哈希）
python dataset/events/selfcheck.py    # 契约/规模/结构/一致性/重跑比对
python dataset/verify/verify.py --stage P4
```

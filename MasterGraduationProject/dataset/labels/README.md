# P5 安全复用标签（双视角）与分支配对（v0.3.0）

本目录只由 `agent-label` 写入。所有判定只读 `events/`、`tasks/`、`db/snapshots/`，
执行走 `db/executor.py`（只读三层保护），结果比对走 `db/compare.py`（列序/行序无关、数值 6 位）。

v0.2.0 依据 `audit_v010_report.json` 的两个问题重建：

1. 旧标签只有一个 `safe`，把“真值已过期”与“系统还没收到通知”混为一谈。通知延迟实测
   0.03–3.0 小时（中位 1.64），窗口内两个视角会分歧；本版拆成 `safe` / `safe_system`
   两列并新增 `divergence_reason`。
2. 旧 N1/N4/N6 负例与正例的向量相似度仅 0.28–0.38（正例 0.955），过于容易区分。
   本版把这三类全部改为**同一 `cluster_id`** 内两道题的请求对（N1 30/30、N4 30/30、
   N6 25/25 同簇，合计 85/85 = 100%，验收下限 80%）。

## 1. 产物与命令

| 文件 | 行数 | 内容 | 判定方式 |
|---|---|---|---|
| `safe_reuse.jsonl` | 300 | 150 条安全（140 条双视角一致 + 10 条系统保守误失效）+ 150 条负例（N1 30 / N2 30 / N3 35 / N4 30 / N5 0 / N6 25） | 双视角谓词判定 |
| `branch_pairs.jsonl` | 120 | 全路径 vs 缓存路径分支配对，本地段时间实测 | 程序实测 |
| `to_review.csv` | 60 | 人工复核清单（五类负例各 10 + 安全样本 10，其中 5 条为系统保守误失效） | 程序初判，待人工确认 |
| `MANIFEST.json` | — | `{文件: {rows, sha256}}` | 构建脚本生成 |
| `build.py` | — | 确定性构造器（双视角谓词 + 配对选择 + 落盘） | — |
| `selfcheck.py` | — | 独立重算双视角谓词、复核 reasons、核对分布/同簇比例/确定性 | — |

```bash
python dataset/labels/build.py        # 约 5 s，重写四个产物
python dataset/labels/selfcheck.py    # 17 项检查，全绿退出码 0
python dataset/verify/verify.py --stage P5
```

## 2. 双视角定义（v0.2.0 核心，全部按时间戳判定）

时间轴：`docs_versioned.updated_at` 是“文档新版本生效时刻”（≡ `update_events.effective_at`）；
`update_events.timestamp` 是“系统接收/通知时刻”，两者之差是 `notification_delay_s`。

可见版本**只按时间戳取**，不使用 `update_events.old_ver`：

```
notified_at(doc, v) = update_events[doc, v].timestamp   若 (doc, v>=2) 有对应事件
                    = docs_versioned[doc, v].updated_at 否则（批量快照版本）
truth_ver(doc, t)   = max{ v : updated_at(doc, v) <= t }   # 真值可见版本
sys_ver(doc, t)     = max{ v : notified_at(doc, v) <= t }  # 系统可见版本
```

对缓存请求（`cached_req`）与待服务请求（`req`），两个视角各自比较同一批
`cached_req.gold_doc_ids` 在两个时刻的可见版本：

| 字段 | 视角 | 判定 |
|---|---|---|
| `safe` | 真值 | 对每个 `cached_doc_ids`：`truth_ver(doc, t_cached) == truth_ver(doc, t_req)` |
| `safe_system` | 系统 | 对每个 `cached_doc_ids`：`sys_ver(doc, t_cached) == sys_ver(doc, t_req)` |
| `divergence_reason` | — | 两视角不同时写 `system_stricter_window`；相同写 `""` |

两个视角都还要求：**同一题目**、**证据集一致**（`cached_req.gold_doc_ids == req.gold_doc_ids`）、
**权限相容**（`priv(req) >= priv(cached)`）、**时间窗一致**（题目 `time_window` 相同）。

**单调性方向**：`sys_ver(t) <= truth_ver(t)`，且本数据的批量升版即时通知
（无事件版本的 `notified_at = updated_at`），所以“系统认为版本没变”必然意味着
“真值也没变”：

```
safe_system = True  ⇒  safe = True        （300/300 成立，selfcheck 逐行断言）
```

反方向不成立：`safe=True, safe_system=False` 是**系统保守误失效**——条目事实上仍然正确，
但缓存落在通知窗口内（系统当时看到旧版），请求发生在通知之后（系统看到新版），
系统据此把仍然正确的条目判为过期。这是可测量的管理成本，不是数据缺陷。

## 3. 通知延迟窗口与 `system_stricter_window`

- 40 条主更新事件中，`(doc_id, new_ver)` 有事件的版本用事件 `timestamp` 作为 `notified_at`；
  其余版本用 `updated_at`。`docs_versioned.jsonl` 的 2000 篇文档各有 3 个版本，其中 40 个版本
  有事件（覆盖 35 篇文档，5 篇有两个版本事件）。
- 实测延迟 120 s–10,800 s（0.03–3.0 h，中位约 1.64 h）；06:00/12:00 两个生效时刻各有
  18/22 条事件，`timestamp` 落在 06:03–15:00。
- 分歧样本必须满足：`effective_at <= cached_req.timestamp < notified_at <= req.timestamp`，
  且同一题、证据集一致、权限相容、时间窗一致。本版 10 条，全部为 `safe=True, safe_system=False`，
  `divergence_reason = system_stricter_window`。
- **为什么没有 `safe=False, safe_system=True` 方向**：该方向要求缓存建立于生效时刻之前、
  请求落在通知窗口内，同时 `cached_doc_ids` 里每个文档的系统可见版本都不变。但 2000 篇文档
  在 06:00/12:00 都批量升版，只有 35 篇有延迟事件；3000 条请求中没有任何一条的
  `gold_doc_ids` 全部落在这 35 篇里（每条请求至少含 1 篇批量升版文档），所以跨生效边界的
  缓存必然见证至少一个文档的系统版本变化。全量同题请求对按时间戳谓词统计：
  `(T,T)=17,454`、`(F,F)=26,223`、`(T,F)=2,900`、`(F,T)=0`。

## 4. 双视角谓词的五条件

| 记号 | 条件 | 程序化判定 | 数据来源 |
|---|---|---|---|
| A | 同一题目 | `task_id(cached) == task_id(req)` | `events/request_context.jsonl` |
| B | 证据集一致 | `cached.gold_doc_ids == req.gold_doc_ids` | `events/request_stream.jsonl` |
| C | 可见版本未变 | 每个 `cached_doc_ids` 的 `truth_ver`（`safe`）或 `sys_ver`（`safe_system`）在缓存/请求两时刻相等 | `events/docs_versioned.jsonl` + `events/update_events.jsonl` |
| D | 权限相容 | `priv(req.permission) >= priv(cached.permission)` | 请求 `permission` 字段 |
| E | 时间窗一致 | 两题目 `time_window` 完全一致（起止 ISO 字符串相等） | `tasks/tasks.jsonl` |

- **权限序**：`public=1 < staff=2 < restricted=3`。`restricted` 可见文档集合最大（限制最少），
  `public` 最小。缓存结果只能给“至少一样可见”的请求复用；反向复用会把宽权限内容喂给窄租户。
- `request_stream.jsonl` 没有 `task_id`，题目关联取自同目录的 `events/request_context.jsonl`
  （`req_id → task_id/variant/permission`），只读引用，不复制。
- **答案一致性不进 safe**：`safe` 只刻画“证据版本是否变化”。答案是否仍相等
  （`compare` 复算）只作为 N3 的“看起来对”子族与 `reasons` 的描述信息，不改变 safe 判定。

## 5. 字段归属

| 字段 | 含义 | 判定者 |
|---|---|---|
| `pair_id` | `b00001…`，与 `branch_pairs` 共用配对号空间（标签 1–300，分支 301–420） | 程序 |
| `req_id` / `cached_req_id` | 待服务请求 / 缓存来源请求 | 程序 |
| `task_id` | `req` 的题目 | 程序 |
| `cached_doc_ids` | 缓存请求引用的全部证据文档 | 程序（来自 events） |
| `safe` | 真值视角 A∧B∧C_truth∧D∧E | **程序**（`view_judge(view="truth")`） |
| `safe_system` | 系统视角 A∧B∧C_system∧D∧E | **程序**（`view_judge(view="system")`） |
| `divergence_reason` | 两视角不同的原因；相同为空串 | 程序 |
| `negative_type` | `none` 或六类负例（第 8 节优先级，用真值视角分类） | **程序** |
| `reasons` | 可回溯证据串（第 9 节语法） | **程序**，每串都能被 `selfcheck` 解析回原始数据 |
| `judged_by` | 恒为 `predicate` | 固定值 |
| `confidence` | 恒为 `1.0`：布尔量全部可由程序判定，无模型参与 | 固定值 |

人工复核只针对 `to_review.csv` 的 60 条抽样，用来看“谓词判负是否与人的直觉一致”，
不参与标签生成；人工结论若与谓词冲突，应改谓词而不是改标签。

## 6. 难负例：同簇构造（N1/N4/N6）

先按题目的 `cluster_id`（40 个语义簇，每簇 3–6 道题，簇内题目共享证据文档）取**同簇的两道题**，
再在两题的请求之间按时间顺序取请求对：

| 类别 | 题级构造 | 条数 | 同簇 / 题对数 / 簇数 | 主要缺陷 | 说明 |
|---|---|---|---|---|---|
| `N1_entity_mismatch` | 同簇、同时间窗、两侧 `metric_refs` 非空且**不相交**、链条互相覆盖 | 30 | 30/30，24 个题对，18 簇 | A（不同实体） | B/C/D/E 不强制，构造主线是“问的是另一个实体” |
| `N4_time_window` | 同簇、**共享同一 `metric_ref`**、时间窗不同 | 30 | 30/30，28 个题对，17 簇 | E（时间窗不同） | 必然同时不满足 A |
| `N6_reasoning_chain` | 同簇、**共享同一 `metric_ref`**、同一时间窗，缓存对象链条更短/不可比 | 25 | 25/25，15 个有序题对，13 簇 | C（推理链不足） | 必然同时不满足 A |

同簇保证两道题意图相近、说法不同（同一主题的不同实体/时间窗/推理深度），字面与语义相似度
显著高于旧版跨簇构造；`reasons` 里统一带 `same_cluster:cls_…`，selfcheck 逐行核对
`req_id` 与 `cached_req_id` 的 `cluster_id` 相同且与理由串一致。

## 7. N2 / N3 构造（维持同题）

| 类别 | 构造 | 条数 | 违反条件 |
|---|---|---|---|
| `N2_permission` | 同一道题、证据集一致、两视角版本均未变、时间窗一致；缓存请求权限更宽（`restricted→staff` / `restricted→public`） | 30 | D |
| `N3_stale_but_looks_right` | 同一道题、证据集一致、权限相容、两视角**都**看到版本变化 | 35 | C（两视角同时过期） |

N3 的 35 条按“看起来还对”的程度分两个子族（`reasons` 可区分）：

| 子族 | 含义 | 条数 |
|---|---|---|
| `answer_equal` | 引用块变了，但两份快照上 gold_sql 的规范化结果仍相等（最危险的一种） | 25 |
| `answer_changed` | 版本与答案都变了（跨快照边界的数据行更新） | 10 |

**系统保守误失效为什么不计入 N3 负例**：`safe=True, safe_system=False` 的行按定义在真值视角
是安全复用（第 2 节），归入 150 条“安全”里；它们与 N3 的区别是“系统单方面收紧”。
`to_review.csv` 中抽 5 条给人工确认这一分类。

**N5 为什么是 0**：本数据集没有写操作。`events/act_plan_pool.json` 的 100 个 act 全部
`readonly: true`、`downstream_tools` 为空；`db/executor.py` 的语句层拒绝 INSERT/UPDATE/DELETE
等全部写关键字，`request_stream.jsonl` 也没有写语义字段。因此不存在可用数据构造的副作用负例，
按任务约定取 0 条并在本节说明，不写入任何“说明性”假样本。

## 8. 负例分类优先级（真值视角）

```
safe = A ∧ B ∧ C_truth ∧ D ∧ E
none        若 safe
N2          否则若 ¬D
N4          否则若 ¬E ∧ ¬A ∧ 共享 metric_ref
N3          否则若 A ∧ ¬C
N6          否则若 ¬A ∧ req.obj_types ⊋ cached.obj_types
N1          否则
```

## 9. `reasons` 语法与回溯

| 前缀 | 例子 | 复核方式（`selfcheck` 独立重算） |
|---|---|---|
| `same_task` | `same_task:q153` | 两请求 task_id 相同 |
| `task_mismatch` | `task_mismatch:q030->q047` | 两侧 task_id 与串一致且不同 |
| `same_cluster` | `same_cluster:cls_finance_cost` | 两请求的 `cluster_id` 与串一致 |
| `evidence_set_equal` | `evidence_set_equal:5` | 两侧 `gold_doc_ids` 相同且长度等于 5 |
| `version_unchanged` | `version_unchanged:wp_178:truth=v1:sys=v1` | 两时刻该文档的真值/系统可见版本都等于所写版本 |
| `truth_stable` | `truth_stable:wp_124@v2` | 两时刻真值可见版本相同 |
| `truth_version_changed` | `truth_version_changed:wp_124:v1->v2` | 真值可见版本在缓存/请求两时刻确实变了 |
| `sys_version_changed` | `sys_version_changed:wp_124:v1->v2` | 系统可见版本确实变了 |
| `system_stricter_window` | `system_stricter_window:wp_088\|cached=…\|effective=…\|notified=…\|req=…` | `effective <= cached < notified <= req` 且真值版本未变 |
| `answer_equal` / `answer_changed` | `answer_equal:v0==v1` | 重跑两侧快照的 gold_sql，比较规范化结果 |
| `permission_ok` / `permission_mismatch` | `permission_mismatch:restricted->staff` | 权限序比较（左 cached、右 req） |
| `time_window_equal` | `time_window_equal:2024-01-01T00:00:00Z~2024-01-31T23:59:59Z` | 与题目 `time_window` 逐字相等 |
| `time_window_mismatch` | `time_window_mismatch:<cached窗>\|<req窗>` | 两个窗口确实不同 |
| `shared_metric` / `disjoint_metric` | `shared_metric:metric_027` | 两题 `metric_refs` 交集/不相交（两侧均非空） |
| `chain_missing` | `chain_missing:act,resp\|plan,rag,act,resp` | 请求所需 `obj_types` 不被缓存对象覆盖 |

## 10. 分支配对的成本口径

每行是同一个请求的两条路径（全部取自双视角都判安全的配对，即“真实收益”行）：

- **全路径本地段** = 检索 + SQL 执行 + 有效性检查：
  检索 = 版本化块索引上按 `domain` 预筛 + 权限预筛（ACL）后做词项计数打分取 top-5；
  SQL 执行 = `executor.execute(req.snapshot, task.gold_sql)`；
  有效性检查 = 证据版本是否仍是系统在请求时刻可见版本、块 hash 是否与索引一致、文档权限是否允许。
- **缓存路径本地段** = 命中查找（按 `(task_id, snapshot)` 取缓存答案签名与证据）+ 同一套有效性检查，
  不执行 SQL。
- 每条路径重复 5 次，取 5 次合计耗时的**中位数**；`g_local_ms = t_local_full_ms - t_local_cache_ms`（保留 3 位）。
- `t_model_full_ms` / `t_model_cache_ms` **一律为 `null`**，`note` 固定写 `requires_author_model_run`：
  作者模型的规划、SQL 生成与作答耗时本阶段不测，不得编造。`measured=true` 表示该行所有非空时间都是实测。
- `quality_full` / `quality_cache` = 由 `compare` 复核对“请求时刻真值”的一致性（1.0/0.0），
  缓存路径另要求缓存答案签名等于请求时刻 gold 签名且缓存证据仍通过有效性检查。
  120 行全部是安全配对，两列因而是 1.0——这是安全配对的推论，`selfcheck` 会重新执行 SQL 复核，
  不是常量填充。

实测（本机多次运行，`python dataset/labels/build.py`；时间列每次重测有毫秒级波动）：

| 指标 | 值 |
|---|---|
| 配对数 / 覆盖题目 / 唯一请求 | 120 / 97 道题 / 120 个 req |
| `t_local_full_ms` | 中位数 ≈3.27，min ≈1.8，max ≈19.6 |
| `t_local_cache_ms` | 中位数 0.012 |
| `g_local_ms` | 中位数 ≈3.26，合计 ≈528 ms，120 行全部为正 |
| 本地段比值（全/缓存，中位数） | ≈270–310× |

该比值只是**本地段**的比值：它把检索与 SQL 执行整段省掉，而模型耗时未测、不在分母里，
不能当作端到端加速比使用。

## 11. 分布与覆盖

- 300 条标签覆盖 148 道题、482 个请求；`safe=True` 150 条（140 条双视角一致 + 10 条系统保守误失效），
  `safe_system=True` 140 条，覆盖 4 个时间窗。
- 负例题对分散度：N1 30 条 / 24 个题对 / 18 簇，N2 30 条 / 26 个题对，N3 35 条 / 28 个题对，
  N4 30 条 / 28 个题对 / 17 簇，N6 25 条 / 15 个有序题对 / 13 簇。
- 难负例同簇：N1+N4+N6 共 85 条，85/85 = 100% 同簇（验收下限 80%）。
- 系统保守误失效 10 条，全部 `(safe=True, safe_system=False)`、`divergence_reason=system_stricter_window`。
- 分支配对覆盖三类链条：`plan>rag>act>sql>resp` 48、`act>sql>resp` 46、`rag>sql>resp` 26。
- `to_review.csv` 60 条：N1/N2/N3/N4/N6 各 10 条 + 安全样本 10 条（其中 5 条为系统保守误失效）。

## 12. 偏差与口径选择（写论文时必须一并交代）

1. **`safe` 只看证据版本是否变化，不含“缓存内容是否正确”的假设。** 缓存条目实际携带的是
   系统在缓存时刻可见的版本；本版按契约用“两个时刻可见版本是否相同”判定 `safe`/`safe_system`，
   因此窗口内建立的缓存可能“真值视角安全、系统视角不安全”（系统保守误失效），这正是要观测的
   通知延迟管理成本。v0.1 用 `old_ver` 反推缓存持有版本的口径已废弃。
2. **单调性方向是 `safe_system ⇒ safe`。** 批量升版即时通知使反向的
   `(safe=False, safe_system=True)` 结构上为 0（第 3 节有全量计数），因此不存在“系统眼里安全、
   事实已过期”的静默复用；可观测的分歧只有系统误杀。
3. **严格版本口径。** 契约要求逐文档比较可见版本；知识层给全部 2000 篇文档在 06:00/12:00
   各写了一行版本（其中 1175 篇内容并未变化），因此跨快照边界的配对一律判为证据过期
   （N3 的来源）。块级宽松口径的取舍留给论文层面讨论。
4. **N6 只有 25 条、集中在 15 个有序题对。** 同簇、同指标、同时间窗且缓存链条更短的题对有限；
   没有为了凑数放宽到跨簇或跨指标。旧版 N6 的近似度最低（均值 0.38），本版同簇构造把它抬到
   与 N1/N4 同一水平。
5. **`branch_pairs.jsonl` 不是逐字节可复现的。** 时间列由 `perf_counter` 实测，同一脚本两次运行
   文件哈希不同；`MANIFEST.json` 记录的是当次构建的哈希。`safe_reuse.jsonl` 与 `to_review.csv`
   逐字节可复现（两次运行 sha256 一致，见第 13 节）。
6. **`quality_*` 恒为 1.0** 是安全配对的推论而非测量缺失；若要观察质量损失，看 N3 负例
   （缓存过期但答案仍相等），它们按定义不进入“收益”配对。
7. **本地检索是替代实现。** 数据集没有真实倒排索引，全路径的“检索”用
   `domain` 预筛 + 权限预筛 + 词项计数打分的确定性词法检索代替；SQL 载荷用题目自身 `gold_sql`，
   因为作者模型生成 SQL 的耗时属于 `t_model`。
8. **配对号共用空间。** 标签用 `b00001–b00300`，分支用 `b00301–b00420`，避免跨文件重号。

## 13. 复现

```bash
python dataset/labels/build.py
python -c "import hashlib;print(hashlib.sha256(open('dataset/labels/safe_reuse.jsonl','rb').read()).hexdigest())"
python dataset/labels/build.py   # 再跑一次
python -c "import hashlib;print(hashlib.sha256(open('dataset/labels/safe_reuse.jsonl','rb').read()).hexdigest())"
python dataset/labels/selfcheck.py
python dataset/verify/verify.py --stage P5
python dataset/verify/verify.py --stage P0
```

随机只来自 `common/seeds.py::rng("labels", name)`（`task_order`、`cluster_order`、`pick:*`），
同一 `global_seed=42` 下配对选择稳定；`selfcheck.py` 会在同一进程内重放一遍 `build_labels()` 与
`select_branch()`，与磁盘内容比对，因此“同种子重跑一致”是自检项而不是口头承诺。

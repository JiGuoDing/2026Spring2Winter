# 数据集使用手册（Agent 版）

> 目标读者：需要在本仓库上写实验脚本的其他 Agent。
> 读这一份就够，不必再翻设计文档。所有路径相对仓库根目录。
> 版本：`dataset-v0.3.0`　最后更新：2026-11-26
> 需要了解"数据集是什么、做过哪些实验、结果是什么"时，读 **`REPORT.md`**。
> 要动手写实验脚本（回放器、策略、A–F 实验）时，先读 **`AGENT_PLAYBOOK.md`**：铁律、分工、验收、常见坑都在那里。

---

## 0. 30 秒速览

```python
import sys
sys.path.insert(0, "dataset")
from common import io
from pathlib import Path

tasks = list(io.read_jsonl(Path("dataset/tasks/tasks.jsonl")))      # 200 题 + 三层真值
reqs  = list(io.read_jsonl(Path("dataset/events/request_stream.jsonl")))  # 3000 请求
docs  = list(io.read_jsonl(Path("dataset/events/docs_versioned.jsonl")))  # 2000 文档 × 3 版
ups   = list(io.read_jsonl(Path("dataset/events/update_events.jsonl")))   # 40 次更新

sys.path.insert(0, "dataset/db")
import executor
res = executor.execute("v0", tasks[0]["gold_sql"])   # {'columns':…, 'rows':…, 'error':None}
```

**三条铁律**

1. 只读 `dataset/`；除自己负责的目录外不要写入。
2. 时间即版本：任何“某时刻的事实”都要按 `timestamp` 解析版本，不能取“最新版”。
3. `measured` 与 `mock` 不得混填；模型耗时本仓库没有代造。

---

## 1. 文件清单

| 路径 | 行数 | 字节量级 | 内容 |
|---|---|---|---|
| `db/snapshots/v0.sqlite` `v1` `v2` | — | 9.1–9.4 MB | 60/60/62 表的三个快照，49,040 / 49,040 / 49,560 行 |
| `db/snapshots/hashes.json` | — | 5.8 KB | 每份快照的 sha256、行数、逐表行数 |
| `db/executor.py` | — | 7.4 KB | 只读执行器，三层保护 |
| `db/compare.py` | — | 9.5 KB | 结果规范化与多重集比对 |
| `db/tests/` | 36 用例 | — | 比对器与执行器单测 |
| `knowledge/docs.jsonl` | 6,000 | 5.8 MB | 2,000 文档 × 3 版本（源） |
| `knowledge/version_changes.jsonl` | 1,360 | 155 KB | 版本变更映射 |
| `tasks/tasks.jsonl` | 200 | 447 KB | 题库与三层真值（600 条主张、40 个语义簇） |
| `tasks/gold_results.jsonl` | 200 | 42 KB | gold SQL 的真实执行结果 |
| `events/docs_versioned.jsonl` | 6,000 | 5.8 MB | 知识层的投影（内容逐行不变） |
| `events/request_stream.jsonl` | 3,000 | 3.2 MB | 主请求流（含 cluster_id） |
| `events/request_context.jsonl` | 3,000 | 0.9 MB | 请求 sidecar：题号、改写序号、租户、复用标记、簇 |
| `events/update_events.jsonl` | 40 | 13 KB | 30 条主张级命中 + 6 条无关更新负对照 |
| `events/act_plan_pool.json` | 100 + 60 | 36 KB | 只读工具池与计划模板池 |
| `events/streams/seed42–46.jsonl` | 各 3,000 | 2.7 MB | 五种到达形态 |
| `events/streams/long_01,02.jsonl` | 各 5,000 | 4.6 MB | 长流，用于容量扫描 |
| `events/real_calibration_300.csv` | 300 | 17 KB | 标定实测结果（七列齐全，v0.3.0） |
| `events/real_calibration_300.template.csv` | 300 | 5.8 KB | 空白模板 |
| `costs/path_costs.csv` | 222 | 58 KB | 六条路径成本，220 实测 / 2 待回填（大模型档案） |
| `costs/tool_cost_model.json` | — | 2.6 KB | 工具调用次数×重试×延迟的场景模型（measured/assumed 分列） |
| `labels/safe_reuse.jsonl` | 300 | 133 KB | 安全复用标签 |
| `labels/branch_pairs.jsonl` | 120 | 39 KB | 两条分支的实测配对 |
| `labels/to_review.csv` | 60 | 30 KB | 待人工复核清单 |
| `contracts/tables.json` | 60 表 | 353 KB | 表目录（1,200 字段） |
| `contracts/lineage.json` | 84 边 | 6.2 KB | 血缘图 |
| `embeddings/query_embeddings.npz` | 600×512 | 1.5 MB | 真实句向量（L2 归一化） |
| `config/params.json` | — | 1.3 KB | 规模、阈值、种子唯一来源 |
| `DATASET_CARD.md` | — | — | 构造/实测边界、许可、局限 |
| `PAPER_MAP.md` | — | — | 实验与文件的对应表 |

---

## 2. 统一约定

### 2.1 ID

| 对象 | 形态 | 生成入口 |
|---|---|---|
| 表 | `t01`…`t60` | `common/ids.py::table_id` |
| 字段 | `fld_t01_01`（`fld_{表}_{序号}`） | `field_id` |
| 文档 | `fld_t01_01` / `wp_001` / `metric_001` / `tool_001` / `plan_01` / `note_001` | 同上 |
| 证据块 | `{doc_id}#p01` | `block_id` |
| 请求 / 更新 / 配对 / 题 | `r000001` / `u0001` / `b00001` / `q001` | `req_id` 等 |

**块 ID 跨版本固定**：`metric_045#p02` 永远指同一段，内容可以变，`hash` 变了就代表变了。

### 2.2 时间与快照

| 时刻（UTC） | 生效 |
|---|---|
| `2024-05-15T00:00:00Z` | 快照 v0、文档版本 1 |
| `2024-05-15T06:00:00Z` | 快照 v1、文档版本 2 |
| `2024-05-15T12:00:00Z` | 快照 v2、文档版本 3 |
| 00:00–18:00 | 请求流跨度 |

所有时间都是同格式 UTC ISO8601，**可直接字符串比较**。

### 2.2b 双时间戳（v0.2.0 新增，最容易踩坑）

文档版本有两个时刻，含义不同：

| 字段 | 含义 | 谁用它 |
|---|---|---|
| `docs_versioned.updated_at` / `update_events.effective_at` | 新版本在**底层生效**的时刻 | 判定“真值上是否已过期” |
| `update_events.timestamp` | 系统**收到通知**的时刻 | 判定“系统当时知道什么” |
| `update_events.notification_delay_s` | 两者之差，实测 0.03–3.0 小时（中位 1.6） | 通知延迟统计 |

含义：在 `[effective_at, timestamp)` 这段窗口里，事实已经变了但系统还不知道。因此“旧缓存是否过期”有两个答案：

- **真值视角**（`labels.safe`）：按 `effective_at` 判，窗口内旧缓存算过期。
- **系统视角**（`labels.safe_system`）：按通知时刻判，窗口内旧缓存算“系统尚不知情”。

做实验时二选一并写清楚：1.4.1 的“已知过期复用必须为 0”用系统视角，“陈旧结果暴露”用真值视角。两者之差就是通知延迟造成的不可避免窗口，应单独计量，不能混入策略缺陷。

### 2.3 权限

`public` ⊃ `staff` ⊃ `restricted`（左边限制最少）。文档 1,400 / 400 / 200，请求按题目权限与租户叠加。

### 2.4 语义域

`sales` / `supply` / `finance` / `ops` / `meta`。

---

## 3. 逐文件字段

### 3.1 `events/docs_versioned.jsonl`（知识正文）

| 字段 | 类型 | 说明 |
|---|---|---|
| `doc_id` | str | 六类前缀之一 |
| `version` | int 1–3 | 对应 00:00 / 06:00 / 12:00 |
| `doc_type` | enum | `field` `whitepaper` `metric` `tool` `plan` `note` |
| `domain` | str | 语义域 |
| `permission` | enum | 密级 |
| `updated_at` | str | 该版本生效时刻 |
| `chunks[]` | list | `{chunk_id, text, hash}`，每篇 1–4 块 |

**用法**：RAG 语料、证据真值、失效判定的对象。不要拿它当“最新的”读，一律按时刻取版本（见 §5.3）。

### 3.2 `knowledge/version_changes.jsonl`（变更映射）

| 字段 | 说明 |
|---|---|
| `doc_id` / `from_ver` / `to_ver` | 哪篇、哪两版 |
| `change_kind` | `modify_text` / `modify_number` / `add_chunk` / `delete_chunk` |
| `changed_chunk_ids[]` | 变更的块；`add`/`delete` 时只存在于一侧 |

### 3.3 `events/request_stream.jsonl`（请求）

| 字段 | 说明 |
|---|---|
| `req_id` | `r000001`… |
| `timestamp` | 到达时刻 |
| `query_text` | 中文问句（同一题有 3 种改写） |
| `query_emb` | **恒为 null**，需你自己生成 |
| `plan_id` / `act_key` | 指向 `act_plan_pool.json`，同题恒定 |
| `gold_doc_ids[]` | 该请求的真值证据文档 |
| `gold_fact_spans[]` | `{claim, chunk_id}`，答案主张到块的映射 |
| `domain` / `permission` | 请求级语义域与密级 |
| `snapshot` | `{index: v0/v1/v2, as_of: 生效时刻}` |
| `obj_types[]` | `resp` / `rag` / `act` / `plan` 的子集，表示该请求涉及哪些缓存对象 |
| `cluster_id` | 语义簇（`cls_{domain}_{topic}`），与所属题目一致 |

**注意**：请求里**没有 `task_id`**，映射在 sidecar `events/request_context.jsonl`（`req_id → task_id, variant, tenant, reused, bucket, hot_set, cluster_id`）。

### 3.4 `events/update_events.jsonl`（更新）

| 字段 | 说明 |
|---|---|
| `event_id` / `timestamp` | `u0001`…；`timestamp` 是**系统收到通知**的时刻，散布 06:05–15:05 |
| `effective_at` | 文档新版本**实际生效**时刻，必须等于 `(doc_id, new_ver)` 的 `updated_at` |
| `notification_delay_s` | `timestamp − effective_at`，秒；实测 0.03–3.0 小时 |
| `doc_id` / `old_ver` / `new_ver` | 与 `version_changes` 完全对齐 |
| `changed_chunk_ids[]` | 具体哪几块变了 |
| `change_type` | `metric_revision` `schema_change` `lineage_switch` `codebook_revision` `data_row_change` |
| `answer_impact` | `changed` / `unchanged` |
| `negative_control` | `true` 表示刻意的“无关更新”负对照 |

**分布**：`schema_change` 14、`metric_revision` 8、`lineage_switch` 6、`data_row_change` 6、`codebook_revision` 6（后者全部是负对照）。

**关于 `codebook_revision`**：本数据集中没有任何请求引用码表类文档（请求只引用字段卡/白皮书/指标卡），
因此这 6 条必然是“发生了更新但不影响任何缓存条目”的**无关更新负对照**。它们不是数据缺陷，
而是实验 E 里测“误失效/误触发率”的负样本——策略不该因为它们而让缓存失效。
其余 34 条全部命中真实请求，其中 24 条命中答案主张，23 条在事件发生后仍可观测。

**影响面示例**（主张级最强）：

```json
{"event_id":"u0019","timestamp":"2024-05-15T08:14:36Z","doc_id":"wp_017","old_ver":1,"new_ver":2,
 "changed_chunk_ids":["wp_017#p01"],"change_type":"lineage_switch","domain":"ops",
 "permission":"public","answer_impact":"changed"}
```

影响 68 条请求、5 条主张，事件后仍有 32 条请求命中旧证据。文档级最强的是 `u0023`（`wp_002`，602 条请求引用，但主张级为 0）。

### 3.5 `events/act_plan_pool.json`

```json
{"acts":[{"act_key":"act_join_t03_t40","act_cost":0.35,"downstream_tools":[],"readonly":true}],
 "plans":[{"plan_id":"plan_51","plan_cost":0.6,"completion_rate":0.92,"steps":["解析口径","…"]}]}
```

`act_cost` / `plan_cost` 是相对单位（1.0 ≈ 一次完整回答生成），不是毫秒。

### 3.6 `tasks/tasks.jsonl`（题库 + 三层真值）

| 字段 | 说明 |
|---|---|
| `task_id` | `q001`… |
| `question` | 业务口吻的中文问句 |
| `difficulty` | `single_table` / `join` / `nested_agg`（60/70/70） |
| `gold_sql` | 单条 SELECT/WITH，可被 `executor` 执行 |
| `snapshot` | 一律 `v0` |
| `answer_shape` | `scalar` / `table` |
| `expected_columns[]` | 结果列名 |
| `truth.value` | 执行结果（标量或 ≤20 行表） |
| `truth.value_hash` | 规范化后 sha256 前 16 位 |
| `truth.claims[]` | 1–5 条中文事实表述，每条 `{text, evidence:[{doc_id, chunk_id, version}]}` |
| `truth.evidence[]` | 所有主张证据的并集 |
| `metric_refs[]` | 关联的口径卡 |
| `permission` / `time_window` | 密级与时间窗 |
| `cluster_id` | 语义簇，40 个簇、每簇 4–6 题，同簇共享 ≥1 个证据文档 |

**主张数分布**（600 条，v0.2.0 起不再是恒 2 条）：1 条 30 题、2 条 40 题、3 条 60 题、4 条 40 题、5 条 30 题。
这决定了“局部修复 vs 全量重生成”的分层：1–2 条主张的题被更新击中即为大改，3–5 条的题才可能 ρ<0.5。

**注意**：`tasks.jsonl` **没有 `domain` 字段**。需要域时从 `truth.evidence` 的第一个 metric/wp 文档取。

### 3.7 `db/`（库与工具）

```python
import sys; sys.path.insert(0, "dataset/db")
import executor, compare

r = executor.execute("v0", "SELECT COUNT(*) FROM dim_date")
# {'columns':['COUNT(*)'], 'rows':[[400]], 'elapsed_ms':65.6, 'error':None, 'truncated':False}

executor.execute("v0", "DELETE FROM dim_date")   # error: 只允许 SELECT / WITH
bad = executor.execute("v0", "SELECT 1; DROP TABLE dim_date")  # 多语句被拒

compare.compare(a, b)     # {'equal':True,'reason':…,'missing':[],'extra':[]}
```

- `execute(db="v0", sql=None, *, timeout_s=5.0, row_limit=10000)`
- 三层保护：`mode=ro&immutable=1` + 语句前缀白名单 + 多语句拒绝；5 秒超时、10,000 行上限。
- `compare(a, b, *, ordered=False)`：列序无关、行序无关、浮点 6 位容差。

### 3.8 `costs/path_costs.csv`

列：`path,stage,model,concurrency,n,metric,value_ms,measured,mock,note`

- `path` ∈ `validity_check` `exact_hit` `semantic_hit` `act` `partial_repair` `full_regen`，另有 `check_full`、`locate_full_scan` 两个上限对照。
- `metric` ∈ `p50` `p95` `mean` `wall_ms_per_item` `build_total` `pending_model_measure`
- **模型阶段**（`partial_repair/rewrite`、`full_regen/generate`）：本地档案 2 行已实测回填（plan p50=49,705.9 ms；resp p50=98,627.4 ms，n=300）；`api-large-placeholder` 2 行仍 `mock=pending`。
- 回填口径（2026-11-25 实测配置）：单卡 27B、串行、`temperature=0`、`max_tokens=32768`、上下文 65536、
  `reasoning_effort=xhigh`；plan 35–73 s / resp 186–211 s（约 3,000 completion token）/ 单条约 250 s。
  详见 `CALIBRATION_HOWTO.md`。**旧配置把 resp 截断在 512 token，会把时延低估约 5 倍，不可用于报数。**
- 本地检查是**微秒级**，这是实测事实；`costs/README.md` §6 给了换算到毫秒的杠杆。

### 3.9 `labels/safe_reuse.jsonl`

| 字段 | 说明 |
|---|---|
| `pair_id` / `req_id` / `cached_req_id` | 新请求与它可复用的旧请求 |
| `task_id` | 所属题目 |
| `cached_doc_ids[]` | 旧结果的证据 |
| `safe` | bool | **真值视角**：按 `effective_at` 判证据是否过期 |
| `safe_system` | bool | **系统视角**：按通知时刻判；`safe ⇒ safe_system` |
| `divergence_reason` | str | 两视角不同时的原因；当前全部为 `system_stricter_window`（系统保守误失效） |
| `negative_type` | | `none` / `N1_entity_mismatch` / `N2_permission` / `N3_stale_but_looks_right` / `N4_time_window` / `N6_reasoning_chain` |
| `reasons[]` | | 可回溯的判定依据，如 `version_changed:metric_012#p01` |
| `judged_by` / `confidence` | | 恒 `predicate` / `1.0` |

分布：安全 150；N1 30、N2 30、N3 35、N4 30、N6 25、N5 0（无副作用场景）。N1/N4/N6 为**同簇难负例**（100% 同簇），避免“太好区分”。

### 3.10 `labels/branch_pairs.jsonl`

`t_local_*` 为实测（SQL 执行 + 检索 + 检查），`t_model_*` 恒 `null` 且 `note=requires_author_model_run`；`g_local_ms = t_local_full_ms − t_local_cache_ms`。

### 3.11 其他

- `events/real_calibration_300.csv`：300 行七列全部实测（`real_calibration_300.template.csv` 为空白模板）。
- `labels/to_review.csv`：60 行人工复核清单。
- `contracts/tables.json`：`{table_id, name, kind, grain, rows, fields[{field_id,name,type,pk,nullable,desc}]}`。
- `contracts/lineage.json`：`{edges:[{from,to,kind}], three_hop_chain:[…]}`，`kind ∈ fk/aggregate/derive`。

---

### 3.12 `embeddings/query_embeddings.npz`（句向量，v0.2.0 新增）

- 600 条唯一 `query_text` 编码为 600×512 float32，**已 L2 归一化**；模型 `BAAI/bge-small-zh-v1.5`（`Xenova` ONNX 导出，commit `75c43b0`），由 onnxruntime 本地推理，未用 torch。
- 加载：

```python
from common import io
texts, mat = io.load_query_embeddings()       # texts: list[str], mat: (600,512)
lut = io.embedding_lookup()                   # text -> vector(list[float])
vec = lut[req["query_text"]]
```

- 请求里的 `query_emb` **仍然是 null**，向量不写回 JSONL（避免文件暴涨），一律按 `query_text` 查表。
- 确定性：同模型同批序重跑，矩阵 sha256 `6e6cccc8…` 逐字节一致；元数据见 `query_embeddings.meta.json`。
- `embeddings/cache/` 下约 90 MB 模型缓存可删可重下，不计入 MANIFEST。
- 句向量文件缺失时 `io.load_query_embeddings()` 会抛 `FileNotFoundError`，**不要**用 TF-IDF 顶替。

## 4. 引用关系

```text
contracts/tables.json ──► knowledge/docs.jsonl（字段卡逐字段一篇）
                     └──► db/schema.sql ──► snapshots/v0,v1,v2

knowledge/docs.jsonl ──► events/docs_versioned.jsonl（逐行投影）
                     └──► knowledge/version_changes.jsonl ──► events/update_events.jsonl

tasks/tasks.jsonl ──► truth.evidence ──► docs 的 doc_id/chunk_id/version
                  └──► gold_sql ──► executor ──► truth.value

events/request_stream.jsonl ──► gold_doc_ids / gold_fact_spans（来自题目）
                            └──► snapshot ──► 决定用哪份 DB 与哪版文档

labels/* ──► 读 request_stream + docs_versioned + update_events + tasks + executor
costs/*  ──► 读 tasks + db + knowledge
```

---

## 5. 六个可直接运行的配方

### 5.1 按时间线归并请求与更新（动机实验 M2）

```python
import sys; sys.path.insert(0, "dataset")
from common import io
from pathlib import Path

reqs = [dict(kind="req", **r) for r in io.read_jsonl(Path("dataset/events/request_stream.jsonl"))]
ups  = [dict(kind="upd", **u) for u in io.read_jsonl(Path("dataset/events/update_events.jsonl"))]
timeline = sorted(reqs + ups, key=lambda e: e["timestamp"])
```

### 5.2 取某请求当时的文档版本

```python
def doc_at(docs_by_id: dict, doc_id: str, ts: str) -> dict:
    """返回 ts 时刻生效的版本（同格式 ISO 字符串可直接比较）。"""
    cands = [d for d in docs_by_id[doc_id].values() if d["updated_at"] <= ts]
    return max(cands, key=lambda d: d["updated_at"])

by_id: dict[str, dict[int, dict]] = {}
for d in io.read_jsonl(Path("dataset/events/docs_versioned.jsonl")):
    by_id.setdefault(d["doc_id"], {})[d["version"]] = d

cur = doc_at(by_id, "metric_045", "2024-05-15T07:00:00Z")   # → version 2
```

### 5.3 执行一道题并与真值比对

```python
import sys; sys.path.insert(0, "dataset/db")
import executor, compare

task = tasks[0]
got = executor.execute(task["snapshot"], task["gold_sql"])
assert got["error"] is None, got["error"]
gold = next(g for g in io.read_jsonl(Path("dataset/tasks/gold_results.jsonl"))
            if g["task_id"] == task["task_id"])
print(compare.compare({"columns": gold["columns"], "rows": gold["rows"]},
                      {"columns": got["columns"], "rows": got["rows"]}))
```

### 5.4 复算“能否安全复用”（标签的谓词版，双视角）

与 `labels/safe_reuse.jsonl` 的 300 条标签**逐条一致**（300/300，含 `safe` 与 `safe_system`）。

```python
ctx = {c["req_id"]: c for c in io.read_jsonl(Path("dataset/events/request_context.jsonl"))}
tasks_by_id = {t["task_id"]: t for t in tasks}
ups = list(io.read_jsonl(Path("dataset/events/update_events.jsonl")))

# 系统视角的“可见版本”：有更新事件的按事件 timestamp，否则按 updated_at
notified = {(d["doc_id"], d["version"]): d["updated_at"] for d in docs}
for u in ups:
    notified[(u["doc_id"], u["new_ver"])] = u["timestamp"]

def visible_version(doc_id: str, ts: str) -> int:
    cands = [v for (did, v), t in notified.items() if did == doc_id and t <= ts]
    return max(cands) if cands else 1

def is_safe(cached_req: dict, req: dict, system_view: bool = False) -> tuple[bool, list[str]]:
    why = []
    rank = {"public": 0, "staff": 1, "restricted": 2}

    if ctx[cached_req["req_id"]]["task_id"] != ctx[req["req_id"]]["task_id"]:
        why.append("task_mismatch")
    for doc_id in cached_req["gold_doc_ids"]:
        if system_view:                     # 系统只知道通知过的版本
            a = visible_version(doc_id, cached_req["timestamp"])
            b = visible_version(doc_id, req["timestamp"])
        else:                               # 真值：按生效时刻
            a = doc_at(by_id, doc_id, cached_req["timestamp"])["version"]
            b = doc_at(by_id, doc_id, req["timestamp"])["version"]
        if a != b:
            why.append(f"version_changed:{doc_id}")
    if cached_req["gold_doc_ids"] != req["gold_doc_ids"]:
        why.append("evidence_set_differs")
    if rank[req["permission"]] < rank[cached_req["permission"]]:
        why.append("permission_mismatch")
    tw = lambda r: tasks_by_id[ctx[r["req_id"]]["task_id"]]["time_window"]
    if tw(cached_req) != tw(req):
        why.append("time_window_differs")
    return (not why), why

safe, _        = is_safe(a, b, system_view=False)   # 对应标签 safe
safe_system, _ = is_safe(a, b, system_view=True)    # 对应标签 safe_system
```

两者不同（`safe=True, safe_system=False`）的行是**系统保守误失效**：缓存条目事实上仍然正确，但通知刚到达、系统认为依赖变过而把它判为过期。这是可测量的管理成本。

反方向（`safe=False, safe_system=True`，即“系统不知情的静默过期”）在本数据中**结构上为 0**：2,000 篇文档在 06:00/12:00 批量升版且即时通知，因此跨版本的请求对必然让系统同时看到变化。这是数据的已知边界，不是 bug。

论文里：**已知过期复用**用系统口径（`safe_system=True` 的复用，应为 0），**陈旧结果暴露**用真值口径（`safe=False`），**保守误失效成本**用分歧行统计。

### 5.5 找一次更新影响了哪些请求

```python
def impact(u):
    affected = [r["req_id"] for r in reqs if u["doc_id"] in r["gold_doc_ids"]]
    hit = [(r["req_id"], s["claim"]) for r in reqs for s in r["gold_fact_spans"]
           if s["chunk_id"] in set(u["changed_chunk_ids"])]
    return affected, hit

u = max(ups, key=lambda x: len(impact(x)[0]))   # 按影响面挑，不要默认 ups[0]
affected, hit = impact(u)
print(u["event_id"], len(affected), "条请求受影响", len(hit), "条主张命中")
```

> 40 条更新不是条条命中。验收器强制：除 `codebook_revision`（无关更新负对照）外，**每条至少影响 1 条请求**，且**至少 22 条命中答案主张**。
> 做案例研究时先按影响面排序再挑，直接取 `ups[0]` 可能拿到影响为 0 的那条。
> 两种排序口径不同：上例按“受影响请求数”取到 `u0023`（602 条请求，主张级 0）；
> 若要找“真正打到答案主张”的更新，改成 `max(ups, key=lambda x: len(impact(x)[1]))`，得到 `u0019`（68 条请求、5 条主张）。
> 反过来，那几条零影响的 `codebook_revision` 不要丢掉——它们是实验 E 里测“误失效/误触发”的负样本。

### 5.6 统计重复率（动机实验 M1 的简化版）

```python
seen, repeat = set(), 0
for r in reqs:
    if r["plan_id"] in seen:
        repeat += 1
    seen.add(r["plan_id"])
print(f"plan 复用率 {repeat / len(reqs):.1%}")
# 更细的题级复用请用 request_context.jsonl 的 task_id + reused 字段（构造复用率 35.8%）
```

---

## 6. 不变量（违反即数据被改坏）

1. 块 ID 跨版本稳定，只有 `hash` 与 `text` 变。
2. 请求的 `snapshot.index` 不晚于其 `timestamp`：`<06:00→v0`、`06:00–12:00→v1`、`≥12:00→v2`。
3. 更新事件的 `old_ver/new_ver/changed_chunk_ids` 必须能在 `docs_versioned` 里定位到。
4. `gold_doc_ids` 必须都在 `docs_versioned` 中出现过；`gold_fact_spans.chunk_id` 必须是合法块 ID。
5. 200 题 `gold_sql` 在 `v0` 上必须执行成功且结果非空。
6. 同一 `(stage, name)` 走 `common/seeds.py` 必得同一随机序列。
7. `costs` 中同一行 `measured` 与 `mock` 不得同时有值。
8. 除 `codebook_revision`（刻意的“无关更新”负对照，≤8 条）外，每条更新至少影响 1 条请求（`doc_id` 被引用）；至少 22 条命中答案主张（`changed_chunk_ids` ∩ `gold_fact_spans.chunk_id` ≠ ∅）。
9. 每条更新的 `effective_at` 必须等于 `docs_versioned` 中 `(doc_id, new_ver)` 的 `updated_at`；`timestamp ≥ effective_at` 且 `notification_delay_s` 与差值一致。
10. 标签满足 `safe_system ⇒ safe`（系统认为安全则事实必安全）；双视角分歧 ≥5 条且方向恒为“系统保守误失效”（`safe=True, safe_system=False`）。
11. 受影响 (更新,请求) 对中，`ρ<0.5`（局部修复）占比必须在 **0.65–0.75**。
12. 每题主张数在 1–5；语义簇 35–50 个，每簇 3–6 题，同簇至少共享 1 个证据文档。

自检：`python dataset/verify/verify.py --all`（39 项断言）。

---

## 7. 常见误用

| 误用 | 后果 | 正确做法 |
|---|---|---|
| 文档一律读最新版 | 制造未来信息泄漏，指标虚高 | 用 §5.2 按 `timestamp` 取版本 |
| 把 `query_emb` 当现成向量 | 它是 null，跑不起来 | 自己跑 embedding，或先做纯文本回放 |
| 用 `tasks.jsonl["domain"]` | KeyError，该字段不存在 | 从 `truth.evidence` 的首个 metric/wp 文档取 |
| 用 v0 跑“结构变更后”的题 | 逻辑错位 | v2 有 62 张表，注意多出的两张表 |
| 把 `act_cost` 当毫秒 | 单位错 | 它是相对单位；毫秒看 `costs/path_costs.csv` |
| 把 `branch_pairs` 的本地时间当端到端收益 | 高估收益 | 模型段为 null，端到端要等回填 |
| 在 `update_events` 里找 00:00 的更新 | 找不到 | 更新最早 06:13，因为不能早于 `new_ver` 生效 |
| 默认 `ups[0]` 做案例，发现影响为 0 | 案例讲不通 | 先算影响面再挑（§5.5） |
| 用 `updated_at` 判断“系统当时是否知道” | 把通知延迟算成策略缺陷 | “系统知道”用 `timestamp`，只有“真值是否过期”才用 `effective_at` |
| 假设每题恒 2 条主张 | ρ 恒 0.5，局部修复测不出 | v0.2.0 起主张 1–5 条，按 `len(gold_fact_spans)` 算 ρ |
| 直接读 `request_stream["query_emb"]` | 仍是 null | 用 `io.embedding_lookup()` 按文本查（§3.12） |
| 拿 `costs/path_costs.csv` 的 rag/act 毫秒数代表生产 | 严重低估 | 那是**本地实现**耗时（BM25 6.2 ms、SQLite 1.1 ms）；生产检索与 SQL 通常高出数个量级，缩放用同表 `act_cost` 相对字段（0.02–0.77） |

---

## 8. 校验与复现

```bash
python dataset/verify/verify.py --all       # 48 项断言，必须全 PASS
python dataset/tools/stats.py               # 打印全部规模数字
python dataset/tools/gen_manifest.py        # 刷新 dataset/MANIFEST.json（57 文件）
python dataset/db/build.py                  # 重建三份快照（同种子哈希一致）
python dataset/knowledge/build.py           # 重建知识层（哈希一致）
python dataset/tasks/build.py               # 重建题库（哈希一致）
python dataset/events/build.py              # 重建事件层（哈希一致）
python dataset/labels/build.py              # 重建标签（safe_reuse 哈希一致）
```

独立验证过的确定性：`knowledge/docs.jsonl`、`events/request_stream.jsonl`、`tasks/tasks.jsonl`
连续两次构建哈希逐字节相同。`branch_pairs.jsonl` 因含实测计时，两次结果不同，属预期。

---

## 9. 构造与实测边界

| 项 | 状态 |
|---|---|
| 表结构、数据行、知识正文、题面、gold SQL、到达过程 | **构造**（`constructed`） |
| 题目答案值、`t_act_ms`、成本表本地阶段、分支配对本地耗时 | **实测**（`measured`） |
| 模型生成/改写耗时、`token_cost` | 已实测（300 条，qwen3.8-27b 单卡串行）；大模型档案仍 pending |
| 安全复用标签 | **规则判定**（可程序复现），60 条人工复核未做 |

完整清单见 `DATASET_CARD.md` 第三节。

---

## 10. 已知局限（写论文时必须照实交代）

1. 60 表 / 5 万行，规模远小于真实仓库，延迟只能相对比较。
2. 文档由模板生成，检索难度偏易。
3. 到达过程未与真实 LLM 推理 trace 对齐。
4. `act` 全只读，**副作用不可跳过**这条边界未检验。
5. 模型耗时只有**单一部署**（`qwen3.8-27b` 单卡串行、无截断）；无第二模型、无并发档位，`ΔT` 的模型分量只代表该部署。
6. 人工标注未做，无标注一致性系数。
7. 单一合成业务域，跨域迁移未验证。
8. 权限负例均为“请求权限高于文档密级”，无硬拒绝样本。
9. 工具成本按「每请求 1 次 rag + 1 次 act、均成功」标定；未含多次工具调用与失败重试，
   生产形态下工具段会被低估（见 `REPORT.md` §7.11 与 `costs/tool_cost_model.json`）。
10. 主标定 300 条记录**没有** reasoning 字段（采集代码跑批中途才修好），思考量结论只有 20 条补跑样本。
11. 句向量只覆盖 600 个不同问句；3,000 条请求按 `query_text` 映射到 600 条向量。
12. rag/act 为本地实现（BM25 6.2 ms、SQLite 1.1 ms），不代表生产检索与 SQL 延迟。

---

## 11. 版本与变更

- 数据版本：`dataset-v0.3.0`
- 契约变更：`contracts/CHANGELOG.md`
  - **v0.3.0**（当前）：模型阶段 300 条真机标定回填（plan p50=49,705.9 ms / resp p50=98,627.4 ms）；
    30 对分支回填；模型列改名 `local-qwen3-8-27b`；新增 `costs/tool_cost_model.json`；
    动机实验 M1/M2 完成（见 `exp_motivation/RESULTS.md`）。
  - v0.2.0：更新事件改双时间戳（`effective_at` / `notification_delay_s`）；新增语义簇 `cluster_id`；
    主张数去退化为 1–5 条；act 下游梯度与 plan 完成率分层；句向量落盘 + 标定脚本；
    标签新增 `safe_system` 双视角与同簇难负例。
  - v0.1.1 工具 ID 两位改三位（`tool_001`…`tool_100`）
  - v0.1.2 请求流跨度 12h → 18h（使 v2 快照有 820 条请求）
- 任何字段或规模改动都必须先改 `schema/` 与 `config/params.json`，再改 `contracts/CHANGELOG.md`，最后才动生成器。
- v0.2.0 的改动依据是 `dataset/audit_v010_report.json`（体检报告），不是主观判断。
- 标定进度与口径见 `CALIBRATION_HOWTO.md`；标定产物归档见 `REPORT.md` 附录 E。

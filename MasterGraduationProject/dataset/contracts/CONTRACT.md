# 数据系统契约（唯一真源之外的协作规则）

本文件规定**谁能写哪里、ID 怎么生成、什么算完成**。字段定义以 `schema/*.schema.json` 为准，
规模与阈值以 `config/params.json` 为准，表结构以 `contracts/tables.json` 为准。
三者冲突时，按 schema > params > tables 的顺序裁决，并立即记入 `contracts/CHANGELOG.md`。

## 一、文件所有权

| 目录 | 唯一写者 | 其他人 |
|---|---|---|
| `schema/ contracts/ config/ verify/ common/ tools/` | lead | 只读 |
| `db/` | agent-db | 只读 |
| `knowledge/` | agent-knowledge | 只读 |
| `tasks/` | agent-tasks | 只读 |
| `events/` | agent-events | 只读 |
| `costs/` | agent-cost | 只读 |
| `labels/` | agent-label | 只读 |

越界写入视为交付失败。需要改契约时，向 lead 提出，不得自行改 schema。

## 二、ID 规则（只能调用 `common/ids.py`）

- 表：`t01`…`t60`；字段：`fld_t01_01`…（`field_id(表, 序号)`）
- 知识文档：`fld_t01_01` / `wp_001` / `metric_001` / `tool_001` / `plan_01` / `note_001`
- 证据块：`{doc_id}#p01`（`block_id(doc, p)`），**跨版本稳定**，内容变了 ID 不变
- 请求：`r000001`；更新：`u0001`；配对：`b00001`；题目：`q001`
- 时间一律 UTC ISO8601，形如 `2024-05-15T08:00:00Z`

## 三、可复现规则

- 任何随机只能来自 `common/seeds.py::rng(stage, name)`；禁止裸 `random`、`numpy.random`、时间戳、`uuid4`
- 任何输出必须能被同一脚本重跑覆盖，且同参数下内容哈希一致
- 写文件统一走 `common/io.py`（JSONL 稳定排序、UTF-8、`\n` 换行）
- 每个目录交付时写 `MANIFEST.json`：`{文件: {rows, sha256}}`，由脚本生成，不手写

## 四、时间轴（全系统统一）

| 时刻 | 含义 |
|---|---|
| `2024-05-15T00:00:00Z` | 快照 v0 生效，索引 `v0` |
| `2024-05-15T06:00:00Z` | 快照 v1 生效（行级变更），索引 `v1` |
| `2024-05-15T12:00:00Z` | 快照 v2 生效（结构 + 口径变更），索引 `v2` |
| 18 小时 | 请求流总跨度（`params.streams.time_span_hours`），覆盖 00:00–18:00 |

请求的 `snapshot.index` 必须是其 `timestamp` 时刻已生效的最新快照，禁止引用未来快照。

## 五、各目录交付验收

| 目录 | 必须产出 | 验收 |
|---|---|---|
| `db/` | `schema.sql`、`build.py`、`snapshots/v{0,1,2}.sqlite`、`executor.py`、`compare.py`、`tests/` | 三个快照可重建；只读执行拒绝写语句；比对器单测全通过 |
| `knowledge/` | `docs.jsonl`（2,000 文档 × 3 版本）、`build.py`、`MANIFEST.json` | 符合 `docs_versioned` schema；doc_id 覆盖六类且数量等于 params；块 ID 跨版本稳定 |
| `tasks/` | `tasks.jsonl`（200 题）、`build.py`、`gold_results.jsonl` | 符合 `tasks` schema；gold SQL 在 `v0` 上全部执行成功；三层真值齐备 |
| `events/` | `docs_versioned.jsonl`、`request_stream.jsonl`、`update_events.jsonl`、`act_plan_pool.json`、`real_calibration_300.template.csv`、`build.py` | 符合四个 schema；规模等于 params；40 条主更新五类齐备 |
| `costs/` | 六路径成本表、`runner.py`、`README.md` | `measured`/`mock` 列分离，无混填 |
| `labels/` | `safe_reuse.jsonl`、`branch_pairs.jsonl`、`to_review.csv` | 每条标签可回溯到请求与文档版本 |

## 六、禁止事项

1. 不得修改他人目录；不得手拼 ID；不得绕过 `seeds.py`
2. 不得把 mock 值写进 `measured` 列
3. 不得让测试请求引用测试期之后才出现的版本
4. 不得在 `events/` 里复制 `knowledge/` 的正文，只引用 `doc_id` / `chunk_id`

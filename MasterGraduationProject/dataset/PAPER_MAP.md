# 论文实验与数据文件的对应表

本表规定每个实验读哪些文件、用哪些列，避免同一指标在不同章节出现不同口径。
文件路径均相对 `dataset/`。

## 一、第 1.1 节动机实验（对应 `动机实验_gemini_v1.md`）

| 实验 | 输入文件 | 用到的列 | 产出 |
|---|---|---|---|
| M1 异质开销与重复率 | `events/request_stream.jsonl`、`events/real_calibration_300.csv`、`events/act_plan_pool.json` | `req_id/timestamp/query_text/query_emb/plan_id/act_key/gold_doc_ids`；校准表 `t_plan_ms/t_rag_ms/t_act_ms/t_resp_ms/t_total_ms/token_cost` | `exp_motivation/results/m1_heterogeneity_summary.csv` |
| M2 静态策略两难 | `events/request_stream.jsonl` + `events/update_events.jsonl` 按 `timestamp` 归并 | `snapshot.index`、`gold_doc_ids`、更新的 `doc_id/old_ver/new_ver/changed_chunk_ids` | `results/m2_baseline_tradeoff.csv` |
| M2-ext 局部波及 | 同上 + `tasks/tasks.jsonl` 的 `truth.claims[].evidence` | `changed_chunk_ids` 与 claim 证据块的交集 | `results/m2_update_impact.csv` |

**口径约定**：`τ_sem = 0.88`、容量档位与误用惩罚权重全部读 `config/params.json`，不得在脚本里另写一份。

## 二、第 1.4 节正式实验

| 实验 | 主输入 | 辅助输入 | 关键列 |
|---|---|---|---|
| A 缓存机会与管理税 | `tasks/tasks.jsonl`、`events/request_stream.jsonl`、`db/snapshots/v0.sqlite` | `knowledge/docs.jsonl` | `difficulty`、`gold_doc_ids`、`truth.value` |
| B 候选检索与有效性检查 | `knowledge/docs.jsonl`、`events/update_events.jsonl` | `contracts/tables.json`（字段卡映射） | `doc_id/version/chunks[].chunk_id/hash` |
| C 价值与生命周期 | `events/streams/seed*.jsonl` | `costs/path_costs.csv` | `snapshot.index`、容量档位 |
| D `resp` 静态层提升 | `events/request_stream.jsonl`、`labels/safe_reuse.jsonl` | `tasks/tasks.jsonl` | `safe`、`negative_type` |
| E 证据更新与修复 | `events/update_events.jsonl`、`tasks/tasks.jsonl` | `knowledge/version_changes.jsonl` | `change_type`、`truth.claims[].evidence` |
| F 组合流与原型 | `events/streams/long_*.jsonl` | 全部 | 时间戳、`obj_types` |

## 三、文件清单与用途

| 文件 | 行数量级 | 谁产出 | 谁消费 |
|---|---|---|---|
| `db/snapshots/v{0,1,2}.sqlite` | 60 表 / 约 4.9 万行 | agent-db | A、C、E |
| `db/executor.py`、`db/compare.py` | — | agent-db | A、E、全部回放 |
| `knowledge/docs.jsonl` | 6,000（2,000×3 版） | agent-knowledge | B、D、E |
| `knowledge/version_changes.jsonl` | 约 1,360 | agent-knowledge | B、E |
| `tasks/tasks.jsonl` | 200 | agent-tasks | A、E、M2-ext |
| `events/docs_versioned.jsonl` | 6,000 | agent-events | M1、M2、B |
| `events/request_stream.jsonl` | 3,000 | agent-events | M1、M2、A、D、F |
| `events/update_events.jsonl` | 40 | agent-events | M2、M2-ext、B、E |
| `events/act_plan_pool.json` | 100 act + 60 plan | agent-events | M1、A |
| `events/streams/seed*.jsonl` | 3,000 × 5 | agent-events | C、F |
| `events/streams/long_*.jsonl` | 5,000 × 2 | agent-events | F |
| `events/real_calibration_300.template.csv` | 300 | agent-events | M1（需你回填实测） |
| `costs/path_costs.csv` | 6 路径 × 2 模型 × 3 并发 | agent-cost | C、E、M2 |
| `labels/safe_reuse.jsonl` | 300 | agent-label | D |
| `labels/branch_pairs.jsonl` | 120 | agent-label | D、E |

## 四、与设计文档的已知差异

`动机实验_gemini_v1.md` 第 2 节写的是"2,000–3,000 篇文档、3,000 条请求、40 次更新"。
本系统取**下界对齐**：2,000 篇文档、3,000 条请求、40 次更新主集，另加 20 条扩展更新与
2 条 5,000 长流。差异仅为规模，字段名与语义完全一致，动机实验脚本可直接读取。

`real_calibration_300.csv` 涉及模型调用的列（`t_rag_ms`、`t_resp_ms`、`token_cost`）**不由本系统代填**，
只提供模板与 runner；本地可测的 SQL 执行耗时已实测。使用前必须回填，否则 M1 的左纵轴无依据。

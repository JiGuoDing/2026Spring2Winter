# 论文实验与数据文件的对应表

本表规定每个实验读哪些文件、用哪些列，避免同一指标在不同章节出现不同口径。
文件路径均相对 `dataset/`。

## 一、第 1.1 节动机实验（对应 `动机实验_gemini_v1.md`）

| 实验 | 输入文件 | 用到的列 | 产出 |
|---|---|---|---|
| M1 异质开销与重复率 | `events/request_stream.jsonl`、`events/real_calibration_300.csv`、`events/act_plan_pool.json` | `req_id/timestamp/query_text/query_emb/plan_id/act_key/gold_doc_ids`；校准表 `t_plan_ms/t_rag_ms/t_act_ms/t_resp_ms/t_total_ms/token_cost` | `exp_motivation/results/m1_stage_costs.csv`、`m1_repetition.csv`（已产出） |
| M2 静态策略两难 | `events/request_stream.jsonl` + `events/update_events.jsonl` 按 `timestamp` 归并 | `snapshot.index`、`gold_doc_ids`、更新的 `doc_id/old_ver/new_ver/changed_chunk_ids` | `exp_motivation/results/m2_baselines.csv`（已产出） |
| M2-ext 局部波及 | 同上 + `tasks/tasks.jsonl` 的 `truth.claims[].evidence` | `changed_chunk_ids` 与 claim 证据块的交集 | `results/m2_update_impact.csv` |
| M3 工具成本结构敏感性 | `costs/tool_cost_model.json`、`events/act_plan_pool.json` | `calls.act_fanout_mean`、`calls.plan_steps_mean`、`profiles[].{model_ms,rag_ms_per_call,act_ms_per_call,p_fail}` | `exp_motivation/results/m3_tool_cost_sensitivity.csv` |

**口径约定**：`τ_sem = 0.88`、容量档位与误用惩罚权重全部读 `config/params.json`，不得在脚本里另写一份。

## 二、第 1.4 节正式实验

| 实验 | 主输入 | 辅助输入 | 关键列 |
|---|---|---|---|
| A 缓存机会与管理税 | `tasks/tasks.jsonl`、`events/request_stream.jsonl`、`db/snapshots/v0.sqlite` | `knowledge/docs.jsonl` | `difficulty`、`gold_doc_ids`、`truth.value` |
| B 候选检索与有效性检查 | `knowledge/docs.jsonl`、`events/update_events.jsonl` | `contracts/tables.json`（字段卡映射） | `doc_id/version/chunks[].chunk_id/hash` |
| C 价值与生命周期 | `events/streams/seed*.jsonl` | `costs/path_costs.csv` | `snapshot.index`、容量档位 |
| D `resp` 静态层提升 | `events/request_stream.jsonl`、`labels/safe_reuse.jsonl` | `tasks/tasks.jsonl`（`cluster_id`） | `safe`、`safe_system`、`negative_type`、`cluster_id` |
| E 证据更新与修复 | `events/update_events.jsonl`、`tasks/tasks.jsonl` | `knowledge/version_changes.jsonl` | `effective_at`、`notification_delay_s`、`change_type`、`truth.claims[].evidence` |
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
| `labels/safe_reuse.jsonl` | 300（含 `safe` 与 `safe_system` 双视角） | agent-label | D、E |
| `labels/branch_pairs.jsonl` | 120 | agent-label | D、E |
| `embeddings/query_embeddings.npz` | 600 × 512 | agent-embed | A、B、D（语义召回） |

## 四、与设计文档的已知差异

`动机实验_gemini_v1.md` 第 2 节写的是"2,000–3,000 篇文档、3,000 条请求、40 次更新"。
本系统取**下界对齐**：2,000 篇文档、3,000 条请求、40 次更新主集，另加 20 条扩展更新与
2 条 5,000 长流。差异仅为规模，字段名与语义完全一致，动机实验脚本可直接读取。

**标定已完成（v0.3.0）**：`events/real_calibration_300.csv` 七列全部实测，可直接用于 M1 与 1.4.1；
模型列已改名 `local-qwen3-8-27b`（实际部署 `qwen3.8-27b` 单卡）。

**v0.2.0 起需要改论文数字的地方**：1.4.5 节写"共 40 个事件、约 1,600 条受影响回答"。
实测口径：

| 口径 | 实测值 | 说明 |
|---|---|---|
| 文档级受影响请求（去重） | 1,795 | 更新文档被该请求引用 |
| 主张级受影响请求（去重） | 874 | 更严格：变更块恰是该请求某条主张的证据 |
| (更新, 请求) 受影响对 | 1,102 | 用于逐对统计局部/大改 |
| 局部修复占比 ρ<0.5 | 73% | 大改 27% |

建议论文写"40 个更新事件、1,102 个（更新,请求）受影响对，其中 73% 仅涉及局部主张变更"，
或直接用去重请求数 874。**不要写 1,600**，三个口径都算不出来。

**时钟口径**：1.4.1 的"过期复用"分两层统计——"已知过期"用 `safe_system`（系统已收到通知仍复用，
必须为 0），"陈旧暴露"用 `safe`（含通知窗口内不可避免的部分，单独报告）。

`real_calibration_300.csv` 涉及模型调用的列（`t_rag_ms`、`t_resp_ms`、`t_total_ms`、`token_cost`）**不由本系统代填**，
只提供模板与 runner；本地可测的 SQL 执行耗时已实测。使用前必须回填，否则 M1 的左纵轴无依据。

## 五、v0.3.0 标定结果（可直接引用）

采样：300 条请求，`qwen3.8-27b` 单卡、串行、`temperature=0`、`max_tokens=32768`、
上下文 65536、`reasoning_effort=xhigh`；**触顶 0 条、空输出 0 条**（时延含完整生成）。

| 阶段 | p50 | p95 | 均值 | 最大 |
|---|---|---|---|---|
| plan | 49.7 s | 86.5 s | 51.8 s | 125.5 s |
| rag | 6.2 ms | 11.3 ms | 6.4 ms | 39.9 ms |
| act | 1.1 ms | 2.0 ms | 1.4 ms | 15.8 ms |
| resp | 98.6 s | 443.2 s | 147.1 s | 798.0 s |
| **端到端** | **154.3 s** | **505.0 s** | 198.9 s | 842.2 s |

- token：plan 平均 completion 744.7、resp 平均 2,111.4；`token_cost` p50=3,686，全量合计 1,302,090。
- 分支 30 对：完整路径 p50=160.3 s，缓存路径 p50=86.7 s（**省 46%**，模型段）。
- MAPE（仅本地可建模段）：act 5.9%，rag 76.9%，本地段合计 64.4%。
  **rag 的建模基线 p50=1.42 ms 明显低估实测 6.16 ms，1.4.1 若报 MAPE 需说明只覆盖本地段。**
- 服务在第 259 条后重启过一次；重启后 41 条已预热，分位数两套：全 300 条端到端 p95=505.0 s，
  前 259 条 p95=540.0 s，差异不影响结论。


### 思考量（20 条补跑，辅助证据）

| 指标 | p50 | p95 | max |
|---|---|---|---|
| 思考字符数 | 3,291 | 11,904 | 17,088 |
| 正文字符数 | 448 | 1,222 | — |
| 思考 token 估算 | 1,859 | — | 8,986 |
| 思考占 completion 比例 | **87%** | 92% | — |

- 思考字数与 resp 时长的 **Spearman ρ = 0.988**（n=20）：resp 时延的方差几乎完全由思考长度解释。
- 含义：缓存命中跳过整段生成，省掉的主要是思考时间；`ΔT` 的模型段收益应按「跳过整段 resp」计，
  不能只按输出正文长度估。数据见 `embeddings/calibration/requests_progress_supp.jsonl`，
  配置与主批次一致。

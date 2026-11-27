# 契约变更记录

规则：任何对 `schema/`、`contracts/`、`config/`、`common/` 的改动都必须在此登记，
写明原因、影响范围与已通知的 agent。

## 2026-11-26 · v0.3.0

**变更**：模型阶段成本实测回填，数据集由"模板 + pending"升级为"300 条真机标定"。

- `config/params.json`：`dataset_version=0.3.0`；`calibration` 块记录标定配置
  （max_tokens 32768 / 上下文 65536 / reasoning_effort=xhigh / temperature 0）、
  服务端型号 `qwen3.8-27b`、300 条请求 + 30 对分支、触顶 0 / 空输出 0、服务重启分界 259。
- `costs/path_costs.csv`：`partial_repair/rewrite`（plan p50=49,705.9 ms）与
  `full_regen/generate`（resp p50=98,627.4 ms）两行由 `mock=pending` 改为 `measured=backfill`，n=300。
  `api-large-placeholder` 两行仍为 `mock=pending`（未部署大模型）。
- `labels/branch_pairs.jsonl`：30 对回填 `t_model_full_ms` / `t_model_cache_ms`；
  full p50=160,337.7 ms，cache p50=86,715.7 ms。
- 模型列改名：`local-small-7b` → `local-qwen3-8-27b`（实际部署 27B 单卡，旧名误标参数量）。
  `tools/run_model_calibration.py` 的 `MODEL_ALIASES`、`default_alias` 与
  `tools/run_calibration_from_env.py` 的 `ALIASES` 同步更新。

**口径**：串行、单请求、`temperature=0`、启用思考（服务端默认，`reasoning_effort=xhigh`），
**无截断**（0/300 触顶），因此时延含完整生成。测量跨一次服务重启（第 260 条起），重启后已预热，
分位数按全 300 条与前 259 条两套给出，差异见 `DATASET_CARD.md`。

**未做**：模型段并发口径（1/8/32）仍未测；`api-large-placeholder` 未回填；act 级缓存收益未单独测。

## 2026-11-25 · v0.2.0

依据 `dataset/audit_v010_report.json` 的体检结论，做五组契约变更。

**1. 更新事件改为双时间戳（时钟语义消歧）**
- `schema/update_events.schema.json` 新增必填 `effective_at`（文档新版本生效时刻）与
  `notification_delay_s`（= timestamp − effective_at，秒）；`timestamp` 明确为“系统接收/通知时刻”。
- 原因：实测通知延迟 0.03–3.08 h（中位 1.64），若把两者混为一谈，1.4.1 的“过期复用必须为 0”
  无法区分“已知过期”与“通知窗口内静默过期”。方案 A（把 updated_at 对齐到事件时刻）会抹掉
  论文 1.3.2/1.4 明确要记录的“通知延迟”，故采用方案 B。

**2. 新增语义簇 `cluster_id`**
- `schema/tasks.schema.json` 与 `schema/request_stream.schema.json` 新增必填 `cluster_id`（`^cls_[a-z0-9_]+$`）。
- `config/params.json` 新增 `clusters: {count: 40, min_size: 3, max_size: 6}`。
- 原因：支撑 1.2.2 的簇内反馈借用；同时为同簇难负例（N1/N4/N6）提供构造基础——体检显示
  这三类负例与正例的相似度仅 0.28–0.38，过于容易区分。

**3. 主张数分布去退化**
- `config/params.json` 新增 `tasks.claims_per_task`（1–5 条，均值约 3.0）。
- 原因：体检显示每题恒为 2 条主张，导致 ρ 恒为 0.5，“局部修复 : 全量重生成”比例恒为 0:100，
  C3 实验无法分层。

**4. act/plan 异质性目标**
- 新增 `act_plan.min_nonempty_ratio: 0.65`、`min_distinct_downstream_buckets: 4`、
  `plan_completion_by_steps`（按步骤数分层的完成率区间）。
- 原因：实测 `downstream_tools` 非空仅 40%、plan 完成率与复杂度不单调（5 步 0.854 > 6 步 0.816）。
- 裁定：原拟的精确分布目标（30/30/25/15）改为**约束**（非空比例 + 档位数），因为 `downstream_tools`
  由血缘图推导后 3+ 档天然偏多；实际分布记录在 `DATASET_CARD.md`，不反过来用数据去凑参数。

**5. 句向量与标定通道**
- 新增 `embedding` 块（模型、维度、归一化方式、路径、`status: pending`）。
- 句向量落盘路径定为 `dataset/embeddings/query_embeddings.npz`（独立目录，由 agent-embed 独占写），
  不放 `events/`，避免与事件层写者冲突。
- 约定：未生成前 `query_emb` 保持 null，**禁止**用 TF-IDF 冒充语义向量写入 `query_embeddings.npz`。

**保留不变**：块 ID 跨版本稳定；6 条 `codebook_revision` 负对照保留；`verify.py` 断言只增不减。

## 2026-11-24 · v0.1.2

**变更**：请求流时间跨度由 12 小时改为 18 小时（`params.streams.time_span_hours = 18`）。

- 涉及：`config/params.json`、`contracts/CONTRACT.md` 时间轴表。
- 原因：快照 v2 在 12:00 生效，若流止于 12:00，则 `snapshot.index = v2` 的请求数为 0，
  实验 E 的结构变更与口径变更样本无法落位。扩到 18:00 后 v0/v1/v2 各覆盖 6 小时。
- 影响：TTL 档位按 18h 等比例换算后仍满足 `Short < 平均更新间隔 < Long`。
- 已通知：agent-events、agent-cost。

## 2026-11-24 · v0.1.1

**变更**：工具文档 ID 由两位改为三位，`tool_01` → `tool_001`，上限 100 篇。

- 涉及：`common/ids.py`（`tool_id` 与三条正则）、`schema/docs_versioned.schema.json`
  （`doc_id` 与 `chunk_id` 的 pattern）、`contracts/CONTRACT.md` 的 ID 示例。
- 原因：`config/params.json` 要求 `tools=100`，而两位 ID 只能表达 99，`ids.block_id("tool_100", 1)`
  直接抛 `ValueError`。属契约自相矛盾，按 schema > params 的顺序本应改需求，但工具卡总量参与
  `docs_total=2000` 的配平（1200+200+150+100+60+290），削到 99 会破坏配平，故改 ID 宽度。
- 影响：`wp_/metric_/note_` 已是三位，改后与之一致且可排序；`plan_` 保持两位（仅 60 篇）。
- 已通知：agent-knowledge（P2 阻塞方）。其他 agent 未使用 tool ID。

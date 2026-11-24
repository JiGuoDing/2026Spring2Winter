# 契约变更记录

规则：任何对 `schema/`、`contracts/`、`config/`、`common/` 的改动都必须在此登记，
写明原因、影响范围与已通知的 agent。

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

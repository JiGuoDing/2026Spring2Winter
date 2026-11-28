"""确定性生成 40 条更新事件的逐事件影响面汇总表（v0.4.0）。

输出：dataset/events/update_impact_summary.jsonl（40 行，与 update_events.jsonl 顺序一致）
用途：
  - 动机实验 M2-ext（图 1-1(c)：文档级粗粒度失效 vs. 主张级真实影响）
  - 正式实验 C3（局部修复 ρ<0.5 vs. 大改 ρ>=0.5 分层基准）

只读主干文件，不修改任何 v0.3.0 冻结数据。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

OUT_PATH = ROOT / "events" / "update_impact_summary.jsonl"


def build() -> list[dict]:
    reqs = list(io.read_jsonl(ROOT / "events" / "request_stream.jsonl"))
    updates = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))

    rows: list[dict] = []
    for u in updates:
        doc_id = u["doc_id"]
        changed = set(u["changed_chunk_ids"])
        ts_notify = u["timestamp"]
        ts_eff = u["effective_at"]

        doc_reqs_all = 0
        doc_reqs_before_notify = 0
        doc_reqs_after_notify = 0
        claim_reqs_all = 0
        claim_reqs_before_notify = 0
        claim_reqs_after_notify = 0
        local_cnt = 0
        major_cnt = 0

        for r in reqs:
            if doc_id not in r["gold_doc_ids"]:
                continue
            doc_reqs_all += 1
            before = r["timestamp"] < ts_notify
            if before:
                doc_reqs_before_notify += 1
            else:
                doc_reqs_after_notify += 1

            spans = r["gold_fact_spans"]
            hit_claims = sum(1 for sp in spans if sp["chunk_id"] in changed)
            if hit_claims > 0:
                claim_reqs_all += 1
                if before:
                    claim_reqs_before_notify += 1
                else:
                    claim_reqs_after_notify += 1
                rho = hit_claims / max(1, len(spans))
                if rho < 0.5:
                    local_cnt += 1
                else:
                    major_cnt += 1

        rows.append({
            "event_id": u["event_id"],
            "doc_id": doc_id,
            "old_ver": u["old_ver"],
            "new_ver": u["new_ver"],
            "change_type": u["change_type"],
            "domain": u["domain"],
            "negative_control": bool(u.get("negative_control", False)),
            "answer_impact": u.get("answer_impact", "unknown"),
            "effective_at": ts_eff,
            "timestamp": ts_notify,
            "notification_delay_s": u["notification_delay_s"],
            "doc_affected_reqs": doc_reqs_all,
            "doc_affected_before_notify": doc_reqs_before_notify,
            "doc_affected_after_notify": doc_reqs_after_notify,
            "claim_affected_reqs": claim_reqs_all,
            "claim_affected_before_notify": claim_reqs_before_notify,
            "claim_affected_after_notify": claim_reqs_after_notify,
            "local_repair_cnt": local_cnt,
            "major_change_cnt": major_cnt,
            "false_invalidation_reqs": doc_reqs_all - claim_reqs_all,
        })
    return rows


def main() -> int:
    rows = build()
    io.write_jsonl(OUT_PATH, rows)
    tot_doc = sum(r["doc_affected_reqs"] for r in rows)
    tot_claim = sum(r["claim_affected_reqs"] for r in rows)
    tot_local = sum(r["local_repair_cnt"] for r in rows)
    tot_major = sum(r["major_change_cnt"] for r in rows)
    ratio = (100.0 * tot_local / tot_claim) if tot_claim else 0.0
    print(
        f"已写 {OUT_PATH}（{len(rows)} 行）：文档级累计对数={tot_doc}，主张级累计对数={tot_claim}，"
        f"局部修复={tot_local}（{ratio:.2f}%），大改={tot_major}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

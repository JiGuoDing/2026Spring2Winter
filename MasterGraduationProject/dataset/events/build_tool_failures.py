"""确定性构造远程工具失败与重试 sidecar 事件表（v0.4.0，显式标注 assumed_synthetic）。

输出：dataset/events/tool_failures.jsonl
用途：为 M3 远程工具画像（P2/P3/P4）与 C4 敏感性回放提供可复现的「失败一次再成功」重试事件，
      不修改 request_stream.jsonl 主干，严守 measured 与 assumed 隔离。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io, seeds  # noqa: E402

OUT_PATH = ROOT / "events" / "tool_failures.jsonl"


def build() -> list[dict]:
    reqs = list(io.read_jsonl(ROOT / "events" / "request_stream.jsonl"))
    model = io.read_json(ROOT / "costs" / "tool_cost_model.json")
    max_retries = int(model["failure"]["max_retries"])
    fail_weights = model["failure"]["typical_p_fail"]
    reasons = list(fail_weights.keys())
    w_sum = sum(fail_weights.values())
    cum_weights = []
    acc = 0.0
    for k in reasons:
        acc += fail_weights[k] / w_sum
        cum_weights.append(acc)

    rows: list[dict] = []
    for prof in model["profiles"]:
        p_fail = float(prof["p_fail"])
        if p_fail <= 0.0:
            continue
        prof_id = prof["id"]
        rgen = seeds.rng("events", f"tool_failures_{prof_id}")
        for req in reqs:
            if "act" not in req["obj_types"] or not req.get("act_key"):
                continue
            attempts = 1
            fail_reasons: list[str] = []
            while attempts <= max_retries and rgen.random() < p_fail:
                u = rgen.random()
                reason = reasons[-1]
                for idx, cw in enumerate(cum_weights):
                    if u <= cw:
                        reason = reasons[idx]
                        break
                fail_reasons.append(reason)
                attempts += 1
            if attempts > 1:
                rows.append({
                    "profile_id": prof_id,
                    "req_id": req["req_id"],
                    "act_key": req["act_key"],
                    "attempts": attempts,
                    "retries": attempts - 1,
                    "fail_reasons": fail_reasons,
                    "source": "assumed_synthetic",
                })
    return rows


def main() -> int:
    rows = build()
    io.write_jsonl(OUT_PATH, rows)
    by_prof: dict[str, int] = {}
    for r in rows:
        by_prof[r["profile_id"]] = by_prof.get(r["profile_id"], 0) + 1
    print(f"已写 {OUT_PATH}（{len(rows)} 条失败重试记录，source=assumed_synthetic）：{by_prof}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

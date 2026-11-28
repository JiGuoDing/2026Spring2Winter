"""硬件无关的 act 缓存价值硬证据诊断脚本（v0.6.0）。

输出：dataset/costs/act_value_diagnostics.json
统计 4 项与机器快慢无关的客观证据：
  1. 跨快照数值漂移率（v0->v1, v1->v2, v0->v2）：直接用 db/compare.py 实测 200 题答案变化，
     证明不感知数据状态版本的 act 缓存必然返回错误数值；
  2. 跨请求/跨题复用率与底层 DB 查询削减上界：3,000 条请求流中含 act 请求的复用空间；
  3. 上层 resp 未命中时的残余复用机会：同一 act_key 覆盖的不同 task_id 与 query_text 数；
  4. 按 downstream_tools (d_i = 0, 1, 2, 3+) 分层的请求覆盖与加权 act_cost 分布。
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

import compare  # noqa: E402
import executor  # noqa: E402
from common import io  # noqa: E402

OUT_PATH = ROOT / "costs" / "act_value_diagnostics.json"


def _sig(snap: str, sql: str) -> str:
    out = executor.execute(snap, sql)
    assert not out.get("error"), f"SQL 执行失败 ({snap}): {out}"
    norm = compare.normalize(out)
    return hashlib.sha256(json.dumps(norm["rows"], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def main() -> int:
    tasks = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
    reqs = list(io.read_jsonl(ROOT / "events" / "request_stream.jsonl"))
    ctx = {c["req_id"]: c for c in io.read_jsonl(ROOT / "events" / "request_context.jsonl")}
    pool = io.read_json(ROOT / "events" / "act_plan_pool.json")
    act_meta = {a["act_key"]: a for a in pool["acts"]}

    # 1) 跨快照数值漂移率（200 题 × v0/v1/v2）
    drift = {"v0_to_v1": 0, "v1_to_v2": 0, "v0_to_v2": 0, "any_change": 0}
    for t in tasks:
        s0 = _sig("v0", t["gold_sql"])
        s1 = _sig("v1", t["gold_sql"])
        s2 = _sig("v2", t["gold_sql"])
        c01 = (s0 != s1)
        c12 = (s1 != s2)
        c02 = (s0 != s2)
        drift["v0_to_v1"] += int(c01)
        drift["v1_to_v2"] += int(c12)
        drift["v0_to_v2"] += int(c02)
        drift["any_change"] += int(c01 or c12 or c02)
    n_tasks = len(tasks)

    # 2) 3,000 条请求流中 act 复用率、DB 查询削减上界与跨题共享
    act_reqs = [r for r in reqs if "act" in r["obj_types"] and r.get("act_key")]
    by_act_tasks: dict[str, set[str]] = defaultdict(set)
    by_act_queries: dict[str, set[str]] = defaultdict(set)
    seen_act_snap: set[tuple[str, str]] = set()
    version_safe_reuses = 0
    seen_exact_query_snap: set[tuple[str, str, str]] = set()
    residual_act_reuses_on_exact_resp_miss = 0

    fanout_reqs = defaultdict(int)
    fanout_cost = defaultdict(float)

    for r in act_reqs:
        ak = r["act_key"]
        snap = r["snapshot"]["index"]
        tid = ctx[r["req_id"]]["task_id"]
        by_act_tasks[ak].add(tid)
        by_act_queries[ak].add(r["query_text"])

        q_key = (r["query_text"], r["permission"], snap)
        resp_exact_hit = q_key in seen_exact_query_snap
        seen_exact_query_snap.add(q_key)

        act_snap_key = (ak, snap)
        if act_snap_key in seen_act_snap:
            version_safe_reuses += 1
            if not resp_exact_hit:
                residual_act_reuses_on_exact_resp_miss += 1
        else:
            seen_act_snap.add(act_snap_key)

        meta = act_meta[ak]
        d_bucket = str(min(len(meta["downstream_tools"]), 3)) + ("+" if len(meta["downstream_tools"]) >= 3 else "")
        fanout_reqs[d_bucket] += 1
        fanout_cost[d_bucket] += float(meta["act_cost"])

    multi_task_acts = sum(1 for s in by_act_tasks.values() if len(s) >= 2)
    multi_query_acts = sum(1 for s in by_act_queries.values() if len(s) >= 2)
    n_act_reqs = len(act_reqs)
    exact_resp_misses_in_act = n_act_reqs - sum(
        1 for i, r in enumerate(act_reqs)
        if (r["query_text"], r["permission"], r["snapshot"]["index"])
        in {(x["query_text"], x["permission"], x["snapshot"]["index"]) for x in act_reqs[:i]}
    )

    report = {
        "dataset_version": "0.6.0",
        "snapshot_numerical_drift": {
            "total_tasks": n_tasks,
            "v0_to_v1_changed": drift["v0_to_v1"],
            "v0_to_v1_pct": round(100.0 * drift["v0_to_v1"] / n_tasks, 2),
            "v1_to_v2_changed": drift["v1_to_v2"],
            "v1_to_v2_pct": round(100.0 * drift["v1_to_v2"] / n_tasks, 2),
            "v0_to_v2_changed": drift["v0_to_v2"],
            "v0_to_v2_pct": round(100.0 * drift["v0_to_v2"] / n_tasks, 2),
            "any_snapshot_changed": drift["any_change"],
            "any_snapshot_changed_pct": round(100.0 * drift["any_change"] / n_tasks, 2),
        },
        "reuse_and_db_qps_reduction": {
            "total_requests": len(reqs),
            "act_involved_requests": n_act_reqs,
            "unique_act_keys_used": len(by_act_tasks),
            "unique_act_snapshot_pairs": len(seen_act_snap),
            "version_safe_act_reuses": version_safe_reuses,
            "db_query_reduction_upper_bound_pct": round(100.0 * version_safe_reuses / max(1, n_act_reqs), 2),
            "acts_shared_across_multiple_tasks": multi_task_acts,
            "acts_shared_across_multiple_queries": multi_query_acts,
            "exact_resp_misses_in_act_reqs": exact_resp_misses_in_act,
            "residual_act_reuses_when_exact_resp_misses": residual_act_reuses_on_exact_resp_miss,
            "residual_act_hit_rate_on_exact_resp_miss_pct": round(
                100.0 * residual_act_reuses_on_exact_resp_miss / max(1, exact_resp_misses_in_act), 2
            ),
        },
        "downstream_fanout_stratification": {
            k: {
                "requests": fanout_reqs[k],
                "share_pct": round(100.0 * fanout_reqs[k] / max(1, n_act_reqs), 2),
                "total_act_cost_units": round(fanout_cost[k], 2),
            }
            for k in ("0", "1", "2", "3+")
        },
    }
    io.write_json(OUT_PATH, report)
    print(f"已写 {OUT_PATH}：")
    print(
        f"  快照数值漂移: v0->v1={report['snapshot_numerical_drift']['v0_to_v1_pct']}%, "
        f"any={report['snapshot_numerical_drift']['any_snapshot_changed_pct']}%"
    )
    print(
        f"  DB查询削减上界={report['reuse_and_db_qps_reduction']['db_query_reduction_upper_bound_pct']}%, "
        f"精确resp未命中时act残余命中率={report['reuse_and_db_qps_reduction']['residual_act_hit_rate_on_exact_resp_miss_pct']}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

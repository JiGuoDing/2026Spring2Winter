"""数据集现状体检（v0.1.0 -> v0.2.0 改动依据）。

输出 dataset/audit_v010_report.json，覆盖六项诊断：
  1. clock_gap        更新事件与文档生效时刻的时钟差
  2. act_plan         act 下游梯度与 plan 完成率分布
  3. clusters         题目频次、变体、域分布（评估簇结构可行性）
  4. update_impact    文档级/主张级影响面与局部-大改比例
  5. similarity       正负例相似度分布（TF-IDF 字 bigram 余弦）
  6. claims           每题主张数分布（局部修复可行性的前置条件）

用法：python dataset/tools/audit_v010.py
"""
from __future__ import annotations

import collections
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")


def dist(values: list[float]) -> dict:
    if not values:
        return {}
    v = sorted(values)
    n = len(v)

    def q(p: float) -> float:
        return round(v[min(n - 1, int(p * (n - 1) + 0.5))], 3)

    return {"n": n, "min": round(v[0], 3), "p50": q(0.5), "p95": q(0.95),
            "max": round(v[-1], 3), "mean": round(sum(v) / n, 3)}


def clock_gap(ups, docs) -> dict:
    rows, delays = [], []
    for u in ups:
        eff = docs.get((u["doc_id"], u["new_ver"]))
        if not eff:
            rows.append({"event_id": u["event_id"], "error": "doc_ver_missing"})
            continue
        d = (parse_ts(u["timestamp"]) - parse_ts(eff)).total_seconds() / 3600.0
        delays.append(d)
        rows.append({"event_id": u["event_id"], "doc_id": u["doc_id"],
                     "effective_at": eff, "timestamp": u["timestamp"],
                     "delay_hours": round(d, 3)})
    return {"distribution_hours": dist(delays), "negative_delay_count": sum(1 for d in delays if d < 0),
            "rows": rows[:5]}


def act_plan(pool) -> dict:
    downstream = [len(a["downstream_tools"]) for a in pool["acts"]]
    act_costs = [a["act_cost"] for a in pool["acts"]]
    plans = pool["plans"]
    comp = [p["completion_rate"] for p in plans]
    by_steps: dict[int, list[float]] = collections.defaultdict(list)
    for p in plans:
        by_steps[len(p["steps"])].append(p["completion_rate"])
    return {
        "act_downstream_dist": dict(sorted(collections.Counter(downstream).items())),
        "act_downstream_nonempty_ratio": round(sum(1 for d in downstream if d) / len(downstream), 3),
        "act_cost": dist(act_costs),
        "plan_completion": dist(comp),
        "plan_completion_by_steps": {k: round(statistics.mean(v), 3) for k, v in sorted(by_steps.items())},
        "plan_count": len(plans),
    }


def clusters(reqs, ctx, tasks) -> dict:
    freq = collections.Counter()
    for r in reqs:
        tid = ctx.get(r["req_id"], {}).get("task_id")
        if tid:
            freq[tid] += 1
    variants = collections.Counter(c.get("variant") for c in ctx.values())
    domains = collections.Counter(c.get("domain") or "?" for c in ctx.values())
    per_task = list(freq.values())
    return {
        "tasks_seen": len(freq),
        "tasks_total": len(tasks),
        "per_task_frequency": dist(per_task),
        "variant_dist": dict(variants),
        "domain_dist": dict(domains),
        "has_cluster_field": any("cluster_id" in t for t in tasks),
    }


def update_impact(reqs, ups) -> dict:
    claim_chunks = {s["chunk_id"] for r in reqs for s in r["gold_fact_spans"]}
    doc_cited = {d for r in reqs for d in r["gold_doc_ids"]}
    per_event, pairs, local, major = [], 0, 0, 0
    doc_total = claim_total = 0
    dedup_claim: set[str] = set()
    for u in ups:
        ch = set(u["changed_chunk_ids"])
        d_aff = [r["req_id"] for r in reqs if u["doc_id"] in r["gold_doc_ids"]]
        c_aff = [r["req_id"] for r in reqs
                 if any(s["chunk_id"] in ch for s in r["gold_fact_spans"])]
        doc_total += len(d_aff)
        claim_total += len(c_aff)
        dedup_claim.update(c_aff)
        for r in reqs:
            if not r["gold_fact_spans"]:
                continue
            hit = sum(1 for s in r["gold_fact_spans"] if s["chunk_id"] in ch)
            if hit == 0:
                continue
            pairs += 1
            if hit / len(r["gold_fact_spans"]) < 0.5:
                local += 1
            else:
                major += 1
        per_event.append({"event_id": u["event_id"], "change_type": u["change_type"],
                          "doc_level": len(d_aff), "claim_level": len(c_aff)})
    return {
        "doc_level_requests_total": doc_total,
        "claim_level_requests_total": claim_total,
        "claim_level_requests_dedup": len(dedup_claim),
        "affected_pairs": pairs,
        "local_ratio": round(local / pairs, 3) if pairs else 0.0,
        "major_ratio": round(major / pairs, 3) if pairs else 0.0,
        "zero_impact_events": sum(1 for e in per_event if e["doc_level"] == 0),
        "top_doc_level": sorted(per_event, key=lambda e: -e["doc_level"])[:5],
        "top_claim_level": sorted(per_event, key=lambda e: -e["claim_level"])[:5],
    }


def _char_bigrams(text: str) -> list[str]:
    t = "".join(ch for ch in text if not ch.isspace())
    return [t[i:i + 2] for i in range(max(0, len(t) - 1))]


def similarity(reqs, ctx, labels, tasks) -> dict:
    by_req = {r["req_id"]: r for r in reqs}
    by_task = {t["task_id"]: t for t in tasks}
    docs, df = [], collections.Counter()
    for r in reqs:
        toks = _char_bigrams(r["query_text"])
        tf = collections.Counter(toks)
        docs.append((r["req_id"], tf, len(toks)))
        df.update(set(tf))
    n = len(docs)
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}

    def vec(tf, total):
        v = {t: (c / total) * idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    vecs = {rid: vec(tf, total) for rid, tf, total in docs}

    def cos(a, b):
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(t, 0.0) for t, x in a.items())

    groups: dict[str, list[float]] = collections.defaultdict(list)
    for lab in labels:
        a, b = by_req.get(lab["req_id"]), by_req.get(lab["cached_req_id"])
        if not a or not b:
            continue
        s = cos(vecs[a["req_id"]], vecs[b["req_id"]])
        key = "safe" if lab["safe"] else lab["negative_type"]
        groups[key].append(s)
    return {k: {"n": len(v), **dist(v)} for k, v in sorted(groups.items())}


def claims(reqs, tasks) -> dict:
    per_req = collections.Counter(len(r["gold_fact_spans"]) for r in reqs)
    per_task = collections.Counter(len(t["truth"]["claims"]) for t in tasks)
    return {"claims_per_request": dict(sorted(per_req.items())),
            "claims_per_task": dict(sorted(per_task.items())),
            "request_claim_count_values": sorted(per_req),
            "degenerate": len(per_req) == 1}


def main() -> int:
    ups = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))
    reqs = list(io.read_jsonl(ROOT / "events" / "request_stream.jsonl"))
    tasks = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
    labels = list(io.read_jsonl(ROOT / "labels" / "safe_reuse.jsonl"))
    ctx = {c["req_id"]: c for c in io.read_jsonl(ROOT / "events" / "request_context.jsonl")}
    pool = io.read_json(ROOT / "events" / "act_plan_pool.json")
    docs = {(d["doc_id"], d["version"]): d["updated_at"]
            for d in io.read_jsonl(ROOT / "events" / "docs_versioned.jsonl")}

    report = {
        "dataset_version": "0.1.0",
        "generated_by": "tools/audit_v010.py",
        "1_clock_gap": clock_gap(ups, docs),
        "2_act_plan": act_plan(pool),
        "3_clusters": clusters(reqs, ctx, tasks),
        "4_update_impact": update_impact(reqs, ups),
        "5_similarity": similarity(reqs, ctx, labels, tasks),
        "6_claims": claims(reqs, tasks),
    }
    out = ROOT / "audit_v010_report.json"
    io.write_json(out, report)

    print(f"写出 {out.relative_to(ROOT)}")
    print("\n[1] 通知延迟(h):", report["1_clock_gap"]["distribution_hours"])
    print("[2] act 非空下游占比:", report["2_act_plan"]["act_downstream_nonempty_ratio"],
          "| 分布:", report["2_act_plan"]["act_downstream_dist"])
    print("    plan 完成率:", report["2_act_plan"]["plan_completion"],
          "| 按步数:", report["2_act_plan"]["plan_completion_by_steps"])
    print("[3] 每题频次:", report["3_clusters"]["per_task_frequency"], "| 变体:", report["3_clusters"]["variant_dist"])
    print("[4] 文档级累计:", report["4_update_impact"]["doc_level_requests_total"],
          "| 主张级累计:", report["4_update_impact"]["claim_level_requests_total"],
          "| 去重:", report["4_update_impact"]["claim_level_requests_dedup"])
    print("    局部/大改:", report["4_update_impact"]["local_ratio"], "/",
          report["4_update_impact"]["major_ratio"])
    print("[5] 相似度:", {k: v.get("mean") for k, v in report["5_similarity"].items()})
    print("[6] 每请求主张数:", report["6_claims"]["claims_per_request"],
          "| 退化:", report["6_claims"]["degenerate"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""冒烟测试：逐条执行 HANDBOOK.md 里的代码配方，确保文档与代码一致。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

sys.path.insert(0, str(ROOT / "db"))
import compare  # noqa: E402
import executor  # noqa: E402

tasks = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
reqs = list(io.read_jsonl(ROOT / "events" / "request_stream.jsonl"))
ups = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))

by_id: dict[str, dict[int, dict]] = {}
for d in io.read_jsonl(ROOT / "events" / "docs_versioned.jsonl"):
    by_id.setdefault(d["doc_id"], {})[d["version"]] = d


def doc_at(docs_by_id: dict, doc_id: str, ts: str) -> dict:
    cands = [d for d in docs_by_id[doc_id].values() if d["updated_at"] <= ts]
    return max(cands, key=lambda d: d["updated_at"])


def main() -> int:
    # 5.1 归并
    ev = [dict(kind="req", **r) for r in reqs] + [dict(kind="upd", **u) for u in ups]
    timeline = sorted(ev, key=lambda e: e["timestamp"])
    assert len(timeline) == 3040, len(timeline)
    print(f"5.1 OK  timeline={len(timeline)} 首事件={timeline[0]['kind']}")

    # 5.2 时刻取版本
    v = doc_at(by_id, "metric_045", "2024-05-15T07:00:00Z")
    assert v["version"] == 2, v["version"]
    print(f"5.2 OK  metric_045 @07:00 -> v{v['version']}")

    # 5.3 执行并比对
    task = tasks[0]
    got = executor.execute(task["snapshot"], task["gold_sql"])
    assert got["error"] is None, got["error"]
    gold = next(g for g in io.read_jsonl(ROOT / "tasks" / "gold_results.jsonl")
                if g["task_id"] == task["task_id"])
    cmp_ = compare.compare({"columns": gold["columns"], "rows": gold["rows"]},
                           {"columns": got["columns"], "rows": got["rows"]})
    assert cmp_["equal"], cmp_
    print(f"5.3 OK  {task['task_id']} 执行一致，{got['elapsed_ms']:.1f} ms")

    # 5.4 双视角谓词复算：与标签文件逐条对照
    rank = {"public": 0, "staff": 1, "restricted": 2}
    ctx = {c["req_id"]: c for c in io.read_jsonl(ROOT / "events" / "request_context.jsonl")}
    tasks_by_id = {t["task_id"]: t for t in tasks}
    ups_all = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))
    notified = {(d["doc_id"], d["version"]): d["updated_at"]
                for d in io.read_jsonl(ROOT / "events" / "docs_versioned.jsonl")}
    for u in ups_all:
        notified[(u["doc_id"], u["new_ver"])] = u["timestamp"]

    def visible_version(doc_id: str, ts: str) -> int:
        cands = [v for (did, v), t in notified.items() if did == doc_id and t <= ts]
        return max(cands) if cands else 1

    def is_safe(cached_req: dict, req: dict, system_view: bool = False):
        why = []
        if ctx[cached_req["req_id"]]["task_id"] != ctx[req["req_id"]]["task_id"]:
            why.append("task_mismatch")
        for doc_id in cached_req["gold_doc_ids"]:
            if system_view:
                a = visible_version(doc_id, cached_req["timestamp"])
                b = visible_version(doc_id, req["timestamp"])
            else:
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

    by_req = {r["req_id"]: r for r in reqs}
    ok_truth = ok_sys = total = 0
    for lab in io.read_jsonl(ROOT / "labels" / "safe_reuse.jsonl"):
        a, b = by_req[lab["cached_req_id"]], by_req[lab["req_id"]]
        p_truth, _ = is_safe(a, b, system_view=False)
        p_sys, _ = is_safe(a, b, system_view=True)
        total += 1
        ok_truth += int(p_truth == lab["safe"])
        ok_sys += int(p_sys == lab["safe_system"])
    assert ok_truth == total and ok_sys == total, f"真值 {ok_truth}/{total} 系统 {ok_sys}/{total}"
    print(f"5.4 OK  双视角谓词一致 真值 {ok_truth}/{total}、系统 {ok_sys}/{total}")

    # 5.5 更新影响
    def impact(u):
        affected = [r["req_id"] for r in reqs if u["doc_id"] in r["gold_doc_ids"]]
        hit = [(r["req_id"], s["claim"]) for r in reqs for s in r["gold_fact_spans"]
               if s["chunk_id"] in set(u["changed_chunk_ids"])]
        return affected, hit

    u = max(ups, key=lambda x: len(impact(x)[0]))
    affected, hit = impact(u)
    assert affected, f"{u['event_id']} 影响为 0，违反不变量 8"
    zero = [x["event_id"] for x in ups if x["doc_id"] not in {d for r in reqs for d in r["gold_doc_ids"]}]
    print(f"5.5 OK  {u['event_id']} 影响请求 {len(affected)} 条、主张 {len(hit)} 条；零影响更新 {len(zero)} 条")

    # 5.6 复用率
    seen, repeat = set(), 0
    for r in reqs:
        if r["plan_id"] in seen:
            repeat += 1
        seen.add(r["plan_id"])
    print(f"5.6 OK  plan 复用率 {repeat / len(reqs):.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""确定性抽取快模型 50 条分层标定样本（v0.5.0）。

从 calibration_sample.jsonl（300 条）中按难度分层抽取 50 条（single_table 15 / join 18 / nested_agg 17），
确保 100% 属于已有 300 条慢模型主标定的子集，便于同一批请求直接做「慢模型 vs. 快模型」配对对比。
输出：dataset/events/fast_calibration_sample_50.jsonl
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io, seeds  # noqa: E402

OUT_PATH = ROOT / "events" / "fast_calibration_sample_50.jsonl"
QUOTA = {"single_table": 15, "join": 18, "nested_agg": 17}


def build() -> list[dict]:
    samples = list(io.read_jsonl(ROOT / "events" / "calibration_sample.jsonl"))
    tasks = {t["task_id"]: t for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}
    reqs = {r["req_id"]: r for r in io.read_jsonl(ROOT / "events" / "request_stream.jsonl")}

    by_diff: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        t = tasks[s["task_id"]]
        r = reqs[s["req_id"]]
        by_diff[t["difficulty"]].append({
            "req_id": s["req_id"],
            "task_id": s["task_id"],
            "snapshot": s["snapshot"],
            "timestamp": s["timestamp"],
            "difficulty": t["difficulty"],
            "obj_types": r["obj_types"],
            "permission": r["permission"],
            "query_text": r["query_text"],
        })

    selected: list[dict] = []
    for diff in ("single_table", "join", "nested_agg"):
        need = QUOTA[diff]
        cands = sorted(by_diff[diff], key=lambda x: (x["snapshot"], x["req_id"]))
        shuffled = seeds.shuffle(cands, "events", f"fast_sample_50_{diff}")
        # 尽量均衡覆盖 v0/v1/v2 三份快照
        by_snap: dict[str, list[dict]] = defaultdict(list)
        for item in shuffled:
            by_snap[item["snapshot"]].append(item)
        picked: list[dict] = []
        snaps = ("v0", "v1", "v2")
        idx = 0
        while len(picked) < need:
            sn = snaps[idx % 3]
            idx += 1
            if by_snap[sn]:
                picked.append(by_snap[sn].pop(0))
        selected.extend(picked)

    selected.sort(key=lambda x: x["req_id"])
    return selected


def main() -> int:
    rows = build()
    io.write_jsonl(OUT_PATH, rows)
    diffs = defaultdict(int)
    snaps = defaultdict(int)
    for r in rows:
        diffs[r["difficulty"]] += 1
        snaps[r["snapshot"]] += 1
    print(f"已写 {OUT_PATH}（{len(rows)} 条）：难度={dict(diffs)}，快照={dict(snaps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

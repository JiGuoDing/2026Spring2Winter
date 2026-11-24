"""题库抽样质检：打印样例、统计难度/证据分布、检查口径题是否引用指标卡。"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402


def main() -> int:
    rows = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
    print(f"题目数 {len(rows)}")

    for r in rows[:3]:
        print(f"\n--- {r['task_id']} {r['difficulty']} {r['permission']}")
        print("Q :", r["question"])
        print("SQL:", " ".join(r["gold_sql"].split())[:180])
        print("val:", str(r["truth"]["value"])[:90])
        print("clm:", len(r["truth"]["claims"]), "| ev:",
              [e["doc_id"] for e in r["truth"]["evidence"]][:4],
              "| met:", r["metric_refs"][:2])

    print("\n难度分布:", dict(collections.Counter(r["difficulty"] for r in rows)))
    print("形状分布:", dict(collections.Counter(r["answer_shape"] for r in rows)))
    print("证据类型:", dict(collections.Counter(
        d.split("_")[0] for r in rows for d in [e["doc_id"] for e in r["truth"]["evidence"]])))

    metric_tasks = [r for r in rows if r["metric_refs"]]
    print(f"引用指标的题 {len(metric_tasks)}；其中证据含 metric 卡 "
          f"{sum(1 for r in metric_tasks if any(e['doc_id'].startswith('metric_') for e in r['truth']['evidence']))}")

    empty = [r["task_id"] for r in rows if r["truth"]["value"] in (None, [])]
    print("空结果题:", empty[:5], f"共 {len(empty)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

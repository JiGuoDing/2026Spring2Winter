"""汇总各目录的实际规模，用于数据集卡片与论文附录。"""
from __future__ import annotations

import collections
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402


def db_stats() -> None:
    for snap in ("v0", "v1", "v2"):
        f = ROOT / "db" / "snapshots" / f"{snap}.sqlite"
        if not f.is_file():
            print(f"[db] {snap}: 缺失")
            continue
        con = sqlite3.connect(f"file:{f}?mode=ro&immutable=1", uri=True)
        tabs = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        rows = sum(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tabs)
        print(f"[db] {snap}: {len(tabs)} 表 / {rows:,} 行 / {f.stat().st_size / 1e6:.1f} MB")
        con.close()


def knowledge_stats() -> None:
    docs, vers, chunks = collections.Counter(), collections.Counter(), 0
    doc_ids = set()
    for r in io.read_jsonl(ROOT / "knowledge" / "docs.jsonl"):
        docs[r["doc_type"]] += 1
        vers[r["version"]] += 1
        chunks += len(r["chunks"])
        doc_ids.add(r["doc_id"])
    print(f"[knowledge] 版本行 {sum(docs.values())} / 唯一文档 {len(doc_ids)} / 块 {chunks}")
    print(f"[knowledge] 类型 {dict(docs)}")
    print(f"[knowledge] 版本分布 {dict(vers)}")
    print(f"[knowledge] 变更记录 {sum(1 for _ in io.read_jsonl(ROOT / 'knowledge' / 'version_changes.jsonl'))}")


def task_stats() -> None:
    rows = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
    print(f"[tasks] {len(rows)} 题 / 难度 {dict(collections.Counter(r['difficulty'] for r in rows))}"
          f" / claims {sum(len(r['truth']['claims']) for r in rows)}"
          f" / 证据链接 {sum(len(r['truth']['evidence']) for r in rows)}")


def event_stats() -> None:
    reqs = list(io.read_jsonl(ROOT / "events" / "request_stream.jsonl"))
    snaps = collections.Counter(r["snapshot"]["index"] for r in reqs)
    objs = collections.Counter(t for r in reqs for t in r["obj_types"])
    ups = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))
    cls = collections.Counter(u["change_type"] for u in ups)
    pool = io.read_json(ROOT / "events" / "act_plan_pool.json")
    print(f"[events] 请求 {len(reqs)} / 快照 {dict(snaps)}")
    print(f"[events] 对象角色 {dict(objs)}")
    print(f"[events] 更新 {len(ups)} / {dict(cls)}")
    print(f"[events] act {len(pool['acts'])} / plan {len(pool['plans'])}")
    for d in sorted((ROOT / "events" / "streams").glob("*.jsonl")):
        print(f"[events] {d.name}: {sum(1 for _ in io.read_jsonl(d))}")


def cost_label_stats() -> None:
    f = ROOT / "costs" / "path_costs.csv"
    if f.is_file():
        lines = f.read_text(encoding="utf-8").splitlines()
        head = lines[0].split(",")
        measured = sum(1 for ln in lines[1:] if "measured" in head and
                       ln.split(",")[head.index("measured")].strip() not in ("", "NA", "False", "0"))
        print(f"[costs] {len(lines) - 1} 行 / measured 非空 {measured}")
    else:
        print("[costs] 缺 path_costs.csv")

    lb = ROOT / "labels"
    if (lb / "safe_reuse.jsonl").is_file():
        rows = list(io.read_jsonl(lb / "safe_reuse.jsonl"))
        print(f"[labels] safe_reuse {len(rows)} / safe {sum(1 for r in rows if r['safe'])}"
              f" / 负例类型 {dict(collections.Counter(r['negative_type'] for r in rows))}")
    else:
        print("[labels] 缺 safe_reuse.jsonl")


def main() -> int:
    db_stats()
    knowledge_stats()
    task_stats()
    event_stats()
    cost_label_stats()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

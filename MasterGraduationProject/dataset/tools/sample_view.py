"""抽样展示各层真实记录，用于说明数据集长什么样。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402


def first(path: Path, pred):
    for r in io.read_jsonl(path):
        if pred(r):
            return r
    return None


def show(title: str, obj, keys=None) -> None:
    print(f"\n=== {title} ===")
    if keys:
        obj = {k: obj[k] for k in keys if k in obj}
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:1400])


def main() -> int:
    docs = ROOT / "knowledge" / "docs.jsonl"
    show("字段卡 fld_t12_05", first(docs, lambda r: r["doc_id"] == "fld_t12_05" and r["version"] == 1))
    show("指标卡 metric_045", first(docs, lambda r: r["doc_id"] == "metric_045" and r["version"] == 2))
    show("白皮书 wp_002（第一块）", first(docs, lambda r: r["doc_id"] == "wp_002" and r["version"] == 1))

    show("更新事件 u0001", first(ROOT / "events" / "update_events.jsonl", lambda r: True))
    show("请求 r000055", first(ROOT / "events" / "request_stream.jsonl",
                               lambda r: r["req_id"] == "r000055"))
    show("安全标签 b00001", first(ROOT / "labels" / "safe_reuse.jsonl", lambda r: True))
    show("负例标签（第一条非安全）",
         first(ROOT / "labels" / "safe_reuse.jsonl", lambda r: not r["safe"]))
    show("分支配对 b00001", first(ROOT / "labels" / "branch_pairs.jsonl", lambda r: True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

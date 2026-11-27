"""打印若干完整文档样本：每类一篇 + 一篇跨三个版本的变更对照。

用法：python dataset/tools/show_docs.py [doc_id ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

DEFAULT = ["fld_t12_05", "wp_002", "tool_007", "plan_01", "note_012"]
VERSION_DEMO = "metric_045"


def load() -> dict:
    by: dict[str, dict[int, dict]] = {}
    for r in io.read_jsonl(ROOT / "knowledge" / "docs.jsonl"):
        by.setdefault(r["doc_id"], {})[r["version"]] = r
    return by


def dump(doc: dict) -> None:
    print(f"--- {doc['doc_id']}  v{doc['version']}  [{doc['doc_type']}/{doc['domain']}/"
          f"{doc['permission']}]  updated_at={doc['updated_at']}  "
          f"chunks={len(doc['chunks'])}")
    for c in doc["chunks"]:
        print(f"\n  [{c['chunk_id']}]  hash={c.get('hash','')[:12]}")
        print("  " + c["text"])


def main() -> int:
    docs = load()
    ids = sys.argv[1:] or DEFAULT
    for doc_id in ids:
        if doc_id not in docs:
            print(f"!! 不存在 {doc_id}")
            continue
        dump(docs[doc_id][1])
        print()

    print("\n================ 跨版本对照 ================")
    for v in (1, 2, 3):
        dump(docs[VERSION_DEMO][v])
        print()

    print("================ 变更记录 ================")
    for ch in io.read_jsonl(ROOT / "knowledge" / "version_changes.jsonl"):
        if ch["doc_id"] == VERSION_DEMO:
            print(ch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

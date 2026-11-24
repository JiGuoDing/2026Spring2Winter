"""生成 fixtures 样例数据（P0 契约的一部分）。

产出 dataset/fixtures/ 下四份文件，各 2–3 条记录，字段严格符合 schema，
供下游 agent 在真实数据尚未生成时解耦开发。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import ids, io  # noqa: E402

V0 = "2024-05-15T00:00:00Z"
V1 = "2024-05-15T06:00:00Z"


def docs() -> list[dict]:
    out = []
    for doc_id, ver, ts in (("fld_t01_01", 1, V0), ("metric_001", 1, V0), ("wp_001", 1, V0)):
        kind = ids.doc_type_of(doc_id)
        chunks = [{"chunk_id": ids.block_id(doc_id, 1),
                   "text": f"{doc_id} 的样例说明段落，用于契约自检。",
                   "hash": "0" * 16}]
        if kind in ("whitepaper", "metric"):
            chunks.append({"chunk_id": ids.block_id(doc_id, 2),
                           "text": f"{doc_id} 的第二个样例段落。",
                           "hash": "1" * 16})
        out.append({"doc_id": doc_id, "version": ver, "doc_type": kind, "domain": "sales",
                    "permission": "public", "updated_at": ts, "chunks": chunks})
    return out


def requests() -> list[dict]:
    out = []
    for i in (1, 2, 3):
        out.append({
            "req_id": ids.req_id(i),
            "timestamp": V0 if i < 3 else V1,
            "query_text": f"上个月华东区 GMV 是多少（样例 {i}）",
            "query_emb": None,
            "plan_id": ids.plan_id(1),
            "act_key": "act_sql_exec",
            "gold_doc_ids": ["metric_001", "wp_001"],
            "gold_fact_spans": [{"claim": "GMV 口径按支付时间统计",
                                 "chunk_id": ids.block_id("metric_001", 1)}],
            "domain": "sales",
            "permission": "public",
            "snapshot": {"index": "v0", "as_of": V0},
            "obj_types": ["rag", "act", "resp"],
        })
    return out


def updates() -> list[dict]:
    return [{
        "event_id": ids.upd_id(1),
        "timestamp": V1,
        "doc_id": "metric_001",
        "old_ver": 1,
        "new_ver": 2,
        "changed_chunk_ids": [ids.block_id("metric_001", 1)],
        "change_type": "metric_revision",
        "domain": "sales",
        "permission": "public",
        "answer_impact": "changed",
    }]


def pool() -> dict:
    return {
        "acts": [
            {"act_key": "act_sql_exec", "act_cost": 0.35, "downstream_tools": [], "readonly": True},
            {"act_key": "act_schema_lookup", "act_cost": 0.05, "downstream_tools": [], "readonly": True},
            {"act_key": "act_lineage_trace", "act_cost": 0.08, "downstream_tools": [], "readonly": True},
        ],
        "plans": [
            {"plan_id": ids.plan_id(1), "plan_cost": 0.60, "completion_rate": 0.92,
             "steps": ["解析口径", "定位表", "生成 SQL", "执行", "组织回答"]},
            {"plan_id": ids.plan_id(2), "plan_cost": 0.45, "completion_rate": 0.88,
             "steps": ["解析口径", "执行", "组织回答"]},
        ],
    }


def main() -> int:
    fx = ROOT / "fixtures"
    io.write_jsonl(fx / "docs_versioned.sample.jsonl", docs())
    io.write_jsonl(fx / "request_stream.sample.jsonl", requests())
    io.write_jsonl(fx / "update_events.sample.jsonl", updates())
    io.write_json(fx / "act_plan_pool.sample.json", pool())
    print("fixtures written:", sorted(p.name for p in fx.iterdir()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

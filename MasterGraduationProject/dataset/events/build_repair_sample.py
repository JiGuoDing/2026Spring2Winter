"""确定性构造 C3 局部修复 / 完整重生成 / 在线双检先导标定样本集（v0.4.0）。

输出：dataset/events/repair_calibration_sample.jsonl（40 对，固定分层配比）
  - local_change       : 20 对（0 < rho < 0.5，局部主张变更）
  - major_change       : 10 对（rho >= 0.5，大改/多主张变更）
  - doc_only_unchanged : 10 对（文档被引用但变更块未命中任何主张）

关键约束：
  1. 100% 绑定 embeddings/calibration/requests_progress.jsonl 中已实测且有旧回答正文的 req_id，
     无需重复生成旧回答。
  2. 确定性抽样（common/seeds.py::rng("events", "repair_sample")），同输入同哈希。
  3. 仅作为标定输入样本集，不修改任何 v0.3.0 主干文件。
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io, seeds  # noqa: E402

OUT_PATH = ROOT / "events" / "repair_calibration_sample.jsonl"
PROGRESS_PATH = ROOT / "embeddings" / "calibration" / "requests_progress.jsonl"
TARGET_STRATA = {
    "local_change": 20,
    "major_change": 10,
    "doc_only_unchanged": 10,
}


def _doc_chunk_map(docs_path: Path) -> dict[tuple[str, int], dict[str, str]]:
    out: dict[tuple[str, int], dict[str, str]] = {}
    for row in io.read_jsonl(docs_path):
        out[(row["doc_id"], row["version"])] = {c["chunk_id"]: c["text"] for c in row["chunks"]}
    return out


def build() -> list[dict]:
    reqs_by_id = {r["req_id"]: r for r in io.read_jsonl(ROOT / "events" / "request_stream.jsonl")}
    updates = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))
    progress = {p["req_id"]: p for p in io.read_jsonl(PROGRESS_PATH) if p.get("resp_text")}
    chunks = _doc_chunk_map(ROOT / "events" / "docs_versioned.jsonl")

    buckets: dict[str, list[dict]] = defaultdict(list)

    for u in updates:
        if u.get("negative_control"):
            continue
        doc_id = u["doc_id"]
        old_ver = u["old_ver"]
        new_ver = u["new_ver"]
        changed = set(u["changed_chunk_ids"])
        old_chunks = chunks.get((doc_id, old_ver), {})
        new_chunks = chunks.get((doc_id, new_ver), {})

        for req_id, prog in sorted(progress.items()):
            r = reqs_by_id.get(req_id)
            if r is None or doc_id not in r["gold_doc_ids"]:
                continue
            spans = r["gold_fact_spans"]
            hit_claims = [sp for sp in spans if sp["chunk_id"] in changed]
            n_claims = max(1, len(spans))
            rho = len(hit_claims) / n_claims

            if len(hit_claims) == 0:
                stratum = "doc_only_unchanged"
            elif rho < 0.5:
                stratum = "local_change"
            else:
                stratum = "major_change"

            diff_chunks = [
                {
                    "chunk_id": cid,
                    "old_text": old_chunks.get(cid, ""),
                    "new_text": new_chunks.get(cid, ""),
                }
                for cid in sorted(changed)
            ]

            buckets[stratum].append({
                "stratum": stratum,
                "event_id": u["event_id"],
                "req_id": req_id,
                "task_id": prog["task_id"],
                "snapshot": prog["snapshot"],
                "doc_id": doc_id,
                "old_ver": old_ver,
                "new_ver": new_ver,
                "change_type": u["change_type"],
                "domain": u["domain"],
                "query_text": r["query_text"],
                "n_claims": len(spans),
                "hit_claims_cnt": len(hit_claims),
                "rho": round(rho, 4),
                "changed_chunk_ids": sorted(changed),
                "diff_chunks": diff_chunks,
                "old_resp_text": prog["resp_text"].strip(),
                "old_resp_ms": prog["t_resp_ms"],
                "old_token_cost": prog["token_cost"],
            })

    selected: list[dict] = []
    used_pairs: set[tuple[str, str]] = set()

    for stratum in ("local_change", "major_change", "doc_only_unchanged"):
        need = TARGET_STRATA[stratum]
        cands = sorted(buckets[stratum], key=lambda x: (x["event_id"], x["req_id"]))
        assert len(cands) >= need, f"{stratum} 候选仅 {len(cands)}，不足 {need}"
        shuffled = seeds.shuffle(cands, "events", f"repair_sample_{stratum}")

        # 尽量分散到不同 event_id 与 req_id，提高覆盖多样性
        picked: list[dict] = []
        seen_req: set[str] = set()
        for item in shuffled:
            key = (item["event_id"], item["req_id"])
            if key in used_pairs or item["req_id"] in seen_req:
                continue
            picked.append(item)
            used_pairs.add(key)
            seen_req.add(item["req_id"])
            if len(picked) == need:
                break
        if len(picked) < need:
            for item in shuffled:
                key = (item["event_id"], item["req_id"])
                if key in used_pairs:
                    continue
                picked.append(item)
                used_pairs.add(key)
                if len(picked) == need:
                    break
        assert len(picked) == need, f"{stratum} 仅选出 {len(picked)} != {need}"
        selected.extend(picked)

    selected.sort(key=lambda x: (x["stratum"], x["event_id"], x["req_id"]))
    for i, row in enumerate(selected, 1):
        row["pair_id"] = f"rp{i:04d}"
    return selected


def main() -> int:
    rows = build()
    io.write_jsonl(OUT_PATH, rows)
    counts = defaultdict(int)
    for r in rows:
        counts[r["stratum"]] += 1
    print(f"已写 {OUT_PATH}（{len(rows)} 对）：{dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

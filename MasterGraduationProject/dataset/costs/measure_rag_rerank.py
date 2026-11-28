"""现代六阶段 RAG 真实耗时标定 + 4 组标准 IR 指标评测（v0.5.0）。

1. 先在独立验证流 seed43（抽样 30 条）上校准 Dynamic Cutoff 阈值 tau_rerank；
2. 再在 calibration_sample.jsonl（300 条，支持 --limit 调试）上真实运行 4 组消融：
     - bm25_only
     - dense_only
     - hybrid_rrf
     - hybrid_rrf_rerank_dynamic（完整现代六阶段流水线）
3. 输出：
     - dataset/costs/rag_rerank_costs.csv（分阶段与端到端 p50/p95/mean，measured=1）
     - dataset/costs/rag_ir_eval.csv（Chunk Recall@K, Doc Recall@5, MRR@5, NDCG@5, avg_k）
     - dataset/embeddings/calibration/rag_rerank_300.jsonl（逐请求明细）
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "costs"))

import rag_pipeline  # noqa: E402
from common import io, seeds  # noqa: E402

OUT_COSTS = ROOT / "costs" / "rag_rerank_costs.csv"
OUT_IR = ROOT / "costs" / "rag_ir_eval.csv"
OUT_DETAIL = ROOT / "embeddings" / "calibration" / "rag_rerank_300.jsonl"


def _pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def ir_metrics(req: dict, items: list[dict]) -> dict:
    gold_chunks = {sp["chunk_id"] for sp in req["gold_fact_spans"]}
    gold_docs = set(req["gold_doc_ids"])

    ret_chunks = [it["chunk_id"] for it in items]
    chunk_recall = len(gold_chunks & set(ret_chunks)) / max(1, len(gold_chunks))

    # 文档级去重保序取前 5
    ret_docs: list[str] = []
    for it in items:
        if it["doc_id"] not in ret_docs:
            ret_docs.append(it["doc_id"])
    top5_docs = ret_docs[:5]
    doc_recall5 = len(gold_docs & set(top5_docs)) / max(1, len(gold_docs))

    mrr5 = 0.0
    for rank, d in enumerate(top5_docs, 1):
        if d in gold_docs:
            mrr5 = 1.0 / rank
            break

    dcg = sum(1.0 / math.log2(rank + 1) for rank, d in enumerate(top5_docs, 1) if d in gold_docs)
    ideal_hits = min(len(gold_docs), 5)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    ndcg5 = dcg / idcg if idcg > 0 else 0.0

    return {
        "chunk_recall": chunk_recall,
        "doc_recall_at_5": doc_recall5,
        "mrr_at_5": mrr5,
        "ndcg_at_5": ndcg5,
        "k_returned": len(items),
    }


def calibrate_tau(pipe: rag_pipeline.ModernRAGPipeline, rerank_top_k: int = 12) -> float:
    """在独立验证流 seed43 上抽样 20 条校准 tau_rerank，兼顾 Chunk/Doc Recall 与精简块数。"""
    val_reqs = list(io.read_jsonl(ROOT / "events" / "streams" / "seed43.jsonl"))
    sample = seeds.shuffle(val_reqs, "costs", "tau_calib_seed43")[:20]
    scored_lists = []
    for req in sample:
        perm_level = rag_pipeline.labels_build.PRIV[req["permission"]]
        a_arr, a_set = pipe._active_indices(req["timestamp"], perm_level)
        b_res = pipe.bm25_search(req["query_text"], a_set, top_k=30)
        d_res = pipe.dense_search(pipe.encode_query(req["query_text"]), a_arr, top_k=30)
        fused = pipe.rrf_fuse(b_res, d_res, k_rrf=60, top_k=rerank_top_k)
        reranked = pipe.rerank(req["query_text"], [i for i, _ in fused])
        scored_lists.append((req, reranked))

    best_tau = 0.15
    best_obj = -1e9
    for tau in (0.05, 0.10, 0.20, 0.35, 0.50):
        c_recs: list[float] = []
        d_recs: list[float] = []
        ks: list[int] = []
        for req, reranked in scored_lists:
            sel = []
            dc: dict[str, int] = defaultdict(int)
            for idx, sc in reranked:
                did = pipe.doc_ids[idx]
                if dc[did] >= 2:
                    continue
                if len(sel) >= 3 and sc < tau:
                    break
                dc[did] += 1
                sel.append({"doc_id": did, "chunk_id": pipe.chunk_ids[idx]})
                if len(sel) >= 8:
                    break
            m = ir_metrics(req, sel)
            c_recs.append(m["chunk_recall"])
            d_recs.append(m["doc_recall_at_5"])
            ks.append(m["k_returned"])
        obj = 0.5 * statistics.fmean(c_recs) + 0.5 * statistics.fmean(d_recs) - 0.005 * statistics.fmean(ks)
        print(
            f"  [seed43 tau={tau:.2f}] chunk_R={statistics.fmean(c_recs):.4f}, "
            f"doc_R@5={statistics.fmean(d_recs):.4f}, avg_k={statistics.fmean(ks):.2f}, obj={obj:.4f}",
            flush=True,
        )
        if obj > best_obj:
            best_obj = obj
            best_tau = tau
    print(f"选定校准阈值 tau_rerank = {best_tau:.2f}", flush=True)
    return best_tau


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="仅测前 N 条（0 表示全部 300 条）")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--rerank-top-k", type=int, default=12)
    args = ap.parse_args()

    pipe = rag_pipeline.ModernRAGPipeline(load_reranker=True, threads=args.threads)
    print("步骤 1：在独立验证流 seed43 上校准动态截断阈值 tau_rerank ...", flush=True)
    tau = calibrate_tau(pipe, rerank_top_k=args.rerank_top_k)

    cal_samples = list(io.read_jsonl(ROOT / "events" / "calibration_sample.jsonl"))
    reqs_by_id = {r["req_id"]: r for r in io.read_jsonl(ROOT / "events" / "request_stream.jsonl")}
    reqs = [reqs_by_id[s["req_id"]] for s in cal_samples]
    if args.limit > 0:
        reqs = reqs[: args.limit]

    modes = ("bm25_only", "dense_only", "hybrid_rrf", "hybrid_rrf_rerank_dynamic")
    ir_buckets: dict[str, list[dict]] = defaultdict(list)
    stage_timings: dict[str, list[float]] = defaultdict(list)
    detail_rows: list[dict] = []

    print(f"步骤 2：在 {len(reqs)} 条标定请求上运行 4 组对照与 6 阶段真实耗时标定 ...", flush=True)
    for i, req in enumerate(reqs, 1):
        for mode in modes:
            res = pipe.retrieve(req, mode=mode, tau_rerank=tau, rerank_top_k=args.rerank_top_k)
            m = ir_metrics(req, res["items"])
            ir_buckets[mode].append({**m, "e2e_ms": res["timings_ms"]["e2e_rag"]})
            if mode == "hybrid_rrf_rerank_dynamic":
                for st, val in res["timings_ms"].items():
                    stage_timings[st].append(val)
                detail_rows.append({
                    "req_id": req["req_id"],
                    "tau_rerank": tau,
                    "k_returned": res["k_returned"],
                    "context_chars": res["context_chars"],
                    "timings_ms": res["timings_ms"],
                    "ir": m,
                    "top_chunks": [
                        {"doc_id": it["doc_id"], "version": it["version"], "chunk_id": it["chunk_id"], "score": it["score"]}
                        for it in res["items"]
                    ],
                })
        if i % 30 == 0 or i == len(reqs):
            print(f"  进度 {i}/{len(reqs)} | e2e_rag p50={_pct(stage_timings['e2e_rag'], 50):.1f} ms", flush=True)

    # 写 rag_rerank_costs.csv
    cost_cols = ["stage", "n", "p50_ms", "p95_ms", "mean_ms", "measured", "mock", "note"]
    notes = {
        "prefilter": "RBAC (PRIV[doc.perm]<=PRIV[req.perm]) 与 sys_ver(doc,ts) 前置过滤",
        "query_encode": "bge-small-zh-v1.5 ONNX 实时查询编码",
        "bm25": "Contextual BM25 块级倒排召回 Top-30",
        "dense": "13,770 块向量矩阵内积召回 Top-30",
        "rrf": "Reciprocal Rank Fusion (k=60) 融合至 Top-20",
        "rerank": "bge-reranker-v2-m3 INT8 ONNX 交叉编码器重排 Top-20",
        "repack": f"Per-Doc Cap=2 + 动态阈值截断(tau={tau:.2f}, K∈[3,8]) + Sides Repacking",
        "e2e_rag": "现代六阶段块级 RAG 端到端本地实测耗时（全实测，零伪造）",
    }
    cost_rows = []
    for st in ("prefilter", "query_encode", "bm25", "dense", "rrf", "rerank", "repack", "e2e_rag"):
        vals = stage_timings[st]
        cost_rows.append({
            "stage": st,
            "n": len(vals),
            "p50_ms": f"{_pct(vals, 50):.4f}",
            "p95_ms": f"{_pct(vals, 95):.4f}",
            "mean_ms": f"{statistics.fmean(vals):.4f}",
            "measured": "1",
            "mock": "",
            "note": notes[st],
        })
    with OUT_COSTS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cost_cols)
        w.writeheader()
        w.writerows(cost_rows)

    # 写 rag_ir_eval.csv
    ir_cols = [
        "mode", "n", "chunk_recall_pct", "doc_recall_at_5_pct",
        "mrr_at_5", "ndcg_at_5", "avg_k_returned", "p50_latency_ms", "p95_latency_ms", "tau_rerank",
    ]
    ir_rows = []
    for mode in modes:
        bs = ir_buckets[mode]
        ir_rows.append({
            "mode": mode,
            "n": len(bs),
            "chunk_recall_pct": round(100.0 * statistics.fmean(x["chunk_recall"] for x in bs), 2),
            "doc_recall_at_5_pct": round(100.0 * statistics.fmean(x["doc_recall_at_5"] for x in bs), 2),
            "mrr_at_5": round(statistics.fmean(x["mrr_at_5"] for x in bs), 4),
            "ndcg_at_5": round(statistics.fmean(x["ndcg_at_5"] for x in bs), 4),
            "avg_k_returned": round(statistics.fmean(x["k_returned"] for x in bs), 2),
            "p50_latency_ms": round(_pct([x["e2e_ms"] for x in bs], 50), 2),
            "p95_latency_ms": round(_pct([x["e2e_ms"] for x in bs], 95), 2),
            "tau_rerank": tau if mode == "hybrid_rrf_rerank_dynamic" else "",
        })
    with OUT_IR.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ir_cols)
        w.writeheader()
        w.writerows(ir_rows)

    io.write_jsonl(OUT_DETAIL, detail_rows)
    print(f"已写 {OUT_COSTS}、{OUT_IR}、{OUT_DETAIL}")
    for r in ir_rows:
        print(
            f"  {r['mode']:26s} | chunk_R={r['chunk_recall_pct']:5.1f}% | doc_R@5={r['doc_recall_at_5_pct']:5.1f}% "
            f"| MRR@5={r['mrr_at_5']:.4f} | NDCG@5={r['ndcg_at_5']:.4f} | avgK={r['avg_k_returned']:.2f} | p50={r['p50_latency_ms']} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

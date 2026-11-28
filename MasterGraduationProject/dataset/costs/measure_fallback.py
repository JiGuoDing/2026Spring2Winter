"""本地回退额外开销实测脚本（v0.4.0）。

测量四类缓存对象在「尝试复用 -> 有效性/版本校验失败 -> 回退正常路径」时
产生的本地探测与校验额外开销（perf_counter 实测，n=3000），写入：
    dataset/costs/fallback_costs.csv

设计原则：
1. 严守 measured 与 pending 隔离：本地可测项写入 measured=1, mock=""；
   涉及模型调用的 plan 适配/返工回退项写入 measured="", mock="pending"，绝不伪造。
2. 额外开销定义严格对齐论文 §1.2.1：「尝试后回退的总耗时 - 直接正常执行的耗时」，
   即纯查表、向量相似度匹配与版本/权限/块哈希校验所消耗的额外时间。
"""
from __future__ import annotations

import csv
import hashlib
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "labels"))

from common import io  # noqa: E402
import build as labels_build  # noqa: E402

OUT_CSV = ROOT / "costs" / "fallback_costs.csv"
HEADER = [
    "obj_type", "fallback_path", "stage", "n",
    "p50_ms", "p95_ms", "mean_ms", "measured", "mock", "note",
]


def _pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def measure_all() -> list[dict]:
    ds = labels_build.Dataset()
    reqs = sorted(ds.reqs, key=lambda r: (r["timestamp"], r["req_id"]))
    n = len(reqs)

    # 准备向量矩阵与内存缓存表（模拟活跃索引）
    texts, emb = io.load_query_embeddings()
    text_to_idx = {t: i for i, t in enumerate(texts)}
    emb_f32 = emb.astype(np.float32)

    exact_cache: dict[tuple, dict] = {}
    rag_cache: dict[str, list[tuple[str, int, str]]] = {}
    act_cache: dict[str, tuple[str, str]] = {}

    for r in reqs[:300]:
        key = (r["query_text"], r["permission"], r["snapshot"]["index"])
        exact_cache[key] = r
        doc_ids = r["gold_doc_ids"]
        rag_cache[r["query_text"]] = [
            (d, ds.sys_ver(d, r["timestamp"]), next(iter(ds.chunk_hashes(d, ds.sys_ver(d, r["timestamp"])).values())))
            for d in doc_ids
        ]
        if r.get("act_key"):
            act_cache[r["act_key"]] = (r["snapshot"]["index"], r["permission"])

    # 活跃语义候选池（取 200 条代表活跃工作集）
    sem_pool_reqs = reqs[:200]
    sem_pool_idx = np.array([text_to_idx[r["query_text"]] for r in sem_pool_reqs], dtype=np.int64)
    sem_pool_mat = emb_f32[sem_pool_idx]

    # 1) resp_exact_invalid_fallback：精确查表 + 权限/版本/块哈希核对失败
    t_resp_exact: list[float] = []
    for r in reqs:
        t0 = time.perf_counter()
        key = (r["query_text"], r["permission"], r["snapshot"]["index"])
        hit = exact_cache.get(key)
        if hit is not None:
            for d in hit["gold_doc_ids"]:
                _ = ds.sys_ver(d, r["timestamp"])
                _ = ds.chunk_hashes(d, 1)
        t_resp_exact.append((time.perf_counter() - t0) * 1000.0)

    # 2) resp_sem_invalid_fallback：语义召回 Top-1 + 硬校验失败回退
    t_resp_sem: list[float] = []
    for r in reqs:
        t0 = time.perf_counter()
        q_vec = emb_f32[text_to_idx[r["query_text"]]]
        sims = sem_pool_mat @ q_vec
        best = int(sims.argmax())
        cand = sem_pool_reqs[best]
        _ = labels_build.view_judge(ds, cand, r, "system")["safe"]
        t_resp_sem.append((time.perf_counter() - t0) * 1000.0)

    # 3) rag_stale_fallback：查 rag 缓存 + 逐块校验版本/哈希失败 -> 准备回退完整检索
    t_rag_fb: list[float] = []
    for r in reqs:
        t0 = time.perf_counter()
        entries = rag_cache.get(r["query_text"])
        if entries:
            for doc_id, cached_ver, cached_hash in entries:
                cur_v = ds.sys_ver(doc_id, r["timestamp"])
                cur_hashes = ds.chunk_hashes(doc_id, cur_v)
                _ = (cur_v == cached_ver) and (cached_hash in cur_hashes.values())
        else:
            _ = hashlib.sha256(r["query_text"].encode("utf-8")).hexdigest()[:16]
        t_rag_fb.append((time.perf_counter() - t0) * 1000.0)

    # 4) act_stale_fallback：查 act 签名表 + 校验快照/权限失败 -> 准备回退 SQL 执行
    t_act_fb: list[float] = []
    for r in reqs:
        t0 = time.perf_counter()
        ak = r.get("act_key")
        if ak and ak in act_cache:
            c_snap, c_perm = act_cache[ak]
            _ = (c_snap == r["snapshot"]["index"]) and (
                labels_build.PRIV[r["permission"]] >= labels_build.PRIV[c_perm]
            )
        t_act_fb.append((time.perf_counter() - t0) * 1000.0)

    def make_row(obj: str, path: str, stage: str, vals: list[float], note: str) -> dict:
        return {
            "obj_type": obj,
            "fallback_path": path,
            "stage": stage,
            "n": len(vals),
            "p50_ms": f"{_pct(vals, 50):.6f}",
            "p95_ms": f"{_pct(vals, 95):.6f}",
            "mean_ms": f"{statistics.fmean(vals):.6f}",
            "measured": "1",
            "mock": "",
            "note": note,
        }

    rows = [
        make_row(
            "resp", "resp_exact_invalid_fallback", "lookup_and_check_fail", t_resp_exact,
            "精确查表+版本/块哈希核对失败后的额外开销（不含后续正常执行）；纯本地 perf_counter 实测",
        ),
        make_row(
            "resp", "resp_sem_invalid_fallback", "sem_recall_and_check_fail", t_resp_sem,
            "200条活跃池句向量Top-1召回+系统视角硬校验失败后的额外开销（不含后续正常执行）；纯本地实测",
        ),
        make_row(
            "rag", "rag_stale_fallback", "chunk_version_check_fail", t_rag_fb,
            "证据块版本与哈希校验失败后回退完整检索的额外探测开销；纯本地 perf_counter 实测",
        ),
        make_row(
            "act", "act_stale_fallback", "signature_state_check_fail", t_act_fb,
            "只读工具签名查表+快照/权限校验失败后回退SQL执行的额外探测开销；纯本地 perf_counter 实测",
        ),
        {
            "obj_type": "plan",
            "fallback_path": "plan_adapt_rework_fallback",
            "stage": "adapt_fail_or_rework",
            "n": 0,
            "p50_ms": "",
            "p95_ms": "",
            "mean_ms": "",
            "measured": "",
            "mock": "pending",
            "note": "计划模板适配失败或执行返工的模型段额外开销；尚未实测，严禁补零或伪造，EvalPath 缺数须返回 UNRESOLVABLE",
        },
    ]
    return rows


def main() -> int:
    rows = measure_all()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    print(f"已写 {OUT_CSV}（{len(rows)} 行）")
    for r in rows:
        print(f"  {r['obj_type']:4s} | {r['fallback_path']:28s} | p50={r['p50_ms'] or 'pending'} ms | measured={r['measured'] or '-'} mock={r['mock'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

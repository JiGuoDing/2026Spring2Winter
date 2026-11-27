"""M2：静态基线的"有效命中 vs 过期误用"权衡（动机实验第二组）。

回放三条 TTL 基线与一条纯语义基线，用数据集自带的权威谓词
`dataset/labels/build.py::view_judge(view="truth")` 判定每次复用是否安全。

基线：
  ttl_short  = 18h × 0.03 ≈ 0.54 h（创建时间起算，不滑动刷新）
  ttl_mid    = 18h × 0.18 ≈ 3.24 h
  ttl_long   = 18h × 0.75 ≈ 13.5 h
  semantic   = 句向量余弦 ≥ 0.88 即复用，不看版本/时间（params.semantic_threshold）

另算一个 oracle 上界：同题历史条目里存在"安全"复用候选的比例，
用来衡量 TTL 因为过期而**丢弃了多少本可安全复用的机会**。

输出：exp_motivation/results/m2_baselines.csv、m2_summary.md
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT.parent / "dataset"
sys.path.insert(0, str(DATASET))
sys.path.insert(0, str(DATASET / "labels"))
import build as labels_build  # noqa: E402

OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)

TTL_FRACTIONS = {"ttl_short": 0.03, "ttl_mid": 0.18, "ttl_long": 0.75}
SPAN_HOURS = 18.0
SEM_THRESHOLD = 0.88


def ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def judge(ds, cached: dict, req: dict) -> bool:
    return bool(labels_build.view_judge(ds, cached, req, "truth")["safe"])


def run_ttl(ds, reqs, ttl_s: float) -> dict:
    cache: dict[str, tuple[dict, float]] = {}
    hits = safe = stale = missed_safe = 0
    for req in reqs:
        task_id = ds.task_of(req)
        decided = False
        entry = cache.get(task_id)
        if entry is not None:
            cached, t_cached = entry
            fresh = (ts(req["timestamp"]) - t_cached) <= ttl_s
            if fresh:
                hits += 1
                decided = True
                if judge(ds, cached, req):
                    safe += 1
                else:
                    stale += 1
            elif judge(ds, cached, req):
                missed_safe += 1
        if not decided and entry is None:
            pass
        if not decided:
            cache[task_id] = (req, ts(req["timestamp"]))
    return {"hits": hits, "safe": safe, "stale": stale, "missed_safe": missed_safe}


def run_semantic(ds, reqs) -> dict:
    npz = np.load(DATASET / "embeddings" / "query_embeddings.npz", allow_pickle=False)
    texts = [str(t) for t in npz["query_texts"]]
    emb = npz["embeddings"].astype(np.float32)
    idx = {t: i for i, t in enumerate(texts)}
    cache: dict[str, dict] = {}          # text -> 该问句最近一次条目
    hits = safe = stale = missed_safe = 0
    for req in reqs:
        text = req["query_text"]
        used = False
        if cache:
            cand_texts = list(cache)
            cand_idx = np.array([idx[t] for t in cand_texts])
            sims = emb[cand_idx] @ emb[idx[text]]
            best = int(sims.argmax())
            if sims[best] >= SEM_THRESHOLD:
                cached = cache[cand_texts[best]]
                hits += 1
                used = True
                if judge(ds, cached, req):
                    safe += 1
                else:
                    stale += 1
            elif judge(ds, cache[cand_texts[best]], req):
                missed_safe += 1
        cache[text] = req
    return {"hits": hits, "safe": safe, "stale": stale, "missed_safe": missed_safe}


def run_oracle(ds, reqs, lookback: int = 8) -> dict:
    """上界：同题最近的 lookback 个历史条目里，只要存在安全候选就记为可复用。"""
    history: dict[str, list[dict]] = defaultdict(list)
    possible = 0
    for req in reqs:
        task_id = ds.task_of(req)
        for prev in reversed(history[task_id][-lookback:]):
            if judge(ds, prev, req):
                possible += 1
                break
        history[task_id].append(req)
    return {"possible_safe": possible}


def main() -> int:
    ds = labels_build.Dataset()
    reqs = sorted(ds.reqs, key=lambda r: (r["timestamp"], r["req_id"]))
    n = len(reqs)
    print(f"回放 {n} 条请求")

    oracle = run_oracle(ds, reqs)
    rows = []
    for name, frac in TTL_FRACTIONS.items():
        ttl_s = frac * SPAN_HOURS * 3600
        r = run_ttl(ds, reqs, ttl_s)
        rows.append({"policy": name, "ttl_hours": round(ttl_s / 3600, 2), **r, "n": n})
        print(f"{name}: 命中 {r['hits']} 有效 {r['safe']} 误用 {r['stale']} 错失 {r['missed_safe']}")
    r = run_semantic(ds, reqs)
    rows.append({"policy": "semantic_0.88", "ttl_hours": "", **r, "n": n})
    print(f"semantic: 命中 {r['hits']} 有效 {r['safe']} 误用 {r['stale']}")

    for row in rows:
        row["hit_rate_pct"] = round(100 * row["hits"] / n, 2)
        row["valid_rate_pct"] = round(100 * row["safe"] / max(1, row["hits"]), 2)
        row["stale_rate_pct"] = round(100 * row["stale"] / max(1, row["hits"]), 2)
        row["missed_safe_per_1k"] = round(1000 * row["missed_safe"] / n, 1)
    with (OUT / "m2_baselines.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    oracle_pct = 100 * oracle["possible_safe"] / n
    lines = [
        "# M2 静态基线的有效命中与过期误用（自动生成）",
        "",
        f"回放 {n} 条请求（18 小时）。安全判定使用 `labels/build.py::view_judge(view=\"truth\")`。",
        "TTL 从条目创建时刻起算，命中不刷新（避免退化成滑动 TTL）。",
        "",
        "| 基线 | TTL(h) | 命中率 | 有效命中率 | 过期误用率 | 错失安全复用/千条 |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['policy']} | {row['ttl_hours'] or '—'} | {row['hit_rate_pct']}% | "
                     f"{row['valid_rate_pct']}% | {row['stale_rate_pct']}% | {row['missed_safe_per_1k']} |")
    lines += [
        "",
        f"**Oracle 上界**：同题最近 8 个历史条目中至少存在一个安全候选的请求占 **{oracle_pct:.1f}%**"
        f"（{oracle['possible_safe']}/{n}）。",
        "",
        "## 解读",
        "",
    ]
    short = rows[0]
    long_ = rows[2]
    sem = rows[3]
    lines += [
        f"1. **TTL 两头不讨好**：短 TTL 命中率仅 {short['hit_rate_pct']}%，"
        f"每千条错失 {short['missed_safe_per_1k']} 次本可安全复用的机会；"
        f"长 TTL 把命中率拉到 {long_['hit_rate_pct']}%，但过期误用率升到 {long_['stale_rate_pct']}%。",
        f"2. **纯语义更危险**：命中率 {sem['hit_rate_pct']}%，过期误用率 {sem['stale_rate_pct']}%——"
        "只看语义相似度会系统性复用已过期或权限不符的内容。",
        f"3. **空间存在**：oracle 显示 {oracle_pct:.1f}% 的请求存在安全复用候选，"
        "说明不是\"没什么可复用\"，而是静态规则无法把安全和过期区分开。",
        "4. 这三条合起来构成\"需要按对象价值与版本证据决定生命周期\"的动机。",
    ]
    (OUT / "m2_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"已写 {OUT/'m2_baselines.csv'}、m2_summary.md；oracle 上界 {oracle_pct:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

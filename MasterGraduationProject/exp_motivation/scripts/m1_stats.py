"""M1：异质开销与重复率（动机实验第一组）。

输入（exp_motivation/data/）：
  real_calibration_300.csv   300 条真机标定的分阶段耗时与 token
  request_stream.jsonl       3,000 条请求
  act_plan_pool.json         100 act / 60 plan
  docs_versioned.jsonl       文档版本视图

输出（exp_motivation/results/）：
  m1_stage_costs.csv         分阶段耗时与占比
  m1_repetition.csv          各类重复率
  m1_summary.md              可直接引用的数字与解读
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)


def pctl(xs, p):
    if not xs:
        return float("nan")
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def read_jsonl(name):
    return [json.loads(l) for l in (DATA / name).open(encoding="utf-8") if l.strip()]


def main() -> int:
    cal = list(csv.DictReader((DATA / "real_calibration_300.csv").open(encoding="utf-8")))
    reqs = read_jsonl("request_stream.jsonl")
    pool = json.loads((DATA / "act_plan_pool.json").read_text(encoding="utf-8"))

    # ---------------------------------------------------------- 1. 开销异质
    stages = {
        "plan": [float(r["t_plan_ms"]) for r in cal],
        "rag": [float(r["t_rag_ms"]) for r in cal],
        "act": [float(r["t_act_ms"]) for r in cal],
        "resp": [float(r["t_resp_ms"]) for r in cal],
        "total": [float(r["t_total_ms"]) for r in cal],
    }
    means = {k: statistics.fmean(v) for k, v in stages.items()}
    rows = []
    for k in ("plan", "rag", "act", "resp"):
        rows.append({
            "stage": k,
            "p50_ms": round(pctl(stages[k], 0.5), 3),
            "p95_ms": round(pctl(stages[k], 0.95), 3),
            "mean_ms": round(means[k], 3),
            "min_ms": round(min(stages[k]), 3),
            "max_ms": round(max(stages[k]), 3),
            "share_of_total_pct": round(100 * means[k] / means["total"], 3),
        })
    rows.append({"stage": "total", "p50_ms": round(pctl(stages["total"], 0.5), 3),
                 "p95_ms": round(pctl(stages["total"], 0.95), 3),
                 "mean_ms": round(means["total"], 3),
                 "min_ms": round(min(stages["total"]), 3),
                 "max_ms": round(max(stages["total"]), 3),
                 "share_of_total_pct": 100.0})
    with (OUT / "m1_stage_costs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    tokens = [int(r["token_cost"]) for r in cal]

    # ---------------------------------------------------------- 2. 重复率
    # 请求 → task_id 的映射来自 request_context（request_stream 无 task_id）
    ctx_path = DATA.parent.parent / "dataset" / "events" / "request_context.jsonl"
    task_of = {}
    if ctx_path.is_file():
        for row in (json.loads(l) for l in ctx_path.open(encoding="utf-8") if l.strip()):
            task_of[row["req_id"]] = row.get("task_id")
    cluster_of = {r["req_id"]: r.get("cluster_id") for r in reqs}

    task_counts = Counter(v for v in task_of.values() if v)
    cluster_counts = Counter(v for v in cluster_of.values() if v)
    plan_counts = Counter(r.get("plan_id") for r in reqs)
    act_counts = Counter(r.get("act_key") for r in reqs)
    query_counts = Counter(r["query_text"] for r in reqs)

    # 证据复用：gold 文��集是否在更早的请求中出现过
    seen_docs: set[str] = set()
    doc_reuse_hits = 0
    exact_set_repeats = 0
    seen_sets: set[frozenset] = set()
    for r in reqs:
        ds = frozenset(r["gold_doc_ids"])
        if ds & seen_docs:
            doc_reuse_hits += 1
        if ds in seen_sets:
            exact_set_repeats += 1
        seen_sets.add(ds)
        seen_docs |= ds

    rep_rows = [
        ("请求总数", len(reqs), "条"),
        ("覆盖题目数", len(task_counts), "题"),
        ("平均每题请求数", round(len(reqs) / max(1, len(task_counts)), 2), "条/题"),
        ("同题请求占比", round(100 * sum(c for c in task_counts.values() if c > 1) / len(reqs), 2), "%"),
        ("覆盖语义簇数", len(cluster_counts), "簇"),
        ("平均每簇请求数", round(len(reqs) / max(1, len(cluster_counts)), 2), "条/簇"),
        ("plan_id 去重数", len(plan_counts), "个"),
        ("plan 复用率", round(100 * (1 - len(plan_counts) / len(reqs)), 2), "%"),
        ("act_key 去重数", len(act_counts), "个"),
        ("act 复用率", round(100 * (1 - len(act_counts) / len(reqs)), 2), "%"),
        ("问句字面重复数", sum(c - 1 for c in query_counts.values() if c > 1), "条"),
        ("证据集有交集的请求", doc_reuse_hits, f"条（{100*doc_reuse_hits/len(reqs):.1f}%）"),
        ("证据集完全相同", exact_set_repeats, f"条（{100*exact_set_repeats/len(reqs):.1f}%）"),
    ]
    with (OUT / "m1_repetition.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["指标", "数值", "单位或说明"])
        w.writerows(rep_rows)

    # ---------------------------------------------------------- 3. 摘要
    share_model = 100 * (means["plan"] + means["resp"]) / means["total"]
    share_local = 100 * (means["rag"] + means["act"]) / means["total"]
    lines = [
        "# M1 异质开销与重复率（自动生成）",
        "",
        f"样本：{len(cal)} 条标定请求、{len(reqs)} 条请求流。",
        "",
        "## 1. 四阶段开销异质",
        "",
        "| 阶段 | p50 | p95 | 均值 | 占总时长 |",
        "|---|---|---|---|---|",
    ]
    for r in rows[:-1]:
        lines.append(f"| {r['stage']} | {r['p50_ms']:.1f} ms | {r['p95_ms']:.1f} ms | "
                     f"{r['mean_ms']:.1f} ms | {r['share_of_total_pct']:.3f}% |")
    t = rows[-1]
    lines += [
        f"| **端到端** | **{t['p50_ms']:.1f} ms** | **{t['p95_ms']:.1f} ms** | "
        f"**{t['mean_ms']:.1f} ms** | 100% |",
        "",
        f"- 模型段（plan+resp）占端到端 **{share_model:.2f}%**，本地段（rag+act）仅 **{share_local:.3f}%**。",
        f"- token_cost：p50={pctl(tokens,0.5):.0f}，p95={pctl(tokens,0.95):.0f}，"
        f"均值={statistics.fmean(tokens):.0f}，合计 {sum(tokens)}。",
        "",
        "## 2. 重复率",
        "",
        "| 指标 | 数值 | 说明 |",
        "|---|---|---|",
    ]
    for name, val, unit in rep_rows:
        lines.append(f"| {name} | {val} | {unit} |")
    lines += [
        "",
        "## 3. 对动机的支撑",
        "",
        f"1. **开销高度异质**：同一套流程里 plan+resp 均值 {means['plan']+means['resp']:.0f} ms，"
        f"而 rag+act 合计 {(means['rag']+means['act']):.2f} ms，相差约 "
        f"{(means['plan']+means['resp'])/max(1e-9, means['rag']+means['act']):.0f} 倍；"
        "单一固定 TTL 无法同时对两类对象给出合理生命周期。",
        f"2. **重复显著**：{len(reqs)} 条请求只覆盖 {len(task_counts)} 道题，"
        f"plan 复用率 {100*(1-len(plan_counts)/len(reqs)):.1f}%、"
        f"act 复用率 {100*(1-len(act_counts)/len(reqs)):.1f}%，"
        f"{100*doc_reuse_hits/len(reqs):.1f}% 的请求与前序请求共享证据文档。",
        "3. 因此\"按对象区分价值、按版本判定有效性\"有数据基础；纯 TTL 会把高价值对象过早淘汰、"
        "把低价值对象留得过久。",
    ]
    (OUT / "m1_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"已写 {OUT/'m1_stage_costs.csv'}、m1_repetition.csv、m1_summary.md")
    print(f"模型段占比 {share_model:.2f}% | 本地段 {share_local:.3f}%")
    print(f"plan 复用率 {100*(1-len(plan_counts)/len(reqs)):.1f}% | "
          f"act 复用率 {100*(1-len(act_counts)/len(reqs)):.1f}% | "
          f"证据文档共享 {100*doc_reuse_hits/len(reqs):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

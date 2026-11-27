"""标定结果汇总：时延分位数、token 统计、质量标记、分段对比。

只读 dataset/embeddings/calibration/requests_progress.jsonl，不修改任何数据文件。

用法：
  python dataset/tools/calibration_report.py
  python dataset/tools/calibration_report.py --split 259   # 服务重启分界
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "embeddings" / "calibration" / "requests_progress.jsonl"


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ordered = sorted(xs)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def summarize(rows: list[dict], label: str) -> None:
    n = len(rows)
    if not n:
        print(f"\n[{label}] 无数据")
        return
    stages = {
        "plan": [r["t_plan_ms"] for r in rows],
        "rag": [r["t_rag_ms"] for r in rows],
        "act": [r["t_act_ms"] for r in rows],
        "resp": [r["t_resp_ms"] for r in rows],
        "total": [r["t_total_ms"] for r in rows],
    }
    print(f"\n[{label}] n={n}")
    print(f"  {'阶段':6s} {'p50':>10s} {'p95':>10s} {'mean':>10s} {'max':>10s}")
    for name, xs in stages.items():
        unit = "ms"
        print(f"  {name:6s} {pct(xs,0.5):10.1f} {pct(xs,0.95):10.1f} "
              f"{statistics.fmean(xs):10.1f} {max(xs):10.1f}  {unit}")
    tok = [r["token_cost"] for r in rows]
    print(f"  token_cost  p50={pct(tok,0.5):.0f}  p95={pct(tok,0.95):.0f}  "
          f"mean={statistics.fmean(tok):.0f}  sum={sum(tok)}")
    plan_tok = [r["plan"]["completion_tokens"] for r in rows]
    resp_tok = [r["resp"]["completion_tokens"] for r in rows]
    print(f"  completion  plan p50={pct(plan_tok,0.5):.0f} / resp p50={pct(resp_tok,0.5):.0f}")
    trunc = sum(1 for r in rows if r.get("resp_truncated"))
    empty = sum(1 for r in rows if not r["resp_text"].strip())
    print(f"  触顶 {trunc} 条 ({trunc/n:.1%}) | 空输出 {empty} 条 ({empty/n:.1%})")
    ends = [r["t_total_ms"] / 1000 for r in rows]
    print(f"  端到端秒: p50={pct(ends,0.5):.0f}s  p95={pct(ends,0.95):.0f}s  max={max(ends):.0f}s")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", type=int, default=0,
                    help="按落盘顺序切分，用于服务重启前后对比（例如 259）")
    args = ap.parse_args()

    rows = [json.loads(l) for l in PROGRESS.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    rows.sort(key=lambda r: r["seq"])
    summarize(rows, "全部")
    if args.split and 0 < args.split < len(rows):
        summarize(rows[:args.split], f"前 {args.split} 条（重启前）")
        summarize(rows[args.split:], f"后 {len(rows)-args.split} 条（重启后）")

    # 慢请求 Top5 归因线索
    slow = sorted(rows, key=lambda r: -r["t_total_ms"])[:5]
    print("\n最慢 5 条：")
    for r in slow:
        print(f"  {r['req_id']}  total={r['t_total_ms']/1000:.0f}s  "
              f"plan={r['t_plan_ms']/1000:.0f}s resp={r['t_resp_ms']/1000:.0f}s  "
              f"resp_tok={r['resp']['completion_tokens']}  "
              f"trunc={r.get('resp_truncated')}  "
              f"answer_len={len(r['resp_text'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

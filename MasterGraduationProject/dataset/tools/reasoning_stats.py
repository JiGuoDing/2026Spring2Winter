"""思考量统计：从标定进度文件里汇总 reasoning / content 的字符与 token 分布。

用途：主批次（旧采集代码）没有 reasoning 字段；补跑 20 条后会生成带字段的进度文件，
用本脚本得到"思考占 resp 的比例"，作为论文里的辅助证据。

用法：
  python dataset/tools/reasoning_stats.py
  python dataset/tools/reasoning_stats.py --progress dataset/embeddings/calibration/requests_progress_supp.jsonl
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "embeddings" / "calibration" / "requests_progress.jsonl"


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ordered = sorted(xs)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--progress", default=str(DEFAULT))
    args = ap.parse_args()

    rows = [json.loads(l) for l in Path(args.progress).read_text(encoding="utf-8").splitlines()
            if l.strip()]
    rows = [r for r in rows if "resp_reasoning_chars" in r]
    if not rows:
        print("该文件没有 reasoning 字段（可能是旧采集代码产出）")
        return 1

    rc = [r["resp_reasoning_chars"] for r in rows]
    cc = [r.get("resp_content_chars", 0) for r in rows]
    resp_s = [r["t_resp_ms"] / 1000 for r in rows]
    comp = [r["resp"]["completion_tokens"] for r in rows]
    # 思考 token 估算：按字符占比折算 completion_tokens
    est = [c * a / max(1, a + b) for a, b, c in zip(rc, cc, comp)]
    share = [a / max(1, a + b) for a, b in zip(rc, cc)]

    print(f"样本 {len(rows)} 条")
    print(f"思考字符数   p50={statistics.median(rc):.0f}  p95={pct(rc, 0.95):.0f}  "
          f"max={max(rc)}")
    print(f"正文字符数   p50={statistics.median(cc):.0f}  p95={pct(cc, 0.95):.0f}")
    print(f"思考占比     p50={statistics.median(share):.0%}  p95={pct(share, 0.95):.0%}")
    print(f"思考 token 估算 p50={statistics.median(est):.0f}  "
          f"均值={statistics.fmean(est):.0f}  max={max(est):.0f}")
    print(f"resp 总时长  p50={statistics.median(resp_s):.0f}s  p95={pct(resp_s, 0.95):.0f}s")

    # 思考占比与耗时的相关性（Spearman 秩相关）
    def rank(xs: list[float]) -> list[float]:
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        for pos, i in enumerate(order):
            r[i] = pos
        return r

    rx, ry = rank(rc), rank(resp_s)
    n = len(rx)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    print(f"思考字数 vs resp 时长  Spearman ρ = {num / den:.3f}（n={n}）")
    print("\n说明：思考 token 是按字符占比折算的估算值；服务端未单独返回 reasoning_tokens。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

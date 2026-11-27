"""工具/RAG 成本敏感性：单次调用 → 多次调用 × 失败重试 × 场景延迟。

读 dataset/costs/tool_cost_model.json（assumed 参数已标注），输出各画像下的
工具段占比与"缓存工具结果可省多少"。

用法：python exp_motivation/scripts/tool_cost_sensitivity.py
输出：exp_motivation/results/m3_tool_cost_sensitivity.csv + 控制台表
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
MODEL = PROJ / "dataset" / "costs" / "tool_cost_model.json"
OUT = PROJ / "exp_motivation" / "results"
OUT.mkdir(parents=True, exist_ok=True)


def attempts(p_fail: float, max_retries: int) -> float:
    """首次 + 最多 max_retries 次重试的期望尝试次数。"""
    total = 0.0
    for k in range(max_retries + 1):
        total += p_fail ** k
    return total


def main() -> int:
    cfg = json.loads(MODEL.read_text(encoding="utf-8"))
    calls = cfg["calls"]
    rag_n = calls["rag_calls_per_request"]
    act_n = calls["act_calls_per_request_total"]
    max_retries = cfg["failure"]["max_retries"]

    rows = []
    for prof in cfg["profiles"]:
        a = attempts(prof["p_fail"], max_retries)
        rag_ms = rag_n * prof["rag_ms_per_call"] * a
        act_ms = act_n * prof["act_ms_per_call"] * a
        tool_ms = rag_ms + act_ms
        model_ms = prof["model_ms"]
        total = model_ms + tool_ms
        rows.append({
            "profile": prof["id"],
            "label": prof["label"],
            "measured": prof["measured"],
            "model_s": round(model_ms / 1000, 3),
            "rag_calls": rag_n,
            "act_calls": act_n,
            "attempts": round(a, 4),
            "rag_s": round(rag_ms / 1000, 4),
            "act_s": round(act_ms / 1000, 4),
            "tool_s": round(tool_ms / 1000, 4),
            "total_s": round(total / 1000, 3),
            "tool_share_pct": round(100 * tool_ms / total, 3),
            "save_if_tool_cached_s": round(tool_ms / 1000, 4),
        })

    with (OUT / "m3_tool_cost_sensitivity.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"{'画像':26s} {'模型':>9s} {'工具':>10s} {'工具占比':>9s} {'缓存工具可省':>12s}")
    for r in rows:
        print(f"{r['profile']:26s} {r['model_s']:>8.2f}s {r['tool_s']:>9.3f}s "
              f"{r['tool_share_pct']:>8.3f}% {r['save_if_tool_cached_s']:>11.3f}s")

    # 单次调用 vs 多次×重试 的放大倍数（P4 最直观）
    p4 = next(r for r in rows if r["profile"].startswith("P4"))
    single = p4["rag_s"] + p4["act_s"]
    print(f"\nP4 已经含 {p4['act_calls']} 次 act 调用与 {p4['attempts']} 次期望尝试；"
          f"若按旧的'1 次成功调用'口径，工具段只有 {single/p4['attempts']:.3f}s，"
          f"低估 {p4['attempts']:.2f} 倍（未含调用次数放大）。")
    print(f"若只算 1 次 rag + 1 次 act 且无重试：P4 工具段 = "
          f"{(p4['rag_s']+p4['act_s'])/p4['act_calls']/p4['attempts']:.3f}s，"
          f"占端到端 {100*((p4['rag_s']+p4['act_s'])/p4['act_calls']/p4['attempts'])/((p4['rag_s']+p4['act_s'])/p4['act_calls']/p4['attempts']+p4['model_s']):.2f}%")
    print(f"\n已写 {OUT/'m3_tool_cost_sensitivity.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

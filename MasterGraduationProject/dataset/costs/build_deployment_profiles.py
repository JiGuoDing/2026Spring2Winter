"""生成统一多部署画像契约表 dataset/costs/deployment_profiles.json（v0.5.0）。

严格分离 measured（真机实测）与 assumed（远程网络/数仓假设），
自动汇总 real_calibration_300.csv、rag_rerank_costs.csv、act_toolchain_costs.csv 与 tool_cost_model.json。
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

OUT_PATH = ROOT / "costs" / "deployment_profiles.json"


def _read_csv_map(path: Path, key_col: str) -> dict[str, dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return {row[key_col]: row for row in csv.DictReader(f)}


def main() -> int:
    with (ROOT / "events" / "real_calibration_300.csv").open("r", encoding="utf-8", newline="") as f:
        cal_rows = list(csv.DictReader(f))
    slow_plan_mean = round(statistics.fmean(float(r["t_plan_ms"]) for r in cal_rows), 2)
    slow_resp_mean = round(statistics.fmean(float(r["t_resp_ms"]) for r in cal_rows), 2)
    slow_rag_old_mean = round(statistics.fmean(float(r["t_rag_ms"]) for r in cal_rows), 2)
    slow_act_old_mean = round(statistics.fmean(float(r["t_act_ms"]) for r in cal_rows), 2)
    slow_model_mean = round(slow_plan_mean + slow_resp_mean, 2)

    rag_map = _read_csv_map(ROOT / "costs" / "rag_rerank_costs.csv", "stage")
    modern_rag_p50 = round(float(rag_map["e2e_rag"]["p50_ms"]), 2)
    modern_rag_mean = round(float(rag_map["e2e_rag"]["mean_ms"]), 2)

    with (ROOT / "costs" / "act_toolchain_costs.csv").open("r", encoding="utf-8", newline="") as f:
        act_rows = [r for r in csv.DictReader(f) if r["difficulty"] == "all" and r["stage"] == "e2e_toolchain"]
    local_act_tc_p50 = round(float(act_rows[0]["p50_ms"]), 2)
    local_act_tc_mean = round(float(act_rows[0]["mean_ms"]), 2)

    with (ROOT / "costs" / "act_prod_costs.csv").open("r", encoding="utf-8", newline="") as f:
        prod_act_rows = [
            r for r in csv.DictReader(f)
            if int(r["concurrency"]) == 8 and r["difficulty"] == "all" and r["stage"] == "e2e_client"
        ]
    prod_act_c8_p50 = round(float(prod_act_rows[0]["p50_ms"]), 2)
    prod_act_c8_p95 = round(float(prod_act_rows[0]["p95_ms"]), 2)
    prod_act_c8_mean = round(float(prod_act_rows[0]["mean_ms"]), 2)

    # 若已有 fast_calibration_50.csv，则自动标为 measured；否则标 assumed
    fast_csv = ROOT / "events" / "fast_calibration_50.csv"
    if fast_csv.is_file():
        with fast_csv.open("r", encoding="utf-8", newline="") as f:
            frows = list(csv.DictReader(f))
        fast_model_stage = {
            "status": "measured",
            "n": len(frows),
            "plan_mean_ms": round(statistics.fmean(float(r["t_plan_ms"]) for r in frows), 2),
            "resp_mean_ms": round(statistics.fmean(float(r["t_resp_ms"]) for r in frows), 2),
            "total_mean_ms": round(statistics.fmean(float(r["t_model_total_ms"]) for r in frows), 2),
            "source": "events/fast_calibration_50.csv",
        }
    else:
        fast_model_stage = {
            "status": "assumed",
            "plan_mean_ms": 1200.0,
            "resp_mean_ms": 2800.0,
            "total_mean_ms": 4000.0,
            "source": "costs/tool_cost_model.json (待 run_fast_model_calibration.py --write-back 替换为 50 条实测)",
        }

    # 计算各画像端到端占比（仅作参考汇总）
    def summarize(model_ms: float, rag_ms: float, act_ms: float) -> dict:
        tot = model_ms + rag_ms + act_ms
        return {
            "e2e_mean_ms": round(tot, 2),
            "model_share_pct": round(100.0 * model_ms / tot, 3),
            "rag_share_pct": round(100.0 * rag_ms / tot, 3),
            "act_share_pct": round(100.0 * act_ms / tot, 3),
        }

    # P4 数仓/长排队：跨区企业数仓 ~2000 ms × 1.11 期望重试(p_fail=0.10) + 探查 ≈ 4500 ms (assumed)
    p4_act_ms = 4500.0

    prod_act_stage = {
        "status": "measured",
        "mode": "http_readonly_gateway_4.4m_rows_c8_bi_probes",
        "concurrency": 8,
        "pool_size": 4,
        "p50_ms": prod_act_c8_p50,
        "p95_ms": prod_act_c8_p95,
        "mean_ms": prod_act_c8_mean,
        "local_49k_baseline_mean_ms": local_act_tc_mean,
        "source": "costs/act_prod_costs.csv",
    }

    profiles = [
        {
            "id": "P1_slow_local_base",
            "label": "P1 慢思考模型 + 基础本地检索/单次SQLite（全实测基线）",
            "model_stage": {
                "status": "measured",
                "model": "qwen3.8-27b (xhigh)",
                "n": len(cal_rows),
                "plan_mean_ms": slow_plan_mean,
                "resp_mean_ms": slow_resp_mean,
                "total_mean_ms": slow_model_mean,
                "source": "events/real_calibration_300.csv",
            },
            "rag_stage": {
                "status": "measured",
                "mode": "bm25_doc_only",
                "mean_ms": slow_rag_old_mean,
                "source": "events/real_calibration_300.csv",
            },
            "act_stage": {
                "status": "measured",
                "mode": "single_sqlite",
                "mean_ms": slow_act_old_mean,
                "source": "events/real_calibration_300.csv",
            },
            "summary": summarize(slow_model_mean, slow_rag_old_mean, slow_act_old_mean),
        },
        {
            "id": "P2_slow_modern_rag_prod_act",
            "label": "P2 慢思考模型 + 现代六阶段重排RAG + 百万行网关act(c=8)（全实测）",
            "model_stage": {
                "status": "measured",
                "model": "qwen3.8-27b (xhigh)",
                "n": len(cal_rows),
                "plan_mean_ms": slow_plan_mean,
                "resp_mean_ms": slow_resp_mean,
                "total_mean_ms": slow_model_mean,
                "source": "events/real_calibration_300.csv",
            },
            "rag_stage": {
                "status": "measured",
                "mode": "hybrid_rrf_rerank_dynamic (bge-reranker-v2-m3 INT8 ONNX)",
                "p50_ms": modern_rag_p50,
                "mean_ms": modern_rag_mean,
                "source": "costs/rag_rerank_costs.csv",
            },
            "act_stage": prod_act_stage,
            "summary": summarize(slow_model_mean, modern_rag_mean, prod_act_c8_mean),
        },
        {
            "id": "P3_fast_modern_rag_prod_act",
            "label": "P3 快模型 + 现代六阶段重排RAG（实测） + 百万行网关act(c=8，实测)",
            "model_stage": fast_model_stage,
            "rag_stage": {
                "status": "measured",
                "mode": "hybrid_rrf_rerank_dynamic (bge-reranker-v2-m3 INT8 ONNX)",
                "p50_ms": modern_rag_p50,
                "mean_ms": modern_rag_mean,
                "source": "costs/rag_rerank_costs.csv",
            },
            "act_stage": prod_act_stage,
            "summary": summarize(fast_model_stage["total_mean_ms"], modern_rag_mean, prod_act_c8_mean),
        },
        {
            "id": "P4_fast_modern_rag_warehouse",
            "label": "P4 快模型 + 现代六阶段重排RAG（实测） + 跨区企业数仓/长排队（假设）",
            "model_stage": fast_model_stage,
            "rag_stage": {
                "status": "measured",
                "mode": "hybrid_rrf_rerank_dynamic (bge-reranker-v2-m3 INT8 ONNX)",
                "p50_ms": modern_rag_p50,
                "mean_ms": modern_rag_mean,
                "source": "costs/rag_rerank_costs.csv",
            },
            "act_stage": {
                "status": "assumed",
                "mode": "enterprise_warehouse_with_retries",
                "mean_ms": p4_act_ms,
                "p_fail": 0.10,
                "retry_sidecar": "events/tool_failures.jsonl (P4_fast_model_warehouse)",
                "source": "costs/tool_cost_model.json",
            },
            "summary": summarize(fast_model_stage["total_mean_ms"], modern_rag_mean, p4_act_ms),
        },
    ]

    doc = {
        "schema_version": 2,
        "dataset_version": "0.6.0",
        "rule": "每个分量独立标注 measured / assumed，论文引用时严禁混淆。",
        "profiles": profiles,
    }
    io.write_json(OUT_PATH, doc)
    print(f"已写 {OUT_PATH}：")
    for p in profiles:
        s = p["summary"]
        print(
            f"  {p['id']:28s} | e2e={s['e2e_mean_ms']:9.1f} ms | "
            f"model={s['model_share_pct']:6.2f}% | rag={s['rag_share_pct']:5.2f}% | act={s['act_share_pct']:5.2f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

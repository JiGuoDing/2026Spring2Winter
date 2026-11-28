"""60 条人工复核一致性与 Cohen's Kappa 评分脚本（v0.4.0）。

读取 dataset/labels/to_review.csv，在作者补充 `human_safe` 列（true/false）后，
计算规则谓词（predicate_safe / predicate_safe_system）与人工标注的一致率及 Cohen's κ，
并导出 dataset/labels/human_review_report.json 供论文 §1.4.1 引用。

用法：
  python dataset/tools/score_human_review.py --check-template
  python dataset/tools/score_human_review.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

REVIEW_CSV = ROOT / "labels" / "to_review.csv"
REPORT_JSON = ROOT / "labels" / "human_review_report.json"


def _parse_bool(val: str) -> bool | None:
    s = (val or "").strip().lower()
    if s in ("true", "1", "yes", "y", "safe"):
        return True
    if s in ("false", "0", "no", "n", "unsafe"):
        return False
    return None


def _kappa(pairs: list[tuple[bool, bool]]) -> dict:
    n = len(pairs)
    tp = sum(1 for a, b in pairs if a and b)
    tn = sum(1 for a, b in pairs if not a and not b)
    fp = sum(1 for a, b in pairs if a and not b)
    fn = sum(1 for a, b in pairs if not a and b)
    po = (tp + tn) / n if n else 0.0
    p_a_pos = (tp + fp) / n if n else 0.0
    p_b_pos = (tp + fn) / n if n else 0.0
    pe = p_a_pos * p_b_pos + (1.0 - p_a_pos) * (1.0 - p_b_pos)
    kappa = (po - pe) / (1.0 - pe) if abs(1.0 - pe) > 1e-12 else 1.0
    return {
        "n": n,
        "agreement_pct": round(100.0 * po, 2),
        "cohens_kappa": round(kappa, 4),
        "confusion": {"both_true": tp, "both_false": tn, "pred_true_human_false": fp, "pred_false_human_true": fn},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-template", action="store_true", help="仅校验 to_review.csv 模板可读性")
    args = ap.parse_args()

    assert REVIEW_CSV.is_file(), f"缺复核清单 {REVIEW_CSV}"
    with REVIEW_CSV.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 60, f"复核样本仅 {len(rows)} 行，应 >= 60"

    if args.check_template:
        has_col = "human_safe" in (rows[0].keys() if rows else ())
        filled = sum(1 for r in rows if _parse_bool(r.get("human_safe", "")) is not None)
        print(f"[check-template] {REVIEW_CSV.name} 合法（{len(rows)} 行），human_safe 列存在={has_col}，已填={filled}/{len(rows)}")
        return 0

    truth_pairs: list[tuple[bool, bool]] = []
    sys_pairs: list[tuple[bool, bool]] = []
    for r in rows:
        hv = _parse_bool(r.get("human_safe", ""))
        if hv is None:
            continue
        pv_t = _parse_bool(r["predicate_safe"])
        pv_s = _parse_bool(r["predicate_safe_system"])
        assert pv_t is not None and pv_s is not None
        truth_pairs.append((pv_t, hv))
        sys_pairs.append((pv_s, hv))

    if not truth_pairs:
        print("尚未在 labels/to_review.csv 中填入 human_safe 列（true/false），无法计算一致率与 κ。")
        return 1

    report = {
        "source": "labels/to_review.csv",
        "total_rows": len(rows),
        "annotated_rows": len(truth_pairs),
        "vs_predicate_safe_truth": _kappa(truth_pairs),
        "vs_predicate_safe_system": _kappa(sys_pairs),
    }
    io.write_json(REPORT_JSON, report)
    print(f"已写 {REPORT_JSON}：truth 一致率={report['vs_predicate_safe_truth']['agreement_pct']}% κ={report['vs_predicate_safe_truth']['cohens_kappa']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

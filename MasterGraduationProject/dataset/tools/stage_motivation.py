"""把数据集投影到动机实验的目录约定（exp_motivation/data/）。

动机实验文档要求 5 个固定文件名。本脚本只做复制与校验，不修改内容；
模型相关列为空时给出显式警告，避免把模板误当实测数据使用。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

DST = ROOT.parent / "exp_motivation" / "data"

MAP = {
    "docs_versioned.jsonl": "events/docs_versioned.jsonl",
    "request_stream.jsonl": "events/request_stream.jsonl",
    "update_events.jsonl": "events/update_events.jsonl",
    "act_plan_pool.json": "events/act_plan_pool.json",
    "real_calibration_300.csv": "events/real_calibration_300.csv",
}


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    for dst_name, src_rel in MAP.items():
        src = ROOT / src_rel
        assert src.is_file(), f"缺源文件 {src_rel}"
        shutil.copy2(src, DST / dst_name)
        print(f"copied {src_rel} -> {DST / dst_name}")

    cal = DST / "real_calibration_300.csv"
    lines = cal.read_text(encoding="utf-8").splitlines()
    head = lines[0].split(",")
    empty_cols = []
    for i, col in enumerate(head):
        if col == "req_id":
            continue
        vals = [ln.split(",")[i].strip() for ln in lines[1:] if ln.count(",") >= len(head) - 1]
        if not any(v not in ("", "NA") for v in vals):
            empty_cols.append(col)
    if empty_cols:
        print("\n[警告] 以下列全为空，必须先回填再跑动机实验：", empty_cols)
        print("      这些是模型相关耗时/费用，本系统不代造；回填方式见 events/CALIBRATION.md")

    note = DST / "README_GENERATED.md"
    note.write_text(
        "# 由 dataset/tools/stage_motivation.py 生成\n\n"
        "本目录的 5 个文件来自 `dataset/events/`，字段与 `动机实验_gemini_v1.md` 第 2 节一致。\n"
        "`real_calibration_300.csv` 为 v0.3.0 的 300 条真机标定结果（七列全部实测）。\n"
        "重新生成：`python dataset/tools/stage_motivation.py`。\n",
        encoding="utf-8", newline="\n")
    print(f"\n完成：{DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

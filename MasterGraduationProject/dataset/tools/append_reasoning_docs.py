"""把 20 条思考量补跑的结论写入 PAPER_MAP 与 DATASET_CARD。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

pm = ROOT / "PAPER_MAP.md"
t = pm.read_text(encoding="utf-8")
add = """
### 思考量（20 条补跑，辅助证据）

| 指标 | p50 | p95 | max |
|---|---|---|---|
| 思考字符数 | 3,291 | 11,904 | 17,088 |
| 正文字符数 | 448 | 1,222 | — |
| 思考 token 估算 | 1,859 | — | 8,986 |
| 思考占 completion 比例 | **87%** | 92% | — |

- 思考字数与 resp 时长的 **Spearman ρ = 0.988**（n=20）：resp 时延的方差几乎完全由思考长度解释。
- 含义：缓存命中跳过整段生成，省掉的主要是思考时间；`ΔT` 的模型段收益应按「跳过整段 resp」计，
  不能只按输出正文长度估。数据见 `embeddings/calibration/requests_progress_supp.jsonl`，
  配置与主批次一致。
"""
assert "思考量（20 条补跑" not in t
pm.write_text(t.rstrip() + "\n\n" + add, encoding="utf-8", newline="\n")

dc = ROOT / "DATASET_CARD.md"
t2 = dc.read_text(encoding="utf-8")
add2 = """
### v0.3.0 补充：思考量（20 条，辅助口径）

- 思考占 completion token 的 **p50 87% / p95 92%**；思考字数与 resp 时长 Spearman ρ=0.988。
- 这 20 条用独立进度文件（`requests_progress_supp.jsonl`）测量，不计入 300 条主标定。
- 主标定的 300 条记录**没有** reasoning 字段（采集代码在跑批中途才修好），所以思考占比只有这 20 条样本；
  主标定的 token 与时长数据仍然完整（`completion_tokens` 已包含思考 token）。
"""
assert "v0.3.0 补充：思考量" not in t2
dc.write_text(t2.rstrip() + "\n" + add2, encoding="utf-8", newline="\n")
print("已写入 PAPER_MAP 与 DATASET_CARD")

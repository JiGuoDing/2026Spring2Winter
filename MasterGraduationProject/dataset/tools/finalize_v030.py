"""把标定结果写回数据集文档，升版 v0.3.0。

只做文本替换与版本号更新；每处替换都断言命中，避免静默漏改。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT


def sub(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{path.name}: 未找到待替换文本：{old[:60]!r}"
    path.write_text(text.replace(old, new, count), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- params.json
pp = D / "config" / "params.json"
params = json.loads(pp.read_text(encoding="utf-8"))
params["dataset_version"] = "0.3.0"
params["calibration"] = {
    "requests": 300,
    "status": "measured",
    "config": {
        "max_tokens": 32768,
        "context_window": 65536,
        "reasoning_effort": "xhigh",
        "temperature": 0.0,
        "timeout_s": 2700,
        "max_retries": 2,
        "act_source": "template",
    },
    "model": {"slot": "local-qwen3-8-27b", "served_model": "qwen3.8-27b",
              "deployment": "single GPU, serial"},
    "measured_at": "2026-11-26",
    "n_requests": 300,
    "n_branch_pairs": 30,
    "resp_truncated": 0,
    "empty_outputs": 0,
    "service_restart_at_request": 259,
}
pp.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n",
              encoding="utf-8", newline="\n")

# ---------------------------------------------------------------- CHANGELOG
cl = D / "contracts" / "CHANGELOG.md"
entry = """## 2026-11-26 · v0.3.0

**变更**：模型阶段成本实测回填，数据集由"模板 + pending"升级为"300 条真机标定"。

- `config/params.json`：`dataset_version=0.3.0`；`calibration` 块记录标定配置
  （max_tokens 32768 / 上下文 65536 / reasoning_effort=xhigh / temperature 0）、
  服务端型号 `qwen3.8-27b`、300 条请求 + 30 对分支、触顶 0 / 空输出 0、服务重启分界 259。
- `costs/path_costs.csv`：`partial_repair/rewrite`（plan p50=49,705.9 ms）与
  `full_regen/generate`（resp p50=98,627.4 ms）两行由 `mock=pending` 改为 `measured=backfill`，n=300。
  `api-large-placeholder` 两行仍为 `mock=pending`（未部署大模型）。
- `labels/branch_pairs.jsonl`：30 对回填 `t_model_full_ms` / `t_model_cache_ms`；
  full p50=160,337.7 ms，cache p50=86,715.7 ms。
- 模型列改名：`local-small-7b` → `local-qwen3-8-27b`（实际部署 27B 单卡，旧名误标参数量）。
  `tools/run_model_calibration.py` 的 `MODEL_ALIASES`、`default_alias` 与
  `tools/run_calibration_from_env.py` 的 `ALIASES` 同步更新。

**口径**：串行、单请求、`temperature=0`、启用思考（服务端默认，`reasoning_effort=xhigh`），
**无截断**（0/300 触顶），因此时延含完整生成。测量跨一次服务重启（第 260 条起），重启后已预热，
分位数按全 300 条与前 259 条两套给出，差异见 `DATASET_CARD.md`。

**未做**：模型段并发口径（1/8/32）仍未测；`api-large-placeholder` 未回填；act 级缓存收益未单独测。

"""
text = cl.read_text(encoding="utf-8")
assert "## 2026-11-25 · v0.2.0" in text
cl.write_text(text.replace("## 2026-11-25 · v0.2.0", entry + "## 2026-11-25 · v0.2.0", 1),
              encoding="utf-8", newline="\n")

# ---------------------------------------------------------------- DATASET_CARD
dc = D / "DATASET_CARD.md"
sub(dc,
    "| 成本剖面 | 6 路径 + 3 对照阶段，222 行（218 实测 / 4 待回填） | 本地阶段实测，模型阶段 `mock=pending` |",
    "| 成本剖面 | 6 路径 + 3 对照阶段，222 行（220 实测 / 2 待回填） | "
    "本地阶段实测 + 模型阶段 300 条真机标定；仅 `api-large-placeholder` 2 行 pending |")
sub(dc,
    "| 成本表模型阶段 | 0（留空） | 待作者用自有模型回填，标 `mock=pending` |",
    "| 成本表模型阶段 | 2（本地档案） | 300 条标定回填：plan p50=49.7 s / resp p50=98.6 s |")
sub(dc,
    "5. **模型耗时缺失**：生成与改写阶段无实测，`ΔT` 目前只有本地分量；标定脚本已就绪但缺 API Key。",
    "5. **模型耗时只有单一部署**：生成与改写阶段已在 `qwen3.8-27b`（单卡、串行、无截断）上标定，"
    "但无第二模型、无并发档位；`ΔT` 的模型分量只代表该部署。")

# ---------------------------------------------------------------- HANDBOOK
hb = D / "HANDBOOK.md"
sub(hb,
    "- **模型阶段**（`partial_repair/rewrite`、`full_regen/generate`）4 行 `mock=pending`、`value_ms` 为空，必须作者回填。",
    "- **模型阶段**（`partial_repair/rewrite`、`full_regen/generate`）：本地档案 2 行已实测回填"
    "（plan p50=49,705.9 ms；resp p50=98,627.4 ms，n=300）；`api-large-placeholder` 2 行仍 `mock=pending`。")
sub(hb,
    "- `events/real_calibration_300.template.csv`：`req_id,t_plan_ms,t_rag_ms,t_act_ms,t_resp_ms,t_total_ms,token_cost`，仅第 4 列有值。",
    "- `events/real_calibration_300.csv`：300 行七列全部实测（`real_calibration_300.template.csv` 为空白模板）。")
sub(hb,
    "| 模型生成/改写耗时、`token_cost` | **待回填**，标 `mock=pending` |",
    "| 模型生成/改写耗时、`token_cost` | 已实测（300 条，qwen3.8-27b 单卡串行）；大模型档案仍 pending |")

# ---------------------------------------------------------------- PAPER_MAP
pm = D / "PAPER_MAP.md"
text = pm.read_text(encoding="utf-8")
anchor = "## "
sect = """## 五、v0.3.0 标定结果（可直接引用）

采样：300 条请求，`qwen3.8-27b` 单卡、串行、`temperature=0`、`max_tokens=32768`、
上下文 65536、`reasoning_effort=xhigh`；**触顶 0 条、空输出 0 条**（时延含完整生成）。

| 阶段 | p50 | p95 | 均值 | 最大 |
|---|---|---|---|---|
| plan | 49.7 s | 86.5 s | 51.8 s | 125.5 s |
| rag | 6.2 ms | 11.3 ms | 6.4 ms | 39.9 ms |
| act | 1.1 ms | 2.0 ms | 1.4 ms | 15.8 ms |
| resp | 98.6 s | 443.2 s | 147.1 s | 798.0 s |
| **端到端** | **154.3 s** | **505.0 s** | 198.9 s | 842.2 s |

- token：plan 平均 completion 744.7、resp 平均 2,111.4；`token_cost` p50=3,686，全量合计 1,302,090。
- 分支 30 对：完整路径 p50=160.3 s，缓存路径 p50=86.7 s（**省 46%**，模型段）。
- MAPE（仅本地可建模段）：act 5.9%，rag 76.9%，本地段合计 64.4%。
  **rag 的建模基线 p50=1.42 ms 明显低估实测 6.16 ms，1.4.1 若报 MAPE 需说明只覆盖本地段。**
- 服务在第 259 条后重启过一次；重启后 41 条已预热，分位数两套：全 300 条端到端 p95=505.0 s，
  前 259 条 p95=540.0 s，差异不影响结论。

"""
assert "## 五、" not in text
pm.write_text(text.rstrip() + "\n\n" + sect, encoding="utf-8", newline="\n")

print("文档更新完成：params / CHANGELOG / DATASET_CARD / HANDBOOK / PAPER_MAP")

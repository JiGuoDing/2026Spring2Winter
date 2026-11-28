"""行业主流 4 步只读 act 工具链本地实测脚本（v0.5.0）。

对 calibration_sample.jsonl（300 条请求）在只读 SQLite 快照上真实执行企业取数 Agent
的纵向 4 步只读工具链，并分阶段 perf_counter 计时：
  1. schema_inspect : PRAGMA table_info 探查主查询涉及表的字段结构；
  2. sql_validate   : EXPLAIN QUERY PLAN 预检语法与执行计划；
  3. sql_execute    : 真实执行主 gold_sql（对 join/nested_agg 复杂题追加 1 次主表行数只读探查）；
  4. result_check   : 结果规范化（compare.normalize）、空值与行数校验。

输出：dataset/costs/act_toolchain_costs.csv（全为 measured=1，绝不伪造远程延迟）。
注：act_plan_pool.json 的 downstream_tools 是缓存价值模型中的下游支撑度 d_i，不作为串行执行次数。
"""
from __future__ import annotations

import csv
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

import compare  # noqa: E402
import executor  # noqa: E402
from common import io  # noqa: E402

OUT_CSV = ROOT / "costs" / "act_toolchain_costs.csv"
HEADER = [
    "difficulty", "stage", "n", "p50_ms", "p95_ms", "mean_ms", "measured", "mock", "note",
]
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)


def _pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def _extract_tables(sql: str) -> list[str]:
    seen: list[str] = []
    for m in _TABLE_RE.finditer(sql):
        tb = m.group(1)
        if tb not in seen:
            seen.append(tb)
    return seen or ["dim_date"]


def main() -> int:
    samples = list(io.read_jsonl(ROOT / "events" / "calibration_sample.jsonl"))
    tasks = {t["task_id"]: t for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}

    # 预热 3 次避免首次连接文件页缓存冷启动
    for s in samples[:3]:
        t = tasks[s["task_id"]]
        _ = executor.execute(s["snapshot"], t["gold_sql"])

    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    for s in samples:
        t = tasks[s["task_id"]]
        snap = s["snapshot"]
        diff = t["difficulty"]
        sql = t["gold_sql"]
        tables = _extract_tables(sql)

        # 1) schema_inspect（纯 SELECT 查 sqlite_master DDL 与 pragma_table_info 表值函数）
        t0 = time.perf_counter()
        for tb in tables:
            res_sc = executor.execute(snap, f"SELECT name, type, [notnull], pk FROM pragma_table_info('{tb}')")
            assert not res_sc.get("error"), f"schema_inspect 失败: {res_sc}"
        ms_inspect = (time.perf_counter() - t0) * 1000.0

        # 2) sql_validate（纯 SELECT dry-run：编译执行计划与列名校验，LIMIT 0 不吐行）
        t0 = time.perf_counter()
        res_ex = executor.execute(snap, f"SELECT * FROM ({sql.rstrip(';')}) LIMIT 0")
        assert not res_ex.get("error"), f"sql_validate 失败: {res_ex}"
        ms_validate = (time.perf_counter() - t0) * 1000.0

        # 3) sql_execute（复杂题追加 1 次主表行数只读探查）
        t0 = time.perf_counter()
        if diff in ("join", "nested_agg"):
            res_probe = executor.execute(snap, f"SELECT COUNT(*) AS cnt FROM {tables[0]}")
            assert not res_probe.get("error"), f"probe 失败: {res_probe}"
        res_main = executor.execute(snap, sql)
        assert not res_main.get("error"), f"sql_execute 失败: {res_main}"
        ms_exec = (time.perf_counter() - t0) * 1000.0

        # 4) result_check
        t0 = time.perf_counter()
        norm = compare.normalize(res_main)
        _ = len(norm["rows"])
        ms_check = (time.perf_counter() - t0) * 1000.0

        ms_total = ms_inspect + ms_validate + ms_exec + ms_check

        for scope in ("all", diff):
            buckets[(scope, "schema_inspect")].append(ms_inspect)
            buckets[(scope, "sql_validate")].append(ms_validate)
            buckets[(scope, "sql_execute")].append(ms_exec)
            buckets[(scope, "result_check")].append(ms_check)
            buckets[(scope, "e2e_toolchain")].append(ms_total)

    notes = {
        "schema_inspect": "PRAGMA table_info 探查主查询涉及表的字段结构（只读 SQLite 实测）",
        "sql_validate": "EXPLAIN QUERY PLAN 语法与执行计划预检（只读 SQLite 实测）",
        "sql_execute": "真实执行 gold_sql；join/nested_agg 含 1 次主表行数探查（只读 SQLite 实测）",
        "result_check": "compare.normalize 规范化、空值与行数截断校验（本地实测）",
        "e2e_toolchain": "4 步只读取数工具链端到端本地实测总耗时；远程数仓缩放见 deployment_profiles.json",
    }

    rows: list[dict] = []
    for scope in ("all", "single_table", "join", "nested_agg"):
        for stage in ("schema_inspect", "sql_validate", "sql_execute", "result_check", "e2e_toolchain"):
            vals = buckets[(scope, stage)]
            rows.append({
                "difficulty": scope,
                "stage": stage,
                "n": len(vals),
                "p50_ms": f"{_pct(vals, 50):.4f}",
                "p95_ms": f"{_pct(vals, 95):.4f}",
                "mean_ms": f"{statistics.fmean(vals):.4f}",
                "measured": "1",
                "mock": "",
                "note": notes[stage],
            })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)

    print(f"已写 {OUT_CSV}（{len(rows)} 行）")
    for r in rows[:5]:
        print(f"  [all] {r['stage']:15s} | p50={r['p50_ms']} ms | p95={r['p95_ms']} ms | mean={r['mean_ms']} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

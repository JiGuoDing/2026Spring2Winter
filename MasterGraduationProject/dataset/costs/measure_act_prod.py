"""真实 HTTP/JSON 只读工具网关多并发压测脚本（v0.6.0）。

在单进程内启动 dataset/costs/act_tool_server.py（绑定 127.0.0.1 随机端口，连接 150 万行
prod_scale.sqlite，有界连接池 pool_size=4），对 calibration_sample.jsonl（300 条请求）
依次执行 c=1、c=8、c=16 三档并发压测（全程零 sleep，100% 真机测量）。

输出：
  - dataset/costs/act_prod_costs.csv（concurrency × difficulty × stage 的 p50/p95/mean，measured=1）
  - dataset/embeddings/calibration/act_prod_300.jsonl（c=1 与 c=8 逐请求实测明细）
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "costs"))

import act_tool_server  # noqa: E402
from common import io  # noqa: E402

SCALE_DB = ROOT / "db" / "scale" / "prod_scale.sqlite"
OUT_CSV = ROOT / "costs" / "act_prod_costs.csv"
OUT_DETAIL = ROOT / "embeddings" / "calibration" / "act_prod_300.jsonl"
HEADER = [
    "concurrency", "difficulty", "stage", "n",
    "p50_ms", "p95_ms", "mean_ms", "measured", "mock", "note",
]


def _pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def _call_gateway(url: str, item: dict) -> dict:
    payload = json.dumps({
        "req_id": item["req_id"],
        "permission": item["permission"],
        "difficulty": item["difficulty"],
        "sql": item["sql"],
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    e2e_client_ms = (time.perf_counter() - t0) * 1000.0
    assert body.get("ok"), f"网关返回失败: {body}"
    return {
        "req_id": item["req_id"],
        "difficulty": item["difficulty"],
        "row_count": body["row_count"],
        "e2e_client_ms": round(e2e_client_ms, 4),
        "server_timings_ms": body["server_timings_ms"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool-size", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    assert SCALE_DB.is_file(), f"缺生产规模库 {SCALE_DB}，请先运行 python dataset/db/build_prod_scale.py"
    samples = list(io.read_jsonl(ROOT / "events" / "calibration_sample.jsonl"))
    tasks = {t["task_id"]: t for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}
    reqs = {r["req_id"]: r for r in io.read_jsonl(ROOT / "events" / "request_stream.jsonl")}

    items = [
        {
            "req_id": s["req_id"],
            "difficulty": tasks[s["task_id"]]["difficulty"],
            "permission": reqs[s["req_id"]]["permission"],
            "sql": tasks[s["task_id"]]["gold_sql"],
        }
        for s in samples
    ]
    if args.limit > 0:
        items = items[: args.limit]

    srv, _th, pool, port = act_tool_server.start_gateway(SCALE_DB, pool_size=args.pool_size)
    url = f"http://127.0.0.1:{port}/v1/tools/act/execute"
    print(f"只读工具网关已启动：{url}（pool_size={args.pool_size}，样本={len(items)}）", flush=True)

    rows: list[dict] = []
    detail_by_req: dict[str, dict] = {it["req_id"]: {"req_id": it["req_id"], "difficulty": it["difficulty"]} for it in items}
    stages = ("auth_parse", "pool_wait", "schema_inspect", "sql_validate", "sql_execute", "result_serialize", "e2e_client")
    notes = {
        "auth_parse": "HTTP 请求解析 + RBAC 鉴权 + SQL 只读校验（真机实测）",
        "pool_wait": f"有界只读连接池(pool_size={args.pool_size})真实排队等待耗时（真机实测）",
        "schema_inspect": "pragma_table_info 元数据探查（真机实测）",
        "sql_validate": "SELECT * FROM (sql) LIMIT 0 执行计划预检（真机实测）",
        "sql_execute": "150 万行 prod_scale.sqlite 真实分析查询执行（真机实测）",
        "result_serialize": "compare.normalize 规范化与 JSON 响应序列化（真机实测）",
        "e2e_client": "含 TCP/HTTP 往返、连接池排队与 4 步工具链的客户端端到端总耗时（真机实测）",
    }

    try:
        # 预热 5 条
        for it in items[:5]:
            _call_gateway(url, it)

        for conc in (1, 8, 16):
            t_start = time.perf_counter()
            if conc == 1:
                results = []
                for idx_i, it in enumerate(items, 1):
                    results.append(_call_gateway(url, it))
                    if idx_i % 50 == 0:
                        print(f"    [c=1] 进度 {idx_i}/{len(items)} ({time.perf_counter()-t_start:.1f}s)", flush=True)
            else:
                with ThreadPoolExecutor(max_workers=conc) as ex:
                    results = list(ex.map(lambda it: _call_gateway(url, it), items))
            wall_s = time.perf_counter() - t_start

            buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
            for res in results:
                diff = res["difficulty"]
                if conc in (1, 8):
                    detail_by_req[res["req_id"]][f"c{conc}_e2e_ms"] = res["e2e_client_ms"]
                    detail_by_req[res["req_id"]][f"c{conc}_pool_wait_ms"] = res["server_timings_ms"]["pool_wait"]
                    detail_by_req[res["req_id"]][f"c{conc}_sql_execute_ms"] = res["server_timings_ms"]["sql_execute"]
                for scope in ("all", diff):
                    for st in stages[:-1]:
                        buckets[(scope, st)].append(res["server_timings_ms"][st])
                    buckets[(scope, "e2e_client")].append(res["e2e_client_ms"])

            for scope in ("all", "single_table", "join", "nested_agg"):
                for st in stages:
                    vals = buckets[(scope, st)]
                    if not vals:
                        continue
                    rows.append({
                        "concurrency": conc,
                        "difficulty": scope,
                        "stage": st,
                        "n": len(vals),
                        "p50_ms": f"{_pct(vals, 50):.4f}",
                        "p95_ms": f"{_pct(vals, 95):.4f}",
                        "mean_ms": f"{statistics.fmean(vals):.4f}",
                        "measured": "1",
                        "mock": "",
                        "note": notes[st],
                    })

            e2e_all = buckets[("all", "e2e_client")]
            wait_all = buckets[("all", "pool_wait")]
            exec_all = buckets[("all", "sql_execute")]
            print(
                f"  [c={conc:2d}] wall={wall_s:5.1f}s | e2e p50={_pct(e2e_all, 50):7.2f} ms "
                f"p95={_pct(e2e_all, 95):7.2f} ms mean={statistics.fmean(e2e_all):7.2f} ms "
                f"| pool_wait p50={_pct(wait_all, 50):6.2f} ms | sql_exec p50={_pct(exec_all, 50):6.2f} ms",
                flush=True,
            )
    finally:
        srv.shutdown()
        srv.server_close()
        pool.close_all()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)

    io.write_jsonl(OUT_DETAIL, [detail_by_req[it["req_id"]] for it in items])
    print(f"已写 {OUT_CSV}（{len(rows)} 行）与 {OUT_DETAIL}（{len(items)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

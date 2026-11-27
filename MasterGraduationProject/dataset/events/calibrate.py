"""真实计时校准：只测 t_act_ms，其余列一律留空。

为什么只有 t_act_ms 是实测
--------------------------
``t_plan_ms`` / ``t_rag_ms`` / ``t_resp_ms`` / ``t_total_ms`` / ``token_cost`` 都由具体模型
（规划模型、召回模型、回答模型）与其上下文长度决定，本系统不跑模型，也不代造这些数。
``t_act_ms`` 只依赖一次只读 SQL 在固定快照上的执行，因此可以在本机真实测量：
用 ``db/executor.py`` 在**该请求自己的 snapshot** 上执行**该请求对应题目的 gold_sql**。

测量口径
--------
1. 每个请求重复 ``--reps`` 次（默认 3），取中位数，保留 3 位小数，单位毫秒；
2. 计时包含只读连接建立（executor 每次调用新建连接并置 query_only），
   即「一次 act 调用」的端到端耗时，而不是纯 SQLite 内核时间；
3. 单机、单进程、无并发；机器不同会得到不同数值，属正常波动（见 CALIBRATION.md）。

用法
----
    python dataset/events/calibrate.py                 # 写 real_calibration_300.template.csv
    python dataset/events/calibrate.py --reps 5
    python dataset/events/build.py --calibrate          # 先构建再校准
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "db") not in sys.path:
    sys.path.insert(0, str(ROOT / "db"))

from common import io  # noqa: E402

COLUMNS = ["req_id", "t_plan_ms", "t_rag_ms", "t_act_ms", "t_resp_ms", "t_total_ms", "token_cost"]
SAMPLE = "calibration_sample.jsonl"
CSV_NAME = "real_calibration_300.template.csv"


def run(out_dir: Path | str = HERE, *, reps: int = 3, verbose: bool = True) -> Path:
    """按 calibration_sample.jsonl 逐条真实执行，写出模板 CSV 并刷新 MANIFEST 中的记录。"""
    import executor  # noqa: PLC0415  只读执行器，来自 db/ 目录

    out = Path(out_dir)
    sample = list(io.read_jsonl(out / SAMPLE))
    tasks = {t["task_id"]: t for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}
    assert sample, f"{SAMPLE} 为空，请先运行 build.py"

    timings: dict[str, float] = {}
    for row in sample:
        task = tasks[row["task_id"]]
        sql = task["gold_sql"]
        samples: list[float] = []
        for _ in range(max(1, reps)):
            res = executor.execute(row["snapshot"], sql)
            if res.get("error"):
                raise RuntimeError(f"{row['req_id']} / {row['task_id']} 执行失败：{res['error']}")
            samples.append(float(res["elapsed_ms"]))
        timings[row["req_id"]] = round(statistics.median(samples), 3)

    path = out / CSV_NAME
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(",".join(COLUMNS) + "\n")
        for row in sample:
            f.write(",".join([row["req_id"], "", "", f"{timings[row['req_id']]:.3f}", "", "", ""]) + "\n")

    # 把 CSV 记录进 MANIFEST（measured 标记区分于构造产物）
    manifest_path = out / "MANIFEST.json"
    manifest = io.read_json(manifest_path) if manifest_path.is_file() else {}
    manifest[CSV_NAME] = {"rows": len(sample), "sha256": io.sha256_file(path),
                          "measured": True, "tolerance": "计时随机器波动，重测会改变哈希"}
    io.write_json(manifest_path, manifest)

    if verbose:
        vals = sorted(timings.values())
        print(f"  {CSV_NAME}  {len(vals)} 行（实测 t_act_ms）")
        print(f"  t_act_ms 中位 {statistics.median(vals):.3f} ms / 最小 {vals[0]:.3f} / "
              f"最大 {vals[-1]:.3f}")
        print(f"  其余 5 列留空，等待作者跑模型回填（见 CALIBRATION.md）")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="采样请求的真实 act 计时")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args(argv)
    started = time.perf_counter()
    run(Path(args.out), reps=args.reps)
    print(f"  用时 {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

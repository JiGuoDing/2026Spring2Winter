"""快模型 50 条小样本标定脚本（v0.5.0，形成第二真实部署画像）。

对 dataset/events/fast_calibration_sample_50.jsonl（50 条，100% 为原 300 条子集）
真实测量常规流式快模型（或关闭 xhigh 超长思考）的 plan/resp 时延与 token，支持：
  python dataset/tools/run_fast_model_calibration.py --dry-run
  python dataset/tools/run_fast_model_calibration.py --resume --limit 5
  python dataset/tools/run_fast_model_calibration.py --resume --write-back

环境变量：优先读取 LLM_FAST_BASE_URL / LLM_FAST_MODEL / LLM_FAST_API_KEY，
          缺省回退至 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY。
铁律：--dry-run 不联网、不写 measured；绝不伪造任何模型耗时。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

import executor  # noqa: E402
from common import io  # noqa: E402

SAMPLE_PATH = ROOT / "events" / "fast_calibration_sample_50.jsonl"
OUT_PROGRESS = ROOT / "embeddings" / "calibration" / "fast_calibration_50_progress.jsonl"
OUT_CSV = ROOT / "events" / "fast_calibration_50.csv"
PROFILES_JSON = ROOT / "costs" / "deployment_profiles.json"
PARAMS_PATH = ROOT / "config" / "params.json"
TASKS_PATH = ROOT / "tasks" / "tasks.jsonl"


def _pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def _chat(base_url: str, api_key: str, model: str, messages: list[dict],
          max_tokens: int, timeout_s: int) -> dict:
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = url + ("/chat/completions" if url.endswith("/v1") else "/v1/chat/completions")
    payload = {"model": model, "messages": messages, "temperature": 0.0, "max_tokens": max_tokens}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    choice = body["choices"][0]
    usage = body.get("usage") or {}
    return {
        "text": (choice.get("message") or {}).get("content") or "",
        "finish_reason": choice.get("finish_reason"),
        "elapsed_ms": round(elapsed_ms, 3),
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
    }


def write_back(records: list[dict], model_name: str) -> None:
    cols = ["req_id", "task_id", "snapshot", "t_plan_ms", "t_resp_ms", "t_model_total_ms", "token_cost"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            w.writerow({
                "req_id": r["req_id"],
                "task_id": r["task_id"],
                "snapshot": r["snapshot"],
                "t_plan_ms": r["plan"]["elapsed_ms"],
                "t_resp_ms": r["resp"]["elapsed_ms"],
                "t_model_total_ms": round(r["plan"]["elapsed_ms"] + r["resp"]["elapsed_ms"], 3),
                "token_cost": r["token_cost"],
            })
    if PROFILES_JSON.is_file() and records:
        profs = io.read_json(PROFILES_JSON)
        tot = [r["plan"]["elapsed_ms"] + r["resp"]["elapsed_ms"] for r in records]
        p_plan = _pct([r["plan"]["elapsed_ms"] for r in records], 50)
        p_resp = _pct([r["resp"]["elapsed_ms"] for r in records], 50)
        mean_tot = round(statistics.fmean(tot), 2)
        for p in profs["profiles"]:
            if p["id"] in ("P3_fast_modern_rag_remote", "P4_fast_modern_rag_warehouse"):
                p["model_stage"] = {
                    "status": "measured",
                    "model": model_name,
                    "n": len(records),
                    "plan_p50_ms": round(p_plan, 2),
                    "resp_p50_ms": round(p_resp, 2),
                    "total_mean_ms": mean_tot,
                    "source": "events/fast_calibration_50.csv",
                }
        io.write_json(PROFILES_JSON, profs)
    params = io.read_json(PARAMS_PATH)
    params["fast_calibration"]["status"] = "measured"
    params["fast_calibration"]["model"] = model_name
    io.write_json(PARAMS_PATH, params)
    print(f"[write-back] 已写 {OUT_CSV} 并更新 {PROFILES_JSON}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--write-back", action="store_true")
    args = ap.parse_args()

    assert SAMPLE_PATH.is_file(), f"缺样本文件 {SAMPLE_PATH}"
    samples = list(io.read_jsonl(SAMPLE_PATH))
    tasks = {t["task_id"]: t for t in io.read_jsonl(TASKS_PATH)}
    assert all(s["task_id"] in tasks for s in samples), "样本含未知 task_id"

    base_url = os.environ.get("LLM_FAST_BASE_URL") or os.environ.get("LLM_BASE_URL", "")
    api_key = os.environ.get("LLM_FAST_API_KEY") or os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_FAST_MODEL") or os.environ.get("LLM_MODEL", "")
    max_tokens = int(os.environ.get("LLM_FAST_MAX_TOKENS", "2048"))
    timeout_s = int(os.environ.get("LLM_FAST_TIMEOUT_S", "300"))

    if args.dry_run:
        print(f"[dry-run] 快模型样本校验通过：{len(samples)} 条（全覆盖 tasks.jsonl）")
        print(f"[dry-run] base_url={'已设' if base_url else '未设'} | model={model or '未设'} | max_tokens={max_tokens}")
        print("[dry-run] 未联网、未写入任何 measured 数值")
        return 0

    if not base_url or not model:
        print("ERROR: 需设置 LLM_FAST_BASE_URL / LLM_FAST_MODEL（或 LLM_BASE_URL / LLM_MODEL）", file=sys.stderr)
        return 2

    existing: list[dict] = []
    done: set[str] = set()
    if args.resume and OUT_PROGRESS.is_file():
        existing = list(io.read_jsonl(OUT_PROGRESS))
        done = {r["req_id"] for r in existing}

    OUT_PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    todo = [s for s in samples if s["req_id"] not in done]
    if args.limit > 0:
        todo = todo[: args.limit]

    with OUT_PROGRESS.open("a", encoding="utf-8", newline="\n") as f:
        for s in todo:
            t = tasks[s["task_id"]]
            exec_res = executor.execute(s["snapshot"], t["gold_sql"])
            rows_preview = json.dumps(exec_res.get("rows", [])[:15], ensure_ascii=False)
            p_res = _chat(
                base_url, api_key, model,
                [
                    {"role": "system", "content": "你是企业取数规划助手，用 3–5 步简明列出执行计划。"},
                    {"role": "user", "content": f"问题：{s['query_text']}"},
                ],
                max_tokens, timeout_s,
            )
            r_res = _chat(
                base_url, api_key, model,
                [
                    {"role": "system", "content": "你是企业数据问答助手，仅依据执行结果简明准确作答。"},
                    {"role": "user", "content": f"问题：{s['query_text']}\n执行结果：{rows_preview}"},
                ],
                max_tokens, timeout_s,
            )
            tok = (
                p_res["prompt_tokens"] + p_res["completion_tokens"]
                + r_res["prompt_tokens"] + r_res["completion_tokens"]
            )
            rec = {
                "req_id": s["req_id"],
                "task_id": s["task_id"],
                "snapshot": s["snapshot"],
                "plan": p_res,
                "resp": r_res,
                "token_cost": tok,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            existing.append(rec)
            print(f"{s['req_id']} plan={p_res['elapsed_ms']}ms resp={r_res['elapsed_ms']}ms tok={tok}")

    if args.write_back:
        write_back(existing, model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

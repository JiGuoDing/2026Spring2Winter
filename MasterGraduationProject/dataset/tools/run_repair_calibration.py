"""C3 局部修复 / 完整重生成 / 在线双检先导标定脚本（v0.4.0）。

对 dataset/events/repair_calibration_sample.jsonl（40 对样本）执行配对真机标定：
  1. ExtractOnlineRequiredItems：仅从 query_text 与新版本可见证据提取必答项（严禁读取金标）；
  2. LocalRepair：基于旧回答与变更证据块执行局部改写；
  3. DualVerify：忠实性 ∧ 必答完整性双检核验；
  4. FullRegenerate：基于最新证据完整重生成 + 双检核验（同批样本配对对照）。

用法：
  python dataset/tools/run_repair_calibration.py --dry-run
  python dataset/tools/run_repair_calibration.py --resume
  python dataset/tools/run_repair_calibration.py --resume --write-back

铁律：
  - --dry-run 不联网、不写任何 measured 数值；
  - 严禁伪造模型耗时；未真机运行前 path_costs.csv 中新增/待替换行保持原状或 pending。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

SAMPLE_PATH = ROOT / "events" / "repair_calibration_sample.jsonl"
DOCS_PATH = ROOT / "events" / "docs_versioned.jsonl"
COSTS_CSV = ROOT / "costs" / "path_costs.csv"
PARAMS_PATH = ROOT / "config" / "params.json"
OUT_PROGRESS = ROOT / "embeddings" / "calibration" / "repair_calibration_results.jsonl"


def _pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def _chat_completion(base_url: str, api_key: str, model: str, messages: list[dict],
                     max_tokens: int, timeout_s: int, reasoning_effort: str | None) -> dict:
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = url + ("/chat/completions" if url.endswith("/v1") else "/v1/chat/completions")
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
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


def build_local_repair_prompt(row: dict, new_doc_text: str) -> list[dict]:
    diff_str = "\n".join(
        f"- 块 {d['chunk_id']}：\n  旧版：{d['old_text']}\n  新版：{d['new_text']}"
        for d in row["diff_chunks"]
    )
    return [
        {
            "role": "system",
            "content": (
                "你是数据问答局部修复助手。给定原问题、旧回答和发生变更的证据块，"
                "仅修改受证据变更影响的事实与口径说明，保留其余仍然正确的表述；"
                "不得遗漏原问题要求回答的任何实体、指标或时间范围。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原问题：{row['query_text']}\n\n"
                f"旧回答：\n{row['old_resp_text']}\n\n"
                f"变更证据块（{row['doc_id']} v{row['old_ver']}→v{row['new_ver']}）：\n{diff_str}\n\n"
                f"新版完整文档参考：\n{new_doc_text[:3000]}\n\n"
                "请输出更新后的完整中文回答。"
            ),
        },
    ]


def build_full_regen_prompt(row: dict, new_doc_text: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": "你是企业数据问答助手。仅依据给定最新版本证据回答用户问题，覆盖全部实体、指标与时间范围要求。",
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{row['query_text']}\n\n"
                f"最新证据（{row['doc_id']} v{row['new_ver']}）：\n{new_doc_text[:4000]}\n\n"
                "请基于最新证据完整作答。"
            ),
        },
    ]


def build_dual_verify_prompt(query_text: str, candidate_answer: str, new_doc_text: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "你是回答核验器。仅根据用户问题和最新证据做两项检查：\n"
                "1. faithful：候选回答中的事实和口径是否与最新证据一致（无过时口径或幻觉）；\n"
                "2. complete：候选回答是否完整覆盖用户问题显式要求的实体、指标与时间范围（不得删去难修部分蒙混过关）。\n"
                '只输出严格 JSON：{"faithful": true/false, "complete": true/false, "reason": "简短原因"}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{query_text}\n\n"
                f"最新证据：\n{new_doc_text[:3500]}\n\n"
                f"候选回答：\n{candidate_answer}"
            ),
        },
    ]


def parse_verify_json(text: str) -> tuple[bool, bool, bool]:
    try:
        s = text.strip()
        start, end = s.find("{"), s.rfind("}")
        obj = json.loads(s[start : end + 1]) if start != -1 and end != -1 else json.loads(s)
        f_ok = bool(obj.get("faithful", False))
        c_ok = bool(obj.get("complete", False))
        return f_ok, c_ok, (f_ok and c_ok)
    except Exception:  # noqa: BLE001
        return False, False, False


def write_back_costs(results: list[dict], model_slot: str) -> None:
    local_ms = [r["local_repair"]["elapsed_ms"] for r in results if r["stratum"] != "doc_only_unchanged"]
    verify_ms = [r["local_verify"]["elapsed_ms"] for r in results if r["stratum"] != "doc_only_unchanged"]
    if not local_ms or not verify_ms:
        print("[write-back] 有效样本不足，跳过回写")
        return

    rows = list(csv.DictReader(COSTS_CSV.open("r", encoding="utf-8", newline="")))
    fieldnames = list(rows[0].keys())
    updated = False
    has_verify_row = False
    for row in rows:
        if row["path"] == "partial_repair" and row["stage"] == "rewrite" and row["model"] == model_slot:
            row["n"] = str(len(local_ms))
            row["metric"] = "p50"
            row["value_ms"] = f"{_pct(local_ms, 50):.3f}"
            row["measured"] = "backfill"
            row["mock"] = ""
            row["note"] = (
                f"run_repair_calibration.py 真实局部改写实测（替换旧 plan P50 代理）；"
                f"p50={_pct(local_ms, 50):.1f}ms; p95={_pct(local_ms, 95):.1f}ms; "
                f"mean={statistics.fmean(local_ms):.1f}ms; n={len(local_ms)}"
            )
            updated = True
        if row["path"] == "partial_repair" and row["stage"] == "dual_verify" and row["model"] == model_slot:
            has_verify_row = True
            row["n"] = str(len(verify_ms))
            row["metric"] = "p50"
            row["value_ms"] = f"{_pct(verify_ms, 50):.3f}"
            row["measured"] = "backfill"
            row["mock"] = ""
            row["note"] = (
                f"run_repair_calibration.py 真实在线双检实测；"
                f"p50={_pct(verify_ms, 50):.1f}ms; p95={_pct(verify_ms, 95):.1f}ms; n={len(verify_ms)}"
            )
    if not has_verify_row:
        rows.append({
            "path": "partial_repair",
            "stage": "dual_verify",
            "model": model_slot,
            "concurrency": "1",
            "n": str(len(verify_ms)),
            "metric": "p50",
            "value_ms": f"{_pct(verify_ms, 50):.3f}",
            "measured": "backfill",
            "mock": "",
            "note": (
                f"run_repair_calibration.py 真实在线双检实测；"
                f"p50={_pct(verify_ms, 50):.1f}ms; p95={_pct(verify_ms, 95):.1f}ms; n={len(verify_ms)}"
            ),
        })
    if updated or not has_verify_row:
        with COSTS_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        params = io.read_json(PARAMS_PATH)
        params["repair_calibration"]["status"] = "measured"
        io.write_json(PARAMS_PATH, params)
        print(f"[write-back] 已更新 {COSTS_CSV} 与 {PARAMS_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="仅校验样本与配置，不发网络请求、不写盘")
    ap.add_argument("--resume", action="store_true", help="跳过已完成 pair_id")
    ap.add_argument("--limit", type=int, default=0, help="仅跑前 N 对（0 表示全部）")
    ap.add_argument("--write-back", action="store_true", help="完成后回填 costs/path_costs.csv")
    ap.add_argument("--model-slot", default="local-qwen3-8-27b")
    args = ap.parse_args()

    assert SAMPLE_PATH.is_file(), f"缺样本文件 {SAMPLE_PATH}，请先运行 dataset/events/build_repair_sample.py"
    samples = list(io.read_jsonl(SAMPLE_PATH))
    docs_text: dict[tuple[str, int], str] = {}
    for row in io.read_jsonl(DOCS_PATH):
        docs_text[(row["doc_id"], row["version"])] = "\n".join(c["text"] for c in row["chunks"])

    missing_docs = [
        (s["pair_id"], s["doc_id"], s["new_ver"])
        for s in samples
        if (s["doc_id"], s["new_ver"]) not in docs_text
    ]
    assert not missing_docs, f"缺失新版文档: {missing_docs[:5]}"

    base_url = os.environ.get("LLM_BASE_URL", "")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS_RESP", "32768"))
    timeout_s = int(os.environ.get("LLM_TIMEOUT_S", "2700"))
    effort = os.environ.get("LLM_REASONING_EFFORT", "") or None

    if args.dry_run:
        print(f"[dry-run] 样本校验通过：{len(samples)} 对，新版文档 100% 命中")
        print(f"[dry-run] LLM_BASE_URL={'已设' if base_url else '未设'} | LLM_MODEL={model or '未设'} | max_tokens={max_tokens}")
        print("[dry-run] 未发起网络调用，未写入任何 measured 数值")
        return 0

    if not base_url or not model:
        print("ERROR: 真实运行需设置环境变量 LLM_BASE_URL 与 LLM_MODEL", file=sys.stderr)
        return 2

    done_ids: set[str] = set()
    existing: list[dict] = []
    if args.resume and OUT_PROGRESS.is_file():
        existing = list(io.read_jsonl(OUT_PROGRESS))
        done_ids = {r["pair_id"] for r in existing}

    OUT_PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    todo = [s for s in samples if s["pair_id"] not in done_ids]
    if args.limit > 0:
        todo = todo[: args.limit]

    with OUT_PROGRESS.open("a", encoding="utf-8", newline="\n") as f:
        for s in todo:
            new_doc = docs_text[(s["doc_id"], s["new_ver"])]
            loc = _chat_completion(base_url, api_key, model, build_local_repair_prompt(s, new_doc),
                                   max_tokens, timeout_s, effort)
            loc_v = _chat_completion(base_url, api_key, model,
                                     build_dual_verify_prompt(s["query_text"], loc["text"], new_doc),
                                     max_tokens, timeout_s, effort)
            lf, lc, l_pass = parse_verify_json(loc_v["text"])

            full = _chat_completion(base_url, api_key, model, build_full_regen_prompt(s, new_doc),
                                    max_tokens, timeout_s, effort)
            full_v = _chat_completion(base_url, api_key, model,
                                      build_dual_verify_prompt(s["query_text"], full["text"], new_doc),
                                      max_tokens, timeout_s, effort)
            ff, fc, f_pass = parse_verify_json(full_v["text"])

            rec = {
                "pair_id": s["pair_id"],
                "stratum": s["stratum"],
                "event_id": s["event_id"],
                "req_id": s["req_id"],
                "rho": s["rho"],
                "local_repair": loc,
                "local_verify": {**loc_v, "faithful": lf, "complete": lc, "dual_pass": l_pass},
                "full_regen": full,
                "full_verify": {**full_v, "faithful": ff, "complete": fc, "dual_pass": f_pass},
                "fallback_triggered": not l_pass,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            existing.append(rec)
            print(f"{s['pair_id']} [{s['stratum']}] local={loc['elapsed_ms']}ms pass={l_pass} | full={full['elapsed_ms']}ms")

    if args.write_back:
        write_back_costs(existing, args.model_slot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

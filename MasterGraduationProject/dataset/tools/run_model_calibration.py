"""真实 LLM 标定通道（Step 5）：四阶段计时 + token 计量 + 成本/标签回填。

本脚本解决 `events/CALIBRATION.md` 留下的五个空列与 `costs/path_costs.csv` 的 4 个
`mock=pending` 单元格：它不造数，只在你**自己的模型服务**上跑真实请求并记录墙钟与 usage。

环境变量（缺一个就不发起真实调用）
----------------------------------
| 变量 | 必填 | 说明 |
|---|---|---|
| ``LLM_BASE_URL`` | 是 | OpenAI 兼容基址。vLLM：``http://127.0.0.1:8000/v1``；Ollama：``http://127.0.0.1:11434/v1`` 或 ``http://127.0.0.1:11434``（自动补 ``/v1/chat/completions``） |
| ``LLM_MODEL`` | 是 | 模型名，原样传给 ``/chat/completions`` 的 ``model`` 字段 |
| ``LLM_API_KEY`` | 非本地必填 | 走 ``Authorization: Bearer``；localhost/127.0.0.1/::1 可省略 |
| ``LLM_TIMEOUT_S`` | 否 | 单次请求超时，默认 120 |
| ``LLM_MAX_RETRIES`` | 否 | 429/5xx 重试次数，默认 3 |

真实运行做的事
--------------
1. 对 ``real_calibration_300.template.csv`` 的 300 条请求依次跑 plan / rag / act / resp：
   - ``plan``：模型规划调用，记墙钟与 prompt/completion tokens；
   - ``rag``：读 ``embeddings/query_embeddings.npz`` 查句向量 + 本地 BM25 检索（按请求快照
     解析文档版本）+ 上下文拼装；本地段，模型 token 记 0；
   - ``act``：默认复用模板里已实测的 ``t_act_ms``（CALIBRATION.md 要求不要重复测两套口径）；
     ``--act-source local`` 可在请求自己的快照上重测 SQL；
   - ``resp``：模型生成调用，同样记墙钟与 usage；
   - ``t_total_ms`` 独立测端到端墙钟，不用四段相加冒充。
2. 写 ``events/real_calibration_300.csv``（模板五列回填；``token_cost`` = plan+resp 的
   prompt+completion 合计 token 数，明细见 ``embeddings/calibration/requests.jsonl``）。
3. 回填 ``costs/path_costs.csv`` 中**所选模型别名**的 2 行 ``mock=pending``：
   ``partial_repair/rewrite`` ← plan 段 p50，``full_regen/generate`` ← resp 段 p50；
   ``measured`` 列写 ``backfill``（见 ``costs/README.md`` 第 4/5 节），``mock`` 清空。
   另一个模型占位行保持 ``pending``——两个模型别名各跑一次才能填满 4 行，不把一个模型的
   数值复制到另一个占位模型上。
4. 对 ``labels/branch_pairs.jsonl`` 抽样回填 ``t_model_full_ms`` / ``t_model_cache_ms`` /
   ``g_e2e_ms``：``t_model_full_ms`` = plan + 全上下文 resp；``t_model_cache_ms`` = 短上下文 resp
   （缓存路径没有保存历史答案正文，用短上下文作答近似，口径写进 note）；
   ``g_e2e_ms = g_local_ms + (t_model_full_ms - t_model_cache_ms)``。
5. 刷新 ``costs/``、``labels/``、``events/`` 三个 MANIFEST 中受影响文件的 sha256/bytes。
6. 打印实测 p50/p95 与 ``costs/path_costs.csv`` 里可建模段（act、rag）的 MAPE；
   plan/resp 在成本表里是 ``mock=pending``，没有建模基线，不硬算 MAPE。

``--dry-run`` 只校验：环境变量、五个输入文件的列名/行数/交叉引用、模型缓存与句向量覆盖、
写回目标是否可写；**不发起任何网络请求、不写任何 measured 数值**（costs/labels/events 一字节不变）。

用法
----
    python dataset/tools/run_model_calibration.py --dry-run
    LLM_BASE_URL=http://127.0.0.1:8000/v1 LLM_MODEL=my-7b \\
        python dataset/tools/run_model_calibration.py --model-alias local-small-7b
    python dataset/tools/run_model_calibration.py --dry-run --strict-env   # 缺环境变量则退出 2

注意：真实运行会回写 ``costs/``、``labels/``、``events/``（按任务书要求，属作者侧测量步骤，
不属于 P 阶段构造产物）；``--no-write-back`` 只写 ``embeddings/calibration/`` 下的副本，便于先试跑。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import platform
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

SCRIPT_VERSION = "0.2.0"

HERE = Path(__file__).resolve().parent          # dataset/tools
DATASET = HERE.parent                           # dataset/
EMB_DIR = DATASET / "embeddings"
CALIB_DIR = EMB_DIR / "calibration"
NPZ = EMB_DIR / "query_embeddings.npz"

EVENTS = DATASET / "events"
TEMPLATE_CSV = EVENTS / "real_calibration_300.template.csv"
OUT_CSV = EVENTS / "real_calibration_300.csv"
SAMPLE_JSONL = EVENTS / "calibration_sample.jsonl"
STREAM_JSONL = EVENTS / "request_stream.jsonl"
DOCS_JSONL = EVENTS / "docs_versioned.jsonl"
TASKS_JSONL = DATASET / "tasks" / "tasks.jsonl"
BRANCH_JSONL = DATASET / "labels" / "branch_pairs.jsonl"
COSTS_CSV = DATASET / "costs" / "path_costs.csv"
EVENTS_MANIFEST = EVENTS / "MANIFEST.json"
LABELS_MANIFEST = DATASET / "labels" / "MANIFEST.json"
COSTS_MANIFEST = DATASET / "costs" / "MANIFEST.json"

sys.path.insert(0, str(DATASET))
from common import io, seeds  # noqa: E402

COLUMNS = ["req_id", "t_plan_ms", "t_rag_ms", "t_act_ms", "t_resp_ms", "t_total_ms", "token_cost"]
COST_HEADER = ["path", "stage", "model", "concurrency", "n", "metric", "value_ms",
               "measured", "mock", "note"]
MODEL_ALIASES = ("local-qwen3-8-27b", "api-large-placeholder")
# path_costs 里 model 阶段的实测值映射：成本行 ← 本脚本的哪一段 p50
COST_ROW_STAGE = {("partial_repair", "rewrite"): "plan", ("full_regen", "generate"): "resp"}

TOP_K = 5
CONTEXT_CHARS = 8000
BM25_K1 = 1.5
BM25_B = 0.75
SNAPSHOT_AS_OF = {
    "v0": "2024-05-15T00:00:00Z",
    "v1": "2024-05-15T06:00:00Z",
    "v2": "2024-05-15T12:00:00Z",
}


class CalibrationError(RuntimeError):
    """环境、输入或接口层面的失败；真实运行失败时不写任何 measured 数值。"""


# ------------------------------------------------------------------ 通用工具
def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, header: list[str], rows: list[dict]) -> None:
    for row in rows:
        for key in header:
            text = str(row.get(key, ""))
            if any(ch in text for ch in (",", '"', "\n")):
                raise CalibrationError(f"{path.name} 的字段 {key} 含会破坏 CSV 的字符：{text!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{k: row.get(k, "") for k in header} for row in rows])
    os.replace(tmp, path)


def write_json_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def fmt_ms(value: float) -> str:
    return f"{value:.3f}"


def percentile(sorted_values: list[float], q: float) -> float:
    """线性插值分位数（与 costs/runner.py 的 type-7 一致，不依赖 numpy）。"""
    if not sorted_values:
        raise CalibrationError("空样本无法求分位数")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def summarize(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "mean": round(statistics.fmean(ordered), 3),
        "p50": round(percentile(ordered, 0.50), 3),
        "p95": round(percentile(ordered, 0.95), 3),
        "min": round(ordered[0], 3),
        "max": round(ordered[-1], 3),
    }


def _line_count(path: Path) -> int:
    with path.open("rb") as f:
        return sum(1 for _ in f)


def update_manifest(manifest_path: Path, rel_name: str, target: Path,
                    rows: int, add_bytes: bool) -> None:
    """刷新所在目录 MANIFEST 中某个文件的 rows/sha256（保留既有额外字段）。"""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    entry = dict(manifest.get(rel_name) or {})
    entry["rows"] = rows
    entry["sha256"] = sha256_file(target)
    if add_bytes or "bytes" in entry:
        entry["bytes"] = target.stat().st_size
    manifest[rel_name] = entry
    write_json_atomic(manifest_path, manifest)


# ------------------------------------------------------------------ 环境变量
def load_env_config() -> dict:
    base = (os.environ.get("LLM_BASE_URL") or "").strip()
    key = (os.environ.get("LLM_API_KEY") or "").strip()
    model = (os.environ.get("LLM_MODEL") or "").strip()
    host = urlsplit(base).hostname if base else None
    is_local = host in {"localhost", "127.0.0.1", "::1"}
    timeout_s = float(os.environ.get("LLM_TIMEOUT_S") or 600)
    max_retries = int(os.environ.get("LLM_MAX_RETRIES") or 3)
    # 生成长度与上下文：用户可指定（默认 32768 输出 / 65536 上下文）
    max_tokens_plan = int(os.environ.get("LLM_MAX_TOKENS_PLAN") or 32768)
    max_tokens_resp = int(os.environ.get("LLM_MAX_TOKENS_RESP") or 32768)
    max_tokens_cache = int(os.environ.get("LLM_MAX_TOKENS_CACHE") or 32768)
    context_window = int(os.environ.get("LLM_CONTEXT_WINDOW") or 65536)
    reasoning_effort = (os.environ.get("LLM_REASONING_EFFORT") or "xhigh").strip()
    enable_thinking = (os.environ.get("LLM_ENABLE_THINKING") or "").strip().lower() in {"1", "true", "yes"}
    missing: list[str] = []
    if not base:
        missing.append("LLM_BASE_URL")
    elif urlsplit(base).scheme not in ("http", "https"):
        missing.append("LLM_BASE_URL（必须以 http:// 或 https:// 开头）")
    if not model:
        missing.append("LLM_MODEL")
    if not key and not is_local:
        missing.append("LLM_API_KEY（目标不是 localhost，必须提供）")
    endpoint = ""
    if base and urlsplit(base).scheme in ("http", "https"):
        endpoint = resolve_endpoint(base)
    return {
        "base_url": base,
        "endpoint": endpoint,
        "api_key": key,
        "model": model,
        "host": host,
        "is_local": is_local,
        "timeout_s": timeout_s,
        "max_retries": max_retries,
        "max_tokens_plan": max_tokens_plan,
        "max_tokens_resp": max_tokens_resp,
        "max_tokens_cache": max_tokens_cache,
        "context_window": context_window,
        "reasoning_effort": reasoning_effort,
        "enable_thinking": enable_thinking,
        "missing": missing,
    }


def resolve_endpoint(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def print_env_status(cfg: dict) -> None:
    if cfg["missing"]:
        print("[BLOCKED] 缺少/非法环境变量，真实运行不会启动：")
        for item in cfg["missing"]:
            print(f"  - {item}")
        print("  示例（PowerShell）：")
        print('    $env:LLM_BASE_URL="http://127.0.0.1:8000/v1"')
        print('    $env:LLM_MODEL="my-7b"')
        print('    $env:LLM_API_KEY="..."   # 非 localhost 必填')
    else:
        print(f"  环境变量：OK  endpoint={cfg['endpoint']}  model={cfg['model']}  "
              f"local={cfg['is_local']}  超时={cfg['timeout_s']:.0f}s  重试={cfg['max_retries']}")


# ------------------------------------------------------------------ 输入校验
def load_inputs(limit: int = 0) -> dict:
    """校验并加载 300 条模板、请求流、抽样清单、题目、句向量覆盖。"""
    problems: list[str] = []
    for path in (TEMPLATE_CSV, SAMPLE_JSONL, STREAM_JSONL, TASKS_JSONL,
                 DOCS_JSONL, BRANCH_JSONL, COSTS_CSV):
        if not path.is_file():
            problems.append(f"缺少输入文件：{path}")
    if problems:
        raise CalibrationError("\n  - ".join(problems))

    template = read_csv_rows(TEMPLATE_CSV)
    if not template:
        raise CalibrationError(f"{TEMPLATE_CSV} 为空")
    header = list(template[0].keys())
    if header != COLUMNS:
        raise CalibrationError(f"模板列顺序不符：{header} != {COLUMNS}")
    if len(template) != 300:
        raise CalibrationError(f"模板应有 300 行，实际 {len(template)} 行")
    req_ids = [r["req_id"] for r in template]
    if len(set(req_ids)) != len(req_ids):
        raise CalibrationError("模板 req_id 有重复")
    blanks = [c for c in COLUMNS if c != "req_id" and c != "t_act_ms"]
    for i, row in enumerate(template, start=1):
        try:
            float(row["t_act_ms"])
        except (TypeError, ValueError):
            raise CalibrationError(f"模板第 {i} 行 t_act_ms 非数值：{row['t_act_ms']!r}")
        for col in blanks:
            if (row[col] or "").strip():
                problems.append(f"模板第 {i} 行 {col} 已非空（真实运行会覆盖 real_calibration_300.csv，不动模板）")

    stream = {}
    for row in read_jsonl(STREAM_JSONL):
        stream[row["req_id"]] = row
    sample = {r["req_id"]: r for r in read_jsonl(SAMPLE_JSONL)}
    tasks = {r["task_id"]: r for r in read_jsonl(TASKS_JSONL)}

    items: list[dict] = []
    for row in template:
        req_id = row["req_id"]
        req = stream.get(req_id)
        if req is None:
            problems.append(f"模板 req_id {req_id} 不在请求流中")
            continue
        smp = sample.get(req_id)
        if smp is None:
            problems.append(f"模板 req_id {req_id} 不在 calibration_sample.jsonl 中")
            continue
        if smp["snapshot"] != req["snapshot"]["index"]:
            problems.append(f"{req_id} 快照不一致：sample={smp['snapshot']} stream={req['snapshot']['index']}")
        if smp["task_id"] not in tasks:
            problems.append(f"{req_id} 的 task_id {smp['task_id']} 不在 tasks.jsonl 中")
        items.append({
            "req_id": req_id,
            "template_row": row,
            "request": req,
            "task_id": smp["task_id"],
            "snapshot": req["snapshot"]["index"],
        })
    if limit > 0:
        items = items[:limit]
    if problems:
        raise CalibrationError("输入交叉校验失败：\n  - " + "\n  - ".join(problems))

    npz_status = inspect_npz(items)
    return {
        "template": template,
        "items": items,
        "stream": stream,
        "tasks": tasks,
        "branch": read_jsonl(BRANCH_JSONL),
        "costs": read_csv_rows(COSTS_CSV),
        "npz": npz_status,
    }


def inspect_npz(items: list[dict]) -> dict:
    """检查句向量文件与 300 条 query_text 的覆盖情况（只读）。"""
    if not NPZ.is_file():
        return {"ok": False, "reason": f"{NPZ} 不存在；先跑 dataset/tools/build_embeddings.py"}
    try:
        import numpy as np  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"numpy 不可用：{exc}"}
    try:
        with np.load(NPZ, allow_pickle=False) as data:
            texts = [str(t) for t in data["query_texts"]]
            emb = data["embeddings"]
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"读取 npz 失败：{exc}"}
    index = {t: i for i, t in enumerate(texts)}
    missing = [it["req_id"] for it in items if it["request"]["query_text"] not in index]
    return {
        "ok": not missing,
        "n": int(emb.shape[0]),
        "dim": int(emb.shape[1]),
        "dtype": str(emb.dtype),
        "missing_req_ids": missing,
        "reason": (f"{len(missing)} 条请求的 query_text 不在 npz 中" if missing else ""),
    }


def pending_cost_rows(costs: list[dict], alias: str) -> list[dict]:
    return [r for r in costs if (r.get("mock") or "") == "pending" and r.get("model") == alias]


def cost_rows_for_alias(costs: list[dict], alias: str) -> list[dict]:
    rows: list[dict] = []
    for (path, stage), _ in COST_ROW_STAGE.items():
        hits = [r for r in costs if r["path"] == path and r["stage"] == stage
                and r["model"] == alias and (r.get("mock") or "") == "pending"]
        rows.extend(hits)
    return rows


def branch_null_count(branch: list[dict]) -> int:
    return sum(1 for r in branch if r.get("t_model_full_ms") is None
               or r.get("t_model_cache_ms") is None or r.get("g_e2e_ms") is None)


# ------------------------------------------------------------------ LLM 客户端
class LLMClient:
    """最小 OpenAI 兼容客户端：urllib 实现，不依赖 openai / requests。"""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.endpoint = cfg["endpoint"]
        self.model = cfg["model"]
        self.timeout_s = cfg["timeout_s"]
        self.max_retries = max(1, cfg["max_retries"])

    def chat(self, messages: list[dict], *, max_tokens: int, tag: str) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "top_p": 1.0,
            "stream": False,
            "max_tokens": max_tokens,
        }
        if self.cfg.get("reasoning_effort"):
            payload["reasoning_effort"] = self.cfg["reasoning_effort"]
        if self.cfg.get("enable_thinking"):
            payload["chat_template_kwargs"] = {"enable_thinking": True}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.cfg["api_key"]:
            headers["Authorization"] = f"Bearer {self.cfg['api_key']}"
        last: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            started = time.perf_counter()
            try:
                req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    raw = resp.read()
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                data = json.loads(raw.decode("utf-8"))
                choices = data.get("choices") or []
                if not choices:
                    raise CalibrationError(f"{tag}: 响应缺少 choices：{str(data)[:200]}")
                message = choices[0].get("message") or {}
                text = message.get("content") or ""
                reasoning_text = (message.get("reasoning") or message.get("reasoning_content") or "")
                usage = data.get("usage") or {}
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
                if prompt_tokens is None or completion_tokens is None:
                    raise CalibrationError(
                        f"{tag}: 服务端未返回 usage.prompt_tokens/completion_tokens，无法计量 token。"
                        "请确认服务开启了 usage 统计（vLLM 默认返回；Ollama OpenAI 兼容层也返回）。"
                    )
                return {
                    "text": text,
                    "t_ms": elapsed_ms,
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "finish_reason": choices[0].get("finish_reason"),
                    # 服务端把思考放 message.reasoning（不是 reasoning_content）；
                    # 原文不落盘，只存长度与前 160 字摘要，用于诊断长尾与空输出。
                    "reasoning_chars": len(reasoning_text),
                    "reasoning_preview": reasoning_text[:160],
                    "content_chars": len(text),
                }
            except urllib.error.HTTPError as exc:
                detail = exc.read()[:300].decode("utf-8", "replace")
                last = CalibrationError(f"{tag}: HTTP {exc.code} {detail!r}")
                if exc.code in (408, 409, 429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
                    continue
                raise last from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                last = CalibrationError(f"{tag}: 连接失败 {exc}")
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
                    continue
                raise last from exc
        raise last or CalibrationError(f"{tag}: 未知失败")


# ------------------------------------------------------------------ RAG（本地）
_RE_LATIN = re.compile(r"[a-z][a-z0-9_]+")
_RE_NUM = re.compile(r"\d+")
_RE_CJK = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> tuple[str, ...]:
    """与 costs/runner.py 同口径的固定分词：英文小写词 / 数字 / 中文 bigram。"""
    low = text.lower()
    out: list[str] = []
    out.extend(_RE_LATIN.findall(low))
    out.extend(_RE_NUM.findall(low))
    for seg in _RE_CJK.findall(low):
        if len(seg) == 1:
            out.append(seg)
        else:
            out.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    return tuple(out)


class Bm25Index:
    def __init__(self, doc_ids: list[str], doc_tokens: list[tuple[str, ...]]) -> None:
        self.doc_ids = list(doc_ids)
        self.n_docs = len(doc_tokens)
        self.lens = [len(t) for t in doc_tokens]
        self.avgdl = (sum(self.lens) / self.n_docs) if self.n_docs else 0.0
        postings: dict[str, list[tuple[int, int]]] = {}
        for i, toks in enumerate(doc_tokens):
            tf: dict[str, int] = {}
            for w in toks:
                tf[w] = tf.get(w, 0) + 1
            for word, freq in tf.items():
                postings.setdefault(word, []).append((i, freq))
        self.postings = {w: tuple(v) for w, v in postings.items()}

    def search(self, tokens: tuple[str, ...], k: int) -> list[str]:
        scores: dict[int, float] = {}
        n = self.n_docs
        for word in tokens:
            plist = self.postings.get(word)
            if not plist:
                continue
            df = len(plist)
            idf = math.log(1.0 + (n - df + 0.5) / (df + 0.5))
            for i, freq in plist:
                dl = self.lens[i]
                scores[i] = scores.get(i, 0.0) + idf * (freq * (BM25_K1 + 1.0)) / (
                    freq + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / self.avgdl))
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return [self.doc_ids[i] for i, _ in ranked]


class DocsIndex:
    """按请求快照解析文档版本后建 BM25 索引；索引构建不计入单请求 rag 计时。"""

    def __init__(self, docs_path: Path) -> None:
        rows = read_jsonl(docs_path)
        by_doc: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            by_doc[row["doc_id"]].append(row)
        self.texts: dict[str, dict[str, str]] = {}
        self.index: dict[str, Bm25Index] = {}
        for snap, as_of in SNAPSHOT_AS_OF.items():
            doc_ids: list[str] = []
            doc_texts: list[str] = []
            texts_map: dict[str, str] = {}
            for doc_id in sorted(by_doc):
                eligible = [v for v in by_doc[doc_id] if str(v["updated_at"]) <= as_of]
                if not eligible:
                    continue
                latest = max(eligible, key=lambda v: (int(v["version"]), str(v["updated_at"])))
                text = " ".join(chunk["text"] for chunk in latest["chunks"])
                doc_ids.append(doc_id)
                doc_texts.append(text)
                texts_map[doc_id] = text
            self.texts[snap] = texts_map
            self.index[snap] = Bm25Index(doc_ids, [tokenize(t) for t in doc_texts])

    def retrieve(self, query: str, snapshot: str) -> tuple[list[str], str, float]:
        started = time.perf_counter()
        doc_ids = self.index[snapshot].search(tokenize(query), TOP_K)
        parts: list[str] = []
        used = 0
        for doc_id in doc_ids:
            text = self.texts[snapshot][doc_id]
            piece = f"[{doc_id}] {text}"
            if used + len(piece) > CONTEXT_CHARS:
                piece = piece[: max(0, CONTEXT_CHARS - used)]
            parts.append(piece)
            used += len(piece)
            if used >= CONTEXT_CHARS:
                break
        return doc_ids, "\n".join(parts), (time.perf_counter() - started) * 1000.0


class EmbeddingLookup:
    def __init__(self, npz_path: Path) -> None:
        import numpy as np  # noqa: PLC0415

        with np.load(npz_path, allow_pickle=False) as data:
            texts = [str(t) for t in data["query_texts"]]
            self.emb = data["embeddings"]
        self.by_text = {t: i for i, t in enumerate(texts)}

    def get(self, text: str) -> "object":
        if text not in self.by_text:
            raise CalibrationError(f"query_text 不在句向量文件中：{text[:40]!r}")
        return self.emb[self.by_text[text]]


# ------------------------------------------------------------------ 四个阶段
PLAN_SYSTEM = "你是数据问答系统的规划器。只输出按行编号的执行步骤，不要解释，不要代码块。"
RESP_SYSTEM = ("你是数据问答助手。依据给定上下文与【数据库执行结果】回答；"
               "执行结果是查询的直接输出，其中的数字可以直接引用，不要声称缺少数据。"
               "引用口径来源时写 [doc_id]。上下文不足时明确说明缺口，不要编造执行结果之外的数字。")
CACHE_RESP_SYSTEM = ("你是缓存复用助手。给定问题与缓存条目（可能为空），判断能否直接复用；"
                     "能则压缩复述结论，不能则说明原因。不要编造上下文之外的事实。")


def stage_plan(client: LLMClient, item: dict) -> dict:
    req = item["request"]
    user = (f"用户问句：{req['query_text']}\n"
            f"plan_id={req.get('plan_id')}  act_key={req.get('act_key')}  "
            f"obj_types={req.get('obj_types')}\n"
            "请输出 3–6 步执行计划，每行一步（检索 → 执行 → 作答），不要展开 SQL。")
    return client.chat([{"role": "system", "content": PLAN_SYSTEM},
                        {"role": "user", "content": user}],
                    max_tokens=client.cfg.get("max_tokens_plan", 32768), tag="plan")


def stage_rag(lookup: EmbeddingLookup, docs: DocsIndex, item: dict) -> dict:
    started = time.perf_counter()
    vec = lookup.get(item["request"]["query_text"])
    doc_ids, context, retrieve_ms = docs.retrieve(item["request"]["query_text"], item["snapshot"])
    total_ms = (time.perf_counter() - started) * 1000.0
    return {
        "t_ms": total_ms,
        "retrieve_ms": retrieve_ms,
        "doc_ids": doc_ids,
        "context": context,
        "vec_dim": int(vec.shape[0]),
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }


def stage_exec_result(item: dict, executor) -> str:
    """把 gold SQL 的执行结果渲染成给 resp 看的文本块。

    没有这一步，resp 只能看到字段口径、看不到数据，会退化成"拒答"，测出的就不是答题时延。
    """
    task = item.get("task")
    if not task or executor is None:
        return ""
    res = executor.execute(item["snapshot"], task["gold_sql"])
    if res.get("error"):
        return f"（执行失败：{res['error']}）"
    cols = res.get("columns") or []
    all_rows = res.get("rows") or []
    lines = [" | ".join(str(c) for c in cols)]
    for row in all_rows[:20]:
        lines.append(" | ".join("" if v is None else str(v) for v in row))
    tail = "" if len(all_rows) <= 20 else f"\n… 共 {len(all_rows)} 行，仅显示前 20 行"
    return "```\n" + "\n".join(lines) + "\n```" + tail


def stage_resp(client: LLMClient, item: dict, context: str, exec_block: str = "") -> dict:
    req = item["request"]
    exec_section = f"\n\n【数据库执行结果】\n{exec_block}" if exec_block else "\n\n【数据库执行结果】\n（无）"
    user = f"上下文：\n{context}{exec_section}\n\n问题：{req['query_text']}"
    return client.chat([{"role": "system", "content": RESP_SYSTEM},
                        {"role": "user", "content": user}],
        max_tokens=client.cfg.get("max_tokens_resp", 32768), tag="resp")


def stage_act(item: dict, act_source: str, executor) -> dict:
    if act_source == "template":
        return {"t_ms": float(item["template_row"]["t_act_ms"]), "source": "template(t_act_ms)"}
    task = item.get("task")
    if not task:
        raise CalibrationError(f"act 本地执行需要 tasks.jsonl 中题目 {item['task_id']}")
    started = time.perf_counter()
    res = executor.execute(item["snapshot"], task["gold_sql"])
    elapsed = (time.perf_counter() - started) * 1000.0
    if res.get("error"):
        raise CalibrationError(f"{item['req_id']} act 执行失败：{res['error']}")
    return {"t_ms": elapsed, "source": "local-execute"}


def run_requests(client: LLMClient, lookup: EmbeddingLookup, docs: DocsIndex,
                 items: list[dict], act_source: str, tasks: dict) -> list[dict]:
    executor = None
    sys.path.insert(0, str(DATASET / "db"))
    import executor  # noqa: PLC0415,F811

    records: list[dict] = []
    for seq, item in enumerate(items, start=1):
        item["task"] = tasks.get(item["task_id"])
        started = time.perf_counter()
        plan = stage_plan(client, item)
        rag = stage_rag(lookup, docs, item)
        act = stage_act(item, act_source, executor)
        exec_block = stage_exec_result(item, executor)
        resp = stage_resp(client, item, rag["context"], exec_block)
        total_ms = (time.perf_counter() - started) * 1000.0
        record = {
            "seq": seq,
            "req_id": item["req_id"],
            "task_id": item["task_id"],
            "snapshot": item["snapshot"],
            "t_plan_ms": round(plan["t_ms"], 3),
            "t_rag_ms": round(rag["t_ms"], 3),
            "t_rag_retrieve_ms": round(rag["retrieve_ms"], 3),
            "t_act_ms": round(act["t_ms"], 3),
            "t_resp_ms": round(resp["t_ms"], 3),
            "t_total_ms": round(total_ms, 3),
            "act_source": act["source"],
            "plan": {"prompt_tokens": plan["prompt_tokens"],
                     "completion_tokens": plan["completion_tokens"]},
            "rag": {"prompt_tokens": 0, "completion_tokens": 0, "doc_ids": rag["doc_ids"],
                    "vec_dim": rag["vec_dim"]},
            "resp": {"prompt_tokens": resp["prompt_tokens"],
                     "completion_tokens": resp["completion_tokens"]},
            "plan_text": plan["text"],
            "resp_text": resp["text"],
            "plan_finish": plan.get("finish_reason"),
            "resp_finish": resp.get("finish_reason"),
            "plan_truncated": plan.get("finish_reason") == "length",
            "resp_truncated": resp.get("finish_reason") == "length",
            "resp_reasoning_chars": resp.get("reasoning_chars", 0),
            "resp_reasoning_preview": resp.get("reasoning_preview", ""),
            "resp_content_chars": resp.get("content_chars", 0),
            "plan_reasoning_chars": plan.get("reasoning_chars", 0),
            "exec_block_chars": len(exec_block),
        }
        record["token_cost"] = (plan["prompt_tokens"] + plan["completion_tokens"]
                                + resp["prompt_tokens"] + resp["completion_tokens"])
        records.append(record)
        if seq % 25 == 0 or seq == len(items):
            print(f"  进度 {seq}/{len(items)}  "
                  f"plan={record['t_plan_ms']:.0f}ms rag={record['t_rag_ms']:.1f}ms "
                  f"act={record['t_act_ms']:.2f}ms resp={record['t_resp_ms']:.0f}ms", flush=True)
    return records


def write_calibration_csv(records: list[dict], template: list[dict], out_path: Path,
                          require_all: bool = True) -> None:
    by_req = {r["req_id"]: r for r in records}
    rows: list[dict] = []
    for trow in template:
        rec = by_req.get(trow["req_id"])
        if rec is None:
            if require_all:
                raise CalibrationError(f"缺少 {trow['req_id']} 的实测记录，拒绝写不完整 CSV")
            continue
        rows.append({
            "req_id": rec["req_id"],
            "t_plan_ms": fmt_ms(rec["t_plan_ms"]),
            "t_rag_ms": fmt_ms(rec["t_rag_ms"]),
            "t_act_ms": fmt_ms(rec["t_act_ms"]),
            "t_resp_ms": fmt_ms(rec["t_resp_ms"]),
            "t_total_ms": fmt_ms(rec["t_total_ms"]),
            "token_cost": str(rec["token_cost"]),
        })
    write_csv_rows(out_path, COLUMNS, rows)


# ------------------------------------------------------------------ 回填
def fill_cost_rows(costs: list[dict], stats: dict, alias: str, model: str) -> list[dict]:
    """把所选模型别名下 2 行 mock=pending 改成 measured=backfill。"""
    targets = cost_rows_for_alias(costs, alias)
    if len(targets) != len(COST_ROW_STAGE):
        raise CalibrationError(
            f"costs/path_costs.csv 中 model={alias} 的 mock=pending 行应有 "
            f"{len(COST_ROW_STAGE)} 个，实际 {len(targets)} 个")
    changes: list[dict] = []
    for row in targets:
        stage_name = COST_ROW_STAGE[(row["path"], row["stage"])]
        stat = stats[stage_name]
        before = {"value_ms": row["value_ms"], "measured": row["measured"], "mock": row["mock"]}
        row["value_ms"] = fmt_ms(stat["p50"])
        row["measured"] = "backfill"
        row["mock"] = ""
        row["n"] = str(stat["n"])
        row["note"] = (f"作者模型 {model} 实测（run_model_calibration.py；alias={alias}）；"
                       f"value=p50({stage_name})={stat['p50']:.3f}ms；"
                       f"p95={stat['p95']:.3f}ms；n={stat['n']}")
        changes.append({"path": row["path"], "stage": row["stage"], "model": row["model"],
                        "before": before,
                        "after": {"value_ms": row["value_ms"], "measured": row["measured"],
                                  "mock": row["mock"], "n": row["n"]}})
    return changes


def sample_branch_indices(branch: list[dict], count: int) -> list[int]:
    if count <= 0:
        return []
    picked = list(range(len(branch)))
    seeds.rng("calibration", "branch_sample").shuffle(picked)
    return sorted(picked[: min(count, len(picked))])


def run_branch_measurements(client: LLMClient, lookup: EmbeddingLookup, docs: DocsIndex,
                            branch: list[dict], stream: dict, tasks: dict,
                            count: int, verbose: bool = True) -> dict:
    """抽样实测分支路径的模型段耗时，返回 {pair_id: 明细}。"""
    sys.path.insert(0, str(DATASET / "db"))
    import executor  # noqa: PLC0415

    chosen = sample_branch_indices(branch, count)
    details: dict[str, dict] = {}
    for counter, idx in enumerate(chosen, start=1):
        pair = branch[idx]
        req = stream.get(pair["req_id"])
        if req is None:
            raise CalibrationError(f"branch_pairs 的 req_id {pair['req_id']} 不在请求流中")
        task = tasks.get(pair["task_id"])
        item = {
            "req_id": pair["req_id"],
            "request": req,
            "task_id": pair["task_id"],
            "snapshot": req["snapshot"]["index"],
            "template_row": {},
            "task": task,
        }
        plan = stage_plan(client, item)
        rag = stage_rag(lookup, docs, item)
        exec_block = stage_exec_result(item, executor)
        full = stage_resp(client, item, rag["context"], exec_block)
        _, short_context, _ = docs.retrieve(req["query_text"], item["snapshot"])
        short_context = short_context[:1000]
        cached = client.chat(
            [{"role": "system", "content": CACHE_RESP_SYSTEM},
             {"role": "user", "content": f"问题：{req['query_text']}\n缓存条目：{short_context}"}],
            max_tokens=client.cfg.get("max_tokens_cache", 32768), tag="cache_resp")
        t_model_full = plan["t_ms"] + full["t_ms"]
        t_model_cache = cached["t_ms"]
        g_e2e = float(pair["g_local_ms"]) + (t_model_full - t_model_cache)
        pair["t_model_full_ms"] = round(t_model_full, 3)
        pair["t_model_cache_ms"] = round(t_model_cache, 3)
        pair["g_e2e_ms"] = round(g_e2e, 3)
        pair["note"] = ("model_measured; t_model_full=plan+resp(full ctx); "
                        "t_model_cache=resp(short ctx) 近似缓存命中；"
                        "g_e2e=g_local+(t_model_full-t_model_cache)")
        details[pair["pair_id"]] = {
            "pair_id": pair["pair_id"],
            "req_id": pair["req_id"],
            "t_model_full_ms": pair["t_model_full_ms"],
            "t_model_cache_ms": pair["t_model_cache_ms"],
            "g_local_ms": float(pair["g_local_ms"]),
            "g_e2e_ms": pair["g_e2e_ms"],
            "plan_ms": round(plan["t_ms"], 3),
            "resp_full_ms": round(full["t_ms"], 3),
            "resp_cache_ms": round(cached["t_ms"], 3),
        }
        if verbose and (counter % 5 == 0 or counter == len(chosen)):
            print(f"  分支进度 {counter}/{len(chosen)}  "
                  f"t_model_full={t_model_full:.0f}ms cache={t_model_cache:.0f}ms", flush=True)
    return details


# ------------------------------------------------------------------ MAPE
def stage_stats(records: list[dict]) -> dict:
    return {
        "plan": summarize([r["t_plan_ms"] for r in records]),
        "rag": summarize([r["t_rag_ms"] for r in records]),
        "act": summarize([r["t_act_ms"] for r in records]),
        "resp": summarize([r["t_resp_ms"] for r in records]),
        "total": summarize([r["t_total_ms"] for r in records]),
    }


def modeled_baseline(costs: list[dict]) -> dict:
    """成本表里已实测的本地段 p50（只取单并发行，与标定的单请求口径一致）。"""
    wanted = {("act", "execute_sql"): "act", ("full_regen", "retrieve"): "rag"}
    out: dict[str, float] = {}
    for row in costs:
        key = (row["path"], row["stage"])
        if key not in wanted or row["metric"] != "p50":
            continue
        if str(row.get("concurrency")) != "1":      # c=8/32 的排队开销不参与单请求比对
            continue
        if (row.get("measured") or "") not in ("1", "backfill"):
            continue
        try:
            out[wanted[key]] = float(row["value_ms"])
        except (TypeError, ValueError):
            continue
    return out


def mape_report(stats: dict, costs: list[dict]) -> list[dict]:
    modeled = modeled_baseline(costs)
    rows: list[dict] = []
    for stage_name in ("act", "rag"):
        if stage_name not in modeled:
            continue
        actual = stats[stage_name]["p50"]
        base = modeled[stage_name]
        if actual <= 0:
            continue
        rows.append({
            "stage": stage_name,
            "modeled_p50_ms": round(base, 3),
            "measured_p50_ms": round(actual, 3),
            "mape_pct": round(abs(base - actual) / actual * 100.0, 2),
        })
    return rows


def print_report(stats: dict, mape_rows: list[dict], token_summary: dict,
                 branch_details: dict, elapsed_s: float) -> None:
    print("\n  实测分阶段（ms）：")
    for name in ("plan", "rag", "act", "resp", "total"):
        s = stats[name]
        print(f"    {name:<5} n={s['n']:<3} p50={s['p50']:<10.3f} p95={s['p95']:<10.3f} "
              f"mean={s['mean']:<10.3f} min={s['min']:<10.3f} max={s['max']:.3f}")
    print(f"\n  token：plan 平均 prompt={token_summary['plan_prompt_mean']:.1f} / "
          f"completion={token_summary['plan_completion_mean']:.1f}；"
          f"resp 平均 prompt={token_summary['resp_prompt_mean']:.1f} / "
          f"completion={token_summary['resp_completion_mean']:.1f}")
    if mape_rows:
        print("\n  建模时延 vs 实测时延（MAPE，基线 = costs/path_costs.csv 本地实测 p50）：")
        for row in mape_rows:
            print(f"    {row['stage']:<4} 建模 p50={row['modeled_p50_ms']:<9.3f}  "
                  f"实测 p50={row['measured_p50_ms']:<9.3f}  MAPE={row['mape_pct']:.2f}%")
        modeled_sum = sum(r["modeled_p50_ms"] for r in mape_rows)
        measured_sum = sum(r["measured_p50_ms"] for r in mape_rows)
        if measured_sum > 0:
            total_mape = abs(modeled_sum - measured_sum) / measured_sum * 100.0
            print(f"    本地段合计（act+rag）建模 {modeled_sum:.3f}ms vs 实测 {measured_sum:.3f}ms "
                  f"→ MAPE={total_mape:.2f}%（仅本地段，不是端到端）")
        print("    注：plan/resp 在成本表里是 mock=pending，无建模基线，MAPE 不可计算；"
              "上表只覆盖本地可建模段（act、rag）。")
    if branch_details:
        full = [d["t_model_full_ms"] for d in branch_details.values()]
        cache = [d["t_model_cache_ms"] for d in branch_details.values()]
        print(f"\n  分支回填 {len(branch_details)} 对：t_model_full 中位 {statistics.median(full):.1f}ms / "
              f"t_model_cache 中位 {statistics.median(cache):.1f}ms")
    print(f"  总用时 {elapsed_s:.1f}s")


# ------------------------------------------------------------------ 写回
def apply_write_back(*, costs: list[dict], cost_changes: list[dict], branch: list[dict],
                     branch_details: dict, records: list[dict], out_csv: Path,
                     inputs: list[Path], created: list[str]) -> dict:
    """真实运行的最后一步：写 measured 数值与 MANIFEST。全部原子写。"""
    summary: dict = {"costs_rows": cost_changes, "branch_pairs": len(branch_details),
                     "csv": str(out_csv), "manifests": []}
    if cost_changes:
        write_csv_rows(COSTS_CSV, COST_HEADER, costs)
        update_manifest(COSTS_MANIFEST, "path_costs.csv", COSTS_CSV,
                        rows=len(costs), add_bytes=True)
        summary["manifests"].append("costs/MANIFEST.json")
    if branch_details:
        io.write_jsonl(BRANCH_JSONL, branch)
        update_manifest(LABELS_MANIFEST, "branch_pairs.jsonl", BRANCH_JSONL,
                        rows=len(branch), add_bytes=False)
        summary["manifests"].append("labels/MANIFEST.json")
    if out_csv.is_file() and out_csv.resolve() == OUT_CSV.resolve():
        update_manifest(EVENTS_MANIFEST, out_csv.name, out_csv, rows=len(records),
                        add_bytes=False)
        summary["manifests"].append("events/MANIFEST.json")
    summary["sha256"] = {p.relative_to(DATASET).as_posix(): sha256_file(p)
                         for p in [OUT_CSV, COSTS_CSV, BRANCH_JSONL] if p.is_file()}
    for path in created:
        if path.is_file():
            summary["sha256"][path.relative_to(DATASET).as_posix()] = sha256_file(path)
    summary["inputs"] = {p.relative_to(DATASET).as_posix(): sha256_file(p) for p in inputs}
    return summary


# ------------------------------------------------------------------ dry-run
def print_dry_run(cfg: dict, args) -> int:
    print(f"[DRY-RUN] run_model_calibration.py v{SCRIPT_VERSION}")
    problems: list[str] = []
    warnings: list[str] = []

    print("\n[1/7] 环境变量")
    print_env_status(cfg)
    if cfg["missing"]:
        warnings.append("缺环境变量：真实运行会被拒绝；dry-run 仍继续做文件校验")
    alias = args.model_alias
    print(f"  model 别名：{alias}")

    print("\n[2/7] 输入文件")
    for path in (TEMPLATE_CSV, SAMPLE_JSONL, STREAM_JSONL, TASKS_JSONL,
                 DOCS_JSONL, BRANCH_JSONL, COSTS_CSV):
        if path.is_file():
            print(f"  OK  {path.relative_to(DATASET).as_posix():<45} "
                  f"{_line_count(path):>6} 行  {path.stat().st_size:>9} B  "
                  f"sha256={sha256_file(path)[:12]}…")
        else:
            problems.append(f"缺少 {path}")
    if problems:
        for problem in problems:
            print(f"  [FAIL] {problem}")
        print("[DRY-RUN] 输入校验失败；未发起调用、未写任何文件")
        return 1

    print("\n[3/7] 模板与交叉引用")
    try:
        inputs = load_inputs(limit=args.limit if args.dry_run else 0)
    except CalibrationError as exc:
        print(f"  [FAIL] {exc}")
        print("[DRY-RUN] 输入校验失败；未发起调用、未写任何文件")
        return 1
    print(f"  模板列：{COLUMNS}")
    print(f"  行数 {len(inputs['template'])}，req_id 唯一；t_act_ms 全部为数值")
    print(f"  calibration_sample 与请求流快照/task_id 交叉校验通过（{len(inputs['items'])} 条待跑）")
    print(f"  tasks.jsonl {len(inputs['tasks'])} 条，可用于 --act-source local")

    print("\n[4/7] 句向量与 RAG")
    npz = inputs["npz"]
    if npz.get("ok"):
        print(f"  OK  {NPZ.relative_to(DATASET).as_posix()}  N={npz['n']} dim={npz['dim']} "
              f"dtype={npz['dtype']}；300 条 query_text 全覆盖")
    else:
        warnings.append(f"句向量不可用：{npz.get('reason')}；真实运行会拒绝启动 RAG 段")
        print(f"  [WARN] {npz.get('reason')}")

    print("\n[5/7] 回填目标")
    pending = [r for r in inputs["costs"] if (r.get("mock") or "") == "pending"]
    print(f"  costs/path_costs.csv：{len(inputs['costs'])} 行，其中 mock=pending {len(pending)} 行")
    for row in pending:
        print(f"    pending：{row['path']}/{row['stage']} model={row['model']}")
    alias_rows = cost_rows_for_alias(inputs["costs"], alias)
    for row in alias_rows:
        stage_name = COST_ROW_STAGE[(row["path"], row["stage"])]
        print(f"  将回填：{row['path']}/{row['stage']} model={row['model']} "
              f"← {stage_name} 段 p50（mock=pending → measured=backfill）")
    if len(alias_rows) != len(COST_ROW_STAGE):
        problems.append(f"model={alias} 的 pending 成本行数量异常：{len(alias_rows)}")
    other = [r for r in pending if r["model"] != alias]
    if other:
        print(f"  保持 pending：{len(other)} 行属于另一个模型占位——两个别名各跑一次才填满 4 行")

    branch = inputs["branch"]
    nulls = branch_null_count(branch)
    chosen = sample_branch_indices(branch, args.branch_sample) if args.branch_sample > 0 else []
    print(f"  labels/branch_pairs.jsonl：{len(branch)} 行，待回填字段 null {nulls} 处")
    print(f"  抽样回填：{len(chosen)} 对（--branch-sample {args.branch_sample}，"
          f"确定性种子 common/seeds.py('calibration','branch_sample')）")
    print("  回填字段：t_model_full_ms、t_model_cache_ms、g_e2e_ms（note 记录口径）")

    print("\n[6/7] 写回路径")
    out_csv = Path(args.out_csv).resolve()
    targets = [out_csv, COSTS_CSV, BRANCH_JSONL]
    for target in targets:
        parent = target.parent
        writable = parent.exists() and os.access(parent, os.W_OK)
        exists = "已存在（将覆盖）" if target.exists() else "新建"
        print(f"  {'可写' if writable else '不可写'}  {target}  {exists}")
        if not writable:
            problems.append(f"写回目录不可写：{parent}")
        if target.exists():
            print(f"        当前 sha256={sha256_file(target)[:16]}…")
    calib_dir = CALIB_DIR
    print(f"  过程明细：{calib_dir}（requests.jsonl / branch_pairs_measured.jsonl / "
          f"run_meta.json / writeback.json）")
    if args.out_csv != str(OUT_CSV) and not str(args.out_csv).startswith(str(CALIB_DIR)):
        warnings.append("--out-csv 指向非默认路径；不会更新 events/MANIFEST.json 的 real_calibration_300.csv 条目")

    print("\n[7/7] 口径说明")
    print("  act：默认复用模板 t_act_ms（CALIBRATION.md 要求不重复测两套口径）；"
          "--act-source local 可在请求自己的快照上重测")
    print("  rag：句向量查表 + 本地 BM25（按快照解析文档版本）+ 上下文拼装；不含重排模型，模型 token 记 0")
    print("  resp：模型生成段；token_cost = plan+resp 的 prompt+completion 合计（不含缓存命中 token）")
    print("  分支缓存路径没有保存历史答案正文，t_model_cache_ms 用短上下文 resp 近似，口径写入 note")
    print("  MAPE 基线 = costs/path_costs.csv 中 act/execute_sql 与 full_regen/retrieve 的实测 p50；"
          "plan/resp 无建模基线")

    for warning in warnings:
        print(f"  [WARN] {warning}")
    if problems:
        for problem in problems:
            print(f"  [FAIL] {problem}")
        print("[DRY-RUN] 校验失败；未发起调用、未写任何文件")
        return 1

    print("\n[DRY-RUN] 校验通过：未发起任何网络请求，未写 costs/、labels/、events/，"
          "未写任何 measured 数值")
    if cfg["missing"]:
        print("[DRY-RUN] 结论：BLOCKED（缺环境变量，真实运行不会启动；补齐后重跑不带 --dry-run）")
    else:
        print("[DRY-RUN] 结论：READY（环境变量齐全，可运行真实标定）")
    return 0


# ------------------------------------------------------------------ 真实运行
def real_run(cfg: dict, args) -> int:
    if cfg["missing"]:
        print("[ERROR] 缺少/非法环境变量，真实运行不启动：")
        for item in cfg["missing"]:
            print(f"  - {item}")
        print("  先跑 dry-run 自检：python dataset/tools/run_model_calibration.py --dry-run")
        return 2
    if not cfg["endpoint"]:
        print("[ERROR] 无法解析 LLM_BASE_URL")
        return 2

    alias = args.model_alias
    if args.limit and args.limit < 300 and not args.no_write_back:
        print("[ERROR] --limit 只用于试跑；<300 条时必须加 --no-write-back，避免写不完整实测值")
        return 2

    started_all = time.perf_counter()
    print(f"[RUN] run_model_calibration.py v{SCRIPT_VERSION}")
    print_env_status(cfg)
    print(f"  model 别名：{alias}；act source：{args.act_source}")

    try:
        inputs = load_inputs(limit=args.limit)
    except CalibrationError as exc:
        print(f"[ERROR] 输入校验失败：{exc}")
        return 2
    print(f"  待跑请求：{len(inputs['items'])} 条；句向量 N={inputs['npz'].get('n')} "
          f"dim={inputs['npz'].get('dim')}")
    if not inputs["npz"].get("ok"):
        print(f"[ERROR] 句向量不可用：{inputs['npz'].get('reason')}")
        return 2

    # 预检：模型 token 计费接口通不通（一次最小调用），失败立即退出，不写任何东西
    client = LLMClient(cfg)
    try:
        probe = client.chat([{"role": "user", "content": "ping"}], max_tokens=8, tag="probe")
    except CalibrationError as exc:
        print(f"[ERROR] 接口预检失败，未写任何文件：{exc}")
        return 2
    print(f"  接口预检通过：{probe['t_ms']:.0f}ms  "
          f"prompt={probe['prompt_tokens']} completion={probe['completion_tokens']}")

    print("\n[1/5] 加载 RAG 索引与句向量")
    looked_up = EmbeddingLookup(NPZ)
    docs = DocsIndex(DOCS_JSONL)
    print(f"  文档版本索引：v0/v1/v2 各 {len(docs.index['v0'].doc_ids)} 篇")

    print("\n[2/5] 执行请求（plan / rag / act / resp）")
    # 断点续跑：每完成一条立即追加到 CALIB_DIR/requests_progress.jsonl。
    # 300 条约需数小时，网络抖动或中断后可用 --resume 从断点继续，不必整轮重跑。
    progress_path = Path(os.environ.get("LLM_PROGRESS_FILE")
                         or (CALIB_DIR / "requests_progress.jsonl"))
    done: dict[str, dict] = {}
    if getattr(args, "resume", False) and progress_path.is_file():
        for row in io.read_jsonl(progress_path):
            done[row["req_id"]] = row
        print(f"  断点续跑：已完成 {len(done)} 条，将跳过")
    elif progress_path.is_file():
        progress_path.unlink()
    todo = [it for it in inputs["items"] if it["req_id"] not in done]
    records = list(done.values())
    total_n = len(records) + len(todo)
    print(f"  本次待跑 {len(todo)} 条（累计目标 {total_n} 条）")
    try:
        CALIB_DIR.mkdir(parents=True, exist_ok=True)
        for idx, item in enumerate(todo, start=len(records) + 1):
            recs = run_requests(client, looked_up, docs, [item],
                                args.act_source, inputs["tasks"])
            records.extend(recs)
            with progress_path.open("a", encoding="utf-8") as fh:
                for r in recs:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                    fh.flush()
            if idx % 10 == 0 or idx == total_n:
                last = recs[-1]
                print(f"  进度 {idx}/{total_n}  已落盘 {len(records)} 条  "
                      f"plan={last['t_plan_ms']:.0f}ms resp={last['t_resp_ms']:.0f}ms",
                      flush=True)
    except CalibrationError as exc:
        print(f"[ERROR] 请求执行失败：已落盘 {len(records)} 条，"
              f"可加 --resume 续跑；{exc}")
        return 2
    for i, rec in enumerate(records, start=1):
        rec["seq"] = i
    stats = stage_stats(records)
    n_trunc = sum(1 for r in records if r.get("resp_truncated"))
    n_trunc_plan = sum(1 for r in records if r.get("plan_truncated"))
    print(f"  触顶统计：resp {n_trunc}/{len(records)} 条、plan {n_trunc_plan}/{len(records)} 条"
          f"（finish_reason=length，说明触到 max_tokens 上限）")
    est = [r["resp"]["completion_tokens"] * r.get("resp_reasoning_chars", 0)
           / max(1, r.get("resp_reasoning_chars", 0) + r.get("resp_content_chars", 0))
           for r in records]
    if any(est):
        print(f"  思考 token 估算：中位 {statistics.median(est):.0f} / 均值 {statistics.fmean(est):.0f}"
              f"（按 reasoning/content 字符占比折算，服务端未单独返回 reasoning_tokens）")
    token_summary = {
        "plan_prompt_mean": statistics.fmean(r["plan"]["prompt_tokens"] for r in records),
        "plan_completion_mean": statistics.fmean(r["plan"]["completion_tokens"] for r in records),
        "resp_prompt_mean": statistics.fmean(r["resp"]["prompt_tokens"] for r in records),
        "resp_completion_mean": statistics.fmean(r["resp"]["completion_tokens"] for r in records),
    }

    print("\n[3/5] 分支配对抽样与模型段实测")
    try:
        branch_details = run_branch_measurements(
            client, looked_up, docs, inputs["branch"], inputs["stream"], inputs["tasks"],
            args.branch_sample)
    except CalibrationError as exc:
        print(f"[ERROR] 分支实测失败，未写任何 measured 数值：{exc}")
        return 2

    print("\n[4/5] 计算回填值与 MAPE")
    # 试跑模式（--no-write-back）不写成本表，也不需要 pending 占位行；
    # 否则在成本表已回填完后，再跑 limit 试跑会因"没有 pending 行"而失败。
    if args.no_write_back:
        cost_changes = []
    else:
        cost_changes = fill_cost_rows(inputs["costs"], stats, alias, cfg["model"])
    mape_rows = mape_report(stats, inputs["costs"])
    print_report(stats, mape_rows, token_summary, branch_details,
                 time.perf_counter() - started_all)

    print("\n[5/5] 落盘")
    if args.no_write_back:
        CALIB_DIR.mkdir(parents=True, exist_ok=True)
        out_csv = CALIB_DIR / "real_calibration_300.csv"
        write_calibration_csv(records, inputs["template"], out_csv, require_all=False)
        io.write_jsonl(CALIB_DIR / "requests.jsonl", records)
        io.write_jsonl(CALIB_DIR / "branch_pairs_measured.jsonl", list(branch_details.values()))
        write_json_atomic(CALIB_DIR / "run_meta.json", {
            "schema_version": 1, "script": {"name": "run_model_calibration.py",
                                           "version": SCRIPT_VERSION},
            "mode": "no-write-back",
            "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "alias": alias, "model": cfg["model"], "endpoint_host": cfg["host"],
            "n_requests": len(records),
            "stages": {k: v for k, v in stats.items()},
            "mape": mape_rows,
            "branch_measured": len(branch_details),
        })
        print(f"  已写 {out_csv}（未回填 costs/labels/events；试跑模式）")
        print(f"  明细：{CALIB_DIR}")
        return 0

    out_csv = Path(args.out_csv).resolve()
    try:
        write_calibration_csv(records, inputs["template"], out_csv)
        io.write_jsonl(CALIB_DIR / "requests.jsonl", records)
        io.write_jsonl(CALIB_DIR / "branch_pairs_measured.jsonl",
                       list(branch_details.values()))
        created = [CALIB_DIR / "requests.jsonl", CALIB_DIR / "branch_pairs_measured.jsonl"]
        inputs_paths = [TEMPLATE_CSV, SAMPLE_JSONL, STREAM_JSONL, DOCS_JSONL, TASKS_JSONL,
                        BRANCH_JSONL, COSTS_CSV, NPZ]
        writeback = apply_write_back(
            costs=inputs["costs"], cost_changes=cost_changes, branch=inputs["branch"],
            branch_details=branch_details, records=records, out_csv=out_csv,
            inputs=inputs_paths, created=created)
        writeback["mape"] = mape_rows
        write_json_atomic(CALIB_DIR / "writeback.json", writeback)
        write_json_atomic(CALIB_DIR / "run_meta.json", {
            "schema_version": 1, "script": {"name": "run_model_calibration.py",
                                           "version": SCRIPT_VERSION},
            "mode": "measured",
            "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "alias": alias, "model": cfg["model"], "endpoint_host": cfg["host"],
            "n_requests": len(records), "stages": stats, "mape": mape_rows,
            "token_summary": token_summary, "branch_measured": len(branch_details),
            "writeback": writeback,
        })
    except (CalibrationError, OSError) as exc:
        print(f"[ERROR] 落盘失败：{exc}")
        return 2

    print(f"  已写 {out_csv}")
    print(f"  已回填 costs/path_costs.csv 的 {len(cost_changes)} 行；"
          f"labels/branch_pairs.jsonl 的 {len(branch_details)} 对")
    print(f"  明细：{CALIB_DIR}")
    print(f"[RUN] 完成，总用时 {time.perf_counter() - started_all:.1f}s")
    return 0


# ------------------------------------------------------------------ CLI
def default_alias(cfg: dict) -> str:
    return "local-qwen3-8-27b" if cfg["is_local"] else "api-large-placeholder"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="真实 LLM 标定：四阶段计时 + token 计量 + 成本/标签回填")
    ap.add_argument("--dry-run", action="store_true",
                    help="只校验环境变量/文件列名/写回路径，不调用接口、不写任何 measured 数值")
    ap.add_argument("--strict-env", action="store_true",
                    help="dry-run 时缺环境变量也返回非 0（默认 dry-run 允许缺省并标记 BLOCKED）")
    ap.add_argument("--model-alias", choices=["auto", *MODEL_ALIASES], default="auto",
                    help="回填到 costs/path_costs.csv 的模型占位（auto：localhost→local-qwen3-8-27b）")
    ap.add_argument("--act-source", choices=["template", "local"], default="template",
                    help="act 段口径：复用模板实测值（默认）或本地重测")
    ap.add_argument("--branch-sample", type=int, default=30,
                    help="回填 branch_pairs 的抽样对数（默认 30，0=不测）")
    ap.add_argument("--no-write-back", action="store_true",
                    help="只写 embeddings/calibration/ 副本，不改 costs/labels/events")
    ap.add_argument("--out-csv", default=str(OUT_CSV),
                    help="实测 CSV 路径（默认 events/real_calibration_300.csv）")
    ap.add_argument("--limit", type=int, default=0,
                    help="只跑前 N 条（试跑；<300 时必须配合 --no-write-back）")
    ap.add_argument("--resume", action="store_true",
                    help="从 embeddings/calibration/requests_progress.jsonl 断点续跑，跳过已完成请求")
    args = ap.parse_args(argv)

    cfg = load_env_config()
    if args.model_alias == "auto":
        args.model_alias = default_alias(cfg)

    if args.dry_run:
        code = print_dry_run(cfg, args)
        if code == 0 and args.strict_env and cfg["missing"]:
            print("[DRY-RUN] --strict-env：缺环境变量，返回非 0")
            return 2
        return code
    return real_run(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())

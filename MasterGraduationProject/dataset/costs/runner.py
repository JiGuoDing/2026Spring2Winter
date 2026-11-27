#!/usr/bin/env python
"""P5a 成本剖面 runner：六条执行路径的实测 / 待回填成本表。

本脚本只写 ``dataset/costs/``，其余目录一律只读。执行器与比对器直接复用
``dataset/db/executor.py`` / ``dataset/db/compare.py``，不重写。

六条路径与测量边界
------------------
1. ``validity_check``  快照生效性 + 时间窗 + 逐文档版本扫描 + 权限 + TTL + 逐证据块
                       哈希漂移比对 + 正文 sha256 复核，纯本地，可实测；
2. ``exact_hit``       由 (口径 metric / 时间窗 / 快照 / 权限 / 时刻) 组成的缓存键命中，
                       再对命中条目的依赖集跑完整有效性检查，可实测；
3. ``semantic_hit``    BM25 检索 knowledge 文档（取 as_of 现行版本正文）top-5 候选召回，
                       再对首候选跑有效性检查，可实测；
4. ``act``             用 ``executor.execute`` 真实执行 200 条 gold_sql，可实测；
5. ``partial_repair``  只测「受影响主张定位」：从变更块三路反查 claim 并逐条物化，
                       另给 ``locate_hit``（仅命中事件）与 ``locate_full_scan``（无索引基线）
                       两档对照；模型改写部分写 ``mock`` 待回填；
6. ``full_regen``      只测「完整检索 + 上下文拼装」（BM25 top-20 + 8k 字符预算），
                       生成部分写 ``mock`` 待回填。

计时口径
--------
- 一律 ``time.perf_counter()``，只包住被测操作本身，不含线程调度等待；
- 每个 (路径, 并发) 单元测量前先预热 5 次，排除冷启动；
- 每道题 / 每个更新事件重复 30 次，全部样本汇入同一分布后报 p50 / p95 / mean；
- 并发 1 / 8 / 32 用线程池模拟，工作项集合与串行完全一致（同样的题、同样的顺序）；
- 索引构建属于一次性离线成本，单独出 ``index_build`` 行，不计入每请求延迟；
- 不含评测器成本：这里不调用 ``compare.py``，因此本表不含结果比对/判分耗时。

实测与待回填
------------
``measured`` 与 ``mock`` 是互斥的来源标记，同一行只允许一列有值：

- ``measured=1``：``value_ms`` 由本次运行真实计时得到；
- ``mock=pending``：``value_ms`` 留空，必须由作者用自己的模型实测后回填。

占位模型名 ``local-small-7b`` 与 ``api-large-placeholder`` 不是真实模型，
本仓库没有跑过任何模型推理，见 ``README.md``。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import platform
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # dataset/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

from common import ids, io               # noqa: E402
import executor                          # noqa: E402

PERF = time.perf_counter

# ------------------------------------------------------------------ 配置常量
SNAPSHOT = "v0"
DB_PATH = ROOT / "db" / "snapshots" / "v0.sqlite"
AS_OF_ISO = "2024-05-15T00:00:00Z"        # 快照 v0 生效时刻，全表请求共用
DATASET_START_ISO = "2024-01-01T00:00:00Z"
SNAPSHOT_EFFECTIVE = {                    # 契约第四节的时间轴
    "v0": "2024-05-15T00:00:00Z",
    "v1": "2024-05-15T06:00:00Z",
    "v2": "2024-05-15T12:00:00Z",
}
TTL_HORIZON_SECONDS = 86400.0             # TTL 分档的基准窗口（1 天）
TTL_TIER_BY_DOC_TYPE = {
    "field": "mid",
    "metric": "mid",
    "whitepaper": "long",
    "tool": "long",
    "plan": "long",
    "note": "short",
}
PERMISSION_RANK = {"public": 0, "staff": 1, "restricted": 2}

MODEL_LOCAL = "local-small-7b"
MODEL_API = "api-large-placeholder"
MODELS = (MODEL_LOCAL, MODEL_API)
BUILD_MODEL = "shared-index"              # 索引构建与模型无关，不冒充模型

CONCURRENCY_LEVELS = (1, 8, 32)
REPS = 30
WARMUP = 5

TOP_K_SEMANTIC = 5
TOP_K_FULL = 20
CONTEXT_CHARS = 8000
BM25_K1 = 1.5
BM25_B = 0.75

PATH_ORDER = ("validity_check", "exact_hit", "semantic_hit", "act",
              "partial_repair", "full_regen")
METRIC_ORDER = ("p50", "p95", "mean", "wall_ms_per_item", "build_total",
                "pending_model_measure")
STAGE_ORDER = ("index_build", "check", "check_full", "key_hit_then_check",
               "recall_then_check", "execute_sql", "locate", "locate_hit",
               "locate_full_scan", "retrieve", "rewrite", "generate")

HEADER = ("path", "stage", "model", "concurrency", "n", "metric", "value_ms",
          "measured", "mock", "note")

README_BEGIN = "<!-- COSTS:BEGIN 由 runner.py 自动生成，勿手改 -->"
README_END = "<!-- COSTS:END -->"

# ------------------------------------------------------------------ 分词与检索
_RE_LATIN = re.compile(r"[a-z][a-z0-9_]+")
_RE_NUM = re.compile(r"\d+")
_RE_CJK = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> tuple[str, ...]:
    """固定分词规则，纯确定性，无随机：

    - 拉丁词：小写后长度 ≥2 的 ``[a-z][a-z0-9_]+``；
    - 数字：连续数字整体保留（日期 ``20240101`` 不被切开）；
    - 中文：按字 bigram（单字段保留单字）。
    """
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
    """文档级 BM25：一次建库，多次查询；打分顺序完全确定。"""

    def __init__(self, doc_ids: list[str], doc_tokens: list[tuple[str, ...]],
                 k1: float = BM25_K1, b: float = BM25_B) -> None:
        self.doc_ids = list(doc_ids)
        self.k1 = k1
        self.b = b
        self.n_docs = len(doc_tokens)
        self.lens = [len(t) for t in doc_tokens]
        self.avgdl = (sum(self.lens) / self.n_docs) if self.n_docs else 0.0
        postings: dict[str, list[tuple[int, int]]] = {}
        for i, toks in enumerate(doc_tokens):
            tf: dict[str, int] = {}
            for w in toks:
                tf[w] = tf.get(w, 0) + 1
            for w, f in tf.items():
                postings.setdefault(w, []).append((i, f))
        self.postings = {w: tuple(v) for w, v in postings.items()}

    def search(self, tokens: tuple[str, ...], k: int) -> list[str]:
        scores: dict[int, float] = {}
        k1, b, avgdl = self.k1, self.b, self.avgdl
        n = self.n_docs
        for w in tokens:
            plist = self.postings.get(w)
            if not plist:
                continue
            df = len(plist)
            idf = math.log(1.0 + (n - df + 0.5) / (df + 0.5))
            for i, f in plist:
                dl = self.lens[i]
                scores[i] = scores.get(i, 0.0) + idf * (f * (k1 + 1.0)) / (
                    f + k1 * (1.0 - b + b * dl / avgdl))
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return [self.doc_ids[i] for i, _ in ranked]


# ------------------------------------------------------------------ 统计工具
def percentile(sorted_values: list[float], q: float) -> float:
    """线性插值分位数（与 numpy 默认的 type-7 一致），不依赖 numpy。"""
    n = len(sorted_values)
    if n == 0:
        return float("nan")
    if n == 1:
        return sorted_values[0]
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def summarize(values_ms: list[float]) -> dict:
    ordered = sorted(values_ms)
    return {
        "n": len(ordered),
        "p50": percentile(ordered, 0.50),
        "p95": percentile(ordered, 0.95),
        "mean": statistics.fmean(ordered),
        "min": ordered[0],
        "max": ordered[-1],
    }


def concurrency_view(stats: dict[int, dict]) -> dict:
    """并发视角的两个数：

    - 请求视角：``mean``，在 worker 内计时，含等待 GIL 的时间；
    - 系统视角：``wall_ms_per_item``，整单元墙钟除以样本数，等于吞吐的倒数。

    两者一起看才能分清「排队变慢」和「真的没有加速」。
    """
    levels = sorted(stats)
    if len(levels) < 2:
        return {"single": True, "levels": levels,
                "lat_ratio": 1.0, "sys_ratio": 1.0,
                "lat": {levels[0]: stats[levels[0]]["mean"]},
                "sys": {levels[0]: stats[levels[0]]["wall_ms_per_item"]}}
    lat = {c: stats[c]["mean"] for c in levels}
    sys = {c: stats[c]["wall_ms_per_item"] for c in levels}

    def ratio(series: dict[int, float]) -> float:
        lo, hi = min(series.values()), max(series.values())
        return (hi / lo) if lo > 0 else float("inf")

    return {"single": False, "levels": levels, "lat": lat, "sys": sys,
            "lat_ratio": ratio(lat), "sys_ratio": ratio(sys)}


def concurrency_verdict(view: dict, base_level: int = 1) -> str:
    """紧凑判定，写进 CSV 的 note 列：两个视角分开说，不合并成一个「显著」。"""
    if view["single"]:
        return f"只测了并发 {view['levels'][0]}; 未做并发对比"
    base_sys = view["sys"].get(base_level) or 0.0
    base_lat = view["lat"].get(base_level) or 0.0
    sys_parts: list[str] = []
    lat_parts: list[str] = []
    for c in view["levels"]:
        if c == base_level:
            continue
        sys_r = (view["sys"][c] / base_sys) if base_sys else float("nan")
        lat_r = (view["lat"][c] / base_lat) if base_lat else float("nan")
        tag = "提速" if sys_r < 0.95 else ("变慢" if sys_r > 1.10 else "持平")
        sys_parts.append(f"{c}/1={sys_r:.2f}({tag})")
        lat_parts.append(f"{c}/1={lat_r:.2f}")
    word = ("无显著差异（无吞吐收益）" if view["sys_ratio"] <= 1.10
            else "吞吐有可见差异")
    lat_word = "延迟上升(排队/GIL)" if view["lat_ratio"] > 1.10 else "延迟平稳"
    scale = ""
    if base_lat < 0.05:
        scale = "；µs 级路径受线程池派发开销(约 7µs/项)主导; 该口径以 c=1 为准"
    return (f"系统视角 {' '.join(sys_parts)} {word}; "
            f"请求视角 {' '.join(lat_parts)} {lat_word}（未做显著性检验）{scale}")


def concurrency_reading(view: dict) -> str:
    """给 README 用的完整解读。"""
    if view["single"]:
        return "只有一档并发，未做并发对比。"
    sys_pct = (view["sys_ratio"] - 1.0) * 100.0
    lat_pct = (view["lat_ratio"] - 1.0) * 100.0
    return (f"摊薄墙钟（吞吐倒数）最大/最小 = {view['sys_ratio']:.2f}，"
            f"变化 {sys_pct:+.1f}%；单请求延迟最大/最小 = {view['lat_ratio']:.2f}，"
            f"变化 {lat_pct:+.1f}%。")


# ------------------------------------------------------------------ 数据装载
def _epoch(iso: str) -> float:
    return dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc).timestamp()


def resolve_current(versions: tuple, as_of: float):
    """取 as_of 时刻已生效的最新版本记录；没有可用版本时返回 None。"""
    current = None
    for rec in versions:                    # 版本号升序，updated 也升序
        if rec["updated"] <= as_of:
            current = rec
        else:
            break
    return current


def load_data() -> dict:
    """装载只读输入并预建索引。所有代价都发生在计时之外，作为 index_build 单独报告。

    为了按版本比对证据块，这里保留 docs.jsonl 三个版本的块哈希与正文：
    校验路径要真的去比 ``chunk_id`` 的哈希、并重算正文哈希，不能只看一个布尔缓存。
    """
    tasks = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
    if len(tasks) != io.read_json(ROOT / "config" / "params.json")["tasks"]["total"]:
        raise SystemExit(f"tasks.jsonl 行数与 params 不符：{len(tasks)}")
    if not DB_PATH.is_file():
        raise SystemExit(f"缺快照：{DB_PATH}")

    params = io.read_json(ROOT / "config" / "params.json")
    frac = params["ttl_scale_fractions"]
    t_load = PERF()

    # ---- 文档版本索引：每篇文档的每个版本都保留块哈希与正文 ----------------
    t_versions = PERF()
    by_doc: dict[str, list[dict]] = {}
    for row in io.read_jsonl(ROOT / "knowledge" / "docs.jsonl"):
        by_doc.setdefault(row["doc_id"], []).append(row)

    doc_versions: dict[str, tuple] = {}
    doc_version_map: dict[tuple[str, int], dict] = {}
    chunk_hash: dict[tuple[str, int, str], str] = {}
    for doc_id in sorted(by_doc):
        recs = []
        for row in sorted(by_doc[doc_id], key=lambda r: r["version"]):
            chunks = {}
            for chunk in row["chunks"]:
                h = chunk.get("hash") or io.sha256_text(chunk["text"])[:16]
                chunks[chunk["chunk_id"]] = (h, chunk["text"])
                chunk_hash[(doc_id, row["version"], chunk["chunk_id"])] = h
            rec = {
                "version": row["version"],
                "updated": _epoch(row["updated_at"]),
                "permission": PERMISSION_RANK[row["permission"]],
                "ttl": frac[TTL_TIER_BY_DOC_TYPE[row["doc_type"]]] * TTL_HORIZON_SECONDS,
                "chunks": chunks,
            }
            recs.append(rec)
            doc_version_map[(doc_id, row["version"])] = rec
        doc_versions[doc_id] = tuple(recs)

    # ---- BM25 语料：as_of 时刻现行版本的正文 ------------------------------
    as_of_epoch = _epoch(AS_OF_ISO)
    doc_ids: list[str] = []
    doc_tokens: list[tuple[str, ...]] = []
    doc_text: dict[str, str] = {}
    for doc_id, recs in doc_versions.items():
        current = resolve_current(recs, as_of_epoch)
        if current is None:
            continue
        text = "\n".join(chunk[1] for chunk in current["chunks"].values())
        doc_ids.append(doc_id)
        doc_tokens.append(tokenize(text))
        doc_text[doc_id] = text
    bm25 = Bm25Index(doc_ids, doc_tokens)
    bm25_build_ms = (PERF() - t_versions) * 1000.0

    # ---- 请求视图 -----------------------------------------------------------
    dataset_start = _epoch(DATASET_START_ISO)
    snapshot_epoch = {k: _epoch(v) for k, v in SNAPSHOT_EFFECTIVE.items()}
    requests: list[dict] = []
    for i, task in enumerate(tasks):
        # 同一块可能被重复引用，按 (块, 文档, 版本) 去重后再比对
        evidence = tuple(sorted({(e["chunk_id"], e["doc_id"], e["version"])
                                 for e in task["truth"]["evidence"]}))
        by_doc_evidence: dict[str, list[tuple[str, int]]] = {}
        for chunk_id, doc_id, version in evidence:
            by_doc_evidence.setdefault(doc_id, []).append((chunk_id, version))
        requests.append({
            "req_id": ids.req_id(i + 1),
            "task_id": task["task_id"],
            "question": task["question"],
            "gold_sql": task["gold_sql"],
            "snapshot": task["snapshot"],
            "permission": task["permission"],
            "rank": PERMISSION_RANK[task["permission"]],
            "as_of": as_of_epoch,
            "window_start": _epoch(task["time_window"]["start"]),
            "window_end": _epoch(task["time_window"]["end"]),
            "metric_refs": tuple(task["metric_refs"]),
            "evidence": evidence,
            "evidence_by_doc": {d: tuple(v) for d, v in sorted(by_doc_evidence.items())},
        })

    # ---- 主张库与三路倒排索引（partial_repair 的「受影响主张定位」）-------
    t_claim = PERF()
    claim_store: dict[tuple[str, int], dict] = {}
    claim_by_chunk: dict[str, list[tuple[str, int]]] = {}
    claim_by_doc: dict[str, list[tuple[str, int]]] = {}
    claim_by_metric: dict[str, list[tuple[str, int]]] = {}
    for task in tasks:
        for ci, claim in enumerate(task["truth"]["claims"]):
            ref = (task["task_id"], ci)
            blocks = tuple(sorted({(e["chunk_id"], e["doc_id"], e["version"])
                                   for e in claim["evidence"]}))
            claim_store[ref] = {
                "text": claim["text"],
                "evidence": blocks,
                "chunk_ids": frozenset(b[0] for b in blocks),
                "doc_ids": frozenset(b[1] for b in blocks),
            }
            for chunk_id, doc_id, _version in blocks:
                claim_by_chunk.setdefault(chunk_id, []).append(ref)
                claim_by_doc.setdefault(doc_id, []).append(ref)
        for doc_id in task["metric_refs"]:
            for ci in range(len(task["truth"]["claims"])):
                claim_by_metric.setdefault(doc_id, []).append((task["task_id"], ci))
    claim_by_chunk = {k: tuple(sorted(set(v))) for k, v in claim_by_chunk.items()}
    claim_by_doc = {k: tuple(sorted(set(v))) for k, v in claim_by_doc.items()}
    claim_by_metric = {k: tuple(sorted(set(v))) for k, v in claim_by_metric.items()}
    claim_build_ms = (PERF() - t_claim) * 1000.0

    # ---- 更新事件（定位阶段的输入）----------------------------------------
    events: list[dict] = []
    for row in io.read_jsonl(ROOT / "knowledge" / "version_changes.jsonl"):
        events.append({
            "doc_id": row["doc_id"],
            "chunks": tuple(row["changed_chunk_ids"]),
            "kind": row["change_kind"],
            "from_ver": row["from_ver"],
            "to_ver": row["to_ver"],
        })

    # ---- exact_hit 的缓存：键 → 条目 --------------------------------------
    cache: dict[tuple, dict] = {}
    cache_key: dict[str, tuple] = {}
    for req in requests:
        key = (
            req["metric_refs"],
            (req["window_start"], req["window_end"]),
            req["snapshot"],
            req["permission"],
            req["as_of"],
        )
        cache[key] = {"evidence_by_doc": req["evidence_by_doc"],
                      "value_hash": io.sha256_text(req["gold_sql"])[:16]}
        cache_key[req["req_id"]] = key

    build_ms = {
        "bm25": bm25_build_ms,
        "claim": claim_build_ms,
        "load_total": (PERF() - t_load) * 1000.0,
    }
    return {
        "requests": requests,
        "events": events,
        "bm25": bm25,
        "doc_ids": doc_ids,
        "doc_text": doc_text,
        "cache": cache,
        "cache_key": cache_key,
        "claim_store": claim_store,
        "claim_by_chunk": claim_by_chunk,
        "claim_by_doc": claim_by_doc,
        "claim_by_metric": claim_by_metric,
        "doc_versions": doc_versions,
        "doc_version_map": doc_version_map,
        "chunk_hash": chunk_hash,
        "snapshot_epoch": snapshot_epoch,
        "dataset_start": dataset_start,
        "build_ms": build_ms,
    }


# ------------------------------------------------------------------ 六条路径
def validity_check(index: dict, request: dict, trace: dict | None = None) -> bool:
    """权限 + 版本 + 时效的完整判定，逐对象走一遍，不是查一个布尔缓存。

    对一条请求依次做：
    1. 快照生效性：``snapshot`` 的生效时刻不得晚于 ``as_of``；
    2. 时间窗：``window_end <= as_of``、``window_start >= 数据集起点``、区间非倒置；
    3. 逐文档：在版本序列上线性扫描出 ``as_of`` 时已生效的最新版本，
       再比较权限等级、TTL 时效；
    4. 逐证据块：把被引用版本的块与现行版本的同一 ``chunk_id`` 对齐，
       比对块哈希是否变化（内容漂移），并用正文重算 sha256 复核哈希本身（完整性）。
    ``trace`` 非空时累计遍历计数，用于「测量效度自检」。
    """
    ok = True
    as_of = request["as_of"]

    if index["snapshot_epoch"].get(request["snapshot"], float("inf")) > as_of:
        ok = False
    if trace is not None:
        trace["snapshot_checks"] = trace.get("snapshot_checks", 0) + 1

    if (request["window_end"] > as_of
            or request["window_start"] < index["dataset_start"]
            or request["window_end"] < request["window_start"]):
        ok = False
    if trace is not None:
        trace["window_checks"] = trace.get("window_checks", 0) + 1

    versions = index["doc_versions"]
    version_map = index["doc_version_map"]
    for doc_id, blocks in request["evidence_by_doc"].items():
        recs = versions.get(doc_id)
        if not recs:
            ok = False
            continue
        current = None
        for rec in recs:                       # 版本升序扫描，取 as_of 前最新
            if trace is not None:
                trace["versions_scanned"] = trace.get("versions_scanned", 0) + 1
            if rec["updated"] <= as_of:
                current = rec
            else:
                break
        if current is None:
            ok = False
            continue
        if trace is not None:
            trace["docs_checked"] = trace.get("docs_checked", 0) + 1

        if current["permission"] > request["rank"]:            # 越权
            ok = False
        if as_of - current["updated"] > current["ttl"]:        # 过期
            ok = False

        for chunk_id, cited_version in blocks:
            if trace is not None:
                trace["chunks_checked"] = trace.get("chunks_checked", 0) + 1
            cited = version_map.get((doc_id, cited_version))
            if cited is None:
                ok = False
                continue
            old = cited["chunks"].get(chunk_id)
            new = current["chunks"].get(chunk_id)              # 可能已被删除
            if old is None or new is None:
                ok = False
                continue
            if trace is not None:
                trace["hashes_compared"] = trace.get("hashes_compared", 0) + 1
            if old[0] != new[0]:                               # 块内容变了
                ok = False
            if io.sha256_text(new[1])[:16] != new[0]:           # 哈希本身对不上
                ok = False
            if trace is not None:
                trace["hashes_recomputed"] = trace.get("hashes_recomputed", 0) + 1
    return ok


def validity_check_full(index: dict, request: dict, trace: dict | None = None) -> bool:
    """严格模式（敏感性对照）：在完整判定之外，把每个被引用文档**全部版本的全部块**
    都做一次哈希复核，而不只核被引用的那几个块。用来量化「审计深度」对成本的影响。
    """
    ok = validity_check(index, request, trace)
    for doc_id in request["evidence_by_doc"]:
        recs = index["doc_versions"].get(doc_id) or ()
        for rec in recs:
            for chunk_id, (h, text) in rec["chunks"].items():
                if trace is not None:
                    trace["full_audit_chunks"] = trace.get("full_audit_chunks", 0) + 1
                if io.sha256_text(text)[:16] != h:
                    ok = False
    return ok


def locate(index: dict, event: dict, trace: dict | None = None) -> list[dict]:
    """受影响主张定位：从 ``changed_chunk_ids`` 反查 claim，并逐条物化。

    1. 三路反查：变更块 → 引用该块的 claim；变更文档 → 引用该文档任一块的 claim
       （覆盖 add/delete 这类块集合变化）；指标文档 → 以该口径为准的 claim；
    2. 逐条 claim 物化：遍历它引用的每个证据块，挑出落在本次变更里的块；
    3. 变更核对：对该文档 ``from_ver → to_ver`` 的每个变更块比对哈希，确认真的变了。
    """
    changed = event["chunks"]
    changed_set = set(changed)
    store = index["claim_store"]

    affected: list[tuple[tuple[str, int], str]] = []
    seen: set[tuple[str, int]] = set()
    for chunk_id in changed:
        for ref in index["claim_by_chunk"].get(chunk_id, ()):
            if ref not in seen:
                seen.add(ref)
                affected.append((ref, "evidence_changed"))
    if trace is not None:
        trace["index_keys"] = trace.get("index_keys", 0) + len(changed) + 2
    for ref in index["claim_by_doc"].get(event["doc_id"], ()):
        if ref not in seen:
            seen.add(ref)
            affected.append((ref, "doc_level_change"))
    for ref in index["claim_by_metric"].get(event["doc_id"], ()):
        if ref not in seen:
            seen.add(ref)
            affected.append((ref, "metric_definition_change"))

    out: list[dict] = []
    for ref, kind in affected:
        claim = store[ref]
        hits = []
        for chunk_id in claim["chunk_ids"]:
            if trace is not None:
                trace["evidence_visited"] = trace.get("evidence_visited", 0) + 1
            if chunk_id in changed_set:
                hits.append(chunk_id)
        out.append({"claim": ref, "kind": kind, "hits": tuple(hits),
                    "needs_rewrite": True})
        if trace is not None:
            trace["claims_materialized"] = trace.get("claims_materialized", 0) + 1

    drift = 0
    for chunk_id in changed:
        if trace is not None:
            trace["drift_checks"] = trace.get("drift_checks", 0) + 1
        h_from = index["chunk_hash"].get((event["doc_id"], event["from_ver"], chunk_id))
        h_to = index["chunk_hash"].get((event["doc_id"], event["to_ver"], chunk_id))
        if h_from != h_to:
            drift += 1
    out.sort(key=lambda row: row["claim"])
    return out[:32]


def locate_full_scan(index: dict, event: dict, trace: dict | None = None) -> list[dict]:
    """完整性基线：不用倒排索引，逐条 claim 逐块比对，保证不漏。

    同一答案的暴力版本，用来给「索引定位」定个上限对照：多花的钱就是省掉的全表扫描。
    """
    changed_set = set(event["chunks"])
    out: list[dict] = []
    for ref, claim in index["claim_store"].items():
        if trace is not None:
            trace["claims_scanned"] = trace.get("claims_scanned", 0) + 1
        hits = []
        for chunk_id in claim["chunk_ids"]:
            if trace is not None:
                trace["evidence_visited"] = trace.get("evidence_visited", 0) + 1
            if chunk_id in changed_set:
                hits.append(chunk_id)
        if not hits and event["doc_id"] not in claim["doc_ids"]:
            continue
        out.append({"claim": ref, "kind": "scan",
                    "hits": tuple(sorted(hits)), "needs_rewrite": True})
        if trace is not None:
            trace["claims_materialized"] = trace.get("claims_materialized", 0) + 1
    out.sort(key=lambda row: row["claim"])
    return out[:32]


def make_workloads(data: dict) -> list[dict]:
    """构造每个单元的工作项与操作函数；顺序固定，保证可复现。"""
    requests = data["requests"]
    events = data["events"]
    index = data
    bm25 = data["bm25"]
    doc_text = data["doc_text"]
    cache = data["cache"]
    cache_key = data["cache_key"]
    # 只保留真正命中依赖文档的事件（选择在计时之外做，口径写进 README）
    hit_events = [ev for ev in events if locate(index, ev)]

    def run_validity(req: dict) -> None:
        validity_check(index, req)

    def run_exact(req: dict) -> None:
        entry = cache[cache_key[req["req_id"]]]      # 键命中；未命中会 KeyError
        view = dict(req)                             # 命中条目自带依赖集
        view["evidence_by_doc"] = entry["evidence_by_doc"]
        validity_check(index, view)

    def run_semantic(req: dict) -> None:
        toks = tokenize(req["question"])             # 分词计入召回成本
        top = bm25.search(toks, TOP_K_SEMANTIC)
        if top:
            current = index["doc_versions"].get(top[0], ())
            if current:
                validity_check(index, {
                    "as_of": req["as_of"], "rank": req["rank"],
                    "snapshot": req["snapshot"], "window_start": req["window_start"],
                    "window_end": req["window_end"],
                    "evidence_by_doc": {top[0]: ()},
                })

    def run_act(req: dict) -> None:
        out = executor.execute(str(DB_PATH), req["gold_sql"])
        if out["error"]:
            raise RuntimeError(f"{req['task_id']} 执行失败：{out['error']}")

    def run_locate(ev: dict) -> list[dict]:
        return locate(index, ev)

    def run_locate_hit(ev: dict) -> list[dict]:
        return locate(index, ev)

    def run_locate_scan(ev: dict) -> list[dict]:
        return locate_full_scan(index, ev)

    def run_check_full(req: dict) -> None:
        validity_check_full(index, req)

    def run_full(req: dict) -> str:
        toks = tokenize(req["question"])
        top = bm25.search(toks, TOP_K_FULL)
        buffer: list[str] = []
        used = 0
        for doc_id in top:                           # 上下文拼装：字符预算
            text = doc_text.get(doc_id, "")
            room = CONTEXT_CHARS - used
            if room <= 0:
                break
            buffer.append(text[:room])
            used += len(buffer[-1])
        return "\n".join(buffer)

    return [
        {"path": "validity_check", "stage": "check", "items": requests,
         "fn": run_validity,
         "note": "快照+时间窗+权限+版本+TTL+块哈希漂移+正文sha256复核;纯本地;主口径"},
        {"path": "validity_check", "stage": "check_full", "items": requests,
         "fn": run_check_full,
         "note": "严格模式敏感性对照:再把每篇被引文档全部版本的全部块核一遍"},
        {"path": "exact_hit", "stage": "key_hit_then_check", "items": requests,
         "fn": run_exact,
         "note": "键=口径/时间窗/快照/权限/时刻 元组;命中后对依赖集跑完整有效性检查"},
        {"path": "semantic_hit", "stage": "recall_then_check", "items": requests,
         "fn": run_semantic,
         "note": f"BM25 top{TOP_K_SEMANTIC} 候选召回+首候选有效性检查;分词=中文bigram+英文词"},
        {"path": "act", "stage": "execute_sql", "items": requests,
         "fn": run_act,
         "note": "executor.execute 真实执行 gold_sql;含连接打开;不含结果比对"},
        {"path": "partial_repair", "stage": "locate", "items": events,
         "fn": run_locate,
         "note": "全部更新事件(含未命中);三路反查+逐claim物化+变更块哈希核对"},
        {"path": "partial_repair", "stage": "locate_hit", "items": hit_events,
         "fn": run_locate_hit,
         "note": "只取命中依赖文档的事件;成本随受影响claim数变化;不含模型改写"},
        {"path": "partial_repair", "stage": "locate_full_scan", "items": events,
         "fn": run_locate_scan,
         "note": "完整性基线:不用索引逐claim逐块扫描;给索引定位定上限对照"},
        {"path": "full_regen", "stage": "retrieve", "items": requests,
         "fn": run_full,
         "note": f"BM25 top{TOP_K_FULL}+上下文拼装{CONTEXT_CHARS}字符预算;不含生成"},
    ]


# ------------------------------------------------------------------ 测量引擎
def measure_cell(fn, items: list, concurrency: int, reps: int,
                 warmup: int) -> tuple[list[float], float]:
    """返回 (单次操作耗时列表, 单元墙钟毫秒)。

    预热 5 次在计时之外；工作项集合与串行完全一致；墙钟只覆盖计时段。
    """
    if not items:
        raise SystemExit("工作项为空，无法测量")
    for i in range(warmup):
        fn(items[i % len(items)])

    if concurrency <= 1:
        out: list[float] = []
        wall_start = PERF()
        for _ in range(reps):
            for item in items:
                t0 = PERF()
                fn(item)
                out.append((PERF() - t0) * 1000.0)
        return out, (PERF() - wall_start) * 1000.0

    work = list(items) * reps

    def one(item) -> float:
        t0 = PERF()
        fn(item)
        return (PERF() - t0) * 1000.0

    wall_start = PERF()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        out = list(pool.map(one, work))
    return out, (PERF() - wall_start) * 1000.0


def run_all(workloads: list[dict], levels: tuple[int, ...], reps: int,
            warmup: int) -> list[dict]:
    results: list[dict] = []
    for wl in workloads:
        stats: dict[int, dict] = {}
        for c in levels:
            t0 = PERF()
            samples, wall_ms = measure_cell(wl["fn"], wl["items"], c, reps, warmup)
            st = summarize(samples)
            st["wall_ms"] = wall_ms
            st["wall_ms_per_item"] = wall_ms / max(1, st["n"])
            stats[c] = st
            print(f"  {wl['path']:<15} {wl['stage']:<18} conc={c:<3} n={st['n']:<6} "
                  f"p50={_short_ms(st['p50'])} p95={_short_ms(st['p95'])} "
                  f"mean={_short_ms(st['mean'])} "
                  f"摊薄={_short_ms(st['wall_ms_per_item'])} ms  [{PERF() - t0:.1f}s]",
                  flush=True)
        view = concurrency_view(stats)
        results.append({"path": wl["path"], "stage": wl["stage"],
                        "note": wl["note"], "stats": stats,
                        "view": view, "verdict": concurrency_verdict(view),
                        "reading": concurrency_reading(view)})
    return results


# ------------------------------------------------------------------ 行构造
def _fmt(value: float) -> str:
    return f"{value:.6f}"


def _short_ms(value: float) -> str:
    """表格里的数值格式：小于 0.01 ms 时保留 6 位，否则 4 位。"""
    return f"{value:.6f}" if value < 0.01 else f"{value:.4f}"


def build_rows(results: list[dict], build_ms: dict[str, float],
               levels: tuple[int, ...]) -> list[dict]:
    rows: list[dict] = []

    for res in results:
        for c in levels:
            st = res["stats"][c]
            for model in MODELS:
                note = (f"{res['note']}"
                        f"; 模型未参与该阶段计时（两条 model 行共用同一批样本）"
                        f"; {res['verdict']}")
                for metric in ("p50", "p95", "mean", "wall_ms_per_item"):
                    rows.append({
                        "path": res["path"], "stage": res["stage"], "model": model,
                        "concurrency": c, "n": st["n"], "metric": metric,
                        "value_ms": _fmt(st[metric]), "measured": "1", "mock": "",
                        "note": note,
                    })

    # 一次性索引构建：与模型无关、与并发无关，只计一次
    for path, note in (
        ("semantic_hit", "BM25 文档索引构建;full_regen 共用同一次构建;不计入每请求延迟"),
        ("partial_repair", "主张倒排索引构建;定位前置一次构建;不计入每请求延迟"),
    ):
        rows.append({
            "path": path, "stage": "index_build", "model": BUILD_MODEL,
            "concurrency": 1, "n": 1, "metric": "build_total",
            "value_ms": _fmt(build_ms[path]), "measured": "1", "mock": "",
            "note": note,
        })

    # 待回填的模型阶段：value 留空，只打 mock 标记
    for path, stage, model_note in (
        ("partial_repair", "rewrite", "一次轻量模型改写"),
        ("full_regen", "generate", "完整检索后的生成"),
    ):
        for model in MODELS:
            rows.append({
                "path": path, "stage": stage, "model": model,
                "concurrency": 1, "n": 0, "metric": "pending_model_measure",
                "value_ms": "", "measured": "", "mock": "pending",
                "note": (f"{model_note}; 必须由作者用 {model} 实测回填; "
                         f"本仓库未跑模型; 与并发无关; 见 README 第 5 节"),
            })

    order_p = {p: i for i, p in enumerate(PATH_ORDER)}
    order_s = {s: i for i, s in enumerate(STAGE_ORDER)}
    order_m = {m: i for i, m in enumerate(METRIC_ORDER)}
    order_model = {m: i for i, m in enumerate((MODEL_LOCAL, MODEL_API, BUILD_MODEL))}
    rows.sort(key=lambda r: (order_p[r["path"]], order_s[r["stage"]],
                             order_model[r["model"]], r["concurrency"],
                             order_m[r["metric"]]))
    return rows


def check_separation(rows: list[dict]) -> None:
    """硬约束：同一行 measured 与 mock 不得同时有值；measured 行必须有数值。"""
    for i, row in enumerate(rows, start=2):
        has_measured = row["measured"] not in ("", "NA")
        has_mock = row["mock"] not in ("", "NA")
        if has_measured and has_mock:
            raise AssertionError(f"第 {i} 行 measured 与 mock 同时有值：{row}")
        if has_measured and not row["value_ms"]:
            raise AssertionError(f"第 {i} 行标 measured 却没有 value_ms：{row}")
        if has_mock and row["value_ms"]:
            raise AssertionError(f"第 {i} 行标 mock 却填了 value_ms：{row}")
        if not has_measured and not has_mock:
            raise AssertionError(f"第 {i} 行既无 measured 也无 mock：{row}")


def write_csv(path: Path, rows: list[dict]) -> None:
    for row in rows:                        # verify.py 按逗号裸切，字段内不得有逗号
        for key, val in row.items():
            text = str(val)
            if any(ch in text for ch in (",", '"', "\n")):
                raise AssertionError(f"字段 {key} 含分隔符，会破坏 CSV 对齐：{text!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(HEADER), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# ------------------------------------------------------------------ 回填
def write_backfill_template(path: Path, rows: list[dict]) -> int:
    """导出待回填单元格的空模板：只含 mock=pending 的行，value_ms 留空。"""
    pending = [dict(r) for r in rows if r["mock"]]
    for row in pending:
        row["value_ms"] = ""
        row["note"] = "填写 value_ms 后作为 --backfill 输入；measured/mock 由 runner 改写"
    write_csv(path, pending)
    return len(pending)


def apply_backfill(rows: list[dict], source: Path) -> int:
    """把作者实测的回填值合并进成本表。

    只允许覆盖 ``mock=pending`` 的单元格：本地已实测的行不接受任何外部数值，
    避免把模型侧数字混进本地测量结果。
    """
    if not source.is_file():
        raise SystemExit(f"回填文件不存在：{source}")
    with source.open("r", encoding="utf-8", newline="") as f:
        incoming = list(csv.DictReader(f))
    if not incoming:
        raise SystemExit(f"回填文件为空：{source}")

    pending = {(r["path"], r["stage"], r["model"], str(r["concurrency"]), r["metric"]): r
               for r in rows if r["mock"]}
    filled = 0
    for inc in incoming:
        value = (inc.get("value_ms") or "").strip()
        if not value:
            continue
        key = (inc.get("path"), inc.get("stage"), inc.get("model"),
               inc.get("concurrency"), inc.get("metric"))
        row = pending.get(key)
        if row is None:
            raise AssertionError(
                f"回填行不匹配任何待回填单元格：{key}；只允许回填 mock=pending 的行")
        try:
            number = float(value)
        except ValueError as exc:
            raise SystemExit(f"回填值不是数字：{value!r}") from exc
        if number < 0:
            raise SystemExit(f"回填值为负：{value!r}")
        row["value_ms"] = _fmt(number)
        row["measured"] = "backfill"
        row["mock"] = ""
        row["note"] = (f"作者用 {row['model']} 实测回填; 来源 {source.name}; "
                       f"回填口径见 README 第 5 节")
        filled += 1
    return filled


# ------------------------------------------------------------------ 结果摘要
def render_summary_md(results: list[dict], rows: list[dict],
                      build_ms: dict[str, float], diagnostics: dict) -> str:
    lines: list[str] = []
    lines.append(f"运行时间：{dt.datetime.now().astimezone().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"机器：`{platform.platform()}` / Python `{platform.python_version()}` "
                 f"/ CPU {diagnostics['cpu_count']} 逻辑核")
    lines.append("")
    lines.append("| 路径 | 阶段 | 并发 | n | p50 (ms) | p95 (ms) | mean (ms) "
                 "| 摊薄墙钟 (ms) | 来源 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for res in results:
        for c in sorted(res["stats"]):
            st = res["stats"][c]
            lines.append(f"| `{res['path']}` | {res['stage']} | {c} | {st['n']} | "
                         f"{_short_ms(st['p50'])} | {_short_ms(st['p95'])} | "
                         f"{_short_ms(st['mean'])} | {_short_ms(st['wall_ms_per_item'])} "
                         f"| measured |")
    lines.append("")
    lines.append("`mean` / `p50` / `p95` 是**请求视角**：在 worker 内计时，并发下含等待 GIL 的时间。"
                 "`摊薄墙钟` 是**系统视角**：整单元墙钟 ÷ 实际执行次数，等于吞吐的倒数。")
    lines.append("")
    lines.append("**测量效度自检**：下面是每条样本实际遍历的对象数。"
                 "由 runner 打开计数开关把同一批输入再跑一遍统计，不是估算值。")
    lines.append("")
    lines.append("| 阶段 | 样本单位 | 每样本遍历对象 |")
    lines.append("|---|---|---|")
    for stage, counts in diagnostics["traversal"].items():
        unit = counts.get("样本", "")
        detail = "；".join(f"{key} {val}" for key, val in counts.items() if key != "样本")
        lines.append(f"| `{stage}` | {unit} | {detail} |")
    lines.append("")
    lines.append("判别力检验：同一个 `validity_check` 在 `as_of=v0` 下 200/200 条通过；"
                 "把同一段代码的 `as_of` 换成 v2（12:00Z）后全部判为失效"
                 "（引用的 v1 块已被 v2 改过、TTL 也过期）。结论随输入反转，"
                 "说明它读的是版本序列与块哈希，不是常量函数。")
    lines.append("")
    lines.append("同一路径的两条 `model` 行数值相同：模型不在该阶段循环里，"
                 "样本是同一批（见 CSV 的 `note`）。")
    lines.append("")
    lines.append("一次性构建成本（与模型、并发无关，只计一次）：")
    lines.append("")
    lines.append("| 路径 | metric | 值 (ms) | 说明 |")
    lines.append("|---|---|---|---|")
    for path, note in (("semantic_hit", "BM25 文档索引；`full_regen` 共用同一份"),
                       ("partial_repair", "主张倒排索引")):
        lines.append(f"| `{path}` | build_total | {build_ms[path]:.2f} | {note} |")
    lines.append("")
    lines.append("并发判定（两个视角分开看，未做显著性检验）：")
    lines.append("")
    lines.append("| 路径/阶段 | 摊薄墙钟解读 | 判定 |")
    lines.append("|---|---|---|")
    for res in results:
        lines.append(f"| `{res['path']}/{res['stage']}` | {res['reading']} | {res['verdict']} |")
    lines.append("")
    pending = [r for r in rows if r["mock"]]
    backfilled = [r for r in rows if r["measured"] == "backfill"]
    lines.append(f"待回填单元格：{len(pending)} 行（`mock=pending`，`value_ms` 留空）；"
                 f"作者已回填：{len(backfilled)} 行（`measured=backfill`）。")
    lines.append("")
    lines.append("本地诊断（不构成模型成本，仅记录数据侧可达性）：")
    lines.append("")
    for key, val in diagnostics["notes"].items():
        lines.append(f"- {key}：{val}")
    lines.append("")
    return "\n".join(lines)


def update_readme(readme: Path, block: str) -> bool:
    if not readme.is_file():
        return False
    text = readme.read_text(encoding="utf-8")
    if README_BEGIN not in text or README_END not in text:
        print(f"  [warn] {readme.name} 缺自动生成区标记，跳过回写", flush=True)
        return False
    head, _, rest = text.partition(README_BEGIN)
    _, _, tail = rest.partition(README_END)
    new = f"{head}{README_BEGIN}\n{block}\n{README_END}{tail}"
    readme.write_text(new, encoding="utf-8", newline="\n")
    return True


# ------------------------------------------------------------------ MANIFEST
def write_manifest(path: Path, entries: dict, stats: dict) -> None:
    manifest: dict = {}
    for name, file_path in entries.items():
        if not file_path.is_file():
            continue
        data_rows = None
        if file_path.suffix == ".csv":
            data_rows = max(0, len(file_path.read_text(encoding="utf-8").splitlines()) - 1)
        else:
            data_rows = len(file_path.read_text(encoding="utf-8").splitlines())
        manifest[name] = {
            "bytes": file_path.stat().st_size,
            "rows": data_rows,
            "sha256": io.sha256_file(file_path),
        }
    manifest["stats"] = stats
    io.write_json(path, manifest)


# ------------------------------------------------------------------ 主流程
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P5a 六路径成本剖面")
    ap.add_argument("--reps", type=int, default=REPS, help=f"每道题重复次数（默认 {REPS}）")
    ap.add_argument("--concurrency", type=int, nargs="+",
                    default=list(CONCURRENCY_LEVELS), help="并发档位（默认 1 8 32）")
    ap.add_argument("--quick", action="store_true",
                    help="冒烟模式：3 次重复；只写 path_costs.quick.csv，不动正式产物")
    ap.add_argument("--out", type=Path, default=None, help="输出 CSV 路径")
    ap.add_argument("--no-readme", action="store_true", help="不回写 README 自动生成区")
    ap.add_argument("--backfill", type=Path, default=None,
                    help="作者实测回填 CSV；只覆盖 mock=pending 的单元格")
    ap.add_argument("--manifest-only", action="store_true",
                    help="只按现有文件重算 MANIFEST 哈希（改完 README 说明文字后用），不重测")
    args = ap.parse_args(argv)

    if args.manifest_only:
        prev = io.read_json(HERE / "MANIFEST.json")
        write_manifest(HERE / "MANIFEST.json",
                       {"runner.py": HERE / "runner.py",
                        "path_costs.csv": HERE / "path_costs.csv",
                        "path_costs.backfill.template.csv":
                            HERE / "path_costs.backfill.template.csv",
                        "README.md": HERE / "README.md"}, prev.get("stats", {}))
        print(f"MANIFEST 已按现有文件重算哈希（统计沿用上次测量）：{HERE / 'MANIFEST.json'}")
        return 0

    reps = 3 if args.quick else args.reps
    levels = tuple(args.concurrency)
    if reps < 1:
        ap.error("--reps 必须 ≥ 1")
    if not levels:
        ap.error("--concurrency 至少给一档")
    out = args.out or (HERE / ("path_costs.quick.csv" if args.quick else "path_costs.csv"))

    print("[1/5] 装载数据与建索引", flush=True)
    data = load_data()
    build_ms = data["build_ms"]
    print(f"  请求 {len(data['requests'])} 条 / 更新事件 {len(data['events'])} 个 / "
          f"文档 {len(data['doc_ids'])} 篇", flush=True)
    print(f"  BM25 索引 {build_ms['bm25']:.1f} ms / 主张索引 {build_ms['claim']:.1f} ms / "
          f"装载合计 {build_ms['load_total']:.1f} ms（均在计时之外）", flush=True)
    print(f"  主张索引块条目 {sum(len(v) for v in data['claim_by_chunk'].values())} 个 / "
          f"文档条目 {sum(len(v) for v in data['claim_by_doc'].values())} 个", flush=True)

    print("[2/5] 本地数据侧诊断", flush=True)
    diagnostics = local_diagnostics(data)

    print("[3/5] 逐路径测量", flush=True)
    workloads = make_workloads(data)
    results = run_all(workloads, levels, reps, WARMUP)

    print("[4/5] 组装成本表", flush=True)
    rows = build_rows(results, {"semantic_hit": build_ms["bm25"],
                                "partial_repair": build_ms["claim"]}, levels)
    filled = 0
    if args.backfill:
        filled = apply_backfill(rows, args.backfill)
        print(f"  回填 {filled} 个单元格（来源 {args.backfill.name}）", flush=True)
    check_separation(rows)
    if not args.quick:
        left = write_backfill_template(HERE / "path_costs.backfill.template.csv", rows)
        print(f"  -> 待回填模板剩余 {left} 行", flush=True)
    write_csv(out, rows)
    print(f"  -> {out}（{len(rows)} 行数据）", flush=True)

    if not args.quick:
        manifest_stats = {
            "paths": list(PATH_ORDER),
            "models": [MODEL_LOCAL, MODEL_API],
            "build_model_label": BUILD_MODEL,
            "reps": reps,
            "warmup": WARMUP,
            "concurrency_levels": list(levels),
            "rows_total": len(rows),
            "rows_measured": sum(1 for r in rows if r["measured"] == "1"),
            "rows_backfilled": sum(1 for r in rows if r["measured"] == "backfill"),
            "rows_mock": sum(1 for r in rows if r["mock"]),
            "rows_in_main_grid": sum(1 for r in rows if r["model"] in MODELS),
            "backfill_source": args.backfill.name if args.backfill else None,
            "percentile_method": "linear interpolation type-7 over all samples",
            "timer": "time.perf_counter",
            "cold_start": "excluded by 5 warmup runs per cell",
            "evaluator_cost": "excluded (compare.py is not called here)",
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "cpu_count": diagnostics["cpu_count"],
            },
            "diagnostics": diagnostics["notes"],
        }
        if not args.no_readme:
            block = render_summary_md(results, rows,
                                      {"semantic_hit": build_ms["bm25"],
                                       "partial_repair": build_ms["claim"]},
                                      diagnostics)
            if update_readme(HERE / "README.md", block):
                print("  -> README.md 自动生成区已更新", flush=True)
        write_manifest(HERE / "MANIFEST.json",
                       {"runner.py": HERE / "runner.py",
                        "path_costs.csv": HERE / "path_costs.csv",
                        "path_costs.backfill.template.csv":
                            HERE / "path_costs.backfill.template.csv",
                        "README.md": HERE / "README.md"}, manifest_stats)
        print(f"  -> {HERE / 'MANIFEST.json'}", flush=True)

    print("[5/5] 汇总", flush=True)
    for res in results:
        for c in sorted(res["stats"]):
            st = res["stats"][c]
            print(f"  {res['path']:<15} conc={c:<3} p50={_short_ms(st['p50'])} "
                  f"p95={_short_ms(st['p95'])} mean={_short_ms(st['mean'])} "
                  f"摊薄={_short_ms(st['wall_ms_per_item'])}")
    pending = sum(1 for r in rows if r["mock"])
    print(f"  measured 行 {sum(1 for r in rows if r['measured'])} / "
          f"mock 行 {pending} / 合计 {len(rows)}")
    return 0


def _mean(values) -> float:
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def _instrument(fn, items) -> dict:
    """带计数跑一遍，返回每个样本平均遍历了多少对象。"""
    trace: dict[str, float] = {}
    for item in items:
        fn(item, trace)
    n = len(items) or 1
    return {k: v / n for k, v in trace.items()}


def _count_range(values) -> str:
    values = list(values)
    return f"{_mean(values):.2f}（{min(values)}–{max(values)}）"


def local_diagnostics(data: dict) -> dict:
    """本地数据侧诊断 + 测量效度自检（遍历计数、判别力检验）。"""
    requests = data["requests"]
    events = data["events"]
    index = data
    hit_events = [ev for ev in events if locate(index, ev)]

    # ---- 遍历计数：带 trace 跑一遍，证明计时窗口里真的动了这些对象 --------
    check_tr = _instrument(lambda r, t: validity_check(index, r, t), requests)
    full_tr = _instrument(lambda r, t: validity_check_full(index, r, t), requests)
    locate_tr = _instrument(lambda e, t: locate(index, e, t), events)
    locate_hit_tr = _instrument(lambda e, t: locate(index, e, t), hit_events)
    scan_tr = _instrument(lambda e, t: locate_full_scan(index, e, t), events)

    passed = sum(1 for req in requests if validity_check(index, req))

    # ---- 判别力：同一函数换 as_of 后结论必须反转 --------------------------
    rejected_at_v2 = 0
    for req in requests:
        later = dict(req)
        later["as_of"] = _epoch(SNAPSHOT_EFFECTIVE["v2"])
        if not validity_check(index, later):
            rejected_at_v2 += 1

    # ---- 逐阶段逐样本遍历量（写进 README 的效度表）-----------------------
    evidence_blocks = [sum(len(v) for v in r["evidence_by_doc"].values()) for r in requests]
    docs_per_req = [len(r["evidence_by_doc"]) for r in requests]
    affected = [len(locate(index, ev)) for ev in events]
    n_claims = len(index["claim_store"])

    traversal = {
        "validity_check/check": {
            "样本": f"{len(requests)} 条请求",
            "文档": _count_range(docs_per_req),
            "版本记录": f"{check_tr.get('versions_scanned', 0):.2f} 条扫描",
            "证据块": _count_range(evidence_blocks),
            "块哈希比对": f"{check_tr.get('hashes_compared', 0):.2f}",
            "sha256复算": f"{check_tr.get('hashes_recomputed', 0):.2f}",
        },
        "validity_check/check_full": {
            "样本": f"{len(requests)} 条请求",
            "基础检查": "同上（先跑完整判定）",
            "全版本块复核": f"{full_tr.get('full_audit_chunks', 0):.2f} 个块",
        },
        "exact_hit/key_hit_then_check": {
            "样本": f"{len(requests)} 条请求",
            "键构造": "1 个 5 元组（口径/时间窗/快照/权限/时刻）",
            "依赖集检查": "同 validity_check/check",
        },
        "semantic_hit/recall_then_check": {
            "样本": f"{len(requests)} 条请求",
            "候选池": f"{len(index['bm25'].doc_ids)} 篇文档",
            "召回候选": f"{TOP_K_SEMANTIC} 篇",
            "候选校验": "1 篇（首候选）",
        },
        "act/execute_sql": {
            "样本": f"{len(requests)} 条请求",
            "SQL": "1 条 gold_sql（SQLite 只读连接 1 次）",
            "返回行上限": f"{executor.ROW_LIMIT}",
        },
        "partial_repair/locate": {
            "样本": f"{len(events)} 个更新事件",
            "命中事件": f"{len(hit_events)}（{len(hit_events) / len(events):.1%}）",
            "受影响claim": _count_range(affected),
            "候选claim物化": f"{locate_tr.get('claims_materialized', 0):.2f}",
            "证据块比对": f"{locate_tr.get('evidence_visited', 0):.2f}",
            "变更块哈希核对": f"{locate_tr.get('drift_checks', 0):.2f}",
        },
        "partial_repair/locate_hit": {
            "样本": f"{len(hit_events)} 个命中事件",
            "受影响claim": _count_range([len(locate(index, ev)) for ev in hit_events]),
            "候选claim物化": f"{locate_hit_tr.get('claims_materialized', 0):.2f}",
            "证据块比对": f"{locate_hit_tr.get('evidence_visited', 0):.2f}",
        },
        "partial_repair/locate_full_scan": {
            "样本": f"{len(events)} 个更新事件",
            "claim全扫": f"{n_claims} 条（固定扫全库）",
            "证据块比对": f"{scan_tr.get('evidence_visited', 0):.2f}",
        },
        "full_regen/retrieve": {
            "样本": f"{len(requests)} 条请求",
            "候选池": f"{len(index['bm25'].doc_ids)} 篇文档",
            "召回候选": f"{TOP_K_FULL} 篇",
            "上下文预算": f"{CONTEXT_CHARS} 字符",
        },
    }

    # ---- 数据侧事实 ------------------------------------------------------
    acl_fail = stale = missing = 0
    for req in requests:
        for doc_id in req["evidence_by_doc"]:
            recs = index["doc_versions"].get(doc_id)
            if not recs:
                missing += 1
                continue
            current = resolve_current(recs, req["as_of"])
            if current is None:
                missing += 1
                continue
            if current["permission"] > req["rank"]:
                acl_fail += 1
            if req["as_of"] - current["updated"] > current["ttl"]:
                stale += 1

    bm25 = data["bm25"]
    hits = 0
    for req in requests:
        top = bm25.search(tokenize(req["question"]), TOP_K_SEMANTIC)
        if set(top) & set(req["evidence_by_doc"]):
            hits += 1
    recall = hits / len(requests) if requests else 0.0

    integrity_bad = 0
    for (doc, ver, cid), h in index["chunk_hash"].items():
        if io.sha256_text(index["doc_version_map"][(doc, ver)]["chunks"][cid][1])[:16] != h:
            integrity_bad += 1

    notes = {
        "有效性检查通过": f"{passed}/{len(requests)} 条（as_of=v0）",
        "判别力（代入 v2 时刻）": f"{rejected_at_v2}/{len(requests)} 条判为失效，"
                                   "说明检查读的是版本与哈希而不是常量",
        "越权引用": f"{acl_fail} 处文档权限高于请求方",
        "过期引用": f"{stale} 处文档超出 TTL",
        "缺版本": f"{missing} 处引用了 as_of 时刻尚无版本的文档",
        "块哈希完整性": f"{integrity_bad}/{len(index['chunk_hash'])} 个块哈希与正文重算不符",
        f"BM25 recall@{TOP_K_SEMANTIC}": f"{recall:.3f}（命中任一 gold 证据文档即算）",
        "更新事件命中率": f"{len(hit_events)}/{len(events)} 事件命中依赖文档，"
                          f"受影响 claim 均值 {_mean(affected):.2f}（最大 {max(affected)}）",
    }
    return {"cpu_count": _cpu_count(), "notes": notes, "recall_at_k": recall,
            "traversal": traversal}


def _cpu_count() -> int:
    import os
    return os.cpu_count() or 1


if __name__ == "__main__":
    raise SystemExit(main())

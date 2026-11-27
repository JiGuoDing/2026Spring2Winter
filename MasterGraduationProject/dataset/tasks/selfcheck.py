#!/usr/bin/env python
"""P3 题库自检。

覆盖题目要求的验收点，并补充交付质量检查：

(a) schema：tasks.jsonl 逐行符合 ``schema/tasks.schema.json``（含必填 cluster_id）；
(b) 难度配比：single_table / join / nested_agg = 60 / 70 / 70；
(c) 可执行性：全部 gold_sql 经 ``db/executor.py`` 在 v0 上执行成功、结果非空、
    单条 SELECT/WITH、显式列名、无 SELECT *；
(d) 主张层与证据可回溯：每题主张数等于分配配额、1 ≤ 主张数 ≤ 5、每条主张 1–2 个
    证据块且块在 ``knowledge/docs.jsonl`` 对应 version 中真实存在；
    ``truth.evidence`` 严格等于全部主张证据的并集；同题主张文本不重复、不全部
    指向同一证据块；
(e) 主张数分布：与 ``params.tasks.claims_per_task`` 的换算名额完全一致（1..5 条
    各 30/40/60/40/30，合计 600），且每种主张数在每个难度层都出现，C3 可分层；
(f) 语义簇：40 个簇、每簇 3–6 题、簇名合法且以域名开头、同簇同域、
    同簇题目共享至少 1 个证据文档；
(g) 可复现：同种子重跑两次 build，tasks.jsonl 的 sha256 与内容完全一致。

另含：数值层与执行结果一致（value / value_hash / expected_columns / 行数上限）、
gold_results 与 tasks 一一对应、时间窗口与 SQL 日期区间一致、金额 2 位与比率 4 位、
口径题必须挂 metric_XXX 且指标卡在证据中、单表事实表 ≥12 张、join 维表组合 ≥15 组、
嵌套窗口/子查询 ≥20 题、权限不低于所引证据密级、MANIFEST 哈希与统计一致。

用法：
    python dataset/tasks/selfcheck.py
    python dataset/tasks/selfcheck.py --skip-rebuild   # 跳过 (g) 的两次重跑
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

from common import ids, io  # noqa: E402
import executor  # noqa: E402

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("FATAL: jsonschema 未安装", file=sys.stderr)
    raise SystemExit(2)

PARAMS = io.read_json(ROOT / "config" / "params.json")
TASK_PARAMS = PARAMS["tasks"]
CLUSTER_PARAMS = PARAMS["clusters"]
TABLES = io.read_json(ROOT / "contracts" / "tables.json")["tables"]
TABLE_NAMES = [t["name"] for t in TABLES]
TABLE_KIND = {t["name"]: ("dim" if t["name"].startswith("dim_") else
                          "agg" if t["name"].startswith("agg_") else
                          "log" if t["name"].startswith("log_") else "fact") for t in TABLES}
FIELD_NAMES = {t["name"]: [f["name"] for f in t["fields"]] for t in TABLES}
PERM_ORDER = ("public", "staff", "restricted")

FAIL: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print(f"  PASS  {name}")
    except AssertionError as exc:
        print(f"  FAIL  {name}: {exc}")
        FAIL.append(name)
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
        FAIL.append(name)


def load_tasks() -> list[dict]:
    return list(io.read_jsonl(TASKS_DIR / "tasks.jsonl"))


def load_gold() -> list[dict]:
    return list(io.read_jsonl(TASKS_DIR / "gold_results.jsonl"))


def canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def value_hash(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()[:16]


def decimals_of(value) -> int:
    """按十进制字面量判断小数位（float 的最短 repr，即 JSON 里的写法）。"""
    text = repr(float(value))
    if "e" in text or "E" in text:
        text = f"{Decimal(text):f}"
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1].rstrip("0"))


# ------------------------------------------------------------------ 主张数配额
def claim_quota() -> dict[str, int]:
    """params.tasks.claims_per_task 在 200 题上的整数名额。"""
    total = TASK_PARAMS["total"]
    return {int(k): round(float(v) * total)
            for k, v in TASK_PARAMS["claims_per_task"].items()}


# ------------------------------------------------------------------ 文档索引
def _docs_index() -> dict[tuple[str, int], dict]:
    idx: dict[tuple[str, int], dict] = {}
    for row in io.read_jsonl(ROOT / "knowledge" / "docs.jsonl"):
        idx[(row["doc_id"], row["version"])] = {
            "chunks": {c["chunk_id"] for c in row["chunks"]},
            "domain": row["domain"],
            "permission": row["permission"],
        }
    return idx


def _task_domain(task: dict, docs: dict) -> str:
    """task 的 domain：取首个 metric_/wp_ 证据文档在知识层的 domain。"""
    for ev in task["truth"]["evidence"]:
        doc = ev["doc_id"]
        if doc.startswith(("metric_", "wp_")):
            row = docs.get((doc, ev["version"]))
            if row:
                return row["domain"]
    raise AssertionError(f"{task['task_id']} 证据里缺少可判定 domain 的文档")


# ------------------------------------------------------------------ (a) schema
def chk_schema() -> None:
    schema = io.read_json(ROOT / "schema" / "tasks.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    rows = load_tasks()
    assert len(rows) == TASK_PARAMS["total"], f"题目数 {len(rows)}"
    for i, row in enumerate(rows):
        errs = sorted(validator.iter_errors(row), key=lambda e: list(e.path))
        assert not errs, f"第 {i + 1} 行 {row.get('task_id')} 不合契约：{errs[0].message}"


# ------------------------------------------------------------------ (b) 难度配比
def chk_difficulty() -> None:
    rows = load_tasks()
    got: dict[str, int] = {}
    for r in rows:
        got[r["difficulty"]] = got.get(r["difficulty"], 0) + 1
    want = {k: TASK_PARAMS[k] for k in ("single_table", "join", "nested_agg")}
    assert got == want, f"难度配比 {got} != {want}"
    assert sorted({r["task_id"] for r in rows}) == sorted(
        ids.task_id(i) for i in range(1, len(rows) + 1)), "task_id 不是 q001..q200 连续编号"
    assert all(r["snapshot"] == "v0" for r in rows), "存在非 v0 的 snapshot"


# ------------------------------------------------------------------ (c) 可执行
FORBIDDEN = ("PRAGMA", "ATTACH", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER")


def chk_sql_runs() -> None:
    rows = load_tasks()
    for r in rows:
        sql = r["gold_sql"]
        assert sql.upper().lstrip().startswith(("SELECT", "WITH")), f"{r['task_id']} 非 SELECT/WITH"
        assert not re.search(r"select\s+\*", sql, re.IGNORECASE), f"{r['task_id']} 使用 SELECT *"
        words = {w.upper() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sql)}
        hit = sorted(words & set(FORBIDDEN))
        assert not hit, f"{r['task_id']} 含禁用关键字 {hit}"
        masked = sql.replace("'", "")
        assert masked.count(";") <= 1, f"{r['task_id']} 疑似多语句"
    for r in rows:
        out = executor.execute("v0", r["gold_sql"])
        assert not out["error"], f"{r['task_id']} 执行失败：{out['error']}"
        assert out["rows"], f"{r['task_id']} 结果为空"
        assert not out["truncated"], f"{r['task_id']} 结果被截断"
        assert out["columns"] == r["expected_columns"], \
            f"{r['task_id']} 列名不符：{out['columns']} != {r['expected_columns']}"
        assert len(out["rows"]) <= 20, f"{r['task_id']} 行数 {len(out['rows'])} 超过 20"


# ------------------------------------------------------------------ (c2) 数值层
def _ratio_columns(cols: list[str]) -> set[str]:
    return {c for c in cols if c.endswith("_ratio") or c.endswith("_weighted")
            or c.endswith("_spread") or c == "mom_diff"}


def chk_value_layer() -> None:
    rows = load_tasks()
    gold_rows = load_gold()
    gold = {g["task_id"]: g for g in gold_rows}
    assert len(gold) == len(rows), f"gold_results 行数 {len(gold)}"
    assert len(gold_rows) == len({g["task_id"] for g in gold_rows}), "gold_results 存在重复 task_id"
    assert sorted(gold) == sorted(r["task_id"] for r in rows), "gold_results 与 tasks 不是一一对应"
    for r in rows:
        out = executor.execute("v0", r["gold_sql"])
        truth = r["truth"]
        shape = "scalar" if (len(out["rows"]) == 1 and len(out["columns"]) == 1
                             and isinstance(out["rows"][0][0], (int, float))) else "table"
        assert r["answer_shape"] == shape, f"{r['task_id']} answer_shape 与执行结果不符"
        expected_value = out["rows"][0][0] if shape == "scalar" else out["rows"]
        assert canonical(truth["value"]) == canonical(expected_value), \
            f"{r['task_id']} truth.value 与执行结果不一致"
        assert truth["value_hash"] == value_hash(truth["value"]), f"{r['task_id']} value_hash 不符"
        assert truth["value"] is not None, f"{r['task_id']} 数值层为空"
        g = gold[r["task_id"]]
        assert g["columns"] == out["columns"], f"{r['task_id']} gold 列名不符"
        assert canonical(g["rows"]) == canonical(out["rows"]), f"{r['task_id']} gold 行不一致"
        assert isinstance(g["elapsed_ms"], (int, float)) and g["elapsed_ms"] >= 0, \
            f"{r['task_id']} 缺少真实耗时"
        ratio_cols = _ratio_columns(out["columns"])
        for row in out["rows"]:
            for col, cell in zip(out["columns"], row):
                if isinstance(cell, float):
                    limit = 4 if col in ratio_cols else 2
                    got = decimals_of(cell)
                    assert got <= limit, f"{r['task_id']} {col} 小数位 {got} > {limit}"


# ------------------------------------------------------------------ (d) 主张层 + 证据
def chk_claim_layer() -> None:
    """主张数、证据数、并集一致性与文本唯一性。"""
    docs = _docs_index()
    rows = load_tasks()
    quota = claim_quota()
    by_count: dict[int, int] = defaultdict(int)
    for r in rows:
        claims = r["truth"]["claims"]
        evidence = r["truth"]["evidence"]
        tid = r["task_id"]
        assert 1 <= len(claims) <= 5, f"{tid} 主张数 {len(claims)} 不在 1—5 之间"
        by_count[len(claims)] += 1
        assert claims, f"{tid} 缺主张层"
        assert evidence, f"{tid} 缺证据层"
        texts = [c["text"] for c in claims]
        assert all(t.strip() for t in texts), f"{tid} 存在空主张"
        assert len(set(texts)) == len(texts), f"{tid} 主张文本重复"
        union: list[tuple[str, str, int]] = []
        block_lists: list[list[tuple[str, str, int]]] = []
        for c in claims:
            assert 1 <= len(c["evidence"]) <= 2, f"{tid} 主张证据数 {len(c['evidence'])} 越界"
            blocks = []
            for ev in c["evidence"]:
                key = (ev["doc_id"], ev["version"])
                assert key in docs, f"{tid} 引用了不存在的文档 {key}"
                assert ids.is_valid_doc_id(ev["doc_id"]), f"{tid} doc_id 非法 {ev['doc_id']}"
                assert ev["chunk_id"] in docs[key]["chunks"], \
                    f"{tid} 块 {ev['chunk_id']} 不在 {key} 中"
                assert ids.is_valid_block_id(ev["chunk_id"]), f"{tid} 块 ID 非法"
                blocks.append((ev["doc_id"], ev["chunk_id"], ev["version"]))
            block_lists.append(blocks)
            union.extend(blocks)
        blocksets = [frozenset(b) for b in block_lists]
        # truth.evidence 严格等于全部主张证据的并集（按首次出现顺序去重）
        dedup: list[tuple[str, str, int]] = []
        seen = set()
        for item in union:
            if item in seen:
                continue
            seen.add(item)
            dedup.append(item)
        got = [(e["doc_id"], e["chunk_id"], e["version"]) for e in evidence]
        assert got == dedup, f"{tid} truth.evidence 不是主张证据并集"
        assert len(got) == len(set(got)), f"{tid} truth.evidence 有重复块"
        # 主张之间可共享证据，但不能全部指向同一块
        assert len(set(union)) >= 2, f"{tid} 全部主张只指向同一个证据块"
        if len(claims) >= 2:
            assert len(set(blocksets)) >= 2, f"{tid} 多条主张使用完全相同的证据组合"
    want = quota
    assert {k: by_count.get(k, 0) for k in sorted(want)} == want, \
        f"主张数分布 {dict(sorted(by_count.items()))} != params 换算 {want}"


# ------------------------------------------------------------------ (d2) 口径层
def chk_metric_layer() -> None:
    docs = _docs_index()
    rows = load_tasks()
    for r in rows:
        for m in r["metric_refs"]:
            assert re.fullmatch(r"metric_\d{3}", m), f"{r['task_id']} metric_ref 非法 {m}"
            assert (m, 1) in docs, f"{r['task_id']} 引用了不存在的指标卡 {m}"
            cited = {e["doc_id"] for e in r["truth"]["evidence"]}
            assert m in cited, f"{r['task_id']} 声明指标 {m} 但未在证据中引用"
        if not r["metric_refs"]:
            sql = r["gold_sql"]
            assert ("log_" in sql) or ("COUNT(" in sql and not re.search(r"(SUM|AVG)\(f\.", sql)), \
                f"{r['task_id']} 口径类题目缺 metric_refs"


# ------------------------------------------------------------------ (d3) 时间窗口
def chk_time_window() -> None:
    rows = load_tasks()
    for r in rows:
        m = re.search(r"date_key\s+BETWEEN\s+(\d{8})\s+AND\s+(\d{8})", r["gold_sql"])
        assert m, f"{r['task_id']} 缺日期区间"
        start, end = m.group(1), m.group(2)
        win = r["time_window"]
        assert win["start"] == f"{start[:4]}-{start[4:6]}-{start[6:]}T00:00:00Z", \
            f"{r['task_id']} time_window.start 与 SQL 不符：{win['start']}"
        assert win["end"] == f"{end[:4]}-{end[4:6]}-{end[6:]}T23:59:59Z", \
            f"{r['task_id']} time_window.end 与 SQL 不符：{win['end']}"


# ------------------------------------------------------------------ (d4) 覆盖面
def chk_coverage() -> None:
    rows = load_tasks()
    single, join, nested = [], [], []
    for r in rows:
        (single if r["difficulty"] == "single_table"
         else join if r["difficulty"] == "join" else nested).append(r)
    single_facts = set()
    for r in single:
        for name in TABLE_NAMES:
            if TABLE_KIND[name] == "fact" and re.search(rf"\b{name}\b", r["gold_sql"]):
                single_facts.add(name)
    assert len(single_facts) >= 12, f"单表题只覆盖 {len(single_facts)} 张事实表"
    pairs = set()
    for r in join:
        tables = {n for n in TABLE_NAMES if re.search(rf"\b{n}\b", r["gold_sql"])}
        facts = {t for t in tables if TABLE_KIND[t] == "fact"}
        dims = {t for t in tables if TABLE_KIND[t] == "dim"}
        for f in facts:
            for d in dims:
                pairs.add((d, f))
    assert len(pairs) >= 15, f"join 只覆盖 {len(pairs)} 组维表-事实表组合"
    window_cnt = sum(1 for r in nested if "OVER (" in r["gold_sql"])
    sub_cnt = sum(1 for r in nested if re.search(r"(?<!AS )\(\s*SELECT", r["gold_sql"], re.I)
                  or re.search(r"AS\s*\(\s*SELECT", r["gold_sql"], re.I))
    assert window_cnt >= 20, f"嵌套题窗口函数仅 {window_cnt} 题"
    assert window_cnt + sub_cnt >= 20, f"嵌套题窗口/子查询仅 {window_cnt + sub_cnt} 题"


# ------------------------------------------------------------------ (d5) 题面
def chk_question_text() -> None:
    rows = load_tasks()
    idp = re.compile(r"\bt\d{2}\b")
    for r in rows:
        q = r["question"]
        assert len(q) >= 4, f"{r['task_id']} 题面过短"
        assert not idp.search(q), f"{r['task_id']} 题面出现内部表编号：{q}"
        for name in TABLE_NAMES:
            assert name not in q, f"{r['task_id']} 题面出现物理表名 {name}"
        assert re.search(r"20\d{2}-\d{2}-\d{2}", q), f"{r['task_id']} 题面缺时间范围"
        assert any(w in q for w in ("元", "额", "比率", "比例", "数量", "记录", "笔",
                                    "耗时", "指标", "值", "天", "客户", "名次", "规模",
                                    "样本量", "GMV", "次数", "载荷")), f"{r['task_id']} 题面缺指标名"


# ------------------------------------------------------------------ (f) 语义簇
def chk_clusters() -> None:
    docs = _docs_index()
    rows = load_tasks()
    by_cluster: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        cid = r["cluster_id"]
        assert ids.is_valid_cluster_id(cid), f"{r['task_id']} cluster_id 非法 {cid}"
        by_cluster[cid].append(r)
    n = len(by_cluster)
    lo, hi = CLUSTER_PARAMS["min_size"], CLUSTER_PARAMS["max_size"]
    assert n == CLUSTER_PARAMS["count"], f"簇数 {n} != params.clusters.count {CLUSTER_PARAMS['count']}"
    assert 35 <= n <= 50, f"簇数 {n} 不在 35—50"
    assert sorted(by_cluster) == sorted(by_cluster.keys()), "簇名未按字典序（不可复现）"
    for cid in sorted(by_cluster):
        items = by_cluster[cid]
        assert lo <= len(items) <= hi, f"{cid} 有 {len(items)} 题，不在 {lo}—{hi}"
        domains = {_task_domain(r, docs) for r in items}
        assert len(domains) == 1, f"{cid} 跨域：{domains}"
        domain = domains.pop()
        assert cid.startswith(f"cls_{domain}_"), f"{cid} 命名未包含域名 {domain}"
        evidence_sets = [{e["doc_id"] for e in r["truth"]["evidence"]} for r in items]
        shared = set.intersection(*evidence_sets)
        assert shared, f"{cid} 内题目不共享任何证据文档"
        # 同簇题目意图相近、参数/角度不同：题面与 SQL 互不重复
        assert len({r["question"] for r in items}) == len(items), f"{cid} 存在完全相同的题面"
        assert len({r["gold_sql"] for r in items}) == len(items), f"{cid} 存在完全相同的 gold_sql"


# ------------------------------------------------------------------ (d6) MANIFEST
def chk_manifest() -> None:
    manifest = io.read_json(TASKS_DIR / "MANIFEST.json")
    for name in ("tasks.jsonl", "gold_results.jsonl", "build.py", "selfcheck.py"):
        assert name in manifest, f"MANIFEST 缺 {name}"
        rec = manifest[name]
        path = TASKS_DIR / name
        assert path.is_file(), f"缺文件 {name}"
        assert rec["sha256"] == io.sha256_file(path), f"{name} 哈希不符"
        assert rec["rows"] == len(path.read_text(encoding="utf-8").splitlines()), \
            f"{name} 行数不符"
    stats = manifest["stats"]
    rows = load_tasks()
    assert stats["task_total"] == TASK_PARAMS["total"], "MANIFEST 题数不符"
    assert stats["difficulty"] == {k: TASK_PARAMS[k] for k in
                                   ("single_table", "join", "nested_agg")}, "MANIFEST 难度分布不符"
    assert sum(stats["domain"].values()) == TASK_PARAMS["total"], "MANIFEST 主题分布不符"
    assert stats["snapshot"] == {"v0": TASK_PARAMS["total"]}, "MANIFEST 快照分布不符"
    # 主张数统计
    claims_stat = stats["claims"]
    want = claim_quota()
    got = {int(k): v for k, v in claims_stat["per_task"].items()}
    assert got == want, f"MANIFEST 主张数分布 {got} != {want}"
    assert claims_stat["total"] == sum(k * v for k, v in want.items()), "MANIFEST 主张总数不符"
    assert claims_stat["total"] == sum(len(r["truth"]["claims"]) for r in rows), \
        "MANIFEST 主张总数与 tasks 不符"
    for difficulty in ("single_table", "join", "nested_agg"):
        dist = claims_stat["by_difficulty"][difficulty]
        assert set(dist) == {"1", "2", "3", "4", "5"}, f"{difficulty} 主张数未覆盖 1—5"
        actual = {str(k): 0 for k in range(1, 6)}
        for r in rows:
            if r["difficulty"] == difficulty:
                actual[str(len(r["truth"]["claims"]))] += 1
        assert dist == actual, f"{difficulty} MANIFEST 主张数分布与 tasks 不符"
    # 簇统计
    cl = stats["clusters"]
    by_cluster: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cluster[r["cluster_id"]].append(r)
    assert cl["count"] == len(by_cluster) == CLUSTER_PARAMS["count"], "MANIFEST 簇数不符"
    assert cl["min_size"] == min(len(v) for v in by_cluster.values()), "MANIFEST 最小簇规模不符"
    assert cl["max_size"] == max(len(v) for v in by_cluster.values()), "MANIFEST 最大簇规模不符"
    assert cl["size_distribution"] == {
        str(k): sum(1 for v in by_cluster.values() if len(v) == k)
        for k in sorted({len(v) for v in by_cluster.values()})}, "MANIFEST 簇规模分布不符"
    table = {entry["cluster_id"]: entry for entry in cl["table"]}
    assert sorted(table) == sorted(by_cluster), "MANIFEST 簇表与 tasks 簇不一致"
    for cid, items in by_cluster.items():
        entry = table[cid]
        assert entry["size"] == len(items), f"{cid} MANIFEST size 不符"
        assert set(entry["task_ids"]) == {r["task_id"] for r in items}, f"{cid} MANIFEST 题号不符"
        assert entry["shared_docs"], f"{cid} MANIFEST 未记录共享证据"
    # 权限分布
    perm_stat = dict(stats["permission"])
    actual_perm: dict[str, int] = defaultdict(int)
    for r in rows:
        actual_perm[r["permission"]] += 1
    assert perm_stat == dict(sorted(actual_perm.items())), "MANIFEST 权限分布不符"


# ------------------------------------------------------------------ (d7) 权限
def chk_permission() -> None:
    docs = _docs_index()
    rows = load_tasks()
    for r in rows:
        perm = r["permission"]
        assert perm in PERM_ORDER, f"{r['task_id']} 权限非法 {perm}"
        for ev in r["truth"]["evidence"]:
            doc_perm = docs[(ev["doc_id"], ev["version"])]["permission"]
            assert PERM_ORDER.index(doc_perm) <= PERM_ORDER.index(perm), \
                f"{r['task_id']} 引用了高于题目密级的证据 {ev['doc_id']}（{doc_perm} > {perm}）"
        for m in r["metric_refs"]:
            doc_perm = docs[(m, 1)]["permission"]
            assert PERM_ORDER.index(doc_perm) <= PERM_ORDER.index(perm), \
                f"{r['task_id']} 声明指标 {m} 密级 {doc_perm} 高于题目 {perm}"


# ------------------------------------------------------------------ (e) 可复现
def chk_rebuild() -> None:
    before = io.sha256_file(TASKS_DIR / "tasks.jsonl")
    rows_before = load_tasks()
    digests = []
    with tempfile.TemporaryDirectory() as tmp:
        for k in ("run1", "run2"):
            out = Path(tmp) / k
            proc = subprocess.run([sys.executable, str(TASKS_DIR / "build.py"),
                                   "--out", str(out), "--quiet"],
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            assert proc.returncode == 0, f"重跑失败：{(proc.stderr or '')[-800:]}"
            digests.append(io.sha256_file(out / "tasks.jsonl"))
            assert io.sha256_file(out / "tasks.jsonl") == before, \
                f"{k} 的 tasks.jsonl 与当前产物哈希不一致"
            # MANIFEST 中的任务哈希也要与重跑一致（证明构建完全确定）
            m = io.read_json(out / "MANIFEST.json")
            assert m["tasks.jsonl"]["sha256"] == before, f"{k} MANIFEST 任务哈希不一致"
        assert digests[0] == digests[1], f"两次重跑哈希不一致：{digests}"
    assert canonical(rows_before) == canonical(load_tasks()), "题目内容与重跑结果不一致"


def main() -> int:
    ap = argparse.ArgumentParser(description="P3 题库自检")
    ap.add_argument("--skip-rebuild", action="store_true", help="跳过两次重跑复现检查")
    args = ap.parse_args()
    print("[tasks.selfcheck]")
    check("schema 合规（含 cluster_id）", chk_schema)
    check("难度配比", chk_difficulty)
    check("gold SQL 可执行且非空", chk_sql_runs)
    check("数值层与执行一致", chk_value_layer)
    check("主张层与证据可回溯（并集一致）", chk_claim_layer)
    check("口径层 metric_refs", chk_metric_layer)
    check("时间窗口一致", chk_time_window)
    check("覆盖面", chk_coverage)
    check("题面规范", chk_question_text)
    check("语义簇结构（40 簇 / 3–6 题 / 共享证据）", chk_clusters)
    check("权限不低于证据密级", chk_permission)
    check("MANIFEST", chk_manifest)
    if not args.skip_rebuild:
        check("同种子重跑一致（tasks.jsonl 哈希）", chk_rebuild)
    if FAIL:
        print(f"\n结果：{len(FAIL)} 项失败 -> {FAIL}")
        return 1
    print("\n结果：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

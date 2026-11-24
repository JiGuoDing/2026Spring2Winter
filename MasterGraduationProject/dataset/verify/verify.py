"""分阶段验收器。任一断言失败即非零退出，禁止进入下一阶段。

用法：
  python dataset/verify/verify.py --stage P0
  python dataset/verify/verify.py --all
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import ids, io, seeds  # noqa: E402

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("FATAL: jsonschema 未安装，无法校验契约", file=sys.stderr)
    raise SystemExit(2)

SCHEMAS = ROOT / "schema"
PARAMS = io.read_json(ROOT / "config" / "params.json")
TABLES = io.read_json(ROOT / "contracts" / "tables.json")["tables"]
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


def load_schema(stem: str) -> dict:
    return io.read_json(SCHEMAS / f"{stem}.schema.json")


def validate_rows(stem: str, rows, limit: int | None = None) -> int:
    schema = load_schema(stem)
    v = jsonschema.Draft202012Validator(schema)
    n = 0
    for row in rows:
        errs = sorted(v.iter_errors(row), key=lambda e: list(e.path))
        assert not errs, f"{stem} 第 {n} 行不合契约: {errs[0].message if errs else ''}"
        n += 1
        if limit and n >= limit:
            break
    return n


def _utc(s: str) -> datetime:
    return datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")


# ---------------------------------------------------------------- P0 契约冻结
def p0() -> None:
    print("[P0] 契约冻结")

    def dirs():
        need = ["schema", "contracts", "config", "common", "fixtures", "db", "knowledge",
                "tasks", "events", "costs", "labels", "verify", "tools"]
        miss = [d for d in need if not (ROOT / d).is_dir()]
        assert not miss, f"缺目录 {miss}"

    def params():
        p = PARAMS
        for k in ("global_seed", "seeds", "semantic_threshold", "db", "knowledge",
                  "tasks", "updates", "streams"):
            assert k in p, f"params 缺键 {k}"
        assert len(p["seeds"]) == p["streams"]["seed_copies"], "seeds 数与 seed_copies 不一致"
        kn = p["knowledge"]
        total = sum(kn[k] for k in ("field_cards", "whitepapers", "metrics", "tools", "plans", "notes"))
        assert total == kn["docs_total"], f"文档构成合计 {total} != docs_total {kn['docs_total']}"
        db = p["db"]
        assert db["tables"] * db["fields_per_table"] == kn["field_cards"], "表×字段数 != 字段卡数"

    def schemas():
        for f in SCHEMAS.glob("*.schema.json"):
            jsonschema.Draft202012Validator.check_schema(io.read_json(f))

    def catalog():
        tables = TABLES
        assert len(tables) == PARAMS["db"]["tables"], f"表数 {len(tables)}"
        seen_t, seen_f = set(), set()
        for tb in tables:
            assert tb["table_id"] not in seen_t, f"重复表 ID {tb['table_id']}"
            seen_t.add(tb["table_id"])
            assert len(tb["fields"]) == PARAMS["db"]["fields_per_table"], tb["name"]
            assert tb["table_id"] == ids.table_id(int(tb["table_id"][1:]))
            for f in tb["fields"]:
                assert f["field_id"] not in seen_f, f"重复字段 ID {f['field_id']}"
                seen_f.add(f["field_id"])
                assert f["field_id"] == ids.field_id(tb["table_id"], int(f["field_id"][-2:]))

    def lineage():
        lin = io.read_json(ROOT / "contracts" / "lineage.json")
        tables = {t["table_id"] for t in TABLES}
        adj: dict[str, set[str]] = {}
        for e in lin["edges"]:
            assert e["from"] in tables and e["to"] in tables, f"血缘边指向未知表 {e}"
            adj.setdefault(e["from"], set()).add(e["to"])
        state: dict[str, int] = {}

        def dfs(u: str) -> None:
            state[u] = 1
            for v in adj.get(u, ()):
                assert state.get(v, 0) != 1, f"血缘存在环：{u}->{v}"
                if state.get(v, 0) == 0:
                    dfs(v)
            state[u] = 2

        for u in list(adj):
            if state.get(u, 0) == 0:
                dfs(u)
        chain = lin["three_hop_chain"]
        for a, b in zip(chain, chain[1:]):
            assert b in adj.get(a, set()), f"三跳链断在 {a}->{b}"

    def id_rules():
        assert ids.table_id(1) == "t01" and ids.table_id(60) == "t60"
        assert ids.field_id("t07", 12) == "fld_t07_12"
        assert ids.block_id("metric_005", 3) == "metric_005#p03"
        assert ids.req_id(412) == "r000412" and ids.upd_id(7) == "u0007"
        assert ids.is_valid_block_id("wp_012#p01")
        assert not ids.is_valid_doc_id("doc_1")
        assert ids.doc_type_of("fld_t03_09") == "field"
        assert ids.doc_type_of("metric_120") == "metric"

    def seeds_stable():
        a = [seeds.rng("unit", "x").random() for _ in range(3)]
        b = [seeds.rng("unit", "x").random() for _ in range(3)]
        c = [seeds.rng("unit", "y").random() for _ in range(3)]
        assert a == b, "同 (stage,name) 不可复现"
        assert a != c, "不同 name 产生相同序列"

    def fixtures():
        fx = ROOT / "fixtures"
        validate_rows("docs_versioned", io.read_jsonl(fx / "docs_versioned.sample.jsonl"))
        validate_rows("request_stream", io.read_jsonl(fx / "request_stream.sample.jsonl"))
        validate_rows("update_events", io.read_jsonl(fx / "update_events.sample.jsonl"))
        validate_rows("act_plan_pool", [io.read_json(fx / "act_plan_pool.sample.json")])

    for name, fn in (("目录结构", dirs), ("params 一致性", params), ("schema 合法", schemas),
                     ("表目录", catalog), ("血缘", lineage), ("ID 规则", id_rules),
                     ("随机数可复现", seeds_stable), ("fixtures 合规", fixtures)):
        check(name, fn)


# ---------------------------------------------------------------- P1 取数库
def p1() -> None:
    print("[P1] 取数库")
    dbdir = ROOT / "db"

    def ddl():
        sql = (dbdir / "schema.sql").read_text(encoding="utf-8")
        con = sqlite3.connect(":memory:")
        con.executescript(sql)
        n = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'").fetchone()[0]
        assert n == PARAMS["db"]["tables"], f"DDL 建出 {n} 张表，应为 {PARAMS['db']['tables']}"
        con.close()

    def snapshots():
        hs = io.read_json(dbdir / "snapshots" / "hashes.json")
        for snap in PARAMS["db"]["snapshots"]:
            f = dbdir / "snapshots" / f"{snap}.sqlite"
            assert f.is_file(), f"缺快照 {f}"
            rec = hs.get(snap) or hs.get(f"{snap}.sqlite")
            assert rec, f"hashes.json 缺 {snap}"
            expect = rec["sha256"] if isinstance(rec, dict) else rec
            assert io.sha256_file(f) == expect, f"{snap} 哈希与记录不符"

    def readonly():
        f = dbdir / "snapshots" / "v0.sqlite"
        con = sqlite3.connect(f"file:{f}?mode=ro&immutable=1", uri=True)
        try:
            con.execute("DELETE FROM dim_date")
            raise AssertionError("只读连接竟然允许 DELETE")
        except sqlite3.OperationalError:
            pass
        finally:
            con.close()

    def executor_behaviour():
        sys.path.insert(0, str(dbdir))
        import executor  # noqa: PLC0415
        f = str(dbdir / "snapshots" / "v0.sqlite")
        fn = None
        for cand in ("execute", "run", "query", "execute_sql"):
            fn = getattr(executor, cand, None)
            if callable(fn):
                break
        assert fn, "executor.py 未提供 execute/run/query 入口"
        try:
            ok = fn(f, "SELECT COUNT(*) FROM dim_date")
        except TypeError:
            ok = fn("SELECT COUNT(*) FROM dim_date")
        assert not ok.get("error"), f"合法查询报错: {ok.get('error')}"
        assert ok["rows"], "合法查询无结果"
        try:
            bad = fn(f, "DELETE FROM dim_date")
        except TypeError:
            bad = fn("DELETE FROM dim_date")
        assert bad.get("error"), "写语句未被拒绝"

    def compare_unit():
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s",
                            str(dbdir / "tests"), "-t", str(ROOT)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        assert r.returncode == 0, f"单测失败:\n{(r.stderr or '')[-1500:]}"

    def manifest():
        m = io.read_json(dbdir / "MANIFEST.json")
        assert len(m) >= 4, "MANIFEST 条目过少"

    for name, fn in (("DDL 与目录一致", ddl), ("快照与哈希", snapshots), ("只读强制",
                     readonly), ("执行器行为", executor_behaviour), ("比对器单测",
                     compare_unit), ("MANIFEST", manifest)):
        check(name, fn)


# ---------------------------------------------------------------- P2 知识层
def p2() -> None:
    print("[P2] 知识层")
    k = ROOT / "knowledge"
    kn = PARAMS["knowledge"]

    def rows():
        n = 0
        for _ in io.read_jsonl(k / "docs.jsonl"):
            n += 1
        assert n == kn["docs_total"] * kn["versions"], \
            f"docs.jsonl 行数 {n}，应为 {kn['docs_total'] * kn['versions']}"

    def schema_ok():
        validate_rows("docs_versioned", io.read_jsonl(k / "docs.jsonl"))

    def doc_counts():
        docs: dict[str, set[int]] = {}
        for r in io.read_jsonl(k / "docs.jsonl"):
            docs.setdefault(r["doc_id"], set()).add(r["version"])
        assert len(docs) == kn["docs_total"], f"文档数 {len(docs)}"
        for d, vs in docs.items():
            assert vs == {1, 2, 3}, f"{d} 版本不全 {sorted(vs)}"
        by = {"field": 0, "whitepaper": 0, "metric": 0, "tool": 0, "plan": 0, "note": 0}
        for d in docs:
            by[ids.doc_type_of(d)] += 1
        assert by["field"] == kn["field_cards"], by
        assert by["whitepaper"] == kn["whitepapers"], by
        assert by["metric"] == kn["metrics"], by
        assert by["tool"] == kn["tools"], by
        assert by["plan"] == kn["plans"], by
        assert by["note"] == kn["notes"], by

    def stable_blocks():
        seen: dict[str, dict[int, dict[str, str]]] = {}
        for r in io.read_jsonl(k / "docs.jsonl"):
            per = seen.setdefault(r["doc_id"], {}).setdefault(r["version"], {})
            for c in r["chunks"]:
                per[c["chunk_id"]] = c.get("hash") or io.sha256_text(c["text"])[:16]
        for d, vers in seen.items():
            allc = set().union(*[set(v) for v in vers.values()])
            for cid in allc:
                assert cid.startswith(d + "#p"), f"{d} 的块 {cid} 前缀不符"
            assert 1 in vers, d

    def changes_consistent():
        docs = {}
        for r in io.read_jsonl(k / "docs.jsonl"):
            docs[(r["doc_id"], r["version"])] = r
        n = 0
        for ch in io.read_jsonl(k / "version_changes.jsonl"):
            a = docs.get((ch["doc_id"], ch["from_ver"]))
            b = docs.get((ch["doc_id"], ch["to_ver"]))
            assert a and b, f"变更记录指向不存在的版本 {ch}"
            ha = {c["chunk_id"]: c.get("hash") for c in a["chunks"]}
            hb = {c["chunk_id"]: c.get("hash") for c in b["chunks"]}
            kind = ch["change_kind"]
            for cid in ch["changed_chunk_ids"]:
                if kind == "add_chunk":
                    assert cid in hb and cid not in ha, f"{ch['doc_id']} {cid} 不是新增块"
                elif kind == "delete_chunk":
                    assert cid in ha and cid not in hb, f"{ch['doc_id']} {cid} 不是删除块"
                else:
                    assert cid in ha and cid in hb, f"{ch['doc_id']} 的 {cid} 不在两版本中"
                    assert ha[cid] != hb[cid], f"{ch['doc_id']} 的 {cid} 声明变更但哈希相同"
            n += 1
        assert n >= 200, f"版本变更记录仅 {n} 条，过少"

    def selfcheck_runs():
        r = subprocess.run([sys.executable, str(k / "selfcheck.py")],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        assert r.returncode == 0, f"selfcheck 失败:\n{(r.stdout or '')[-1200:]}\n{(r.stderr or '')[-800:]}"

    for name, fn in (("行数", rows), ("schema 合规", schema_ok), ("六类文档计数",
                     doc_counts), ("块 ID 稳定", stable_blocks), ("变更自洽",
                     changes_consistent), ("selfcheck", selfcheck_runs)):
        check(name, fn)


# ---------------------------------------------------------------- P3 题库
def p3() -> None:
    print("[P3] 题库")
    t = ROOT / "tasks"
    tk = PARAMS["tasks"]

    def counts():
        rows = list(io.read_jsonl(t / "tasks.jsonl"))
        assert len(rows) == tk["total"], f"题目数 {len(rows)}"
        by: dict[str, int] = {}
        for r in rows:
            by[r["difficulty"]] = by.get(r["difficulty"], 0) + 1
        assert by.get("single_table", 0) == tk["single_table"], by
        assert by.get("join", 0) == tk["join"], by
        assert by.get("nested_agg", 0) == tk["nested_agg"], by

    def schema_ok():
        validate_rows("tasks", io.read_jsonl(t / "tasks.jsonl"))

    def sql_runs():
        sys.path.insert(0, str(ROOT / "db"))
        import executor  # noqa: PLC0415
        fn = next(getattr(executor, c) for c in ("execute", "run", "query", "execute_sql")
                  if callable(getattr(executor, c, None)))
        db = str(ROOT / "db" / "snapshots" / "v0.sqlite")
        bad = []
        for r in io.read_jsonl(t / "tasks.jsonl"):
            try:
                out = fn(db, r["gold_sql"])
            except TypeError:
                out = fn(r["gold_sql"])
            if out.get("error"):
                bad.append((r["task_id"], out["error"]))
        assert not bad, f"{len(bad)} 条 gold SQL 执行失败，例：{bad[:3]}"

    def truth_layers():
        rows = list(io.read_jsonl(t / "tasks.jsonl"))
        assert all(r["truth"]["claims"] for r in rows), "存在无主张层真值的题"
        assert all(r["truth"]["evidence"] for r in rows), "存在无证据引用的题"
        cov = sum(1 for r in rows if r["truth"].get("value") is not None or
                  r["truth"].get("value_hash"))
        assert cov == len(rows), f"只有 {cov}/{len(rows)} 题有数值层真值"

    for name, fn in (("题目数与难度配比", counts), ("schema 合规", schema_ok),
                     ("gold SQL 可执行", sql_runs), ("三层真值齐备", truth_layers)):
        check(name, fn)


# ---------------------------------------------------------------- P4 事件层
def p4() -> None:
    print("[P4] 事件层")
    e = ROOT / "events"
    up = PARAMS["updates"]
    st = PARAMS["streams"]

    def files():
        for f in ("docs_versioned.jsonl", "request_stream.jsonl", "update_events.jsonl",
                  "act_plan_pool.json"):
            assert (e / f).is_file(), f"缺 {f}"

    def schemas():
        validate_rows("docs_versioned", io.read_jsonl(e / "docs_versioned.jsonl"), limit=500)
        validate_rows("request_stream", io.read_jsonl(e / "request_stream.jsonl"), limit=500)
        validate_rows("update_events", io.read_jsonl(e / "update_events.jsonl"))
        validate_rows("act_plan_pool", [io.read_json(e / "act_plan_pool.json")])

    def stream_size():
        n = sum(1 for _ in io.read_jsonl(e / "request_stream.jsonl"))
        assert n == st["primary_len"], f"请求数 {n}，应为 {st['primary_len']}"
        n_up = sum(1 for _ in io.read_jsonl(e / "update_events.jsonl"))
        assert n_up == up["primary"], f"更新事件 {n_up}，应为 {up['primary']}"
        pool = io.read_json(e / "act_plan_pool.json")
        assert len(pool["acts"]) == PARAMS["knowledge"]["tools"], f"act 数 {len(pool['acts'])}"
        assert len(pool["plans"]) == PARAMS["knowledge"]["plans"], f"plan 数 {len(pool['plans'])}"

    def update_classes():
        cls: dict[str, int] = {}
        for r in io.read_jsonl(e / "update_events.jsonl"):
            cls[r["change_type"]] = cls.get(r["change_type"], 0) + 1
        for c in up["classes"]:
            assert cls.get(c, 0) >= 6, f"{c} 仅 {cls.get(c, 0)} 条，至少 6 条"

    def no_leak():
        eff = {"v0": "2024-05-15T00:00:00+0000", "v1": "2024-05-15T06:00:00+0000",
               "v2": "2024-05-15T12:00:00+0000"}
        for i, r in enumerate(io.read_jsonl(e / "request_stream.jsonl")):
            assert eff[r["snapshot"]["index"]] <= _utc(r["snapshot"]["as_of"]).strftime(
                "%Y-%m-%dT%H:%M:%S%z"), f"{r['req_id']} 引用未来快照"
            if i > 2000:
                break

    def ids_valid():
        for r in io.read_jsonl(e / "request_stream.jsonl"):
            for d in r["gold_doc_ids"]:
                assert ids.is_valid_doc_id(d), f"{r['req_id']} 引用非法 doc_id {d}"
            for s in r["gold_fact_spans"]:
                assert ids.is_valid_block_id(s["chunk_id"]), f"{r['req_id']} 非法块 {s['chunk_id']}"

    for name, fn in (("文件齐备", files), ("schema 合规", schemas), ("规模", stream_size),
                     ("五类更新齐备", update_classes), ("无未来快照泄漏", no_leak),
                     ("ID 合法", ids_valid)):
        check(name, fn)


# ---------------------------------------------------------------- P5 剖面与标签
def p5() -> None:
    print("[P5] 剖面与标签")
    c = ROOT / "costs"
    lb = ROOT / "labels"

    def cost_table():
        f = c / "path_costs.csv"
        assert f.is_file(), "缺 costs/path_costs.csv"
        head = f.read_text(encoding="utf-8").splitlines()[0].split(",")
        for col in ("path", "model", "concurrency", "n", "metric"):
            assert col in head, f"缺列 {col}: {head}"
        if "measured" in head and "mock" in head:
            for line in f.read_text(encoding="utf-8").splitlines()[1:]:
                parts = line.split(",")
                mi, mo = head.index("measured"), head.index("mock")
                assert not (parts[mi] not in ("", "NA") and parts[mo] not in ("", "NA")), \
                    "同一行 measured 与 mock 同时有值"

    def label_table():
        rows = list(io.read_jsonl(lb / "safe_reuse.jsonl"))
        assert len(rows) == PARAMS["labels"]["safe_reuse"], f"标签数 {len(rows)}"
        for r in rows:
            assert "safe" in r and "negative_type" in r, "标签缺字段"

    def pairs():
        rows = list(io.read_jsonl(lb / "branch_pairs.jsonl"))
        assert len(rows) == PARAMS["labels"]["branch_pairs"], f"配对数 {len(rows)}"

    for name, fn in (("成本表", cost_table), ("安全复用标签", label_table), ("分支配对", pairs)):
        check(name, fn)


# ---------------------------------------------------------------- P6 交付
def p6() -> None:
    print("[P6] 交付")

    def docs():
        for f in ("DATASET_CARD.md", "PAPER_MAP.md", "MANIFEST.json"):
            assert (ROOT / f).is_file(), f"缺 {f}"

    def card_fields():
        txt = (ROOT / "DATASET_CARD.md").read_text(encoding="utf-8")
        for key in ("构造", "measured", "许可", "局限"):
            assert key in txt, f"数据集卡片缺「{key}」小节"

    for name, fn in (("交付文档", docs), ("卡片要素", card_fields)):
        check(name, fn)


STAGES = {"P0": p0, "P1": p1, "P2": p2, "P3": p3, "P4": p4, "P5": p5, "P6": p6}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=sorted(STAGES))
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all:
        for s in sorted(STAGES):
            STAGES[s]()
    elif args.stage:
        STAGES[args.stage]()
    else:
        ap.error("需要 --stage 或 --all")

    if FAIL:
        print(f"\n结果：{len(FAIL)} 项失败 -> {FAIL}")
        return 1
    print("\n结果：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

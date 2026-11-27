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

    def claims_distribution():
        import collections
        rows = list(io.read_jsonl(t / "tasks.jsonl"))
        target = PARAMS["tasks"]["claims_per_task"]
        cnt = collections.Counter(len(r["truth"]["claims"]) for r in rows)
        total = sum(k * v for k, v in cnt.items())
        assert 540 <= total <= 660, f"主张总数 {total}，应在 540–660"
        for k, ratio in target.items():
            got = cnt.get(int(k), 0) / len(rows)
            assert abs(got - ratio) <= 0.08, f"{k} 条主张占比 {got:.2f}，目标 {ratio}"
        assert len(cnt) >= 4, f"主张数只有 {sorted(cnt)} 种，退化"

    def clusters():
        import collections
        rows = list(io.read_jsonl(t / "tasks.jsonl"))
        by_cluster = collections.defaultdict(list)
        for r in rows:
            assert ids.is_valid_cluster_id(r["cluster_id"]), r["cluster_id"]
            by_cluster[r["cluster_id"]].append(r)
        assert 35 <= len(by_cluster) <= 50, f"簇数 {len(by_cluster)}"
        for cid, items in by_cluster.items():
            assert 3 <= len(items) <= 6, f"{cid} 有 {len(items)} 题"
            common = None
            for it in items:
                docs = {e["doc_id"] for e in it["truth"]["evidence"]}
                common = docs if common is None else (common & docs)
            assert common, f"{cid} 内题目不共享任何证据文档"

    for name, fn in (("题目数与难度配比", counts), ("schema 合规", schema_ok),
                     ("gold SQL 可执行", sql_runs), ("三层真值齐备", truth_layers),
                     ("主张数分布", claims_distribution), ("语义簇结构", clusters)):
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

    def streams():
        for s in PARAMS["seeds"]:
            f = e / "streams" / f"seed{s}.jsonl"
            assert f.is_file(), f"缺 {f.name}"
            n = sum(1 for _ in io.read_jsonl(f))
            assert n == st["primary_len"], f"{f.name} {n} 条"
        longs = sorted((e / "streams").glob("long_*.jsonl"))
        assert len(longs) == st["long_count"], f"长流 {len(longs)} 条"
        for f in longs:
            n = sum(1 for _ in io.read_jsonl(f))
            assert n == st["long_len"], f"{f.name} {n} 条"

    def calibration():
        f = e / "real_calibration_300.template.csv"
        assert f.is_file(), "缺校准模板"
        lines = f.read_text(encoding="utf-8").splitlines()
        head = lines[0].split(",")
        want = ["req_id", "t_plan_ms", "t_rag_ms", "t_act_ms", "t_resp_ms",
                "t_total_ms", "token_cost"]
        assert head == want, f"表头不符: {head}"
        assert len(lines) - 1 == PARAMS["calibration"]["requests"], \
            f"行数 {len(lines) - 1}"
        assert (e / "CALIBRATION.md").is_file(), "缺 CALIBRATION.md"
        filled = sum(1 for ln in lines[1:] if ln.split(",")[3].strip() not in ("", "NA"))
        assert filled >= 0.9 * (len(lines) - 1), f"t_act_ms 实测仅 {filled} 行"

    def referential():
        pool = io.read_json(e / "act_plan_pool.json")
        act_keys = {a["act_key"] for a in pool["acts"]}
        plan_ids = {p["plan_id"] for p in pool["plans"]}
        doc_ids, chunks_by_doc = set(), {}
        for r in io.read_jsonl(e / "docs_versioned.jsonl"):
            doc_ids.add(r["doc_id"])
            chunks_by_doc.setdefault((r["doc_id"], r["version"]), set()).update(
                c["chunk_id"] for c in r["chunks"])
        bad_act, bad_plan, bad_doc = [], [], []
        for r in io.read_jsonl(e / "request_stream.jsonl"):
            if r["act_key"] and r["act_key"] not in act_keys:
                bad_act.append(r["act_key"])
            if r["plan_id"] and r["plan_id"] not in plan_ids:
                bad_plan.append(r["plan_id"])
            if not set(r["gold_doc_ids"]) <= doc_ids:
                bad_doc.append(r["req_id"])
        assert not bad_act, f"{len(bad_act)} 个 act_key 不在池中，例 {bad_act[:3]}"
        assert not bad_plan, f"{len(bad_plan)} 个 plan_id 不在池中，例 {bad_plan[:3]}"
        assert not bad_doc, f"{len(bad_doc)} 条请求引用不存在的文档"
        bad_chunk = []
        for u in io.read_jsonl(e / "update_events.jsonl"):
            have = chunks_by_doc.get((u["doc_id"], u["old_ver"]), set())
            if not have:
                bad_chunk.append((u["event_id"], "doc_ver_missing"))
            elif not set(u["changed_chunk_ids"]) <= have:
                bad_chunk.append((u["event_id"], "chunk_missing"))
        assert not bad_chunk, f"更新事件引用不实，例 {bad_chunk[:3]}"

    def update_impact():
        reqs = list(io.read_jsonl(e / "request_stream.jsonl"))
        cited_docs = {d for r in reqs for d in r["gold_doc_ids"]}
        claim_chunks = {s["chunk_id"] for r in reqs for s in r["gold_fact_spans"]}
        zero, control, claim_hit = [], 0, 0
        for u in io.read_jsonl(e / "update_events.jsonl"):
            miss = u["doc_id"] not in cited_docs
            if miss and u["change_type"] == "codebook_revision":
                control += 1
            elif miss:
                zero.append(u["event_id"])
            if set(u["changed_chunk_ids"]) & claim_chunks:
                claim_hit += 1
        assert not zero, f"{len(zero)} 条非负对照更新不影响任何请求: {zero[:5]}"
        assert control <= PARAMS["updates"]["negative_control_max"], \
            f"无关更新负对照 {control} 条，超上限"
        assert claim_hit >= 22, f"主张级命中仅 {claim_hit} 条，低于下限 22"

    def clock_semantics():
        docs = {(d["doc_id"], d["version"]): d["updated_at"]
                for d in io.read_jsonl(e / "docs_versioned.jsonl")}
        delays = []
        for u in io.read_jsonl(e / "update_events.jsonl"):
            eff = docs.get((u["doc_id"], u["new_ver"]))
            assert eff, f"{u['event_id']} 指向不存在的文档版本"
            assert u["effective_at"] == eff, \
                f"{u['event_id']} effective_at 与文档 updated_at 不一致"
            calc = (_utc(u["timestamp"]) - _utc(u["effective_at"])).total_seconds()
            assert calc >= 0, f"{u['event_id']} 通知早于生效"
            assert abs(calc - u["notification_delay_s"]) <= 1, \
                f"{u['event_id']} notification_delay_s 与时间差不符"
            delays.append(calc)
        assert max(delays) > 60, "通知延迟全为 0，双时间戳失去意义"

    def local_repair_ratio():
        reqs = list(io.read_jsonl(e / "request_stream.jsonl"))
        ups = list(io.read_jsonl(e / "update_events.jsonl"))
        local = major = 0
        for u in ups:
            ch = set(u["changed_chunk_ids"])
            for r in reqs:
                n = len(r["gold_fact_spans"])
                if not n:
                    continue
                hit = sum(1 for s in r["gold_fact_spans"] if s["chunk_id"] in ch)
                if not hit:
                    continue
                if hit / n < 0.5:
                    local += 1
                else:
                    major += 1
        total = local + major
        assert total >= 200, f"受影响对仅 {total} 个，样本不足"
        ratio = local / total
        lo, hi = PARAMS["updates"]["local_repair_ratio_target"]
        assert lo <= ratio <= hi, f"局部修复占比 {ratio:.2f} 不在 [{lo},{hi}]"

    def act_plan_heterogeneity():
        pool = io.read_json(e / "act_plan_pool.json")
        dn = [len(a["downstream_tools"]) for a in pool["acts"]]
        ratio = sum(1 for d in dn if d) / len(dn)
        assert ratio >= PARAMS["act_plan"]["min_nonempty_ratio"], \
            f"act 非空下游占比 {ratio:.2f} 低于目标"
        buckets = {0: 0, 1: 0, 2: 0, 3: 0}
        for d in dn:
            buckets[min(d, 3)] += 1
        assert all(v > 0 for v in buckets.values()), f"act 下游梯度不全: {buckets}"
        bands = PARAMS["act_plan"]["plan_completion_by_steps"]
        for p in pool["plans"]:
            band = bands.get(str(len(p["steps"])))
            if band:
                assert band[0] <= p["completion_rate"] <= band[1], \
                    f"{p['plan_id']} 完成率 {p['completion_rate']} 不在 {len(p['steps'])} 步区间"

    def cluster_consistency():
        tasks = {t["task_id"]: t["cluster_id"] for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}
        ctx = {c["req_id"]: c for c in io.read_jsonl(e / "request_context.jsonl")}
        for r in io.read_jsonl(e / "request_stream.jsonl"):
            cid = r["cluster_id"]
            assert ids.is_valid_cluster_id(cid), cid
            tid = ctx.get(r["req_id"], {}).get("task_id")
            if tid and tid in tasks:
                assert tasks[tid] == cid, f"{r['req_id']} 的簇与题目簇不一致"

    for name, fn in (("文件齐备", files), ("schema 合规", schemas), ("规模", stream_size),
                     ("五类更新齐备", update_classes), ("无未来快照泄漏", no_leak),
                     ("ID 合法", ids_valid), ("种子流与长流", streams),
                     ("校准模板", calibration), ("引用完整性", referential),
                     ("更新影响面", update_impact), ("双时间戳语义", clock_semantics),
                     ("局部修复比例", local_repair_ratio),
                     ("act/plan 异质性", act_plan_heterogeneity),
                     ("簇一致性", cluster_consistency)):
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
            assert "safe_system" in r, "缺系统视角标签 safe_system"
            assert "divergence_reason" in r, "缺 divergence_reason"
            # 系统认为安全 ⇒ 事实必安全（批量升版即时通知，(F,T) 结构上不存在）
            if r["safe_system"]:
                assert r["safe"], f"{r['pair_id']} 系统视角安全但真值不安全"

    def divergent_cases():
        reqs = {r["req_id"]: r for r in io.read_jsonl(ROOT / "events" / "request_stream.jsonl")}
        rows = list(io.read_jsonl(lb / "safe_reuse.jsonl"))
        diff = [r for r in rows if r["safe"] != r["safe_system"]]
        assert len(diff) >= 5, f"双视角分歧样本仅 {len(diff)} 条"
        for r in diff:
            assert r["safe"] and not r["safe_system"], \
                f"{r['pair_id']} 分歧方向应为“系统保守误失效”(T,F)"
            assert r["divergence_reason"], f"{r['pair_id']} 缺分歧原因"
        hard = [r for r in rows if not r["safe"] and
                r["negative_type"] in ("N1_entity_mismatch", "N4_time_window", "N6_reasoning_chain")]
        same = sum(1 for r in hard
                   if reqs[r["req_id"]]["cluster_id"] == reqs[r["cached_req_id"]]["cluster_id"])
        assert hard and same / len(hard) >= 0.8, \
            f"难负例同簇比例 {same}/{len(hard)}，低于 0.8，相似度过低易被区分"

    def pairs():
        rows = list(io.read_jsonl(lb / "branch_pairs.jsonl"))
        assert len(rows) == PARAMS["labels"]["branch_pairs"], f"配对数 {len(rows)}"
        for r in rows:
            assert "t_model_full_ms" in r and "t_model_cache_ms" in r, "配对缺模型耗时列"

    def review_csv():
        f = lb / "to_review.csv"
        assert f.is_file(), "缺待人工复核清单"
        lines = f.read_text(encoding="utf-8").splitlines()
        assert len(lines) - 1 >= PARAMS["labels"]["human_review"], \
            f"待复核 {len(lines) - 1} 行，应 ≥ {PARAMS['labels']['human_review']}"

    for name, fn in (("成本表", cost_table), ("安全复用标签", label_table),
                     ("双视角分歧样本", divergent_cases), ("分支配对", pairs),
                     ("待复核清单", review_csv)):
        check(name, fn)


# ---------------------------------------------------------------- P6 交付
def p6() -> None:
    print("[P6] 交付")

    def docs():
        for f in ("DATASET_CARD.md", "PAPER_MAP.md", "MANIFEST.json", "HANDBOOK.md",
                  "audit_v010_report.json"):
            assert (ROOT / f).is_file(), f"缺 {f}"

    def card_fields():
        txt = (ROOT / "DATASET_CARD.md").read_text(encoding="utf-8")
        for key in ("构造", "measured", "许可", "局限", "双时间戳"):
            assert key in txt, f"数据集卡片缺「{key}」小节"

    def embeddings():
        cfg = PARAMS["embedding"]
        path = ROOT / cfg["path"]
        if cfg.get("status") == "generated":
            assert path.is_file(), f"状态为 generated 但缺 {cfg['path']}"
            import numpy as np  # noqa: PLC0415
            z = np.load(path, allow_pickle=False)
            assert "query_texts" in z and "embeddings" in z, "npz 缺键"
            n, dim = z["embeddings"].shape
            assert n == len(z["query_texts"]), "向量行数与文本数不符"
            assert dim == cfg["dim"], f"维度 {dim} != {cfg['dim']}"
            norms = np.linalg.norm(z["embeddings"], axis=1)
            assert np.allclose(norms, 1.0, atol=1e-3), "向量未 L2 归一化"
        else:
            assert (ROOT / "embeddings" / "STATUS.md").is_file(), \
                "句向量未生成时必须提供 embeddings/STATUS.md 说明原因"

    for name, fn in (("交付文档", docs), ("卡片要素", card_fields), ("句向量状态", embeddings)):
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

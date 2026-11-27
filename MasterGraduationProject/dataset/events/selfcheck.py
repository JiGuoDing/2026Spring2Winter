"""P4 事件层自检：契约、规模、结构、一致性与可复现。

    python dataset/events/selfcheck.py

检查项
------
1. 四个 schema 逐行合规（含 7 条流）；
2. 规模等于 config/params.json；
3. docs_versioned 与 knowledge/docs.jsonl 逐行一致；
4. 请求流：ID/时间轴/无未来快照、gold 主张与 doc 可溯、cluster_id 与源题一致、
   obj_types 与题型匹配、热点 60% 与第 9 小时迁移、复用结构、租户与权限；
5. 更新事件：取自 version_changes 真实记录、五类各 ≥6 条、**双时间戳语义**
   （effective_at = 文档 updated_at、notification_delay_s = timestamp−effective_at）、
   6 条 negative_control 无关更新、**局部修复比例 ρ 落入 [0.65, 0.75]**；
6. act/plan 池：数量、成本区间、步骤数、下游工具可解析、**下游梯度与完成率分层**；
7. 校准模板：列有序、300 行、只有 t_act_ms 有值，req_id 与抽样清单逐条对齐；
8. 同种子重跑一致（含与磁盘产物对齐），且不同种子产物不同。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import ids, io  # noqa: E402

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("FATAL: jsonschema 未安装", file=sys.stderr)
    raise SystemExit(2)

SCHEMA = ROOT / "schema"
PARAMS = io.read_json(ROOT / "config" / "params.json")
FAIL: list[str] = []

STREAM_FILES = ["streams/seed42.jsonl", "streams/seed43.jsonl", "streams/seed44.jsonl",
                "streams/seed45.jsonl", "streams/seed46.jsonl",
                "streams/long_01.jsonl", "streams/long_02.jsonl"]


# --------------------------------------------------------------------------- 框架
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


def _utc(s: str) -> datetime:
    return datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")


def _validator(stem: str):
    return jsonschema.Draft202012Validator(io.read_json(SCHEMA / f"{stem}.schema.json"))


def _validate(stem: str, rows) -> int:
    v = _validator(stem)
    n = 0
    for row in rows:
        errs = sorted(v.iter_errors(row), key=lambda e: list(e.path))
        assert not errs, f"{stem} 第 {n} 行不合契约：{errs[0].message if errs else ''}"
        n += 1
    return n


def _load(rel: str) -> list[dict]:
    return list(io.read_jsonl(HERE / rel))


# --------------------------------------------------------------------------- 1 契约
def schema_checks() -> None:
    print("[1] schema 合规")
    check("docs_versioned.schema.json × 6000 行",
          lambda: _validate("docs_versioned", _load("docs_versioned.jsonl")))
    check("request_stream.schema.json × 3000 行",
          lambda: _validate("request_stream", _load("request_stream.jsonl")))
    check("update_events.schema.json × 40 行",
          lambda: _validate("update_events", _load("update_events.jsonl")))
    check("act_plan_pool.schema.json", lambda: _validate("act_plan_pool",
                                                         [io.read_json(HERE / "act_plan_pool.json")]))

    def all_streams():
        for rel in STREAM_FILES:
            _validate("request_stream", _load(rel))
    check("7 条流全部合规", all_streams)


# --------------------------------------------------------------------------- 2 规模
def scale_checks() -> None:
    print("[2] 规模")
    kn, st, up = PARAMS["knowledge"], PARAMS["streams"], PARAMS["updates"]
    docs_rows = _load("docs_versioned.jsonl")
    reqs = _load("request_stream.jsonl")
    ups = _load("update_events.jsonl")
    pool = io.read_json(HERE / "act_plan_pool.json")

    def docs():
        assert len(docs_rows) == kn["docs_total"] * kn["versions"], f"docs 行数 {len(docs_rows)}"
    check(f"文档 {kn['docs_total']}×{kn['versions']} = 6000", docs)

    def reqs_n():
        assert len(reqs) == st["primary_len"], f"请求数 {len(reqs)}"
    check(f"主请求流 {st['primary_len']} 条", reqs_n)

    def ups_n():
        assert len(ups) == up["primary"], f"更新数 {len(ups)}"
    check(f"主更新 {up['primary']} 条", ups_n)

    def pool_n():
        assert len(pool["acts"]) == kn["tools"], f"act 数 {len(pool['acts'])}"
        assert len(pool["plans"]) == kn["plans"], f"plan 数 {len(pool['plans'])}"
    check(f"act {kn['tools']} / plan {kn['plans']}", pool_n)

    def streams():
        assert len(STREAM_FILES) == st["seed_copies"] + st["long_count"], len(STREAM_FILES)
        for rel in STREAM_FILES[:st["seed_copies"]]:
            assert len(_load(rel)) == st["primary_len"], rel
        for rel in STREAM_FILES[st["seed_copies"]:]:
            assert len(_load(rel)) == st["long_len"], rel
    check("5 个种子副本 + 2 条长流", streams)

    check("MANIFEST 覆盖全部产物", lambda: _manifest_files())


def _manifest_files() -> None:
    m = io.read_json(HERE / "MANIFEST.json")
    need = ["docs_versioned.jsonl", "request_stream.jsonl", "update_events.jsonl",
            "act_plan_pool.json", "request_stream.jsonl", "real_calibration_300.template.csv"]
    need += STREAM_FILES
    miss = [f for f in need if f not in m]
    assert not miss, f"MANIFEST 缺 {miss}"
    for rel in need:
        assert io.sha256_file(HERE / rel) == m[rel]["sha256"], f"{rel} 哈希与 MANIFEST 不符"


# --------------------------------------------------------------------------- 3 文档投影
def docs_checks() -> None:
    print("[3] 文档投影")
    src = list(io.read_jsonl(ROOT / "knowledge" / "docs.jsonl"))
    dst = _load("docs_versioned.jsonl")

    def same():
        assert len(src) == len(dst), f"{len(src)} vs {len(dst)}"
        for i, (a, b) in enumerate(zip(src, dst)):
            assert a == b, f"第 {i} 行内容被改写：{a.get('doc_id')}"
    check("内容与 knowledge/docs.jsonl 逐行一致（未改写）", same)

    def axis():
        eff = {1: "2024-05-15T00:00:00Z", 2: "2024-05-15T06:00:00Z", 3: "2024-05-15T12:00:00Z"}
        vers: dict[str, set[int]] = {}
        for r in dst:
            assert r["updated_at"] == eff[r["version"]], f"{r['doc_id']} v{r['version']} 时间不在时轴"
            vers.setdefault(r["doc_id"], set()).add(r["version"])
        assert len(vers) == PARAMS["knowledge"]["docs_total"], len(vers)
        assert all(v == {1, 2, 3} for v in vers.values()), "存在版本不全的文档"
    check("updated_at 落在 00/06/12 时轴，每个文档 3 个版本", axis)

    def stable():
        per_doc: dict[str, dict[int, list[str]]] = {}
        for r in dst:
            per_doc.setdefault(r["doc_id"], {})[r["version"]] = \
                [c["chunk_id"] for c in r["chunks"]]
        for doc_id, per in per_doc.items():
            for v, cids in per.items():
                assert cids, f"{doc_id} v{v} 无块"
                nums = []
                for cid in cids:
                    assert cid.startswith(doc_id + "#p"), cid
                    nums.append(int(cid.rsplit("#p", 1)[1]))
                # 块 ID 跨版本稳定：删除某块只会在编号上留空洞，不会重新编号
                assert nums == sorted(set(nums)), f"{doc_id} v{v} 块 ID 重复或乱序：{nums}"
                assert 1 <= nums[0] <= 99, f"{doc_id} v{v} 起始块号 {nums[0]}"
    check("块 ID 为 doc#pNN 稳定编号（删除留空洞，不重排）", stable)


def _doc_chunks() -> dict[str, dict[int, dict[str, str]]]:
    """doc_id → version → {chunk_id: hash}，供 gold 回溯与版本漂移检查。"""
    out: dict[str, dict[int, dict[str, str]]] = {}
    for r in _load("docs_versioned.jsonl"):
        out.setdefault(r["doc_id"], {})[r["version"]] = {
            c["chunk_id"]: c.get("hash", "") for c in r["chunks"]}
    return out


# --------------------------------------------------------------------------- 4 请求流
def stream_checks() -> None:
    print("[4] 请求流")
    reqs = _load("request_stream.jsonl")
    ctx = {c["req_id"]: c for c in _load("request_context.jsonl")}
    tasks = {t["task_id"]: t for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}
    chunks = _doc_chunks()
    eff_ver = {1: "2024-05-15T00:00:00Z", 2: "2024-05-15T06:00:00Z", 3: "2024-05-15T12:00:00Z"}
    snap_eff = {"v0": "2024-05-15T00:00:00Z", "v1": "2024-05-15T06:00:00Z",
                "v2": "2024-05-15T12:00:00Z"}

    def ids_seq():
        assert len(reqs) == len(ctx), "context 与请求不等长"
        for i, r in enumerate(reqs, start=1):
            assert r["req_id"] == ids.req_id(i), f"第 {i} 条 req_id 应为 {ids.req_id(i)}"
            assert r["req_id"] in ctx
    check("req_id 连续 r000001…", ids_seq)

    def time_axis():
        prev = None
        for r in reqs:
            t = _utc(r["timestamp"])
            assert "2024-05-15T00:00:00+0000" <= t.strftime("%Y-%m-%dT%H:%M:%S%z") \
                < "2024-05-15T18:00:00+0000", f"{r['req_id']} 越出 18 小时窗口"
            if prev is not None:
                assert t >= prev, f"{r['req_id']} 时间倒序"
            prev = t
        assert reqs[0]["timestamp"] == "2024-05-15T00:00:00Z", "首条不在 00:00"
    check("时间升序且落在 18 小时窗口内", time_axis)

    def snapshots():
        seen = {"v0": 0, "v1": 0, "v2": 0}
        for r in reqs:
            t = r["timestamp"]
            idx = "v0" if t < "2024-05-15T06:00:00Z" else (
                "v1" if t < "2024-05-15T12:00:00Z" else "v2")
            assert r["snapshot"]["index"] == idx, f"{r['req_id']} 快照应为 {idx}"
            assert r["snapshot"]["as_of"] == snap_eff[idx], f"{r['req_id']} as_of 不符"
            assert r["snapshot"]["as_of"] <= t, f"{r['req_id']} 引用了未来快照"
            seen[idx] += 1
        assert all(v > 0 for v in seen.values()), f"快照覆盖不足：{seen}"
        print(f"        snapshot 覆盖 {seen}")
    check("snapshot.index/as_of 与时间轴一致（无未来泄漏）", snapshots)

    def emb():
        assert all(r["query_emb"] is None for r in reqs), "query_emb 必须为 null"
    check("query_emb 全为 null", emb)

    def gold():
        drift = 0
        total = 0
        for r in reqs:
            for d in r["gold_doc_ids"]:
                assert ids.is_valid_doc_id(d), f"{r['req_id']} 非法 doc_id {d}"
                assert d in chunks, f"{r['req_id']} gold doc {d} 不在 docs_versioned"
            for s in r["gold_fact_spans"]:
                assert ids.is_valid_block_id(s["chunk_id"]), f"{r['req_id']} 非法块"
                assert s["claim"].strip(), f"{r['req_id']} 空 claim"
                doc = s["chunk_id"].split("#")[0]
                assert doc in chunks, f"{r['req_id']} 块所属文档不存在 {doc}"
                assert s["chunk_id"] in chunks[doc][1], f"{r['req_id']} 块不在 v1：{s['chunk_id']}"
                avail = max(v for v in chunks[doc] if eff_ver[v] <= r["timestamp"])
                total += 1
                if s["chunk_id"] not in chunks[doc][avail]:
                    drift += 1
        share = drift / max(1, total)
        print(f"        gold span 共 {total} 条，其中 {drift} 条（{share:.2%}）"
              f"在其快照版本已被改写/删除（版本漂移，属预期）")
        assert share <= 0.05, f"版本漂移 {share:.2%} 过高"
    check("gold_doc_ids / gold_fact_spans 均可回溯", gold)

    def pools():
        pool = io.read_json(HERE / "act_plan_pool.json")
        acts = {a["act_key"] for a in pool["acts"]}
        plans = {p["plan_id"] for p in pool["plans"]}
        for r in reqs:
            assert r["plan_id"] in plans, f"{r['req_id']} plan 不在池中"
            assert r["act_key"] in acts, f"{r['req_id']} act 不在池中"
    check("plan_id / act_key 均在池中", pools)

    def obj_types():
        need = {"single_table": {"rag", "resp"}, "join": {"act", "resp"},
                "nested_agg": {"plan"}}
        for r in reqs:
            task = tasks[ctx[r["req_id"]]["task_id"]]
            want = need[task["difficulty"]]
            assert want <= set(r["obj_types"]), \
                f"{r['req_id']} obj_types 缺 {want - set(r['obj_types'])}"
            assert "resp" in r["obj_types"]
    check("obj_types 与题型匹配（口径/执行/多步）", obj_types)

    def per_task():
        groups: dict[str, list[dict]] = {}
        for r in reqs:
            groups.setdefault(ctx[r["req_id"]]["task_id"], []).append(r)
        assert len(groups) == 200, f"只覆盖 {len(groups)} 题"
        for tid, rs in groups.items():
            task = tasks[tid]
            assert len({r["domain"] for r in rs}) == 1, f"{tid} domain 不一致"
            assert len({r["plan_id"] for r in rs}) == 1, f"{tid} plan 不一致"
            assert len({r["act_key"] for r in rs}) == 1, f"{tid} act 不一致"
            assert len({tuple(r["gold_doc_ids"]) for r in rs}) == 1, f"{tid} gold docs 不一致"
            assert len({tuple(r["obj_types"]) for r in rs}) == 1, f"{tid} obj_types 不一致"
            assert len({r["query_text"] for r in rs}) == 3, \
                f"{tid} 应出现 3 种改写，实为 {len({r['query_text'] for r in rs})}"
            want = [d for d in {e["doc_id"] for e in task["truth"]["evidence"]}]
            assert set(want) == set(rs[0]["gold_doc_ids"]), f"{tid} gold docs 与真值不符"
            claims = task["truth"]["claims"]
            assert len(rs[0]["gold_fact_spans"]) == len(claims), f"{tid} 主张条数不符"
            assert [s["claim"] for s in rs[0]["gold_fact_spans"]] == [c["text"] for c in claims], \
                f"{tid} 主张文本与 tasks.truth.claims 不一致"
            assert [s["chunk_id"] for s in rs[0]["gold_fact_spans"]] == \
                [c["evidence"][0]["chunk_id"] for c in claims], \
                f"{tid} 主张证据块与 tasks.truth.claims 不一致"
            assert len({len(r["gold_fact_spans"]) for r in rs}) == 1, f"{tid} 同题主张数不一致"
    check("同题不同改写：domain/plan/act/gold 一致，gold 主张逐条取自真值", per_task)

    def clusters():
        want = {t["cluster_id"] for t in tasks.values()}
        assert len(want) == PARAMS["clusters"]["count"], f"题簇数 {len(want)}"
        for r in reqs:
            assert ids.is_valid_cluster_id(r["cluster_id"]), r["cluster_id"]
            tid = ctx[r["req_id"]]["task_id"]
            assert r["cluster_id"] == tasks[tid]["cluster_id"], \
                f"{r['req_id']} 簇 {r['cluster_id']} 与源题 {tid} 不一致"
            assert ctx[r["req_id"]]["cluster_id"] == r["cluster_id"], \
                f"{r['req_id']} sidecar 簇不一致"
        for rel in STREAM_FILES:
            seen = {r["cluster_id"] for r in _load(rel)}
            assert seen <= want and seen, f"{rel} 出现未定义簇：{sorted(seen - want)[:3]}"
        print(f"        主请求流覆盖 {len({r['cluster_id'] for r in reqs})} 个簇，7 条流均带簇")
    check("cluster_id 与源题一致（请求流/上下文/7 条流）", clusters)

    def tenants():
        from collections import Counter
        cnt = Counter(c["tenant"] for c in ctx.values())
        assert len(cnt) == 3, f"租户数 {len(cnt)}"
        for r in reqs:
            c = ctx[r["req_id"]]
            task = tasks[c["task_id"]]
            if c["tenant_scope"] == "restricted":
                assert r["permission"] == "restricted", f"{r['req_id']} restricted 租户权限不是 restricted"
            else:
                assert r["permission"] == task["permission"], \
                    f"{r['req_id']} 权限应沿用题目 {task['permission']}"
        neg = sum(1 for c in ctx.values() if c["permission_negative"])
        print(f"        租户分布 {dict(cnt)}，权限负例 {neg} 条")
    check("三个租户 + restricted 权限覆盖", tenants)

    def hotspot():
        first6 = [c for c in ctx.values() if c["timestamp"] < "2024-05-15T06:00:00Z"]
        hot6 = [c for c in first6 if c["bucket"] == "hot"]
        share = len(hot6) / max(1, len(first6))
        assert 0.55 <= share <= 0.65, f"前 6 小时热点占比 {share:.3f}"
        assert {c["hot_set"] for c in hot6} == {"A"}, "前 6 小时混入了 B 组"
        after9 = [c for c in ctx.values() if c["timestamp"] >= "2024-05-15T09:00:00Z"]
        hot9 = [c for c in after9 if c["bucket"] == "hot"]
        assert {c["hot_set"] for c in hot9} == {"B"}, "第 9 小时后仍有 A 组热点"
        mid = [c for c in ctx.values()
               if "2024-05-15T06:00:00Z" <= c["timestamp"] < "2024-05-15T09:00:00Z"]
        assert {c["hot_set"] for c in mid if c["bucket"] == "hot"} == {"A", "B"}, "迁移窗未混合"
        print(f"        前 6h 热点 {len(hot6)}/{len(first6)} = {share:.2%}；"
              f"9h 后热点全在 B 组")
        tail_share = 1 - len([c for c in ctx.values() if c["bucket"] == "hot"]) / len(ctx)
        assert 0.35 <= tail_share <= 0.45, f"长尾占比 {tail_share:.3f}"
    check("热点 60% + 第 9 小时迁移 + 长尾", hotspot)

    def reuse():
        texts = [r["query_text"] for r in reqs]
        uniq = len(set(texts))
        assert uniq < len(texts) * 0.35, f"复用不足：{uniq} 种文本 / {len(texts)} 条"
        assert uniq == 200 * 3, f"改写覆盖 {uniq}/600，应覆盖每题 3 种"
        rate = sum(1 for c in ctx.values() if c["reused"]) / len(ctx)
        assert 0.25 <= rate <= 0.60, f"复用率 {rate:.3f}"
        dup = len(texts) - uniq
        print(f"        不同文本 {uniq} 种（200 题 × 3 改写全覆盖），重复到达 {dup} 条，"
              f"标记复用率 {rate:.2%}")
    check("复用结构（600 种改写全覆盖 + 同文本多次到达）", reuse)

    def seed_diff():
        base = [r["query_text"] for r in _load("streams/seed42.jsonl")]
        for rel in STREAM_FILES[1:]:
            other = [r["query_text"] for r in _load(rel)]
            assert len(other) == len(_load(rel))
            assert other != base, f"{rel} 与 seed42 完全相同"
        assert io.sha256_file(HERE / "streams" / "seed42.jsonl") == \
            io.sha256_file(HERE / "request_stream.jsonl"), "主请求流应等于 seed42"
    check("各流内容不同，主请求流 = seed42", seed_diff)

    def long_span():
        for rel in STREAM_FILES[PARAMS["streams"]["seed_copies"]:]:
            rows = _load(rel)
            assert rows[0]["timestamp"] == "2024-05-15T00:00:00Z", f"{rel} 未从 00:00 开始"
            assert rows[-1]["timestamp"] < "2024-05-15T18:00:00Z", f"{rel} 越过 18:00"
            span = (_utc(rows[-1]["timestamp"]) - _utc(rows[0]["timestamp"])).total_seconds() / 3600
            assert span > 16, f"{rel} 只跨 {span:.1f} 小时"
    check("长流 5000 条仍覆盖 18 小时", long_span)

    def other_switch():
        """换一个种子重建，确认迁移时刻与热点组都随种子变化（不是只改了文件名）。"""
        import build  # noqa: PLC0415
        tasks = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
        v1 = {r["doc_id"]: r for r in _load("docs_versioned.jsonl") if r["version"] == 1}
        pool = io.read_json(HERE / "act_plan_pool.json")
        ctx_static = build.build_task_ctx(tasks, v1, build.load_tables(), pool)
        rows, c46 = build.gen_stream(tasks, ctx_static, name="seed46", n=3000, switch_hour=11)
        assert rows == _load("streams/seed46.jsonl"), "seed46 重建结果与磁盘不一致"
        hot = [c for c in c46 if c["bucket"] == "hot"]
        assert {c["hot_set"] for c in hot if c["timestamp"] < "2024-05-15T08:00:00Z"} == {"A"}, \
            "seed46 在 8 点前不该混入 B 组"
        assert {c["hot_set"] for c in hot if c["timestamp"] >= "2024-05-15T11:00:00Z"} == {"B"}, \
            "seed46 在 11 点后应只剩 B 组"
        a46 = {c["task_id"] for c in hot if c["hot_set"] == "A"}
        a42 = {c["task_id"] for c in ctx.values()
               if c["bucket"] == "hot" and c["hot_set"] == "A"}
        assert len(a46) == 40 and a46 != a42, "热点组没有随种子变化"
        print(f"        seed46 迁移 11:00，热点组与 seed42 不同（重合 {len(a46 & a42)}/40）")
    check("另一种子：迁移时刻与热点组均不同", other_switch)


# --------------------------------------------------------------------------- 5 更新事件
def update_checks() -> None:
    print("[5] 更新事件")
    ups = _load("update_events.jsonl")
    v1 = {r["doc_id"]: r for r in _load("docs_versioned.jsonl") if r["version"] == 1}
    changes = list(io.read_jsonl(ROOT / "knowledge" / "version_changes.jsonl"))
    index = {}
    for ch in changes:
        index.setdefault((ch["doc_id"], ch["from_ver"], ch["to_ver"],
                          tuple(ch["changed_chunk_ids"])), ch)

    def source():
        for u in ups:
            key = (u["doc_id"], u["old_ver"], u["new_ver"], tuple(u["changed_chunk_ids"]))
            assert key in index, f"{u['event_id']} 不是 version_changes 的真实记录"
            assert u["old_ver"] < u["new_ver"] and u["new_ver"] <= 3
    check("doc/old_ver/new_ver/chunk 取自真实版本变更", source)

    def classes():
        from collections import Counter
        cnt = Counter(u["change_type"] for u in ups)
        for c in PARAMS["updates"]["classes"]:
            assert cnt.get(c, 0) >= 6, f"{c} 仅 {cnt.get(c, 0)} 条"
        assert sum(cnt.values()) == PARAMS["updates"]["primary"]
        print(f"        五类计数 {dict(sorted(cnt.items()))}")
    check("五类更新各 ≥6 条", classes)

    def mapping():
        import build  # noqa: PLC0415  复用同一套分类逻辑
        docs_idx = {(r["doc_id"], r["version"]): r for r in _load("docs_versioned.jsonl")}
        for u in ups:
            assert u["change_type"] == build.update_class(u, docs_idx), \
                f"{u['event_id']} 类别与文档类型/变更块内容不匹配"
            doc = v1[u["doc_id"]]
            assert u["domain"] == doc["domain"] and u["permission"] == doc["permission"]
    check("change_type 按文档类型映射，domain/permission 一致", mapping)

    def impact():
        """R1/R2 + 负对照：codebook_revision 刻意不影响任何请求，其余四类必须命中。"""
        reqs = _load("request_stream.jsonl")
        cited_docs: dict[str, int] = {}
        cited_chunks: dict[str, set[str]] = {}
        for r in reqs:
            for d in r["gold_doc_ids"]:
                cited_docs[d] = cited_docs.get(d, 0) + 1
            for s in r["gold_fact_spans"]:
                cited_chunks.setdefault(s["chunk_id"], set()).add(s["claim"])

        rows = []
        for u in ups:
            doc_n = cited_docs.get(u["doc_id"], 0)
            claims = set()
            for cid in u["changed_chunk_ids"]:
                claims |= cited_chunks.get(cid, set())
            chunk_n = sum(1 for r in reqs
                          if any(s["chunk_id"] in u["changed_chunk_ids"]
                                 for s in r["gold_fact_spans"]))
            rows.append((u["event_id"], doc_n, chunk_n, len(claims), u["change_type"],
                         u["doc_id"], u["answer_impact"]))
            assert u["answer_impact"] == ("changed" if claims else "unchanged"), \
                f"{u['event_id']} answer_impact 应为 {'changed' if claims else 'unchanged'}"

        control = [r for r in rows if r[1] == 0 and r[4] == "codebook_revision"]
        zero = [r for r in rows if r[1] == 0 and r[4] != "codebook_revision"]
        doc_level = sum(1 for r in rows if r[1] > 0)
        chunk_level = sum(1 for r in rows if r[2] > 0)
        assert not zero, f"非负对照更新零影响：{[r[0] for r in zero]}"
        assert 1 <= len(control) <= 8, f"无关更新负对照 {len(control)} 条，超出 1–8"
        assert doc_level >= 32, f"文档级影响只有 {doc_level}/40（下限 32）"
        assert chunk_level >= 22, f"主张级影响只有 {chunk_level}/40（下限 22）"
        assert sum(1 for r in rows if r[6] == "changed") == chunk_level
        top_doc = sorted(rows, key=lambda r: -r[1])[:5]
        top_chunk = sorted(rows, key=lambda r: -r[2])[:5]
        print(f"        文档级影响 {doc_level}/40，主张级影响 {chunk_level}/40，"
              f"负对照 {len(control)} 条（均 codebook_revision），非负对照零影响 0 条")
        print("        受影响请求数前 5：" +
              "，".join(f"{r[0]} {r[5]}={r[1]}" for r in top_doc))
        print("        命中主张的请求数前 5：" +
              "，".join(f"{r[0]} {r[5]}={r[2]}" for r in top_chunk))
    check("R1/R2 + 负对照：四类命中请求，codebook 作无关更新对照", impact)

    def timing():
        ver_eff = {2: "2024-05-15T06:00:00+0000", 3: "2024-05-15T12:00:00+0000"}
        first = None
        last = None
        hours = {}
        for u in ups:
            t = _utc(u["timestamp"])
            assert t.strftime("%Y-%m-%dT%H:%M:%S%z") >= ver_eff[u["new_ver"]], \
                f"{u['event_id']} 早于 new_ver 生效时刻"
            assert t.strftime("%Y-%m-%dT%H:%M:%S%z") < "2024-05-15T18:00:00+0000"
            hours[t.hour] = hours.get(t.hour, 0) + 1
            first = t if first is None else min(first, t)
            last = t if last is None else max(last, t)
        span_h = (last - first).total_seconds() / 3600
        assert span_h >= 8, f"事件只跨 {span_h:.1f} 小时，过于集中"
        assert max(hours.values()) <= len(ups) // 3, f"单小时最多 {max(hours.values())} 条，过于集中"
        print(f"        时间跨度 {first:%H:%M}–{last:%H:%M}（{span_h:.1f}h），覆盖 {len(hours)} 个小时")
    check("时间散布、不早于新版本生效、不在开头堆积", timing)

    def dual_clock():
        """v0.2.0 双时间戳：effective_at = 文档 updated_at；delay = timestamp − effective_at。"""
        docs_ = {(d["doc_id"], d["version"]): d for d in _load("docs_versioned.jsonl")}
        delays, prev = [], None
        for u in ups:
            row = docs_.get((u["doc_id"], u["new_ver"]))
            assert row, f"{u['event_id']} 指向不存在的文档版本"
            assert u["effective_at"] == row["updated_at"], \
                f"{u['event_id']} effective_at 与文档 updated_at 不一致"
            t, eff = _utc(u["timestamp"]), _utc(u["effective_at"])
            calc = (t - eff).total_seconds()
            assert calc >= 0, f"{u['event_id']} 通知早于生效"
            assert abs(calc - u["notification_delay_s"]) <= 1, \
                f"{u['event_id']} notification_delay_s 与时间差不符"
            assert t < _utc("2024-05-15T18:00:00Z"), f"{u['event_id']} 越出 18 小时窗口"
            if prev is not None:
                assert t >= prev, f"{u['event_id']} 时间倒序"
            prev = t
            delays.append(calc / 3600.0)
        lo_ref, hi_ref = 0.03, 3.08
        assert lo_ref - 0.02 <= min(delays), f"最小通知延迟 {min(delays):.3f}h 过小"
        assert max(delays) <= hi_ref + 0.02, f"最大通知延迟 {max(delays):.3f}h 过大"
        med = sorted(delays)[len(delays) // 2]
        assert 1.4 <= med <= 1.8, f"通知延迟中位 {med:.3f}h 偏离参考 1.6h"
        print(f"        通知延迟 {min(delays):.3f}–{max(delays):.3f}h，"
              f"中位 {med:.3f}h（参考 0.03–3.08h / 1.6h）")
    check("双时间戳语义（effective_at / notification_delay_s）", dual_clock)

    def negative_control():
        """6 条 codebook_revision 必须是无关更新负对照：零文档级影响、answer_impact=unchanged。"""
        reqs_ = _load("request_stream.jsonl")
        cited = {d for r in reqs_ for d in r["gold_doc_ids"]}
        controls = [u for u in ups if u.get("negative_control")]
        assert len(controls) == 6, f"negative_control 行 {len(controls)} 条，应为 6"
        for u in controls:
            assert u["change_type"] == "codebook_revision", u["event_id"]
            assert u["doc_id"] not in cited, f"{u['event_id']} 负对照竟被请求引用"
            assert u["answer_impact"] == "unchanged", u["event_id"]
        codebook = [u for u in ups if u["change_type"] == "codebook_revision"]
        assert {u["event_id"] for u in codebook} == {u["event_id"] for u in controls}, \
            "存在未标 negative_control 的 codebook 更新"
        for u in ups:
            if u["change_type"] != "codebook_revision":
                assert not u.get("negative_control"), f"{u['event_id']} 非负对照被误标"
        others = [u for u in ups if u["change_type"] != "codebook_revision"]
        hit = [u for u in others if u["doc_id"] in cited]
        assert len(hit) == len(others) == 34, "非负对照更新必须全部命中真实请求"
        assert sum(1 for u in others if u["answer_impact"] == "changed") >= 22, \
            "主张级命中不足 22 条"
    check("6 条 codebook 负对照 + 34 条非负对照全部命中请求", negative_control)

    def local_repair():
        """v0.2.0 新增硬目标：受影响 (更新,请求) 对中 ρ<0.5 的比例落在 [0.65,0.75]。"""
        reqs_ = _load("request_stream.jsonl")
        lo, hi = PARAMS["updates"]["local_repair_ratio_target"]
        local = major = 0
        by_n: dict[int, list[int]] = {}
        for u in ups:
            ch = set(u["changed_chunk_ids"])
            for r in reqs_:
                n = len(r["gold_fact_spans"])
                hit = sum(1 for s in r["gold_fact_spans"] if s["chunk_id"] in ch)
                if not hit:
                    continue
                pair = by_n.setdefault(n, [0, 0])
                if hit / n < 0.5:
                    local += 1
                    pair[0] += 1
                else:
                    major += 1
                    pair[1] += 1
        total = local + major
        assert total >= 200, f"受影响对仅 {total} 个，样本不足"
        ratio = local / total
        assert lo <= ratio <= hi, f"局部修复占比 {ratio:.3f} 不在 [{lo},{hi}]"
        print(f"        受影响对 {total}：局部修复 {local}（{ratio:.2%}）/ 大改 {major}"
              f"（{1 - ratio:.2%}）；按主张数 [局部, 大改] = "
              f"{ {n: tuple(v) for n, v in sorted(by_n.items())} }")
    check("局部修复比例 ρ ∈ [0.65, 0.75]", local_repair)

    def claim_breadth():
        """保留“命中 ≥2 条主张”的大改样本：统计变更块被 ≥2 条不同主张引用的更新。"""
        reqs_ = _load("request_stream.jsonl")
        span_claims: dict[str, set[str]] = {}
        for r in reqs_:
            for s in r["gold_fact_spans"]:
                span_claims.setdefault(s["chunk_id"], set()).add(s["claim"])
        breadth = {}
        for u in ups:
            claims = set()
            for cid in u["changed_chunk_ids"]:
                claims |= span_claims.get(cid, set())
            breadth[u["event_id"]] = len(claims)
        multi = {k: v for k, v in breadth.items() if v >= 2}
        assert len(multi) >= 8, f"命中 ≥2 条主张的更新仅 {len(multi)} 条，大改样本不足"
        print(f"        命中 ≥2 条主张的更新 {len(multi)} 条（最多 {max(breadth.values())} 条主张）；"
              f"单块更新下单请求最多命中 1 条主张")
    check("更新级主张广度（大改样本）", claim_breadth)

    def ids_seq():
        for i, u in enumerate(ups, start=1):
            assert u["event_id"] == ids.upd_id(i), f"第 {i} 条应为 {ids.upd_id(i)}"
    check("event_id 连续 u0001…", ids_seq)


# --------------------------------------------------------------------------- 6 act/plan 池
def pool_checks() -> None:
    print("[6] act / plan 池")
    pool = io.read_json(HERE / "act_plan_pool.json")
    import re
    names = {}
    for r in _load("docs_versioned.jsonl"):
        if r["doc_type"] == "tool" and r["version"] == 1:
            m = re.search(r"（([a-z0-9_]+)）", r["chunks"][0]["text"])
            assert m, r["doc_id"]
            names[r["doc_id"]] = m.group(1)

    def acts():
        keys = [a["act_key"] for a in pool["acts"]]
        assert len(keys) == len(set(keys)) == 100, f"act 数 {len(keys)}"
        want = {f"act_{n}" for n in names.values()}
        assert set(keys) == want, f"act_key 与 tool 卡不一致：{sorted(want ^ set(keys))[:3]}"
        for a in pool["acts"]:
            assert re.fullmatch(r"act_[a-z0-9_]+", a["act_key"]), a["act_key"]
            assert a["readonly"] is True, a["act_key"]
            assert 0.02 <= a["act_cost"] <= 0.80, a
            assert set(a["downstream_tools"]) <= set(keys), a["act_key"]
        cheap = min(a["act_cost"] for a in pool["acts"])
        dear = max(a["act_cost"] for a in pool["acts"])
        print(f"        act_cost {cheap}–{dear}，带下游工具的 act "
              f"{sum(1 for a in pool['acts'] if a['downstream_tools'])} 个")
    check("100 个只读 act，成本 0.02–0.80", acts)

    def plans():
        ids_ = [p["plan_id"] for p in pool["plans"]]
        assert ids_ == [ids.plan_id(i) for i in range(1, 61)], "plan_id 不是 plan_01…plan_60"
        for p in pool["plans"]:
            assert 0.30 <= p["plan_cost"] <= 1.20, p
            assert 0.70 <= p["completion_rate"] <= 0.98, p
            assert 3 <= len(p["steps"]) <= 6, f"{p['plan_id']} 步数 {len(p['steps'])}"
            for s in p["steps"]:
                assert re.search(r"[\u4e00-\u9fa5]", s), f"{p['plan_id']} 步骤非中文：{s}"
        print(f"        plan_cost {min(p['plan_cost'] for p in pool['plans'])}–"
              f"{max(p['plan_cost'] for p in pool['plans'])}，"
              f"completion_rate {min(p['completion_rate'] for p in pool['plans'])}–"
              f"{max(p['completion_rate'] for p in pool['plans'])}")
    check("60 个 plan，成本 0.30–1.20，3–6 步中文", plans)

    def heterogeneity():
        """v0.2.0 异质性目标：下游非空 ≥0.65、四档都有样本、完成率按步数分层。"""
        dn = [len(a["downstream_tools"]) for a in pool["acts"]]
        ratio = sum(1 for d in dn if d) / len(dn)
        target = PARAMS["act_plan"]["min_nonempty_ratio"]
        assert ratio >= target, f"act 下游非空占比 {ratio:.2f} 低于 {target}"
        buckets = {0: 0, 1: 0, 2: 0, 3: 0}
        for d in dn:
            buckets[min(d, 3)] += 1
        assert all(v > 0 for v in buckets.values()), f"act 下游梯度不全：{buckets}"
        bands = PARAMS["act_plan"]["plan_completion_by_steps"]
        by_steps: dict[int, list[float]] = {}
        for p in pool["plans"]:
            n = len(p["steps"])
            band = bands.get(str(n))
            assert band, f"{p['plan_id']} 步数 {n} 无分层区间"
            assert band[0] <= p["completion_rate"] <= band[1], \
                f"{p['plan_id']} 完成率 {p['completion_rate']} 不在 {n} 步区间 {band}"
            by_steps.setdefault(n, []).append(p["completion_rate"])
        means = {n: sum(v) / len(v) for n, v in by_steps.items()}
        assert means[3] > means[4] and means[4] >= means[5] and means[5] > means[6], \
            f"完成率随步数不单调：{ {k: round(v, 3) for k, v in means.items()} }"
        print(f"        下游非空 {sum(1 for d in dn if d)}/100 = {ratio:.0%}，"
              f"0/1/2/3+ = {buckets[0]}/{buckets[1]}/{buckets[2]}/{buckets[3]}")
        print(f"        plan 完成率均值按步数 " +
              "，".join(f"{n} 步 {v:.3f}" for n, v in sorted(means.items())))
    check("act 下游梯度 + plan 完成率按步数分层", heterogeneity)


# --------------------------------------------------------------------------- 7 校准模板
def calibration_checks() -> None:
    print("[7] 校准模板")
    path = HERE / "real_calibration_300.template.csv"
    cols = ["req_id", "t_plan_ms", "t_rag_ms", "t_act_ms", "t_resp_ms", "t_total_ms", "token_cost"]

    def header():
        head = path.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert head == cols, f"列不符：{head}"
    check("列严格为 " + ",".join(cols), header)

    def rows():
        lines = path.read_text(encoding="utf-8").splitlines()[1:]
        assert len(lines) == PARAMS["calibration"]["requests"], f"{len(lines)} 行"
        reqs = {r["req_id"]: r for r in _load("request_stream.jsonl")}
        blanks = 0
        measured = []
        for line in lines:
            parts = line.split(",")
            assert len(parts) == len(cols), line
            rid = parts[0]
            assert rid in reqs, f"{rid} 不在主请求流"
            assert parts[3], f"{rid} 缺 t_act_ms"
            val = float(parts[3])
            assert 0.0 < val < 60000.0, f"{rid} t_act_ms={val}"
            measured.append(val)
            for j in (1, 2, 4, 5, 6):
                assert parts[j] == "", f"{rid} 第 {j} 列应为空（模型相关，不得代造）"
                blanks += 1
        print(f"        t_act_ms 中位 {sorted(measured)[len(measured)//2]:.3f} ms，"
              f"其余 {blanks} 格留空")
    check("300 行、只有 t_act_ms 有值", rows)

    def sample_align():
        """抽样清单与模板 req_id 逐条对齐；req_id 集合不变时 t_act_ms 为原有实测值。"""
        sample = [r["req_id"] for r in _load("calibration_sample.jsonl")]
        csv_ids = [ln.split(",")[0] for ln in path.read_text(encoding="utf-8").splitlines()[1:]
                   if ln.strip()]
        assert csv_ids == sample, "校准模板 req_id 序列与抽样清单不一致"
        assert len(sample) == PARAMS["calibration"]["requests"]
    check("模板 req_id 与 calibration_sample 逐条对齐", sample_align)

    def sandbox():
        assert (HERE / "CALIBRATION.md").is_file(), "缺 CALIBRATION.md"
        txt = (HERE / "CALIBRATION.md").read_text(encoding="utf-8")
        for key in ("t_act_ms", "t_plan_ms", "measured", "回填"):
            assert key in txt, f"CALIBRATION.md 缺「{key}」说明"
    check("CALIBRATION.md 说明实测与回填", sandbox)


# --------------------------------------------------------------------------- 8 可复现
def determinism_checks() -> None:
    print("[8] 可复现")
    import build  # noqa: PLC0415

    work = HERE / ".tmp_selfcheck"
    if work.exists():
        shutil.rmtree(work)

    def twice():
        a, b = work / "a", work / "b"
        build.build_all(a, verbose=False)
        build.build_all(b, verbose=False)
        rels = ["docs_versioned.jsonl", "request_stream.jsonl", "request_context.jsonl",
                "update_events.jsonl", "act_plan_pool.json", "calibration_sample.jsonl"] + STREAM_FILES
        for rel in rels:
            ha, hb = io.sha256_file(a / rel), io.sha256_file(b / rel)
            assert ha == hb, f"{rel} 两次构建哈希不同"
            assert ha == io.sha256_file(HERE / rel), f"{rel} 与磁盘产物不一致"
        print(f"        {len(rels)} 个文件两次构建 + 磁盘产物三方哈希一致")
    try:
        check("同种子两次构建哈希一致", twice)
    finally:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------- 主流程
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P4 事件层自检")
    ap.add_argument("--skip-determinism", action="store_true", help="跳过重跑比对")
    args = ap.parse_args(argv)
    print("[events] 自检 dataset/events")
    schema_checks()
    scale_checks()
    docs_checks()
    stream_checks()
    update_checks()
    pool_checks()
    calibration_checks()
    if not args.skip_determinism:
        determinism_checks()
    if FAIL:
        print(f"\n结果：{len(FAIL)} 项失败 -> {FAIL}")
        return 1
    print("\n结果：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

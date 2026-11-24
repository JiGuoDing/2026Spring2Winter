"""P2 知识文档层自检。

覆盖：
  (a) 6,000 行全部符合 docs_versioned schema（jsonschema Draft 2020-12）
  (b) 六类文档数量等于 config/params.json
  (c) 块 ID 跨版本稳定（{doc_id}#pNN，p01 恒在，p02 仅允许 v3 删除，p03 仅在 v2 新增）
  (d) version_changes 与 docs 逐块自洽（对三个版本重新 diff 并与文件比对）
  (e) 同种子重跑一致：两次内存渲染 + 落盘文件三方 sha256 相同
另查：权限 70/20/10、chunk 长度 60–220、hash 正确、MANIFEST 行数与 sha256。

用法：python dataset/knowledge/selfcheck.py
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KN = ROOT / "knowledge"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(KN))

from common import ids, io  # noqa: E402

import build  # noqa: E402
import jsonschema  # noqa: E402

PARAMS = io.read_json(ROOT / "config" / "params.json")
KN_PARAMS = PARAMS["knowledge"]
SCHEMA = io.read_json(ROOT / "schema" / "docs_versioned.schema.json")
FAIL: list[str] = []
DOCS = KN / "docs.jsonl"
CHANGES = KN / "version_changes.jsonl"


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


def load_rows() -> list[dict]:
    return list(io.read_jsonl(DOCS))


def load_changes() -> list[dict]:
    return list(io.read_jsonl(CHANGES))


def index(rows: list[dict]) -> dict[str, dict[int, dict]]:
    idx: dict[str, dict[int, dict]] = defaultdict(dict)
    for r in rows:
        assert r["version"] not in idx[r["doc_id"]], f"重复版本 {r['doc_id']} v{r['version']}"
        idx[r["doc_id"]][r["version"]] = r
    return idx


# ------------------------------------------------------------------ (a) schema
def schema_ok() -> None:
    validator = jsonschema.Draft202012Validator(SCHEMA)
    rows = load_rows()
    for i, row in enumerate(rows):
        errs = sorted(validator.iter_errors(row), key=lambda e: list(e.path))
        assert not errs, f"第 {i + 1} 行不合 schema：{errs[0].message}"
    assert len(rows) == KN_PARAMS["docs_total"] * KN_PARAMS["versions"], len(rows)


# ------------------------------------------------------------------ (b) 数量
def counts_ok() -> None:
    rows = load_rows()
    idx = index(rows)
    assert len(idx) == KN_PARAMS["docs_total"], f"doc 数 {len(idx)}"
    expect = {
        "field": KN_PARAMS["field_cards"],
        "whitepaper": KN_PARAMS["whitepapers"],
        "metric": KN_PARAMS["metrics"],
        "tool": KN_PARAMS["tools"],
        "plan": KN_PARAMS["plans"],
        "note": KN_PARAMS["notes"],
    }
    got = Counter(r["doc_type"] for r in rows if r["version"] == 1)
    assert got == Counter(expect), f"类型数量 {dict(got)} != {expect}"
    for doc_id, vers in idx.items():
        assert set(vers) == {1, 2, 3}, f"{doc_id} 版本 {sorted(vers)}"
        assert ids.doc_type_of(doc_id) == vers[1]["doc_type"], f"{doc_id} doc_type 不符"
        assert all(v["doc_id"] == doc_id for v in vers.values())
        assert all(v["doc_type"] == vers[1]["doc_type"] for v in vers.values())
        assert all(v["domain"] == vers[1]["domain"] for v in vers.values())
        assert all(v["permission"] == vers[1]["permission"] for v in vers.values())


# ------------------------------------------------------------------ (c) 块 ID
def chunk_ids_stable() -> None:
    rows = load_rows()
    idx = index(rows)
    for doc_id, vers in idx.items():
        p_sets = {}
        for v in (1, 2, 3):
            chunks = vers[v]["chunks"]
            assert 1 <= len(chunks) <= 4, f"{doc_id} v{v} 块数 {len(chunks)}"
            ps = []
            for c in chunks:
                prefix, sep, suffix = c["chunk_id"].rpartition("#p")
                assert sep and prefix == doc_id and suffix.isdigit(), \
                    f"{doc_id} v{v} 块 ID 不符：{c['chunk_id']}"
                p = int(suffix)
                assert p not in ps, f"{doc_id} v{v} 重复块 {c['chunk_id']}"
                assert c["chunk_id"] == ids.block_id(doc_id, p), c["chunk_id"]
                assert 60 <= len(c["text"]) <= 220, \
                    f"{c['chunk_id']} 长度 {len(c['text'])}"
                assert c["hash"] == io.sha256_text(c["text"])[:16], \
                    f"{c['chunk_id']} hash 不符"
                ps.append(p)
            assert ps == sorted(ps), f"{doc_id} v{v} 块未按 pNN 升序"
            p_sets[v] = set(ps)
        assert 1 in p_sets[1] and 1 in p_sets[2] and 1 in p_sets[3], f"{doc_id} 缺 p01"
        assert 2 in p_sets[1] and 2 in p_sets[2], f"{doc_id} 前两版缺 p02"
        base_two = vers[1]["doc_type"] in ("field", "note")
        if base_two:
            assert 3 not in p_sets[1], f"{doc_id} v1 不应有 p03"
            if 3 in p_sets[2]:
                assert 3 in p_sets[3], f"{doc_id} p03 在 v3 丢失"
        else:
            assert 3 in p_sets[1] and 3 in p_sets[2] and 3 in p_sets[3], \
                f"{doc_id} 基础三段缺 p03"
        assert p_sets[3] in (p_sets[2], p_sets[2] - {2}), \
            f"{doc_id} v3 块集合 {p_sets[3]} 非 v2 子集"
        # 同一 p 在不同版本必须是同一 block id（内容可变）
        for p in p_sets[3] & p_sets[1]:
            ids_v1 = {c["chunk_id"] for c in vers[1]["chunks"]}
            ids_v3 = {c["chunk_id"] for c in vers[3]["chunks"]}
            assert ids.block_id(doc_id, p) in ids_v1 and ids.block_id(doc_id, p) in ids_v3


# ------------------------------------------------------------------ (d) 变更
KIND_ORDER = ("modify_text", "modify_number", "add_chunk", "delete_chunk")


def changes_ok() -> None:
    rows = load_rows()
    changes = load_changes()
    idx = index(rows)
    assert len({(c["doc_id"], c["from_ver"], c["to_ver"], c["change_kind"])
                for c in changes}) == len(changes), "version_changes 有重复行"
    for c in changes:
        assert set(c) == {"doc_id", "from_ver", "to_ver", "change_kind",
                          "changed_chunk_ids"}, f"字段不符 {c}"
        assert c["doc_id"] in idx, f"未知 doc {c['doc_id']}"
        assert (c["from_ver"], c["to_ver"]) in ((1, 2), (2, 3)), c
        assert c["change_kind"] in KIND_ORDER, c
        assert c["changed_chunk_ids"], f"{c['doc_id']} 变更块为空"
        a = {x["chunk_id"]: x["hash"] for x in idx[c["doc_id"]][c["from_ver"]]["chunks"]}
        b = {x["chunk_id"]: x["hash"] for x in idx[c["doc_id"]][c["to_ver"]]["chunks"]}
        expected_ids = {"modify_text": [ids.block_id(c["doc_id"], 1)],
                        "modify_number": [ids.block_id(c["doc_id"], 1)],
                        "add_chunk": [ids.block_id(c["doc_id"], 3)],
                        "delete_chunk": [ids.block_id(c["doc_id"], 2)]}[c["change_kind"]]
        assert sorted(c["changed_chunk_ids"]) == expected_ids, \
            f"{c['doc_id']} {c['change_kind']} 块 {c['changed_chunk_ids']}"
        for cid in c["changed_chunk_ids"]:
            if c["change_kind"].startswith("modify"):
                assert cid in a and cid in b, f"{cid} 未在两版同时存在"
                assert a[cid] != b[cid], f"{cid} 两版 hash 相同"
            elif c["change_kind"] == "add_chunk":
                assert cid not in a and cid in b, f"{cid} 新增语义不符"
            else:
                assert cid in a and cid not in b, f"{cid} 删除语义不符"
    # 重新 diff，逐块比对，确保没有漏记/多记
    actual: list[tuple] = []
    for doc_id, vers in idx.items():
        for fv, tv in ((1, 2), (2, 3)):
            a = {x["chunk_id"]: x["hash"] for x in vers[fv]["chunks"]}
            b = {x["chunk_id"]: x["hash"] for x in vers[tv]["chunks"]}
            mods = sorted(cid for cid in a if cid in b and a[cid] != b[cid])
            if mods:
                rows_kind = [c["change_kind"] for c in changes
                             if c["doc_id"] == doc_id and c["from_ver"] == fv
                             and c["to_ver"] == tv and c["change_kind"].startswith("modify")]
                assert len(rows_kind) == 1, f"{doc_id} v{fv}->v{tv} 修改行 {rows_kind}"
                actual.append((doc_id, fv, tv, rows_kind[0], tuple(mods)))
            for kind, ids_ in (("add_chunk", sorted(set(b) - set(a))),
                               ("delete_chunk", sorted(set(a) - set(b)))):
                if ids_:
                    actual.append((doc_id, fv, tv, kind, tuple(ids_)))
    recorded = [(c["doc_id"], c["from_ver"], c["to_ver"], c["change_kind"],
                 tuple(c["changed_chunk_ids"])) for c in changes]
    assert Counter(actual) == Counter(recorded), \
        f"diff 与文件不一致：diff {len(actual)} 行，文件 {len(recorded)} 行"
    kinds = Counter(c["change_kind"] for c in changes)
    pairs = Counter((c["from_ver"], c["to_ver"]) for c in changes)
    assert kinds["add_chunk"] == 200 and kinds["delete_chunk"] == 160, dict(kinds)
    assert pairs[(1, 2)] == 900 and pairs[(2, 3)] == 460, dict(pairs)
    v2_mod = Counter(c["change_kind"] for c in changes
                     if c["from_ver"] == 1 and c["change_kind"].startswith("modify"))
    v3_mod = Counter(c["change_kind"] for c in changes
                     if c["from_ver"] == 2 and c["change_kind"].startswith("modify"))
    assert v2_mod == Counter({"modify_number": 350, "modify_text": 350}), dict(v2_mod)
    assert v3_mod == Counter({"modify_number": 150, "modify_text": 150}), dict(v3_mod)


# ------------------------------------------------------------------ (e) 复现
def deterministic() -> None:
    a_text = build.render_docs_text()
    b_text = build.render_docs_text()
    ha, hb = io.sha256_text(a_text), io.sha256_text(b_text)
    hfile = io.sha256_file(DOCS)
    assert ha == hb, f"两次渲染 docs 哈希不同 {ha} vs {hb}"
    assert ha == hfile, f"渲染哈希 {ha} != 文件 {hfile}"
    ca, cb = build.render_changes_text(), build.render_changes_text()
    assert io.sha256_text(ca) == io.sha256_text(cb), "两次渲染 changes 哈希不同"
    assert io.sha256_text(ca) == io.sha256_file(CHANGES), "changes 渲染与文件不一致"


# ------------------------------------------------------------------ 权限/清单
def permissions_ok() -> None:
    rows = load_rows()
    perms = Counter(r["permission"] for r in rows if r["version"] == 1)
    assert perms == Counter({"public": 1400, "staff": 400, "restricted": 200}), dict(perms)
    per_type = defaultdict(Counter)
    for r in rows:
        if r["version"] == 1:
            per_type[r["doc_type"]][r["permission"]] += 1
    expect = {
        "field": (840, 240, 120), "whitepaper": (140, 40, 20),
        "metric": (105, 30, 15), "tool": (70, 20, 10),
        "plan": (42, 12, 6), "note": (203, 58, 29),
    }
    for t, (pub, st, re) in expect.items():
        c = per_type[t]
        assert (c["public"], c["staff"], c["restricted"]) == (pub, st, re), \
            f"{t} 权限分布 {dict(c)}"


def distinction_ok() -> None:
    rows = [r for r in load_rows() if r["version"] == 1]
    seen = Counter()
    for r in rows:
        for c in r["chunks"]:
            seen[c["text"]] += 1
    dups = [t[:40] for t, n in seen.items() if n > 1]
    assert not dups, f"{len(dups)} 段文本重复，例如 {dups[:3]}"
    per_table = defaultdict(set)
    for r in rows:
        if r["doc_type"] == "field":
            per_table[r["doc_id"].split("_")[1]].add(r["chunks"][0]["text"])
    assert len(per_table) == 60, len(per_table)
    bad = [t for t, texts in per_table.items() if len(texts) != 20]
    assert not bad, f"这些表的字段卡 p01 有重复：{bad}"


def manifest_ok() -> None:
    man = io.read_json(KN / "MANIFEST.json")
    for name, meta in man.items():
        allowed = {"rows", "sha256", "doc_counts"} if name == "docs.jsonl" \
            else {"rows", "sha256"}
        assert set(meta) <= allowed and {"rows", "sha256"} <= set(meta), \
            f"{name} 条目字段 {meta}"
        p = KN / name
        assert p.is_file(), f"MANIFEST 指向缺失文件 {name}"
        assert meta["sha256"] == io.sha256_file(p), f"{name} sha256 不符"
        assert meta["rows"] == len(p.read_text(encoding="utf-8").splitlines()), \
            f"{name} rows 不符"
    assert set(man) >= {"docs.jsonl", "version_changes.jsonl"}, set(man)
    doc_counts = man["docs.jsonl"]["doc_counts"]
    assert doc_counts == {"field": 1200, "whitepaper": 200, "metric": 150,
                          "tool": 100, "plan": 60, "note": 290}, doc_counts
    assert sum(doc_counts.values()) == 2000


def main() -> int:
    print("[P2 knowledge] 自检")
    check("(a) docs_versioned schema", schema_ok)
    check("(b) 六类文档数量 = params", counts_ok)
    check("(c) 块 ID 跨版本稳定", chunk_ids_stable)
    check("(d) version_changes 与 docs 自洽", changes_ok)
    check("(e) 同种子重跑哈希一致", deterministic)
    check("(f) 权限 70/20/10", permissions_ok)
    check("(g) MANIFEST 行数与 sha256", manifest_ok)
    check("(h) 文本区分度", distinction_ok)
    if FAIL:
        print(f"\n结果：{len(FAIL)} 项失败 -> {FAIL}")
        return 1
    print("\n结果：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

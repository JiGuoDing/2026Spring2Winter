"""P5 交付自检（v0.2.0 双视角版）：规模、双视角谓词一致性、系统保守误失效方向、同簇难负例、
reasons 可追溯、重跑确定性、无编造模型耗时。

运行：
    python dataset/labels/selfcheck.py

设计：本文件**不复用** build.py 的 view_judge()，而是按契约的时间戳规则独立重实现一遍
双视角谓词（不使用 update_events.old_ver），再逐条核对磁盘上的标签；reasons 里的每个字符串
也按语法独立解析回原始数据核对。

单调性方向（v0.2.0 修正）：``safe_system=True ⇒ safe=True``。
反方向 ``safe=True, safe_system=False`` 是“系统保守误失效”：批量升版即时通知，系统只在
延迟通知到达后才收紧判定，因此系统认为安全时事实必安全，而系统可能误杀仍然正确的缓存。
"""
from __future__ import annotations

import bisect
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "labels"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))
sys.path.insert(0, str(LABELS))

import compare  # noqa: E402
import executor  # noqa: E402
from common import ids, io  # noqa: E402

PARAMS = io.read_json(ROOT / "config" / "params.json")
PRIV = {"public": 1, "staff": 2, "restricted": 3}
NEG_TYPES = ("N1_entity_mismatch", "N2_permission", "N3_stale_but_looks_right",
             "N4_time_window", "N5_side_effect", "N6_reasoning_chain")
HARD_CLASSES = ("N1_entity_mismatch", "N4_time_window", "N6_reasoning_chain")
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


# ---------------------------------------------------------------------------
# 独立重算（只按时间戳取可见版本，不读 old_ver）
# ---------------------------------------------------------------------------
class Raw:
    """events/ + tasks/ 的只读视图；双视角可见版本在这里独立重建。"""

    def __init__(self) -> None:
        self.tasks = {t["task_id"]: t for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}
        self.reqs = {r["req_id"]: r for r in io.read_jsonl(ROOT / "events" / "request_stream.jsonl")}
        self.ctx = {c["req_id"]: c for c in io.read_jsonl(ROOT / "events" / "request_context.jsonl")}
        self.docs: dict[str, dict[int, dict]] = defaultdict(dict)
        for row in io.read_jsonl(ROOT / "events" / "docs_versioned.jsonl"):
            self.docs[row["doc_id"]][row["version"]] = row
        self.updates = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))
        self.notified: dict[str, dict[int, str]] = defaultdict(dict)
        for doc_id, versions in self.docs.items():
            for ver, row in versions.items():
                self.notified[doc_id][ver] = row["updated_at"]
        for event in self.updates:
            self.notified[event["doc_id"]][event["new_ver"]] = event["timestamp"]
        self._truth = {d: sorted((row["updated_at"], v) for v, row in versions.items())
                       for d, versions in self.docs.items()}
        self._sys = {d: sorted((self.notified[d][v], v) for v in versions)
                     for d, versions in self.docs.items()}
        self._sig: dict[tuple[str, str], str] = {}

    def task_of(self, req_id: str) -> str:
        return self.ctx[req_id]["task_id"]

    def task_of_req(self, req_id: str) -> dict:
        return self.tasks[self.task_of(req_id)]

    def _ver_at(self, table: dict, doc_id: str, timestamp: str) -> int:
        rows = table[doc_id]
        idx = bisect.bisect_right([s for s, _ in rows], timestamp) - 1
        assert idx >= 0, f"{doc_id} 在 {timestamp} 无可见版本"
        return rows[idx][1]

    def truth_ver(self, doc_id: str, timestamp: str) -> int:
        return self._ver_at(self._truth, doc_id, timestamp)

    def sys_ver(self, doc_id: str, timestamp: str) -> int:
        return self._ver_at(self._sys, doc_id, timestamp)

    def notified_at(self, doc_id: str, version: int) -> str:
        return self.notified[doc_id][version]

    def effective_at(self, doc_id: str, version: int) -> str:
        return self.docs[doc_id][version]["updated_at"]

    def chunk_hash(self, doc_id: str, version: int, chunk_id: str):
        for chunk in self.docs[doc_id][version]["chunks"]:
            if chunk["chunk_id"] == chunk_id:
                return chunk.get("hash") or io.sha256_text(chunk["text"])[:16]
        return None

    def sig(self, task_id: str, snapshot: str) -> str:
        key = (task_id, snapshot)
        if key not in self._sig:
            out = executor.execute(snapshot, self.tasks[task_id]["gold_sql"])
            assert not out["error"], f"{task_id}@{snapshot}: {out['error']}"
            rows = compare.normalize(out)["rows"]
            self._sig[key] = hashlib.sha256(
                json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()
        return self._sig[key]


def predicate(raw: Raw, cached_req_id: str, req_id: str, view: str = "truth") -> dict:
    """独立实现的单视角谓词（与 ctx 契约一致：same task / evidence set / version / permission / window）。"""
    cached, req = raw.reqs[cached_req_id], raw.reqs[req_id]
    t_c, t_r = raw.task_of_req(cached_req_id), raw.task_of_req(req_id)
    cur = raw.truth_ver if view == "truth" else raw.sys_ver
    changes = []
    for doc_id in cached["gold_doc_ids"]:
        va = cur(doc_id, cached["timestamp"])
        vb = cur(doc_id, req["timestamp"])
        if va != vb:
            changes.append((doc_id, va, vb))
    checks = {
        "A": t_c["task_id"] == t_r["task_id"],
        "B": cached["gold_doc_ids"] == req["gold_doc_ids"],
        "C": not changes,
        "D": PRIV[req["permission"]] >= PRIV[cached["permission"]],
        "E": t_c["time_window"] == t_r["time_window"],
    }
    return {"safe": all(checks.values()), "checks": checks, "changes": changes, "view": view}


def classification(raw: Raw, cached_req_id: str, req_id: str) -> str:
    j = predicate(raw, cached_req_id, req_id, "truth")
    ch = j["checks"]
    cached, req = raw.reqs[cached_req_id], raw.reqs[req_id]
    if j["safe"]:
        return "none"
    if not ch["D"]:
        return "N2_permission"
    t_c, t_r = raw.task_of_req(cached_req_id), raw.task_of_req(req_id)
    shared = sorted(set(t_c["metric_refs"]) & set(t_r["metric_refs"]))
    if (not ch["E"]) and (not ch["A"]) and shared:
        return "N4_time_window"
    if ch["A"] and not ch["C"]:
        return "N3_stale_but_looks_right"
    if set(req["obj_types"]) > set(cached["obj_types"]) and not ch["A"]:
        return "N6_reasoning_chain"
    return "N1_entity_mismatch"


# ---------------------------------------------------------------------------
# reasons 独立复核
# ---------------------------------------------------------------------------
_ALLOWED = {
    "same_task", "task_mismatch", "same_cluster", "evidence_set_equal",
    "version_unchanged", "truth_stable", "truth_version_changed", "sys_version_changed",
    "system_stricter_window", "answer_equal", "answer_changed",
    "permission_ok", "permission_mismatch", "time_window_equal", "time_window_mismatch",
    "shared_metric", "disjoint_metric", "chain_missing",
}


def verify_reason(raw: Raw, reason: str, cached_req_id: str, req_id: str) -> None:
    cached, req = raw.reqs[cached_req_id], raw.reqs[req_id]
    t_c, t_r = raw.task_of_req(cached_req_id), raw.task_of_req(req_id)
    snap_c, snap_r = cached["snapshot"]["index"], req["snapshot"]["index"]
    head, _, body = reason.partition(":")
    assert head in _ALLOWED, f"未定义的 reason 前缀：{reason}"

    if head == "same_task":
        assert body == t_c["task_id"] == t_r["task_id"], reason
    elif head == "task_mismatch":
        left, right = body.split("->")
        assert left == t_c["task_id"] and right == t_r["task_id"], reason
        assert left != right, reason
    elif head == "same_cluster":
        assert ids.is_valid_cluster_id(body), reason
        assert body == cached["cluster_id"] == req["cluster_id"], reason
    elif head == "evidence_set_equal":
        assert cached["gold_doc_ids"] == req["gold_doc_ids"], reason
        assert int(body) == len(cached["gold_doc_ids"]), reason
    elif head == "version_unchanged":
        doc_id, rest = body.split(":truth=v")
        truth_v, sys_v = rest.split(":sys=v")
        v, s = int(truth_v), int(sys_v)
        assert doc_id in cached["gold_doc_ids"], reason
        assert raw.truth_ver(doc_id, cached["timestamp"]) == v, reason
        assert raw.truth_ver(doc_id, req["timestamp"]) == v, reason
        assert raw.sys_ver(doc_id, cached["timestamp"]) == s, reason
        assert raw.sys_ver(doc_id, req["timestamp"]) == s, reason
    elif head == "truth_stable":
        doc_id, version = body.split("@v")
        v = int(version)
        assert doc_id in cached["gold_doc_ids"], reason
        assert raw.truth_ver(doc_id, cached["timestamp"]) == v, reason
        assert raw.truth_ver(doc_id, req["timestamp"]) == v, reason
    elif head == "truth_version_changed":
        doc_id, rest = body.split(":v")
        left, right = rest.split("->v")
        va, vb = int(left), int(right)
        assert doc_id in cached["gold_doc_ids"], reason
        assert raw.truth_ver(doc_id, cached["timestamp"]) == va, reason
        assert raw.truth_ver(doc_id, req["timestamp"]) == vb, reason
        assert va != vb, reason
    elif head == "sys_version_changed":
        doc_id, rest = body.split(":v")
        left, right = rest.split("->v")
        va, vb = int(left), int(right)
        assert doc_id in cached["gold_doc_ids"], reason
        assert raw.sys_ver(doc_id, cached["timestamp"]) == va, reason
        assert raw.sys_ver(doc_id, req["timestamp"]) == vb, reason
        assert va != vb, reason
    elif head == "system_stricter_window":
        doc_id, rest = body.split("|", 1)
        fields = dict(part.split("=", 1) for part in rest.split("|"))
        assert set(fields) == {"cached", "effective", "notified", "req"}, reason
        assert fields["cached"] == cached["timestamp"], reason
        assert fields["req"] == req["timestamp"], reason
        assert doc_id in cached["gold_doc_ids"], reason
        vb = raw.sys_ver(doc_id, req["timestamp"])
        assert fields["effective"] == raw.effective_at(doc_id, vb), reason
        assert fields["notified"] == raw.notified_at(doc_id, vb), reason
        # 系统保守误失效的窗口：生效时刻 <= 缓存时刻 < 通知时刻 <= 请求时刻
        assert fields["effective"] <= cached["timestamp"], reason
        assert cached["timestamp"] < fields["notified"], reason
        assert fields["notified"] <= req["timestamp"], reason
        assert raw.truth_ver(doc_id, cached["timestamp"]) == raw.truth_ver(doc_id, req["timestamp"]), \
            reason
    elif head in ("answer_equal", "answer_changed"):
        if head == "answer_equal":
            left, right = body.split("==")
            assert left == snap_c and right == snap_r, reason
            assert raw.sig(t_c["task_id"], snap_c) == raw.sig(t_r["task_id"], snap_r), reason
        else:
            task_id, rest = body.split(":", 1)
            left, right = rest.split("!=")
            assert task_id == t_c["task_id"], reason
            assert left == snap_c and right == snap_r, reason
            assert raw.sig(task_id, left) != raw.sig(task_id, right), reason
    elif head in ("permission_ok", "permission_mismatch"):
        left, right = body.split("->")
        assert left == cached["permission"] and right == req["permission"], reason
        assert (PRIV[right] >= PRIV[left]) == (head == "permission_ok"), reason
    elif head == "time_window_equal":
        left, right = body.split("~")
        assert t_c["time_window"] == t_r["time_window"] == {"start": left, "end": right}, reason
    elif head == "time_window_mismatch":
        left, right = body.split("|")
        cs, ce = left.split("~")
        rs, re_ = right.split("~")
        assert t_c["time_window"] == {"start": cs, "end": ce}, reason
        assert t_r["time_window"] == {"start": rs, "end": re_}, reason
        assert t_c["time_window"] != t_r["time_window"], reason
    elif head == "shared_metric":
        assert body in t_c["metric_refs"] and body in t_r["metric_refs"], reason
    elif head == "disjoint_metric":
        left, right = body.split("|")
        ls = {x for x in left.split(",") if x}
        rs = {x for x in right.split(",") if x}
        assert ls and rs, reason
        assert ls == set(t_c["metric_refs"]), reason
        assert rs == set(t_r["metric_refs"]), reason
        assert not (ls & rs), reason
    elif head == "chain_missing":
        cached_chain, req_chain = body.split("|", 1)
        cs = [x for x in cached_chain.split(",") if x]
        rs = [x for x in req_chain.split(",") if x]
        assert sorted(cs) == sorted(cached["obj_types"]), reason
        assert sorted(rs) == sorted(req["obj_types"]), reason
        assert not set(rs) <= set(cs), reason


# ---------------------------------------------------------------------------
# 数据
# ---------------------------------------------------------------------------
def load_outputs():
    return (list(io.read_jsonl(LABELS / "safe_reuse.jsonl")),
            list(io.read_jsonl(LABELS / "branch_pairs.jsonl")))


_REPLAY: dict = {}


def replay_branch():
    """重放 build 的配对选择（不测时间），返回 [(cached_req, req)]，用于核对配对来源。"""
    if "items" not in _REPLAY:
        import build  # noqa: PLC0415
        ds = build.Dataset()
        on_disk = list(io.read_jsonl(LABELS / "safe_reuse.jsonl"))
        taken = {(r["cached_req_id"], r["req_id"]) for r in on_disk}
        _REPLAY["items"] = build.select_branch(ds, taken)
    return _REPLAY["items"]


def main() -> int:
    labels, branch = load_outputs()
    raw = Raw()
    print(f"[labels] 自检目标：safe_reuse {len(labels)} 行，branch_pairs {len(branch)} 行")
    reviews = list(csv.DictReader((LABELS / "to_review.csv").open(encoding="utf-8")))
    by_req = {r["req_id"]: r for r in raw.reqs.values()}

    LABEL_FIELDS = {"pair_id", "req_id", "cached_req_id", "task_id", "cached_doc_ids",
                    "safe", "safe_system", "divergence_reason", "negative_type", "reasons",
                    "judged_by", "confidence"}
    BRANCH_FIELDS = {"pair_id", "req_id", "task_id", "path_full", "path_cache",
                     "t_local_full_ms", "t_local_cache_ms", "g_local_ms",
                     "t_model_full_ms", "t_model_cache_ms", "quality_full", "quality_cache",
                     "measured", "note"}
    REVIEW_HEAD = ["pair_id", "req_id", "cached_req_id", "question", "old_answer_doc",
                   "current_version_of_those_docs", "predicate_safe", "predicate_safe_system",
                   "predicate_reason"]

    # -- 1 规模 ---------------------------------------------------------
    def sizes():
        assert len(labels) == PARAMS["labels"]["safe_reuse"], f"标签 {len(labels)} 行"
        assert len(branch) == PARAMS["labels"]["branch_pairs"], f"配对 {len(branch)} 行"
        assert len(reviews) >= PARAMS["labels"]["human_review"], f"复核 {len(reviews)} 行"

    # -- 2 字段固定 -----------------------------------------------------
    def fields():
        for i, row in enumerate(labels):
            assert set(row) == LABEL_FIELDS, f"第 {i} 行字段不符：{set(row) ^ LABEL_FIELDS}"
            assert row["judged_by"] == "predicate", row["pair_id"]
            assert row["confidence"] == 1.0, row["pair_id"]
            assert isinstance(row["safe"], bool), row["pair_id"]
            assert isinstance(row["safe_system"], bool), row["pair_id"]
            assert isinstance(row["divergence_reason"], str), row["pair_id"]
            assert isinstance(row["reasons"], list) and row["reasons"], row["pair_id"]
        for i, row in enumerate(branch):
            assert set(row) == BRANCH_FIELDS, f"第 {i} 行字段不符：{set(row) ^ BRANCH_FIELDS}"

    # -- 3 时间戳规则谓词一致 -------------------------------------------
    def predicate_agrees():
        for row in labels:
            got = predicate(raw, row["cached_req_id"], row["req_id"], "truth")
            sys_got = predicate(raw, row["cached_req_id"], row["req_id"], "system")
            assert got["safe"] == row["safe"], \
                f"{row['pair_id']} safe 标签 {row['safe']} 与时间戳谓词 {got['safe']} 不一致"
            assert sys_got["safe"] == row["safe_system"], \
                f"{row['pair_id']} safe_system 标签 {row['safe_system']} 与时间戳谓词 {sys_got['safe']} 不一致"
            assert classification(raw, row["cached_req_id"], row["req_id"]) == row["negative_type"], \
                f"{row['pair_id']} 类别与真值谓词分类不一致"
            assert row["task_id"] == raw.task_of(row["req_id"]), row["pair_id"]
            expect = "" if row["safe"] == row["safe_system"] else "system_stricter_window"
            assert row["divergence_reason"] == expect, \
                f"{row['pair_id']} divergence_reason 应为 {expect!r}"
            assert "stored=" not in "".join(row["reasons"]), \
                f"{row['pair_id']} reasons 仍使用 old_ver 口径"

    # -- 4 单调性：系统安全 ⇒ 真值安全 ----------------------------------
    def monotone():
        for row in labels:
            if row["safe_system"]:
                assert row["safe"], f"{row['pair_id']} 系统视角安全但真值不安全"

    # -- 5 系统保守误失效（T,F）样本 ------------------------------------
    def divergent_cases():
        diff = [r for r in labels if r["safe"] != r["safe_system"]]
        assert len(diff) >= 5, f"双视角分歧样本仅 {len(diff)} 条"
        for row in diff:
            assert row["safe"] is True and row["safe_system"] is False, \
                f"{row['pair_id']} 分歧方向应为 (T,F) 系统保守误失效"
            assert row["divergence_reason"] == "system_stricter_window", row["pair_id"]
            cached, req = by_req[row["cached_req_id"]], by_req[row["req_id"]]
            # 同题、证据集一致、权限相容、时间窗一致
            jt = predicate(raw, row["cached_req_id"], row["req_id"], "truth")
            assert jt["safe"], row["pair_id"]
            assert all(jt["checks"].values()), row["pair_id"]
            wins = [x for x in row["reasons"] if x.startswith("system_stricter_window:")]
            assert wins, f"{row['pair_id']} 缺 system_stricter_window 理由"
            changed = [x for x in row["reasons"] if x.startswith("sys_version_changed:")]
            assert len(wins) == len(changed), \
                f"{row['pair_id']} 每个系统版本变化都应落在误失效窗口内"
            for reason in wins:
                doc_id, rest = reason.split("|", 1)[0].split(":", 1)[1], reason.split("|", 1)[1]
                fields = dict(part.split("=", 1) for part in rest.split("|"))
                # 要求：effective <= cached < notified <= req
                assert fields["effective"] <= fields["cached"], reason
                assert fields["cached"] < fields["notified"], reason
                assert fields["notified"] <= fields["req"], reason
                assert raw.truth_ver(doc_id, cached["timestamp"]) == \
                    raw.truth_ver(doc_id, req["timestamp"]), reason

    # -- 6 负例分布 -----------------------------------------------------
    def distribution():
        dist = Counter(r["negative_type"] for r in labels)
        for name in NEG_TYPES:
            assert dist.get(name, 0) >= 25 or name == "N5_side_effect", \
                f"{name} 仅 {dist.get(name, 0)} 条，少于 25"
        assert 0 <= dist.get("N5_side_effect", 0) <= 2, \
            f"N5 应为 0–2 条说明性样本，实际 {dist.get('N5_side_effect', 0)}"
        safe = sum(1 for r in labels if r["safe"])
        assert 145 <= safe <= 155, f"安全标签 {safe} 条，应在 150 附近"
        assert dist["none"] == safe, "negative_type=none 与 safe=true 数量不一致"
        for row in labels:
            assert (row["negative_type"] == "none") == row["safe"], row["pair_id"]
        assert set(dist) <= set(NEG_TYPES) | {"none"}, f"出现未定义类别 {set(dist) - set(NEG_TYPES)}"
        assert dist["N3_stale_but_looks_right"] == 35, dist["N3_stale_but_looks_right"]

    # -- 7 负例构造约束 -------------------------------------------------
    def defects():
        for row in labels:
            cached_id, req_id = row["cached_req_id"], row["req_id"]
            cached, req = raw.reqs[cached_id], raw.reqs[req_id]
            jt = predicate(raw, cached_id, req_id, "truth")
            js = predicate(raw, cached_id, req_id, "system")
            neg = row["negative_type"]
            if neg == "none":
                continue
            assert not jt["safe"] and not js["safe"], \
                f"{row['pair_id']} 负例不应出现视角安全"
            ch = jt["checks"]
            t_c, t_r = raw.task_of_req(cached_id), raw.task_of_req(req_id)
            shared = set(t_c["metric_refs"]) & set(t_r["metric_refs"])
            if neg == "N1_entity_mismatch":
                assert not ch["A"] and ch["E"], row["pair_id"]
                ma, mb = set(t_c["metric_refs"]), set(t_r["metric_refs"])
                assert ma and mb and not (ma & mb), row["pair_id"]
                assert cached["cluster_id"] == req["cluster_id"], row["pair_id"]
            elif neg == "N2_permission":
                assert (not ch["D"]) and ch["A"] and ch["B"] and ch["C"] and ch["E"], row["pair_id"]
            elif neg == "N3_stale_but_looks_right":
                assert ch["A"] and ch["B"] and ch["D"] and ch["E"] and not ch["C"], row["pair_id"]
            elif neg == "N4_time_window":
                assert (not ch["A"]) and (not ch["E"]) and shared, row["pair_id"]
                assert cached["cluster_id"] == req["cluster_id"], row["pair_id"]
            elif neg == "N6_reasoning_chain":
                assert (not ch["A"]) and ch["E"] and shared, row["pair_id"]
                assert not set(req["obj_types"]) <= set(cached["obj_types"]), row["pair_id"]
                assert cached["cluster_id"] == req["cluster_id"], row["pair_id"]

    # -- 8 难负例同簇比例 -----------------------------------------------
    def hard_same_cluster():
        hard = [r for r in labels if r["negative_type"] in HARD_CLASSES]
        assert hard, "没有 N1/N4/N6 难负例"
        same = [r for r in hard
                if by_req[r["req_id"]]["cluster_id"] == by_req[r["cached_req_id"]]["cluster_id"]]
        ratio = len(same) / len(hard)
        assert ratio >= 0.8, f"难负例同簇比例 {len(same)}/{len(hard)} 低于 0.8"
        for row in hard:
            cid = by_req[row["req_id"]]["cluster_id"]
            assert f"same_cluster:{cid}" in row["reasons"], \
                f"{row['pair_id']} 同簇难负例缺少 same_cluster 理由"
            assert by_req[row["cached_req_id"]]["cluster_id"] == cid, row["pair_id"]
        for name in HARD_CLASSES:
            rows = [r for r in hard if r["negative_type"] == name]
            same_n = sum(1 for r in rows
                         if by_req[r["req_id"]]["cluster_id"]
                         == by_req[r["cached_req_id"]]["cluster_id"])
            assert rows and same_n / len(rows) >= 0.8, \
                f"{name} 同簇比例 {same_n}/{len(rows)} 低于 0.8"

    # -- 9 reasons 可追溯 -----------------------------------------------
    def reasons_traceable():
        counts = Counter()
        for row in labels:
            for reason in row["reasons"]:
                verify_reason(raw, reason, row["cached_req_id"], row["req_id"])
                counts[reason.split(":", 1)[0]] += 1
        for name in ("same_task", "evidence_set_equal", "version_unchanged",
                     "permission_ok", "time_window_equal"):
            assert counts[name] > 0, f"缺少正向理由 {name}"
        for name in ("truth_version_changed", "sys_version_changed",
                     "permission_mismatch", "time_window_mismatch", "task_mismatch",
                     "same_cluster", "system_stricter_window", "chain_missing"):
            assert counts[name] > 0, f"缺少负向/双视角理由 {name}"

    # -- 10 配对时序与题号 ----------------------------------------------
    def pair_semantics():
        ids_all = [r["pair_id"] for r in labels] + [r["pair_id"] for r in branch]
        assert len(ids_all) == len(set(ids_all)), "pair_id 重复"
        for row in labels:
            cached, req = by_req[row["cached_req_id"]], by_req[row["req_id"]]
            assert row["cached_req_id"] != row["req_id"], row["pair_id"]
            assert cached["timestamp"] <= req["timestamp"], \
                f"{row['pair_id']} 缓存请求晚于待服务请求"
            assert row["task_id"] == raw.task_of(row["req_id"]), row["pair_id"]
            assert row["cached_doc_ids"] == cached["gold_doc_ids"], \
                f"{row['pair_id']} cached_doc_ids 与缓存请求证据不符"
        for row in branch:
            req = by_req[row["req_id"]]
            assert row["task_id"] == raw.task_of(row["req_id"]), row["pair_id"]
            assert req["snapshot"]["index"] in ("v0", "v1", "v2"), row["pair_id"]

    # -- 11 分支配对 ----------------------------------------------------
    def branch_rows():
        for row in branch:
            assert row["t_model_full_ms"] is None and row["t_model_cache_ms"] is None, \
                f"{row['pair_id']} 出现模型耗时，本阶段不得编造"
            assert row["note"] == "requires_author_model_run", row["pair_id"]
            assert row["measured"] is True, row["pair_id"]
            for key in ("t_local_full_ms", "t_local_cache_ms"):
                assert isinstance(row[key], (int, float)) and row[key] > 0, \
                    f"{row['pair_id']} {key} 非正数"
            expect = round(row["t_local_full_ms"] - row["t_local_cache_ms"], 3)
            assert abs(row["g_local_ms"] - expect) < 1e-9, f"{row['pair_id']} g_local 不等于差值"
            assert row["g_local_ms"] > 0, f"{row['pair_id']} g_local 非正，需核查测量口径"
            for key in ("quality_full", "quality_cache"):
                assert row[key] in (0.0, 1.0), f"{row['pair_id']} {key} 不在 {0,1}"
            assert ">" in row["path_full"] and ">" in row["path_cache"], row["pair_id"]

    def branch_safe_and_quality():
        by_id = {row["req_id"]: row for row in branch}
        assert len(by_id) == len(branch), "branch 的 req_id 有重复，无法与研究口径一一对应"
        items = replay_branch()
        assert len(items) == len(branch), "重放的配对数与文件不一致"
        for item in items:
            req, cached = item["req"], item["cached"]
            row = by_id[req["req_id"]]
            got = predicate(raw, cached["req_id"], req["req_id"], "truth")
            assert got["safe"], f"{row['pair_id']} 收益配对并非真值安全"
            got_sys = predicate(raw, cached["req_id"], req["req_id"], "system")
            assert got_sys["safe"], f"{row['pair_id']} 收益配对系统视角不安全"
            task = raw.task_of(req["req_id"])
            snapshot = req["snapshot"]["index"]
            gold = executor.execute(snapshot, raw.tasks[task]["gold_sql"])
            assert not gold["error"], row["pair_id"]
            assert row["quality_full"] == 1.0, f"{row['pair_id']} quality_full 与重算不符"
            cached_sig = raw.sig(raw.task_of(cached["req_id"]), cached["snapshot"]["index"])
            expect = 1.0 if cached_sig == raw.sig(task, snapshot) else 0.0
            assert row["quality_cache"] == expect, f"{row['pair_id']} quality_cache 与重算不符"

    def branch_no_mock():
        blob = (LABELS / "branch_pairs.jsonl").read_text(encoding="utf-8")
        for bad in ("mock", "estimated", "simulated", "placeholder"):
            assert bad not in blob.lower(), f"配对文件出现可疑标记 {bad}"

    # -- 12 待复核清单 --------------------------------------------------
    def review_csv():
        head = (LABELS / "to_review.csv").read_text(encoding="utf-8").splitlines()[0]
        assert head.split(",") == REVIEW_HEAD, head
        assert len(reviews) >= PARAMS["labels"]["human_review"], len(reviews)
        by_type = {r["pair_id"]: r for r in labels}
        seen = Counter()
        div_seen = 0
        for row in reviews:
            assert row["pair_id"] in by_type, f"复核行 {row['pair_id']} 不在标签里"
            label = by_type[row["pair_id"]]
            assert row["predicate_safe"] == ("true" if label["safe"] else "false"), row["pair_id"]
            assert row["predicate_safe_system"] == \
                ("true" if label["safe_system"] else "false"), row["pair_id"]
            assert row["req_id"] == label["req_id"], row["pair_id"]
            assert row["cached_req_id"] == label["cached_req_id"], row["pair_id"]
            assert row["question"].strip() and row["old_answer_doc"].strip(), row["pair_id"]
            req = raw.reqs[label["req_id"]]
            for part in row["current_version_of_those_docs"].split(";"):
                m = re.fullmatch(
                    r"((?:fld_t\d{2}_\d{2})|(?:wp_\d{3})|(?:metric_\d{3})|(?:tool_\d{3})|"
                    r"(?:plan_\d{2})|(?:note_\d{3}))@v(\d+)(?:\(sys:v(\d+)\))?", part)
                assert m, f"{row['pair_id']} 版本列格式不符：{part}"
                doc_id, tv = m.group(1), int(m.group(2))
                assert doc_id in label["cached_doc_ids"], row["pair_id"]
                assert raw.truth_ver(doc_id, req["timestamp"]) == tv, row["pair_id"]
                if m.group(3) is not None:
                    assert raw.sys_ver(doc_id, req["timestamp"]) == int(m.group(3)), row["pair_id"]
            seen[label["negative_type"]] += 1
            if label["safe"] != label["safe_system"]:
                div_seen += 1
        for name in NEG_TYPES:
            if name in ("N5_side_effect",):
                continue
            assert seen[name] >= 10, f"复核清单 {name} 仅 {seen[name]} 条"
        assert seen["none"] >= 5, f"复核清单安全样本 {seen['none']} 条"
        assert div_seen >= 5, f"复核清单系统保守误失效样本仅 {div_seen} 条"

    # -- 13 确定性 ------------------------------------------------------
    def deterministic_labels():
        import build  # noqa: PLC0415  只调用纯函数，不落盘
        ds = build.Dataset()
        rebuilt = build.build_labels(ds)
        on_disk = list(io.read_jsonl(LABELS / "safe_reuse.jsonl"))
        assert rebuilt == on_disk, "同种子重算的 safe_reuse 与磁盘内容不一致"

    def deterministic_branch_selection():
        items = replay_branch()
        on_disk = list(io.read_jsonl(LABELS / "branch_pairs.jsonl"))
        got = sorted((raw.task_of(i["req"]["req_id"]), i["req"]["req_id"]) for i in items)
        want = sorted((r["task_id"], r["req_id"]) for r in on_disk)
        assert got == want, "同种子重算的分支配对选择与磁盘内容不一致"

    # -- 14 MANIFEST ----------------------------------------------------
    def manifest():
        record = io.read_json(LABELS / "MANIFEST.json")
        for name in ("safe_reuse.jsonl", "branch_pairs.jsonl", "to_review.csv"):
            path = LABELS / name
            assert name in record, f"MANIFEST 缺 {name}"
            assert record[name]["sha256"] == io.sha256_file(path), f"{name} 哈希与 MANIFEST 不符"
            with path.open("r", encoding="utf-8") as f:
                rows = sum(1 for _ in f) - (1 if path.suffix == ".csv" else 0)
            assert record[name]["rows"] == rows, f"{name} 行数与 MANIFEST 不符"

    for name, fn in (
        ("规模 300/120/60", sizes),
        ("字段固定（含 safe_system/divergence_reason）", fields),
        ("时间戳规则双视角谓词一致", predicate_agrees),
        ("系统安全⇒真值安全（300/300）", monotone),
        ("系统保守误失效样本（T,F）", divergent_cases),
        ("负例分布", distribution),
        ("负例构造约束", defects),
        ("难负例同簇比例", hard_same_cluster),
        ("reasons 可回溯", reasons_traceable),
        ("配对时序与题号", pair_semantics),
        ("分支配对字段与算术", branch_rows),
        ("分支配对安全性与质量", branch_safe_and_quality),
        ("无编造模型耗时", branch_no_mock),
        ("待复核清单", review_csv),
        ("同种子重跑一致（标签）", deterministic_labels),
        ("同种子重跑一致（配对选择）", deterministic_branch_selection),
        ("MANIFEST 自洽", manifest),
    ):
        check(name, fn)

    if FAIL:
        print(f"\n结果：{len(FAIL)} 项失败 -> {FAIL}")
        return 1
    print("\n结果：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

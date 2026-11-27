"""P5 安全复用标签（双视角）与分支配对构造器（v0.2.0，确定性可重跑）。

运行：
    python dataset/labels/build.py

产出（全部写在本目录）：
    safe_reuse.jsonl   300 条 —— 双视角安全复用标签（150 安全 + 150 负例）
    branch_pairs.jsonl 120 条 —— 全路径 / 缓存路径分支配对（本地时间实测，模型时间留空）
    to_review.csv       60 条 —— 人工复核清单（含系统视角判定列）
    MANIFEST.json             —— {文件: {rows, sha256}}

双视角口径（v0.2.0 契约新增 ``safe_system`` / ``divergence_reason``）
-------------------------------------------------------------------
每个文档在时刻 t 的可见版本（**一律按时间戳判定，不使用 update_events.old_ver**）：

    truth_ver(doc, t) = max{ v : docs_versioned[doc, v].updated_at <= t }     # 真值视角
    sys_ver(doc, t)   = max{ v : notified_at(doc, v) <= t }                   # 系统视角
    notified_at(doc, v) = update_events[doc, v].timestamp   若 (doc, v>=2) 有对应事件
                        = docs_versioned[doc, v].updated_at 否则（批量快照版本）

缓存条目持有的是系统在缓存时刻看到的证据版本；对同一 ``cached_doc_ids``：

- ``safe``（真值视角）：``truth_ver(doc, t_cached) == truth_ver(doc, t_req)`` 对每个文档成立；
- ``safe_system``（系统视角）：``sys_ver(doc, t_cached) == sys_ver(doc, t_req)`` 对每个文档成立；
- 两个视角都还要求：同一题目、证据集一致（cached 与 req 的 gold_doc_ids 相同）、
  权限相容（``priv(req) >= priv(cached)``）、时间窗一致。

**单调性的方向**：``sys_ver(t) <= truth_ver(t)``，批量升版即时通知，因此本数据里
“系统认为版本没变”必然意味着“真值也没变”，即 ``safe_system=True ⇒ safe=True`` 恒成立；
反方向不成立：``safe=True, safe_system=False`` 表示**系统保守误失效**——条目事实上仍然正确，
但通知刚到达、系统认为依赖变过而把它判为过期。``divergence_reason = system_stricter_window``。

设计要点
--------
1. 标签不是手写常量：构造器只挑配对，``view_judge(cached, req, view)`` 决定 safe / safe_system /
   negative_type 与 reasons，因此「标签 == 谓词输出」由构造保证，selfcheck 再独立复核一遍。
2. 谓词只读 ``events/``、``tasks/`` 与 ``db/snapshots/``；执行一律走 ``db/executor.py``
   （只读三层保护），结果比对一律走 ``db/compare.py``（列序/行序无关、数值 6 位）。
3. N1/N4/N6 三类难负例全部取**同一 cluster_id** 的两道题的请求对（意图相近、问法不同），
   使字面/语义相似度显著高于旧版跨簇构造；N2/N3 维持同题构造。
4. 随机只来自 ``common/seeds.py::rng("labels", name)``，同一 seed 下配对选择逐字节稳定；
   时间列由 perf_counter 实测，故 branch_pairs.jsonl 的文件哈希逐次不同。
"""
from __future__ import annotations

import bisect
import csv
import hashlib
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "labels"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

import compare  # noqa: E402
import executor  # noqa: E402
from common import ids, io, seeds  # noqa: E402

# 权限序：restricted 可见范围最大（限制最少），public 最小。
# 安全复用要求 req 至少和 cached 一样“看得多”，否则把宽权限内容喂给窄租户即越权。
PRIV = {"public": 1, "staff": 2, "restricted": 3}

SAFE_CLEAN_TARGET = 140       # 双视角都判安全的干净配对
DIVERGENCE_TARGET = 10        # 系统保守误失效（T,F）配对，计入 150 安全里
SAFE_TARGET = SAFE_CLEAN_TARGET + DIVERGENCE_TARGET
NEG_QUOTA = {
    "N1_entity_mismatch": 30,
    "N2_permission": 30,
    "N3_stale_but_looks_right": 35,
    "N4_time_window": 30,
    "N6_reasoning_chain": 25,
}
N3_SPLIT = {"answer_equal": 25, "answer_changed": 10}
HARD_CLASSES = ("N1_entity_mismatch", "N4_time_window", "N6_reasoning_chain")
NEG_TYPES = ("N1_entity_mismatch", "N2_permission", "N3_stale_but_looks_right",
             "N4_time_window", "N5_side_effect", "N6_reasoning_chain")
BRANCH_TARGET = 120
REVIEW_TARGET = 60

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}|[\u4e00-\u9fff]{2}")
_WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# 数据装载
# ---------------------------------------------------------------------------
class Dataset:
    """events/ + tasks/ + 快照的只读视图（全部经 common/io 读取）。"""

    def __init__(self) -> None:
        self.tasks = {t["task_id"]: t for t in io.read_jsonl(ROOT / "tasks" / "tasks.jsonl")}
        self.reqs = list(io.read_jsonl(ROOT / "events" / "request_stream.jsonl"))
        self.ctx = {c["req_id"]: c for c in io.read_jsonl(ROOT / "events" / "request_context.jsonl")}
        self.docs: dict[str, dict[int, dict]] = defaultdict(dict)
        for row in io.read_jsonl(ROOT / "events" / "docs_versioned.jsonl"):
            self.docs[row["doc_id"]][row["version"]] = row
        self.updates = list(io.read_jsonl(ROOT / "events" / "update_events.jsonl"))
        self.notified = self._notified_table()
        self._truth = self._ver_table(lambda row: row["updated_at"])
        self._sys = self._ver_table(lambda row: self.notified[row["doc_id"]][row["version"]])
        self.by_task: dict[str, list[dict]] = defaultdict(list)
        for req in self.reqs:
            self.by_task[self.task_of(req)].append(req)
        for rows in self.by_task.values():
            rows.sort(key=lambda r: (r["timestamp"], r["req_id"]))
        self.by_cluster: dict[str, list[str]] = defaultdict(list)
        for task_id, task in self.tasks.items():
            self.by_cluster[task["cluster_id"]].append(task_id)
        for tids in self.by_cluster.values():
            tids.sort()
        self._sig: dict[tuple[str, str], str] = {}
        self._chunk_hash: dict[tuple[str, int], dict[str, str]] = {}
        self._doc_text: dict[tuple[str, int], str] = {}
        self._tokens: dict[str, tuple[str, ...]] = {}
        # 题目 / 簇遍历顺序按 seed 洗牌：让候选截断不偏向 q001… 或字母序靠前的簇
        self.order: tuple[str, ...] = tuple(seeds.shuffle(sorted(self.tasks), "labels", "task_order"))
        self.cluster_order: tuple[str, ...] = tuple(
            seeds.shuffle(sorted(self.by_cluster), "labels", "cluster_order"))

    # -- 基础查询 ---------------------------------------------------------
    def task_of(self, req: dict) -> str:
        return self.ctx[req["req_id"]]["task_id"]

    def task(self, req: dict) -> dict:
        return self.tasks[self.task_of(req)]

    def cluster_of(self, req: dict) -> str:
        return req["cluster_id"]

    def _notified_table(self) -> dict[str, dict[int, str]]:
        out: dict[str, dict[int, str]] = defaultdict(dict)
        for doc_id, versions in self.docs.items():
            for ver, row in versions.items():
                out[doc_id][ver] = row["updated_at"]
        for event in self.updates:
            out[event["doc_id"]][event["new_ver"]] = event["timestamp"]
        return out

    def _ver_table(self, stamp) -> dict[str, dict]:
        table: dict[str, dict] = {}
        for doc_id, versions in self.docs.items():
            rows = sorted((stamp(versions[ver]), ver) for ver in versions)
            table[doc_id] = {"keys": [s for s, _ in rows], "versions": [v for _, v in rows]}
        return table

    def _ver_at(self, table: dict, doc_id: str, timestamp: str) -> int:
        keys = table[doc_id]["keys"]
        idx = bisect.bisect_right(keys, timestamp) - 1
        assert idx >= 0, f"{doc_id} 在 {timestamp} 无可见版本"
        return table[doc_id]["versions"][idx]

    def truth_ver(self, doc_id: str, timestamp: str) -> int:
        return self._ver_at(self._truth, doc_id, timestamp)

    def sys_ver(self, doc_id: str, timestamp: str) -> int:
        return self._ver_at(self._sys, doc_id, timestamp)

    def notified_at(self, doc_id: str, version: int) -> str:
        return self.notified[doc_id][version]

    def effective_at(self, doc_id: str, version: int) -> str:
        return self.docs[doc_id][version]["updated_at"]

    def chunk_hashes(self, doc_id: str, version: int) -> dict[str, str]:
        key = (doc_id, version)
        got = self._chunk_hash.get(key)
        if got is None:
            got = {c["chunk_id"]: (c.get("hash") or io.sha256_text(c["text"])[:16])
                   for c in self.docs[doc_id][version]["chunks"]}
            self._chunk_hash[key] = got
        return got

    def doc_text(self, doc_id: str, version: int) -> str:
        key = (doc_id, version)
        got = self._doc_text.get(key)
        if got is None:
            got = "".join(c["text"] for c in self.docs[doc_id][version]["chunks"])
            self._doc_text[key] = got
        return got

    def tokens(self, text: str, limit: int = 24) -> tuple[str, ...]:
        got = self._tokens.get(text)
        if got is None:
            seen: list[str] = []
            for m in _TOKEN_RE.finditer(text):
                word = m.group()
                if word not in seen:
                    seen.append(word)
                    if len(seen) >= limit:
                        break
            got = tuple(seen)
            self._tokens[text] = got
        return got

    def result_sig(self, task_id: str, snapshot: str) -> str:
        """gold_sql 在某快照上执行结果的规范化哈希（列序/行序无关）。"""
        key = (task_id, snapshot)
        got = self._sig.get(key)
        if got is None:
            out = executor.execute(snapshot, self.tasks[task_id]["gold_sql"])
            assert not out["error"], f"{task_id} 在 {snapshot} 上执行失败：{out['error']}"
            rows = compare.normalize(out)["rows"]
            got = hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
            self._sig[key] = got
        return got


# ---------------------------------------------------------------------------
# 双视角谓词（严格按时间戳取可见版本，不使用 old_ver）
# ---------------------------------------------------------------------------
def view_judge(ds: Dataset, cached: dict, req: dict, view: str) -> dict:
    """单视角安全复用判定。

    ``view="truth"`` 用文档真实生效时刻取版本（safe）；
    ``view="system"`` 用系统 notified_at 取版本（safe_system）。

    条件：
        A 同一题目     task_id 相同
        B 证据集一致   cached 与 req 的 gold_doc_ids 相同
        C 版本未变     对 cached_doc_ids 每个文档：view 在 cached/req 两个时刻的可见版本相同
        D 权限相容     priv(req) >= priv(cached)
        E 时间窗一致   两题目 time_window 完全一致
    """
    t_c, t_r = ds.task(cached), ds.task(req)
    cur = ds.truth_ver if view == "truth" else ds.sys_ver
    versions: list[tuple[str, int]] = []
    changes: list[tuple[str, int, int]] = []
    for doc_id in cached["gold_doc_ids"]:
        va = cur(doc_id, cached["timestamp"])
        vb = cur(doc_id, req["timestamp"])
        versions.append((doc_id, va))
        if va != vb:
            changes.append((doc_id, va, vb))
    checks = {
        "A": t_c["task_id"] == t_r["task_id"],
        "B": cached["gold_doc_ids"] == req["gold_doc_ids"],
        "C": not changes,
        "D": PRIV[req["permission"]] >= PRIV[cached["permission"]],
        "E": t_c["time_window"] == t_r["time_window"],
    }
    return {"safe": all(checks.values()), "view": view, "checks": checks,
            "versions": versions, "changes": changes}


def classification(ds: Dataset, cached: dict, req: dict) -> str:
    """真值视角的负例分类（与旧版一致：先权限，再时间窗，再同题过期，再链条，最后实体）。"""
    j = view_judge(ds, cached, req, "truth")
    ch = j["checks"]
    if j["safe"]:
        return "none"
    if not ch["D"]:
        return "N2_permission"
    shared = sorted(set(ds.task(cached)["metric_refs"]) & set(ds.task(req)["metric_refs"]))
    if (not ch["E"]) and (not ch["A"]) and shared:
        return "N4_time_window"
    if ch["A"] and not ch["C"]:
        return "N3_stale_but_looks_right"
    if set(req["obj_types"]) > set(cached["obj_types"]) and not ch["A"]:
        return "N6_reasoning_chain"
    return "N1_entity_mismatch"


# ---------------------------------------------------------------------------
# reasons
# ---------------------------------------------------------------------------
def _flavor_answer(ds: Dataset, cached: dict, req: dict) -> tuple[bool, str]:
    """答案是否仍相等（B 子判定，只用于 N3 子族与 reasons 描述，不进入 safe 谓词）。"""
    task_id = ds.task_of(cached)
    snap_c, snap_r = cached["snapshot"]["index"], req["snapshot"]["index"]
    equal = ds.result_sig(task_id, snap_c) == ds.result_sig(task_id, snap_r)
    return equal, f"{snap_c}=={snap_r}" if equal else f"{snap_c}!={snap_r}"


def reasons_for(ds: Dataset, cached: dict, req: dict, truth_j: dict, sys_j: dict) -> list[str]:
    """把判定落成可回溯字符串；每条都能被 selfcheck 用原始数据独立复核。"""
    t_c, t_r = ds.task(cached), ds.task(req)
    snap_c, snap_r = cached["snapshot"]["index"], req["snapshot"]["index"]
    out: list[str] = []
    safe = truth_j["safe"]
    safe_system = sys_j["safe"]

    if safe and safe_system:                      # 干净安全配对
        out.append(f"same_task:{t_c['task_id']}")
        out.append(f"evidence_set_equal:{len(cached['gold_doc_ids'])}")
        for doc_id, ver in truth_j["versions"]:
            out.append(f"version_unchanged:{doc_id}:truth=v{ver}"
                       f":sys=v{ds.sys_ver(doc_id, cached['timestamp'])}")
        out.append(f"permission_ok:{cached['permission']}->{req['permission']}")
        out.append(f"time_window_equal:{t_r['time_window']['start']}~{t_r['time_window']['end']}")
        return out

    if safe and not safe_system:                  # 系统保守误失效（T,F）
        out.append(f"same_task:{t_c['task_id']}")
        out.append(f"evidence_set_equal:{len(cached['gold_doc_ids'])}")
        for doc_id, ver in truth_j["versions"]:
            out.append(f"truth_stable:{doc_id}@v{ver}")
        for doc_id, va, vb in sys_j["changes"]:
            out.append(f"sys_version_changed:{doc_id}:v{va}->v{vb}")
            out.append(f"system_stricter_window:{doc_id}"
                       f"|cached={cached['timestamp']}"
                       f"|effective={ds.effective_at(doc_id, vb)}"
                       f"|notified={ds.notified_at(doc_id, vb)}"
                       f"|req={req['timestamp']}")
        out.append(f"permission_ok:{cached['permission']}->{req['permission']}")
        out.append(f"time_window_equal:{t_r['time_window']['start']}~{t_r['time_window']['end']}")
        return out

    neg = classification(ds, cached, req)

    if neg == "N3_stale_but_looks_right":
        out.append(f"same_task:{t_c['task_id']}")
        out.append(f"evidence_set_equal:{len(cached['gold_doc_ids'])}")
        for doc_id, va, vb in truth_j["changes"]:
            out.append(f"truth_version_changed:{doc_id}:v{va}->v{vb}")
        for doc_id, va, vb in sys_j["changes"]:
            out.append(f"sys_version_changed:{doc_id}:v{va}->v{vb}")
        equal, pair = _flavor_answer(ds, cached, req)
        out.append(f"answer_equal:{pair}" if equal else f"answer_changed:{t_c['task_id']}:{pair}")
        out.append(f"permission_ok:{cached['permission']}->{req['permission']}")
        out.append(f"time_window_equal:{t_r['time_window']['start']}~{t_r['time_window']['end']}")
        return out

    if neg == "N2_permission":
        out.append(f"same_task:{t_c['task_id']}")
        out.append(f"permission_mismatch:{cached['permission']}->{req['permission']}")
        return out

    if neg == "N4_time_window":
        wc, wr = t_c["time_window"], t_r["time_window"]
        out.append(f"time_window_mismatch:{wc['start']}~{wc['end']}|{wr['start']}~{wr['end']}")
        out.append(f"shared_metric:{sorted(set(t_c['metric_refs']) & set(t_r['metric_refs']))[0]}")
        out.append(f"task_mismatch:{t_c['task_id']}->{t_r['task_id']}")
        out.append(f"same_cluster:{req['cluster_id']}")
        return out

    if neg == "N6_reasoning_chain":
        out.append("chain_missing:" + ",".join(cached["obj_types"]) + "|" + ",".join(req["obj_types"]))
        out.append(f"task_mismatch:{t_c['task_id']}->{t_r['task_id']}")
        out.append(f"shared_metric:{sorted(set(t_c['metric_refs']) & set(t_r['metric_refs']))[0]}")
        out.append(f"same_cluster:{req['cluster_id']}")
        return out

    # N1
    out.append(f"task_mismatch:{t_c['task_id']}->{t_r['task_id']}")
    out.append("disjoint_metric:" + ",".join(sorted(t_c["metric_refs"])) + "|"
               + ",".join(sorted(t_r["metric_refs"])))
    out.append(f"same_cluster:{req['cluster_id']}")
    return out


# ---------------------------------------------------------------------------
# 配对候选
# ---------------------------------------------------------------------------
def same_task_pairs(ds: Dataset):
    """同一题目的有序请求对（cached 不晚于 req），题目按 seed 洗牌遍历。"""
    for task_id in ds.order:
        rows = ds.by_task[task_id]
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                yield rows[i], rows[j]


def _request_pairs_for(ds: Dataset, a: str, b: str):
    for rc in ds.by_task[a]:
        for rr in ds.by_task[b]:
            if rc["timestamp"] <= rr["timestamp"]:
                yield rc, rr


def cluster_task_pairs(ds: Dataset, task_filter):
    """遍历同簇题对（簇按 seed 洗牌、簇内按 task_id 排序），先做便宜的题级过滤。"""
    for cluster_id in ds.cluster_order:
        tids = ds.by_cluster[cluster_id]
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                a, b = tids[i], tids[j]
                if task_filter(ds, a, b):
                    yield cluster_id, a, b


def _window(task: dict) -> tuple[str, str]:
    return task["time_window"]["start"], task["time_window"]["end"]


def _chain(ds: Dataset, task_id: str) -> set[str]:
    return set(ds.by_task[task_id][0]["obj_types"])


def pick(pool: list[dict], want: int, name: str, *, key=None, max_per: int = 0) -> list[dict]:
    """按 seed 洗牌后取前 want 条；池子不够直接失败，绝不重复硬凑。"""
    assert len(pool) >= want, f"{name} 候选仅 {len(pool)} 条，不足 {want} 条"
    shuffled = seeds.shuffle(pool, "labels", f"pick:{name}")
    if not max_per or key is None:
        return shuffled[:want]
    out: list[dict] = []
    seen: dict[object, int] = defaultdict(int)
    for item in shuffled:
        k = key(item)
        if seen[k] >= max_per:
            continue
        seen[k] += 1
        out.append(item)
        if len(out) >= want:
            return out
    raise AssertionError(f"{name} 限制每 key {max_per} 条后仅 {len(out)} 条，不足 {want} 条")


def _is_same_task_clean(ds: Dataset, rc: dict, rr: dict) -> tuple[dict, dict]:
    jt = view_judge(ds, rc, rr, "truth")
    js = view_judge(ds, rc, rr, "system")
    return jt, js


def collect_same_task(ds: Dataset, kind: str, cap: int, per_task: int = 0) -> list[dict]:
    """同题候选。

    kind: safe | divergence | N2 | N3:answer_equal | N3:answer_changed
    """
    out: list[dict] = []
    used: dict[str, int] = defaultdict(int)
    for rc, rr in same_task_pairs(ds):
        task_id = ds.task_of(rc)
        if per_task and used[task_id] >= per_task:
            continue
        jt, js = _is_same_task_clean(ds, rc, rr)
        neg = classification(ds, rc, rr)
        if kind == "safe":
            ok = jt["safe"] and js["safe"]
        elif kind == "divergence":
            ok = jt["safe"] and (not js["safe"])
            if ok:
                # 每条系统版本变化都必须落在“缓存已过生效时刻、请求已过通知时刻”的窗口里
                for doc_id, va, vb in js["changes"]:
                    if not (ds.effective_at(doc_id, vb) <= rc["timestamp"]
                            and ds.notified_at(doc_id, vb) <= rr["timestamp"]
                            and rc["timestamp"] < ds.notified_at(doc_id, vb)):
                        ok = False
                        break
        elif kind == "N2":
            ok = ((not jt["safe"]) and (not js["safe"]) and neg == "N2_permission"
                  and jt["checks"]["B"] and jt["checks"]["C"] and js["checks"]["C"])
        elif kind.startswith("N3:"):
            flavor = kind.split(":", 1)[1]
            ok = ((not jt["safe"]) and (not js["safe"]) and neg == "N3_stale_but_looks_right"
                  and jt["checks"]["B"] and bool(jt["changes"]) and bool(js["changes"]))
            if ok:
                equal, _ = _flavor_answer(ds, rc, rr)
                ok = (flavor == "answer_equal") == equal
        else:
            raise ValueError(kind)
        if not ok:
            continue
        used[task_id] += 1
        out.append({"cached": rc, "req": rr, "judge": jt, "sys_judge": js})
        if len(out) >= cap:
            return out
    return out


def _cluster_task_filter(ds: Dataset, target: str):
    if target == "N1_entity_mismatch":
        def task_filter(ds_, a, b):
            if _window(ds_.tasks[a]) != _window(ds_.tasks[b]):
                return False
            ma, mb = set(ds_.tasks[a]["metric_refs"]), set(ds_.tasks[b]["metric_refs"])
            if not ma or not mb or (ma & mb):
                return False
            ca, cb = _chain(ds_, a), _chain(ds_, b)
            return cb <= ca or ca <= cb
    elif target == "N4_time_window":
        def task_filter(ds_, a, b):
            if _window(ds_.tasks[a]) == _window(ds_.tasks[b]):
                return False
            return bool(set(ds_.tasks[a]["metric_refs"]) & set(ds_.tasks[b]["metric_refs"]))
    elif target == "N6_reasoning_chain":
        def task_filter(ds_, a, b):
            if _window(ds_.tasks[a]) != _window(ds_.tasks[b]):
                return False
            if not (set(ds_.tasks[a]["metric_refs"]) & set(ds_.tasks[b]["metric_refs"])):
                return False
            ca, cb = _chain(ds_, a), _chain(ds_, b)
            return not (ca <= cb and cb <= ca)
    else:
        raise ValueError(target)
    return task_filter


def collect_same_cluster(ds: Dataset, target: str, cap: int, per_pair: int = 0) -> list[dict]:
    """同簇难负例：N1/N4/N6 只从同一 cluster_id 的两道题之间取请求对。"""
    task_filter = _cluster_task_filter(ds, target)
    out: list[dict] = []
    used: dict[tuple[str, str], int] = defaultdict(int)
    for _, a, b in cluster_task_pairs(ds, task_filter):
        for ta, tb in ((a, b), (b, a)):
            pair_key = (ta, tb)
            if per_pair and used[pair_key] >= per_pair:
                continue
            for rc, rr in _request_pairs_for(ds, ta, tb):
                if per_pair and used[pair_key] >= per_pair:
                    break
                jt, js = _is_same_task_clean(ds, rc, rr)
                if jt["safe"] or js["safe"] or classification(ds, rc, rr) != target:
                    continue
                used[pair_key] += 1
                out.append({"cached": rc, "req": rr, "judge": jt, "sys_judge": js})
                if len(out) >= cap:
                    return out
    return out


# ---------------------------------------------------------------------------
# safe_reuse.jsonl
# ---------------------------------------------------------------------------
def build_labels(ds: Dataset) -> list[dict]:
    picked: list[tuple[str, dict]] = []
    task_key = lambda item: ds.task_of(item["req"])  # noqa: E731

    pool = collect_same_task(ds, "safe", cap=SAFE_CLEAN_TARGET * 30, per_task=12)
    picked += [("none", item) for item in
               pick(pool, SAFE_CLEAN_TARGET, "safe", key=task_key, max_per=2)]

    pool = collect_same_task(ds, "divergence", cap=DIVERGENCE_TARGET * 30, per_task=8)
    picked += [("none", item) for item in
               pick(pool, DIVERGENCE_TARGET, "divergence", key=task_key, max_per=2)]

    pool = collect_same_task(ds, "N2", cap=NEG_QUOTA["N2_permission"] * 20, per_task=8)
    picked += [("N2_permission", item) for item in
               pick(pool, NEG_QUOTA["N2_permission"], "N2", key=task_key, max_per=2)]

    for flavor, want in N3_SPLIT.items():
        pool = collect_same_task(ds, f"N3:{flavor}", cap=want * 20, per_task=8)
        picked += [("N3_stale_but_looks_right", item) for item in
                   pick(pool, want, f"n3:{flavor}", key=task_key, max_per=2)]

    for target in HARD_CLASSES:
        want = NEG_QUOTA[target]
        pool = collect_same_cluster(ds, target, cap=want * 20,
                                    per_pair=4 if target == "N6_reasoning_chain" else 2)
        pair_key = lambda item: tuple(sorted((ds.task_of(item["cached"]),  # noqa: E731
                                              ds.task_of(item["req"]))))
        picked += [(target, item) for item in
                   pick(pool, want, target, key=pair_key,
                        max_per=4 if target == "N6_reasoning_chain" else 2)]

    rows = []
    for target, item in picked:
        cached, req, jt, js = item["cached"], item["req"], item["judge"], item["sys_judge"]
        assert (jt["safe"] and js["safe"]) or (not jt["safe"] and not js["safe"]) \
            or (jt["safe"] and not js["safe"]), "系统安全必然真值安全"
        if target == "none":
            assert jt["safe"], (req["req_id"], cached["req_id"])
        if target in HARD_CLASSES:
            assert ds.cluster_of(req) == ds.cluster_of(cached) == req["cluster_id"], \
                (target, req["req_id"])
        diverged = jt["safe"] != js["safe"]
        rows.append({
            "pair_id": "",
            "req_id": req["req_id"],
            "cached_req_id": cached["req_id"],
            "task_id": ds.task_of(req),
            "cached_doc_ids": list(cached["gold_doc_ids"]),
            "safe": bool(jt["safe"]),
            "safe_system": bool(js["safe"]),
            "divergence_reason": "system_stricter_window" if diverged else "",
            "negative_type": target,
            "reasons": reasons_for(ds, cached, req, jt, js),
            "judged_by": "predicate",
            "confidence": 1.0,
        })
    rows.sort(key=lambda r: (r["negative_type"] != "none", r["negative_type"],
                             r["req_id"], r["cached_req_id"]))
    for i, row in enumerate(rows, start=1):
        row["pair_id"] = ids.branch_pair_id(i)
    return rows


# ---------------------------------------------------------------------------
# 本地检索 + 有效性检查（分支配对的成本口径）
# ---------------------------------------------------------------------------
class LocalPaths:
    """全路径与缓存路径的本地可测部分：检索 / SQL 执行 / 缓存查找 / 有效性检查。

    口径说明：``retrieve`` 是版本化块索引上的词项匹配检索（域名预筛 + 词项计数打分，
    取 top-k），用来代表“检索”这一段本地成本；SQL 载荷用题目自身 gold_sql，
    因为作者模型的 SQL 生成与作答耗时属于 t_model（本阶段不测、一律 null）。
    证据版本按**系统可见版本**取，与缓存条目落盘口径一致。
    """

    TOP_K = 5

    def __init__(self, ds: Dataset) -> None:
        self.ds = ds

    def retrieve(self, req: dict) -> list[dict]:
        ds = self.ds
        terms = ds.tokens(req["query_text"])
        ref = PRIV[req["permission"]]
        scored = []
        for doc_id in ds.docs:
            version = ds.sys_ver(doc_id, req["timestamp"])
            row = ds.docs[doc_id][version]
            # ACL 预筛：只检索请求权限可见的文档（真实检索层的第一道过滤）
            if row["domain"] != req["domain"] or PRIV[row["permission"]] > ref:
                continue
            text = ds.doc_text(doc_id, version)
            score = 0
            for term in terms:
                score += text.count(term)
            if score:
                scored.append((-score, doc_id, version))
        scored.sort()
        out = []
        for _, doc_id, version in scored[:self.TOP_K]:
            out.append({"doc_id": doc_id, "version": version,
                        "chunks": [{"chunk_id": cid, "hash": h}
                                   for cid, h in ds.chunk_hashes(doc_id, version).items()]})
        return out

    def validate(self, evidence: list[dict], req: dict) -> bool:
        """有效性检查：版本仍是系统在请求时刻可见版本 + 块 hash 与索引一致 + 权限允许。"""
        ds = self.ds
        ok = True
        ref = PRIV[req["permission"]]
        for item in evidence:
            doc_id = item["doc_id"]
            if ds.sys_ver(doc_id, req["timestamp"]) != item["version"]:
                ok = False
            if PRIV[ds.docs[doc_id][item["version"]]["permission"]] > ref:
                ok = False
            index = ds.chunk_hashes(doc_id, item["version"])
            for chunk in item["chunks"]:
                if index.get(chunk["chunk_id"]) != chunk["hash"]:
                    ok = False
        return ok

    def cache_lookup(self, cached: dict, req: dict) -> dict:
        """缓存对象：cached 时刻系统可见版本上的答案签名与证据（键 = 题目 + 快照）。"""
        ds = self.ds
        task_id = ds.task_of(cached)
        evidence = []
        for doc_id in cached["gold_doc_ids"]:
            version = ds.sys_ver(doc_id, cached["timestamp"])
            hashes = ds.chunk_hashes(doc_id, version)
            evidence.append({
                "doc_id": doc_id,
                "version": version,
                "chunks": [{"chunk_id": s["chunk_id"], "hash": hashes.get(s["chunk_id"])}
                           for s in cached["gold_fact_spans"]
                           if s["chunk_id"].startswith(doc_id + "#")],
            })
        return {"task_id": task_id,
                "snapshot": cached["snapshot"]["index"],
                "answer_sig": ds.result_sig(task_id, cached["snapshot"]["index"]),
                "evidence": evidence}


def _time(fn, *args):
    started = time.perf_counter()
    out = fn(*args)
    return out, (time.perf_counter() - started) * 1000.0


def measure_pair(ds: Dataset, paths: LocalPaths, cached: dict, req: dict,
                 reps: int = 5) -> dict:
    """单个配对重复 5 次取中位数。

    全路径本地段 = 检索 + SQL 执行 + 有效性检查；缓存路径本地段 = 命中查找 + 有效性检查。
    """
    task = ds.task(req)
    snapshot = req["snapshot"]["index"]
    gold_sig = ds.result_sig(task["task_id"], snapshot)
    full_totals: list[float] = []
    cache_totals: list[float] = []
    evidence_full = evidence_cached = None
    answer_sig_cache = None
    sql_out = None
    for _ in range(reps):
        evidence_full, t_retrieve = _time(paths.retrieve, req)
        sql_out, t_sql = _time(executor.execute, snapshot, task["gold_sql"])
        _, t_valid_full = _time(paths.validate, evidence_full, req)
        full_totals.append(t_retrieve + t_sql + t_valid_full)
        cached_obj, t_lookup = _time(paths.cache_lookup, cached, req)
        _, t_valid_cache = _time(paths.validate, cached_obj["evidence"], req)
        cache_totals.append(t_lookup + t_valid_cache)
        answer_sig_cache = cached_obj["answer_sig"]
        evidence_cached = cached_obj["evidence"]

    gold = executor.execute(snapshot, task["gold_sql"])
    ok_full = compare.compare(sql_out, gold)["equal"] and paths.validate(evidence_full, req)
    ok_cache = answer_sig_cache == gold_sig and paths.validate(evidence_cached, req)
    return {
        "t_local_full_ms": round(statistics.median(full_totals), 3),
        "t_local_cache_ms": round(statistics.median(cache_totals), 3),
        "quality_full": 1.0 if ok_full else 0.0,
        "quality_cache": 1.0 if ok_cache else 0.0,
    }


def select_branch(ds: Dataset, taken: set[tuple[str, str]]) -> list[dict]:
    """选出 120 个「全路径 vs 缓存路径」配对（与测量分离，便于重放核对）。

    每个 req 只出现一次，同一题目最多 2 条，避免 branch 文件内部重复。
    """
    pool = collect_same_task(ds, "safe", cap=BRANCH_TARGET * 40, per_task=12)
    fresh = [item for item in pool
             if (item["cached"]["req_id"], item["req"]["req_id"]) not in taken]
    shuffled = seeds.shuffle(fresh, "labels", "pick:branch")
    out: list[dict] = []
    used_req: set[str] = set()
    per_task: dict[str, int] = defaultdict(int)
    for item in shuffled:
        req = item["req"]
        task_id = ds.task_of(req)
        if req["req_id"] in used_req or per_task[task_id] >= 2:
            continue
        used_req.add(req["req_id"])
        per_task[task_id] += 1
        out.append(item)
        if len(out) >= BRANCH_TARGET:
            return out
    raise AssertionError(f"branch 去重后仅 {len(out)} 条，不足 {BRANCH_TARGET} 条")


def build_branch(ds: Dataset, taken: set[tuple[str, str]], first_seq: int) -> list[dict]:
    """120 条分支配对：全部为双视角都判安全的配对（真实收益行）。"""
    paths = LocalPaths(ds)
    chosen = select_branch(ds, taken)

    rows = []
    for item in chosen:
        cached, req = item["cached"], item["req"]
        assert view_judge(ds, cached, req, "truth")["safe"], (req["req_id"], cached["req_id"])
        measured = measure_pair(ds, paths, cached, req)
        chain = list(req["obj_types"])
        full = chain[:chain.index("resp")] + ["sql", "resp"] if "resp" in chain else chain + ["sql"]
        rows.append({
            "pair_id": "",
            "req_id": req["req_id"],
            "task_id": ds.task_of(req),
            "path_full": ">".join(full),
            "path_cache": "cache>validate>resp",
            "t_local_full_ms": measured["t_local_full_ms"],
            "t_local_cache_ms": measured["t_local_cache_ms"],
            "g_local_ms": round(measured["t_local_full_ms"] - measured["t_local_cache_ms"], 3),
            "t_model_full_ms": None,
            "t_model_cache_ms": None,
            "quality_full": measured["quality_full"],
            "quality_cache": measured["quality_cache"],
            "measured": True,
            "note": "requires_author_model_run",
        })
    rows.sort(key=lambda r: (r["task_id"], r["req_id"]))
    for i, row in enumerate(rows, start=1):
        row["pair_id"] = ids.branch_pair_id(first_seq + i - 1)
    return rows


# ---------------------------------------------------------------------------
# to_review.csv
# ---------------------------------------------------------------------------
def build_review(ds: Dataset, label_rows: list[dict]) -> list[dict]:
    """60 条：五类负例各 10 条 + 10 条安全样本（含 5 条系统保守误失效）。"""
    by_class: dict[str, list[dict]] = defaultdict(list)
    for row in label_rows:
        by_class[row["negative_type"]].append(row)
    picked: list[dict] = []
    for neg in NEG_TYPES:
        if neg == "N5_side_effect":
            continue
        picked += by_class[neg][:10]
    none_rows = by_class["none"]
    divergent = [r for r in none_rows if r["safe"] != r["safe_system"]]
    clean = [r for r in none_rows if r["safe"] == r["safe_system"]]
    picked += divergent[:5] + clean[:5]
    assert len(picked) >= REVIEW_TARGET, len(picked)

    by_id = {r["req_id"]: r for r in ds.reqs}
    out = []
    for row in picked:
        req = by_id[row["req_id"]]
        cached = by_id[row["cached_req_id"]]
        task = ds.task(req)
        docs = cached["gold_doc_ids"]
        current = []
        for d in docs:
            tv = ds.truth_ver(d, req["timestamp"])
            sv = ds.sys_ver(d, req["timestamp"])
            current.append(f"{d}@v{tv}" if tv == sv else f"{d}@v{tv}(sys:v{sv})")
        out.append({
            "pair_id": row["pair_id"],
            "req_id": row["req_id"],
            "cached_req_id": row["cached_req_id"],
            "question": _WS_RE.sub(" ", task["question"]).strip(),
            "old_answer_doc": ";".join(docs),
            "current_version_of_those_docs": ";".join(current),
            "predicate_safe": "true" if row["safe"] else "false",
            "predicate_safe_system": "true" if row["safe_system"] else "false",
            "predicate_reason": ";".join(row["reasons"]),
        })
    return out


# ---------------------------------------------------------------------------
# 落盘
# ---------------------------------------------------------------------------
def write_review(path: Path, rows: list[dict]) -> int:
    head = ["pair_id", "req_id", "cached_req_id", "question", "old_answer_doc",
            "current_version_of_those_docs", "predicate_safe", "predicate_safe_system",
            "predicate_reason"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=head, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


def write_manifest(files: list[Path]) -> dict:
    manifest = {}
    for path in files:
        with path.open("r", encoding="utf-8") as f:
            rows = sum(1 for _ in f) - (1 if path.suffix == ".csv" else 0)
        manifest[path.name] = {"rows": rows, "sha256": io.sha256_file(path)}
    io.write_json(LABELS / "MANIFEST.json", manifest)
    return manifest


def main() -> int:
    started = time.perf_counter()
    ds = Dataset()
    print(f"装载：题目 {len(ds.tasks)}，请求 {len(ds.reqs)}，文档 {len(ds.docs)}，"
          f"更新事件 {len(ds.updates)}，簇 {len(ds.by_cluster)}")

    labels = build_labels(ds)
    taken = {(r["cached_req_id"], r["req_id"]) for r in labels}
    branch = build_branch(ds, taken, first_seq=len(labels) + 1)
    review = build_review(ds, labels)

    io.write_jsonl(LABELS / "safe_reuse.jsonl", labels)
    io.write_jsonl(LABELS / "branch_pairs.jsonl", branch)
    write_review(LABELS / "to_review.csv", review)
    manifest = write_manifest([LABELS / "safe_reuse.jsonl",
                               LABELS / "branch_pairs.jsonl",
                               LABELS / "to_review.csv"])

    dist: dict[str, int] = defaultdict(int)
    for row in labels:
        dist[row["negative_type"]] += 1
    hard = [r for r in labels if r["negative_type"] in HARD_CLASSES]
    by_req = {r["req_id"]: r for r in ds.reqs}
    same_cluster = sum(1 for r in hard
                       if by_req[r["req_id"]]["cluster_id"] == by_req[r["cached_req_id"]]["cluster_id"])
    diverged = [r for r in labels if r["safe"] != r["safe_system"]]
    print("safe_reuse:", len(labels), "安全", dist["none"],
          "负例", {k: v for k, v in sorted(dist.items()) if k != "none"})
    print("双视角分歧:", len(diverged),
          "方向:", sorted({(r["safe"], r["safe_system"]) for r in diverged}),
          "原因:", sorted({r["divergence_reason"] for r in diverged}))
    print(f"难负例同簇: {same_cluster}/{len(hard)} = {same_cluster / len(hard):.3f}")
    print("branch_pairs:", len(branch), "to_review:", len(review))
    print("g_local 中位数", statistics.median(r["g_local_ms"] for r in branch), "ms")
    print("哈希：", {k: v["sha256"][:16] + "…" for k, v in manifest.items()})
    print(f"耗时 {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""P4 事件层构建器（v0.2.0，确定性，可重跑）。

产出（只写 dataset/events/）：

  docs_versioned.jsonl        knowledge/docs.jsonl 的 docs_versioned 投影（6000 行，内容不改写）
  request_stream.jsonl        主请求流 3000 条（= streams/seed42.jsonl，逐字节相同）
  update_events.jsonl         40 条主更新（双时间戳 + 6 条 negative_control 负对照）
  act_plan_pool.json          100 个 act（tool_001…tool_100）+ 60 个 plan（plan_01…plan_60）
  streams/seed42..seed46      5 个种子副本，各 3000 条，热点迁移时刻不同
  streams/long_01,long_02     2 条长流，各 5000 条，跨度仍是 18 小时
  request_context.jsonl       主请求流 sidecar：租户、源题、改写序号、复用标记、权限负例、簇
  MANIFEST.json               文件 / 行数 / sha256 / 统计，由本脚本生成

本版相对 v0.1.x 的五组变化（对应 contracts/CHANGELOG.md v0.2.0）：

1. 请求流增加语义簇 ``cluster_id``（取自所源题目），7 条流与 sidecar 同步；
2. ``gold_fact_spans`` 逐条取自 ``tasks.jsonl`` 的主张层真值（每题 1–5 条，不再恒为 2），
   ``gold_doc_ids`` 取该题证据文档并集；
3. 更新事件改**双时间戳**：``effective_at`` 恒等于该 ``(doc_id, new_ver)`` 在 docs_versioned
   中的 ``updated_at``，``notification_delay_s`` = ``timestamp − effective_at``，落在
   0.03–3.08 小时的参考区间且中位约 1.6 小时；6 条 codebook_revision 标 ``negative_control``；
4. 重选 40 条更新使受影响 (更新, 请求) 对的局部修复占比 ρ 落入 params 的 [0.65, 0.75]：
   优先打中主张数 3–5 的请求，保留少量命中 ≥2 条主张的大改样本；
5. act_plan_pool：``downstream_tools`` 由 ``contracts/lineage.json`` 的血缘下游推导，
   ``completion_rate`` 按步骤数落进 params 的分层区间。

两条硬约束（决定了下面所有时间取值）：

1. 快照与版本同一时轴：文档版本 1/2/3 与快照 v0/v1/v2 都在 00:00 / 06:00 / 12:00 生效。
   请求的 ``snapshot.index`` 只能是其 ``timestamp`` 时刻已生效的最新快照，
   ``snapshot.as_of`` 取该快照的生效时刻，禁止引用未来快照。
2. 更新事件描述的是「某个文档从 old_ver 变成 new_ver」这一既成事实，因此其 timestamp 不得早于
   ``effective_at``（= new_ver 的 updated_at，06:00 / 12:00）；否则与 docs_versioned 冲突。

随机性：只经 ``common/seeds.py::rng(stage, name)``；ID 只经 ``common/ids.py``；
写盘只经 ``common/io.py``。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:                      # 允许 python events/build.py 直接运行
    sys.path.insert(0, str(ROOT))

from common import ids, io, seeds  # noqa: E402

STAGE = "events"

# ---- 时轴 -----------------------------------------------------------------
DAY = datetime(2024, 5, 15, tzinfo=timezone.utc)
PARAMS = io.read_json(ROOT / "config" / "params.json")
SPAN_HOURS = int(PARAMS["streams"]["time_span_hours"])
SPAN_SEC = SPAN_HOURS * 3600                       # 18h
SNAPSHOT_EFF_SEC = {"v0": 0, "v1": 6 * 3600, "v2": 12 * 3600}
VERSION_EFF_SEC = {1: 0, 2: 6 * 3600, 3: 12 * 3600}

# ---- 规模 -----------------------------------------------------------------
PRIMARY_LEN = int(PARAMS["streams"]["primary_len"])
LONG_LEN = int(PARAMS["streams"]["long_len"])
SEED_COPIES = int(PARAMS["streams"]["seed_copies"])
PRIMARY_UPDATES = int(PARAMS["updates"]["primary"])
CALIB_ROWS = int(PARAMS["calibration"]["requests"])

# ---- 请求流结构参数（不是均匀分布：热点 + 长尾 + 迁移 + 复用） -------------
HOT_SIZE = 40                                      # 热点题数
HOT_SHARE = 0.60                                   # 热点时段内热点题占比
MIGRATION_HOURS = 3                                # 热点迁移过渡窗
TAIL_SIZE = 200 - 2 * HOT_SIZE                     # 120 个长尾题（不含两组热点）
REUSE_P = 0.45                                     # 直接复用同题既有改写的概率
HOT_ZIPF = 0.80                                    # 热点组内部集中度
TAIL_ZIPF = 0.95                                   # 长尾组内部集中度
TAIL_COVER_P = 0.50                                # 长尾里走「覆盖牌堆」的比例（保证 120 题都出现）
HOUR_WEIGHTS = [0.70, 0.65, 0.70, 0.85, 1.00, 1.10,
                1.25, 1.35, 1.40, 1.30, 1.15, 1.05,
                0.95, 0.85, 0.80, 0.75, 0.70, 0.65]

# 主流的种子与热点迁移时刻；seed43–46 迁移时刻各不相同（参数其余相同）
STREAM_SPECS = [
    ("seed42", PRIMARY_LEN, 9),
    ("seed43", PRIMARY_LEN, 7),
    ("seed44", PRIMARY_LEN, 10),
    ("seed45", PRIMARY_LEN, 8),
    ("seed46", PRIMARY_LEN, 11),
]
LONG_SPECS = [("long_01", LONG_LEN, 5), ("long_02", LONG_LEN, 13)]

TENANTS = (("tenant_public", "public", 0.40),
           ("tenant_staff", "staff", 0.35),
           ("tenant_restricted", "restricted", 0.25))

UPDATE_CLASSES = ("metric_revision", "schema_change", "lineage_switch",
                  "codebook_revision", "data_row_change")
# 40 条主更新的名额：6 条 codebook 固定为「无关更新」负对照，其余 4 类 34 条
UPDATE_QUOTAS = {"schema_change": 14, "metric_revision": 8,
                 "data_row_change": 6, "lineage_switch": 6}
NEGATIVE_CONTROL_ROWS = 6
NEGATIVE_CONTROL_MAX = int(PARAMS["updates"]["negative_control_max"])
CLASS_MIN = 6
# ρ = 命中主张数 / 该请求主张总数；< 0.5 记为「局部修复」，否则「大改」
RHO_LOCAL_MAX = 0.5
LOCAL_STEPS = {1: 0.85, 2: 0.85, 3: 0.90, 4: 0.95, 5: 1.0, 6: 1.05, 7: 1.0, 8: 0.95, 9: 0.90}
# 事件 timestamp 相对 effective_at 的铺开窗：0.05 h – 3.0 h（参考区间 0.03–3.08 h）
EVENT_DELAY_MIN_SEC = 180
EVENT_DELAY_MAX_SEC = 3 * 3600

ACT_COST_BANDS = (("query_dim_", 0.02, 0.05), ("query_log_", 0.04, 0.08),
                  ("query_fact_", 0.08, 0.22), ("query_agg_", 0.16, 0.35),
                  ("join_", 0.35, 0.80))
DOWNSTREAM_CAP = 4                                 # 单个 act 最多登记 4 个下游工具
STEP_HEAD = "解析问题口径与统计范围"
STEP_MIDS = ("核对权限范围与快照版本", "生成只读 SQL 并做语法检查",
             "在快照上执行并校验行数", "比对口径说明与结果差异")
STEP_TAIL = "组织中文回答并附证据块"
STEP_PRIORITY = (1, 2, 3, 0)           # 中间步骤的补入优先级（对应 STEP_MIDS 下标）
PLAN_COMPLETION_BANDS = {3: (0.90, 0.98), 4: (0.80, 0.90),
                         5: (0.80, 0.88), 6: (0.70, 0.82)}

DOC_KEYS = ("doc_id", "version", "doc_type", "domain", "permission", "updated_at", "chunks")


# --------------------------------------------------------------------------- 工具
def _iso(sec: int) -> str:
    """把「距 2024-05-15T00:00:00Z 的秒数」写成 UTC ISO8601。"""
    return (DAY + timedelta(seconds=int(sec))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sec_of(stamp: str) -> int:
    """'2024-05-15T08:00:00Z' → 距 00:00 的秒数。"""
    dt = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int((dt - DAY).total_seconds())


def _zipf_dict(items, s: float) -> dict:
    """按次序给出 1/(i+2)^s 的权重字典，保证热点组内部仍不平坦。"""
    return {k: 1.0 / ((i + 2) ** s) for i, k in enumerate(items)}


def _hour_counts(n: int) -> list[int]:
    """把 n 条请求按 HOUR_WEIGHTS 分到 18 个小时，每小时至少 1 条。"""
    total_w = sum(HOUR_WEIGHTS)
    raw = [n * w / total_w for w in HOUR_WEIGHTS]
    counts = [max(1, int(x)) for x in raw]
    while sum(counts) < n:                      # 余数按小数部分补齐
        order = sorted(range(len(raw)), key=lambda i: (raw[i] - int(raw[i])), reverse=True)
        for i in order:
            if sum(counts) >= n:
                break
            counts[i] += 1
    while sum(counts) > n:                      # 超出则从最大项削
        i = max(range(len(counts)), key=lambda j: counts[j])
        if counts[i] <= 1:
            break
        counts[i] -= 1
    return counts


def _dist(values: list[float]) -> dict:
    """min / p50 / max / mean，供 MANIFEST 统计。"""
    if not values:
        return {}
    v = sorted(values)
    n = len(v)
    return {"n": n, "min": round(v[0], 4), "p50": round(v[n // 2], 4),
            "max": round(v[-1], 4), "mean": round(sum(v) / n, 4)}


# --------------------------------------------------------------------------- 输入
def load_docs() -> tuple[list[dict], dict[str, dict], dict[tuple[str, int], dict]]:
    """返回 (原序行, v1 文档索引, (doc_id, version) 索引)。"""
    rows = list(io.read_jsonl(ROOT / "knowledge" / "docs.jsonl"))
    by_key: dict[tuple[str, int], dict] = {}
    v1: dict[str, dict] = {}
    for r in rows:
        assert tuple(sorted(r)) == tuple(sorted(DOC_KEYS)), f"docs.jsonl 字段异常：{sorted(r)}"
        assert ids.is_valid_doc_id(r["doc_id"]), r["doc_id"]
        assert r["updated_at"] == _iso(VERSION_EFF_SEC[r["version"]]), \
            f"{r['doc_id']} v{r['version']} updated_at 不在时轴上：{r['updated_at']}"
        by_key[(r["doc_id"], r["version"])] = r
        if r["version"] == 1:
            v1[r["doc_id"]] = r
    assert len(by_key) == len(rows), "docs.jsonl 存在重复 (doc_id, version)"
    return rows, v1, by_key


def load_version_changes() -> list[dict]:
    return list(io.read_jsonl(ROOT / "knowledge" / "version_changes.jsonl"))


def load_tasks() -> list[dict]:
    return list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))


def load_tables() -> dict[str, dict]:
    tables = io.read_json(ROOT / "contracts" / "tables.json")["tables"]
    return {t["table_id"]: t for t in tables}


# --------------------------------------------------------------------------- act / plan 池
def _tool_names(v1: dict[str, dict]) -> list[tuple[str, str]]:
    """从工具卡首块取出 (doc_id, 工具名)，工具名形如 query_dim_date / join_t05_t18。"""
    out = []
    for doc_id in sorted(v1):
        doc = v1[doc_id]
        if doc["doc_type"] != "tool":
            continue
        m = re.search(r"（([a-z0-9_]+)）", doc["chunks"][0]["text"])
        assert m, f"{doc_id} 首块没有工具名"
        out.append((doc_id, m.group(1)))
    assert len(out) == 100, f"工具卡 {len(out)} 篇"
    return out


def _act_cost(key: str) -> float:
    """按工具类型给成本：维度查询最便宜，连接工具最贵，落在 0.02–0.80。"""
    r = seeds.rng(STAGE, f"act_cost:{key}")
    body = key[len("act_"):]
    for prefix, lo, hi in ACT_COST_BANDS:
        if body.startswith(prefix):
            return round(min(0.80, max(0.02, r.uniform(lo, hi))), 2)
    return round(min(0.80, max(0.02, r.uniform(0.05, 0.20))), 2)


def _table_of_field(doc_id: str) -> str:
    return "t" + doc_id[5:7]


def _descendants() -> dict[str, set[str]]:
    """contracts/lineage.json → 每张表的全部下游表（传递闭包，edges 视为“从上游指向下游”）。"""
    lineage = io.read_json(ROOT / "contracts" / "lineage.json")
    adj: dict[str, set[str]] = defaultdict(set)
    for e in lineage["edges"]:
        adj[e["from"]].add(e["to"])
    out: dict[str, set[str]] = {}
    for tid in {t["table_id"] for t in load_tables().values()}:
        seen: set[str] = set()
        stack = [tid]
        while stack:
            u = stack.pop()
            for v in adj.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        out[tid] = seen
    return out


def _tool_table_sets(v1: dict[str, dict], tables: dict[str, dict]) -> dict[str, tuple[str, ...]]:
    """act_key → 该 act 直接读的表集合：query_* 取同名表，join_tA_tB 取两张输入表。"""
    name_to_tid = {t["name"]: tid for tid, t in tables.items()}
    out: dict[str, tuple[str, ...]] = {}
    for _, name in _tool_names(v1):
        act_key = f"act_{name}"
        if name.startswith("join_"):
            out[act_key] = tuple(sorted(tid for tid in re.findall(r"t\d{2}", name)
                                        if tid in tables))
        else:
            body = name[len("query_"):]
            assert body in name_to_tid, f"{act_key} 找不到表 {body}"
            out[act_key] = (name_to_tid[body],)
    assert len(out) == 100
    return out


def _downstream_tools(act_key: str, tool_tables: dict[str, tuple[str, ...]],
                      by_table: dict[str, set[str]], desc: dict[str, set[str]]) -> list[str]:
    """由血缘下游推导 downstream_tools。

    规则（确定性，只用血缘图与工具-表映射）：
    1. 血缘下游：该 act 读的每张表 T 的全部下游表 T' 上可执行的工具，都算它的下游工具
       （T 变了，T' 的物化结果随之变化，读 T' 的工具必须重算）；
    2. 直接消费者：查询类 act 被连接类 act 直接调用，因此读了同一张表的 join 工具也是它的
       下游工具（连接结果由查询结果拼出来）；连接类 act 不再向下派（连接结果不是表）。
    3. 去重后按 act_key 排序，最多登记 DOWNSTREAM_CAP 个，避免把整条血缘链无限展开。
    """
    out: set[str] = set()
    is_join = act_key.startswith("act_join_")
    for tid in tool_tables[act_key]:
        for down_tid in desc[tid]:
            out |= by_table.get(down_tid, set())
        if not is_join:
            out |= {a for a in by_table.get(tid, set()) if a.startswith("act_join_")}
    out.discard(act_key)
    return sorted(out)[:DOWNSTREAM_CAP]


def build_pool(v1: dict[str, dict], tables: dict[str, dict]) -> dict:
    tool_tables = _tool_table_sets(v1, tables)
    desc = _descendants()
    by_table: dict[str, set[str]] = defaultdict(set)
    for act_key, tids in tool_tables.items():
        for tid in tids:
            by_table[tid].add(act_key)

    acts = []
    for act_key in sorted(tool_tables):
        acts.append({
            "act_key": act_key,
            "act_cost": _act_cost(act_key),
            "downstream_tools": _downstream_tools(act_key, tool_tables, by_table, desc),
            "readonly": True,
        })
    assert len(acts) == 100

    plans = []
    for i in range(1, 61):
        pid = ids.plan_id(i)
        doc = v1.get(pid)
        assert doc, f"知识层缺计划卡 {pid}"
        text = "".join(c["text"] for c in doc["chunks"])
        m = re.search(r"（([a-z_]+)）", text)
        table_en = m.group(1) if m else "dim_date"
        label = _cn_table_label(text, table_en)
        r = seeds.rng(STAGE, f"plan:{pid}")
        extra = r.randrange(4)                    # 0..3 个可选中间步骤 → 总步数 3..6
        n_steps = 3 + extra
        mids = [STEP_MIDS[j] for j in sorted(STEP_PRIORITY[:extra])]
        steps = [STEP_HEAD, f"定位主表{label}（{table_en}）与关联字段"] + mids + [STEP_TAIL]
        lo, hi = PLAN_COMPLETION_BANDS[n_steps]
        plans.append({
            "plan_id": pid,
            "plan_cost": round(r.uniform(0.30, 1.20), 2),
            "completion_rate": round(r.uniform(lo, hi), 3),
            "steps": steps,
        })
    plans.sort(key=lambda p: p["plan_id"])

    for a in acts:
        assert 0.02 <= a["act_cost"] <= 0.80, a
        assert set(a["downstream_tools"]) <= set(tool_tables), a
    for p in plans:
        assert 0.30 <= p["plan_cost"] <= 1.20 and 0.70 <= p["completion_rate"] <= 0.98, p
        assert 3 <= len(p["steps"]) <= 6, p
    return {"acts": acts, "plans": plans}


def _cn_table_label(text: str, table_en: str) -> str:
    """从计划卡正文里取主表的中文名，如「日期维」「区域维」。"""
    idx = text.find("（" + table_en + "）")
    if idx < 0:
        return "主表"
    win = text[max(0, idx - 8):idx]
    m = re.search(r"([\u4e00-\u9fa5]{2,4}维)$", win)
    if not m:
        return "主表"
    label = m.group(1)
    for prefix in ("主表选", "主表为", "主表", "表选", "选用", "使用", "以", "为", "的", "选"):
        if label.startswith(prefix) and len(label) - len(prefix) >= 2:
            return label[len(prefix):]
    return label


# --------------------------------------------------------------------------- 题目上下文
def _split_question(q: str) -> tuple[str, str | None]:
    """把题目拆成（提问主体，统计口径）。口径子句前的分隔符有「？」「。」「，」等多种写法。"""
    i = q.find("统计口径：")
    if i > 0:
        head = q[:i].rstrip("？。；，、 ")
        scope = q[i + len("统计口径："):].strip()
        if scope.endswith("。"):
            scope = scope[:-1]
        return head, (scope.strip() or None)
    return q.strip().rstrip("？。"), None


def paraphrase(head: str, scope: str | None, variant: int) -> str:
    """同一意图的三种中文说法：内容一致，句式与引导词不同。"""
    if scope is None:
        frames = (f"{head}？", f"帮我查一下：{head}？", f"想确认{head}？")
        return frames[variant]
    if variant == 0:
        return f"{head}？统计口径为{scope}。"
    if variant == 1:
        return f"帮我查一下：{head}？口径按{scope}。"
    return f"想确认{head}？请按{scope}的口径给出结果。"


_TBL_DOMAIN_RULES = (
    (("fact_orders", "order_item", "sales", "returns", "refund", "promotion", "campaign",
      "click", "session", "lead", "quote", "contract", "subscription", "renewal", "churn",
      "target", "forecast", "engagement", "usage"), "sales"),
    (("inventory", "shipment", "deliver", "stock", "supplier", "quality"), "supply"),
    (("payment", "invoice", "cost", "budget", "collection", "price"), "finance"),
    (("ticket", "sla"), "ops"),
)


def _table_domain_fallback(name: str) -> str:
    if name.startswith("dim_"):
        return "meta"
    if name.startswith("log_"):
        return "ops"
    for keys, dom in _TBL_DOMAIN_RULES:
        if any(k in name for k in keys):
            return dom
    return "ops"


def task_domain(task: dict, v1: dict[str, dict], tables: dict[str, dict]) -> str:
    """domain 由证据文档派生，保证同一题的所有改写请求取到同一个值。

    1. 首个 metric_/wp_ 证据在知识层的 domain；
    2. 否则首个字段卡所属表的 domain（表名启发式兜底）。
    """
    ev = task["truth"]["evidence"]
    for e in ev:
        d = e["doc_id"]
        if (d.startswith("metric_") or d.startswith("wp_")) and d in v1:
            return v1[d]["domain"]
    for e in ev:
        d = e["doc_id"]
        if d.startswith("fld_t") and d in v1:
            return v1[d]["domain"]
    for e in ev:
        d = e["doc_id"]
        if d.startswith("fld_t"):
            tid = _table_of_field(d)
            if tid in tables:
                return _table_domain_fallback(tables[tid]["name"])
    return "meta"


def _task_tables(task: dict) -> list[str]:
    out: list[str] = []
    for e in task["truth"]["evidence"]:
        d = e["doc_id"]
        if d.startswith("fld_t"):
            tid = _table_of_field(d)
            if tid not in out:
                out.append(tid)
    return out


def _obj_types(difficulty: str) -> list[str]:
    """口径题含 rag+resp，执行题含 act+resp，多步题含 plan。"""
    if difficulty == "single_table":                 # 单表口径题：以口径检索为主
        return ["rag", "resp"]
    if difficulty == "join":                          # 连接执行题：以工具执行为主
        return ["act", "resp"]
    return ["plan", "rag", "act", "resp"]             # nested_agg：多步计划


def task_act_key(task: dict, pool: dict, tables: dict[str, dict]) -> str:
    r = seeds.rng(STAGE, f"act_pick:{task['task_id']}")
    keys = [a["act_key"] for a in pool["acts"]]
    keyset = set(keys)
    tids = _task_tables(task)
    names = [tables[t]["name"] for t in tids if t in tables]

    if task["difficulty"] == "single_table":
        for name in names:
            k = f"act_query_{name}"
            if k in keyset:
                return k
        return r.choice(sorted(k for k in keys if k.startswith("act_query_fact_")))

    want = {f"act_join_{a}_{b}" for a in tids for b in tids if a < b} | \
           {f"act_join_{b}_{a}" for a in tids for b in tids if a < b}
    hit = sorted(k for k in want if k in keyset)
    if hit:
        return r.choice(hit)
    if task["difficulty"] == "join":
        return r.choice(sorted(k for k in keys if k.startswith("act_join_")))
    return r.choice(sorted(k for k in keys if k.startswith("act_query_agg_")))


def task_plan_id(task: dict, pool: dict, v1: dict[str, dict], domain: str,
                 tables: dict[str, dict]) -> str:
    r = seeds.rng(STAGE, f"plan_pick:{task['task_id']}")
    names = [tables[t]["name"] for t in _task_tables(task) if t in tables]
    cands = []
    for p in pool["plans"]:
        doc = v1.get(p["plan_id"])
        if doc is None or doc["domain"] != domain:
            continue
        text = "".join(c["text"] for c in doc["chunks"])
        if any(n in text for n in names):
            cands.append(p["plan_id"])
    if cands:
        return r.choice(sorted(cands))
    same_dom = sorted(p["plan_id"] for p in pool["plans"]
                      if v1.get(p["plan_id"]) is not None
                      and v1[p["plan_id"]]["domain"] == domain)
    if same_dom:
        return r.choice(same_dom)
    return r.choice(sorted(p["plan_id"] for p in pool["plans"]))


def build_task_ctx(tasks: list[dict], v1: dict[str, dict], tables: dict[str, dict],
                   pool: dict) -> dict[str, dict]:
    """每题的静态上下文：domain / 三种改写 / act / plan / obj_types / 证据 / 簇。

    ``gold_fact_spans`` 逐条取自主张层：claim 文本 + 该主张的第一条证据块
    （块跨版本稳定，v1 中必然存在）。主张数 1–5 不等，直接决定 ρ 的分母。
    """
    ctx: dict[str, dict] = {}
    for task in tasks:
        tid = task["task_id"]
        dom = task_domain(task, v1, tables)
        head, scope = _split_question(task["question"])
        texts = [paraphrase(head, scope, v) for v in range(3)]
        assert len(set(texts)) == 3, f"{tid} 三种改写重复"
        gold_docs: list[str] = []
        for e in task["truth"]["evidence"]:
            if e["doc_id"] not in gold_docs:
                gold_docs.append(e["doc_id"])
        spans = []
        for claim in task["truth"]["claims"]:
            ev = claim["evidence"][0]
            chunk_id = ev["chunk_id"]
            assert ids.is_valid_block_id(chunk_id), f"{tid} 非法块 {chunk_id}"
            assert ev["doc_id"] in gold_docs, f"{tid} 主张证据文档不在 gold_doc_ids"
            assert chunk_id in {c["chunk_id"] for c in v1[ev["doc_id"]]["chunks"]}, \
                f"{tid} 主张块不在 v1：{chunk_id}"
            spans.append({"claim": claim["text"], "chunk_id": chunk_id})
        assert len({s["claim"] for s in spans}) == len(spans), f"{tid} 主张文本重复"
        ctx[tid] = {
            "task_id": tid,
            "cluster_id": task["cluster_id"],
            "domain": dom,
            "permission": task["permission"],
            "difficulty": task["difficulty"],
            "texts": texts,
            "gold_doc_ids": gold_docs,
            "gold_fact_spans": spans,
            "gold_doc_perm_max": max(v1[d]["permission"] for d in gold_docs
                                     if d in v1) if any(d in v1 for d in gold_docs) else "public",
            "plan_id": task_plan_id(task, pool, v1, dom, tables),
            "act_key": task_act_key(task, pool, tables),
            "obj_types": _obj_types(task["difficulty"]),
        }
    return ctx


# --------------------------------------------------------------------------- 请求流
def _hot_state(t_sec: int, switch_hour: int) -> tuple[str, float]:
    """热点状态。前 switch_hour-3 小时只有 A；过渡窗内按比例混入 B；之后只有 B。"""
    h = t_sec / 3600.0
    start = switch_hour - MIGRATION_HOURS
    if h < start:
        return "A", 0.0
    if h < switch_hour:
        return "mix", (h - start) / MIGRATION_HOURS
    return "B", 0.0


def _time_slots(r, n: int) -> list[int]:
    """18 小时内的到达时刻（秒）。逐小时配额 + 小时内抖动，最终升序。"""
    counts = _hour_counts(n)
    out: list[int] = []
    for h, c in enumerate(counts):
        for _ in range(c):
            out.append(h * 3600 + int(r.random() * 3600))
    out.sort()
    out[0] = 0                                  # 覆盖 00:00:00
    out[-1] = min(out[-1], SPAN_SEC - 1)        # 不越过 18:00:00
    return out


def _hot_flags(r, times: list[int]) -> list[bool]:
    """逐小时按 HOT_SHARE 定额标记「热点请求」，使每个时段的热点占比稳定在 60%。"""
    flags = [False] * len(times)
    by_hour: dict[int, list[int]] = {}
    for i, t in enumerate(times):
        by_hour.setdefault(t // 3600, []).append(i)
    for hour in sorted(by_hour):
        idxs = by_hour[hour]
        k = int(round(len(idxs) * HOT_SHARE))
        for i in r.sample(idxs, k):
            flags[i] = True
    return flags


def _snapshot(t_sec: int) -> dict:
    idx = "v0" if t_sec < SNAPSHOT_EFF_SEC["v1"] else (
        "v1" if t_sec < SNAPSHOT_EFF_SEC["v2"] else "v2")
    return {"index": idx, "as_of": _iso(SNAPSHOT_EFF_SEC[idx])}


def gen_stream(tasks: list[dict], ctx: dict[str, dict], *, name: str, n: int,
               switch_hour: int) -> tuple[list[dict], list[dict]]:
    """生成一条请求流。返回 (请求行, 上下文行)。"""
    r = seeds.rng(STAGE, f"stream:{name}")
    task_ids = [t["task_id"] for t in tasks]

    order = seeds.shuffle(task_ids, STAGE, f"hot:{name}")
    hot_a, hot_b = order[:HOT_SIZE], order[HOT_SIZE:2 * HOT_SIZE]
    tail = order[2 * HOT_SIZE:]
    assert len(tail) == TAIL_SIZE

    w_hot_a = _zipf_dict(seeds.shuffle(hot_a, STAGE, f"hotw_a:{name}"), HOT_ZIPF)
    w_hot_b = _zipf_dict(seeds.shuffle(hot_b, STAGE, f"hotw_b:{name}"), HOT_ZIPF)
    w_tail = _zipf_dict(seeds.shuffle(tail, STAGE, f"tailw:{name}"), TAIL_ZIPF)

    times = _time_slots(r, n)
    hot_flags = _hot_flags(r, times)
    recent: dict[str, list[tuple[int, int]]] = {}
    var_order: dict[str, list[int]] = {}
    var_used: dict[str, int] = {}
    deck: list[str] = []
    cycle = [0]
    rows: list[dict] = []
    context: list[dict] = []

    for i, t_sec in enumerate(times):
        mode, split = _hot_state(t_sec, switch_hour)
        if hot_flags[i]:
            if mode == "mix":
                grp = "B" if r.random() < split else "A"
            else:
                grp = mode
            task_id = seeds.choice_weighted(r, w_hot_a if grp == "A" else w_hot_b)
            bucket = "hot"
        else:
            if r.random() < TAIL_COVER_P:
                if not deck:                     # 覆盖牌堆：洗牌后逐张发，发完再洗
                    cycle[0] += 1
                    deck.extend(seeds.shuffle(tail, STAGE, f"taildeck:{name}:{cycle[0]}"))
                task_id = deck.pop()
            else:
                task_id = seeds.choice_weighted(r, w_tail)
            bucket = "tail"
            grp = "-"

        seen = recent.get(task_id)
        # 之前的到达若还没把该题的 3 种改写走满，就先不判复用，保证三种说法都会出现
        covered = bool(seen) and len({v for v, _ in seen}) >= 3
        reused = covered and r.random() < REUSE_P
        if reused:
            variant, tenant_i = seen[-1] if r.random() < 0.6 else seen[r.randrange(len(seen))]
        else:
            # 改写按题轮转（顺序对每题洗一次），保证每题的 3 种说法都会到达
            order_v = var_order.get(task_id)
            if order_v is None:
                order_v = seeds.shuffle([0, 1, 2], STAGE, f"variant:{name}:{task_id}")
                var_order[task_id] = order_v
            variant = order_v[var_used.get(task_id, 0) % 3]
            var_used[task_id] = var_used.get(task_id, 0) + 1
            tnames = {j: w for j, (_, _, w) in enumerate(TENANTS)}
            tenant_i = seeds.choice_weighted(r, tnames)
            recent.setdefault(task_id, []).append((variant, tenant_i))

        c = ctx[task_id]
        tenant_name, tenant_scope, _ = TENANTS[tenant_i]
        perm = "restricted" if tenant_scope == "restricted" else c["permission"]
        snap = _snapshot(t_sec)
        row = {
            "req_id": ids.req_id(i + 1),
            "timestamp": _iso(t_sec),
            "query_text": c["texts"][variant],
            "query_emb": None,
            "plan_id": c["plan_id"],
            "act_key": c["act_key"],
            "gold_doc_ids": list(c["gold_doc_ids"]),
            "gold_fact_spans": [dict(s) for s in c["gold_fact_spans"]],
            "domain": c["domain"],
            "permission": perm,
            "snapshot": snap,
            "obj_types": list(c["obj_types"]),
            "cluster_id": c["cluster_id"],
        }
        rows.append(row)
        context.append({
            "req_id": row["req_id"],
            "timestamp": row["timestamp"],
            "task_id": task_id,
            "cluster_id": c["cluster_id"],
            "variant": variant + 1,
            "tenant": tenant_name,
            "tenant_scope": tenant_scope,
            "permission": perm,
            "task_permission": c["permission"],
            "permission_negative": perm != c["gold_doc_perm_max"],
            "bucket": bucket,
            "hot_set": grp,
            "reused": reused,
            "snapshot": snap["index"],
        })
    return rows, context


# --------------------------------------------------------------------------- 更新事件
# 实验 E 需要「证据更新 → 缓存回答失效 → 局部修复」，因此更新分两层命中：
#   R1 文档级：doc_id 至少被 1 条请求的 gold_doc_ids 引用 —— 缓存里得先有这份证据；
#   R2 主张级：至少一个 changed_chunk_id 被某条请求的 gold_fact_spans 引用 —— 被推翻的
#      必须是具体主张，才能观察局部修复。
#
# v0.2.0 新增 ρ 目标：受影响 (更新, 请求) 对中，ρ = 命中主张数 / 该请求主张总数 < 0.5 的比例
# 必须落在 params.updates.local_repair_ratio_target（0.65–0.75）。单块更新下 ρ 由该请求的
# 主张数决定（命中 1 条时 ρ=1/n），因此选样要偏向主张数 3–5 的请求，同时保留少量
# 命中 2 条以上主张、ρ≥0.5 的大改样本（主张数为 2 的请求被命中即为 0.5，计入大改）。
#
# codebook_revision 全部是 note 码表说明，请求流从不引用 note，因此**刻意保留 6 条
# negative_control: true 的无关更新**作负对照，用来检验失效策略的误触发率；其余 34 条
# 必须命中真实请求（文档级），其中 ≥22 条命中答案主张（主张级）。


def _chunk_text(docs: dict[tuple[str, int], dict], doc_id: str, ver: int,
                chunk_id: str) -> str | None:
    row = docs.get((doc_id, ver))
    if not row:
        return None
    for c in row["chunks"]:
        if c["chunk_id"] == chunk_id:
            return c["text"]
    return None


def update_class(rec: dict, docs: dict[tuple[str, int], dict]) -> str:
    """变更记录 → 五类之一。

    先看"变更块讲的是什么"（血缘说明 / 码表说明），再看文档类型：
    指标卡→metric_revision；白皮书结构→schema_change；血缘说明→lineage_switch；
    码表说明（note 首块）→codebook_revision；其余→data_row_change。
    ``rec`` 既可以是 version_changes 的记录（from_ver/to_ver），也可以是 update_events
    的行（old_ver/new_ver）。
    """
    doc_id = rec["doc_id"]
    from_ver = rec.get("from_ver", rec.get("old_ver"))
    to_ver = rec.get("to_ver", rec.get("new_ver"))
    doc_type = docs[(doc_id, 1)]["doc_type"]
    texts = []
    for cid in rec["changed_chunk_ids"]:
        for ver in (to_ver, from_ver):
            t = _chunk_text(docs, doc_id, ver, cid)
            if t:
                texts.append(t)
                break
    joined = " ".join(texts)
    head = docs[(doc_id, 1)]["chunks"][0]["text"]
    if doc_type == "metric":
        return "metric_revision"
    if doc_type == "whitepaper":
        # 白皮书分两种：使用说明（结构）与关联说明（血缘/上下游关系）
        if "关联说明" in head or "关联关系" in head or "上游" in head:
            return "lineage_switch"
        return "lineage_switch" if "血缘" in joined else "schema_change"
    if doc_type == "note":
        if "码表说明" in head:
            return "codebook_revision"
        if "血缘" in head:
            return "lineage_switch"
        return "data_row_change"
    if doc_type == "field":
        return "lineage_switch" if "血缘" in head else "data_row_change"
    return "data_row_change"


def _rho_breakdown(changed: list[str], requests: list[dict]) -> tuple[int, int]:
    """受影响请求中 ρ<0.5（局部修复）与 ρ≥0.5（大改）的条数。"""
    chs = set(changed)
    local = major = 0
    for r in requests:
        spans = r["gold_fact_spans"]
        hit = sum(1 for s in spans if s["chunk_id"] in chs)
        if not hit:
            continue
        if hit / len(spans) < RHO_LOCAL_MAX:
            local += 1
        else:
            major += 1
    return local, major


def _candidates(docs: dict[tuple[str, int], dict], v1: dict[str, dict],
                changes: list[dict], requests: list[dict]) -> tuple[list[dict], list[dict]]:
    """把 version_changes 变成更新候选：只保留可核验、可命中的真实记录。"""
    cited_docs = Counter()
    for r in requests:
        for d in r["gold_doc_ids"]:
            cited_docs[d] += 1
    out: list[dict] = []
    for rec in changes:
        if rec["change_kind"] == "add_chunk":
            continue                            # 新增块不在 old_ver 里，无法通过引用校验
        old = docs.get((rec["doc_id"], rec["from_ver"]))
        if old is None:
            continue
        have = {c["chunk_id"] for c in old["chunks"]}
        if not set(rec["changed_chunk_ids"]) <= have:
            continue
        cls = update_class(rec, docs)
        local, major = _rho_breakdown(rec["changed_chunk_ids"], requests)
        cited = rec["doc_id"] in cited_docs
        out.append({
            "rec": rec,
            "cls": cls,
            "local": local,
            "major": major,
            "pairs": local + major,
            "doc_requests": cited_docs.get(rec["doc_id"], 0),
            "cited": cited,
            "chunk_level": (local + major) > 0,
        })
    return out, [dict(doc=doc, requests=n) for doc, n in sorted(cited_docs.items())]


def _rank_key(c: dict) -> tuple:
    rec = c["rec"]
    return (-c["pairs"], -c["doc_requests"], rec["doc_id"], rec["from_ver"])


def _select_updates(cands: list[dict]) -> list[dict]:
    """按类名额选 34 条有命中候选 + 6 条负对照，使 ρ 落入目标区间。

    1. 每类先按「受影响对数 → 文档级影响 → doc_id」取名额；
    2. codebook_revision 取 6 条未被请求引用的真实记录作 negative_control；
    3. 类内换入换出（确定性贪心）：每步挑使 ρ 最接近目标中值的单次替换，
       直到 ρ 落入 params 区间；替换不得使主张级影响条数低于契约下限 22。
    """
    quotas = dict(UPDATE_QUOTAS)
    assert sum(quotas.values()) + NEGATIVE_CONTROL_ROWS == PRIMARY_UPDATES
    target_min, target_max = PARAMS["updates"]["local_repair_ratio_target"]
    target = (target_min + target_max) / 2

    controls = [c for c in cands
                if c["cls"] == "codebook_revision" and not c["cited"] and c["pairs"] == 0]
    controls.sort(key=lambda c: (c["rec"]["doc_id"], c["rec"]["from_ver"]))
    assert len(controls) >= NEGATIVE_CONTROL_ROWS, \
        f"可用于负对照的 codebook 记录只有 {len(controls)} 条"
    controls = controls[:NEGATIVE_CONTROL_ROWS]

    by_class: dict[str, list[dict]] = {cls: [] for cls in quotas}
    for c in cands:
        if c["cls"] in quotas and c["cited"]:
            by_class[c["cls"]].append(c)
    for cls, need in quotas.items():
        by_class[cls].sort(key=_rank_key)
        assert len(by_class[cls]) >= need, f"{cls} 只有 {len(by_class[cls])} 条命中候选"

    selected: list[dict] = []
    for cls, need in quotas.items():
        selected.extend(by_class[cls][:need])

    def totals(sel: list[dict]) -> tuple[int, int]:
        local = sum(c["local"] for c in sel)
        major = sum(c["major"] for c in sel)
        return local, major

    for _ in range(80):
        local, major = totals(selected)
        share = local / (local + major)
        if target_min <= share <= target_max:
            break
        selected_set = {id(c) for c in selected}
        best = None
        for cls in quotas:
            chosen = [c for c in selected if c["cls"] == cls]
            for a in chosen:
                for b in by_class[cls]:
                    if id(b) in selected_set or b is a:
                        continue
                    l2 = local - a["local"] + b["local"]
                    m2 = major - a["major"] + b["major"]
                    if l2 + m2 <= 0:
                        continue
                    s2 = l2 / (l2 + m2)
                    n_chunk = sum(1 for c in selected if c["chunk_level"]) \
                        - int(a["chunk_level"]) + int(b["chunk_level"])
                    if n_chunk < CLASS_MIN + 16:          # 主张级下限 22
                        continue
                    d2 = abs(s2 - target)
                    if d2 >= abs(share - target) - 1e-12:
                        continue
                    key = (round(d2, 9), cls, a["rec"]["doc_id"], a["rec"]["from_ver"],
                           b["rec"]["doc_id"], b["rec"]["from_ver"])
                    if best is None or key < best[0]:
                        best = (key, a, b)
        if best is None:
            raise AssertionError(f"无法把 ρ 调进 {target_min}-{target_max}（当前 {share:.3f}）")
        _, a, b = best
        selected = [b if c is a else c for c in selected]

    local, major = totals(selected)
    share = local / (local + major)
    assert target_min <= share <= target_max, f"ρ={share:.3f} 不在目标区间"
    assert local + major >= 200, f"受影响对只有 {local + major} 个"
    assert sum(1 for c in selected if c["chunk_level"]) >= 2 * CLASS_MIN + 10
    return selected + controls


def _schedule_updates(picked: list[dict], requests: list[dict]) -> list[dict]:
    """给 40 条更新排时间：timestamp 不早于 effective_at，且尽量早于其最后一条引用。"""
    doc_times: dict[str, list[int]] = defaultdict(list)
    chunk_times: dict[str, list[int]] = defaultdict(list)
    for r in requests:
        sec = _sec_of(r["timestamp"])
        for d in r["gold_doc_ids"]:
            doc_times[d].append(sec)
        for s in r["gold_fact_spans"]:
            chunk_times[s["chunk_id"]].append(sec)

    def last_cite(c: dict) -> int:
        rec = c["rec"]
        secs = [t for cid in rec["changed_chunk_ids"] for t in chunk_times.get(cid, [])]
        if not secs:
            secs = doc_times.get(rec["doc_id"], [])
        return max(secs) if secs else SPAN_SEC - 60

    def first_cite(c: dict) -> int:
        rec = c["rec"]
        secs = [t for cid in rec["changed_chunk_ids"] for t in chunk_times.get(cid, [])]
        if not secs:
            secs = doc_times.get(rec["doc_id"], [])
        return min(secs) if secs else VERSION_EFF_SEC[rec["to_ver"]]

    scheduled: list[list] = []
    for ver in (2, 3):
        items = [c for c in picked if c["rec"]["to_ver"] == ver]
        if not items:
            continue
        items.sort(key=lambda c: (last_cite(c), c["rec"]["doc_id"], c["rec"]["from_ver"]))
        lo = VERSION_EFF_SEC[ver] + EVENT_DELAY_MIN_SEC
        hi = VERSION_EFF_SEC[ver] + EVENT_DELAY_MAX_SEC
        n = len(items)
        for i, c in enumerate(items):
            t = lo if n == 1 else lo + round(i * (hi - lo) / (n - 1))
            # 事件尽量落在「第一条引用之后、最后一条引用之前」，保证更新后仍有请求可观测
            t = max(t, first_cite(c) + 1)
            t = min(t, last_cite(c) - 120)
            t = min(t, hi)
            t = max(t, VERSION_EFF_SEC[ver] + 120)
            scheduled.append([int(t), c])
    scheduled.sort(key=lambda x: (x[0], x[1]["rec"]["doc_id"], x[1]["rec"]["from_ver"]))
    for i in range(1, len(scheduled)):          # 同一秒的事件按 +11s 错开
        if scheduled[i][0] <= scheduled[i - 1][0]:
            scheduled[i][0] = scheduled[i - 1][0] + 11
    assert len(scheduled) == PRIMARY_UPDATES, f"排期 {len(scheduled)} 条"
    return [[t, c] for t, c in scheduled]


def build_updates(docs: dict[tuple[str, int], dict], v1: dict[str, dict],
                  changes: list[dict], requests: list[dict]) -> tuple[list[dict], dict]:
    """挑 40 条主更新（含 6 条负对照）、排双时间戳、算影响统计。"""
    cands, _ = _candidates(docs, v1, changes, requests)
    picked = _select_updates(cands)
    scheduled = _schedule_updates(picked, requests)

    rows: list[dict] = []
    for i, (t, c) in enumerate(scheduled, start=1):
        rec = c["rec"]
        doc = v1[rec["doc_id"]]
        eff_at = docs[(rec["doc_id"], rec["to_ver"])]["updated_at"]
        eff_sec = _sec_of(eff_at)
        delay = int(t - eff_sec)
        assert delay >= 0, f"{rec['doc_id']} 通知早于生效"
        rows.append({
            "event_id": ids.upd_id(i),
            "timestamp": _iso(t),
            "effective_at": eff_at,
            "notification_delay_s": delay,
            "doc_id": rec["doc_id"],
            "old_ver": rec["from_ver"],
            "new_ver": rec["to_ver"],
            "changed_chunk_ids": list(rec["changed_chunk_ids"]),
            "change_type": c["cls"],
            "domain": doc["domain"],
            "permission": doc["permission"],
            "answer_impact": "changed" if c["chunk_level"] else "unchanged",
            "negative_control": c["cls"] == "codebook_revision" and not c["cited"],
        })

    # 影响统计（文档级 / 主张级 / ρ 分布 / 双时间戳）
    doc_hits: dict[str, int] = defaultdict(int)
    chunk_hit_reqs: dict[str, set[str]] = defaultdict(set)
    doc_last: dict[str, int] = defaultdict(int)
    chunk_last: dict[str, int] = defaultdict(int)
    for r in requests:
        sec = _sec_of(r["timestamp"])
        for d in r["gold_doc_ids"]:
            doc_hits[d] += 1
            doc_last[d] = max(doc_last[d], sec)
        for s in r["gold_fact_spans"]:
            chunk_hit_reqs[s["chunk_id"]].add(r["req_id"])
            chunk_last[s["chunk_id"]] = max(chunk_last[s["chunk_id"]], sec)
    local = major = 0
    post_doc = post_claim = 0
    affected_req_ids: set[str] = set()
    impact = []
    for row in rows:
        chs = set(row["changed_chunk_ids"])
        reqs = set()
        for cid in chs:
            reqs |= chunk_hit_reqs.get(cid, set())
        affected_req_ids |= reqs
        l, m = _rho_breakdown(row["changed_chunk_ids"], requests)
        local += l
        major += m
        t = _sec_of(row["timestamp"])
        if doc_last.get(row["doc_id"], 0) > t:
            post_doc += 1
        if any(chunk_last.get(cid, 0) > t for cid in chs):
            post_claim += 1
        impact.append({
            "event_id": row["event_id"], "change_type": row["change_type"],
            "doc_id": row["doc_id"], "doc_level": doc_hits.get(row["doc_id"], 0),
            "claim_level": len(reqs), "local": l, "major": m,
        })
    pairs = local + major
    share = local / pairs if pairs else 0.0
    delays = [row["notification_delay_s"] / 3600 for row in rows]
    stats = {
        "rows": len(rows),
        "by_class": dict(sorted(Counter(row["change_type"] for row in rows).items())),
        "doc_level_rows": sum(1 for x in impact if x["doc_level"] > 0),
        "chunk_level_rows": sum(1 for x in impact if x["claim_level"] > 0),
        "negative_control_rows": sum(1 for row in rows if row["negative_control"]),
        "zero_impact_rows": sum(1 for x in impact if x["doc_level"] == 0),
        "post_event_rows": post_doc,
        "post_event_claim_rows": post_claim,
        "doc_level_requests_total": sum(x["doc_level"] for x in impact),
        "claim_level_requests_total": pairs,
        "claim_level_requests_dedup": len(affected_req_ids),
        "rho": {"affected_pairs": pairs, "local": local, "major": major,
                "local_ratio": round(share, 4),
                "target": list(PARAMS["updates"]["local_repair_ratio_target"]),
                "rule": "ρ=命中主张数/该请求主张总数；ρ<0.5 记局部修复"},
        "delay_hours": _dist(delays),
        "answer_impact": dict(sorted(Counter(row["answer_impact"] for row in rows).items())),
        "top_by_doc_requests": sorted(impact, key=lambda x: (-x["doc_level"], x["event_id"]))[:5],
        "top_by_claim_requests": sorted(impact, key=lambda x: (-x["claim_level"], x["event_id"]))[:5],
        "first_event": rows[0]["timestamp"],
        "last_event": rows[-1]["timestamp"],
        "window": "timestamp ≥ effective_at（= new_ver 的 updated_at），落在 18 小时窗口内",
    }
    return rows, stats


# --------------------------------------------------------------------------- 校准抽样
def calibration_sample(rows: list[dict], request_ctx: dict[str, dict]) -> list[dict]:
    """从主请求流抽 300 条：先保证 200 题各一条，再补 100 条不同快照/不同改写。

    t_act_ms 由 calibrate.py 在本机真实执行 gold_sql 得到；本函数只选样。
    """
    order = seeds.shuffle(range(len(rows)), STAGE, "calib_sample")
    by_task: dict[str, int] = {}
    first: list[int] = []
    rest: list[int] = []
    for i in order:
        tid = request_ctx[rows[i]["req_id"]]["task_id"]
        if tid not in by_task:
            by_task[tid] = i
            first.append(i)
        else:
            rest.append(i)
    picked = sorted(first)[:200] + sorted(rest)[:CALIB_ROWS - 200]
    picked = sorted(set(picked), key=lambda i: (rows[i]["timestamp"], rows[i]["req_id"]))
    if len(picked) < CALIB_ROWS:              # 极端情况下某题一次未出现，用剩余行补足
        used = set(picked)
        for i in range(len(rows)):
            if len(picked) >= CALIB_ROWS:
                break
            if i not in used:
                picked.append(i)
        picked = sorted(set(picked), key=lambda i: (rows[i]["timestamp"], rows[i]["req_id"]))
    assert len(picked) == CALIB_ROWS, len(picked)
    return [{"req_id": rows[i]["req_id"],
             "timestamp": rows[i]["timestamp"],
             "snapshot": rows[i]["snapshot"]["index"],
             "task_id": request_ctx[rows[i]["req_id"]]["task_id"]} for i in picked]


def _check_calibration_template(out: Path, calib: list[dict]) -> None:
    """校准模板的 req_id 集合必须与新旧抽样一致；不一致才允许重测，且重测必须真跑。

    这里只做一致性检查：若模板还在且 req_id 序列不同，直接报错要求跑 calibrate.py，
    绝不改写已实测列，也绝不编造 t_act_ms。
    """
    path = out / "real_calibration_300.template.csv"
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines()[1:]
    old_ids = [ln.split(",")[0] for ln in lines if ln.strip()]
    new_ids = [row["req_id"] for row in calib]
    if old_ids != new_ids:
        raise SystemExit("校准模板 req_id 序列已变化：请运行 python dataset/events/calibrate.py "
                         "真实重测 t_act_ms（不得沿用或编造）")


# --------------------------------------------------------------------------- 主流程
def build_all(out_dir: Path | str = HERE, *, verbose: bool = True) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assert PARAMS["streams"]["time_span_hours"] == SPAN_HOURS

    docs, v1, doc_index = load_docs()
    changes = load_version_changes()
    tasks = load_tasks()
    tables = load_tables()
    assert len(tasks) == PARAMS["tasks"]["total"] == 200
    assert len(docs) == PARAMS["knowledge"]["docs_total"] * PARAMS["knowledge"]["versions"]
    assert len({t["cluster_id"] for t in tasks}) == PARAMS["clusters"]["count"]

    # 1. docs_versioned 投影：原样搬运，不改写内容
    io.write_jsonl(out / "docs_versioned.jsonl", docs)
    if verbose:
        print(f"  docs_versioned.jsonl      {len(docs)} 行")

    # 2. act / plan 池
    pool = build_pool(v1, tables)
    io.write_json(out / "act_plan_pool.json", pool)
    if verbose:
        dn = [len(a["downstream_tools"]) for a in pool["acts"]]
        print(f"  act_plan_pool.json        {len(pool['acts'])} act / {len(pool['plans'])} plan"
              f"（下游非空 {sum(1 for d in dn if d)}/100）")

    # 3. 题目上下文
    ctx = build_task_ctx(tasks, v1, tables, pool)

    # 4. 请求流（主流 + 种子副本 + 长流）
    streams_dir = out / "streams"
    streams_dir.mkdir(parents=True, exist_ok=True)
    main_rows: list[dict] = []
    main_ctx: list[dict] = []
    for name, n, switch in STREAM_SPECS:
        rows, context = gen_stream(tasks, ctx, name=name, n=n, switch_hour=switch)
        io.write_jsonl(streams_dir / f"{name}.jsonl", rows)
        if name == "seed42":
            main_rows, main_ctx = rows, context
        if verbose:
            print(f"  streams/{name}.jsonl      {len(rows)} 行（迁移 {switch}:00）")
    assert len(main_rows) == PRIMARY_LEN
    io.write_jsonl(out / "request_stream.jsonl", main_rows)
    io.write_jsonl(out / "request_context.jsonl", main_ctx)
    if verbose:
        print(f"  request_stream.jsonl      {len(main_rows)} 行（含 cluster_id）")
        print(f"  request_context.jsonl     {len(main_ctx)} 行")

    for name, n, switch in LONG_SPECS:
        rows, _ = gen_stream(tasks, ctx, name=name, n=n, switch_hour=switch)
        io.write_jsonl(streams_dir / f"{name}.jsonl", rows)
        if verbose:
            print(f"  streams/{name}.jsonl      {len(rows)} 行（迁移 {switch}:00）")

    # 5. 更新事件（双时间戳 + ρ 目标 + 负对照）
    updates, update_stats = build_updates(doc_index, v1, changes, main_rows)
    io.write_jsonl(out / "update_events.jsonl", updates)
    if verbose:
        rho = update_stats["rho"]
        print(f"  update_events.jsonl       {len(updates)} 行"
              f"（文档级 {update_stats['doc_level_rows']}/40，"
              f"主张级 {update_stats['chunk_level_rows']}/40，"
              f"ρ 局部 {rho['local_ratio']:.3f}）")

    # 6. 校准抽样清单（计时由 calibrate.py 执行；req_id 集合不变时保留已实测 t_act_ms）
    calib = calibration_sample(main_rows, {c["req_id"]: c for c in main_ctx})
    io.write_jsonl(out / "calibration_sample.jsonl", calib)
    if out.resolve() == HERE.resolve():
        _check_calibration_template(out, calib)

    manifest = _manifest(out, docs, main_rows, updates, pool, calib, update_stats)
    io.write_json(out / "MANIFEST.json", manifest)
    if verbose:
        print(f"  MANIFEST.json             记录 {len(manifest) - 1} 个文件")
    return manifest


def _rows_of(path: Path) -> int:
    if path.suffix == ".csv":
        with path.open("r", encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)
    if path.suffix == ".json":
        return 1
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def _manifest(out: Path, docs: list[dict], main_rows: list[dict], updates: list[dict],
              pool: dict, calib: list[dict], update_stats: dict) -> dict:
    files = ["docs_versioned.jsonl", "request_stream.jsonl", "request_context.jsonl",
             "update_events.jsonl", "act_plan_pool.json", "calibration_sample.jsonl"]
    names = [s[0] for s in STREAM_SPECS] + [s[0] for s in LONG_SPECS]
    files += [f"streams/{n}.jsonl" for n in names]
    # 脚本与说明按存在与否登记（临时目录里可能没有），保证 --out 到空目录也能跑通
    for extra in ("build.py", "calibrate.py", "selfcheck.py", "CALIBRATION.md", "README.md"):
        if (out / extra).is_file():
            files.append(extra)
    manifest: dict = {}
    for rel in files:
        p = out / rel
        manifest[rel] = {"rows": _rows_of(p), "sha256": io.sha256_file(p)}
    csv = out / "real_calibration_300.template.csv"
    if csv.is_file():
        manifest["real_calibration_300.template.csv"] = {
            "rows": _rows_of(csv), "sha256": io.sha256_file(csv),
            "measured": True, "tolerance": "计时随机器波动，重测会改变哈希",
            "note": "只有 t_act_ms 是 calibrate.py 真实执行 gold_sql 的实测值，其余列留空"}

    snaps = Counter(r["snapshot"]["index"] for r in main_rows)
    classes = Counter(u["change_type"] for u in updates)
    ctx = list(io.read_jsonl(out / "request_context.jsonl"))
    tenants = Counter(c["tenant"] for c in ctx)
    first6 = [c for c in ctx if c["timestamp"] < "2024-05-15T06:00:00Z"]
    hot_first6 = sum(1 for c in first6 if c["bucket"] == "hot")
    dn = [len(a["downstream_tools"]) for a in pool["acts"]]
    buckets = Counter(min(d, 3) for d in dn)
    by_steps: dict[str, list[float]] = defaultdict(list)
    for p in pool["plans"]:
        by_steps[str(len(p["steps"]))].append(p["completion_rate"])
    manifest["stats"] = {
        "docs_versioned": {"rows": len(docs),
                           "doc_types": dict(sorted(Counter(
                               d["doc_type"] for d in docs if d["version"] == 1).items())),
                           "versions": dict(sorted(Counter(
                               str(d["version"]) for d in docs).items()))},
        "streams": {"primary": len(main_rows), "seed_copies": len(STREAM_SPECS),
                    "long": [s[1] for s in LONG_SPECS],
                    "time_span_hours": SPAN_HOURS,
                    "switch_hours": {s[0]: s[2] for s in STREAM_SPECS + LONG_SPECS},
                    "snapshot_index": dict(sorted(snaps.items())),
                    "distinct_query_text": len({r["query_text"] for r in main_rows}),
                    "distinct_tasks": len({c["task_id"] for c in ctx}),
                    "distinct_clusters": len({c["cluster_id"] for c in ctx}),
                    "claims_per_request": dict(sorted(Counter(
                        len(r["gold_fact_spans"]) for r in main_rows).items())),
                    "reuse_rate": round(sum(1 for c in ctx if c["reused"]) / len(ctx), 4),
                    "hot_share_first_6h": round(hot_first6 / max(1, len(first6)), 4),
                    "hot_set_size": HOT_SIZE,
                    "tail_set_size": TAIL_SIZE,
                    "query_emb": "all null"},
        "tenants": {"counts": dict(sorted(tenants.items())),
                    "permission_negatives": sum(1 for c in ctx if c["permission_negative"]),
                    "note": "租户在 schema 里只能通过 permission 落地："
                            "tenant_restricted 一律 permission=restricted，"
                            "其余租户沿用题目 permission；租户与源题映射见 request_context.jsonl"},
        "updates": dict(update_stats, rows=len(updates),
                        by_class=dict(sorted(classes.items()))),
        "pool": {"acts": len(pool["acts"]), "plans": len(pool["plans"]),
                 "act_cost_min": min(a["act_cost"] for a in pool["acts"]),
                 "act_cost_max": max(a["act_cost"] for a in pool["acts"]),
                 "downstream_nonempty_ratio": round(sum(1 for d in dn if d) / len(dn), 4),
                 "downstream_buckets": {str(k): buckets.get(k, 0) for k in (0, 1, 2, 3)},
                 "downstream_target": PARAMS["act_plan"]["downstream_target"],
                 "plan_steps": dict(sorted(Counter(
                     str(len(p["steps"])) for p in pool["plans"]).items())),
                 "plan_completion_by_steps": {k: round(sum(v) / len(v), 4)
                                              for k, v in sorted(by_steps.items())},
                 "plan_completion": [min(p["completion_rate"] for p in pool["plans"]),
                                     max(p["completion_rate"] for p in pool["plans"])],
                 "plan_cost": [min(p["plan_cost"] for p in pool["plans"]),
                               max(p["plan_cost"] for p in pool["plans"])]},
        "calibration": {"sample_rows": len(calib), "target_rows": CALIB_ROWS,
                        "measured_columns": ["t_act_ms"],
                        "blank_columns": ["t_plan_ms", "t_rag_ms", "t_resp_ms",
                                          "t_total_ms", "token_cost"],
                        "template_note": "req_id 集合未变时保留已实测 t_act_ms，不重测"},
    }
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="构建 P4 事件层")
    ap.add_argument("--out", default=str(HERE), help="输出目录（默认 dataset/events）")
    ap.add_argument("--calibrate", action="store_true", help="构建后顺带跑真实计时校准")
    args = ap.parse_args(argv)
    out = Path(args.out)
    print(f"[events] 输出目录 {out}")
    build_all(out)
    if args.calibrate:
        sys.path.insert(0, str(HERE))
        import calibrate  # noqa: PLC0415  同一目录的执行器，仅在显式要求时加载
        calibrate.run(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""P3：取数题库（200 题）与三层真值的确定性生成器。

设计要点
--------
* 题目、SQL、证据全部由本脚本确定性生成：随机只来自 ``common/seeds.py``，
  表结构只来自 ``contracts/tables.json``，规模只来自 ``config/params.json``。
  同一 (params, v0 快照, docs v1) 下重跑 ``tasks.jsonl`` 字节一致。
* 数值层：``truth.value`` 来自 ``db/executor.py`` 在 v0 上的真实执行结果。
  标量题存数字，表格题存行列表；每题 SQL 自带行数上限（≤20 行），不做截断。
  gold_sql / truth.value / expected_columns 与 v0.1.0 保持一致，只重建主张层与簇。
* 口径层：``metric_refs`` 指向 ``knowledge/docs.jsonl`` 中真实存在的 ``metric_XXX``，
  并在证据里引用其定义块 / 计算式块 / 口径边界块。
* 主张层：按 ``params.tasks.claims_per_task`` 的分层配额给每题分配 1–5 条主张
  （难度层内分层抽样，保证每类题量都有 1..5 条主张的样本）。每条主张对应一个
  不同侧面（答案值 / 规模 / 结构占比 / 覆盖面 / 口径边界等），每条挂 1–2 个
  真实证据块；``truth.evidence`` 严格等于该题全部主张证据的并集。
  题干答案值不可从结果集直接读出的侧面（如记录数、去重客户数、全期占比）由
  本脚本在 v0 上执行**只读探查 SQL**得到，探查 SQL 不进入 ``gold_sql``。
* 语义簇：200 题按 (domain, 表族) 分组、组内再按主指标排序后切成 40 个 3–6 题的
  簇，簇名 ``cls_{domain}_{topic}``；同簇题目除共享所属表的白皮书外，还共同引用
  该数据域《…关键指标》白皮书的「计算与对账」块，作为簇内反馈借用的公共证据。
  分簇只依赖参数顺序与确定性排序，重跑一致，不含随机。
* 权限：取题目涉及表与指标的规范密级上限（public < staff < restricted）；
  主题（domain）取主表所属数据域，写入 MANIFEST。

用法
----
    python dataset/tasks/build.py              # 写入 dataset/tasks/
    python dataset/tasks/build.py --out DIR    # 写入指定目录（selfcheck 复现用）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

from common import ids, io, seeds  # noqa: E402
import executor  # noqa: E402

SNAPSHOT = "v0"
EVIDENCE_VERSION = 1
ROW_CAP = 20
PERM_ORDER = ("public", "staff", "restricted")

PARAMS = io.read_json(ROOT / "config" / "params.json")
TASK_PARAMS = PARAMS["tasks"]
CLUSTER_PARAMS = PARAMS["clusters"]
TABLES = io.read_json(ROOT / "contracts" / "tables.json")["tables"]

# 主张数配额：按 params.tasks.claims_per_task 换算成 200 题的整数名额，
# 再在难度层内按同一比例分摊（单表 9/12/18/12/9，join 10/14/21/14/11，
# 嵌套 11/14/21/14/10），保证每种主张数在每个难度层都出现。
CLAIM_QUOTA = {
    "single_table": {1: 9, 2: 12, 3: 18, 4: 12, 5: 9},
    "join": {1: 10, 2: 14, 3: 21, 4: 14, 5: 11},
    "nested_agg": {1: 11, 2: 14, 3: 21, 4: 14, 5: 10},
}
CLAIM_COUNT_VALUES = (1, 2, 3, 4, 5)

# 域级白皮书：wp_181..wp_200 为五个数据域各四篇（总览 / 关键指标 / 关联陷阱 / 权限与合规），
# 由 knowledge 层的标题首句识别，不手写文档编号。
DOMAIN_ZH = {"sales": "销售", "supply": "供应链", "finance": "财务",
             "ops": "运营", "meta": "元数据"}
DOMAIN_ANGLE_KEYS = (("域总览", "overview"), ("关键指标", "metrics"),
                     ("关联陷阱", "joins"), ("权限与合规", "permission"))


# ---------------------------------------------------------------- 表与字段目录
TABLE_NAMES = [t["name"] for t in TABLES]
TABLE_ID = {t["name"]: t["table_id"] for t in TABLES}
TABLE_FIELDS = {t["name"]: [f["name"] for f in t["fields"]] for t in TABLES}
FIELD_POS = {t["name"]: {f["name"]: i + 1 for i, f in enumerate(t["fields"])} for t in TABLES}
TABLE_KIND = {}
for _t in TABLES:
    _n = _t["name"]
    TABLE_KIND[_n] = ("dim" if _n.startswith("dim_") else
                      "agg" if _n.startswith("agg_") else
                      "log" if _n.startswith("log_") else "fact")

FACT_TABLES = [n for n in TABLE_NAMES if TABLE_KIND[n] == "fact"]
AGG_TABLES = [n for n in TABLE_NAMES if TABLE_KIND[n] == "agg"]
LOG_TABLES = [n for n in TABLE_NAMES if TABLE_KIND[n] == "log"]

# 题面用中文业务名（不出现 t12 / fact_orders 这类内部编号）
NAME_ZH = {
    "dim_date": "日期维", "dim_region": "区域维", "dim_channel": "渠道维",
    "dim_customer": "客户维", "dim_product": "商品维", "dim_store": "门店维",
    "dim_employee": "员工维", "dim_promotion": "促销活动维",
    "fact_orders": "订单", "fact_order_item": "订单明细", "fact_sales_daily": "日销售",
    "fact_returns": "退货", "fact_refunds": "退款", "fact_payments": "支付",
    "fact_invoices": "发票", "fact_shipments": "发货", "fact_deliveries": "配送",
    "fact_inventory": "库存", "fact_inventory_snapshot": "库存快照",
    "fact_stock_move": "库存移动", "fact_price_change": "调价",
    "fact_promotion_apply": "促销核销", "fact_campaign_touch": "营销触达",
    "fact_clicks": "点击", "fact_sessions": "会话", "fact_leads": "线索",
    "fact_quotes": "报价", "fact_contracts": "合同", "fact_subscriptions": "订阅",
    "fact_renewals": "续费", "fact_churn": "流失", "fact_tickets": "工单",
    "fact_sla_events": "SLA 事件", "fact_usage": "用量", "fact_engagement": "互动",
    "fact_budget": "预算", "fact_targets": "目标", "fact_forecast": "预测",
    "fact_collections": "回款", "fact_supplier_orders": "采购订单",
    "fact_quality_checks": "质检", "fact_costs": "成本",
    "agg_daily_sales": "日销售汇总", "agg_monthly_gmv": "月度 GMV 汇总",
    "agg_region_share": "区域份额", "agg_channel_mix": "渠道结构",
    "agg_product_rank": "商品排名", "agg_customer_ltv": "客户 LTV",
    "agg_cohort_retention": "队列留存", "agg_funnel": "转化漏斗",
    "agg_sla_summary": "SLA 汇总", "agg_cost_breakdown": "成本拆解",
    "agg_forecast_error": "预测误差", "agg_inventory_turnover": "库存周转",
    "log_query_audit": "查询审计日志", "log_etl_run": "ETL 运行日志",
    "log_access": "访问审计日志", "log_metric_change": "指标变更日志",
    "log_schema_change": "结构变更日志", "log_backfill": "回填日志",
}
assert set(NAME_ZH) == set(TABLE_NAMES), "中文业务名未覆盖全部 60 张表"

# ---------------------------------------------------------------- 度量目录
# field -> (中文名, 小数位, 单位类型, 聚合函数, 单位后缀)
MEASURE_FIELDS = {
    "amount": ("金额", 2, "money", "sum", "元"),
    "gross_amount": ("毛金额", 2, "money", "sum", "元"),
    "net_amount": ("净金额", 2, "money", "sum", "元"),
    "discount_amount": ("折扣额", 2, "money", "sum", "元"),
    "tax_amount": ("税额", 2, "money", "sum", "元"),
    "cost_amount": ("成本额", 2, "money", "sum", "元"),
    "unit_price": ("单价", 2, "money", "avg", "元"),
    "quantity": ("数量", 2, "qty", "sum", ""),
    "metric_value": ("指标值", 2, "money", "sum", "元"),
    "metric_ratio": ("指标比率", 4, "ratio", "weighted", ""),
    "metric_delta": ("指标增量", 4, "ratio", "sum", ""),
    "sample_size": ("样本量", 2, "qty", "sum", ""),
    "duration_ms": ("耗时", 2, "dur", "avg", "毫秒"),
    "payload_size": ("载荷大小", 2, "qty", "sum", ""),
}

# ---------------------------------------------------------------- 时间区间
def _iso(key: int) -> str:
    return f"{key // 10000:04d}-{key % 10000 // 100:02d}-{key % 100:02d}"


@dataclass(frozen=True)
class Period:
    key: str
    start: int
    end: int
    zh: str
    months: int = 1

    @property
    def iso_start(self) -> str:
        return _iso(self.start)

    @property
    def iso_end(self) -> str:
        return _iso(self.end)

    def window(self) -> dict:
        return {"start": f"{self.iso_start}T00:00:00Z", "end": f"{self.iso_end}T23:59:59Z"}

    def range_zh(self) -> str:
        return f"{self.iso_start} 至 {self.iso_end}"


PERIODS = [
    Period("2024-01", 20240101, 20240131, "2024 年 1 月", 1),
    Period("2024-02", 20240201, 20240229, "2024 年 2 月", 1),
    Period("2024-03", 20240301, 20240331, "2024 年 3 月", 1),
    Period("2024-04", 20240401, 20240430, "2024 年 4 月", 1),
    Period("2024-Q1", 20240101, 20240331, "2024 年 1—3 月", 3),
    Period("2024-02..04", 20240201, 20240430, "2024 年 2—4 月", 3),
    Period("2024-01..04", 20240101, 20240430, "2024 年 1—4 月", 4),
    Period("2024-02..03", 20240201, 20240331, "2024 年 2—3 月", 2),
    Period("2024-01..05", 20240101, 20240514, "2024 年 1—5 月", 5),
]

# ---------------------------------------------------------------- 知识层索引
def _load_docs() -> dict:
    by_id = {}
    for row in io.read_jsonl(ROOT / "knowledge" / "docs.jsonl"):
        if row["version"] == EVIDENCE_VERSION:
            by_id[row["doc_id"]] = row
    return by_id


DOCS = _load_docs()
DOC_CHUNKS = {d: tuple(c["chunk_id"] for c in r["chunks"]) for d, r in DOCS.items()}
DOC_PERM = {d: r["permission"] for d, r in DOCS.items()}
DOC_DOMAIN = {d: r["domain"] for d, r in DOCS.items()}
DOC_TEXT = {d: "\n".join(c["text"] for c in r["chunks"]) for d, r in DOCS.items()}

# 白皮书：每张表三篇（使用说明 / 关联说明 / 口径陷阱），按 tables.json 顺序每表 3 篇
WP_SLOTS: dict[str, dict[str, str]] = {}
for _idx, _tbl in enumerate(TABLES, start=1):
    _group = [f"wp_{3 * (_idx - 1) + k:03d}" for k in (1, 2, 3)]
    _pk = TABLE_FIELDS[_tbl["name"]][0]
    _slots: dict[str, str] = {}
    for _doc in _group:
        assert _doc in DOCS, f"缺白皮书 {_doc}"
        _head = DOCS[_doc]["chunks"][0]["text"]
        _slot = ("join" if "关联说明" in _head
                 else "trap" if "口径陷阱" in _head
                 else "usage")
        assert _tbl["name"] in DOC_TEXT[_doc] or _pk in DOC_TEXT[_doc], \
            f"{_doc} 未指向 {_tbl['name']}"
        _slots[_slot] = _doc
    WP_SLOTS[_tbl["name"]] = _slots
for _name in TABLE_NAMES:
    assert set(WP_SLOTS.get(_name, {})) == {"usage", "join", "trap"}, f"{_name} 白皮书分档不全"

# 域级白皮书索引：{domain: {overview/metrics/joins/permission: doc_id}}。
DOMAIN_WP: dict[str, dict[str, str]] = {}
for _doc, _row in sorted(DOCS.items()):
    if not _doc.startswith("wp_") or int(_doc[3:]) < 181:
        continue
    _head = _row["chunks"][0]["text"]
    _angle = next((key for marker, key in DOMAIN_ANGLE_KEYS if marker in _head), None)
    assert _angle, f"域级白皮书 {_doc} 无法识别角度"
    DOMAIN_WP.setdefault(_row["domain"], {})[_angle] = _doc
for _dom in DOMAIN_ZH:
    assert set(DOMAIN_WP.get(_dom, {})) == {"overview", "metrics", "joins", "permission"}, \
        f"{_dom} 域级白皮书不齐：{sorted(DOMAIN_WP.get(_dom, {}))}"
assert set(DOMAIN_WP) == set(DOMAIN_ZH), f"域级白皮书出现未知域：{sorted(DOMAIN_WP)}"

# 域口径块（《关键指标》p02「计算与对账」）：同域题目共同引用的公共证据。
DOMAIN_REF: dict[str, tuple[str, int]] = {
    dom: (DOMAIN_WP[dom]["metrics"], 2) for dom in DOMAIN_ZH
}
for _dom, (_doc, _p) in DOMAIN_REF.items():
    assert f"{_doc}#p{_p:02d}" in DOC_CHUNKS[_doc], f"{_dom} 域口径块不存在"


# 指标卡：(表, 字段) -> [metric_id]；同时解析指标名与默认窗口
METRIC_BY_TF: dict[tuple[str, str], list[str]] = {}
METRIC_META: dict[str, dict] = {}
_MONEY_WORDS = ("金额", "GMV", "gmv", "收入", "成本", "税额", "折扣", "单价", "价")
_RATIO_WORDS = ("比率", "占比", "率", "系数", "倍数", "份额", "留存", "误差", "周转")
_QTY_WORDS = ("数量", "笔数", "行数", "次数", "天数", "样本量", "名次", "序号")
_PK2TABLE = {t["fields"][0]["name"]: t["name"] for t in TABLES}


def _metric_label(text: str) -> str:
    """指标名（去掉括注里的表名限定，如「指标比率（区域份额）」→「指标比率」）。"""
    m = re.search(r"指标 (metric_\d+)：([^。]+)。", text)
    raw = m.group(2).strip() if m else ""
    if not raw:
        m = re.search(r"metric_\d+（([^）]+)）", text)
        raw = m.group(1).strip() if m else ""
    return re.sub(r"（[^）]*）", "", raw).strip()


def _classify(label: str) -> str:
    if any(w in label for w in _RATIO_WORDS):
        return "ratio"
    if any(w in label for w in _QTY_WORDS):
        return "qty"
    if any(w in label for w in _MONEY_WORDS):
        return "money"
    return "ratio"


for _metric in sorted(d for d in DOCS if d.startswith("metric_")):
    _text = DOC_TEXT[_metric]
    _label = _metric_label(_text)
    _hit = None
    m = re.search(r"((?:fact|agg|dim|log)_[a-z_]+)\.([a-z_]+)", _text)
    if m and m.group(1) in TABLE_FIELDS and m.group(2) in TABLE_FIELDS[m.group(1)]:
        _hit = (m.group(1), m.group(2))
    else:
        fm = re.search(r"度量对象是 (\w+) 字段", _text)
        dm = re.search(r"去重键为 (\w+)", _text)
        if fm and dm and dm.group(1) in _PK2TABLE:
            tbl = _PK2TABLE[dm.group(1)]
            if fm.group(1) in TABLE_FIELDS[tbl]:
                _hit = (tbl, fm.group(1))
    if not _hit:
        continue
    _win = re.search(r"默认统计窗口 (\d+) 天", _text)
    METRIC_META[_metric] = {
        "table": _hit[0],
        "field": _hit[1],
        "label": _label or f"{NAME_ZH[_hit[0]]}{MEASURE_FIELDS[_hit[1]][0]}",
        "kind": _classify(_label),
        "window": int(_win.group(1)) if _win else 30,
        "perm": DOC_PERM[_metric],
        "domain": DOC_DOMAIN[_metric],
    }
    METRIC_BY_TF.setdefault(_hit, []).append(_metric)
for _k in METRIC_BY_TF:
    METRIC_BY_TF[_k] = sorted(METRIC_BY_TF[_k])


# 汇总表度量的表级语义：通用标签（指标值 / 指标增量）靠这张表判定金额还是比率
AGG_KIND = {
    "agg_daily_sales": "money", "agg_monthly_gmv": "money", "agg_region_share": "ratio",
    "agg_channel_mix": "ratio", "agg_product_rank": "ordinal",
    "agg_customer_ltv": "money", "agg_cohort_retention": "ratio", "agg_funnel": "ratio",
    "agg_sla_summary": "ratio", "agg_cost_breakdown": "money",
    "agg_forecast_error": "ratio", "agg_inventory_turnover": "ratio",
}
assert set(AGG_KIND) == set(AGG_TABLES), "汇总表语义表未覆盖 12 张汇总表"


def measure_info(table: str, field: str, metric: str | None) -> dict:
    """返回度量的展示信息：中文名、小数位、单位类型、聚合函数、单位后缀、指标名。"""
    zh, dec, kind, agg, unit = MEASURE_FIELDS[field]
    label = METRIC_META.get(metric, {}).get("label", "") if metric else ""
    if field in ("metric_value", "metric_delta") and table in AGG_KIND:
        if AGG_KIND[table] == "money":
            kind, dec, unit = "money", 2, "元"
        else:
            kind, dec, unit = "ratio", 4, ""
    if zh.startswith("指标值") and label:
        zh = label
    if field == "metric_value" and "GMV" in label:
        zh = "GMV"
    return {"field": field, "zh": zh, "decimals": dec, "kind": kind,
            "agg": agg, "unit": unit, "label": label}


def field_doc(table: str, field_name: str) -> str:
    return ids.field_id(TABLE_ID[table], FIELD_POS[table][field_name])


# ---------------------------------------------------------------- 集合与文档引用
def canonical_perm(table: str) -> str:
    perms = [DOC_PERM[WP_SLOTS[table][s]] for s in ("usage", "join", "trap")]
    return max(perms, key=PERM_ORDER.index)


TABLE_PERM = {n: canonical_perm(n) for n in TABLE_NAMES}
TABLE_DOMAIN = {n: DOC_DOMAIN[WP_SLOTS[n]["usage"]] for n in TABLE_NAMES}

# ---------------------------------------------------------------- 语义簇
# 分簇依据：(domain, 表族)；表族按业务过程划分，簇内再按主指标、表、周期、
# 题族排序后均分成 3–6 题的簇。分簇过程不含随机，重跑一致。
DOMAIN_FAMILIES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "sales": (
        ("orders", ("fact_orders", "fact_order_item", "fact_sales_daily",
                    "agg_daily_sales", "agg_product_rank", "agg_region_share")),
        ("promotion", ("fact_promotion_apply", "fact_campaign_touch", "fact_clicks",
                       "fact_sessions", "fact_leads", "agg_funnel")),
        ("subscription", ("fact_subscriptions", "fact_renewals", "fact_churn",
                          "agg_customer_ltv", "agg_cohort_retention")),
        ("returns", ("fact_returns",)),
        ("contract", ("fact_contracts", "fact_quotes", "fact_price_change")),
    ),
    "supply": (
        ("shipment", ("fact_shipments", "fact_deliveries")),
        ("procurement", ("fact_supplier_orders", "fact_quality_checks")),
        ("inventory", ("fact_inventory", "fact_stock_move", "agg_inventory_turnover")),
    ),
    "finance": (
        ("invoice", ("fact_invoices", "fact_payments")),
        ("cost", ("fact_costs", "agg_cost_breakdown", "fact_forecast",
                  "agg_forecast_error")),
        ("target", ("fact_targets", "fact_budget")),
        ("collection", ("fact_collections", "fact_refunds")),
    ),
    "ops": (
        ("usage", ("fact_usage",)),
        ("sla", ("fact_sla_events", "agg_sla_summary")),
        ("ticket", ("fact_tickets",)),
    ),
    "meta": (
        ("audit", ("log_query_audit", "log_etl_run", "log_access",
                   "log_metric_change", "log_schema_change", "log_backfill")),
    ),
}
DOMAIN_ORDER = tuple(DOMAIN_FAMILIES)          # sales, supply, finance, ops, meta
TABLE_FAMILY: dict[str, str] = {}
FAMILY_TABLES: dict[tuple[str, str], tuple[str, ...]] = {}
for _dom, _fams in DOMAIN_FAMILIES.items():
    assert _dom in DOMAIN_ZH, f"未知数据域 {_dom}"
    for _fam, _tbs in _fams:
        assert (_dom, _fam) not in FAMILY_TABLES
        FAMILY_TABLES[(_dom, _fam)] = tuple(_tbs)
        for _tb in _tbs:
            assert _tb in TABLE_NAMES, f"表族 {_fam} 引用了不存在的表 {_tb}"
            assert _tb not in TABLE_FAMILY, f"表 {_tb} 被重复归族"
            assert TABLE_KIND[_tb] in ("fact", "agg", "log"), f"表族不应包含维表 {_tb}"
            assert TABLE_DOMAIN[_tb] == _dom, f"{_tb} 域为 {TABLE_DOMAIN[_tb]}，与族 {_dom} 不符"
            TABLE_FAMILY[_tb] = _fam

# 主指标排序：金额类 → 数量类 → 汇总指标 → 日志耗时/载荷 → 计数类
MEASURE_ORDER = ("amount", "gross_amount", "net_amount", "discount_amount", "tax_amount",
                 "cost_amount", "unit_price", "quantity", "metric_value", "metric_ratio",
                 "metric_delta", "duration_ms", "payload_size")
COUNT_MEASURE_RANK = len(MEASURE_ORDER)


def _measure_rank(spec: "Spec") -> int:
    return (MEASURE_ORDER.index(spec.measure) if spec.measure in MEASURE_ORDER
            else COUNT_MEASURE_RANK)


def _family_sizes(n: int) -> list[int]:
    """把 n 道题均分成每簇 3–6 题（k 取最少簇数，余数摊到前面的簇）。"""
    lo, hi = CLUSTER_PARAMS["min_size"], CLUSTER_PARAMS["max_size"]
    if n <= hi:
        assert n >= lo, f"表族只有 {n} 道题，不足最小簇规模 {lo}"
        return [n]
    k = -(-n // hi)
    base, extra = divmod(n, k)
    sizes = [base + 1] * extra + [base] * (k - extra)
    assert sizes[0] <= hi and sizes[-1] >= lo, f"{n} 题无法均分为 3–6 题簇：{sizes}"
    return sizes


def assign_clusters(specs: list["Spec"]) -> tuple[dict[int, str], list[dict]]:
    """给每道题分配 cluster_id，返回 ({seq: cluster_id}, 簇元数据列表)。"""
    grouped: dict[tuple[str, str], list[tuple[int, "Spec"]]] = {}
    for seq, spec in enumerate(specs, start=1):
        primary = spec.tables[0]
        family = TABLE_FAMILY.get(primary)
        assert family, f"{spec.family} 第 {seq} 题主表 {primary} 未归入任何表族"
        grouped.setdefault((spec.domain, family), []).append((seq, spec))

    seq_to_cluster: dict[int, str] = {}
    clusters: list[dict] = []
    for dom in DOMAIN_ORDER:
        for family, tables in DOMAIN_FAMILIES[dom]:
            items = grouped.get((dom, family), [])
            if not items:
                continue
            table_pos = {tb: i for i, tb in enumerate(tables)}
            items.sort(key=lambda it: (
                _measure_rank(it[1]),
                table_pos[it[1].tables[0]],
                PERIODS.index(it[1].period),
                it[1].family,
                it[0],
            ))
            sizes = _family_sizes(len(items))
            cursor = 0
            for idx, size in enumerate(sizes, start=1):
                chunk = items[cursor:cursor + size]
                cursor += size
                cluster_id = f"cls_{dom}_{family}" if idx == 1 else f"cls_{dom}_{family}_{idx}"
                assert cluster_id not in {c["cluster_id"] for c in clusters}, cluster_id
                for seq, _spec in chunk:
                    assert seq not in seq_to_cluster, f"q{seq:03d} 被分到多个簇"
                    seq_to_cluster[seq] = cluster_id
                clusters.append({
                    "cluster_id": cluster_id,
                    "domain": dom,
                    "family": family,
                    "size": len(chunk),
                    "task_ids": [f"q{seq:03d}" for seq, _ in chunk],
                    "primary_tables": sorted({_spec.tables[0] for _, _spec in chunk}),
                    "measures": sorted({_spec.measure for _, _spec in chunk}),
                    "difficulties": dict(sorted(Counter(
                        _spec.difficulty for _, _spec in chunk).items())),
                    "claim_counts": sorted({_spec.extra["claim_count"] for _, _spec in chunk})
                    if chunk and "claim_count" in chunk[0][1].extra else [],
                })
    want = CLUSTER_PARAMS["count"]
    assert len(clusters) == want, f"簇数 {len(clusters)} != params.clusters.count {want}"
    assert len(seq_to_cluster) == len(specs), f"分簇覆盖 {len(seq_to_cluster)}/{len(specs)} 题"
    return seq_to_cluster, clusters


DIM_SPECS = {
    "dim_customer": {"alias": "c", "key": "customer_key", "pk": "customer_id",
                     "zh": "客户维", "attrs": {
                         "region_code": "客户所属大区编码",
                         "status": "客户状态"}},
    "dim_product": {"alias": "p", "key": "product_key", "pk": "product_id",
                    "zh": "商品维", "attrs": {"status": "商品状态"}},
    "dim_store": {"alias": "s", "key": "store_key", "pk": "store_id",
                  "zh": "门店维", "attrs": {
                      "region_code": "门店所属大区编码",
                      "status": "门店状态"}},
    "dim_channel": {"alias": "ch", "key": "channel_key", "pk": "channel_id",
                    "zh": "渠道维", "attrs": {
                        "channel_code": "渠道类型编码",
                        "status": "渠道状态"}},
    "dim_date": {"alias": "d", "key": "date_key", "pk": "date_id", "right": "date_key",
                 "zh": "日期维", "attrs": {
                     "category": "日期类型",
                     "month_label": "月份"}},
}
DIM_CARD = {"dim_customer": 8, "dim_store": 8, "dim_product": 2,
            "dim_channel": 20, "dim_date": 5}


def make_refs(table: str, field_name: str, metric: str | None,
              dims: tuple[str, ...] = ()) -> dict[str, tuple[str, int]]:
    """题目可引用的证据块索引：全部来自 knowledge/docs.jsonl 的 v1 真实块。"""
    refs: dict[str, tuple[str, int]] = {
        "wp_usage": (WP_SLOTS[table]["usage"], 1),
        "wp_rows": (WP_SLOTS[table]["usage"], 2),
        "wp_grain": (WP_SLOTS[table]["usage"], 3),
        "wp_keys": (WP_SLOTS[table]["join"], 1),
        "wp_join": (WP_SLOTS[table]["join"], 2),
        "wp_join_risk": (WP_SLOTS[table]["join"], 3),
        "wp_caliber": (WP_SLOTS[table]["trap"], 1),
        "wp_trap": (WP_SLOTS[table]["trap"], 2),
        "wp_recon": (WP_SLOTS[table]["trap"], 3),
        "field_def": (field_doc(table, field_name), 1),
        "field_trap": (field_doc(table, field_name), 2),
        # 客户计数类主张用客户维主键字段卡作证据（维表字段卡为公开级，避免无谓抬升题目密级）
        "customer_field": (field_doc("dim_customer", "customer_id"), 1)
        if "customer_key" in TABLE_FIELDS[table] else None,
    }
    refs = {k: v for k, v in refs.items() if v}
    if metric:
        refs["metric_def"] = (metric, 1)
        refs["metric_calc"] = (metric, 2)
        refs["metric_bound"] = (metric, 3)
    for dim in dims:
        spec = DIM_SPECS[dim]
        refs[f"{dim}_join"] = (WP_SLOTS[dim]["join"], 2)
        refs[f"{dim}_keys"] = (WP_SLOTS[dim]["join"], 1)
        refs[f"{dim}_field"] = (field_doc(dim, spec["pk"]), 1)
    for key, (doc, no) in refs.items():
        assert f"{doc}#p{no:02d}" in DOC_CHUNKS[doc], f"证据块不存在：{doc}#p{no:02d}"
    return refs


# ---------------------------------------------------------------- 数据探查（只读）
@lru_cache(maxsize=None)
def distinct_values(table: str, column: str) -> tuple:
    out = executor.execute(SNAPSHOT, f"SELECT DISTINCT {column} AS v FROM {table} ORDER BY 1")
    assert not out["error"], f"探查失败 {table}.{column}: {out['error']}"
    return tuple(r[0] for r in out["rows"])


# ---------------------------------------------------------------- 题面与真值组装
@dataclass
class Spec:
    family: str
    difficulty: str
    question: str
    sql: str
    tables: list[str]
    domain: str
    measure: str
    measure_zh: str
    decimals: int
    kind: str
    unit: str
    period: Period
    caliber: str
    metric_refs: list[str]
    refs: dict
    claims: object
    measure_agg: str = "sum"
    limit: int | None = None
    extra: dict = field(default_factory=dict)


_CJK_LATIN = re.compile(r"([\u4e00-\u9fff])([A-Za-z0-9])")
_LATIN_CJK = re.compile(r"([A-Za-z0-9])([\u4e00-\u9fff])")


def tidy(text: str) -> str:
    """中英混排补空格，码值（RG01/CH03）与中文之间也留空，便于阅读。"""
    text = _CJK_LATIN.sub(r"\1 \2", text)
    text = _LATIN_CJK.sub(r"\1 \2", text)
    return re.sub(r"[ ]{2,}", " ", text).strip()


def _claim(text: str, *refs) -> dict:
    return {"text": tidy(text), "refs": [r for r in refs if r]}


def _num(value, decimals: int) -> str:
    return f"{float(value):,.{decimals}f}"


def _int(value) -> str:
    return f"{int(value):,}"


def fmt_value(value, decimals: int, kind: str, unit: str = "") -> str:
    """真值的题面写法：金额/数量 2 位、比率 4 位、计数取整。"""
    if kind == "count":
        return f"{int(value):,} 笔"
    if kind == "ratio":
        return _num(value, decimals)
    return (f"{_num(value, decimals)} {unit}").strip()


class Context:
    """执行结果访问器，供 claims 闭包使用。"""

    def __init__(self, spec: Spec, columns: list[str], rows: list[list]):
        self.spec = spec
        self.columns = list(columns)
        self.rows = [list(r) for r in rows]
        self.pos = {c: i for i, c in enumerate(self.columns)}

    def cell(self, row: int, name: str):
        return self.rows[row][self.pos[name]]

    def col(self, name: str) -> list:
        i = self.pos[name]
        return [r[i] for r in self.rows]

    @property
    def n(self) -> int:
        return len(self.rows)


def _normalize(rows: list[list]) -> tuple[object, str]:
    cells = [[v for v in row] for row in rows]
    if len(cells) == 1 and len(cells[0]) == 1 and isinstance(cells[0][0], (int, float)):
        return cells[0][0], "scalar"
    return cells, "table"


def _ref_tuple(ref) -> tuple[str, int]:
    doc, no = ref
    return doc, no


def _to_evidence(refs) -> list[dict]:
    seen, out = set(), []
    for doc, no in refs:
        chunk = f"{doc}#p{no:02d}"
        if chunk in seen:
            continue
        seen.add(chunk)
        out.append({"doc_id": doc, "chunk_id": chunk, "version": EVIDENCE_VERSION})
    return out


# ---------------------------------------------------------------- 主张构造工具
def _dref(domain: str) -> tuple[str, int]:
    """该数据域的公共口径块（《…关键指标》p02「计算与对账」）。"""
    return DOMAIN_REF[domain]


def _share(num, den, decimals: int = 2) -> str:
    """占比写成百分比；分母为 0 时按 0 处理（题面区间内实际不会出现）。"""
    den = float(den)
    val = 0.0 if den == 0 else float(num) / den
    return f"{val * 100:.{decimals}f}%"


def _rel_diff(value, base) -> str:
    """相对差（value 相对 base），写成百分比。"""
    base = float(base)
    return "0.00%" if base == 0 else f"{(float(value) - base) / base * 100:+.2f}%"


def _period_days(period: Period) -> int:
    def _d(key: int):
        return date(key // 10000, key % 10000 // 100, key % 100)

    return (_d(period.end) - _d(period.start)).days + 1


@lru_cache(maxsize=None)
def probe(sql: str):
    """执行一条只读探查 SQL（不进入 gold_sql），返回首行首列；空结果返回 None。"""
    out = executor.execute(SNAPSHOT, sql)
    if out["error"]:
        raise RuntimeError(f"探查 SQL 失败：{out['error']}\n{sql}")
    return out["rows"][0][0] if out["rows"] else None


def probe_row(sql: str) -> list:
    out = executor.execute(SNAPSHOT, sql)
    if out["error"]:
        raise RuntimeError(f"探查 SQL 失败：{out['error']}\n{sql}")
    return list(out["rows"][0]) if out["rows"] else []


FULL_PERIOD = PERIODS[-1]  # 2024-01-01..2024-05-14，覆盖 v0 快照全部业务日期


def scope_where(fact: str, period: Period, conds, joins: str = "",
                extra: str = "") -> str:
    """与题目同口径的 WHERE（仅用于探查，不进入 gold_sql）。"""
    parts = [where_fact("f", period, conds)]
    if extra:
        parts.append(extra)
    return f"FROM {fact} f\n{joins}WHERE " + " AND ".join(parts)


def build_one(seq: int, spec: Spec, claim_count: int, cluster_id: str) -> tuple[dict, dict, dict]:
    out = executor.execute(SNAPSHOT, spec.sql)
    if out["error"]:
        raise RuntimeError(f"{spec.family} 第 {seq} 题 SQL 执行失败：{out['error']}\n{spec.sql}")
    rows, columns = out["rows"], out["columns"]
    if not rows:
        raise RuntimeError(f"{spec.family} 第 {seq} 题结果为空：\n{spec.sql}")
    if spec.limit is not None and len(rows) > spec.limit:
        raise RuntimeError(f"{spec.family} 第 {seq} 题超出上限：{len(rows)} > {spec.limit}")
    if len(rows) > ROW_CAP:
        raise RuntimeError(f"{spec.family} 第 {seq} 题行数 {len(rows)} 超过 {ROW_CAP}")

    value, shape = _normalize(rows)
    ctx = Context(spec, columns, rows)
    claims = spec.claims(ctx, claim_count)
    if len(claims) != claim_count:
        raise RuntimeError(f"{spec.family} 第 {seq} 题主张数 {len(claims)} != 配额 {claim_count}")
    if not 1 <= len(claims) <= 5:
        raise RuntimeError(f"{spec.family} 第 {seq} 题 claim 数 {len(claims)} 不在 1—5 之间")
    texts = [c["text"] for c in claims]
    if len(set(texts)) != len(texts):
        raise RuntimeError(f"{spec.family} 第 {seq} 题主张文本重复：{texts}")
    for c in claims:
        if not 1 <= len(c["refs"]) <= 2:
            raise RuntimeError(f"{spec.family} 第 {seq} 题 claim 证据数超限：{c['refs']}")
        assert c["text"].strip(), f"{spec.family} 第 {seq} 题存在空主张"

    metric_refs = list(spec.metric_refs)
    # 证据层 = 全部主张证据的并集（不再额外挂 base 证据，保证可逐条回溯）
    refs: list[tuple[str, int]] = []
    for c in claims:
        refs.extend(c["refs"])
    evidence = _to_evidence(refs)
    if not evidence:
        raise RuntimeError(f"{spec.family} 第 {seq} 题证据层为空")

    # 权限：题目访问基线的密级上限 = 涉及表 + 声明指标 + 基线证据（表使用说明、度量字段卡、
    # 指标定义卡）+ 实际引用证据。基线证据即使未逐条写进主张，也是回答该题必须读到的对象，
    # 因此参与密级判定；与 v0.1.0 相比权限分布保持不变。
    access_refs = [spec.refs["wp_usage"], spec.refs["field_def"]]
    if metric_refs:
        access_refs.append(spec.refs["metric_def"])
    perms = {TABLE_PERM[t] for t in spec.tables}
    perms |= {DOC_PERM[m] for m in metric_refs}
    perms |= {DOC_PERM[doc] for doc, _no in access_refs}
    perms |= {DOC_PERM[e["doc_id"]] for e in evidence}
    permission = max(perms, key=PERM_ORDER.index)
    for doc in [e["doc_id"] for e in evidence]:
        assert PERM_ORDER.index(DOC_PERM[doc]) <= PERM_ORDER.index(permission), \
            f"{seq} 题引用了高于题目密级的证据 {doc}"

    if metric_refs and not any(e["doc_id"] in metric_refs for e in evidence):
        raise RuntimeError(f"{spec.family} 第 {seq} 题声明了指标但未引用指标卡")

    task = OrderedDict([
        ("task_id", ids.task_id(seq)),
        ("cluster_id", cluster_id),
        ("question", tidy(spec.question)),
        ("difficulty", spec.difficulty),
        ("gold_sql", spec.sql.strip()),
        ("snapshot", SNAPSHOT),
        ("answer_shape", shape),
        ("expected_columns", list(columns)),
        ("truth", {
            "value": value,
            "value_hash": io.sha256_text(json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))[:16],
            "claims": [{"text": c["text"], "evidence": _to_evidence(c["refs"])} for c in claims],
            "evidence": evidence,
        }),
        ("metric_refs", metric_refs),
        ("permission", permission),
        ("time_window", spec.period.window()),
    ])
    gold = {
        "task_id": ids.task_id(seq),
        "columns": list(columns),
        "rows": rows,
        "elapsed_ms": out["elapsed_ms"],
    }
    meta = {
        "family": spec.family,
        "difficulty": spec.difficulty,
        "cluster_id": cluster_id,
        "primary_table": spec.tables[0],
        "claim_count": claim_count,
        "tables": list(spec.tables),
        "domain": spec.domain,
        "permission": permission,
        "metric_refs": metric_refs,
        "column_cnt": len(columns),
        "uses_window": "OVER (" in spec.sql,
        "uses_cte": bool(re.search(r"AS\s*\(\s*SELECT", spec.sql, re.IGNORECASE)),
        "uses_subquery": bool(re.search(r"\(\s*SELECT", spec.sql, re.IGNORECASE))
        and (len(re.findall(r"\(\s*SELECT", spec.sql, re.IGNORECASE))
             - len(re.findall(r"AS\s*\(\s*SELECT", spec.sql, re.IGNORECASE))) > 0,
        "complete": spec.limit is None or len(rows) < spec.limit,
        "answer_shape": shape,
        "elapsed_ms": out["elapsed_ms"],
        "fact_tables": [t for t in spec.tables if TABLE_KIND[t] == "fact"],
        "dim_tables": [t for t in spec.tables if TABLE_KIND[t] == "dim"],
    }
    return task, gold, meta


# ---------------------------------------------------------------- WHERE 片段
def where_fact(alias: str, period: Period, extras=()) -> str:
    parts = [f"{alias}.date_key BETWEEN {period.start} AND {period.end}",
             f"{alias}.is_deleted = 0"]
    parts.extend(extras)
    return " AND ".join(parts)


def where_agg(alias: str, period: Period, extras=()) -> str:
    parts = [f"{alias}.date_key BETWEEN {period.start} AND {period.end}"]
    parts.extend(extras)
    return " AND ".join(parts)


def caliber_zh(extra_phrases) -> str:
    phrases = [p for p in extra_phrases if p]
    return "、".join(phrases) if phrases else "全量口径"


STATUS_VALUES = {t: distinct_values(t, "status_code") for t in FACT_TABLES}
CURRENCY_VALUES = {t: distinct_values(t, "currency_code") for t in FACT_TABLES}
EVENT_TYPES = {t: distinct_values(t, "event_type") for t in LOG_TABLES}

@lru_cache(maxsize=None)
def field_distinct(table: str, column: str) -> int:
    """列的不同取值数：用于剔除常量列（全 0 或单值），避免退化题面。"""
    out = executor.execute(SNAPSHOT, f"SELECT COUNT(DISTINCT {column}) AS n FROM {table}")
    assert not out["error"], f"探查失败 {table}.{column}: {out['error']}"
    return int(out["rows"][0][0] or 0)


MONEY_MEASURE_OPTIONS: dict[str, list[tuple[str, str]]] = {}
for _fact in FACT_TABLES:
    opts = []
    for (_t, _f), _mets in sorted(METRIC_BY_TF.items()):
        if _t == _fact and _f in MEASURE_FIELDS and field_distinct(_fact, _f) > 1:
            opts.append((_f, _mets[0]))
    if opts:
        MONEY_MEASURE_OPTIONS[_fact] = opts
MONEY_FACTS = [f for f in FACT_TABLES if f in MONEY_MEASURE_OPTIONS]
FACT_ORDER = seeds.shuffle(MONEY_FACTS, "tasks", "fact-order")
AGG_ORDER = seeds.shuffle(AGG_TABLES, "tasks", "agg-order")
LOG_ORDER = seeds.shuffle(LOG_TABLES, "tasks", "log-order")


def pick_measure(fact: str, salt: int) -> tuple[str, str, dict]:
    """选一个可累加的度量（单价这类平均值型度量只在描述统计题里出现）。"""
    opts = MONEY_MEASURE_OPTIONS[fact]
    sums = [o for o in opts if MEASURE_FIELDS[o[0]][3] == "sum"]
    pool = sums or opts
    field_name, metric = pool[salt % len(pool)]
    info = measure_info(fact, field_name, metric)
    return field_name, metric, info


def fact_caliber(fact: str, salt: int, mode: str = "default") -> tuple[list[str], list[str]]:
    """题目级口径过滤：剔除作废行（恒有）+ 人民币记账 + 可选状态码。"""
    rng = seeds.rng("tasks", f"caliber-{fact}-{salt}-{mode}")
    conds, zhs = [], ["剔除作废行"]
    if mode != "noccy" and rng.random() < 0.85:
        conds.append("f.currency_code = 'CNY'")
        zhs.append("人民币记账口径")
    if mode == "default" and rng.random() < 0.45:
        values = STATUS_VALUES[fact]
        status = values[salt % len(values)]
        conds.append(f"f.status_code = '{status}'")
        zhs.append(f"状态码 {status}")
    return conds, zhs


def _alias(prefix: str, field_name: str, agg: str) -> str:
    suffix = {"sum": "total", "avg": "avg", "weighted": "weighted"}[agg]
    return f"{prefix}_{field_name}_{suffix}" if prefix else f"{field_name}_{suffix}"


def _spec(family: str, difficulty: str, question: str, sql: str, tables: list[str],
          period: Period, refs: dict, metric_refs: list[str], claims,
          measure: str = "", measure_zh: str = "记录数", decimals: int = 0,
          kind: str = "count", unit: str = "", measure_agg: str = "sum",
          limit: int | None = None, caliber: str = "") -> Spec:
    return Spec(family=family, difficulty=difficulty, question=question, sql=sql,
                tables=list(tables), domain=TABLE_DOMAIN[tables[0]],
                measure=measure, measure_zh=measure_zh, decimals=decimals,
                kind=kind, unit=unit, period=period, caliber=caliber,
                metric_refs=list(metric_refs), refs=refs, claims=claims,
                measure_agg=measure_agg, limit=limit)


def agg_metric_expr(alias: str, field_name: str, info: dict) -> tuple[str, str]:
    """汇总表指标的聚合写法。

    比率型指标（指标值 / 指标比率）按样本量加权，避免把行级比率直接相加或平均；
    金额型与增量型指标按合计累加。返回 (SQL 表达式, 中文动词)。
    """
    d = info["decimals"]
    if info["kind"] == "ratio" and field_name in ("metric_value", "metric_ratio"):
        expr = (f"ROUND(SUM({alias}.{field_name} * {alias}.sample_size) "
                f"/ NULLIF(SUM({alias}.sample_size), 0), {d})")
        return expr, "加权平均值"
    return f"ROUND(SUM({alias}.{field_name}), {d})", "合计"


def dim_join_clauses(dims, fact_alias: str = "f", indent: str = "") -> str:
    out = []
    for dim in dims:
        s = DIM_SPECS[dim]
        out.append(f"{indent}JOIN {dim} {s['alias']} "
                   f"ON {fact_alias}.{s['key']} = {s['alias']}.{s.get('right', s['pk'])}")
    return "\n".join(out)


def dim_attr_expr(dim: str, attr: str) -> str:
    s = DIM_SPECS[dim]
    if attr == "month_label":
        return f"substr({s['alias']}.name, 1, 7)"
    return f"{s['alias']}.{attr}"


def dim_attr_zh(dim: str, attr: str) -> str:
    return DIM_SPECS[dim]["attrs"][attr]


# ================================================================ 单表题
def fam_a(i: int) -> Spec:
    """同表标量聚合：某月某度量的合计/平均值。"""
    fact = FACT_ORDER[i % len(FACT_ORDER)]
    period = PERIODS[(i * 3) % 4]
    field_name, metric, info = pick_measure(fact, i * 7 + 1)
    conds, zhs = fact_caliber(fact, i)
    func = "SUM" if info["agg"] == "sum" else "AVG"
    alias = _alias("", field_name, info["agg"])
    sql = (f"SELECT ROUND({func}(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"FROM {fact} f\n"
           f"WHERE {where_fact('f', period, conds)}")
    refs = make_refs(fact, field_name, metric)
    caliber = caliber_zh(zhs)
    word = "合计" if info["agg"] == "sum" else "平均值"
    question = (f"{period.range_zh()} 期间（{period.zh}），{NAME_ZH[fact]}的"
                f"{info['zh']}{word}是多少？统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]
    agg_verb = "SUM" if info["agg"] == "sum" else "AVG"

    def claims(ctx, n):
        v = ctx.cell(0, alias)
        out = [
            _claim(f"{period.range_zh()} 期间，{NAME_ZH[fact]}的{info['zh']}{word}为 "
                   f"{fmt_value(v, dec, kind, unit)}（{caliber}；按{dom_zh}域指标口径与"
                   f"{'指标卡计算式' if metric else '字段定义'}汇总）。",
                   refs["metric_calc"] if metric else refs["field_def"], domain_ref),
        ]
        if n >= 2:
            cnt = int(probe(f"SELECT COUNT(*) AS n {scope_where(fact, period, conds)}"))
            out.append(_claim(
                f"同口径明细共 {_int(cnt)} 笔记录，{info['zh']}{word}由这 {_int(cnt)} 笔"
                f"按 {agg_verb} 聚合得到。", refs["wp_rows"], refs["field_def"]))
        if n >= 3:
            full = probe(f"SELECT ROUND({func}(f.{field_name}), {info['decimals']}) AS m "
                         f"{scope_where(fact, FULL_PERIOD, conds)}")
            if info["agg"] == "sum" and full:
                text = (f"该区间{info['zh']}合计相当于 2024-01-01 至 2024-05-14 同口径"
                        f"全期合计（{fmt_value(full, dec, kind, unit)}）的 {_share(v, full)}。")
            elif full:
                text = (f"全期（2024-01-01 至 2024-05-14）同口径平均为 "
                        f"{fmt_value(full, dec, kind, unit)}，本区间平均与之相差 "
                        f"{_rel_diff(v, full)}。")
            else:
                text = (f"统计区间共 {_period_days(period)} 天，区间内按业务日期逐日归属后"
                        f"再聚合，不做跨天累计。")
            out.append(_claim(text, refs["metric_bound"], refs["wp_recon"]))
        if n >= 4:
            cnt_c = int(probe(f"SELECT COUNT(DISTINCT f.customer_key) AS c "
                              f"{scope_where(fact, period, conds)}"))
            out.append(_claim(
                f"该区间涉及 {_int(cnt_c)} 个不同客户（按 customer_key 对应客户维主键去重），"
                f"客户粒度与明细行粒度不同。", refs["customer_field"], refs["wp_rows"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：按业务发生日期归属，{caliber}，区间外的行不计入；"
                f"{'金额' if kind == 'money' else '数量'}保留 {dec} 位小数。",
                refs["wp_caliber"], refs["metric_bound"]))
        return out[:n]

    return _spec("A", "single_table", question, sql, [fact], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, measure_agg=info["agg"], caliber=caliber)


def fam_b(i: int) -> Spec:
    """同表标量计数：记录数 / 去重客户数 / 有业务的日期数。"""
    fact = FACT_ORDER[(i * 3 + 2) % len(FACT_ORDER)]
    period = PERIODS[(i * 2) % 4]
    mode = i % 3
    pk = TABLE_FIELDS[fact][0]
    conds, zhs = fact_caliber(fact, i + 40, mode="default" if mode else "noccy")
    refs = make_refs(fact, pk, None)
    caliber = caliber_zh(zhs)
    where = where_fact("f", period, conds)
    if mode == 0:
        alias, what = "row_count", "有效记录数"
        sql = f"SELECT COUNT(*) AS {alias}\nFROM {fact} f\nWHERE {where}"
        question = (f"{period.range_zh()} 期间（{period.zh}），{NAME_ZH[fact]}中符合口径"
                    f"（{caliber}）的记录有多少笔？")
    elif mode == 1:
        alias, what = "customer_cnt", "去重客户数"
        sql = (f"SELECT COUNT(DISTINCT f.customer_key) AS {alias}\n"
               f"FROM {fact} f\nWHERE {where}")
        question = (f"{period.range_zh()} 期间（{period.zh}），{NAME_ZH[fact]}涉及的"
                    f"不同客户有多少个（去重，{caliber}）？")
    else:
        alias, what = "active_day_cnt", "有业务的业务日期数"
        sql = (f"SELECT COUNT(DISTINCT f.date_key) AS {alias}\n"
               f"FROM {fact} f\nWHERE {where}")
        question = (f"{period.range_zh()} 期间（{period.zh}），{NAME_ZH[fact]}有业务发生的"
                    f"业务日期共有多少天（按业务日期去重，{caliber}）？")

    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]
    unit_zh = "天" if mode == 2 else "笔"
    days = _period_days(period)
    value_ref = {0: refs["wp_rows"], 1: refs["customer_field"], 2: refs["wp_grain"]}[mode]

    def claims(ctx, n):
        v = ctx.cell(0, alias)
        out = [
            _claim(f"{period.range_zh()} 期间，{NAME_ZH[fact]}的{what}为 {_int(v)} {unit_zh}"
                   f"（{caliber}；按{dom_zh}域口径统计）。", value_ref, domain_ref),
        ]
        if n >= 2:
            if mode == 2:
                text = (f"统计区间共 {days} 天，有业务发生的日期占 {_share(v, days)}，"
                        f"其余日期无有效记录。")
                refs2 = (refs["wp_rows"], refs["field_def"])
            else:
                text = (f"统计区间共 {days} 天，折合日均 {int(v) / days:.2f} 笔/天；"
                        f"计数按业务日期逐日归属后汇总。")
                refs2 = (refs["wp_caliber"], refs["field_def"])
            out.append(_claim(text, *refs2))
        if n >= 3:
            full = int(probe(f"SELECT COUNT(*) AS n FROM {fact} f "
                             f"WHERE {where_fact('f', FULL_PERIOD, conds)}"))
            out.append(_claim(
                f"2024-01-01 至 2024-05-14 同口径全期为 {_int(full)} {unit_zh}，"
                f"本区间占其 {_share(v, full)}。", refs["wp_trap"], refs["wp_recon"]))
        if n >= 4:
            if mode == 1:
                aux_col, aux_what, aux_unit = "date_key", "有业务的业务日期", "天"
                aux_refs = (refs["wp_rows"], refs["wp_grain"])
            else:
                aux_col, aux_what, aux_unit = "customer_key", "涉及的客户", "个"
                aux_refs = (refs["customer_field"], refs["wp_rows"])
            aux_cnt = int(probe(f"SELECT COUNT(DISTINCT f.{aux_col}) AS c "
                                f"FROM {fact} f WHERE {where}"))
            out.append(_claim(
                f"同一区间内{aux_what}共 {_int(aux_cnt)} {aux_unit}"
                f"（按 {aux_col} 对应主键去重），与{what}使用的是同一份口径过滤。", *aux_refs))
        if n >= 5:
            out.append(_claim(
                f"口径说明：按业务发生日期与主键去重后统计，{caliber}；"
                f"区间外的记录不参与计数。", refs["wp_caliber"], refs["wp_usage"]))
        return out[:n]

    return _spec("B", "single_table", question, sql, [fact], period, refs, [],
                 claims, measure=pk, measure_zh=what, decimals=0, kind="count",
                 unit="笔", caliber=caliber)


def fam_c(i: int) -> Spec:
    """同表分组：按状态码 / 记账币种 / 业务月份分组汇总。"""
    fact = FACT_ORDER[(i * 5 + 1) % len(FACT_ORDER)]
    period = PERIODS[(i * 2 + 1) % 4]
    field_name, metric, info = pick_measure(fact, i * 3 + 2)
    variant = i % 3
    if variant == 0:
        group_expr, group, attr_zh = "f.status_code", "status_code", "状态码"
        conds, zhs = fact_caliber(fact, i + 60, mode="noccy")
    elif variant == 1:
        group_expr, group, attr_zh = "f.currency_code", "currency_code", "记账币种"
        conds, zhs = fact_caliber(fact, i + 60, mode="noccy")
        zhs = ["剔除作废行", "不做跨币种折算"]
    else:
        period = PERIODS[4 + (i % 3)]
        group_expr = "substr(CAST(f.date_key AS TEXT), 1, 6)"
        group, attr_zh = "month_key", "业务月份（业务日期键前 6 位）"
        conds, zhs = fact_caliber(fact, i + 60, mode="noccy")
    alias = _alias("", field_name, info["agg"])
    sql = (f"SELECT {group_expr} AS {group},\n"
           f"       COUNT(*) AS row_count,\n"
           f"       ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"FROM {fact} f\n"
           f"WHERE {where_fact('f', period, conds)}\n"
           f"GROUP BY {group_expr}\n"
           f"ORDER BY {alias} DESC")
    refs = make_refs(fact, field_name, metric)
    caliber = caliber_zh(zhs)
    question = (f"{period.range_zh()} 期间（{period.zh}），按{attr_zh}分组统计{NAME_ZH[fact]}的"
                f"{info['zh']}合计与记录数，并按{info['zh']}从高到低排列。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top, low = ctx.rows[0], ctx.rows[-1]
        total = sum(ctx.col(alias))
        total_cnt = sum(ctx.col("row_count"))
        top_v = top[ctx.pos[alias]]
        low_v = low[ctx.pos[alias]]
        out = [
            _claim(f"{period.range_zh()} 期间，按{attr_zh}分组后 {top[0]} 的{info['zh']}"
                   f"最高，为 {fmt_value(top_v, dec, kind, unit)}（{caliber}；"
                   f"按{dom_zh}域指标口径分组汇总）。", refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"参与汇总的 {ctx.n} 个{attr_zh}分组合计{info['zh']} "
                f"{fmt_value(total, dec, kind, unit)}，记录 {_int(total_cnt)} 笔。",
                refs["wp_recon"], refs["field_trap"]))
        if n >= 3:
            out.append(_claim(
                f"最低分组为 {low[0]}，{info['zh']} {fmt_value(low_v, dec, kind, unit)}；"
                f"最高与最低相差 {fmt_value(float(top_v) - float(low_v), dec, kind, unit)}。",
                refs["metric_calc"], refs["wp_caliber"]))
        if n >= 4:
            out.append(_claim(
                f"最高分组 {top[0]} 占全部{info['zh']}的 {_share(top_v, total)}，"
                f"其余 {max(ctx.n - 1, 0)} 个分组分摊剩余部分。",
                refs["metric_bound"], refs["wp_rows"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：按{attr_zh}分组后对{info['zh']}做 SUM 汇总，{caliber}；"
                f"不把行级取值直接相加之外的统计量混入。",
                refs["wp_caliber"], refs["wp_usage"]))
        return out[:n]

    return _spec("C", "single_table", question, sql, [fact], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)


def fam_d(i: int) -> Spec:
    """同表比率：两列聚合后相除，保留 4 位小数。"""
    fact = FACT_ORDER[(i * 4 + 3) % len(FACT_ORDER)]
    period = PERIODS[i % 4]
    pairs = [("discount_amount", "gross_amount"), ("net_amount", "amount"),
             ("cost_amount", "gross_amount"), ("tax_amount", "gross_amount")]
    num, den = pairs[i % len(pairs)]
    num_zh, den_zh = MEASURE_FIELDS[num][0], MEASURE_FIELDS[den][0]
    metric = (METRIC_BY_TF.get((fact, num)) or METRIC_BY_TF.get((fact, den)) or [None])[0]
    conds, zhs = fact_caliber(fact, i + 80)
    alias = f"{num}_to_{den}_ratio"
    sql = (f"SELECT ROUND(SUM(f.{num}) / NULLIF(SUM(f.{den}), 0), 4) AS {alias}\n"
           f"FROM {fact} f\nWHERE {where_fact('f', period, conds)}")
    refs = make_refs(fact, num, metric)
    refs["num_field"] = (field_doc(fact, num), 1)
    refs["den_field"] = (field_doc(fact, den), 1)
    for _key in ("num_field", "den_field"):
        _doc, _no = refs[_key]
        assert f"{_doc}#p{_no:02d}" in DOC_CHUNKS[_doc], f"证据块不存在：{_doc}#p{_no:02d}"
    caliber = caliber_zh(zhs)
    question = (f"{period.range_zh()} 期间（{period.zh}），{NAME_ZH[fact]}的{num_zh}占"
                f"{den_zh}的比率是多少？比率保留 4 位小数，统计口径：{caliber}。")
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]
    num_dec = MEASURE_FIELDS[num][1]
    den_dec = MEASURE_FIELDS[den][1]

    def pair_sums(period_) -> list:
        return probe_row(
            f"SELECT ROUND(SUM(f.{num}), {num_dec}) AS num_sum, "
            f"ROUND(SUM(f.{den}), {den_dec}) AS den_sum "
            f"{scope_where(fact, period_, conds)}")

    def claims(ctx, n):
        v = ctx.cell(0, alias)
        out = [
            _claim(f"{period.range_zh()} 期间，{NAME_ZH[fact]}的{num_zh}占{den_zh}的比率为 "
                   f"{_num(v, 4)}（{caliber}；按{dom_zh}域口径回到分子分母重算）。",
                   refs["metric_bound"], domain_ref),
        ]
        nums = pair_sums(period)
        if n >= 2 and nums:
            out.append(_claim(
                f"分子{num_zh}在区间内合计 {_num(nums[0], num_dec)} 元。",
                refs["metric_calc"], refs["num_field"]))
        if n >= 3 and nums:
            out.append(_claim(
                f"分母{den_zh}在区间内合计 {_num(nums[1], den_dec)} 元，比率正是由这两个"
                f"汇总值相除得到。", refs["den_field"], refs["wp_grain"]))
        if n >= 4:
            cnt = int(probe(f"SELECT COUNT(*) AS n {scope_where(fact, period, conds)}"))
            out.append(_claim(
                f"同口径明细共 {_int(cnt)} 笔参与计算，分子分母由同一批行分别汇总。",
                refs["wp_rows"], refs["wp_usage"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：分子分母分别按{caliber}汇总后再相除，不对行级比率取平均；"
                f"比率保留 4 位小数。", refs["wp_caliber"], refs["metric_calc"]))
        return out[:n]

    return _spec("D", "single_table", question, sql, [fact], period, refs,
                 [metric] if metric else [], claims, measure=num, measure_zh=num_zh,
                 decimals=4, kind="ratio", unit="", caliber=caliber)


def fam_e(i: int) -> Spec:
    """同表描述统计：平均值 / 最大值 / 最小值（1 行 3 列）。"""
    fact = FACT_ORDER[(i * 6 + 4) % len(FACT_ORDER)]
    field_name, metric, info = pick_measure(fact, i + 5)
    period = PERIODS[(i * 3 + 2) % 4]
    conds, zhs = fact_caliber(fact, i + 100)
    d = info["decimals"]
    a_avg, a_max, a_min = (f"{field_name}_avg", f"{field_name}_max", f"{field_name}_min")
    sql = (f"SELECT ROUND(AVG(f.{field_name}), {d}) AS {a_avg},\n"
           f"       ROUND(MAX(f.{field_name}), {d}) AS {a_max},\n"
           f"       ROUND(MIN(f.{field_name}), {d}) AS {a_min}\n"
           f"FROM {fact} f\nWHERE {where_fact('f', period, conds)}")
    refs = make_refs(fact, field_name, metric)
    caliber = caliber_zh(zhs)
    question = (f"{period.range_zh()} 期间（{period.zh}），{NAME_ZH[fact]}的{info['zh']}"
                f"平均值、最大值与最小值分别是多少？统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        avg, mx, mn = ctx.cell(0, a_avg), ctx.cell(0, a_max), ctx.cell(0, a_min)
        out = [
            _claim(f"{period.range_zh()} 期间，{NAME_ZH[fact]}的{info['zh']}平均值为 "
                   f"{fmt_value(avg, dec, kind, unit)}（{caliber}；按{dom_zh}域口径做描述统计）。",
                   refs["metric_def"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"同一区间内的最大值为 {fmt_value(mx, dec, kind, unit)}，取自行级明细。",
                refs["field_def"], refs["metric_calc"]))
        if n >= 3:
            out.append(_claim(
                f"同一区间内的最小值为 {fmt_value(mn, dec, kind, unit)}。",
                refs["wp_grain"], refs["metric_bound"]))
        if n >= 4:
            out.append(_claim(
                f"最大值与最小值相差 {fmt_value(float(mx) - float(mn), dec, kind, unit)}，"
                f"分布跨度按同一口径与同一批行计算。", refs["metric_bound"], refs["wp_recon"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：平均值、最大值、最小值都由{caliber}下的同一批明细行直接计算，"
                f"未做任何平滑或截尾。", refs["wp_caliber"], refs["field_trap"]))
        return out[:n]

    return _spec("E", "single_table", question, sql, [fact], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, measure_agg="avg", caliber=caliber)


AGG_RATIO_TABLES = [t for t in AGG_ORDER if (t, "metric_ratio") in METRIC_BY_TF]
AGG_VALUE_TABLES = [t for t in AGG_ORDER if (t, "metric_value") in METRIC_BY_TF]


def fam_f(i: int) -> Spec:
    """汇总表自带口径：加权比率、指标值合计、比率极差、按是否部分周期分组。"""
    mode = i % 4
    if mode in (0, 2):
        assert AGG_RATIO_TABLES, "无可用比率型汇总表"
        table = AGG_RATIO_TABLES[(i // 4) * 2 + (0 if mode == 0 else 1)]
        metric = METRIC_BY_TF[(table, "metric_ratio")][0]
    else:
        assert AGG_VALUE_TABLES, "无可用指标值型汇总表"
        table = AGG_VALUE_TABLES[(i // 4) * 2 + (0 if mode == 1 else 1)]
        metric = METRIC_BY_TF[(table, "metric_value")][0]
    period = PERIODS[i % 4]
    refs = make_refs(table, "metric_ratio" if mode in (0, 2) else "metric_value", metric)
    zh = NAME_ZH[table]
    label = METRIC_META[metric]["label"]
    where = where_agg("a", period)

    if mode == 0:
        alias = "metric_ratio_weighted"
        sql = (f"SELECT ROUND(SUM(a.metric_ratio * a.sample_size) "
               f"/ NULLIF(SUM(a.sample_size), 0), 4) AS {alias}\n"
               f"FROM {table} a\nWHERE {where}")
        question = (f"{period.range_zh()} 期间（{period.zh}），{zh}的「{label}」按样本量加权"
                    f"后的取值是多少？加权口径为 SUM(比率×样本量)/SUM(样本量)，保留 4 位小数。")
        caliber = "按汇总行样本量加权"
        dom_zh = DOMAIN_ZH[TABLE_DOMAIN[table]]
        domain_ref = DOMAIN_REF[TABLE_DOMAIN[table]]

        def claims(ctx, n):
            v = ctx.cell(0, alias)
            out = [
                _claim(f"{period.range_zh()} 期间，{zh}的「{label}」加权比率为 {_num(v, 4)}"
                       f"（按{dom_zh}域口径回到分子分母重算）。",
                       refs["metric_calc"], domain_ref),
            ]
            stats = probe_row(
                f"SELECT ROUND(SUM(a.sample_size), 2) AS s, COUNT(*) AS n, "
                f"ROUND(MAX(a.metric_ratio) - MIN(a.metric_ratio), 4) AS spread "
                f"FROM {table} a WHERE {where}")
            if n >= 2 and stats:
                out.append(_claim(
                    f"参与加权的样本量合计为 {_num(stats[0], 2)}，权重来自汇总行自带的"
                    f" sample_size 字段。", refs["metric_def"], refs["field_def"]))
            if n >= 3 and stats:
                out.append(_claim(
                    f"该区间共有 {_int(stats[1])} 个汇总行参与加权，按 date_key 裁剪后聚合。",
                    refs["wp_grain"], refs["wp_rows"]))
            if n >= 4 and stats:
                out.append(_claim(
                    f"同期各汇总行「{label}」的极差为 {_num(stats[2], 4)}（最大值减最小值），"
                    f"行间离散度不等于加权结果本身。", refs["metric_bound"], refs["wp_recon"]))
            if n >= 5:
                out.append(_claim(
                    "口径说明：加权口径为 SUM(比率×样本量)/SUM(样本量)，"
                    "分子分母分别汇总后再相除，不对行级比率取平均。",
                    refs["metric_calc"], refs["wp_caliber"]))
            return out[:n]

        return _spec("F", "single_table", question, sql, [table], period, refs, [metric],
                     claims, measure="metric_ratio", measure_zh="指标比率",
                     decimals=4, kind="ratio", unit="", caliber=caliber)

    if mode == 1:
        info = measure_info(table, "metric_value", metric)
        expr, word = agg_metric_expr("a", "metric_value", info)
        alias = f"metric_value_{'weighted' if word == '加权平均值' else 'total'}"
        sql = (f"SELECT {expr} AS {alias},\n"
               f"       ROUND(SUM(a.sample_size), 2) AS sample_size_total,\n"
               f"       COUNT(*) AS row_count\n"
               f"FROM {table} a\nWHERE {where}")
        question = (f"{period.range_zh()} 期间（{period.zh}），{zh}的「{label}」{word}、"
                    f"样本量合计与汇总行数分别是多少？")
        caliber = "按汇总行直接相加，不跨版本混算"
        dec, kind, unit = info["decimals"], info["kind"], info["unit"]
        dom_zh = DOMAIN_ZH[TABLE_DOMAIN[table]]
        domain_ref = DOMAIN_REF[TABLE_DOMAIN[table]]

        def claims(ctx, n):
            total = ctx.cell(0, alias)
            sample = ctx.cell(0, "sample_size_total")
            cnt = ctx.cell(0, "row_count")
            out = [
                _claim(f"{period.range_zh()} 期间，{zh}的「{label}」{word}为 "
                       f"{fmt_value(total, dec, kind, unit)}（按{dom_zh}域指标口径汇总）。",
                       refs["metric_def"], domain_ref),
            ]
            if n >= 2:
                out.append(_claim(
                    f"对应样本量合计 {_num(sample, 2)}，覆盖 {_int(cnt)} 个汇总行。",
                    refs["metric_calc"], refs["field_def"]))
            if n >= 3:
                out.append(_claim(
                    f"该区间共 {_int(cnt)} 个汇总行参与计算，行数按 date_key 裁剪后计数。",
                    refs["wp_grain"], refs["wp_rows"]))
            if n >= 4:
                out.append(_claim(
                    f"口径说明：{caliber}；{word}由区间内全部汇总行直接汇总得到。",
                    refs["metric_bound"], refs["wp_caliber"]))
            if n >= 5:
                out.append(_claim(
                    "指标卡口径：样本量不足 30 行时只标注、不对外发布；跨版本不可直接相减。",
                    refs["metric_bound"], refs["metric_def"]))
            return out[:n]

        return _spec("F", "single_table", question, sql, [table], period, refs, [metric],
                     claims, measure="metric_value", measure_zh=info["zh"], decimals=dec,
                     kind=kind, unit=unit, caliber=caliber)

    if mode == 2:
        alias = "metric_ratio_spread"
        sql = (f"SELECT ROUND(MAX(a.metric_ratio) - MIN(a.metric_ratio), 4) AS {alias}\n"
               f"FROM {table} a\nWHERE {where}")
        question = (f"{period.range_zh()} 期间（{period.zh}），{zh}的「{label}」在汇总行之间的"
                    f"极差（最大值减最小值）是多少？保留 4 位小数。")
        caliber = "极差按汇总行取最大最小，不做跨版本相减"
        dom_zh = DOMAIN_ZH[TABLE_DOMAIN[table]]
        domain_ref = DOMAIN_REF[TABLE_DOMAIN[table]]

        def claims(ctx, n):
            v = ctx.cell(0, alias)
            out = [
                _claim(f"{period.range_zh()} 期间，{zh}的「{label}」在汇总行之间的极差为 "
                       f"{_num(v, 4)}（最大值减最小值；按{dom_zh}域口径同期比较）。",
                       refs["metric_def"], domain_ref),
            ]
            stats = probe_row(
                f"SELECT ROUND(MAX(a.metric_ratio), 4) AS mx, "
                f"ROUND(MIN(a.metric_ratio), 4) AS mn, COUNT(*) AS n "
                f"FROM {table} a WHERE {where}")
            if n >= 2 and stats:
                out.append(_claim(
                    f"同期「{label}」的最大值为 {_num(stats[0], 4)}，取自分组汇总行。",
                    refs["metric_bound"], refs["field_def"]))
            if n >= 3 and stats:
                out.append(_claim(
                    f"同期「{label}」的最小值为 {_num(stats[1], 4)}，与最大值相差即上述极差。",
                    refs["metric_bound"], refs["wp_recon"]))
            if n >= 4 and stats:
                out.append(_claim(
                    f"该区间共有 {_int(stats[2])} 个汇总行参与比较，极差只反映同期行间差异。",
                    refs["wp_rows"], refs["wp_grain"]))
            if n >= 5:
                out.append(_claim(
                    "口径说明：比率不可跨周期直接相减，本结果只比较同 period 内的汇总行，"
                    "不做版本间拼接。", refs["metric_calc"], refs["wp_caliber"]))
            return out[:n]

        return _spec("F", "single_table", question, sql, [table], period, refs, [metric],
                     claims, measure="metric_ratio", measure_zh="指标比率",
                     decimals=4, kind="ratio", unit="", caliber=caliber)

    period = PERIODS[8]
    where = where_agg("a", period)
    info = measure_info(table, "metric_value", metric)
    expr, word = agg_metric_expr("a", "metric_value", info)
    alias = f"metric_value_{'weighted' if word == '加权平均值' else 'total'}"
    sql = (f"SELECT a.is_partial AS is_partial,\n"
           f"       COUNT(*) AS row_count,\n"
           f"       {expr} AS {alias}\n"
           f"FROM {table} a\nWHERE {where}\n"
           f"GROUP BY a.is_partial\nORDER BY {alias} DESC")
    question = (f"{period.range_zh()} 期间（{period.zh}），按是否部分周期分组统计{zh}的"
                f"「{label}」{word}与汇总行数，并按{word}从高到低排列。")
    caliber = "按 is_partial 标记分组"
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[table]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[table]]

    def claims(ctx, n):
        top = ctx.rows[0]
        low = ctx.rows[-1]
        out = [
            _claim(f"{period.range_zh()} 期间，{zh}中 is_partial={top[0]} 的分组「{label}」"
                   f"{word}最高，为 {fmt_value(top[ctx.pos[alias]], dec, kind, unit)}"
                   f"（按{dom_zh}域口径汇总）。", refs["metric_def"], domain_ref),
        ]
        if n >= 2:
            rows_zh = "、".join(f"is_partial={r[0]} 有 {_int(r[ctx.pos['row_count']])} 行"
                               for r in ctx.rows)
            out.append(_claim(f"该区间共 {ctx.n} 个 is_partial 分组：{rows_zh}。",
                              refs["wp_rows"], refs["field_def"]))
        if n >= 3:
            out.append(_claim(
                f"另一分组 is_partial={low[0]} 的「{label}」{word}为 "
                f"{fmt_value(low[ctx.pos[alias]], dec, kind, unit)}。",
                refs["metric_calc"], refs["metric_bound"]))
        if n >= 4:
            diff = float(top[ctx.pos[alias]]) - float(low[ctx.pos[alias]])
            out.append(_claim(
                f"两个分组之间的「{label}」{word}相差 "
                f"{fmt_value(diff, dec, kind, unit)}，部分周期行不可与完整周期行混比。",
                refs["wp_grain"], refs["field_trap"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：{caliber}；部分周期行只标注、不与完整周期行同比，"
                f"跨版本不可直接相减。", refs["wp_caliber"], refs["metric_bound"]))
        return out[:n]

    return _spec("F", "single_table", question, sql, [table], period, refs, [metric],
                 claims, measure="metric_value", measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)


def fam_g(i: int) -> Spec:
    """日志表（受限域）：按事件类型 / 执行状态统计调用次数与耗时。"""
    table = LOG_ORDER[i]
    period = PERIODS[(i * 2 + 1) % 4]
    mode = i % 2
    refs = make_refs(table, "duration_ms" if mode == 0 else "payload_size", None)
    zh = NAME_ZH[table]
    where = f"f.date_key BETWEEN {period.start} AND {period.end}"
    if mode == 0:
        group, attr_zh, alias = "f.event_type", "事件类型", "duration_ms_avg"
        sql = (f"SELECT {group} AS event_type,\n"
               f"       COUNT(*) AS row_count,\n"
               f"       ROUND(AVG(f.duration_ms), 2) AS {alias}\n"
               f"FROM {table} f\nWHERE {where}\n"
               f"GROUP BY {group}\nORDER BY row_count DESC")
        measure, info = "duration_ms", MEASURE_FIELDS["duration_ms"]
        question = (f"{period.range_zh()} 期间（{period.zh}），{zh}按{attr_zh}统计调用次数与"
                    f"平均耗时（毫秒），并按调用次数从高到低排列。")
    else:
        group, attr_zh, alias = "f.status", "执行状态", "payload_size_total"
        sql = (f"SELECT {group} AS status,\n"
               f"       COUNT(*) AS row_count,\n"
               f"       ROUND(SUM(f.payload_size), 2) AS {alias}\n"
               f"FROM {table} f\nWHERE {where}\n"
               f"GROUP BY {group}\nORDER BY row_count DESC")
        measure, info = "payload_size", MEASURE_FIELDS["payload_size"]
        question = (f"{period.range_zh()} 期间（{period.zh}），{zh}按{attr_zh}统计调用次数与"
                    f"载荷大小合计，并按调用次数从高到低排列。")
    caliber = "按日志日期分区统计"
    dec, kind, unit = info[1], info[2], info[4]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[table]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[table]]
    agg_word = "平均值" if info[3] == "avg" else "合计"

    def claims(ctx, n):
        top = ctx.rows[0]
        total_cnt = sum(ctx.col("row_count"))
        out = [
            _claim(f"{period.range_zh()} 期间，{zh}中 {top[0]} 的调用次数最多，为 "
                   f"{_int(top[ctx.pos['row_count']])} 次，对应{info[0]}{agg_word} "
                   f"{fmt_value(top[ctx.pos[alias]], dec, kind, unit)}"
                   f"（按{dom_zh}域日志口径统计）。", refs["wp_rows"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"该区间共 {_int(total_cnt)} 次调用，覆盖 {ctx.n} 个{attr_zh}分组。",
                refs["wp_usage"], refs["field_def"]))
        if n >= 3:
            out.append(_claim(
                f"{attr_zh}分组共 {ctx.n} 个，调用次数最多的分组占比为 "
                f"{_share(top[ctx.pos['row_count']], total_cnt)}。",
                refs["field_def"], refs["wp_grain"]))
        if n >= 4:
            if info[3] == "avg":
                weighted = sum(float(r[ctx.pos["row_count"]]) * float(r[ctx.pos[alias]])
                               for r in ctx.rows) / max(total_cnt, 1)
                out.append(_claim(
                    f"按调用次数加权后，全区间{info[0]}的平均值为 "
                    f"{fmt_value(weighted, dec, kind, unit)}，与各分组算术平均不同。",
                    refs["wp_recon"], refs["wp_usage"]))
            else:
                total_payload = sum(ctx.col(alias))
                out.append(_claim(
                    f"各分组{info[0]}合计 {fmt_value(total_payload, dec, kind, unit)}。",
                    refs["wp_recon"], refs["wp_usage"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：{caliber}，按 date_key 分区裁剪，{caliber}；"
                f"日志表为受限数据，结果只保留聚合值。",
                refs["wp_caliber"], refs["wp_usage"]))
        return out[:n]

    return _spec("G", "single_table", question, sql, [table], period, refs, [],
                 claims, measure=measure, measure_zh=info[0], decimals=dec,
                 kind=kind, unit=unit, measure_agg=info[3], caliber=caliber)


# ================================================================ join 题
H_DIMS = [("dim_customer", "region_code"), ("dim_store", "region_code"),
          ("dim_channel", "channel_code"), ("dim_product", "status")]


def fam_h(i: int) -> Spec:
    """事实表 ⨝ 维表：按维表属性分组的度量汇总。"""
    fact = FACT_ORDER[i // 4]
    dim, attr = H_DIMS[i % 4]
    period = PERIODS[(i * 3 + 1) % 4]
    field_name, metric, info = pick_measure(fact, i * 2 + 3)
    conds, zhs = fact_caliber(fact, i + 200)
    expr = dim_attr_expr(dim, attr)
    alias = _alias("", field_name, info["agg"])
    sql = (f"SELECT {expr} AS {attr},\n"
           f"       COUNT(*) AS row_count,\n"
           f"       ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"FROM {fact} f\n"
           f"{dim_join_clauses([dim])}\n"
           f"WHERE {where_fact('f', period, conds)}\n"
           f"GROUP BY {expr}\n"
           f"ORDER BY {alias} DESC")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH[dim]}后按{a_zh}分组，"
                f"统计{NAME_ZH[fact]}的{info['zh']}合计与记录数，并按{info['zh']}从高到低排列。"
                f"统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top, low = ctx.rows[0], ctx.rows[-1]
        total = sum(ctx.col(alias))
        total_cnt = sum(ctx.col("row_count"))
        top_v = top[ctx.pos[alias]]
        out = [
            _claim(f"{period.range_zh()} 期间，按{a_zh}分组后 {top[0]} 的{info['zh']}最高，为 "
                   f"{fmt_value(top_v, dec, kind, unit)}（{caliber}；按{dom_zh}域指标口径"
                   f"关联{NAME_ZH[dim]}后分组）。", refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"{ctx.n} 个{a_zh}分组合计{info['zh']} {fmt_value(total, dec, kind, unit)}，"
                f"对应明细 {_int(total_cnt)} 笔。", refs["wp_grain"], refs["field_trap"]))
        if n >= 3:
            out.append(_claim(
                f"最低分组为 {low[0]}，{info['zh']}为 "
                f"{fmt_value(low[ctx.pos[alias]], dec, kind, unit)}。",
                refs["wp_join"], refs[f"{dim}_field"]))
        if n >= 4:
            out.append(_claim(
                f"最高分组 {top[0]} 占全部{info['zh']}的 {_share(top_v, total)}，"
                f"分组占比之和为 1。", refs["metric_bound"], refs["wp_join"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：以{NAME_ZH[dim]}主键与事实表外键关联后分组，"
                f"{a_zh}取自维表属性；一对一关联未放大明细行数。",
                refs[f"{dim}_keys"], refs["wp_join_risk"]))
        return out[:n]

    return _spec("H", "join", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)


I_COMBOS = [
    (7, "dim_customer", "region_code"),
    (7, "dim_store", "region_code"),
    (4, "dim_product", "status"),
    (5, "dim_product", "status"),
    (6, "dim_customer", "status"),
    (4, "dim_store", "status"),
    (5, "dim_channel", "status"),
    (6, "dim_store", "status"),
    (4, "dim_date", "category"),
    (6, "dim_date", "category"),
]


def fam_i(i: int) -> Spec:
    """日期维 ⨝ 业务维：按月份 × 维表属性的双维汇总。"""
    period_idx, dim, attr = I_COMBOS[i]
    period = PERIODS[period_idx]
    fact = FACT_ORDER[(i * 3 + 5) % len(FACT_ORDER)]
    field_name, metric, info = pick_measure(fact, i * 5 + 1)
    conds, zhs = fact_caliber(fact, i + 240)
    expr = dim_attr_expr(dim, attr)
    alias = _alias("", field_name, info["agg"])
    extra = "" if dim == "dim_date" else dim_join_clauses([dim]) + "\n"
    sql = (f"SELECT substr(d.name, 1, 7) AS month_label,\n"
           f"       {expr} AS {attr},\n"
           f"       ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"FROM {fact} f\n"
           f"JOIN dim_date d ON f.date_key = d.date_key\n"
           f"{extra}"
           f"WHERE {where_fact('f', period, conds)}\n"
           f"GROUP BY substr(d.name, 1, 7), {expr}\n"
           f"ORDER BY month_label, {alias} DESC")
    refs = make_refs(fact, field_name, metric, dims=("dim_date", dim))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    join_zh = (f"关联{NAME_ZH['dim_date']}" if dim == "dim_date"
               else f"关联{NAME_ZH['dim_date']}与{NAME_ZH[dim]}")
    question = (f"{period.range_zh()} 期间（{period.zh}），{join_zh}，"
                f"按月份与{a_zh}统计{NAME_ZH[fact]}的{info['zh']}合计，"
                f"先按月份、再按{info['zh']}降序排列。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top, low = ctx.rows[0], ctx.rows[-1]
        months = sorted({r[ctx.pos["month_label"]] for r in ctx.rows})
        total = sum(ctx.col(alias))
        out = [
            _claim(f"{months[0]} 至 {months[-1]} 共 {len(months)} 个月份中，"
                   f"{top[ctx.pos['month_label']]} 的 {top[ctx.pos[attr]]} 分组{info['zh']}最高，"
                   f"为 {fmt_value(top[ctx.pos[alias]], dec, kind, unit)}（{caliber}；"
                   f"按{dom_zh}域指标口径关联日期维后汇总）。", refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"结果覆盖 {ctx.n} 个「月份×{a_zh}」组合，月份取自{NAME_ZH['dim_date']}的"
                f" name 属性前 7 位。", refs["dim_date_join"], refs[f"{dim}_field"]))
        if n >= 3:
            out.append(_claim(
                f"全部组合的{info['zh']}合计为 {fmt_value(total, dec, kind, unit)}，"
                f"与不分月的同口径汇总一致。", refs["metric_bound"], refs["field_def"]))
        if n >= 4:
            out.append(_claim(
                f"最低组合为 {low[ctx.pos['month_label']]} 的 {low[ctx.pos[attr]]}，"
                f"{info['zh']} {fmt_value(low[ctx.pos[alias]], dec, kind, unit)}。",
                refs["wp_recon"], refs["field_trap"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：月份由{NAME_ZH['dim_date']}的日期名截取，{caliber}；"
                f"月份与{a_zh}双维分组后不再回写明细。", refs["wp_caliber"], refs["wp_join"]))
        return out[:n]

    return _spec("I", "join", question, sql, [fact, "dim_date", dim], period, refs,
                 [metric], claims, measure=field_name, measure_zh=info["zh"],
                 decimals=dec, kind=kind, unit=unit, caliber=caliber)


J_COMBOS = ([("dim_customer", "region_code", k) for k in range(5)] +
            [("dim_channel", "channel_code", k) for k in range(4)] +
            [("dim_store", "region_code", k) for k in range(3)])


def fam_j(i: int) -> Spec:
    """事实表 ⨝ 维表 + 维表属性过滤：标量汇总。"""
    dim, attr, k = J_COMBOS[i]
    values = distinct_values(dim, attr)
    value = values[k % len(values)]
    fact = FACT_ORDER[(i * 4 + 2) % len(FACT_ORDER)]
    period = PERIODS[(i * 3 + 2) % 4]
    field_name, metric, info = pick_measure(fact, i * 3 + 7)
    conds, zhs = fact_caliber(fact, i + 280, mode="nostatus")
    s = DIM_SPECS[dim]
    alias = _alias("", field_name, info["agg"])
    sql = (f"SELECT ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"FROM {fact} f\n"
           f"{dim_join_clauses([dim])}\n"
           f"WHERE {where_fact('f', period, conds)}\n"
           f"  AND {s['alias']}.{attr} = '{value}'")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），{a_zh}为 {value} 的"
                f"{NAME_ZH[dim]}对应的{NAME_ZH[fact]}，其{info['zh']}合计是多少？"
                f"统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]
    join_sql = dim_join_clauses([dim])
    filter_sql = f"{s['alias']}.{attr} = '{value}'"

    def scope(period_) -> str:
        return scope_where(fact, period_, conds, joins=join_sql + "\n", extra=filter_sql)

    def claims(ctx, n):
        v = ctx.cell(0, alias)
        out = [
            _claim(f"{period.range_zh()} 期间，{a_zh}为 {value} 的{NAME_ZH[dim]}对应"
                   f"{NAME_ZH[fact]}{info['zh']}合计为 {fmt_value(v, dec, kind, unit)}"
                   f"（{caliber}；按{dom_zh}域指标口径关联维表后过滤）。",
                   refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            cnt = int(probe(f"SELECT COUNT(*) AS n {scope(period)}"))
            out.append(_claim(
                f"同口径明细共 {_int(cnt)} 笔记录，均能一对一关联到{a_zh}为 {value} 的"
                f"{NAME_ZH[dim]}。", refs["wp_grain"], refs["field_def"]))
        if n >= 3:
            full = probe(f"SELECT ROUND(SUM(f.{field_name}), {dec}) AS m {scope(FULL_PERIOD)}")
            if full:
                out.append(_claim(
                    f"该结果相当于 2024-01-01 至 2024-05-14 同口径全期合计"
                    f"（{fmt_value(full, dec, kind, unit)}）的 {_share(v, full)}。",
                    refs["metric_bound"], refs["wp_recon"]))
        if n >= 4:
            customers = int(probe(f"SELECT COUNT(DISTINCT f.customer_key) AS c {scope(period)}"))
            out.append(_claim(
                f"这些记录来自 {_int(customers)} 个不同客户"
                f"（按 customer_key 对应客户维主键去重）。",
                refs["customer_field"], refs["wp_usage"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：以{NAME_ZH[dim]}主键与事实表外键一对一关联后过滤 {a_zh}，"
                f"{caliber}，未放大明细行数。", refs[f"{dim}_keys"], refs[f"{dim}_field"]))
        return out[:n]

    return _spec("J", "join", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)


K_TABLES = [t for t in AGG_ORDER
            if ("metric_value" in [f for (_t, f) in METRIC_BY_TF if _t == t]
                or "metric_delta" in [f for (_t, f) in METRIC_BY_TF if _t == t])][:8]


def fam_k(i: int) -> Spec:
    """汇总表 ⨝ 日期维：按月份汇总指标值与样本量。"""
    table = K_TABLES[i]
    period = PERIODS[4 + (i % 3)]
    field_name = "metric_value" if (table, "metric_value") in METRIC_BY_TF else "metric_delta"
    metric = METRIC_BY_TF[(table, field_name)][0]
    info = measure_info(table, field_name, metric)
    d = info["decimals"]
    expr, word = agg_metric_expr("a", field_name, info)
    alias = f"{field_name}_{'weighted' if word == '加权平均值' else 'total'}"
    sql = (f"SELECT substr(d.name, 1, 7) AS month_label,\n"
           f"       {expr} AS {alias},\n"
           f"       ROUND(SUM(a.sample_size), 2) AS sample_size_total\n"
           f"FROM {table} a\n"
           f"JOIN dim_date d ON a.date_key = d.date_key\n"
           f"WHERE {where_agg('a', period)}\n"
           f"GROUP BY substr(d.name, 1, 7)\n"
           f"ORDER BY month_label")
    refs = make_refs(table, field_name, metric, dims=("dim_date",))
    caliber = "按汇总周期归属、不跨版本混算"
    label = METRIC_META[metric]["label"]
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH['dim_date']}后按月统计"
                f"{NAME_ZH[table]}的「{label}」{word}与样本量合计，并按月份排序。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[table]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[table]]

    def claims(ctx, n):
        rows = ctx.rows
        peak = max(rows, key=lambda r: r[ctx.pos[alias]])
        low = min(rows, key=lambda r: r[ctx.pos[alias]])
        sample_total = sum(ctx.col("sample_size_total"))
        out = [
            _claim(f"{period.range_zh()} 期间共有 {ctx.n} 个月份有汇总行，"
                   f"{peak[0]} 的「{label}」{word}最高，为 "
                   f"{fmt_value(peak[ctx.pos[alias]], dec, kind, unit)}"
                   f"（按{dom_zh}域指标口径按月归属）。", refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"结果覆盖 {_int(ctx.n)} 个月份汇总行，月份由{NAME_ZH['dim_date']}的日期属性"
                f"与汇总表 date_key 关联得到。", refs["dim_date_join"], refs["field_def"]))
        if n >= 3:
            out.append(_claim(
                f"各月样本量合计为 {_num(sample_total, 2)}，样本量不足 30 行时只标注、"
                f"不对外发布。", refs["metric_def"], refs["wp_rows"]))
        if n >= 4:
            out.append(_claim(
                f"最低月份为 {low[0]}，「{label}」{word}为 "
                f"{fmt_value(low[ctx.pos[alias]], dec, kind, unit)}。",
                refs["metric_bound"], refs["wp_recon"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：{caliber}；各月横向比较前已固定版本标签，"
                f"部分周期行不参与同比。", refs["wp_caliber"], refs["wp_grain"]))
        return out[:n]

    return _spec("K", "join", question, sql, [table, "dim_date"], period, refs,
                 [metric], claims, measure="metric_value", measure_zh=info["zh"],
                 decimals=dec, kind=kind, unit=unit, caliber=caliber)


def fam_m(i: int) -> Spec:
    """事实表 ⨝ 维表：一组多度量指标（记录数 + 金额 + 平均数量）。"""
    fact = FACT_ORDER[(i * 3 + 1) % len(FACT_ORDER)]
    dim = "dim_customer" if i % 2 == 0 else "dim_store"
    attr = "region_code"
    period = PERIODS[(i * 3) % 4]
    field_name, metric, info = pick_measure(fact, i * 2 + 5)
    conds, zhs = fact_caliber(fact, i + 320)
    expr = dim_attr_expr(dim, attr)
    alias = _alias("", field_name, info["agg"])
    sql = (f"SELECT {expr} AS {attr},\n"
           f"       COUNT(*) AS row_count,\n"
           f"       ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias},\n"
           f"       ROUND(AVG(f.quantity), 2) AS quantity_avg\n"
           f"FROM {fact} f\n"
           f"{dim_join_clauses([dim])}\n"
           f"WHERE {where_fact('f', period, conds)}\n"
           f"GROUP BY {expr}\n"
           f"ORDER BY {alias} DESC")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH[dim]}后按{a_zh}分组，"
                f"同时给出{NAME_ZH[fact]}的记录数、{info['zh']}合计与平均数量，"
                f"并按{info['zh']}降序排列。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top, low = ctx.rows[0], ctx.rows[-1]
        total_cnt = sum(ctx.col("row_count"))
        weighted_qty = (sum(float(r[ctx.pos["row_count"]]) * float(r[ctx.pos["quantity_avg"]])
                            for r in ctx.rows) / max(total_cnt, 1))
        out = [
            _claim(f"{period.range_zh()} 期间，{top[0]} 分组的{info['zh']}最高，为 "
                   f"{fmt_value(top[ctx.pos[alias]], dec, kind, unit)}（{caliber}；"
                   f"按{dom_zh}域指标口径关联{NAME_ZH[dim]}后分组）。",
                   refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"{ctx.n} 个{a_zh}分组共 {_int(total_cnt)} 条记录，"
                f"分组记录数由同一批明细行计数得到。", refs["wp_grain"], refs["field_def"]))
        if n >= 3:
            out.append(_claim(
                f"按记录数加权的全区间平均数量为 {_num(weighted_qty, 2)}，"
                f"与各分组平均数量的算术平均不同。", refs["field_trap"], refs["metric_calc"]))
        if n >= 4:
            out.append(_claim(
                f"最低分组为 {low[0]}，{info['zh']}为 "
                f"{fmt_value(low[ctx.pos[alias]], dec, kind, unit)}，平均数量 "
                f"{_num(low[ctx.pos['quantity_avg']], 2)}。",
                refs["wp_join"], refs[f"{dim}_field"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：{a_zh}取自{NAME_ZH[dim]}，与事实表按主键一对一关联后分组，"
                f"平均数量按行级 quantity 求均值。", refs[f"{dim}_keys"], refs[f"{dim}_field"]))
        return out[:n]

    return _spec("M", "join", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)


def fam_n(i: int) -> Spec:
    """事实表 ⨝ 维表 + 条件比例：某一维取值的金额占全部的比例。"""
    fact = FACT_ORDER[(i * 5 + 2) % len(FACT_ORDER)]
    dim, attr = ("dim_customer", "region_code") if i % 2 == 0 else ("dim_channel", "channel_code")
    values = distinct_values(dim, attr)
    value = values[(i * 3) % len(values)]
    period = PERIODS[(i * 2 + 1) % 4]
    field_name, metric, info = pick_measure(fact, i + 9)
    conds, zhs = fact_caliber(fact, i + 360)
    s = DIM_SPECS[dim]
    alias = "share_ratio"
    sql = (f"SELECT ROUND(SUM(CASE WHEN {s['alias']}.{attr} = '{value}' "
           f"THEN f.{field_name} ELSE 0 END)\n"
           f"             / NULLIF(SUM(f.{field_name}), 0), 4) AS {alias}\n"
           f"FROM {fact} f\n"
           f"{dim_join_clauses([dim])}\n"
           f"WHERE {where_fact('f', period, conds)}")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），{a_zh}为 {value} 的{NAME_ZH[dim]}"
                f"对应{NAME_ZH[fact]}的{info['zh']}，占全部{info['zh']}的比例是多少？"
                f"比例保留 4 位小数，统计口径：{caliber}。")

    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]
    join_sql = dim_join_clauses([dim])
    num_expr = f"SUM(CASE WHEN {s['alias']}.{attr} = '{value}' THEN f.{field_name} ELSE 0 END)"
    den_expr = f"SUM(f.{field_name})"
    part_dec = MEASURE_FIELDS[field_name][1]
    part_kind, part_unit = info["kind"], info["unit"]

    def sums(period_) -> list:
        return probe_row(
            f"SELECT ROUND({num_expr}, {part_dec}) AS num_sum, "
            f"ROUND({den_expr}, {part_dec}) AS den_sum "
            f"{scope_where(fact, period_, conds, joins=join_sql + chr(10))}")

    def claims(ctx, n):
        v = ctx.cell(0, alias)
        out = [
            _claim(f"{period.range_zh()} 期间，{a_zh}为 {value} 的{NAME_ZH[dim]}对应"
                   f"{NAME_ZH[fact]}的{info['zh']}占全部{info['zh']}的比例为 {_num(v, 4)}"
                   f"（{caliber}；按{dom_zh}域口径回到分子分母重算）。",
                   refs["metric_bound"], domain_ref),
        ]
        parts = sums(period)
        if n >= 2 and parts:
            out.append(_claim(
                f"分子（{a_zh}为 {value} 的条件{info['zh']}）在区间内合计 "
                f"{fmt_value(parts[0], part_dec, part_kind, part_unit)}。",
                refs["metric_calc"], refs["field_def"]))
        if n >= 3 and parts:
            out.append(_claim(
                f"分母（同口径全部{info['zh']}）在区间内合计 "
                f"{fmt_value(parts[1], part_dec, part_kind, part_unit)}，"
                f"比例正是分子除以分母。", refs["wp_grain"], refs["field_def"]))
        if n >= 4:
            cnt = int(probe(f"SELECT COUNT(*) AS n "
                            f"{scope_where(fact, period, conds, joins=join_sql + chr(10))}"))
            out.append(_claim(
                f"同口径明细共 {_int(cnt)} 笔参与计算，分子分母在同一批关联行上汇总。",
                refs["wp_rows"], refs["wp_usage"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：分子为条件{info['zh']}、分母为同口径全部{info['zh']}，"
                f"两者在同一过滤与关联条件下汇总，比例保留 4 位小数。",
                refs["wp_caliber"], refs["wp_join"]))
        return out[:n]

    return _spec("N", "join", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=4,
                 kind="ratio", unit="", caliber=caliber)

# ================================================================ 嵌套题
O_DIMS = [("dim_customer", "region_code", 3), ("dim_channel", "channel_code", 5),
          ("dim_store", "region_code", 2)]


def fam_o(i: int) -> Spec:
    """窗口函数：分组汇总后用 ROW_NUMBER 取前 N 名。"""
    dim, attr, topn = O_DIMS[i % 3]
    fact = FACT_ORDER[(i * 2) % len(FACT_ORDER)]
    period = PERIODS[i % 4]
    field_name, metric, info = pick_measure(fact, i * 4 + 1)
    conds, zhs = fact_caliber(fact, i + 400)
    expr = dim_attr_expr(dim, attr)
    alias = _alias("", field_name, info["agg"])
    sql = (f"WITH group_totals AS (\n"
           f"    SELECT {expr} AS {attr},\n"
           f"           ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"    FROM {fact} f\n"
           f"{dim_join_clauses([dim], fact_alias='f', indent='    ')}\n"
           f"    WHERE {where_fact('f', period, conds)}\n"
           f"    GROUP BY {expr}\n"
           f"), ranked AS (\n"
           f"    SELECT {attr}, {alias},\n"
           f"           ROW_NUMBER() OVER (ORDER BY {alias} DESC) AS rank_no\n"
           f"    FROM group_totals\n"
           f")\n"
           f"SELECT {attr}, {alias}, rank_no\n"
           f"FROM ranked\n"
           f"WHERE rank_no <= {topn}\n"
           f"ORDER BY rank_no")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH[dim]}后按{a_zh}汇总"
                f"{NAME_ZH[fact]}的{info['zh']}，用窗口函数取{info['zh']}最高的前 {topn} 个"
                f"{a_zh}并给出名次。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        first, last = ctx.rows[0], ctx.rows[-1]
        out = [
            _claim(f"{period.range_zh()} 期间{info['zh']}排名第一的{a_zh}为 {first[0]}，"
                   f"{info['zh']} {fmt_value(first[ctx.pos[alias]], dec, kind, unit)}"
                   f"（{caliber}；按{dom_zh}域指标口径关联{NAME_ZH[dim]}后汇总）。",
                   refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            top_sum = sum(ctx.col(alias))
            out.append(_claim(
                f"前 {ctx.n} 名{a_zh}的{info['zh']}合计为 "
                f"{fmt_value(top_sum, dec, kind, unit)}。", refs["wp_grain"], refs[f"{dim}_field"]))
        if n >= 3:
            out.append(_claim(
                f"第 {ctx.n} 名的{a_zh}为 {last[0]}，{info['zh']} "
                f"{fmt_value(last[ctx.pos[alias]], dec, kind, unit)}。",
                refs["metric_bound"], refs["field_def"]))
        if n >= 4:
            gap = float(first[ctx.pos[alias]]) - float(last[ctx.pos[alias]])
            out.append(_claim(
                f"第一名与第 {ctx.n} 名的{info['zh']}相差 "
                f"{fmt_value(gap, dec, kind, unit)}，名次由 ROW_NUMBER 按汇总值降序生成。",
                refs["wp_grain"], refs["wp_recon"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：先按{a_zh}汇总再排序取前 {ctx.n} 名，{caliber}；"
                f"名次只反映本区间内的相对高低。", refs["wp_caliber"], refs["wp_join"]))
        return out[:n]

    return _spec("O", "nested_agg", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber, limit=topn)


def fam_p(i: int) -> Spec:
    """窗口函数：按月份分区做 RANK，取每月第一名。"""
    dim, attr = ("dim_customer", "region_code") if i % 2 == 0 else ("dim_store", "region_code")
    fact = FACT_ORDER[(i * 3 + 2) % len(FACT_ORDER)]
    period = PERIODS[4 + (i % 3)]
    field_name, metric, info = pick_measure(fact, i * 3 + 4)
    conds, zhs = fact_caliber(fact, i + 440)
    expr = dim_attr_expr(dim, attr)
    alias = _alias("", field_name, info["agg"])
    sql = (f"WITH monthly AS (\n"
           f"    SELECT substr(d.name, 1, 7) AS month_label,\n"
           f"           {expr} AS {attr},\n"
           f"           ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"    FROM {fact} f\n"
           f"    JOIN dim_date d ON f.date_key = d.date_key\n"
           f"    {dim_join_clauses([dim])}\n"
           f"    WHERE {where_fact('f', period, conds)}\n"
           f"    GROUP BY substr(d.name, 1, 7), {expr}\n"
           f"), ranked AS (\n"
           f"    SELECT month_label, {attr}, {alias},\n"
           f"           RANK() OVER (PARTITION BY month_label ORDER BY {alias} DESC) AS rank_no\n"
           f"    FROM monthly\n"
           f")\n"
           f"SELECT month_label, {attr}, {alias}, rank_no\n"
           f"FROM ranked\n"
           f"WHERE rank_no = 1\n"
           f"ORDER BY month_label")
    refs = make_refs(fact, field_name, metric, dims=("dim_date", dim))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH['dim_date']}与"
                f"{NAME_ZH[dim]}，按月统计各{a_zh}的{info['zh']}合计并用窗口函数排名，"
                f"只保留每月{info['zh']}最高的{a_zh}。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        first, last = ctx.rows[0], ctx.rows[-1]
        values = ctx.col(alias)
        out = [
            _claim(f"{period.range_zh()} 期间共 {ctx.n} 个月份有排名结果，"
                   f"{first[ctx.pos['month_label']]} 的第一名为 {first[ctx.pos[attr]]}，"
                   f"{info['zh']} {fmt_value(first[ctx.pos[alias]], dec, kind, unit)}"
                   f"（{caliber}；按{dom_zh}域指标口径分月排名）。", refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"末月 {last[ctx.pos['month_label']]} 的第一名为 {last[ctx.pos[attr]]}，"
                f"{info['zh']} {fmt_value(last[ctx.pos[alias]], dec, kind, unit)}。",
                refs["wp_grain"], refs[f"{dim}_field"]))
        if n >= 3:
            out.append(_claim(
                f"排名覆盖 {_int(ctx.n)} 个月份，每月各取 {info['zh']}最高的一组，"
                f"月份由{NAME_ZH['dim_date']}的日期属性提供。",
                refs["dim_date_join"], refs["field_def"]))
        if n >= 4:
            out.append(_claim(
                f"各月第一名的{info['zh']}介于 {fmt_value(min(values), dec, kind, unit)} 与 "
                f"{fmt_value(max(values), dec, kind, unit)} 之间。",
                refs["metric_bound"], refs["wp_recon"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：RANK() 按 month_label 分区、按{info['zh']}降序编号，"
                f"每月只保留第 1 名，{caliber}。", refs["wp_caliber"], refs["wp_join"]))
        return out[:n]

    return _spec("P", "nested_agg", question, sql, [fact, "dim_date", dim], period,
                 refs, [metric], claims, measure=field_name, measure_zh=info["zh"],
                 decimals=dec, kind=kind, unit=unit, caliber=caliber)


def fam_q(i: int) -> Spec:
    """窗口函数：月份序列上用 LAG 计算环比增减额。"""
    fact = FACT_ORDER[(i * 4 + 3) % len(FACT_ORDER)]
    period = PERIODS[4 + (i % 3)]
    field_name, metric, info = pick_measure(fact, i * 5 + 2)
    conds, zhs = fact_caliber(fact, i + 480)
    alias = _alias("", field_name, info["agg"])
    d = info["decimals"]
    sql = (f"WITH monthly AS (\n"
           f"    SELECT substr(d.name, 1, 7) AS month_label,\n"
           f"           ROUND(SUM(f.{field_name}), {d}) AS {alias}\n"
           f"    FROM {fact} f\n"
           f"    JOIN dim_date d ON f.date_key = d.date_key\n"
           f"    WHERE {where_fact('f', period, conds)}\n"
           f"    GROUP BY substr(d.name, 1, 7)\n"
           f"), series AS (\n"
           f"    SELECT month_label, {alias},\n"
           f"           LAG({alias}) OVER (ORDER BY month_label) AS prev_total,\n"
           f"           ROUND({alias} - LAG({alias}) OVER (ORDER BY month_label), {d}) "
           f"AS mom_diff\n"
           f"    FROM monthly\n"
           f")\n"
           f"SELECT month_label, {alias}, prev_total, mom_diff\n"
           f"FROM series\n"
           f"WHERE prev_total IS NOT NULL\n"
           f"ORDER BY month_label")
    refs = make_refs(fact, field_name, metric, dims=("dim_date",))
    caliber = caliber_zh(zhs)
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH['dim_date']}后按月统计"
                f"{NAME_ZH[fact]}的{info['zh']}合计，并用窗口函数给出相邻月份的环比增减额。"
                f"统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top = max(ctx.rows, key=lambda r: abs(r[ctx.pos["mom_diff"]]))
        out = [
            _claim(f"环比增减额绝对值最大出现在 {top[ctx.pos['month_label']]}，"
                   f"较上月变动 {fmt_value(top[ctx.pos['mom_diff']], dec, kind, unit)}"
                   f"（{caliber}；按{dom_zh}域指标口径按月计算）。",
                   refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"序列覆盖 {ctx.n + 1} 个月份，其中 {ctx.n} 个可计算环比；"
                f"月份由{NAME_ZH['dim_date']}的日期属性提供。",
                refs["dim_date_join"], refs["field_def"]))
        if n >= 3:
            out.append(_claim(
                f"首个可比月份为 {ctx.rows[0][ctx.pos['month_label']]}，"
                f"其前一月作为环比基期只参与计算、不出现在结果中。",
                refs["wp_grain"], refs["metric_bound"]))
        if n >= 4:
            cumulative = sum(ctx.col("mom_diff"))
            out.append(_claim(
                f"序列首月到末月的累计变动为 {fmt_value(cumulative, dec, kind, unit)}，"
                f"等于各月环比增减额之和。", refs["wp_recon"], refs["metric_calc"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：{caliber}；环比用 LAG 取上一月同口径汇总值，"
                f"首月无基期不参与比较。", refs["wp_caliber"], refs["field_trap"]))
        return out[:n]

    return _spec("Q", "nested_agg", question, sql, [fact, "dim_date"], period, refs,
                 [metric], claims, measure=field_name, measure_zh=info["zh"],
                 decimals=dec, kind=kind, unit=unit, caliber=caliber)


def fam_r(i: int) -> Spec:
    """相关子查询：挑出高于同门店平均水平的明细行。"""
    fact = FACT_ORDER[(i * 2 + 1) % len(FACT_ORDER)]
    period = PERIODS[(i * 2) % 4]
    field_name, metric, info = pick_measure(fact, i * 6 + 3)
    conds, zhs = fact_caliber(fact, i + 520)
    alias = f"line_{field_name}"
    sql = (f"SELECT f.order_no AS order_no,\n"
           f"       ROUND(f.{field_name}, {info['decimals']}) AS {alias}\n"
           f"FROM {fact} f\n"
           f"WHERE {where_fact('f', period, conds)}\n"
           f"  AND f.{field_name} > (\n"
           f"      SELECT AVG(f2.{field_name})\n"
           f"      FROM {fact} f2\n"
           f"      WHERE f2.store_key = f.store_key\n"
           f"        AND f2.is_deleted = 0\n"
           f"        AND f2.date_key BETWEEN {period.start} AND {period.end}\n"
           f"  )\n"
           f"ORDER BY {alias} DESC\n"
           f"LIMIT {ROW_CAP}")
    refs = make_refs(fact, field_name, metric, dims=("dim_store",))
    caliber = caliber_zh(zhs)
    question = (f"{period.range_zh()} 期间（{period.zh}），找出{NAME_ZH[fact]}中{info['zh']}"
                f"高于同一门店平均水平（同区间口径）的业务单号与{info['zh']}，"
                f"按{info['zh']}降序最多返回 {ROW_CAP} 条。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top, low = ctx.rows[0], ctx.rows[-1]
        out = [
            _claim(f"符合「高于同门店平均」条件的记录中，{top[0]} 的{info['zh']}最高，为 "
                   f"{fmt_value(top[ctx.pos[alias]], dec, kind, unit)}（{caliber}；"
                   f"按{dom_zh}域指标口径同门店比较）。", refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"本次共返回 {_int(ctx.n)} 条高于基准的明细记录，按{info['zh']}降序排列。",
                refs["wp_rows"], refs["field_def"]))
        if n >= 3:
            out.append(_claim(
                f"返回记录中{info['zh']}最低的一条为 {low[0]}，"
                f"{info['zh']} {fmt_value(low[ctx.pos[alias]], dec, kind, unit)}。",
                refs["wp_join"], refs["metric_bound"]))
        if n >= 4:
            out.append(_claim(
                f"比较基准是同一门店、同一区间内的行级平均{info['zh']}，"
                f"逐行判断是否严格高于该基准。", refs["dim_store_field"], refs["wp_join_risk"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：{caliber}；子查询按门店分区计算平均值，只返回高于平均的明细行。",
                refs["wp_caliber"], refs["wp_usage"]))
        return out[:n]

    return _spec("R", "nested_agg", question, sql, [fact, "dim_store"], period, refs,
                 [metric], claims, measure=field_name, measure_zh=info["zh"],
                 decimals=dec, kind=kind, unit=unit, caliber=caliber, limit=ROW_CAP)


def fam_s(i: int) -> Spec:
    """EXISTS 半连接：只统计存在目标维取值的明细行。"""
    fact = FACT_ORDER[(i * 3 + 4) % len(FACT_ORDER)]
    dim, attr = ("dim_customer", "region_code") if i % 2 == 0 else ("dim_store", "region_code")
    values = distinct_values(dim, attr)
    value = values[(i * 3 + 1) % len(values)]
    period = PERIODS[(i * 3 + 1) % 4]
    field_name, metric, info = pick_measure(fact, i * 4 + 5)
    conds, zhs = fact_caliber(fact, i + 560, mode="nostatus")
    s = DIM_SPECS[dim]
    alias = _alias("", field_name, info["agg"])
    sql = (f"SELECT ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"FROM {fact} f\n"
           f"WHERE {where_fact('f', period, conds)}\n"
           f"  AND EXISTS (\n"
           f"      SELECT 1\n"
           f"      FROM {dim} {s['alias']}\n"
           f"      WHERE {s['alias']}.{s['pk']} = f.{s['key']}\n"
           f"        AND {s['alias']}.{attr} = '{value}'\n"
           f"  )")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），只统计能关联到{a_zh}为 {value} 的"
                f"{NAME_ZH[dim]}的{NAME_ZH[fact]}记录，其{info['zh']}合计是多少？"
                f"用 EXISTS 半连接实现，统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]
    exists_sql = (f"EXISTS (SELECT 1 FROM {dim} {s['alias']} "
                  f"WHERE {s['alias']}.{s['pk']} = f.{s['key']} "
                  f"AND {s['alias']}.{attr} = '{value}')")

    def scope(period_) -> str:
        return scope_where(fact, period_, conds, extra=exists_sql)

    def claims(ctx, n):
        v = ctx.cell(0, alias)
        out = [
            _claim(f"{period.range_zh()} 期间，存在{a_zh}为 {value} 的{NAME_ZH[dim]}时，"
                   f"{NAME_ZH[fact]}{info['zh']}合计为 {fmt_value(v, dec, kind, unit)}"
                   f"（{caliber}；按{dom_zh}域指标口径做半连接过滤）。",
                   refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            cnt = int(probe(f"SELECT COUNT(*) AS n {scope(period)}"))
            out.append(_claim(
                f"满足存在性条件的明细共 {_int(cnt)} 笔，半连接只做存在性判断。",
                refs["wp_grain"], refs["field_def"]))
        if n >= 3:
            full = probe(f"SELECT ROUND(SUM(f.{field_name}), {dec}) AS m {scope(FULL_PERIOD)}")
            if full:
                out.append(_claim(
                    f"该结果相当于 2024-01-01 至 2024-05-14 同口径全期合计"
                    f"（{fmt_value(full, dec, kind, unit)}）的 {_share(v, full)}。",
                    refs["metric_bound"], refs["wp_recon"]))
        if n >= 4:
            customers = int(probe(f"SELECT COUNT(DISTINCT f.customer_key) AS c {scope(period)}"))
            out.append(_claim(
                f"这些记录来自 {_int(customers)} 个不同客户"
                f"（按 customer_key 对应客户维主键去重）。",
                refs["customer_field"], refs["wp_usage"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：半连接只做存在性判断、不放大明细行数，{info['zh']}仍按明细聚合；"
                f"{caliber}。", refs[f"{dim}_keys"], refs[f"{dim}_field"]))
        return out[:n]

    return _spec("S", "nested_agg", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)


T_DIMS = [("dim_customer", "region_code"), ("dim_channel", "channel_code"),
          ("dim_store", "region_code")]


def fam_t(i: int) -> Spec:
    """CTE + 标量子查询：只保留高于分组平均值的组。"""
    dim, attr = T_DIMS[i % 3]
    fact = FACT_ORDER[(i * 2) % len(FACT_ORDER)]
    period = PERIODS[(i * 2 + 1) % 4]
    field_name, metric, info = pick_measure(fact, i * 3 + 6)
    conds, zhs = fact_caliber(fact, i + 600)
    expr = dim_attr_expr(dim, attr)
    alias = _alias("", field_name, info["agg"])
    sql = (f"WITH group_totals AS (\n"
           f"    SELECT {expr} AS {attr},\n"
           f"           ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"    FROM {fact} f\n"
           f"    {dim_join_clauses([dim])}\n"
           f"    WHERE {where_fact('f', period, conds)}\n"
           f"    GROUP BY {expr}\n"
           f")\n"
           f"SELECT {attr}, {alias}\n"
           f"FROM group_totals\n"
           f"WHERE {alias} > (SELECT AVG({alias}) FROM group_totals)\n"
           f"ORDER BY {alias} DESC")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH[dim]}后按{a_zh}汇总"
                f"{NAME_ZH[fact]}的{info['zh']}，只保留高于全部{a_zh}平均水平的组，"
                f"并按{info['zh']}降序排列。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top, low = ctx.rows[0], ctx.rows[-1]
        values = ctx.col(alias)
        out = [
            _claim(f"{period.range_zh()} 期间高于平均水平的{a_zh}共 {ctx.n} 个，"
                   f"其中 {top[0]} 最高，{info['zh']}为 "
                   f"{fmt_value(top[ctx.pos[alias]], dec, kind, unit)}（{caliber}；"
                   f"按{dom_zh}域指标口径分组后过滤）。", refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"返回的组中最低为 {low[0]}，{info['zh']} "
                f"{fmt_value(low[ctx.pos[alias]], dec, kind, unit)}。",
                refs["wp_grain"], refs["field_trap"]))
        if n >= 3:
            out.append(_claim(
                f"过滤条件是组汇总值大于全部{a_zh}的组均值，而非行级均值；"
                f"故入榜组的{info['zh']}都高于基准。", refs["wp_trap"], refs["wp_usage"]))
        if n >= 4:
            out.append(_claim(
                f"入榜组的{info['zh']}介于 {fmt_value(min(values), dec, kind, unit)}"
                f"与 {fmt_value(max(values), dec, kind, unit)} 之间。",
                refs["wp_recon"], refs["field_trap"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：先按{a_zh}汇总{info['zh']}，再用标量子查询与该组均值比较，"
                f"{caliber}。", refs["wp_caliber"], refs[f"{dim}_field"]))
        return out[:n]

    return _spec("T", "nested_agg", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)


def fam_u(i: int) -> Spec:
    """两层聚合：先按客户汇总，再对客户粒度做二次统计。"""
    fact = FACT_ORDER[(i * 3 + 1) % len(FACT_ORDER)]
    period = PERIODS[(i * 3 + 2) % 4]
    field_name, metric, info = pick_measure(fact, i * 2 + 7)
    conds, zhs = fact_caliber(fact, i + 640)
    inner = f"{field_name}_total"
    sql = (f"WITH per_customer AS (\n"
           f"    SELECT f.customer_key AS customer_key,\n"
           f"           ROUND(SUM(f.{field_name}), {info['decimals']}) AS {inner}\n"
           f"    FROM {fact} f\n"
           f"    WHERE {where_fact('f', period, conds)}\n"
           f"    GROUP BY f.customer_key\n"
           f")\n"
           f"SELECT COUNT(*) AS customer_cnt,\n"
           f"       ROUND(AVG({inner}), {info['decimals']}) AS avg_{inner},\n"
           f"       ROUND(MAX({inner}), {info['decimals']}) AS max_{inner}\n"
           f"FROM per_customer")
    refs = make_refs(fact, field_name, metric, dims=("dim_customer",))
    caliber = caliber_zh(zhs)
    question = (f"{period.range_zh()} 期间（{period.zh}），先按客户汇总{NAME_ZH[fact]}的"
                f"{info['zh']}，再给出有业务的客户数、户均{info['zh']}与最高{info['zh']}。"
                f"统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        cnt = ctx.cell(0, "customer_cnt")
        avg = ctx.cell(0, f"avg_{inner}")
        mx = ctx.cell(0, f"max_{inner}")
        out = [
            _claim(f"{period.range_zh()} 期间有业务的客户共 {_int(cnt)} 个"
                   f"（按 customer_key 去重；客户粒度汇总后计数，口径与指标卡计算式一致）。",
                   refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            out.append(_claim(
                f"户均{info['zh']}为 {fmt_value(avg, dec, kind, unit)}，"
                f"由客户粒度汇总值再取平均得到。", refs["wp_grain"], refs["field_trap"]))
        if n >= 3:
            out.append(_claim(
                f"单客户最高{info['zh']}为 {fmt_value(mx, dec, kind, unit)}。",
                refs["metric_bound"], refs["wp_recon"]))
        if n >= 4:
            gap = float(mx) - float(avg)
            out.append(_claim(
                f"最高客户{info['zh']}比户均高 {fmt_value(gap, dec, kind, unit)}，"
                f"相当于户均水平的 {_num(float(mx) / float(avg), 2) if float(avg) else 'n/a'} 倍。",
                refs["wp_usage"], refs["metric_calc"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：先按客户汇总{NAME_ZH[fact]}的{info['zh']}，再对客户粒度取"
                f"均值与最大值，避免用明细行直接求平均；{caliber}。",
                refs["wp_caliber"], refs["dim_customer_field"]))
        return out[:n]

    return _spec("U", "nested_agg", question, sql, [fact, "dim_customer"], period,
                 refs, [metric], claims, measure=field_name, measure_zh=info["zh"],
                 decimals=dec, kind=kind, unit=unit, caliber=caliber)


V_DIMS = [("dim_customer", "region_code"), ("dim_channel", "channel_code")]


def fam_v(i: int) -> Spec:
    """CTE + 标量子查询：各组占比（分母为分组汇总之和）。"""
    dim, attr = V_DIMS[i % 2]
    fact = FACT_ORDER[(i * 4 + 2) % len(FACT_ORDER)]
    period = PERIODS[(i * 3 + 1) % 4]
    field_name, metric, info = pick_measure(fact, i * 5 + 3)
    conds, zhs = fact_caliber(fact, i + 680)
    expr = dim_attr_expr(dim, attr)
    alias = _alias("", field_name, info["agg"])
    sql = (f"WITH group_totals AS (\n"
           f"    SELECT {expr} AS {attr},\n"
           f"           ROUND(SUM(f.{field_name}), {info['decimals']}) AS {alias}\n"
           f"    FROM {fact} f\n"
           f"    {dim_join_clauses([dim])}\n"
           f"    WHERE {where_fact('f', period, conds)}\n"
           f"    GROUP BY {expr}\n"
           f")\n"
           f"SELECT {attr}, {alias},\n"
           f"       ROUND({alias} / (SELECT SUM({alias}) FROM group_totals), 4) AS share_ratio\n"
           f"FROM group_totals\n"
           f"ORDER BY share_ratio DESC")
    refs = make_refs(fact, field_name, metric, dims=(dim,))
    caliber = caliber_zh(zhs)
    a_zh = dim_attr_zh(dim, attr)
    question = (f"{period.range_zh()} 期间（{period.zh}），关联{NAME_ZH[dim]}后按{a_zh}汇总"
                f"{NAME_ZH[fact]}的{info['zh']}，并给出各组占全部{info['zh']}的比例"
                f"（保留 4 位小数），按比例降序排列。统计口径：{caliber}。")
    dec, kind, unit = info["decimals"], info["kind"], info["unit"]
    dom_zh = DOMAIN_ZH[TABLE_DOMAIN[fact]]
    domain_ref = DOMAIN_REF[TABLE_DOMAIN[fact]]

    def claims(ctx, n):
        top, low = ctx.rows[0], ctx.rows[-1]
        out = [
            _claim(f"{period.range_zh()} 期间占比最高的{a_zh}是 {top[0]}，"
                   f"占 {_num(top[ctx.pos['share_ratio']], 4)}，对应{info['zh']} "
                   f"{fmt_value(top[ctx.pos[alias]], dec, kind, unit)}"
                   f"（{caliber}；按{dom_zh}域指标口径分组后求占比）。",
                   refs["metric_calc"], domain_ref),
        ]
        if n >= 2:
            total = sum(ctx.col(alias))
            out.append(_claim(
                f"参与占比计算的 {ctx.n} 个分组，其{info['zh']}合计为 "
                f"{fmt_value(total, dec, kind, unit)}，即占比计算的分母。",
                refs["wp_join"], refs["field_def"]))
        if n >= 3:
            out.append(_claim(
                f"本次共 {ctx.n} 个{a_zh}分组参与占比计算，分组由维表属性产生。",
                refs["wp_rows"], refs["wp_usage"]))
        if n >= 4:
            out.append(_claim(
                f"占比最低的分组为 {low[0]}，份额 "
                f"{_num(low[ctx.pos['share_ratio']], 4)}。", refs["metric_bound"], refs["wp_recon"]))
        if n >= 5:
            out.append(_claim(
                f"口径说明：{ctx.n} 个分组的占比合计为 1，分母取同口径分组汇总之和，"
                f"{caliber}。", refs["wp_caliber"], refs[f"{dim}_field"]))
        return out[:n]

    return _spec("V", "nested_agg", question, sql, [fact, dim], period, refs, [metric],
                 claims, measure=field_name, measure_zh=info["zh"], decimals=dec,
                 kind=kind, unit=unit, caliber=caliber)

# ================================================================ 组题与产出
def single_table_specs() -> list[Spec]:
    specs = [fam_a(i) for i in range(18)]
    specs += [fam_b(i) for i in range(8)]
    specs += [fam_c(i) for i in range(10)]
    specs += [fam_d(i) for i in range(8)]
    specs += [fam_e(i) for i in range(3)]
    specs += [fam_f(i) for i in range(8)]
    specs += [fam_g(i) for i in range(5)]
    return specs


def join_specs() -> list[Spec]:
    specs = [fam_h(i) for i in range(24)]
    specs += [fam_i(i) for i in range(10)]
    specs += [fam_j(i) for i in range(12)]
    specs += [fam_k(i) for i in range(8)]
    specs += [fam_m(i) for i in range(10)]
    specs += [fam_n(i) for i in range(6)]
    return specs


def nested_specs() -> list[Spec]:
    specs = [fam_o(i) for i in range(12)]
    specs += [fam_p(i) for i in range(8)]
    specs += [fam_q(i) for i in range(8)]
    specs += [fam_r(i) for i in range(10)]
    specs += [fam_s(i) for i in range(8)]
    specs += [fam_t(i) for i in range(10)]
    specs += [fam_u(i) for i in range(8)]
    specs += [fam_v(i) for i in range(6)]
    return specs


def assign_claim_counts(specs: list[Spec]) -> list[int]:
    """在难度层内按 CLAIM_QUOTA 给每题分配主张数，保证各难度层覆盖 1–5 条。

    名额来自 ``params.tasks.claims_per_task`` 的整数换算，层内用固定种子洗牌后
    按题序分配：整体分布恰好等于 params 的目标比例，且每种主张数在每个难度层
    都出现，便于 C3 按主张数分层。
    """
    counts = [0] * len(specs)
    for difficulty in ("single_table", "join", "nested_agg"):
        idxs = [i for i, spec in enumerate(specs) if spec.difficulty == difficulty]
        quota = CLAIM_QUOTA[difficulty]
        pool = [n for n in CLAIM_COUNT_VALUES for _ in range(quota[n])]
        assert len(pool) == len(idxs), \
            f"{difficulty} 主张名额 {len(pool)} 与题目数 {len(idxs)} 不符"
        shuffled = seeds.shuffle(pool, "tasks", f"claim-counts-{difficulty}")
        for i, n in zip(idxs, shuffled):
            counts[i] = n
    totals = Counter(counts)
    want = {int(k): round(float(v) * len(specs)) for k, v in
            TASK_PARAMS["claims_per_task"].items()}
    assert {k: totals.get(k, 0) for k in CLAIM_COUNT_VALUES} == want, \
        f"主张数分布 {dict(totals)} 与 params 换算 {want} 不符"
    assert len(set(counts)) == 5, f"主张数只有 {sorted(set(counts))} 种，退化"
    return counts


def generate() -> tuple[list[dict], list[dict], list[dict], list[Spec], list[dict]]:
    specs = single_table_specs() + join_specs() + nested_specs()
    want = {"single_table": TASK_PARAMS["single_table"], "join": TASK_PARAMS["join"],
            "nested_agg": TASK_PARAMS["nested_agg"]}
    assert len(specs) == TASK_PARAMS["total"], f"题目数 {len(specs)} != {TASK_PARAMS['total']}"
    got = Counter(s.difficulty for s in specs)
    assert {k: got.get(k, 0) for k in want} == want, f"难度配比不符：{dict(got)}"

    claim_counts = assign_claim_counts(specs)
    for spec, n in zip(specs, claim_counts):
        spec.extra["claim_count"] = n
    cluster_map, clusters = assign_clusters(specs)

    tasks, golds, metas = [], [], []
    for seq, spec in enumerate(specs, start=1):
        task, gold, meta = build_one(seq, spec, spec.extra["claim_count"], cluster_map[seq])
        tasks.append(task)
        golds.append(gold)
        metas.append(meta)
    assert [m["claim_count"] for m in metas] == claim_counts, "主张数与配额不一致"
    return tasks, golds, metas, specs, clusters


def _file_entry(path: Path) -> dict:
    text_rows = len(path.read_text(encoding="utf-8").splitlines())
    return {"rows": text_rows, "sha256": io.sha256_file(path)}


def write_manifest(out: Path, tasks, golds, metas, specs, clusters) -> dict:
    files = {
        "tasks.jsonl": _file_entry(out / "tasks.jsonl"),
        "gold_results.jsonl": _file_entry(out / "gold_results.jsonl"),
    }
    for name in ("build.py", "selfcheck.py"):
        src = TASKS_DIR / name
        if src.is_file():
            files[name] = _file_entry(src)

    def dist(key):
        return dict(sorted(Counter(m[key] for m in metas).items()))

    single = [m for m in metas if m["difficulty"] == "single_table"]
    joins = [m for m in metas if m["difficulty"] == "join"]
    nested = [m for m in metas if m["difficulty"] == "nested_agg"]

    single_facts = sorted({f for m in single for f in m["fact_tables"]})
    join_pairs = sorted({(d, f) for m in joins for d in m["dim_tables"] for f in m["fact_tables"]})
    agg_join_pairs = sorted({(d, f) for m in joins for d in m["dim_tables"]
                             for f in m["tables"] if TABLE_KIND[f] == "agg"})

    task_by_id = {t["task_id"]: t for t in tasks}
    cluster_table = []
    for cluster in clusters:
        members = [task_by_id[tid] for tid in cluster["task_ids"]]
        shared = None
        for task in members:
            docs = {e["doc_id"] for e in task["truth"]["evidence"]}
            shared = docs if shared is None else (shared & docs)
        cluster_table.append({
            "cluster_id": cluster["cluster_id"],
            "domain": cluster["domain"],
            "family": cluster["family"],
            "size": cluster["size"],
            "task_ids": cluster["task_ids"],
            "primary_tables": cluster["primary_tables"],
            "measures": cluster["measures"],
            "difficulties": cluster["difficulties"],
            "claim_counts": cluster["claim_counts"],
            "shared_docs": sorted(shared or []),
        })

    claim_dist = dict(sorted(Counter(m["claim_count"] for m in metas).items()))
    claims_by_difficulty = {}
    for difficulty in ("single_table", "join", "nested_agg"):
        sub = Counter(m["claim_count"] for m in metas if m["difficulty"] == difficulty)
        claims_by_difficulty[difficulty] = {str(k): sub.get(k, 0)
                                            for k in CLAIM_COUNT_VALUES}

    stats = {
        "task_total": len(tasks),
        "difficulty": dict(sorted(Counter(t["difficulty"] for t in tasks).items())),
        "domain": dist("domain"),
        "permission": dist("permission"),
        "answer_shape": dict(sorted(Counter(t["answer_shape"] for t in tasks).items())),
        "snapshot": dict(sorted(Counter(t["snapshot"] for t in tasks).items())),
        "family": dist("family"),
        "claims": {
            "per_task": {str(k): v for k, v in claim_dist.items()},
            "per_task_ratio": {str(k): round(v / len(tasks), 4) for k, v in claim_dist.items()},
            "by_difficulty": claims_by_difficulty,
            "total": sum(claim_dist[k] * k for k in claim_dist),
            "target": TASK_PARAMS["claims_per_task"],
        },
        "clusters": {
            "count": len(clusters),
            "min_size": min(c["size"] for c in clusters),
            "max_size": max(c["size"] for c in clusters),
            "size_distribution": dict(sorted(Counter(c["size"] for c in clusters).items())),
            "with_multiple_shared_docs": sum(
                1 for c in cluster_table if len(c["shared_docs"]) > 1),
            "table": cluster_table,
        },
        "coverage": {
            "single_table_fact_tables": len(single_facts),
            "single_table_fact_table_names": single_facts,
            "join_dim_fact_pairs": len(join_pairs),
            "join_dim_fact_pair_samples": [f"{d}+{f}" for d, f in join_pairs[:12]],
            "join_dim_agg_pairs": len(agg_join_pairs),
            "nested_with_window": sum(1 for m in nested if m["uses_window"]),
            "nested_with_subquery": sum(1 for m in nested if m["uses_subquery"]),
            "nested_with_cte": sum(1 for m in nested if m["uses_cte"]),
            "nested_window_or_subquery": sum(
                1 for m in nested if m["uses_window"] or m["uses_subquery"]),
            "window_function_tasks": sum(1 for m in metas if m["uses_window"]),
            "subquery_tasks": sum(1 for m in metas if m["uses_subquery"]),
            "tasks_with_metric_refs": sum(1 for m in metas if m["metric_refs"]),
            "tasks_without_metric_refs": sum(1 for m in metas if not m["metric_refs"]),
            "evidence_docs": len({d for t in tasks for e in t["truth"]["evidence"]
                                  for d in [e["doc_id"]]}),
            "max_result_rows": max(len(t["truth"]["value"]) for t in tasks
                                   if isinstance(t["truth"]["value"], list)),
            "queries_executed": len(tasks),
        },
        "truth_layers": {
            "value": len(tasks),
            "claims": sum(len(t["truth"]["claims"]) for t in tasks),
            "evidence": sum(len(t["truth"]["evidence"]) for t in tasks),
            "version": EVIDENCE_VERSION,
        },
        "generated_from": {
            "params_tasks": TASK_PARAMS,
            "params_clusters": CLUSTER_PARAMS,
            "tables": len(TABLES),
            "docs_version": EVIDENCE_VERSION,
            "snapshot": SNAPSHOT,
            "seed": PARAMS["global_seed"],
        },
    }
    manifest = dict(files)
    manifest["stats"] = stats
    io.write_json(out / "MANIFEST.json", manifest)
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="生成 P3 取数题库与三层真值")
    ap.add_argument("--out", default=None, help="输出目录，默认 dataset/tasks")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else TASKS_DIR
    out.mkdir(parents=True, exist_ok=True)

    tasks, golds, metas, specs, clusters = generate()
    n_task = io.write_jsonl(out / "tasks.jsonl", tasks)
    n_gold = io.write_jsonl(out / "gold_results.jsonl", golds)
    manifest = write_manifest(out, tasks, golds, metas, specs, clusters)
    digest = manifest["tasks.jsonl"]["sha256"]

    if not args.quiet:
        st = manifest["stats"]
        print(f"题目 {n_task} 条，gold 结果 {n_gold} 条 -> {out}")
        print(f"难度分布 {st['difficulty']}")
        print(f"主题分布 {st['domain']}")
        print(f"权限分布 {st['permission']}")
        print(f"主张数分布 {st['claims']['per_task']}（合计 {st['claims']['total']} 条）")
        cl = st["clusters"]
        print(f"语义簇 {cl['count']} 个，规模分布 {cl['size_distribution']}，"
              f"簇内共享证据（>1 份）{cl['with_multiple_shared_docs']} 个")
        print(f"答案形态 {st['answer_shape']}｜fingerprint {digest[:16]}")
        cov = st["coverage"]
        print(f"覆盖：单表事实表 {cov['single_table_fact_tables']} 张；"
              f"join 维表-事实表组合 {cov['join_dim_fact_pairs']} 组；"
              f"嵌套窗口 {cov['nested_with_window']} 题 / 子查询 {cov['nested_with_subquery']} 题")
        print(f"tasks.jsonl sha256 = {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

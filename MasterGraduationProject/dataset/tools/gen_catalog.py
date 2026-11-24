"""生成表目录与血缘图（P0 契约的一部分）。

用法：python dataset/tools/gen_catalog.py
产出：
  dataset/contracts/tables.json   60 表 × 20 字段的完整目录
  dataset/contracts/lineage.json  血缘边（含一条三跳链）
  dataset/fixtures/*.jsonl        各文件 3 条样例，供下游解耦开发

本脚本不含随机性；同输入必得同输出。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import ids, io  # noqa: E402

DIMS = ["dim_date", "dim_region", "dim_channel", "dim_customer", "dim_product",
        "dim_store", "dim_employee", "dim_promotion"]
FACTS = ["fact_orders", "fact_order_item", "fact_sales_daily", "fact_returns", "fact_refunds",
         "fact_payments", "fact_invoices", "fact_shipments", "fact_deliveries", "fact_inventory",
         "fact_inventory_snapshot", "fact_stock_move", "fact_price_change", "fact_promotion_apply",
         "fact_campaign_touch", "fact_clicks", "fact_sessions", "fact_leads", "fact_quotes",
         "fact_contracts", "fact_subscriptions", "fact_renewals", "fact_churn", "fact_tickets",
         "fact_sla_events", "fact_usage", "fact_engagement", "fact_budget", "fact_targets",
         "fact_forecast", "fact_collections", "fact_supplier_orders", "fact_quality_checks",
         "fact_costs"]
AGGS = ["agg_daily_sales", "agg_monthly_gmv", "agg_region_share", "agg_channel_mix",
        "agg_product_rank", "agg_customer_ltv", "agg_cohort_retention", "agg_funnel",
        "agg_sla_summary", "agg_cost_breakdown", "agg_forecast_error", "agg_inventory_turnover"]
LOGS = ["log_query_audit", "log_etl_run", "log_access", "log_metric_change",
        "log_schema_change", "log_backfill"]

POOLS = {
    "dim": ["name", "code", "short_name", "category", "status", "valid_from", "valid_to",
            "region_code", "channel_code", "owner", "description", "level", "parent_id",
            "sort_order", "is_active", "ext_attr"],
    "fact": ["quantity", "amount", "gross_amount", "net_amount", "discount_amount", "tax_amount",
             "unit_price", "cost_amount", "currency_code", "order_no", "customer_key",
             "product_key", "store_key", "channel_key", "status_code", "is_deleted"],
    "agg": ["metric_value", "metric_delta", "metric_ratio", "window_start", "window_end",
            "dimension_key", "sample_size", "is_partial", "version_tag", "source_table",
            "calc_expr", "owner", "refresh_mode", "unit_label", "rounding", "comment"],
    "log": ["event_type", "actor", "object_id", "before_value", "after_value", "duration_ms",
            "status", "error_code", "statement_hash", "ip_hash", "user_agent", "trace_id",
            "span_id", "payload_size", "retry_count", "comment"],
}

REAL_HINTS = ("amount", "price", "cost", "quantity", "ratio", "delta", "value", "size", "ms")


def _type_of(name: str) -> str:
    if name.endswith("_id") or name.endswith("_key") or name.endswith("_count"):
        return "INTEGER"
    if any(h in name for h in REAL_HINTS):
        return "REAL"
    if name.endswith("_at") or name.startswith("window_") or name.endswith("_from") \
            or name.endswith("_to") or name == "valid_from" or name == "valid_to":
        return "TEXT"
    if name.startswith("is_") or name.endswith("_flag"):
        return "INTEGER"
    return "TEXT"


def _desc(kind: str, table: str, name: str) -> str:
    label = {"dim": "维度表", "fact": "事实表", "agg": "汇总表", "log": "日志表"}[kind]
    return f"{table}（{label}）中的 {name} 字段，按本表粒度记录该属性的取值与口径。"


def build_tables() -> tuple[list[dict], int]:
    rows_plan = {"dim": 400, "fact": 1200, "agg": 120, "log": 600}
    seq = 0
    tables: list[dict] = []
    for kind, names in (("dim", DIMS), ("fact", FACTS), ("agg", AGGS), ("log", LOGS)):
        for name in names:
            seq += 1
            tid = ids.table_id(seq)
            base = name.split("_", 1)[1]
            fields = []
            fields.append({"field_id": ids.field_id(tid, 1), "name": f"{base}_id",
                           "type": "INTEGER", "pk": True, "nullable": False,
                           "desc": f"{name} 的主键，按加载批次单调生成。"})
            fields.append({"field_id": ids.field_id(tid, 2), "name": "date_key",
                           "type": "INTEGER", "pk": False, "nullable": False,
                           "desc": "业务日期键，格式 YYYYMMDD，关联 dim_date。"})
            fields.append({"field_id": ids.field_id(tid, 3), "name": "updated_at",
                           "type": "TEXT", "pk": False, "nullable": False,
                           "desc": "该行最近一次写入的 UTC 时间，用于版本比对。"})
            fields.append({"field_id": ids.field_id(tid, 4), "name": "etl_batch_id",
                           "type": "TEXT", "pk": False, "nullable": True,
                           "desc": "产生该行的 ETL 批次号，同一批次可见性一致。"})
            pool = POOLS[kind]
            for j, fname in enumerate(pool, start=5):
                fields.append({
                    "field_id": ids.field_id(tid, j),
                    "name": fname,
                    "type": _type_of(fname),
                    "pk": False,
                    "nullable": fname not in ("currency_code",),
                    "desc": _desc(kind, name, fname),
                })
            assert len(fields) == 20, (name, len(fields))
            tables.append({
                "table_id": tid,
                "name": name,
                "kind": kind,
                "grain": {"dim": "实体", "fact": "事件", "agg": "业务周期", "log": "调用"}[kind],
                "rows": rows_plan[kind],
                "fields": fields,
            })
    return tables, seq


def build_lineage(tables: list[dict]) -> tuple[list[dict], list[str]]:
    by_name = {t["name"]: t["table_id"] for t in tables}
    edges: list[dict] = []
    # 维度 -> 事实：每个事实表引用两个维度
    for i, f in enumerate(FACTS):
        for d in (DIMS[i % len(DIMS)], DIMS[(i + 3) % len(DIMS)]):
            edges.append({"from": by_name[d], "to": by_name[f], "kind": "fk"})
    # 事实 -> 汇总：每个汇总表来自一个事实表。偏移 2 使 agg_daily_sales 取自
    # fact_sales_daily，从而与 dim_customer -> fact_orders -> fact_sales_daily ->
    # agg_daily_sales 构成一条三跳链，供多跳传播实验使用。
    for i, a in enumerate(AGGS):
        edges.append({"from": by_name[FACTS[(i + 2) % len(FACTS)]], "to": by_name[a],
                      "kind": "aggregate"})
    # 事实 -> 事实：派生链（含一条三跳链 dim_customer -> fact_orders -> fact_sales_daily -> agg_daily_sales）
    for src, dst in (("fact_orders", "fact_sales_daily"),
                     ("fact_returns", "fact_refunds"),
                     ("fact_payments", "fact_collections"),
                     ("fact_orders", "fact_shipments")):
        edges.append({"from": by_name[src], "to": by_name[dst], "kind": "derive"})
    chain = [by_name["dim_customer"], by_name["fact_orders"],
             by_name["fact_sales_daily"], by_name["agg_daily_sales"]]
    return edges, chain


def main() -> int:
    tables, n = build_tables()
    edges, chain = build_lineage(tables)
    io.write_json(ROOT / "contracts" / "tables.json",
                  {"generated_by": "tools/gen_catalog.py", "table_count": n, "tables": tables})
    io.write_json(ROOT / "contracts" / "lineage.json",
                  {"generated_by": "tools/gen_catalog.py", "edge_count": len(edges),
                   "three_hop_chain": chain,
                   "edges": edges})
    print(f"tables={n} fields={n * 20} edges={len(edges)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

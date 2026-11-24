import sqlite3
con=sqlite3.connect("file:db/snapshots/v0.sqlite?mode=ro",uri=True)
def q(s): return con.execute(s).fetchall()
print("discount zeros:", q("select (select count(*) from fact_inventory where discount_amount=0),(select count(*) from fact_inventory),(select count(*) from fact_orders where discount_amount=0),(select sum(discount_amount) from fact_inventory)"))
print("metric_value scale:")
for t in ["agg_daily_sales","agg_monthly_gmv","agg_region_share","agg_channel_mix","agg_product_rank","agg_customer_ltv","agg_cohort_retention","agg_funnel","agg_sla_summary","agg_cost_breakdown","agg_forecast_error","agg_inventory_turnover"]:
    print(" ",t,q(f"select round(max(abs(metric_value)),4),round(max(abs(metric_delta)),4) from {t}"))
print("is_partial dist:")
for t in ["agg_cohort_retention","agg_customer_ltv","agg_inventory_turnover","agg_sla_summary","agg_forecast_error","agg_monthly_gmv","agg_cost_breakdown","agg_daily_sales","agg_region_share"]:
    print(" ",t,q(f"select is_partial,count(*) from {t} group by 1"))

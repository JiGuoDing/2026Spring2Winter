"""确定性构建 dataset/db/snapshots/{v0,v1,v2}.sqlite。

用法：
  python dataset/db/gen_schema.py     # 先由目录生成 DDL（schema.sql）
  python dataset/db/build.py          # 再构建三个快照与 hashes.json

设计要点
--------
1. 随机性只来自 ``common/seeds.py::rng("db", 表名)``，一表一个 Random 实例，按目录顺序
   消费，不跨表共享，因此同参数重跑得到同一序列；
2. 先建一份基准库 ``snapshots/.base.sqlite``，再逐份字节复制，分别应用 v1/v2 增量，
   最后写临时文件 + ``os.replace`` 原子替换。三个快照中 v0 与基准库字节相同；
3. v0 = 基准；v1 = 8 张事实表 + 3 张维度表的行级 UPDATE/DELETE/INSERT（同步刷新
   updated_at 与 etl_batch_id，行数守恒）；v2 = 在 v1 之上新增 2 张表、给 3 张表加列，
   并修订 12 张汇总表的口径（metric_value / metric_delta / version_tag / calc_expr）；
4. 事实表业务日期严格落在 2024-01-01..2024-05-14，金额非负且保留 2 位小数；
   dim_date 是日历维，覆盖 2024 自然年 400 天（含事实窗口前后余量，日历维属于预加载维表）；
5. 12 张汇总表的 metric_value 是按信息量级独立构造的合成口径值，不保证与事实表逐行可加总
   复现；表与表之间的血缘以 contracts/lineage.json 为准（source_table 字段即取自该文件）。
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
ROOT = DB_DIR.parent
for _p in (str(ROOT), str(DB_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import io, seeds  # noqa: E402

import gen_schema  # noqa: E402

SNAPSHOT_DIR = DB_DIR / "snapshots"
HASHES_JSON = SNAPSHOT_DIR / "hashes.json"

# 契约第四节时间轴：三个快照的生效时刻
SNAP_TS = {
    "v0": "2024-05-15T00:00:00Z",
    "v1": "2024-05-15T06:00:00Z",
    "v2": "2024-05-15T12:00:00Z",
}
SNAP_BATCH = {
    "v0": "batch_20240515_v0",
    "v1": "batch_20240515_v1",
    "v2": "batch_20240515_v2",
}

BUSINESS_START = date(2024, 1, 1)
BUSINESS_END = date(2024, 5, 14)          # 窗口最后一天，次日 00:00 快照 v0 生效
CALENDAR_START = date(2024, 1, 1)
CALENDAR_ROWS = 400                        # dim_date 行数，与目录一致

# v1 行级变更对象：8 张事实表 + 3 张维度表
V1_FACTS = ("fact_orders", "fact_sales_daily", "fact_returns", "fact_payments",
            "fact_inventory", "fact_sessions", "fact_tickets", "fact_costs")
V1_DIMS = ("dim_region", "dim_product", "dim_employee")
V1_TABLES = frozenset(V1_FACTS) | frozenset(V1_DIMS)

# v2 结构变更：新增 2 张表 + 给 3 张表加列
V2_ADD_COLUMNS = (
    ("fact_orders", "channel_caliber", "TEXT"),
    ("fact_sales_daily", "gmv_flag", "INTEGER"),
    ("agg_daily_sales", "caliber_tag", "TEXT"),
)

# ---------------------------------------------------------------------------
# 词表：所有中文名称都从这里取，保证同一份脚本内可复现
# ---------------------------------------------------------------------------
REGION_MAJORS = ["华东大区", "华北大区", "华南大区", "华中大区",
                 "西南大区", "西北大区", "东北大区", "海外大区"]

CITY_POOL = [
    "北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "天津", "重庆", "成都",
    "武汉", "长沙", "西安", "郑州", "青岛", "济南", "合肥", "福州", "厦门", "南昌",
    "沈阳", "大连", "长春", "哈尔滨", "石家庄", "太原", "呼和浩特", "兰州", "西宁", "银川",
    "乌鲁木齐", "昆明", "贵阳", "南宁", "海口", "拉萨", "宁波", "无锡", "佛山", "东莞",
    "珠海", "常州", "温州", "绍兴", "嘉兴", "金华", "台州", "中山", "惠州", "泉州",
]

CHANNEL_MAJORS = [
    "官方商城", "天猫旗舰店", "京东自营", "拼多多店铺", "抖音直播", "快手直播",
    "视频号小店", "小红书商城", "线下直营店", "加盟门店", "分销代理", "企业直销",
    "电话销售", "海外经销", "亚马逊店铺", "独立站", "社群团购", "银行联名",
    "运营商合作", "员工内购",
]

PRODUCT_MAJORS = [
    "智能空调", "变频冰箱", "滚筒洗衣机", "厨房小电", "清洁电器", "个护电器",
    "影音设备", "智能照明", "空气净化", "净水设备", "智能门锁", "电动工具",
    "家纺用品", "储能电源", "车载电器", "商用冷链", "医疗护理", "宠物电器",
    "户外电源", "配件耗材",
]

PRODUCT_MODELS = [
    "A1型", "A2型", "A3型", "A5型", "B1型", "B2型", "B3型", "C1型", "C2型", "C3型",
    "D1型", "D2型", "D5型", "E1型", "E2型", "F1型", "F2型", "G1型", "G2型",
]

STORE_SUBS = [
    "静安旗舰店", "中心广场店", "万象城店", "高铁站店", "社区服务店", "仓储直销店",
    "奥莱折扣店", "大学城店", "科技园店", "滨江店", "老城店", "新区店", "机场店",
    "物流园店", "产业园店", "湖畔店", "中央商圈店", "南站店", "北城店",
]

DEPT_MAJORS = [
    "销售一部", "销售二部", "市场部", "品牌部", "供应链部", "仓储物流部", "财务部",
    "客服中心", "信息技术部", "数据治理部", "人力资源部", "战略投资部", "法务合规部",
    "采购部", "质量管理部", "运营支持部", "海外事业部", "渠道发展部", "售后服务部",
    "内部审计部",
]

SURN = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
        "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗",
        "郑", "梁", "谢", "宋", "唐", "许", "韩", "冯", "邓", "曹"]

GIVEN = ["伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋",
         "勇", "艳", "杰", "娟", "涛", "明", "超", "秀英", "霞", "平",
         "刚", "桂英", "英", "华", "建", "文", "辉", "力", "红", "鹏"]

CUSTOMER_INDUSTRY = [
    "制造业", "零售业", "批发业", "金融业", "物流业", "医疗健康", "教育培训", "互联网",
    "能源电力", "建筑工程", "汽车后市场", "食品饮料", "纺织服装", "电子制造", "化工新材",
    "农业科技", "文化旅游", "通信服务", "环保水务", "政府机构",
]

CUSTOMER_PREFIX = [
    "华信", "恒达", "中科", "瑞丰", "远景", "启明", "天工", "众诚", "汇川", "金桥",
    "博远", "嘉禾", "泰和", "联创", "海纳", "卓越", "新元", "拓普", "安泰",
]

CUSTOMER_SUFFIX = ["有限公司", "股份有限公司", "集团有限公司", "科技股份有限公司", "控股有限公司"]

PROMO_MAJORS = [
    "618大促", "开门红", "春季上新", "品牌日", "会员日", "满300减30", "跨店满减",
    "新品首发", "清仓特卖", "直播专享", "渠道联合促销", "老客召回", "首单立减",
    "满赠礼遇", "积分翻倍", "节日礼盒", "企业团购", "换季清库", "秒杀专场", "预售定金",
]

OWNERS = ["王磊", "李静", "张伟", "陈曦", "刘洋", "赵敏", "周涛", "吴倩",
          "徐鹏", "孙莉", "马超", "朱琳"]

FX = ["USD", "HKD", "EUR"]

# 维度表规格：majors 为一级行，其余为二级行
DIM_SPECS = {
    "dim_region": dict(
        majors=REGION_MAJORS, l1="大区", l2="城市", cat_l1="区域层级", cat_l2="城市层级",
        prefix="RG", src="crm_region", unit="区域",
        status=("active", "active", "active", "inactive"),
        name_major=lambda g, m: m,
        name_child=lambda g, c, m: f"{m}·{CITY_POOL[(c // len(REGION_MAJORS)) % len(CITY_POOL)]}",
    ),
    "dim_channel": dict(
        majors=CHANNEL_MAJORS, l1="渠道类型", l2="渠道单元", cat_l1="渠道层级", cat_l2="渠道单元",
        prefix="CH", src="crm_channel", unit="渠道",
        status=("active", "active", "active", "pilot"),
        name_major=lambda g, m: m,
        name_child=lambda g, c, m: f"{m}·{CITY_POOL[(c // len(CHANNEL_MAJORS)) % len(CITY_POOL)]}",
    ),
    "dim_customer": dict(
        majors=CUSTOMER_INDUSTRY, l1="行业", l2="客户", cat_l1="客户层级", cat_l2="行业客户",
        prefix="CU", src="crm_customer", unit="客户",
        status=("active", "active", "active", "churned"),
        name_major=lambda g, m: f"{m}客户群",
        name_child=lambda g, c, m: (
            f"{CITY_POOL[g % len(CITY_POOL)]}"
            f"{CUSTOMER_PREFIX[(g // 21) % len(CUSTOMER_PREFIX)]}"
            f"{CUSTOMER_SUFFIX[g % len(CUSTOMER_SUFFIX)]}"
        ),
    ),
    "dim_product": dict(
        majors=PRODUCT_MAJORS, l1="产品线", l2="SKU", cat_l1="产品层级", cat_l2="产品型号",
        prefix="PD", src="plm_product", unit="产品",
        status=("active", "active", "active", "eol"),
        name_major=lambda g, m: m,
        name_child=lambda g, c, m: f"{m} {PRODUCT_MODELS[(c // len(PRODUCT_MAJORS)) % len(PRODUCT_MODELS)]}",
    ),
    "dim_store": dict(
        majors=CITY_POOL[:20], l1="城市", l2="门店", cat_l1="城市层级", cat_l2="门店类型",
        prefix="ST", src="pos_store", unit="门店",
        status=("active", "active", "active", "closed"),
        name_major=lambda g, m: f"{m}城市群",
        name_child=lambda g, c, m: f"{m}·{STORE_SUBS[(c // 20) % len(STORE_SUBS)]}",
    ),
    "dim_employee": dict(
        majors=DEPT_MAJORS, l1="部门", l2="员工", cat_l1="组织层级", cat_l2="部门成员",
        prefix="EM", src="hrm_employee", unit="员工",
        status=("active", "active", "active", "leave"),
        name_major=lambda g, m: m,
        name_child=lambda g, c, m: f"{SURN[g % len(SURN)]}{GIVEN[(g // len(SURN)) % len(GIVEN)]}",
    ),
    "dim_promotion": dict(
        majors=PROMO_MAJORS, l1="促销类型", l2="促销批次", cat_l1="活动层级", cat_l2="活动批次",
        prefix="PR", src="mkt_promotion", unit="促销",
        status=("active", "active", "planned", "finished"),
        name_major=lambda g, m: m,
        name_child=lambda g, c, m: f"{m} 第{(c // len(PROMO_MAJORS)) + 1}期",
    ),
}

# 事实表分组：同一组共用一套金额/数量/状态口径，再按表做确定性微调
FACT_GROUPS = {
    "fact_orders": "retail", "fact_order_item": "retail", "fact_sales_daily": "retail",
    "fact_payments": "retail", "fact_invoices": "retail", "fact_shipments": "retail",
    "fact_deliveries": "retail", "fact_promotion_apply": "retail",
    "fact_campaign_touch": "retail",
    "fact_returns": "returns", "fact_refunds": "returns",
    "fact_inventory": "inventory", "fact_inventory_snapshot": "inventory",
    "fact_stock_move": "inventory", "fact_price_change": "inventory",
    "fact_clicks": "web", "fact_sessions": "web", "fact_leads": "web",
    "fact_quotes": "web", "fact_engagement": "web",
    "fact_contracts": "contract", "fact_subscriptions": "contract",
    "fact_renewals": "contract", "fact_churn": "contract",
    "fact_tickets": "service", "fact_sla_events": "service", "fact_usage": "service",
    "fact_budget": "finance", "fact_targets": "finance", "fact_forecast": "finance",
    "fact_costs": "finance", "fact_collections": "finance",
    "fact_supplier_orders": "supply", "fact_quality_checks": "supply",
}

GROUP_PROFILE = {
    "retail": dict(price=(39.0, 2600.0), qty=(1, 12), disc=(0.0, 0.0, 0.05, 0.1, 0.15),
                   tax=0.13, cny=0.94, prefix="SO",
                   status=("created", "paid", "shipped", "completed", "cancelled")),
    "returns": dict(price=(29.0, 1800.0), qty=(1, 4), disc=(0.0, 0.0, 0.05),
                    tax=0.13, cny=0.95, prefix="RT",
                    status=("received", "approved", "restocked", "rejected")),
    "inventory": dict(price=(15.0, 900.0), qty=(0, 320), disc=(0.0,),
                      tax=0.13, cny=0.97, prefix="IV",
                      status=("on_hand", "reserved", "damaged", "expired")),
    "web": dict(price=(9.0, 450.0), qty=(1, 30), disc=(0.0, 0.1, 0.2),
                tax=0.06, cny=0.92, prefix="WB",
                status=("new", "qualified", "converted", "abandoned")),
    "contract": dict(price=(800.0, 26000.0), qty=(1, 5), disc=(0.0, 0.08, 0.15),
                     tax=0.06, cny=0.96, prefix="CT",
                     status=("active", "pending", "expired", "terminated")),
    "service": dict(price=(20.0, 1500.0), qty=(1, 20), disc=(0.0, 0.05),
                    tax=0.06, cny=0.98, prefix="SV",
                    status=("open", "in_progress", "resolved", "closed")),
    "finance": dict(price=(100.0, 90000.0), qty=(1, 8), disc=(0.0, 0.03),
                    tax=0.06, cny=0.90, prefix="FN",
                    status=("draft", "approved", "posted", "void")),
    "supply": dict(price=(5.0, 3000.0), qty=(1, 500), disc=(0.0, 0.02, 0.05),
                   tax=0.13, cny=0.93, prefix="PO",
                   status=("pending", "received", "inspected", "rejected")),
}

AGG_PROFILE = {
    "agg_daily_sales": dict(lo=48000.0, hi=920000.0, unit="元", span=1, grain="日",
                            expr="SUM(net_amount) GROUP BY date_key"),
    "agg_monthly_gmv": dict(lo=1200000.0, hi=26000000.0, unit="元", span=30, grain="月",
                            expr="SUM(amount) GROUP BY strftime('%Y-%m', date_key)"),
    "agg_region_share": dict(lo=0.02, hi=0.32, unit="%", span=30, grain="月",
                             expr="SUM(amount) / SUM(SUM(amount)) OVER ()"),
    "agg_channel_mix": dict(lo=0.03, hi=0.41, unit="%", span=30, grain="月",
                            expr="SUM(amount) / SUM(SUM(amount)) OVER (PARTITION BY 月)"),
    "agg_product_rank": dict(lo=1.0, hi=400.0, unit="名次", span=7, grain="周", integer=True,
                             expr="RANK() OVER (ORDER BY SUM(amount) DESC)"),
    "agg_customer_ltv": dict(lo=680.0, hi=52000.0, unit="元", span=90, grain="月",
                             expr="SUM(net_amount) GROUP BY customer_key"),
    "agg_cohort_retention": dict(lo=0.12, hi=0.78, unit="%", span=30, grain="月",
                                 expr="活跃客户数 / 首购客户数"),
    "agg_funnel": dict(lo=0.05, hi=0.62, unit="%", span=7, grain="周",
                       expr="转化事件数 / 曝光事件数"),
    "agg_sla_summary": dict(lo=0.82, hi=0.995, unit="%", span=1, grain="日",
                            expr="按时完成工单数 / 工单总数"),
    "agg_cost_breakdown": dict(lo=12000.0, hi=780000.0, unit="元", span=30, grain="月",
                               expr="SUM(cost_amount) GROUP BY 成本科目"),
    "agg_forecast_error": dict(lo=0.012, hi=0.24, unit="%", span=30, grain="月",
                               expr="ABS(预测值 - 实际值) / 实际值"),
    "agg_inventory_turnover": dict(lo=1.4, hi=11.8, unit="次", span=90, grain="季",
                                   expr="销售成本 / 平均库存成本"),
}

LOG_PROFILE = {
    "log_query_audit": dict(events=("SELECT", "WITH", "EXPLAIN", "PRAGMA"),
                            actors=("analyst", "bi_reader", "svc_query", "dba_oncall")),
    "log_etl_run": dict(events=("full_load", "incremental_load", "merge_upsert", "quality_gate"),
                        actors=("etl_runner", "airflow", "dbt_run", "scheduler")),
    "log_access": dict(events=("login", "export_csv", "grant_role", "revoke_role"),
                       actors=("analyst", "ops", "auditor", "hr_admin")),
    "log_metric_change": dict(events=("metric_revision", "threshold_update", "unit_change",
                                      "caliber_change"),
                              actors=("metric_owner", "data_steward", "bi_lead")),
    "log_schema_change": dict(events=("add_column", "add_table", "rename_column",
                                      "drop_index"),
                              actors=("dba_oncall", "schema_owner", "migration_bot")),
    "log_backfill": dict(events=("backfill_run", "replay_partition", "repair_gap", "reload_dim"),
                         actors=("etl_runner", "data_ops", "scheduler")),
}

# v2 口径修订系数（按汇总表）
AGG_V2_FACTOR = {
    "agg_daily_sales": 1.02, "agg_monthly_gmv": 1.02, "agg_region_share": 0.98,
    "agg_channel_mix": 0.98, "agg_product_rank": 1.0, "agg_customer_ltv": 1.02,
    "agg_cohort_retention": 0.99, "agg_funnel": 1.01, "agg_sla_summary": 1.0,
    "agg_cost_breakdown": 1.03, "agg_forecast_error": 0.96, "agg_inventory_turnover": 1.0,
}

AGG_V2_EXPR = {
    "agg_daily_sales": "SUM(amount) / 1.02 GROUP BY date_key -- 含税口径修订",
    "agg_monthly_gmv": "SUM(amount) GROUP BY strftime('%Y-%m', date_key) -- 含税口径修订",
}

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
BUSINESS_DATES = [BUSINESS_START + timedelta(days=i)
                  for i in range((BUSINESS_END - BUSINESS_START).days + 1)]


def r2(x: float) -> float:
    """保留 2 位小数，四舍五入走十进制字符串，避免二进制浮点尾差。"""
    return float(f"{x:.2f}")


def dkey(d: date) -> int:
    """业务日期键：YYYYMMDD 整数。"""
    return int(d.strftime("%Y%m%d"))


def q(name: str) -> str:
    """SQLite 标识符转义。"""
    return '"' + name.replace('"', '""') + '"'


def pk_name(table: dict) -> str:
    return next(f["name"] for f in table["fields"] if f.get("pk"))


def _agg_source() -> dict[str, str]:
    """由 lineage.json 的 aggregate 边得到：汇总表 ID -> 来源事实表名。"""
    lineage = io.read_json(ROOT / "contracts" / "lineage.json")
    tables = gen_schema.load_tables()
    by_id = {t["table_id"]: t["name"] for t in tables}
    return {e["to"]: by_id[e["from"]] for e in lineage["edges"] if e["kind"] == "aggregate"}


# ---------------------------------------------------------------------------
# 行生成
# ---------------------------------------------------------------------------
def _meta(table: dict, i: int, snap: str) -> dict:
    """公共四列：主键、业务日期键、更新时间、ETL 批次号。"""
    return {
        pk_name(table): i,
        "updated_at": SNAP_TS[snap],
        "etl_batch_id": SNAP_BATCH[snap],
    }


def _calendar_row(table: dict, i: int, snap: str) -> dict:
    dt = CALENDAR_START + timedelta(days=i - 1)
    dow = dt.weekday()
    holiday = (dt.month, dt.day) in {
        (1, 1), (2, 10), (2, 11), (2, 12), (2, 13), (2, 14), (2, 15), (2, 16),
        (4, 4), (4, 5), (5, 1), (5, 2), (5, 3),
    }
    category = "节假日" if holiday else ("周末" if dow >= 5 else "工作日")
    effective = dt <= BUSINESS_END
    row = _meta(table, i, snap)
    row.update({
        "date_key": dkey(dt),
        "name": dt.isoformat(),
        "code": f"D{dkey(dt)}",
        "short_name": dt.strftime("%m-%d"),
        "category": category,
        "status": "effective" if effective else "planned",
        "valid_from": dt.isoformat(),
        "valid_to": dt.isoformat(),
        "region_code": None,
        "channel_code": None,
        "owner": "数据平台组",
        "description": f"{dt.isoformat()} 日历行，{category}，粒度为自然日。",
        "level": "日",
        "parent_id": None,
        "sort_order": str(i),
        "is_active": 1 if effective else 0,
        "ext_attr": (f'{{"year":{dt.year},"month":{dt.month},'
                     f'"week":{dt.isocalendar().week},"day":{dt.day}}}'),
    })
    return row


def _dim_row(table: dict, i: int, r, snap: str, spec: dict) -> dict:
    majors = spec["majors"]
    n_major = len(majors)
    g = i - 1
    child = i - n_major - 1          # 二级行 0 基下标
    is_l1 = i <= n_major
    if is_l1:
        major = majors[g]
        name = spec["name_major"](g, major)
        level = spec["l1"]
        category = spec["cat_l1"]
        parent = None
    else:
        major = majors[child % n_major]
        name = spec["name_child"](g, child, major)
        level = spec["l2"]
        category = spec["cat_l2"]
        parent = (child % n_major) + 1

    row = _meta(table, i, snap)
    row.update({
        "date_key": dkey(BUSINESS_DATES[g % len(BUSINESS_DATES)]),
        "name": name,
        "code": f"{spec['prefix']}{i:04d}",
        "short_name": name if len(name) <= 8 else name[:8],
        "category": category,
        "status": r.choice(spec["status"]),
        "valid_from": "2023-11-01",
        "valid_to": None if r.random() < 0.08 else "9999-12-31",
        "region_code": f"RG{(g % len(REGION_MAJORS)) + 1:02d}",
        "channel_code": f"CH{(g % len(CHANNEL_MAJORS)) + 1:02d}",
        "owner": r.choice(OWNERS),
        "description": f"{name} 属于{major}，{category}，源系统 {spec['src']}。",
        "level": level,
        "parent_id": parent,
        "sort_order": str(i),
        "is_active": 0 if g % 41 == 0 else 1,
        "ext_attr": (f'{{"src":"{spec["src"]}","unit":"{spec["unit"]}",'
                     f'"zone":"CN","refresh":"daily"}}'),
    })
    return row


def _fact_setup(name: str, r) -> dict:
    base = GROUP_PROFILE[FACT_GROUPS[name]]
    lo, hi = base["price"]
    scale = 0.72 + 0.56 * r.random()
    return dict(
        lo=lo * scale, hi=hi * scale, qty=base["qty"], disc=base["disc"],
        tax=base["tax"] * (0.85 + 0.30 * r.random()),
        cny=base["cny"], prefix=base["prefix"], status=base["status"],
    )


def _fact_row(table: dict, i: int, r, snap: str, prof: dict) -> dict:
    dt = BUSINESS_DATES[r.randrange(len(BUSINESS_DATES))]
    key = dkey(dt)
    qty = float(r.randint(prof["qty"][0], prof["qty"][1]))
    unit = r2(r.uniform(prof["lo"], prof["hi"]))
    gross = r2(unit * qty)
    discount = r2(gross * r.choice(prof["disc"]))
    net = r2(gross - discount)
    tax = r2(net * prof["tax"])
    amount = r2(net + tax)
    cost = r2(net * r.uniform(0.52, 0.88))
    currency = "CNY" if r.random() < prof["cny"] else r.choice(FX)

    row = _meta(table, i, snap)
    row.update({
        "date_key": key,
        "quantity": qty,
        "amount": amount,
        "gross_amount": gross,
        "net_amount": net,
        "discount_amount": discount,
        "tax_amount": tax,
        "unit_price": unit,
        "cost_amount": cost,
        "currency_code": currency,
        "order_no": f"{prof['prefix']}{key}{i:05d}",
        "customer_key": r.randint(1, 400),
        "product_key": r.randint(1, 400),
        "store_key": r.randint(1, 400),
        "channel_key": r.randint(1, 400),
        "status_code": r.choice(prof["status"]),
        "is_deleted": 1 if r.random() < 0.02 else 0,
    })
    return row


def _agg_row(table: dict, i: int, r, snap: str, source: str) -> dict:
    prof = AGG_PROFILE[table["name"]]
    end = BUSINESS_DATES[r.randrange(len(BUSINESS_DATES))]
    start = max(BUSINESS_START, end - timedelta(days=prof["span"] - 1))
    raw = r.uniform(prof["lo"], prof["hi"])
    value = float(int(round(raw))) if prof.get("integer") else r2(raw)
    ratio = value if prof["unit"] == "%" else r.uniform(0.01, 0.90)
    ratio = round(min(max(float(ratio), 0.0), 1.0), 6)
    delta = r2(value * r.uniform(-0.18, 0.18))
    sample = float(r.randint(60, 1400))

    row = _meta(table, i, snap)
    row.update({
        "date_key": dkey(end),
        "metric_value": value,
        "metric_delta": delta,
        "metric_ratio": ratio,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "dimension_key": r.randint(1, 400),
        "sample_size": sample,
        "is_partial": 1 if end >= BUSINESS_END - timedelta(days=3) else 0,
        "version_tag": snap,
        "source_table": source,
        "calc_expr": prof["expr"],
        "owner": r.choice(OWNERS),
        "refresh_mode": r.choice(("daily", "hourly", "weekly")),
        "unit_label": prof["unit"],
        "rounding": "2位小数",
        "comment": f"{prof['grain']}粒度{prof['unit']}口径，来源 {source}。",
    })
    return row


def _log_row(table: dict, i: int, r, snap: str, spec: dict) -> dict:
    dt = BUSINESS_DATES[r.randrange(len(BUSINESS_DATES))]
    event = r.choice(spec["events"])
    actor = f"{r.choice(spec['actors'])}{r.randint(1, 40):02d}"
    ok = r.random() > 0.07
    status = "success" if ok else "failed"
    before = r2(r.uniform(10.0, 90000.0)) if r.random() < 0.72 else None
    after = r2(before * r.uniform(0.82, 1.24)) if before is not None else None
    duration = r2(r.uniform(4.0, 11800.0))
    retry = r.randint(0, 3)

    row = _meta(table, i, snap)
    row.update({
        "date_key": dkey(dt),
        "event_type": event,
        "actor": actor,
        "object_id": r.randint(1, 60),
        "before_value": before,
        "after_value": after,
        "duration_ms": duration,
        "status": status,
        "error_code": None if ok else r.choice(("E1001", "E2004", "E4001", "E5003")),
        "statement_hash": io.sha256_text(f"{table['name']}|{i}|{event}")[:16],
        "ip_hash": io.sha256_text(f"10.{(i * 7) % 254}.{(i * 13) % 254}.{(i * 29) % 254}")[:16],
        "user_agent": r.choice((
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "python-requests/2.31.0", "dbt-runner/1.7", "curl/8.4.0",
        )),
        "trace_id": r.randint(100000000, 999999999),
        "span_id": r.randint(1, 9999),
        "payload_size": r2(r.uniform(180.0, 880000.0)),
        "retry_count": retry,
        "comment": f"{event} 事件：{status}，耗时 {duration} ms，重试 {retry} 次。",
    })
    return row


# ---------------------------------------------------------------------------
# v1 行级变更计划（与基础行共用同一个 RNG，保证“随机只来自 rng(db, 表名)”）
# ---------------------------------------------------------------------------
def _v1_plan(table: dict, rows: list[dict], r, prof: dict | None) -> dict:
    n = len(rows)
    deleted = sorted(r.sample(range(1, n + 1), 3))
    deleted_set = set(deleted)
    updatable = [i for i in range(1, n + 1) if i not in deleted_set]
    updated = sorted(r.sample(updatable, 4))

    stamp = {"updated_at": SNAP_TS["v1"], "etl_batch_id": SNAP_BATCH["v1"]}
    updates: list[tuple[int, dict]] = []
    if table["kind"] == "fact":
        for key in updated:
            old = rows[key - 1]
            gross = old["gross_amount"]
            factor = 1.0 + 0.15 * r.random()
            net = min(r2(old["net_amount"] * factor), gross)
            values = {
                "net_amount": net,
                "discount_amount": r2(gross - net),
                "tax_amount": r2(net * r.uniform(0.05, 0.14)),
                "cost_amount": r2(net * r.uniform(0.50, 0.85)),
                "status_code": r.choice(prof["status"]),
                "is_deleted": 0,
            }
            values["amount"] = r2(values["net_amount"] + values["tax_amount"])
            values.update(stamp)
            updates.append((key, values))
    else:
        for key in updated:
            old = rows[key - 1]
            values = {
                "status": r.choice(("active", "inactive", "pending")),
                "owner": r.choice(OWNERS),
                "is_active": 1 if r.random() < 0.7 else 0,
                "description": old["description"] + "（v1 复核）",
            }
            values.update(stamp)
            updates.append((key, values))

    inserts = []
    for k in range(3):
        new_id = n + 1 + k
        if table["kind"] == "fact":
            row = _fact_row(table, new_id, r, "v1", prof)
        else:
            spec = DIM_SPECS[table["name"]]
            row = _dim_row(table, new_id, r, "v1", spec)
            # 新增行的父节点指向已有一级行，保持层级自洽
            row["parent_id"] = (new_id % len(spec["majors"])) + 1
        row[pk_name(table)] = new_id
        row["updated_at"] = SNAP_TS["v1"]
        row["etl_batch_id"] = SNAP_BATCH["v1"]
        inserts.append(row)

    return {"pk": pk_name(table), "updates": updates, "deletes": deleted,
            "inserts": inserts, "updated_keys": updated}


# ---------------------------------------------------------------------------
# v2 扩展表（不属于 60 表目录，只在结构变更后出现）
# ---------------------------------------------------------------------------
DIM_POOL_TYPES = [
    ("name", "TEXT"), ("code", "TEXT"), ("short_name", "TEXT"), ("category", "TEXT"),
    ("status", "TEXT"), ("valid_from", "TEXT"), ("valid_to", "TEXT"),
    ("region_code", "TEXT"), ("channel_code", "TEXT"), ("owner", "TEXT"),
    ("description", "TEXT"), ("level", "TEXT"), ("parent_id", "INTEGER"),
    ("sort_order", "TEXT"), ("is_active", "INTEGER"), ("ext_attr", "TEXT"),
]

AGG_POOL_TYPES = [
    ("metric_value", "REAL"), ("metric_delta", "REAL"), ("metric_ratio", "REAL"),
    ("window_start", "TEXT"), ("window_end", "TEXT"), ("dimension_key", "INTEGER"),
    ("sample_size", "REAL"), ("is_partial", "INTEGER"), ("version_tag", "TEXT"),
    ("source_table", "TEXT"), ("calc_expr", "TEXT"), ("owner", "TEXT"),
    ("refresh_mode", "TEXT"), ("unit_label", "TEXT"), ("rounding", "TEXT"),
    ("comment", "TEXT"),
]


def _mk_table(table_id: str, name: str, kind: str, rows: int, pk: str) -> dict:
    pool = DIM_POOL_TYPES if kind == "dim" else AGG_POOL_TYPES
    fields = [
        {"name": pk, "type": "INTEGER", "pk": True, "nullable": False},
        {"name": "date_key", "type": "INTEGER", "pk": False, "nullable": False},
        {"name": "updated_at", "type": "TEXT", "pk": False, "nullable": False},
        {"name": "etl_batch_id", "type": "TEXT", "pk": False, "nullable": True},
    ]
    fields += [{"name": n, "type": t, "pk": False, "nullable": True} for n, t in pool]
    return {"table_id": table_id, "name": name, "kind": kind, "rows": rows, "fields": fields}


V2_TABLES = [
    _mk_table("t61", "dim_geo_rollup", "dim", 400, "geo_rollup_id"),
    _mk_table("t62", "agg_metric_recalibration", "agg", 120, "metric_recalibration_id"),
]

DIM_SPECS["dim_geo_rollup"] = dict(
    majors=CITY_POOL[:20], l1="城市", l2="商圈", cat_l1="地理层级", cat_l2="商圈层级",
    prefix="GR", src="geo_rollup_v2", unit="商圈",
    status=("active", "active", "active", "inactive"),
    name_major=lambda g, m: f"{m}地理汇总",
    name_child=lambda g, c, m: f"{m}·{STORE_SUBS[(c // 20) % len(STORE_SUBS)]}商圈",
)

AGG_PROFILE["agg_metric_recalibration"] = dict(
    lo=1000.0, hi=480000.0, unit="元", span=30, grain="月",
    expr="SUM(amount) * 1.02 GROUP BY dimension_key",
)


# ---------------------------------------------------------------------------
# 生成全部行（含 v1/v2 需要的附加行），不写库
# ---------------------------------------------------------------------------
def generate_all(tables: list[dict], agg_source: dict[str, str]) -> dict[str, dict]:
    payload: dict[str, dict] = {}
    for table in tables:
        name = table["name"]
        kind = table["kind"]
        n = table["rows"]
        r = seeds.rng("db", name)
        prof = None
        if kind == "dim":
            if name == "dim_date":
                rows = [_calendar_row(table, i, "v0") for i in range(1, n + 1)]
            else:
                spec = DIM_SPECS[name]
                rows = [_dim_row(table, i, r, "v0", spec) for i in range(1, n + 1)]
        elif kind == "fact":
            prof = _fact_setup(name, r)
            rows = [_fact_row(table, i, r, "v0", prof) for i in range(1, n + 1)]
        elif kind == "agg":
            source = agg_source.get(table["table_id"], "")
            rows = [_agg_row(table, i, r, "v0", source) for i in range(1, n + 1)]
        elif kind == "log":
            rows = [_log_row(table, i, r, "v0", LOG_PROFILE[name]) for i in range(1, n + 1)]
        else:
            raise ValueError(f"未知表类型 {kind}")
        record = {"table": table, "rows": rows, "profile": prof, "v1": None}
        if name in V1_TABLES:
            record["v1"] = _v1_plan(table, rows, r, prof)
        payload[name] = record

    for table in V2_TABLES:
        name = table["name"]
        r = seeds.rng("db", name)
        n = table["rows"]
        if table["kind"] == "dim":
            rows = [_dim_row(table, i, r, "v2", DIM_SPECS[name]) for i in range(1, n + 1)]
        else:
            rows = [_agg_row(table, i, r, "v2", "fact_orders") for i in range(1, n + 1)]
        payload[name] = {"table": table, "rows": rows, "profile": None, "v1": None}
    return payload


def _selfcheck(payload: dict[str, dict], tables: list[dict]) -> None:
    """生成阶段自检：行数、日期窗口、金额非负、2 位小数。"""
    for table in tables + V2_TABLES:
        rows = payload[table["name"]]["rows"]
        assert len(rows) == table["rows"], f"{table['name']} 行数 {len(rows)} != {table['rows']}"
        keys = [row[pk_name(table)] for row in rows]
        assert len(set(keys)) == len(keys), f"{table['name']} 主键重复"
        for row in rows:
            if table["kind"] == "dim" and table["name"] == "dim_date":
                continue
            assert BUSINESS_START <= date(row["date_key"] // 10000,
                                          row["date_key"] // 100 % 100,
                                          row["date_key"] % 100) <= BUSINESS_END, \
                f"{table['name']} 日期越界 {row['date_key']}"
            if table["kind"] == "fact":
                for col in ("quantity", "amount", "gross_amount", "net_amount",
                            "discount_amount", "tax_amount", "unit_price", "cost_amount"):
                    assert row[col] >= 0, f"{table['name']} {col} 为负"
                    assert abs(row[col] * 100 - round(row[col] * 100)) < 1e-6, \
                        f"{table['name']} {col} 超过 2 位小数"
                assert row["net_amount"] + row["tax_amount"] == row["amount"] or \
                    abs(row["net_amount"] + row["tax_amount"] - row["amount"]) < 0.011, \
                    f"{table['name']} amount 口径不一致"
                assert row["gross_amount"] == r2(row["unit_price"] * row["quantity"])


# ---------------------------------------------------------------------------
# 写库
# ---------------------------------------------------------------------------
def _insert_sql(table: dict) -> str:
    cols = [f["name"] for f in table["fields"]]
    return (f"INSERT INTO {q(table['name'])} "
            f"({', '.join(q(c) for c in cols)}) "
            f"VALUES ({', '.join('?' * len(cols))})")


def _insert(con: sqlite3.Connection, table: dict, rows: list[dict]) -> None:
    cols = [f["name"] for f in table["fields"]]
    con.executemany(_insert_sql(table), [tuple(row[c] for c in cols) for row in rows])


def build_base(path: Path, tables: list[dict], payload: dict[str, dict]) -> None:
    _remove(path)
    con = sqlite3.connect(str(path), isolation_level=None)
    try:
        con.execute("PRAGMA page_size=4096")
        con.execute("PRAGMA journal_mode=DELETE")
        con.execute("PRAGMA synchronous=OFF")
        con.executescript(gen_schema.render_ddl(tables))
        con.execute("BEGIN")
        for table in tables:
            _insert(con, table, payload[table["name"]]["rows"])
        con.execute("COMMIT")
    finally:
        con.close()


def apply_v1(con: sqlite3.Connection, payload: dict[str, dict], order: list[str]) -> None:
    """v1：行级 UPDATE / DELETE / INSERT，同步 updated_at 与 etl_batch_id。"""
    for name in order:
        plan = payload[name]["v1"]
        table = payload[name]["table"]
        con.execute("BEGIN")
        for key, values in plan["updates"]:
            cols = list(values)
            con.execute(
                f"UPDATE {q(name)} SET {', '.join(f'{q(c)}=?' for c in cols)} "
                f"WHERE {q(plan['pk'])}=?",
                [values[c] for c in cols] + [key],
            )
        for key in plan["deletes"]:
            con.execute(f"DELETE FROM {q(name)} WHERE {q(plan['pk'])}=?", (key,))
        _insert(con, table, plan["inserts"])
        con.execute("COMMIT")


def apply_v2(con: sqlite3.Connection, payload: dict[str, dict]) -> None:
    """v2：结构变更（+2 表 / +3 列）与口径相关数据变更。"""
    ts, batch = SNAP_TS["v2"], SNAP_BATCH["v2"]

    # 1) 新增 2 张表
    con.executescript(gen_schema.render_ddl(V2_TABLES))
    con.execute("BEGIN")
    for table in V2_TABLES:
        _insert(con, table, payload[table["name"]]["rows"])
    con.execute("COMMIT")

    # 2) 给 3 张表加列
    for table_name, column, coltype in V2_ADD_COLUMNS:
        con.execute(f"ALTER TABLE {q(table_name)} ADD COLUMN {q(column)} {coltype}")

    # 3) 回填新列（口径切换）
    con.execute(
        f"UPDATE {q('fact_orders')} SET {q('channel_caliber')} = "
        f"CASE WHEN {q('channel_key')} <= ? THEN ? ELSE ? END, "
        f"{q('updated_at')} = ?, {q('etl_batch_id')} = ?",
        (200, "GMV_V2", "GMV_V1", ts, batch),
    )
    con.execute(
        f"UPDATE {q('fact_sales_daily')} SET {q('gmv_flag')} = "
        f"CASE WHEN {q('is_deleted')} = 0 THEN 1 ELSE 0 END, "
        f"{q('updated_at')} = ?, {q('etl_batch_id')} = ?",
        (ts, batch),
    )
    con.execute(
        f"UPDATE {q('agg_daily_sales')} SET {q('caliber_tag')} = ?, "
        f"{q('updated_at')} = ?, {q('etl_batch_id')} = ?",
        ("gmv_incl_tax_v2", ts, batch),
    )

    # 4) 12 张汇总表的口径修订：metric_value / metric_delta / metric_ratio / version_tag
    for table_name, factor in AGG_V2_FACTOR.items():
        table = payload[table_name]["table"]
        key = pk_name(table)
        rows = con.execute(
            f"SELECT {q(key)}, metric_value, metric_ratio FROM {q(table_name)} ORDER BY {q(key)}"
        ).fetchall()
        params = []
        for row_key, value, ratio in rows:
            value = float(value or 0.0)
            new_value = r2(value * factor)
            new_delta = r2(new_value - value)
            new_ratio = (None if ratio is None else
                         round(min(max(float(ratio) * (1.0 + (factor - 1.0) * 0.6), 0.0), 1.0), 6))
            params.append((new_value, new_delta, new_ratio, "v2", ts, batch, row_key))
        con.execute("BEGIN")
        con.executemany(
            f"UPDATE {q(table_name)} SET metric_value=?, metric_delta=?, metric_ratio=?, "
            f"version_tag=?, updated_at=?, etl_batch_id=? WHERE {q(key)}=?",
            params,
        )
        con.execute("COMMIT")
        if table_name in AGG_V2_EXPR:
            con.execute(
                f"UPDATE {q(table_name)} SET calc_expr=? WHERE {q(key)} <= ?",
                (AGG_V2_EXPR[table_name], 30),
            )

    # 5) 结构变更写回日志表：记录“表数 60->62”“字段数 20->21”
    con.execute("BEGIN")
    con.executemany(
        f"UPDATE {q('log_schema_change')} SET event_type=?, object_id=?, before_value=?, "
        f"after_value=?, status=?, comment=?, updated_at=?, etl_batch_id=? "
        f"WHERE {q('schema_change_id')}=?",
        [
            ("add_table", 61, 60.0, 62.0, "success",
             "v2 结构变更：新增 dim_geo_rollup 与 agg_metric_recalibration。", ts, batch, 1),
            ("add_column", 9, 20.0, 21.0, "success",
             "v2 结构变更：fact_orders 增加 channel_caliber 列。", ts, batch, 2),
            ("add_column", 11, 20.0, 21.0, "success",
             "v2 结构变更：fact_sales_daily 增加 gmv_flag 列。", ts, batch, 3),
            ("add_column", 43, 20.0, 21.0, "success",
             "v2 结构变更：agg_daily_sales 增加 caliber_tag 列。", ts, batch, 4),
            ("caliber_change", 43, 1.0, 1.02, "success",
             "v2 口径变更：GMV 由不含税改为含税，汇总系数 1.02。", ts, batch, 5),
            ("caliber_change", 44, 1.0, 1.02, "success",
             "v2 口径变更：月 GMV 同步改为含税口径。", ts, batch, 6),
        ],
    )
    con.execute("COMMIT")


def _remove(path: Path) -> None:
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            p.unlink()


def materialize(base: Path, target: Path, apply, payload: dict[str, dict]) -> None:
    """从基准库字节复制出一份快照，应用增量后用 os.replace 原子替换。"""
    tmp = target.with_name(target.name + ".tmp")
    _remove(tmp)
    shutil.copyfile(base, tmp)
    if apply is not None:
        con = sqlite3.connect(str(tmp), isolation_level=None)
        try:
            con.execute("PRAGMA journal_mode=DELETE")
            con.execute("PRAGMA synchronous=OFF")
            apply(con, payload)
        finally:
            con.close()
    os.replace(tmp, target)


def snapshot_record(path: Path) -> dict:
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {n: con.execute(f"SELECT COUNT(*) FROM {q(n)}").fetchone()[0] for n in names}
    finally:
        con.close()
    return {"sha256": io.sha256_file(path), "rows_total": sum(counts.values()),
            "tables": counts}


def main() -> int:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    tables = gen_schema.load_tables()
    agg_source = _agg_source()
    payload = generate_all(tables, agg_source)
    _selfcheck(payload, tables)

    v1_order = [t["name"] for t in tables if t["name"] in V1_TABLES]

    base = SNAPSHOT_DIR / ".base.sqlite"
    build_base(base, tables, payload)

    records = {}
    materialize(base, SNAPSHOT_DIR / "v0.sqlite", None, payload)
    materialize(base, SNAPSHOT_DIR / "v1.sqlite",
                lambda con, p: apply_v1(con, p, v1_order), payload)
    materialize(base, SNAPSHOT_DIR / "v2.sqlite",
                lambda con, p: (apply_v1(con, p, v1_order), apply_v2(con, p)), payload)
    _remove(base)

    for snap in ("v0", "v1", "v2"):
        path = SNAPSHOT_DIR / f"{snap}.sqlite"
        records[snap] = snapshot_record(path)
        print(f"[build] {snap}: {records[snap]['rows_total']} 行, "
              f"{len(records[snap]['tables'])} 表, sha256={records[snap]['sha256'][:16]}…")
    io.write_json(HASHES_JSON, records)

    try:
        import manifest  # noqa: PLC0415  延迟导入，避免循环依赖
        manifest.write_manifest()
    except Exception as exc:  # noqa: BLE001  构建主体成功即可，MANIFEST 可单独重跑
        print(f"[build] MANIFEST 未刷新：{type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

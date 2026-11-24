-- 由 dataset/db/gen_schema.py 从 dataset/contracts/tables.json 生成，请勿手改。
-- 表数 60，字段数 1200。
-- 字段名、顺序、类型、主键、非空约束与目录一一对应；类型仅用 INTEGER / REAL / TEXT。

-- t01 dim_date kind=dim rows=400
CREATE TABLE "dim_date" (
  "date_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("date_id")
);

-- t02 dim_region kind=dim rows=400
CREATE TABLE "dim_region" (
  "region_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("region_id")
);

-- t03 dim_channel kind=dim rows=400
CREATE TABLE "dim_channel" (
  "channel_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("channel_id")
);

-- t04 dim_customer kind=dim rows=400
CREATE TABLE "dim_customer" (
  "customer_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("customer_id")
);

-- t05 dim_product kind=dim rows=400
CREATE TABLE "dim_product" (
  "product_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("product_id")
);

-- t06 dim_store kind=dim rows=400
CREATE TABLE "dim_store" (
  "store_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("store_id")
);

-- t07 dim_employee kind=dim rows=400
CREATE TABLE "dim_employee" (
  "employee_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("employee_id")
);

-- t08 dim_promotion kind=dim rows=400
CREATE TABLE "dim_promotion" (
  "promotion_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "name" TEXT,
  "code" TEXT,
  "short_name" TEXT,
  "category" TEXT,
  "status" TEXT,
  "valid_from" TEXT,
  "valid_to" TEXT,
  "region_code" TEXT,
  "channel_code" TEXT,
  "owner" TEXT,
  "description" TEXT,
  "level" TEXT,
  "parent_id" INTEGER,
  "sort_order" TEXT,
  "is_active" INTEGER,
  "ext_attr" TEXT,
  PRIMARY KEY ("promotion_id")
);

-- t09 fact_orders kind=fact rows=1200
CREATE TABLE "fact_orders" (
  "orders_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("orders_id")
);

-- t10 fact_order_item kind=fact rows=1200
CREATE TABLE "fact_order_item" (
  "order_item_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("order_item_id")
);

-- t11 fact_sales_daily kind=fact rows=1200
CREATE TABLE "fact_sales_daily" (
  "sales_daily_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("sales_daily_id")
);

-- t12 fact_returns kind=fact rows=1200
CREATE TABLE "fact_returns" (
  "returns_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("returns_id")
);

-- t13 fact_refunds kind=fact rows=1200
CREATE TABLE "fact_refunds" (
  "refunds_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("refunds_id")
);

-- t14 fact_payments kind=fact rows=1200
CREATE TABLE "fact_payments" (
  "payments_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("payments_id")
);

-- t15 fact_invoices kind=fact rows=1200
CREATE TABLE "fact_invoices" (
  "invoices_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("invoices_id")
);

-- t16 fact_shipments kind=fact rows=1200
CREATE TABLE "fact_shipments" (
  "shipments_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("shipments_id")
);

-- t17 fact_deliveries kind=fact rows=1200
CREATE TABLE "fact_deliveries" (
  "deliveries_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("deliveries_id")
);

-- t18 fact_inventory kind=fact rows=1200
CREATE TABLE "fact_inventory" (
  "inventory_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("inventory_id")
);

-- t19 fact_inventory_snapshot kind=fact rows=1200
CREATE TABLE "fact_inventory_snapshot" (
  "inventory_snapshot_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("inventory_snapshot_id")
);

-- t20 fact_stock_move kind=fact rows=1200
CREATE TABLE "fact_stock_move" (
  "stock_move_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("stock_move_id")
);

-- t21 fact_price_change kind=fact rows=1200
CREATE TABLE "fact_price_change" (
  "price_change_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("price_change_id")
);

-- t22 fact_promotion_apply kind=fact rows=1200
CREATE TABLE "fact_promotion_apply" (
  "promotion_apply_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("promotion_apply_id")
);

-- t23 fact_campaign_touch kind=fact rows=1200
CREATE TABLE "fact_campaign_touch" (
  "campaign_touch_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("campaign_touch_id")
);

-- t24 fact_clicks kind=fact rows=1200
CREATE TABLE "fact_clicks" (
  "clicks_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("clicks_id")
);

-- t25 fact_sessions kind=fact rows=1200
CREATE TABLE "fact_sessions" (
  "sessions_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("sessions_id")
);

-- t26 fact_leads kind=fact rows=1200
CREATE TABLE "fact_leads" (
  "leads_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("leads_id")
);

-- t27 fact_quotes kind=fact rows=1200
CREATE TABLE "fact_quotes" (
  "quotes_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("quotes_id")
);

-- t28 fact_contracts kind=fact rows=1200
CREATE TABLE "fact_contracts" (
  "contracts_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("contracts_id")
);

-- t29 fact_subscriptions kind=fact rows=1200
CREATE TABLE "fact_subscriptions" (
  "subscriptions_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("subscriptions_id")
);

-- t30 fact_renewals kind=fact rows=1200
CREATE TABLE "fact_renewals" (
  "renewals_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("renewals_id")
);

-- t31 fact_churn kind=fact rows=1200
CREATE TABLE "fact_churn" (
  "churn_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("churn_id")
);

-- t32 fact_tickets kind=fact rows=1200
CREATE TABLE "fact_tickets" (
  "tickets_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("tickets_id")
);

-- t33 fact_sla_events kind=fact rows=1200
CREATE TABLE "fact_sla_events" (
  "sla_events_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("sla_events_id")
);

-- t34 fact_usage kind=fact rows=1200
CREATE TABLE "fact_usage" (
  "usage_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("usage_id")
);

-- t35 fact_engagement kind=fact rows=1200
CREATE TABLE "fact_engagement" (
  "engagement_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("engagement_id")
);

-- t36 fact_budget kind=fact rows=1200
CREATE TABLE "fact_budget" (
  "budget_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("budget_id")
);

-- t37 fact_targets kind=fact rows=1200
CREATE TABLE "fact_targets" (
  "targets_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("targets_id")
);

-- t38 fact_forecast kind=fact rows=1200
CREATE TABLE "fact_forecast" (
  "forecast_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("forecast_id")
);

-- t39 fact_collections kind=fact rows=1200
CREATE TABLE "fact_collections" (
  "collections_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("collections_id")
);

-- t40 fact_supplier_orders kind=fact rows=1200
CREATE TABLE "fact_supplier_orders" (
  "supplier_orders_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("supplier_orders_id")
);

-- t41 fact_quality_checks kind=fact rows=1200
CREATE TABLE "fact_quality_checks" (
  "quality_checks_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("quality_checks_id")
);

-- t42 fact_costs kind=fact rows=1200
CREATE TABLE "fact_costs" (
  "costs_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "quantity" REAL,
  "amount" REAL,
  "gross_amount" REAL,
  "net_amount" REAL,
  "discount_amount" REAL,
  "tax_amount" REAL,
  "unit_price" REAL,
  "cost_amount" REAL,
  "currency_code" TEXT NOT NULL,
  "order_no" TEXT,
  "customer_key" INTEGER,
  "product_key" INTEGER,
  "store_key" INTEGER,
  "channel_key" INTEGER,
  "status_code" TEXT,
  "is_deleted" INTEGER,
  PRIMARY KEY ("costs_id")
);

-- t43 agg_daily_sales kind=agg rows=120
CREATE TABLE "agg_daily_sales" (
  "daily_sales_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("daily_sales_id")
);

-- t44 agg_monthly_gmv kind=agg rows=120
CREATE TABLE "agg_monthly_gmv" (
  "monthly_gmv_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("monthly_gmv_id")
);

-- t45 agg_region_share kind=agg rows=120
CREATE TABLE "agg_region_share" (
  "region_share_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("region_share_id")
);

-- t46 agg_channel_mix kind=agg rows=120
CREATE TABLE "agg_channel_mix" (
  "channel_mix_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("channel_mix_id")
);

-- t47 agg_product_rank kind=agg rows=120
CREATE TABLE "agg_product_rank" (
  "product_rank_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("product_rank_id")
);

-- t48 agg_customer_ltv kind=agg rows=120
CREATE TABLE "agg_customer_ltv" (
  "customer_ltv_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("customer_ltv_id")
);

-- t49 agg_cohort_retention kind=agg rows=120
CREATE TABLE "agg_cohort_retention" (
  "cohort_retention_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("cohort_retention_id")
);

-- t50 agg_funnel kind=agg rows=120
CREATE TABLE "agg_funnel" (
  "funnel_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("funnel_id")
);

-- t51 agg_sla_summary kind=agg rows=120
CREATE TABLE "agg_sla_summary" (
  "sla_summary_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("sla_summary_id")
);

-- t52 agg_cost_breakdown kind=agg rows=120
CREATE TABLE "agg_cost_breakdown" (
  "cost_breakdown_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("cost_breakdown_id")
);

-- t53 agg_forecast_error kind=agg rows=120
CREATE TABLE "agg_forecast_error" (
  "forecast_error_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("forecast_error_id")
);

-- t54 agg_inventory_turnover kind=agg rows=120
CREATE TABLE "agg_inventory_turnover" (
  "inventory_turnover_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "metric_value" REAL,
  "metric_delta" REAL,
  "metric_ratio" REAL,
  "window_start" TEXT,
  "window_end" TEXT,
  "dimension_key" INTEGER,
  "sample_size" REAL,
  "is_partial" INTEGER,
  "version_tag" TEXT,
  "source_table" TEXT,
  "calc_expr" TEXT,
  "owner" TEXT,
  "refresh_mode" TEXT,
  "unit_label" TEXT,
  "rounding" TEXT,
  "comment" TEXT,
  PRIMARY KEY ("inventory_turnover_id")
);

-- t55 log_query_audit kind=log rows=600
CREATE TABLE "log_query_audit" (
  "query_audit_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "event_type" TEXT,
  "actor" TEXT,
  "object_id" INTEGER,
  "before_value" REAL,
  "after_value" REAL,
  "duration_ms" REAL,
  "status" TEXT,
  "error_code" TEXT,
  "statement_hash" TEXT,
  "ip_hash" TEXT,
  "user_agent" TEXT,
  "trace_id" INTEGER,
  "span_id" INTEGER,
  "payload_size" REAL,
  "retry_count" INTEGER,
  "comment" TEXT,
  PRIMARY KEY ("query_audit_id")
);

-- t56 log_etl_run kind=log rows=600
CREATE TABLE "log_etl_run" (
  "etl_run_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "event_type" TEXT,
  "actor" TEXT,
  "object_id" INTEGER,
  "before_value" REAL,
  "after_value" REAL,
  "duration_ms" REAL,
  "status" TEXT,
  "error_code" TEXT,
  "statement_hash" TEXT,
  "ip_hash" TEXT,
  "user_agent" TEXT,
  "trace_id" INTEGER,
  "span_id" INTEGER,
  "payload_size" REAL,
  "retry_count" INTEGER,
  "comment" TEXT,
  PRIMARY KEY ("etl_run_id")
);

-- t57 log_access kind=log rows=600
CREATE TABLE "log_access" (
  "access_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "event_type" TEXT,
  "actor" TEXT,
  "object_id" INTEGER,
  "before_value" REAL,
  "after_value" REAL,
  "duration_ms" REAL,
  "status" TEXT,
  "error_code" TEXT,
  "statement_hash" TEXT,
  "ip_hash" TEXT,
  "user_agent" TEXT,
  "trace_id" INTEGER,
  "span_id" INTEGER,
  "payload_size" REAL,
  "retry_count" INTEGER,
  "comment" TEXT,
  PRIMARY KEY ("access_id")
);

-- t58 log_metric_change kind=log rows=600
CREATE TABLE "log_metric_change" (
  "metric_change_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "event_type" TEXT,
  "actor" TEXT,
  "object_id" INTEGER,
  "before_value" REAL,
  "after_value" REAL,
  "duration_ms" REAL,
  "status" TEXT,
  "error_code" TEXT,
  "statement_hash" TEXT,
  "ip_hash" TEXT,
  "user_agent" TEXT,
  "trace_id" INTEGER,
  "span_id" INTEGER,
  "payload_size" REAL,
  "retry_count" INTEGER,
  "comment" TEXT,
  PRIMARY KEY ("metric_change_id")
);

-- t59 log_schema_change kind=log rows=600
CREATE TABLE "log_schema_change" (
  "schema_change_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "event_type" TEXT,
  "actor" TEXT,
  "object_id" INTEGER,
  "before_value" REAL,
  "after_value" REAL,
  "duration_ms" REAL,
  "status" TEXT,
  "error_code" TEXT,
  "statement_hash" TEXT,
  "ip_hash" TEXT,
  "user_agent" TEXT,
  "trace_id" INTEGER,
  "span_id" INTEGER,
  "payload_size" REAL,
  "retry_count" INTEGER,
  "comment" TEXT,
  PRIMARY KEY ("schema_change_id")
);

-- t60 log_backfill kind=log rows=600
CREATE TABLE "log_backfill" (
  "backfill_id" INTEGER NOT NULL,
  "date_key" INTEGER NOT NULL,
  "updated_at" TEXT NOT NULL,
  "etl_batch_id" TEXT,
  "event_type" TEXT,
  "actor" TEXT,
  "object_id" INTEGER,
  "before_value" REAL,
  "after_value" REAL,
  "duration_ms" REAL,
  "status" TEXT,
  "error_code" TEXT,
  "statement_hash" TEXT,
  "ip_hash" TEXT,
  "user_agent" TEXT,
  "trace_id" INTEGER,
  "span_id" INTEGER,
  "payload_size" REAL,
  "retry_count" INTEGER,
  "comment" TEXT,
  PRIMARY KEY ("backfill_id")
);

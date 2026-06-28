-- ============================================================
-- Hive SQL 面试题：聚合与分组
-- ============================================================

-- 建表：销售明细表
DROP TABLE IF EXISTS sales_detail;
CREATE TABLE sales_detail (
    sale_id     STRING        COMMENT '销售ID',
    product     STRING        COMMENT '商品名称',
    category    STRING        COMMENT '商品类别',
    salesman    STRING        COMMENT '销售员',
    region      STRING        COMMENT '区域',
    sale_amount DECIMAL(10,2) COMMENT '销售额',
    sale_date   STRING        COMMENT '销售日期'
) COMMENT '销售明细表';

INSERT INTO sales_detail VALUES
    ('S001', '手机A',   '电子产品', '张三', '华东', 5999.00, '2024-01-05'),
    ('S002', '手机B',   '电子产品', '李四', '华南', 4999.00, '2024-01-10'),
    ('S003', '电脑A',   '电子产品', '张三', '华东', 8999.00, '2024-01-15'),
    ('S004', '电脑B',   '电子产品', '王五', '华北', 7999.00, '2024-02-01'),
    ('S005', '显示器',  '电子产品', '李四', '华南', 1499.00, '2024-02-10'),
    ('S006', '办公椅',  '办公用品', '张三', '华东',  899.00, '2024-02-15'),
    ('S007', '办公桌',  '办公用品', '王五', '华北', 1999.00, '2024-03-01'),
    ('S008', '台灯',    '办公用品', '李四', '华南',  199.00, '2024-03-10'),
    ('S009', '键盘',    '电子产品', '赵六', '华东',  399.00, '2024-03-15'),
    ('S010', '鼠标',    '电子产品', '赵六', '华北',   89.00, '2024-03-20'),
    ('S011', '手机A',   '电子产品', '张三', '华东', 5999.00, '2024-04-01'),
    ('S012', '电脑A',   '电子产品', '李四', '华南', 8999.00, '2024-04-10'),
    ('S013', '文件柜',  '办公用品', '王五', '华北', 1299.00, '2024-04-15'),
    ('S014', '办公椅',  '办公用品', '赵六', '华东',  899.00, '2024-05-01'),
    ('S015', '打印机',  '办公用品', '张三', '华东', 2499.00, '2024-05-10');

-- ============================================================
-- 题目 1：按类别统计销售额汇总
-- 要求：按商品类别分组，统计各类别的总销售额和销售笔数
-- 期望列：类别、总销售额、销售笔数
-- ============================================================
SELECT
    category,
    SUM(sale_amount) AS total_sales_amount,
    COUNT(*)         AS total_sales_count
FROM sales_detail
GROUP BY category;

-- [评价] ✅ 正确。
-- 1. GROUP BY category 按类别分组，SUM 求和，COUNT(*) 统计笔数，逻辑正确。
-- 2. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 2：按区域和类别统计销售额
-- 要求：按区域和商品类别两个维度分组，统计总销售额
-- 期望列：区域、类别、总销售额
-- ============================================================
SELECT
    region,
    category,
    SUM(sale_amount) AS total_sales_amount
FROM sales_detail
GROUP BY region, category;

-- [评价] ✅ 正确。
-- 1. GROUP BY region, category 按两个维度分组，逻辑正确。
-- 2. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 3：销售额超过5000的销售员及其总销售额
-- 要求：计算每个销售员的总销售额，只显示总销售额超过5000的
-- 期望列：销售员、总销售额
-- ============================================================
SELECT
    salesman,
    SUM(sale_amount) AS total_sales_amount
FROM sales_detail
GROUP BY salesman
HAVING SUM(sale_amount) > 5000;

-- [评价] ✅ 正确。
-- 1. GROUP BY 按销售员聚合，HAVING 对聚合后结果过滤，逻辑正确。
-- 2. 注意：HAVING 是在 GROUP BY 之后过滤，WHERE 是在 GROUP BY 之前过滤，此处用法正确。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 4：找出销售额最高的商品（TOP 3）
-- 要求：按商品分组统计总销售额，取销售额最高的前3个商品
-- 期望列：商品、总销售额
-- ============================================================
WITH ranked_total_sales_amount AS (
    SELECT
        product,
        SUM(sale_amount)                                AS total_sales_amount,
        ROW_NUMBER() OVER (ORDER BY SUM(sale_amount) DESC) AS total_sales_amount_rank
    FROM sales_detail
    GROUP BY product
)
SELECT
    product,
    total_sales_amount
FROM ranked_total_sales_amount
WHERE total_sales_amount_rank <= 3;

select product, sum(sale_amount) as total_sales_amount from sales_detail group by product order by total_sales_amount desc limit 3;

-- [评价] ✅ 正确。
-- 1. CTE 中先 GROUP BY 按商品聚合，再用 ROW_NUMBER 按总销售额降序排名，最后筛选前3名，逻辑正确。
-- 2. 注意：ROW_NUMBER 在总销售额相同时会随机分配排名，若希望并列则需改用 RANK 或 DENSE_RANK。
--    本题没有并列情况（数据不重复），所以结果正确。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 5：每个区域中销售额最高的销售员
-- 要求：在每个区域内，找出销售额最高的销售员
-- 期望列：区域、销售员、总销售额
-- 提示：使用窗口函数 ROW_NUMBER() 或 RANK() 配合子查询
-- ============================================================
WITH region_salesman_amount_agg AS (
    SELECT
        salesman,
        region,
        SUM(sale_amount) AS total_region_salesman_amount
    FROM sales_detail
    GROUP BY salesman, region
),
ranked_region_salesman_amount_agg AS (
    SELECT
        salesman,
        region,
        total_region_salesman_amount,
        ROW_NUMBER() OVER (
            PARTITION BY region
            ORDER BY total_region_salesman_amount DESC
        ) AS rn
    FROM region_salesman_amount_agg
)
SELECT
    salesman,
    region,
    total_region_salesman_amount
FROM ranked_region_salesman_amount_agg
WHERE rn = 1;

with ranked_region_salesman_amount_agg as (
    select salesman, region, sum(sale_amount) as total_region_salesman_amount, row_number() over (partition by region order by sum(sale_amount) desc) as rn from sales_detail group by salesman, region
)
select salesman, region, total_region_salesman_amount from ranked_region_salesman_amount_agg where rn = 1;

-- [评价] ✅ 正确（存在一个拼写小问题已修正）。
-- 1. 思路清晰：先按销售员+区域聚合求总额，再用 ROW_NUMBER 分区排名取第一名，逻辑正确。
-- 2. 原题解中第二个 CTE 的别名写成了 `ranked_region_salesman_amont_agg`（amount 少了一个 u），
--    且引用了 `region_salesman_amount_agg` 中的 `total_region_salesman_amount`。
--    拼写已修正为 `amount`。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 6：统计每个月的销售额及环比增长率
-- 要求：按月统计销售额，并计算环比增长率
--       （环比增长率 = (当月-上月) / 上月 * 100%）
-- 期望列：月份、销售额、上月销售额、环比增长率(%)
-- 提示：使用 LAG 窗口函数
-- ============================================================
WITH monthly_total_sales_amount AS (
    SELECT
        SUBSTR(sale_date, 1, 7)    AS sale_year_month,
        SUM(sale_amount)            AS monthly_sales_amount
    FROM sales_detail
    GROUP BY SUBSTR(sale_date, 1, 7)
),
monthly_total_sales_amount_with_preceding AS (
    SELECT
        sale_year_month,
        monthly_sales_amount,
        LAG(monthly_sales_amount) OVER (ORDER BY sale_year_month) AS preceding_month_sales_amount
    FROM monthly_total_sales_amount
)
SELECT
    sale_year_month,
    monthly_sales_amount,
    preceding_month_sales_amount,
    CASE
    -- * 注意这里的判断也要用 IS NULL 而不能直接写一个 NULL
        WHEN preceding_month_sales_amount IS NULL THEN NULL
        WHEN preceding_month_sales_amount = 0   THEN NULL
        ELSE ROUND(
            (monthly_sales_amount - preceding_month_sales_amount)
            / preceding_month_sales_amount * 100,
            2
        )
    END AS monthly_growth_rate
FROM monthly_total_sales_amount_with_preceding;

-- [评价] ❌ 原题解的 CASE WHEN 写法有严重错误，已修正。
-- 1. ✅ 整体思路正确：SUBSTR 提取年月 -> CTE 按月聚合 -> LAG 取上月值 -> 计算环比。
-- 2. ❌ 原题解：CASE preceding_month_sales_amount WHEN NULL THEN 0 是错误的。
--    在 Hive（及标准 SQL）中，CASE 简单表达式（case col when null）无法正确判断 NULL，
--    NULL 必须用 CASE WHEN col IS NULL 的搜索表达式来判断。原写法会导致 WHEN NULL 永远
--    不成立，preceding_month_sales_amount 为 NULL 时直接进入 ELSE 分支，因除 NULL 而报错。
-- 3. ❌ 原题解中 WHEN 0 THEN 0 的分支也不会被触发，因为首月的 preceding 值是 NULL 而非 0。
-- 4. ✅ 修正后：首月无上月数据返回 NULL，上月为 0 时返回 NULL（避免除零），
--    正常情况保留 2 位小数。
-- 5. 修正后的输出列与期望列完全匹配。但需要说明环比增长率的处理方式可以有不同的业务约定：
--    - 上月为 NULL（首月）-> NULL（无可比数据）
--    - 上月为 0 -> NULL（分母为 0，无穷大无意义）
--    也可以约定首月环比为 0 或直接保留 NULL，取决于业务需求。
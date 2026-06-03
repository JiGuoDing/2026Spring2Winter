-- =====================================================
-- 文件名：08_窗口函数.sql ⭐ 大数据岗位面试必考
-- 难度：★★★★☆
-- 前置知识：03_聚合函数与分组, 05_JOIN连接
-- 学习时间：约 75 分钟
-- 对应面试考点：排名、TopN、累计求和、移动平均、同比环比、LAG/LEAD
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 8.0 窗口函数 vs 聚合函数：核心区别
-- ---------------------------------------------------
-- 聚合函数（GROUP BY）：将多行折叠为一行，丢失明细
-- 窗口函数（OVER）：保留每行明细，同时计算聚合值

-- 聚合函数：只能看到每类一个总数
SELECT category_id, AVG(price) AS 均价 FROM products
WHERE category_id IS NOT NULL GROUP BY category_id;

-- 窗口函数：每行都能看到自己 + 本类均价
SELECT
    name,
    category_id,
    price,
    AVG(price) OVER (PARTITION BY category_id) AS 本类均价,
    price - AVG(price) OVER (PARTITION BY category_id) AS 与均价差值
FROM products
WHERE category_id IS NOT NULL
ORDER BY category_id, price DESC
LIMIT 10;

-- ---------------------------------------------------
-- 8.1 OVER() 子句结构
-- ---------------------------------------------------
-- OVER([PARTITION BY 列] [ORDER BY 列] [ROWS/RANGE 子句])
-- PARTITION BY：分组（类似 GROUP BY 但不合并行）
-- ORDER BY：    组内排序（决定窗口函数的计算顺序）
-- Frame：       指定窗口范围

-- ---------------------------------------------------
-- 8.2 排名函数
-- ---------------------------------------------------

-- ROW_NUMBER()：唯一行号（并列也递增 1,2,3,4...）
SELECT
    ROW_NUMBER() OVER (ORDER BY price DESC) AS 排名,
    name,
    price
FROM products
LIMIT 10;

-- RANK()：有间隔排名（同值同排名，下一名跳号 1,1,3...）
SELECT
    RANK() OVER (ORDER BY price DESC) AS 排名,
    name,
    price
FROM products
LIMIT 10;

-- DENSE_RANK()：无间隔排名（同值同排名，下一名不跳号 1,1,2...）
SELECT
    DENSE_RANK() OVER (ORDER BY price DESC) AS 排名,
    name,
    price
FROM products
LIMIT 10;

-- 分组排名：每个分类内按价格排名（PARTITION BY）
SELECT
    RANK() OVER (PARTITION BY category_id ORDER BY price DESC) AS 类内排名,
    category_id,
    name,
    price
FROM products
WHERE category_id IS NOT NULL
ORDER BY category_id, 类内排名
LIMIT 15;

-- NTILE(n)：分成 n 组，返回组号（常用于分位数分析）
SELECT
    name,
    price,
    NTILE(4) OVER (ORDER BY price DESC) AS 价格四分位
FROM products;

-- ---------------------------------------------------
-- 8.3 偏移函数 — LAG / LEAD ⭐ 同比环比利器
-- ---------------------------------------------------
-- LAG(column, offset, default)：向上取（前面的行）
-- LEAD(column, offset, default)：向下取（后面的行）
-- offset 默认 1，default 是超出范围时的默认值

-- 查每个客户订单日期及上一单日期
SELECT
    customer_id,
    order_date,
    total_amount,
    LAG(order_date)   OVER (PARTITION BY customer_id ORDER BY order_date) AS 上一单日期,
    LAG(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date) AS 上一单金额,
    DATEDIFF(order_date, LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)) AS 距上单天数
FROM orders
ORDER BY customer_id, order_date
LIMIT 20;

-- 环比增长：当前订单金额比上一单增长了%？
SELECT
    customer_id,
    order_date,
    total_amount,
    LAG(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date) AS prev_amount,
    ROUND(
        (total_amount - LAG(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date))
        / LAG(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date) * 100,
        2
    ) AS 环比增长率
FROM orders
WHERE total_amount > 0
ORDER BY customer_id, order_date
LIMIT 20;

-- LEAD：查下一单信息
SELECT
    customer_id,
    order_date,
    total_amount,
    LEAD(order_date)   OVER (PARTITION BY customer_id ORDER BY order_date) AS 下一单日期,
    LEAD(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date) AS 下一单金额
FROM orders
ORDER BY customer_id, order_date
LIMIT 15;

-- ---------------------------------------------------
-- 8.4 取值函数
-- ---------------------------------------------------
-- FIRST_VALUE / LAST_VALUE / NTH_VALUE

-- 每个分类的最贵商品和最便宜商品名
SELECT
    category_id,
    name,
    price,
    FIRST_VALUE(name) OVER (PARTITION BY category_id ORDER BY price DESC) AS 最贵商品,
    FIRST_VALUE(price) OVER (PARTITION BY category_id ORDER BY price DESC) AS 最贵价格
FROM products
WHERE category_id IS NOT NULL
ORDER BY category_id, price DESC
LIMIT 15;

-- ⚠️ LAST_VALUE 的陷阱：默认窗口帧是 RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
-- 所以 LAST_VALUE 总是等于当前行！需要指定窗口帧范围：
SELECT
    category_id,
    name,
    price,
    LAST_VALUE(name) OVER (
        PARTITION BY category_id ORDER BY price
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS 最贵商品
FROM products
WHERE category_id IS NOT NULL
ORDER BY category_id, price
LIMIT 15;

-- ---------------------------------------------------
-- 8.5 聚合窗口函数 ⭐ 大数据场景最常用
-- ---------------------------------------------------
-- SUM/AVG/COUNT/MAX/MIN 也能作为窗口函数使用

-- 累计销售额（累计求和）
SELECT
    order_date,
    total_amount,
    SUM(total_amount) OVER (ORDER BY order_date) AS 累计销售额
FROM orders
WHERE status = 'delivered'
ORDER BY order_date
LIMIT 15;

-- 每个客户的累计消费
SELECT
    customer_id,
    order_date,
    total_amount,
    SUM(total_amount) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS 客户累计消费
FROM orders
ORDER BY customer_id, order_date
LIMIT 20;

-- 移动平均（最近3笔订单的平均金额）
SELECT
    customer_id,
    order_date,
    total_amount,
    ROUND(AVG(total_amount) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS 近3单移动平均
FROM orders
ORDER BY customer_id, order_date
LIMIT 20;

-- ---------------------------------------------------
-- 8.6 Frame 子句（窗口帧）⭐
-- ---------------------------------------------------
-- 格式：ROWS/RANGE BETWEEN start AND end
-- start：UNBOUNDED PRECEDING | n PRECEDING | CURRENT ROW
-- end：  CURRENT ROW | n FOLLOWING | UNBOUNDED FOLLOWING

-- ROWS：物理行（按行数计算）
-- RANGE：逻辑值（按 ORDER BY 列的值范围计算，同值视为同一范围）

-- 默认 Frame（无 ORDER BY）：所有行
-- 默认 Frame（有 ORDER BY）：RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW

-- 过去3行到当前行（含当前行，共4行）
SELECT
    order_date,
    total_amount,
    SUM(total_amount) OVER (ORDER BY order_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS 近4笔累计
FROM orders
WHERE status = 'delivered'
ORDER BY order_date
LIMIT 10;

-- 前1行 + 当前行 + 后1行（共3行窗口）
SELECT
    order_date,
    total_amount,
    AVG(total_amount) OVER (
        ORDER BY order_date
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) AS 三行移动均
FROM orders
WHERE status = 'delivered'
ORDER BY order_date
LIMIT 10;

-- ---------------------------------------------------
-- 8.7 TopN 每组前 N 名 ⭐ 面试高频模式
-- ---------------------------------------------------

-- 套路：ROW_NUMBER() + 子查询/CTE
-- 查询每个分类价格前 3 名的商品
SELECT * FROM (
    SELECT
        category_id,
        name,
        price,
        ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY price DESC) AS rn
    FROM products
    WHERE category_id IS NOT NULL
) AS ranked
WHERE rn <= 3
ORDER BY category_id, rn;

-- RANK() 版：并列第三名也都显示
SELECT * FROM (
    SELECT
        category_id,
        name,
        price,
        RANK() OVER (PARTITION BY category_id ORDER BY price DESC) AS rk
    FROM products
    WHERE category_id IS NOT NULL
) AS ranked
WHERE rk <= 3
ORDER BY category_id, rk;

-- 每个客户消费金额最高的订单
SELECT * FROM (
    SELECT
        customer_id,
        id AS order_id,
        total_amount,
        order_date,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total_amount DESC) AS rn
    FROM orders
) AS t
WHERE rn = 1
ORDER BY customer_id
LIMIT 10;

-- ---------------------------------------------------
-- 8.8 实战：RFM 分析（部分）
-- ---------------------------------------------------
-- 每个客户：首次购买日期、最近购买日期、购买次数、总消费

SELECT
    c.id,
    c.name,
    MIN(o.order_date) AS 首次购买,
    MAX(o.order_date) AS 最近购买,
    COUNT(o.id)       AS 购买次数,
    COALESCE(SUM(o.total_amount), 0) AS 总消费,
    DATEDIFF(CURDATE(), MAX(o.order_date)) AS 距今天数,
    -- 给客户分档
    CASE
        WHEN COUNT(o.id) >= 5 AND SUM(o.total_amount) >= 50000 THEN '高价值'
        WHEN COUNT(o.id) >= 3 THEN '中价值'
        WHEN COUNT(o.id) >= 1 THEN '低价值'
        ELSE '流失'
    END AS 客户价值
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY 总消费 DESC
LIMIT 10;

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：查询所有商品，用 ROW_NUMBER() 按价格降序编号
-- 你的代码：


-- 题2：查询每个分类中价格排名前 3 的商品（用 ROW_NUMBER + 子查询）
-- 你的代码：


-- 题3：查询每个客户订单的环比增长率（用 LAG）
-- 提示：(current - prev) / prev * 100
-- 你的代码：


-- 题4：查询订单的累计销售额（按日期排序的累计 SUM）
-- 你的代码：


-- 题5：查询最近 5 笔订单的移动平均金额（ROWS BETWEEN 4 PRECEDING AND CURRENT ROW）
-- 你的代码：


-- 题6：将商品按价格分为 5 个桶（NTILE(5)），统计每桶的商品数
-- 你的代码：


-- 题7：查每个客户第一笔订单和最后一笔订单的日期和金额（FIRST_VALUE + LAST_VALUE）
-- 你的代码：


-- 题8：查询每个客户订单中金额最高的一笔（ROW_NUMBER + rn=1）
-- 你的代码：


-- 题9：查询每种商品在其分类中的价格排名（RANK），只显示排名前 5 的
-- 你的代码：


-- 题10：计算每天销售额的 7 日移动平均
-- 提示：先按天汇总，再窗口函数 ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
-- 你的代码：


-- 题11：查询相邻两笔订单间隔超过 30 天的客户和订单
-- 提示：用 LAG 取上一单日期，计算差值
-- 你的代码：


-- 题12：查询"每个客户消费总额在全客户中的百分位排名"（PERCENT_RANK 或 CUME_DIST）
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: RANK() 和 DENSE_RANK() 和 ROW_NUMBER() 的区别？
-- A: ROW_NUMBER(): 唯一递增，并列也递增 (1,2,3,4)
--    RANK():       同值同排名，下一名跳号 (1,1,3,4)
--    DENSE_RANK(): 同值同排名，下一名连续 (1,1,2,3)
--    选择：要唯一行号用 ROW_NUMBER，要连续排名用 DENSE_RANK
--
-- Q: 窗口函数和 GROUP BY 的区别？
-- A: GROUP BY 折叠行（一行变一行），窗口函数保留行（每行都在）
--    窗口函数可以在不丢失明细的情况下计算分组聚合值
--    这是大数据场景下窗口函数如此重要的原因
--
-- Q: ROWS 和 RANGE 的区别？
-- A: ROWS 按物理行计算边界（行数）
--    RANGE 按逻辑值计算边界（ORDER BY 列的值）
--    当 ORDER BY 列有重复值时：
--      ROWS BETWEEN 1 PRECEDING AND CURRENT ROW → 总是 2 行
--      RANGE BETWEEN 1 PRECEDING AND CURRENT ROW → 可能更多行（同值全包括）
--    绝大多数场景用 ROWS
--
-- Q: 窗口函数为什么不能在 WHERE 中使用？
-- A: SQL 执行顺序：WHERE → 窗口函数 → SELECT
--    窗口函数在 WHERE 之后计算，所以 WHERE 看不到窗口函数的计算结果
--    需要用子查询/CTE：把窗口函数结果放在子查询中，外层 WHERE 过滤

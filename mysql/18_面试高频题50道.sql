-- =====================================================
-- 文件名：18_面试高频题50道.sql
-- 难度：★★ ~ ★★★★★（按难度分级）
-- 前置知识：全部前面章节
-- 学习时间：综合练习，按需刷题
-- =====================================================
-- 题目分级：
--   简单 (1-15)：  基础 CRUD、简单 JOIN、聚合统计
--   中等 (16-35)： 多表关联、复杂子查询、窗口函数、连续登录
--   困难 (36-50)： 复杂业务场景、性能优化、留存分析
-- 每道题包含：题目 → 测试数据 → 解题思路 → 参考答案 → 易错点
-- =====================================================

USE mysql_tutorial;

-- #######################################################
-- 简单难度（1-15）
-- #######################################################

-- -------------------------------------------------------
-- 题1：查询所有商品名称和价格，按价格从高到低排序
-- -------------------------------------------------------
-- 思路：直接 SELECT + ORDER BY DESC
SELECT name, price FROM products ORDER BY price DESC;

-- -------------------------------------------------------
-- 题2：查询 2024 年后注册的客户姓名和注册日期
-- -------------------------------------------------------
SELECT name, register_date FROM customers
WHERE register_date >= '2024-01-01'
ORDER BY register_date;

-- -------------------------------------------------------
-- 题3：查询每种状态的订单数量
-- -------------------------------------------------------
SELECT status, COUNT(*) AS cnt
FROM orders
GROUP BY status
ORDER BY cnt DESC;

-- -------------------------------------------------------
-- 题4：查询价格最贵的 5 件商品
-- -------------------------------------------------------
SELECT name, price FROM products
ORDER BY price DESC LIMIT 5;

-- -------------------------------------------------------
-- 题5：查询所有北京和上海的客户（用 IN）
-- -------------------------------------------------------
SELECT name, city FROM customers
WHERE city IN ('北京', '上海');

-- -------------------------------------------------------
-- 题6：查询所有邮箱为 NULL 的客户（IS NULL）
-- -------------------------------------------------------
SELECT name, phone FROM customers
WHERE email IS NULL;

-- -------------------------------------------------------
-- 题7：按城市统计客户数，按人数降序，取前 5
-- -------------------------------------------------------
SELECT city, COUNT(*) AS cnt
FROM customers
GROUP BY city
ORDER BY cnt DESC
LIMIT 5;

-- -------------------------------------------------------
-- 题8：查询所有商品以及它们的分类名称（INNER JOIN）
-- -------------------------------------------------------
SELECT p.name AS 商品, c.name AS 分类
FROM products p
INNER JOIN categories c ON p.category_id = c.id;

-- -------------------------------------------------------
-- 题9：查询每个月的订单数和总金额（按月份分组）
-- -------------------------------------------------------
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS 月份,
    COUNT(*) AS 订单数,
    SUM(total_amount) AS 总金额
FROM orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY 月份;

-- -------------------------------------------------------
-- 题10：查询价格高于平均价格的商品
-- -------------------------------------------------------
SELECT name, price FROM products
WHERE price > (SELECT AVG(price) FROM products)
ORDER BY price DESC;

-- -------------------------------------------------------
-- 题11：插入一条新商品记录
-- -------------------------------------------------------
-- INSERT INTO products (name, category_id, price, stock) VALUES ('新商品', 1, 199.00, 100);
-- SELECT * FROM products WHERE name = '新商品';
-- DELETE FROM products WHERE name = '新商品';  -- 清理

-- -------------------------------------------------------
-- 题12：将所有"智能手机"分类的商品打 9 折
-- -------------------------------------------------------
-- UPDATE products p
-- JOIN categories c ON p.category_id = c.id
-- SET p.price = p.price * 0.9
-- WHERE c.name = '智能手机';
-- SELECT name, price FROM products WHERE category_id = 11;

-- -------------------------------------------------------
-- 题13：删除所有未使用的供应商（没有商品的供应商）
-- -------------------------------------------------------
-- DELETE FROM suppliers
-- WHERE id NOT IN (SELECT DISTINCT supplier_id FROM products WHERE supplier_id IS NOT NULL);
-- 更安全的写法：用 NOT EXISTS

-- -------------------------------------------------------
-- 题14：查询每个商品分类的商品数量（含 0 个商品的分类）
-- -------------------------------------------------------
SELECT c.name, COUNT(p.id) AS 商品数
FROM categories c
LEFT JOIN products p ON c.id = p.category_id
GROUP BY c.id, c.name
ORDER BY 商品数 DESC;

-- -------------------------------------------------------
-- 题15：计算订单总金额的日同比（今天 vs 昨天，用子查询）
-- -------------------------------------------------------
-- 思路：先按日汇总，再关联前一天
SELECT
    DATE(order_date) AS 日期,
    SUM(total_amount) AS 日销售额
FROM orders
GROUP BY DATE(order_date)
ORDER BY 日期;

-- #######################################################
-- 中等难度（16-35）
-- #######################################################

-- -------------------------------------------------------
-- 题16：查询从未下过单的客户（LEFT JOIN + IS NULL）
-- -------------------------------------------------------
SELECT c.id, c.name, c.register_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.id IS NULL;

select c.id, c.name, c.register_date from customers c left join orders o on c.id = o.customer_id where o.id is null;

-- -------------------------------------------------------
-- 题17：查询消费总额 TOP 5 的客户姓名和消费总额
-- -------------------------------------------------------
SELECT c.name, SUM(o.total_amount) AS 总消费
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY 总消费 DESC
LIMIT 5;

select c.name, sum(o.total_amount) as 总消费 from customers as c join orders as o on o.customer_id = c.id group by c.id, c.name order by 总消费 desc limit 5;

-- -------------------------------------------------------
-- 题18：查询每个分类价格最高的商品（关联子查询）
-- -------------------------------------------------------
SELECT p.name, p.category_id, p.price
FROM products p
WHERE p.price = (
    SELECT MAX(price) FROM products
    WHERE category_id = p.category_id
)
AND p.category_id IS NOT NULL
ORDER BY p.category_id;

-- -------------------------------------------------------
-- 题19：查询同时购买了"华为 Mate 70 Pro"和"小米 15 Ultra"的客户
-- -------------------------------------------------------
SELECT c.name
FROM customers c
JOIN orders o ON c.id = o.customer_id
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE p.name IN ('华为 Mate 70 Pro', '小米 15 Ultra')
GROUP BY c.id, c.name
HAVING COUNT(DISTINCT p.id) = 2;



-- -------------------------------------------------------
-- 题20：用窗口函数查每个客户消费金额最高的订单
-- -------------------------------------------------------
SELECT * FROM (
    SELECT
        c.name,
        o.id AS order_id,
        o.total_amount,
        RANK() OVER (PARTITION BY o.customer_id ORDER BY o.total_amount DESC) AS rk
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
) t
WHERE rk = 1
LIMIT 10;

-- -------------------------------------------------------
-- 题21：查询每个客户的第一笔订单和最后一笔订单日期
-- -------------------------------------------------------
SELECT
    customer_id,
    MIN(order_date) AS 首单日期,
    MAX(order_date) AS 末单日期
FROM orders
GROUP BY customer_id;

-- -------------------------------------------------------
-- 题22：查询购买次数超过 5 次的客户
-- -------------------------------------------------------
SELECT c.name, COUNT(o.id) AS 购买次数
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
HAVING COUNT(o.id) > 5
ORDER BY 购买次数 DESC;

-- -------------------------------------------------------
-- 题23：查询商品销量 TOP 10（按订单明细中数量汇总）
-- -------------------------------------------------------
SELECT p.name, SUM(oi.quantity) AS 总销量
FROM products p
JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.id, p.name
ORDER BY 总销量 DESC
LIMIT 10;

-- -------------------------------------------------------
-- 题24：用 CASE WHEN 将订单状态转为中文显示
-- -------------------------------------------------------
SELECT
    id,
    status,
    CASE status
        WHEN 'pending'   THEN '待处理'
        WHEN 'paid'      THEN '已付款'
        WHEN 'shipped'   THEN '已发货'
        WHEN 'delivered' THEN '已签收'
        WHEN 'cancelled' THEN '已取消'
    END AS 状态中文
FROM orders
LIMIT 10;

-- -------------------------------------------------------
-- 题25：用 UNION ALL 查询价格最高3个和最低3个商品
-- -------------------------------------------------------
(SELECT name, price, '最贵' AS 类型 FROM products ORDER BY price DESC LIMIT 3)
UNION ALL
(SELECT name, price, '最便宜' FROM products ORDER BY price ASC LIMIT 3);

-- -------------------------------------------------------
-- 题26：查询每个城市客户的平均 VIP 等级（保留1位小数）
-- -------------------------------------------------------
SELECT city, ROUND(AVG(vip_level), 1) AS 平均VIP等级, COUNT(*) AS 人数
FROM customers
GROUP BY city
HAVING COUNT(*) >= 3
ORDER BY 平均VIP等级 DESC;

-- -------------------------------------------------------
-- 题27：查询"数码电子"分类的所有子分类（递归 CTE）
-- -------------------------------------------------------
WITH RECURSIVE cat_tree AS (
    SELECT id, name, parent_id, 1 AS lvl
    FROM categories WHERE name = '数码电子'
    UNION ALL
    SELECT c.id, c.name, c.parent_id, ct.lvl + 1
    FROM categories c
    JOIN cat_tree ct ON c.parent_id = ct.id
)
SELECT CONCAT(REPEAT('  ', lvl-1), name) AS 分类树 FROM cat_tree ORDER BY lvl, id;

-- -------------------------------------------------------
-- 题28：用 LAG 计算每个客户订单间隔天数
-- -------------------------------------------------------
SELECT
    customer_id,
    order_date,
    LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS 上一单,
    DATEDIFF(order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
    ) AS 间隔天数
FROM orders
ORDER BY customer_id, order_date
LIMIT 15;

-- -------------------------------------------------------
-- 题29：查询供应商及其供应的商品数量（含0个商品的供应商）
-- -------------------------------------------------------
SELECT s.name AS 供应商, COUNT(p.id) AS 商品数
FROM suppliers s
LEFT JOIN products p ON s.id = p.supplier_id
GROUP BY s.id, s.name
ORDER BY 商品数 DESC;

-- -------------------------------------------------------
-- 题30：查询月销售额超过 50000 的月份
-- -------------------------------------------------------
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS 月份,
    SUM(total_amount) AS 总销售额
FROM orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
HAVING SUM(total_amount) > 50000
ORDER BY 月份;

-- -------------------------------------------------------
-- 题31：用 EXISTS 查询至少有一笔"已签收"订单的客户
-- -------------------------------------------------------
SELECT name FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.id AND o.status = 'delivered'
);

-- -------------------------------------------------------
-- 题32：查询每种商品的售价与其分类均价的差值
-- -------------------------------------------------------
SELECT
    name,
    category_id,
    price,
    ROUND(AVG(price) OVER (PARTITION BY category_id), 2) AS 分类均价,
    ROUND(price - AVG(price) OVER (PARTITION BY category_id), 2) AS 与均价差
FROM products
WHERE category_id IS NOT NULL
ORDER BY category_id, price DESC;

-- -------------------------------------------------------
-- 题33：查询客户总数、有订单的客户数、下单率
-- -------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM customers) AS 总客户数,
    COUNT(DISTINCT customer_id) AS 有订单客户数,
    ROUND(COUNT(DISTINCT customer_id) * 100.0 / (SELECT COUNT(*) FROM customers), 2) AS 下单率
FROM orders;

-- -------------------------------------------------------
-- 题34：查询注册最早和注册最晚的客户信息
-- -------------------------------------------------------
(SELECT name, register_date, '最早' AS 类型 FROM customers
 ORDER BY register_date ASC LIMIT 1)
UNION ALL
(SELECT name, register_date, '最晚' FROM customers
 ORDER BY register_date DESC LIMIT 1);

-- -------------------------------------------------------
-- 题35：查询每个客户消费金额在全体的排名（窗口函数）
-- -------------------------------------------------------
SELECT
    c.name,
    SUM(o.total_amount) AS 总消费,
    RANK() OVER (ORDER BY SUM(o.total_amount) DESC) AS 消费排名
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
LIMIT 10;

-- #######################################################
-- 困难难度（36-50）
-- #######################################################

-- -------------------------------------------------------
-- 题36：连续登录问题 — 查出有连续3天以上下单记录的客户
-- -------------------------------------------------------
-- 思路：用 LAG 或 ROW_NUMBER 差值法
-- 核心原理：连续日期 - 连续行号 = 相同的值

WITH ordered AS (
    SELECT DISTINCT customer_id, DATE(order_date) AS order_date
    FROM orders
),
numbered AS (
    SELECT
        customer_id,
        order_date,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS rn
    FROM ordered
),
grouped AS (
    SELECT
        customer_id,
        DATE_SUB(order_date, INTERVAL rn DAY) AS grp,
        COUNT(*) AS consecutive_days
    FROM numbered
    GROUP BY customer_id, grp
    HAVING consecutive_days >= 3
)
SELECT DISTINCT c.name, g.consecutive_days AS 连续天数
FROM grouped g
JOIN customers c ON g.customer_id = c.id;

-- -------------------------------------------------------
-- 题37：查询累计销售额（窗口函数累计求和）
-- -------------------------------------------------------
SELECT
    DATE(order_date) AS 日期,
    SUM(total_amount) AS 日销售额,
    SUM(SUM(total_amount)) OVER (ORDER BY DATE(order_date)
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS 累计销售额
FROM orders
WHERE status = 'delivered'
GROUP BY DATE(order_date)
ORDER BY 日期;

-- -------------------------------------------------------
-- 题38：一条 SQL 删除重复数据，保留 ID 最小的那条
-- -------------------------------------------------------
-- 思路：找到重复数据的"要保留的 id"，删除其余
-- 场景：假设有重复邮箱的客户
-- 先查看重复数据：
SELECT email, COUNT(*), MIN(id) AS 保留ID
FROM customers
WHERE email IS NOT NULL
GROUP BY email
HAVING COUNT(*) > 1;

-- 删除方案（仅演示，不实际执行）：
-- DELETE c FROM customers c
-- JOIN (
--     SELECT email, MIN(id) AS keep_id
--     FROM customers
--     WHERE email IS NOT NULL
--     GROUP BY email
--     HAVING COUNT(*) > 1
-- ) keeper ON c.email = keeper.email
-- WHERE c.id > keeper.keep_id;

-- -------------------------------------------------------
-- 题39：计算用户留存率（次日留存）
-- -------------------------------------------------------
-- 思路：首日用户数 vs 次日仍活跃的用户数
WITH first_day AS (
    SELECT customer_id, MIN(DATE(order_date)) AS first_date
    FROM orders
    GROUP BY customer_id
),
retention AS (
    SELECT
        fd.first_date,
        COUNT(DISTINCT fd.customer_id) AS new_users,
        COUNT(DISTINCT CASE
            WHEN DATE(o.order_date) = DATE_ADD(fd.first_date, INTERVAL 1 DAY)
            THEN o.customer_id
        END) AS day1_retained
    FROM first_day fd
    LEFT JOIN orders o ON fd.customer_id = o.customer_id
    GROUP BY fd.first_date
)
SELECT
    first_date,
    new_users,
    day1_retained,
    ROUND(day1_retained * 100.0 / new_users, 2) AS 次日留存率
FROM retention
WHERE new_users > 0
ORDER BY first_date;

-- -------------------------------------------------------
-- 题40：查询"每个客户最后一笔订单"的详情
-- -------------------------------------------------------
SELECT * FROM (
    SELECT
        o.*,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
    FROM orders o
) t
WHERE rn = 1
LIMIT 10;

-- -------------------------------------------------------
-- 题41：行转列 — 按月统计各状态的订单数量
-- -------------------------------------------------------
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS 月份,
    SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS 已签收,
    SUM(CASE WHEN status = 'shipped'   THEN 1 ELSE 0 END) AS 运输中,
    SUM(CASE WHEN status = 'paid'      THEN 1 ELSE 0 END) AS 已付款,
    SUM(CASE WHEN status = 'pending'   THEN 1 ELSE 0 END) AS 待处理,
    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS 已取消
FROM orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY 月份;

-- -------------------------------------------------------
-- 题42：查询每个客户的最大消费间隔天数
-- -------------------------------------------------------
WITH gaps AS (
    SELECT
        customer_id,
        order_date,
        DATEDIFF(order_date,
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS gap_days
    FROM orders
)
SELECT c.name AS 客户, MAX(g.gap_days) AS 最大间隔天数
FROM gaps g
JOIN customers c ON g.customer_id = c.id
WHERE g.gap_days IS NOT NULL
GROUP BY g.customer_id, c.name
ORDER BY 最大间隔天数 DESC
LIMIT 10;

-- -------------------------------------------------------
-- 题43：查询"被所有 VIP=5 客户购买过的商品"
-- -------------------------------------------------------
-- 思路：用双重否定 — 不存在某个 VIP=5 客户没买过的商品
SELECT p.name
FROM products p
WHERE NOT EXISTS (
    SELECT 1 FROM customers c
    WHERE c.vip_level = 5
    AND NOT EXISTS (
        SELECT 1 FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE oi.product_id = p.id AND o.customer_id = c.id
    )
);

-- -------------------------------------------------------
-- 题44：用一条 SQL 查出中位数价格
-- -------------------------------------------------------
-- 思路：用窗口函数 + 子查询
WITH numbered AS (
    SELECT price,
           ROW_NUMBER() OVER (ORDER BY price) AS rn,
           COUNT(*) OVER () AS total
    FROM products
)
SELECT AVG(price) AS 中位数 FROM numbered
WHERE rn IN (FLOOR((total + 1) / 2), CEIL((total + 1) / 2));

-- -------------------------------------------------------
-- 题45：查询复购率（购买 >= 2 次的客户占比）
-- -------------------------------------------------------
SELECT
    ROUND(
        SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END) * 100.0
        / COUNT(*),
        2
    ) AS 复购率
FROM (
    SELECT customer_id, COUNT(*) AS order_count
    FROM orders
    GROUP BY customer_id
) t;

-- -------------------------------------------------------
-- 题46：用 EXPLAIN 分析慢查询并给出优化方案
-- -------------------------------------------------------
-- 问题查询：查某客户某时期内的已签收订单
EXPLAIN SELECT * FROM orders
WHERE customer_id = 5
  AND order_date >= '2024-01-01'
  AND status = 'delivered';
-- 优化方案：已有 idx_customer_date，覆盖 customer_id + order_date
-- 如果查询频繁加 status 过滤，需建 (customer_id, status, order_date) 复合索引

-- -------------------------------------------------------
-- 题47：查询日销售额的 7 日移动平均
-- -------------------------------------------------------
WITH daily AS (
    SELECT
        DATE(order_date) AS dt,
        SUM(total_amount) AS daily_total
    FROM orders
    GROUP BY DATE(order_date)
)
SELECT
    dt,
    daily_total,
    ROUND(AVG(daily_total) OVER (
        ORDER BY dt
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS ma_7day
FROM daily
ORDER BY dt;

-- -------------------------------------------------------
-- 题48：查询"连续 N 个月有消费的客户"
-- -------------------------------------------------------
-- 思路：先获取每个客户有消费的月份，再用差值法判断连续性
WITH monthly AS (
    SELECT DISTINCT
        customer_id,
        DATE_FORMAT(order_date, '%Y-%m') AS ym
    FROM orders
),
numbered AS (
    SELECT
        customer_id,
        ym,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY ym) AS rn
    FROM monthly
),
consecutive AS (
    SELECT
        customer_id,
        -- 以 ym 为基准减去 rn 个月 → 连续月份归到同一组
        DATE_SUB(CONCAT(ym, '-01'), INTERVAL rn MONTH) AS grp,
        COUNT(*) AS cnt
    FROM numbered
    GROUP BY customer_id, grp
    HAVING cnt >= 3  -- 连续3个月以上
)
SELECT DISTINCT c.name, con.cnt AS 连续月数
FROM consecutive con
JOIN customers c ON con.customer_id = c.id
ORDER BY 连续月数 DESC;

-- -------------------------------------------------------
-- 题49：用 CTE 实现"树形分类的完整路径"
-- -------------------------------------------------------
WITH RECURSIVE paths AS (
    SELECT id, name, parent_id, CAST(name AS CHAR(200)) AS path, 1 AS depth
    FROM categories
    WHERE parent_id IS NULL
    UNION ALL
    SELECT c.id, c.name, c.parent_id,
           CONCAT(p.path, ' > ', c.name),
           p.depth + 1
    FROM categories c
    JOIN paths p ON c.parent_id = p.id
)
SELECT path, depth FROM paths
WHERE depth <= 3
ORDER BY path;

-- -------------------------------------------------------
-- 题50：查询 GMV（总成交额）最高的那个月的 TOP5 客户
-- -------------------------------------------------------
-- 思路：先找到最高月份，再查该月份的客户排名
WITH month_gmv AS (
    SELECT
        DATE_FORMAT(order_date, '%Y-%m') AS ym,
        SUM(total_amount) AS gmv
    FROM orders
    WHERE status = 'delivered'
    GROUP BY DATE_FORMAT(order_date, '%Y-%m')
    ORDER BY gmv DESC
    LIMIT 1
),
top_customers AS (
    SELECT
        DATE_FORMAT(o.order_date, '%Y-%m') AS ym,
        c.name,
        SUM(o.total_amount) AS 消费额,
        RANK() OVER (PARTITION BY DATE_FORMAT(o.order_date, '%Y-%m')
                     ORDER BY SUM(o.total_amount) DESC) AS rk
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    WHERE o.status = 'delivered'
      AND DATE_FORMAT(o.order_date, '%Y-%m') = (SELECT ym FROM month_gmv)
    GROUP BY DATE_FORMAT(o.order_date, '%Y-%m'), c.id, c.name
)
SELECT ym AS 月份, name AS 客户, 消费额, rk AS 排名
FROM top_customers
WHERE rk <= 5
ORDER BY rk;

-- =====================================================
-- 附录：面试速查表
-- =====================================================
-- 1. 查没买过的 → LEFT JOIN + IS NULL / NOT EXISTS
-- 2. 每组 TOP N → ROW_NUMBER() OVER(PARTITION BY ... ORDER BY ...) + 外层 WHERE rn <= N
-- 3. 连续天数 → ROW_NUMBER 差值法（日期 - 序号 = 相同值 = 同一连续段）
-- 4. 累计求和 → SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING)
-- 5. 行列转换 → CASE WHEN + GROUP BY (行转列) / UNION ALL (列转行)
-- 6. 中位数 → ROW_NUMBER + COUNT(*) OVER() 定位中间行
-- 7. 删除重复 → GROUP BY + MIN(id) 确定保留行，JOIN 删除其余
-- 8. 树形结构 → 递归 CTE (WITH RECURSIVE)
-- 9. 保留率 → 先找首日，再 LEFT JOIN 次日，COUNT(DISTINCT) 计算
-- 10. EXPLAIN 重点 → type(至少range)、key(用了索引)、Extra(避免filesort/temporary)

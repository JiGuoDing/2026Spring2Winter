-- =====================================================
-- 09_CTE公共表达式 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：CTE 计算客户总消费 > 10000
WITH cust_spending AS (
    SELECT customer_id, SUM(total_amount) AS total_spent, COUNT(*) AS order_cnt
    FROM orders GROUP BY customer_id
)
SELECT c.name, cs.total_spent, cs.order_cnt
FROM cust_spending cs JOIN customers c ON cs.customer_id = c.id
WHERE cs.total_spent > 10000 ORDER BY cs.total_spent DESC;

-- 题2：CTE + 窗口函数 TOP 3
WITH ranked AS (
    SELECT category_id, name, price,
           ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY price DESC) AS rn
    FROM products WHERE category_id IS NOT NULL
)
SELECT * FROM ranked WHERE rn <= 3 ORDER BY category_id, rn;

-- 题3：生成2024年6月每一天
WITH RECURSIVE june_dates AS (
    SELECT '2024-06-01' AS dt
    UNION ALL
    SELECT DATE_ADD(dt, INTERVAL 1 DAY) FROM june_dates WHERE dt < '2024-06-30'
)
SELECT * FROM june_dates;

-- 题4：服装鞋帽的所有子分类
WITH RECURSIVE sub AS (
    SELECT id, name, parent_id, 1 AS lvl FROM categories WHERE name = '服装鞋帽'
    UNION ALL
    SELECT c.id, c.name, c.parent_id, sub.lvl + 1
    FROM categories c JOIN sub ON c.parent_id = sub.id
)
SELECT CONCAT(REPEAT('  ', lvl-1), name) AS 分类 FROM sub ORDER BY lvl, id;

-- 题5：某商品的完整分类路径（查"智能手机"向上的路径）
WITH RECURSIVE path AS (
    SELECT id, name, parent_id, CAST(name AS CHAR(200)) AS full_path
    FROM categories WHERE name = '智能手机'
    UNION ALL
    SELECT c.id, c.name, c.parent_id, CONCAT(c.name, ' > ', p.full_path)
    FROM categories c JOIN path p ON c.id = p.parent_id
)
SELECT full_path FROM path ORDER BY id;

-- 题6：多CTE — 客户消费 → 城市排名
WITH
cust AS (
    SELECT c.city, c.name, SUM(o.total_amount) AS total
    FROM customers c JOIN orders o ON c.id = o.customer_id
    GROUP BY c.id, c.city, c.name
),
city_rank AS (
    SELECT city, name, total,
           RANK() OVER (PARTITION BY city ORDER BY total DESC) AS rk
    FROM cust
)
SELECT city, name, total, rk FROM city_rank WHERE rk <= 3 ORDER BY city, rk;

-- =====================================================
-- 03_聚合函数与分组 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：总行数 + 有描述的行数
SELECT COUNT(*) AS 总行数, COUNT(description) AS 有描述行数 FROM products;

-- 题2：每个供应商的商品数
SELECT supplier_id, COUNT(*) AS 商品数
FROM products
WHERE supplier_id IS NOT NULL
GROUP BY supplier_id
ORDER BY 商品数 DESC;

-- 题3：每个分类均价 > 500
SELECT category_id, ROUND(AVG(price), 2) AS 均价
FROM products
WHERE category_id IS NOT NULL
GROUP BY category_id
HAVING AVG(price) > 500
ORDER BY 均价 DESC;

-- 题4：2024年每月的订单数和总销售额
SELECT DATE_FORMAT(order_date, '%Y-%m') AS 月份,
       COUNT(*) AS 订单数,
       SUM(total_amount) AS 总销售额
FROM orders
WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01'
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY 月份;

-- 题5：客户数 >= 5 的城市
SELECT city, COUNT(*) AS 客户数
FROM customers
GROUP BY city
HAVING COUNT(*) >= 5
ORDER BY 客户数 DESC;

-- 题6：每个订单状态的订单数和总金额
SELECT status, COUNT(*) AS 订单数, SUM(total_amount) AS 总金额
FROM orders
GROUP BY status;

-- 题7：每种性别 + VIP 等级的客户数
SELECT gender, vip_level, COUNT(*) AS 人数
FROM customers
GROUP BY gender, vip_level
ORDER BY gender, vip_level;

-- 题8：不同城市数 + 总人数（ROLLUP）
SELECT COALESCE(city, '合计') AS 城市, COUNT(*) AS 人数
FROM customers
GROUP BY city WITH ROLLUP;

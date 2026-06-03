-- =====================================================
-- 07_集合操作 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：2023下半年 vs 2024上半年注册人数
SELECT '2023下半年' AS 时段, COUNT(*) AS 注册人数
FROM customers WHERE register_date BETWEEN '2023-07-01' AND '2023-12-31'
UNION ALL
SELECT '2024上半年', COUNT(*)
FROM customers WHERE register_date BETWEEN '2024-01-01' AND '2024-06-30';

-- 题2：最贵+最便宜 TOP3
(SELECT name, price, '最贵TOP3' AS 类型 FROM products ORDER BY price DESC LIMIT 3)
UNION ALL
(SELECT name, price, '最便宜TOP3' FROM products ORDER BY price ASC LIMIT 3);

-- 题3：同时有邮箱和手机号的客户
SELECT name FROM customers WHERE email IS NOT NULL AND phone IS NOT NULL;

-- 题4：从未买过智能手机的客户（NOT EXISTS）
SELECT name FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    WHERE o.customer_id = c.id AND p.category_id = 11
);

-- 题5：2024年有订单的客户 ∪ VIP>3的客户
SELECT c.name, '有订单' AS 来源 FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id
              AND o.order_date >= '2024-01-01')
UNION
SELECT c.name, 'VIP高等级' FROM customers c WHERE c.vip_level > 3;

-- 题6：价格排行表
(SELECT name, price, '最贵' AS 类别 FROM products ORDER BY price DESC LIMIT 3)
UNION ALL
(SELECT name, price, '最便宜' FROM products ORDER BY price ASC LIMIT 3);

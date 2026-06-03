-- =====================================================
-- 05_JOIN连接 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：商品+分类名称
SELECT p.name AS 商品, c.name AS 分类
FROM products p
JOIN categories c ON p.category_id = c.id;

-- 题2：所有商品+供应商（LEFT JOIN）
SELECT p.name AS 商品, s.name AS 供应商
FROM products p
LEFT JOIN suppliers s ON p.supplier_id = s.id;

-- 题3：从未下过单的客户
SELECT c.name, c.register_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.id IS NULL;

-- 题4：每个分类+商品数（含0个）
SELECT c.name AS 分类, COUNT(p.id) AS 商品数
FROM categories c
LEFT JOIN products p ON c.id = p.category_id
GROUP BY c.id, c.name
ORDER BY 商品数 DESC;

-- 题5：自连接查父子分类
SELECT child.name AS 子分类, parent.name AS 父分类
FROM categories child
LEFT JOIN categories parent ON child.parent_id = parent.id;

-- 题6：订单详情（4表连接）
SELECT o.id AS 订单ID, c.name AS 客户, p.name AS 商品,
       oi.quantity AS 数量, oi.unit_price AS 单价
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
LIMIT 20;

-- 题7：张伟的订单
SELECT o.id, o.order_date, o.total_amount, o.status
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE c.name = '张伟';

-- 题8：每个供应商的商品种类数
SELECT s.name AS 供应商, COUNT(DISTINCT p.id) AS 商品种类
FROM suppliers s
LEFT JOIN products p ON s.id = p.supplier_id
GROUP BY s.id, s.name
ORDER BY 商品种类 DESC;

-- 题9：同时购买了商品1和商品2的订单
SELECT order_id
FROM order_items
WHERE product_id IN (1, 2)
GROUP BY order_id
HAVING COUNT(DISTINCT product_id) = 2;

-- 题10：每个分类的最高价商品
SELECT c.name AS 分类, p.name AS 商品, p.price
FROM products p
JOIN categories c ON p.category_id = c.id
WHERE p.price = (SELECT MAX(price) FROM products WHERE category_id = p.category_id)
AND p.category_id IS NOT NULL;

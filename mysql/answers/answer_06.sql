-- =====================================================
-- 06_子查询 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：高于均价
SELECT name, price FROM products
WHERE price > (SELECT AVG(price) FROM products);

-- 题2：和刘洋同城市
SELECT name FROM customers
WHERE city = (SELECT city FROM customers WHERE name = '刘洋')
  AND name != '刘洋';

-- 题3：有已签收订单的客户（EXISTS）
SELECT name FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.status = 'delivered');

-- 题4：从未被购买过的商品（NOT EXISTS）
SELECT name FROM products p
WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.id);

-- 题5：每个分类价格最高的商品（关联子查询）
SELECT name, category_id, price FROM products p
WHERE price = (SELECT MAX(price) FROM products WHERE category_id = p.category_id)
  AND category_id IS NOT NULL;

-- 题6：评分高于平均的供应商
SELECT name, rating FROM suppliers
WHERE rating > (SELECT AVG(rating) FROM suppliers);

-- 题7：下单总额超10000的客户
SELECT c.name, SUM(o.total_amount) AS 总额
FROM customers c JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
HAVING SUM(o.total_amount) > 10000;

-- 题8：买过智能手机的客户
SELECT DISTINCT c.name
FROM customers c
JOIN orders o ON c.id = o.customer_id
JOIN order_items oi ON o.id = oi.order_id
WHERE oi.product_id IN (SELECT id FROM products WHERE category_id = 11)
   OR oi.product_id IN (SELECT id FROM products WHERE category_id IN
       (SELECT id FROM categories WHERE parent_id =
           (SELECT id FROM categories WHERE name = '手机通讯')));

-- 题9：库存最多的商品（ALL）
SELECT name, stock FROM products
WHERE stock >= ALL (SELECT stock FROM products WHERE stock IS NOT NULL);

-- 题10：客户数 > 北京客户数的城市
SELECT city, COUNT(*) AS cnt FROM customers
GROUP BY city
HAVING COUNT(*) > (SELECT COUNT(*) FROM customers WHERE city = '北京');

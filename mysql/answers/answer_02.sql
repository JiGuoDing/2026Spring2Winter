-- =====================================================
-- 02_高级过滤与排序 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：价格大于 100 且库存大于 100
SELECT name, price FROM products WHERE price > 100 AND stock > 100;

-- 题2：分类ID为1或3、且价格小于200
SELECT name, price, category_id FROM products
WHERE (category_id = 1 OR category_id = 3) AND price < 200;

-- 题3：姓名以"王"开头
SELECT name FROM customers WHERE name LIKE '王%';

-- 题4：城市在北京、上海、广州
SELECT name, city FROM customers WHERE city IN ('北京', '上海', '广州');

-- 题5：注册日期在 2024年3月
SELECT name, register_date FROM customers
WHERE register_date BETWEEN '2024-03-01' AND '2024-03-31';

-- 题6：价格最高的 10 件商品
SELECT name, price FROM products ORDER BY price DESC LIMIT 10;

-- 题7：库存不为NULL，按库存升序，第2页（每页5条）
SELECT id, name, stock FROM products
WHERE stock IS NOT NULL
ORDER BY stock ASC
LIMIT 5 OFFSET 5;

-- 题8：供应商评分为 NULL
SELECT name FROM suppliers WHERE rating IS NULL;

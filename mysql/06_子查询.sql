-- =====================================================
-- 文件名：06_子查询.sql
-- 难度：★★★☆☆
-- 前置知识：05_JOIN连接
-- 学习时间：约 55 分钟
-- 对应面试考点：EXISTS vs IN、关联子查询、NOT IN 的 NULL 陷阱
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 6.1 子查询分类（按返回值）
-- ---------------------------------------------------

-- A. 标量子查询：返回单行单列（单个值）
-- 可以出现在 SELECT、WHERE、HAVING 中

-- 查询价格高于平均价的商品
SELECT name, price
FROM products
WHERE price > (SELECT AVG(price) FROM products);

-- SELECT 中使用标量子查询
SELECT
    name,
    price,
    (SELECT ROUND(AVG(price), 2) FROM products) AS 整体均价,
    ROUND(price - (SELECT AVG(price) FROM products), 2) AS 与均价差额
FROM products
ORDER BY 与均价差额 DESC
LIMIT 5;

-- B. 列子查询：返回多行单列
-- 常用于 IN / NOT IN / ANY / ALL

-- 查询有订单的客户（用 IN）
SELECT id, name FROM customers
WHERE id IN (SELECT DISTINCT customer_id FROM orders);

-- C. 行子查询：返回单行多列
-- 查询和张伟同一个城市、同一个VIP等级的客户
SELECT name, city, vip_level
FROM customers
WHERE (city, vip_level) = (
    SELECT city, vip_level FROM customers WHERE name = '张伟'
)
AND name != '张伟';

-- D. 表子查询（派生表）：FROM 中的子查询（必须有别名）
SELECT 子.average
FROM (SELECT AVG(price) AS average FROM products) AS 子;

-- ---------------------------------------------------
-- 6.2 子查询按位置分类
-- ---------------------------------------------------

-- WHERE 中（最常用）
SELECT name FROM products
WHERE category_id = (SELECT id FROM categories WHERE name = '智能手机');

-- FROM 中（派生表，必须指定别名！）
SELECT cat_name, avg_price
FROM (
    SELECT c.name AS cat_name, AVG(p.price) AS avg_price
    FROM categories c
    JOIN products p ON c.id = p.category_id
    GROUP BY c.id, c.name
) AS category_stats
WHERE avg_price > 500;

-- HAVING 中
SELECT category_id, AVG(price) AS avg_price
FROM products
GROUP BY category_id
HAVING AVG(price) > (SELECT AVG(price) FROM products);

-- ---------------------------------------------------
-- 6.3 关联子查询 vs 非关联子查询 ⭐
-- ---------------------------------------------------

-- 非关联子查询：子查询独立运行，不依赖外部
-- 查询每个分类中价格高于该分类平均价的商品
SELECT p.name, p.price, p.category_id
FROM products p
WHERE p.price > (
    SELECT AVG(price) FROM products WHERE category_id = p.category_id
);
-- ↑ 这是关联子查询！因为内部引用了外部的 p.category_id

-- 关联子查询：子查询引用外部列，外部每行都要执行一次子查询
-- 所以关联子查询通常较慢，需要合理使用

-- ---------------------------------------------------
-- 6.4 EXISTS / NOT EXISTS ⭐ 面试高频
-- ---------------------------------------------------

-- EXISTS：检查子查询是否返回至少一行
-- 查至少下过一次订单的客户
SELECT id, name
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id
);

-- 等价于 IN（但 EXISTS 通常更高效）
SELECT id, name FROM customers
WHERE id IN (SELECT DISTINCT customer_id FROM orders);

-- NOT EXISTS：查从未下过单的客户
SELECT id, name
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id
);

-- ---------------------------------------------------
-- 6.5 IN vs EXISTS 性能差异 ⭐ 面试高频
-- ---------------------------------------------------

-- IN：先执行子查询得到结果集，外层逐行检查是否在集合中
--     适合子查询结果集小、外层表大的情况

-- EXISTS：外层每行都执行一次子查询（但有短路优化，找到就停）
--     适合子查询结果集大、外层表小的情况
--     关联字段有索引时，EXISTS 通常比 IN 快

-- 通用建议：
-- 1. 子查询结果小用 IN，子查询结果大用 EXISTS
-- 2. NOT EXISTS 优于 NOT IN（可避免 NULL 陷阱）
-- 3. 如果两表连接字段都有索引，IN 和 EXISTS 性能接近

-- ---------------------------------------------------
-- 6.6 NOT IN 的 NULL 陷阱 ⚠️ 重要！
-- ---------------------------------------------------

-- 场景：查询"不在某个集合中"的记录

-- 先看：哪些商品的 category_id 有 NULL？
SELECT id, name, category_id FROM products WHERE category_id IS NULL;

-- 危险：如果子查询包含 NULL，NOT IN 返回空集！
SELECT COUNT(*) FROM products
WHERE category_id NOT IN (SELECT parent_id FROM categories);
-- 如果 categories.parent_id 包含 NULL，这个查询返回 0！

-- 安全做法1：子查询中加 IS NOT NULL
SELECT COUNT(*) FROM products
WHERE category_id NOT IN (
    SELECT parent_id FROM categories WHERE parent_id IS NOT NULL
);

-- 安全做法2：用 NOT EXISTS（推荐！自动处理 NULL）
SELECT COUNT(*) FROM products p
WHERE NOT EXISTS (
    SELECT 1 FROM categories c WHERE c.parent_id = p.category_id
);

-- ---------------------------------------------------
-- 6.7 ANY / ALL 量化比较
-- ---------------------------------------------------

-- ANY：满足任意一个即可
-- 查询价格高于任一智能手机的商品
SELECT name, price FROM products
WHERE price > ANY (
    SELECT price FROM products WHERE category_id = 11
)
AND category_id != 11
ORDER BY price;

-- ALL：必须满足所有
-- 查询价格高于所有智能手机的商品（即比最贵的还贵）
SELECT name, price FROM products
WHERE price > ALL (
    SELECT price FROM products WHERE category_id = 11
)
ORDER BY price;
-- 等价于：WHERE price > (SELECT MAX(price) FROM products WHERE category_id = 11)

-- ---------------------------------------------------
-- 6.8 子查询 vs JOIN
-- ---------------------------------------------------

-- 子查询写法：查有订单的客户
SELECT name FROM customers
WHERE id IN (SELECT DISTINCT customer_id FROM orders);

-- JOIN 写法（同一需求）
SELECT DISTINCT c.name FROM customers c
JOIN orders o ON c.id = o.customer_id;

-- 选择标准：
-- 1. 只需要主表数据（不需要子表字段）→ 子查询或 EXISTS
-- 2. 需要子表的字段参与 SELECT → JOIN
-- 3. 子查询结果大但外层数据小 → EXISTS 可能更快
-- 4. 大多数情况下 MySQL 优化器会自动转换 IN → EXISTS

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：查询价格高于所有商品平均价的商品名称和价格（标量子查询）
-- 你的代码：


-- 题2：查询和"刘洋"同一个城市的客户姓名（去掉刘洋自己）
-- 你的代码：


-- 题3：用 EXISTS 查询至少有一笔"已签收"订单的客户
-- 你的代码：


-- 题4：用 NOT EXISTS 查询从未被购买过的商品（在 order_items 中无记录）
-- 你的代码：


-- 题5：查询每个分类中价格最高的商品（关联子查询）
-- 提示：WHERE price = (SELECT MAX(price) FROM products WHERE category_id = p.category_id)
-- 你的代码：


-- 题6：查询供应商中评分高于所有供应商平均评分的供应商（标量子查询）
-- 你的代码：


-- 题7：查询下单总额超过 10000 的客户（WHERE 中的子查询 + SUM）
-- 你的代码：


-- 题8：查询客户中，那些"曾经买过智能手机（category_id=11）"的客户姓名
-- 你的代码：


-- 题9：用 ALL 查询库存最多的商品（stock >= ALL (SELECT stock FROM products)）
-- 你的代码：


-- 题10：查询城市客户总数大于北京客户总数的城市（HAVING + 子查询）
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: EXISTS 和 IN 的区别？
-- A: IN 先执行子查询得到结果集，外层逐行匹配
--    EXISTS 外层每行执行子查询，有结果就返回 TRUE（短路）
--    EXISTS 在子查询结果集大或关联字段有索引时通常更高效
--    NOT EXISTS 可以安全处理 NULL，NOT IN 有 NULL 陷阱
--
-- Q: NOT IN 遇到 NULL 为什么会返回空集？
-- A: x NOT IN (1, 2, NULL) → x <> 1 AND x <> 2 AND x <> NULL
--    x <> NULL 永远返回 UNKNOWN，导致整个 AND 条件为 UNKNOWN
--    WHERE 只保留 TRUE，UNKNOWN 被丢弃 → 0 行
--
-- Q: 关联子查询和非关联子查询的区别？
-- A: 关联子查询：子查询内引用了外层表的列，外层每行都需执行内查询
--    非关联子查询：子查询独立于外层，只执行一次
--    关联子查询通常较慢，但有时是必需的（如每组 Top N）
--
-- Q: 子查询和 JOIN 该选哪个？
-- A: 只要 SELECT 的主表字段 → 子查询/EXISTS 更直观
--    需要多表字段 → JOIN
--    多数情况下优化器会优化，性能差距不大
--    优先考虑可读性

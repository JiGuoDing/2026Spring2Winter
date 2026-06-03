-- =====================================================
-- 文件名：07_集合操作.sql
-- 难度：★★★☆☆
-- 前置知识：03_聚合函数与分组, 05_JOIN连接, 06_子查询
-- 学习时间：约 30 分钟
-- 对应面试考点：UNION vs UNION ALL、差集实现、集合运算
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 7.1 UNION — 并集（去重）
-- ---------------------------------------------------

-- UNION 将多个 SELECT 的结果纵向合并，自动去重

-- 示例：查询"北京和上海的客户"和"VIP等级>3的客户"的并集
SELECT name, city, '城市筛选' AS 来源
FROM customers
WHERE city IN ('北京', '上海')
UNION
SELECT name, city, 'VIP筛选' AS 来源
FROM customers
WHERE vip_level > 3;

-- ---------------------------------------------------
-- 7.2 UNION ALL — 并集（不去重，保留全部）
-- ---------------------------------------------------

-- UNION ALL 不检查重复，性能比 UNION 好
-- 如果确定无重复或需要保留重复，用 UNION ALL

-- 按季度统计订单（用 UNION ALL 拼接4个季度）
SELECT 'Q1' AS 季度, COUNT(*) AS 订单数, SUM(total_amount) AS 总额
FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-03-31'
UNION ALL
SELECT 'Q2', COUNT(*), SUM(total_amount)
FROM orders WHERE order_date BETWEEN '2024-04-01' AND '2024-06-30'
UNION ALL
SELECT 'Q3', COUNT(*), SUM(total_amount)
FROM orders WHERE order_date BETWEEN '2024-07-01' AND '2024-09-30'
UNION ALL
SELECT 'Q4', COUNT(*), SUM(total_amount)
FROM orders WHERE order_date BETWEEN '2024-10-01' AND '2024-12-31';

-- ---------------------------------------------------
-- 7.3 INTERSECT — 交集（MySQL 8.0.31+ 支持）
-- ---------------------------------------------------
-- 返回两个查询都有的行

-- 既在北京又在上海的客户？不可能同一个人在两个城市，所以结果为0
-- SELECT name FROM customers WHERE city = '北京'
-- INTERSECT
-- SELECT name FROM customers WHERE city = '上海';

-- 更实际的例子：既买过商品1又买过商品2的客户
-- （结果先略，因为实际数据可能没有这种组合）

-- 不直接支持 INTERSECT 的版本：用 IN 或 EXISTS 模拟
SELECT DISTINCT c.name
FROM customers c
JOIN orders o ON c.id = o.customer_id
JOIN order_items oi ON o.id = oi.order_id
WHERE oi.product_id = 1
  AND c.id IN (
    SELECT c2.id
    FROM customers c2
    JOIN orders o2 ON c2.id = o2.customer_id
    JOIN order_items oi2 ON o2.id = oi2.order_id
    WHERE oi2.product_id = 2
);

-- ---------------------------------------------------
-- 7.4 EXCEPT — 差集（MySQL 8.0.31+ 支持）
-- ---------------------------------------------------
-- 返回第一个查询有但第二个查询没有的行

-- MySQL 8.0.31+ 写法：
-- SELECT name FROM customers WHERE city = '北京'
-- EXCEPT
-- SELECT name FROM customers WHERE vip_level > 3;
-- ↑ 北京客户中，VIP等级不>3的客户

-- 旧版兼容写法1：LEFT JOIN + IS NULL
SELECT c1.name
FROM customers c1
LEFT JOIN (SELECT id FROM customers WHERE vip_level > 3) c2
    ON c1.id = c2.id
WHERE c1.city = '北京' AND c2.id IS NULL;

-- 旧版兼容写法2：NOT EXISTS（推荐）
SELECT name
FROM customers c1
WHERE c1.city = '北京'
  AND NOT EXISTS (
    SELECT 1 FROM customers c2
    WHERE c2.id = c1.id AND c2.vip_level > 3
);

-- ---------------------------------------------------
-- 7.5 集合操作的规则
-- ---------------------------------------------------
-- 1. 列数必须相同
-- 2. 对应列的数据类型必须兼容
-- 3. ORDER BY 只能出现在整个集合操作的末尾（或每个子查询用()包裹）
-- 4. 列名以第一个 SELECT 为准

-- UNION 后的排序
(SELECT name, price FROM products WHERE price > 5000)
UNION ALL
(SELECT name, price FROM products WHERE price < 10)
ORDER BY price DESC;

-- 如果想每个子查询内部排序+限制：
(SELECT name, price FROM products WHERE price > 5000 ORDER BY price DESC LIMIT 3)
UNION ALL
(SELECT name, price FROM products WHERE price < 10 ORDER BY price ASC  LIMIT 3);

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：用 UNION ALL 统计 2023 下半年和 2024 上半年的客户注册人数
-- 你的代码：


-- 题2：用 UNION ALL 显示"最贵商品 TOP 3"和"最便宜商品 TOP 3"
-- 你的代码：


-- 题3：查询同时具有邮箱和手机号的客户（用 JOIN 或 INTERSECT 的思路）
-- 你的代码：


-- 题4：用 NOT EXISTS 实现：查询从未买过智能手机(category_id=11)的客户
-- 你的代码：


-- 题5：用 UNION 合并"2024年有订单的客户"和"VIP>3的客户"
-- 你的代码：


-- 题6：列一张"商品价格排行表"，包含"最贵3个"（UNION ALL "最便宜3个"），并加一列"类别"标注
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: UNION 和 UNION ALL 的区别？
-- A: UNION 会去重（排序+比较），UNION ALL 不去重直接拼接
--    UNION ALL 性能更好，能确定无重复或需要保留重复时应优先使用
--    UNION 等同于 UNION ALL + DISTINCT
--
-- Q: UNION 和 JOIN 的区别？
-- A: UNION 是纵向拼接（行数增加），JOIN 是横向拼接（列数增加）
--    UNION 要求列数相同，JOIN 需要 ON 条件
--
-- Q: MySQL 不支持 INTERSECT/EXCEPT 怎么办？
-- A: INTERSECT → IN / EXISTS / JOIN
--    EXCEPT → NOT IN (注意NULL) / NOT EXISTS (推荐) / LEFT JOIN + IS NULL
--
-- Q: 集合操作中 ORDER BY 为什么放最后？
-- A: 集合操作的本质是对多个结果集进行合并
--    对整个合并后的结果排序才有意义
--    如果想在子查询内排序，需要用 () 包裹并配合 LIMIT

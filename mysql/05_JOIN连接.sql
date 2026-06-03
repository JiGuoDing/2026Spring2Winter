-- =====================================================
-- 文件名：05_JOIN连接.sql
-- 难度：★★★☆☆
-- 前置知识：01_基础查询_CRUD, 02_高级过滤与排序, 03_聚合函数与分组
-- 学习时间：约 60 分钟
-- 对应面试考点：各种 JOIN 的区别、自连接、多表连接、ON vs WHERE
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 5.0 JOIN 概念总览
-- ---------------------------------------------------
-- INNER JOIN：返回两表匹配的行（交集）
-- LEFT JOIN： 返回左表全部行 + 右表匹配的行（左表驱动）
-- RIGHT JOIN：返回右表全部行 + 左表匹配的行（右表驱动，实际少用）
-- CROSS JOIN：笛卡尔积（左表每行 × 右表每行）
-- SELF JOIN： 表和自己 JOIN

-- ---------------------------------------------------
-- 5.1 INNER JOIN — 内连接（最常用 ~80%）
-- ---------------------------------------------------

-- 查商品及其分类名称
SELECT
    p.id,
    p.name AS 商品,
    c.name AS 分类
FROM products p
INNER JOIN categories c ON p.category_id = c.id
LIMIT 10;

-- 只写 JOIN 默认就是 INNER JOIN
SELECT p.name, c.name
FROM products p
JOIN categories c ON p.category_id = c.id
LIMIT 5;

-- 注意：INNER JOIN 只返回匹配行
-- category_id 为 NULL 的商品不会出现在结果中
-- 供应商不匹配的商品也不会出现

-- ---------------------------------------------------
-- 5.2 LEFT JOIN — 左外连接 ⭐ 最重要
-- ---------------------------------------------------

-- LEFT JOIN 保留左表全部行，右表无匹配则填 NULL
SELECT
    p.id,
    p.name AS 商品,
    p.category_id,
    c.name AS 分类名称
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
ORDER BY p.id
LIMIT 15;
-- 注意：category_id 为 NULL 的商品也会显示，分类名称为 NULL

-- 经典面试题：查没有分类的商品（LEFT JOIN + IS NULL）
SELECT p.id, p.name
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
WHERE c.id IS NULL;

-- 经典面试题：查从未下过单的客户
SELECT c.id, c.name
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.id IS NULL;

-- ---------------------------------------------------
-- 5.3 RIGHT JOIN — 右外连接
-- ---------------------------------------------------

-- RIGHT JOIN 等价于交换左右表位置的 LEFT JOIN
-- 实际开发中很少用 RIGHT JOIN（所有 RIGHT JOIN 都可以改写为 LEFT JOIN）

-- 查所有分类及其商品（包括没有商品的分类）
SELECT c.name AS 分类, p.name AS 商品
FROM products p
RIGHT JOIN categories c ON p.category_id = c.id
ORDER BY c.id;

-- 上述等价于 LEFT JOIN（推荐写法）：
SELECT c.name AS 分类, p.name AS 商品
FROM categories c
LEFT JOIN products p ON c.category_id = p.id
ORDER BY c.id;

-- ---------------------------------------------------
-- 5.4 CROSS JOIN — 笛卡尔积
-- ---------------------------------------------------

-- 交叉连接：左表每行和右表每行都组合
-- 通常是无意的（忘了写 ON 条件），但有时故意使用

-- 生成组合表（如：所有颜色 × 所有尺码）
-- SELECT colors.color, sizes.size
-- FROM colors CROSS JOIN sizes;

-- 生成数字序列
-- SELECT a.id + b.id * 10 AS n FROM ...
-- 实际：CROSS JOIN 产生 rows(left) × rows(right) 行，大表慎用！

-- ---------------------------------------------------
-- 5.5 SELF JOIN — 自连接 ⭐
-- ---------------------------------------------------

-- 表自己连接自己（必须用别名区分）
-- 查商品的父子分类关系（categories 有 parent_id 指向自身）

SELECT
    child.id     AS 子分类ID,
    child.name   AS 子分类,
    parent.id    AS 父分类ID,
    parent.name  AS 父分类
FROM categories child
LEFT JOIN categories parent ON child.parent_id = parent.id
ORDER BY parent.id, child.id;

-- 查顶级分类下的二级分类（即两层关系）
SELECT
    l1.name AS 一级分类,
    l2.name AS 二级分类
FROM categories l1
JOIN categories l2 ON l1.id = l2.parent_id
WHERE l1.parent_id IS NULL  -- 顶级分类
ORDER BY l1.id, l2.id;

-- ---------------------------------------------------
-- 5.6 多表连接（3表、4表）
-- ---------------------------------------------------

-- 查：订单 → 客户 → 订单明细 → 商品 → 分类
-- 5 表连接（四表关联链）
SELECT
    o.id           AS 订单号,
    c.name         AS 客户,
    p.name         AS 商品,
    oi.quantity    AS 数量,
    oi.unit_price  AS 单价,
    cat.name       AS 商品分类
FROM orders o
JOIN customers c    ON o.customer_id = c.id
JOIN order_items oi ON o.id = oi.order_id
JOIN products p     ON oi.product_id = p.id
LEFT JOIN categories cat ON p.category_id = cat.id
WHERE o.status = 'delivered'
ORDER BY o.id
LIMIT 20;

-- ---------------------------------------------------
-- 5.7 USING vs ON
-- ---------------------------------------------------

-- 当两表连接列同名时，可以用 USING 简写
SELECT p.name, c.name
FROM products p
JOIN categories c USING (id);  -- 等价于 ON p.id = c.id（但这里 id 含义不同，不适用）

-- 正确的 USING 场景：列名相同且含义相同
-- 假设 order_items 有列也叫 product_id：
-- SELECT * FROM products JOIN order_items USING (product_id);
-- 等价于 ON products.product_id = order_items.product_id

-- USING 的副作用：SELECT * 时连接列只出现一次（ON 会出现两次）

-- ---------------------------------------------------
-- 5.8 隐式连接 vs 显式 JOIN
-- ---------------------------------------------------

-- ❌ 隐式连接（老写法，不推荐）
SELECT c.name, o.id
FROM customers c, orders o
WHERE c.id = o.customer_id;

-- ✅ 显式 JOIN（推荐！可读性好，不容易漏 ON 条件）
SELECT c.name, o.id
FROM customers c
JOIN orders o ON c.id = o.customer_id;

-- 为什么不用隐式连接？
-- 1. 容易忘记 WHERE 条件写成笛卡尔积
-- 2. LEFT/RIGHT JOIN 无法用隐式写法表达（各数据库语法不一）
-- 3. 可读性差，WHERE 里混杂连接条件和筛选条件

-- ---------------------------------------------------
-- 5.9 JOIN 与 ON 条件的技巧
-- ---------------------------------------------------

-- ON 条件中可以用 AND 加更多连接条件
-- LEFT JOIN 时 ON 条件和 WHERE 条件结果不同！

-- 查客户及其已签收的订单
-- 写法1：条件放 ON（LEFT JOIN 不会过滤左表行）
SELECT c.name, o.id, o.status
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id AND o.status = 'delivered'
LIMIT 10;
-- ↑ 所有客户都会出现，没签收订单的客户订单列为 NULL

-- 写法2：条件放 WHERE（会过滤左表行，LEFT JOIN 退化为 INNER JOIN）
SELECT c.name, o.id, o.status
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.status = 'delivered'
LIMIT 10;
-- ↑ 只有有签收订单的客户才出现

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：查询商品名称及其所属分类名称（INNER JOIN）
-- 你的代码：


-- 题2：查询所有商品及其供应商名称，注意保留没有供应商的商品（LEFT JOIN）
-- 你的代码：


-- 题3：查询从未下过单的客户姓名和注册日期（LEFT JOIN + IS NULL）
-- 你的代码：


-- 题4：查询每个商品分类及其商品数量（含 0 个商品的分类也要显示）
-- 你的代码：


-- 题5：用自连接查询 categories 表，显示每个分类的名称和其父分类名称
-- 你的代码：


-- 题6：查询订单详情：订单ID、客户姓名、商品名称、数量、单价（4表连接）
-- 你的代码：


-- 题7：查询"张伟"客户的所有订单，显示订单ID、日期、总金额、状态
-- 你的代码：


-- 题8：查询每个供应商供应的商品种类数（INNER JOIN + GROUP BY），按种类数降序
-- 你的代码：


-- 题9：查询同时购买了商品1和商品2的订单ID（SELF JOIN order_items 或用 GROUP BY + HAVING）
-- 提示：用 order_items 表自连接或 GROUP BY order_id HAVING COUNT(CASE WHEN ...)
-- 你的代码：


-- 题10：查询每个分类的最高价商品名称和价格（用 JOIN + 子查询）
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: INNER JOIN 和 LEFT JOIN 的区别？
-- A: INNER JOIN 只返回两表都匹配的行（交集）
--    LEFT JOIN 返回左表全部行，右表无匹配则填 NULL
--    实际开发中 LEFT JOIN 使用率 ≈80%，INNER JOIN ≈15%
--
-- Q: LEFT JOIN 中 ON 条件和 WHERE 条件的区别？
-- A: ON 条件在 JOIN 时生效，不满足时右表列填 NULL（不影响左表行数）
--    WHERE 条件在 JOIN 之后过滤，不满足时整行删除（可能减少行数）
--    WHERE 中对右表列做非 NULL 条件过滤，LEFT JOIN 会退化为 INNER JOIN
--
-- Q: 怎么查 A 表有但 B 表没有的记录？
-- A: LEFT JOIN + WHERE B.id IS NULL（这是最常用的差集写法）
--
-- Q: 自连接是什么场景？
-- A: 树形结构（组织架构、分类层级、评论回复）
--    找重复数据
--    相邻行比较
--
-- Q: 多表 JOIN 的顺序有影响吗？
-- A: MySQL 优化器会自动选择最优的 JOIN 顺序
--    但 ON 条件和驱动表的选择会影响性能
--    小表驱动大表、在连接列上建索引是优化关键

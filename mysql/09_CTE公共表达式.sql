-- =====================================================
-- 文件名：09_CTE公共表达式.sql
-- 难度：★★★☆☆
-- 前置知识：06_子查询, 08_窗口函数
-- 学习时间：约 40 分钟
-- 对应面试考点：CTE vs 子查询、递归 CTE、树形结构查询
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 9.1 普通 CTE（Common Table Expression）
-- ---------------------------------------------------
-- 语法：WITH cte_name AS (SELECT ...) SELECT ... FROM cte_name
-- CTE 本质是"有名字的子查询"，可被后续查询多次引用

-- 不用 CTE：子查询嵌套，可读性差
SELECT *
FROM (
    SELECT category_id, AVG(price) AS avg_price
    FROM products
    GROUP BY category_id
) AS cat_avg
WHERE avg_price > 500;

-- 用 CTE：逻辑分层，清晰易读
WITH cat_avg AS (
    SELECT category_id, AVG(price) AS avg_price
    FROM products
    GROUP BY category_id
)
SELECT * FROM cat_avg WHERE avg_price > 500;

-- 多个 CTE 链式定义（后面的 CTE 可以引用前面的）
WITH
    -- CTE 1：每个客户的消费统计
    customer_stats AS (
        SELECT
            customer_id,
            COUNT(*)    AS order_count,
            SUM(total_amount) AS total_spent
        FROM orders
        GROUP BY customer_id
    ),
    -- CTE 2：只取高价值客户（引用 CTE 1）
    high_value AS (
        SELECT customer_id, total_spent
        FROM customer_stats
        WHERE order_count >= 3 AND total_spent > 10000
    )
-- 主查询
SELECT c.name, c.city, hv.total_spent AS 总消费
FROM high_value hv
JOIN customers c ON hv.customer_id = c.id
ORDER BY hv.total_spent DESC;

-- ---------------------------------------------------
-- 9.2 CTE + 窗口函数：TopN 的优雅写法
-- ---------------------------------------------------

-- 不用 CTE：
-- SELECT * FROM (SELECT *, ROW_NUMBER() OVER(...) AS rn FROM ...) t WHERE t.rn <= 3

-- 用 CTE（推荐！可读性显著提升）：
WITH ranked AS (
    SELECT
        category_id,
        name,
        price,
        ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY price DESC) AS rn
    FROM products
    WHERE category_id IS NOT NULL
)
SELECT category_id, name, price, rn
FROM ranked
WHERE rn <= 3
ORDER BY category_id, rn;

-- ---------------------------------------------------
-- 9.3 CTE vs 子查询 vs 临时表 vs 视图
-- ---------------------------------------------------
-- CTE：     存在于单个 SQL 语句中，执行完即释放
-- 子查询：  嵌套在 SQL 中，不可复用
-- 临时表：  存在于整个会话，可多次引用，需要手动 DROP
-- 视图：    持久化到数据库，所有人可用
--
-- 选择建议：
--   单次查询内复用 → CTE
--   同一会话中多次使用 → 临时表
--   常用复杂查询 → 视图
--   简单的一次性子查询 → 子查询

-- ---------------------------------------------------
-- 9.4 递归 CTE ⭐ 重要！
-- ---------------------------------------------------
-- 语法：WITH RECURSIVE cte AS (初始查询 UNION ALL 递归查询)
-- 结构包含两部分：锚定成员(初始数据) + 递归成员(引用自身)

-- 经典案例1：生成 1~10 的序列
WITH RECURSIVE seq AS (
    SELECT 1 AS n                           -- 锚定：起始值
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 10      -- 递归：每次+1，直到 n>=10 停止
)
SELECT * FROM seq;

-- 经典案例2：生成日期序列（常用于补全缺失日期）
WITH RECURSIVE dates AS (
    SELECT '2024-01-01' AS dt
    UNION ALL
    SELECT DATE_ADD(dt, INTERVAL 1 DAY) FROM dates WHERE dt < '2024-01-31'
)
SELECT * FROM dates;

-- 经典案例3：遍历分类树 ⭐⭐⭐
-- 查询"数码电子"分类下的所有子分类（包括子分类的子分类...）
WITH RECURSIVE category_tree AS (
    -- 锚定：从"数码电子"开始
    SELECT id, name, parent_id, 1 AS level
    FROM categories
    WHERE name = '数码电子'

    UNION ALL

    -- 递归：找所有子分类
    SELECT c.id, c.name, c.parent_id, ct.level + 1
    FROM categories c
    JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT
    CONCAT(REPEAT('  ', level - 1), name) AS 分类层级,
    id,
    parent_id,
    level
FROM category_tree
ORDER BY level, id;

-- 经典案例4：查某个分类的完整父级链（向上递归）
-- 查"智能手机"往上所有父级
WITH RECURSIVE parent_chain AS (
    SELECT id, name, parent_id, 1 AS level
    FROM categories
    WHERE name = '智能手机'

    UNION ALL

    SELECT c.id, c.name, c.parent_id, pc.level + 1
    FROM categories c
    JOIN parent_chain pc ON c.id = pc.parent_id
)
SELECT
    CONCAT(REPEAT('  ', level - 1), name) AS 层级,
    level
FROM parent_chain
ORDER BY level DESC;

-- ---------------------------------------------------
-- 9.5 递归 CTE 的限制
-- ---------------------------------------------------
-- 1. 递归部分不能包含 GROUP BY / DISTINCT / 聚合函数 / ORDER BY / LIMIT
-- 2. 默认最大递归深度 1000（由 cte_max_recursion_depth 控制）
-- 3. 不能用于子查询中

-- 查看/修改递归深度限制
-- SELECT @@cte_max_recursion_depth;
-- SET SESSION cte_max_recursion_depth = 500;

-- 递归终止条件：当递归查询不再产生新行时自动终止
-- 务必确保递归有终止条件，否则会报错！

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：用 CTE 计算每个客户的消费总额和订单数，然后查消费总额 > 10000 的客户
-- 你的代码：


-- 题2：用 CTE + 窗口函数，查每个分类价格 Top 3 的商品
-- 你的代码：


-- 题3：用递归 CTE 生成 2024 年 6 月的每一天
-- 你的代码：


-- 题4：用递归 CTE 查询"服装鞋帽"的所有子分类（向下递归）
-- 你的代码：


-- 题5：用递归 CTE 查询某一商品的完整分类路径（从顶级到当前）
-- 你的代码：


-- 题6：用多个 CTE 链式定义：先统计客户消费，再统计城市消费排名
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: CTE 和子查询的区别？什么时候用 CTE？
-- A: CTE 是"有名字的子查询"，可被后续查询多次引用
--    子查询嵌套在 SQL 中，不可复用
--    用 CTE 的场景：①同一查询中需要复用子查询结果
--    ②复杂查询需要分层（提高可读性）③递归查询
--
-- Q: 什么是递归 CTE？结构是怎样的？
-- A: WITH RECURSIVE cte AS (锚定 UNION ALL 递归)
--    锚定=初始数据，递归=基于上一步结果继续查（引用自身）
--    常用于：树形结构遍历、生成序列、图路径查找
--
-- Q: 递归 CTE 怎么终止？会不会死循环？
-- A: 当递归部分不再产生新行时自动终止
--    MySQL 有默认 cte_max_recursion_depth=1000 的保护
--    但还是要确保递归条件最终能收敛到不产生新行
--
-- Q: 大数据框架（Hive/Spark SQL）支持 CTE 吗？
-- A: 都支持！Hive 从 0.13.0+ 支持 CTE
--    Spark SQL 从 2.0+ 支持 CTE
--    CTE 语法是 SQL-99 标准，几乎所有大数据 SQL 引擎都支持

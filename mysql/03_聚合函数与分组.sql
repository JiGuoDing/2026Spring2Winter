-- =====================================================
-- 文件名：03_聚合函数与分组.sql
-- 难度：★★☆☆☆
-- 前置知识：01_基础查询_CRUD, 02_高级过滤与排序
-- 学习时间：约 50 分钟
-- 对应面试考点：GROUP BY、HAVING vs WHERE、SQL 执行顺序、聚合分析
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 3.1 聚合函数概览
-- ---------------------------------------------------
-- 聚合函数对一组行进行计算，返回单个值
-- NULL 值在聚合中被忽略（COUNT(*) 除外）

-- COUNT：计数
SELECT COUNT(*)   AS 总商品数 FROM products;
SELECT COUNT(description) AS 有描述的商品数 FROM products;  -- NULL不计数
SELECT COUNT(DISTINCT city) AS 客户分布城市数 FROM customers;

-- SUM：求和（忽略NULL）
SELECT SUM(total_amount) AS 总销售额 FROM orders;
SELECT SUM(stock) AS 总库存 FROM products;

-- AVG：平均值
SELECT AVG(price)  AS 平均价格 FROM products;
SELECT ROUND(AVG(price), 2) AS 平均价格 FROM products;  -- 保留2位小数

-- MAX / MIN：最大/最小值
SELECT MAX(price) AS 最贵, MIN(price) AS 最便宜 FROM products;

-- 聚合函数 + WHERE
SELECT AVG(price) FROM products WHERE category_id = 11;  -- 智能手机均价

-- ---------------------------------------------------
-- 3.2 GROUP BY — 分组聚合
-- ---------------------------------------------------
-- 将数据按某列分组，然后对每组分别聚合

-- 每个城市的客户数
SELECT city, COUNT(*) AS 客户数
FROM customers
GROUP BY city
ORDER BY 客户数 DESC
LIMIT 5;

-- 每个分类的商品数和平均价格
SELECT
    category_id,
    COUNT(*)  AS 商品数,
    ROUND(AVG(price), 2) AS 均价,
    MAX(price) AS 最高价,
    MIN(price) AS 最低价
FROM products
WHERE category_id IS NOT NULL
GROUP BY category_id
ORDER BY 商品数 DESC;

-- 多列分组：每个城市 + 每种性别的客户数
SELECT city, gender, COUNT(*) AS 人数
FROM customers
GROUP BY city, gender
ORDER BY city, gender;

-- ---------------------------------------------------
-- 3.3 HAVING vs WHERE ⭐ 面试必考！
-- ---------------------------------------------------
-- WHERE：在分组前过滤行（原始数据过滤）
-- HAVING：在分组后过滤组（聚合结果过滤）

-- SQL 执行顺序（核心！）：
-- FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT

-- 错误示例：WHERE 中不能用聚合函数
-- SELECT category_id, AVG(price) FROM products WHERE AVG(price) > 500 GROUP BY category_id;  -- 报错！

-- 正确：用 HAVING 过滤聚合结果
SELECT
    category_id,
    COUNT(*)  AS 商品数,
    ROUND(AVG(price), 2) AS 均价
FROM products
WHERE category_id IS NOT NULL    -- 先过滤：只要非空分类
GROUP BY category_id             -- 分组
HAVING COUNT(*) >= 3             -- 后过滤：商品数>=3的分类
ORDER BY 均价 DESC;

-- WHERE 和 HAVING 可以同时存在（各司其职）
SELECT
    status,
    COUNT(*)  AS 订单数,
    SUM(total_amount) AS 总额
FROM orders
WHERE order_date >= '2024-01-01'             -- 先过滤行：只要2024年的
GROUP BY status                                -- 分组
HAVING SUM(total_amount) > 10000              -- 后过滤组：总额>10000
ORDER BY 总额 DESC;

-- ---------------------------------------------------
-- 3.4 WITH ROLLUP — 小计汇总
-- ---------------------------------------------------
-- 在 GROUP BY 末尾加一行"总计"

SELECT
    COALESCE(city, '合计') AS 城市,
    COUNT(*) AS 客户数
FROM customers
GROUP BY city WITH ROLLUP;

-- 多列小计（有层级关系）
SELECT
    COALESCE(city, '所有城市') AS 城市,
    COALESCE(gender, '所有性别') AS 性别,
    COUNT(*) AS 人数
FROM customers
GROUP BY city, gender WITH ROLLUP;

-- ---------------------------------------------------
-- 3.5 GROUP_CONCAT — 组内拼接（MySQL 独有）
-- ---------------------------------------------------
-- 把每组内的某个列拼接成字符串

SELECT
    city,
    COUNT(*) AS 人数,
    GROUP_CONCAT(name ORDER BY name SEPARATOR ', ') AS 客户名单
FROM customers
GROUP BY city
HAVING COUNT(*) >= 5
ORDER BY 人数 DESC;

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：统计 products 表的总行数、有描述的行数（description IS NOT NULL）
-- 你的代码：


-- 题2：查询每个供应商（supplier_id）供应的商品数，按商品数降序排列
-- 你的代码：


-- 题3：查询每个商品分类的平均价格，只显示均价 > 500 的分类
-- 你的代码：


-- 题4：查询 2024 年每个月的订单数和总销售额（提示：用 MONTH(order_date) 或 DATE_FORMAT）
-- 你的代码：


-- 题5：查询客户数 >= 5 的城市，按客户数降序（用 HAVING 过滤）
-- 你的代码：


-- 题6：查询每个订单状态（status）的订单数和总金额
-- 你的代码：


-- 题7：查询每种性别 + VIP 等级的客户数量（多列 GROUP BY）
-- 你的代码：


-- 题8：统计 customers 表中不同城市的数量和客户总人数（用 ROLLUP 给出合计行）
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: WHERE 和 HAVING 的区别？
-- A: ① WHERE 过滤行（分组前），HAVING 过滤组（分组后）
--    ② WHERE 不能用聚合函数，HAVING 可以
--    ③ SQL 执行顺序中 WHERE 在 GROUP BY 之前，HAVING 之后
--    ④ 能放 WHERE 的条件尽量放 WHERE（减少分组数据量，提高性能）
--
-- Q: SQL 语句的完整执行顺序？
-- A: FROM → ON (JOIN) → WHERE → GROUP BY → HAVING →
--    SELECT → DISTINCT → ORDER BY → LIMIT
--    理解这个顺序是写好 SQL 的基础！
--
-- Q: COUNT(*) 和 COUNT(column) 的区别？
-- A: COUNT(*) 统计所有行（含NULL）；COUNT(column) 忽略 NULL 值。
--    COUNT(1) 等价于 COUNT(*)。
--    如果 column 是主键：COUNT(*) ≈ COUNT(column)，都很快。
--    如果 column 可 NULL：COUNT(*) ≠ COUNT(column)，后者少算 NULL 行。
--    一般推荐 COUNT(*)。

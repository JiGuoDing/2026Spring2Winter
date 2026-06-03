-- =====================================================
-- 文件名：02_高级过滤与排序.sql
-- 难度：★★☆☆☆
-- 前置知识：01_基础查询_CRUD
-- 学习时间：约 40 分钟
-- 对应面试考点：条件组合、模糊匹配、分页查询、SQL 执行顺序
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 2.1 AND / OR / NOT — 逻辑运算符
-- ---------------------------------------------------
-- ⚠️ AND 优先级高于 OR！不确定时用括号明确意图

-- AND：同时满足
SELECT name, price, stock
FROM products
WHERE price > 100 AND stock > 100;

-- OR：满足任一
SELECT name, price, stock
FROM products
WHERE price > 5000 OR price < 10;

-- AND 和 OR 混合时必须用括号！
-- ❌ 错误：查价格>100的数码或所有食品
-- SELECT name, category_id, price FROM products
-- WHERE category_id = 1 OR category_id = 3 AND price > 100;
-- 上述实际执行：category_id = 1 OR (category_id = 3 AND price > 100)

-- ✅ 正确：
SELECT name, category_id, price
FROM products
WHERE (category_id = 1 OR category_id = 3) AND price > 100;

-- NOT：取反
SELECT name, price FROM products WHERE NOT (price > 100);
select name, price from products where not (price > 100);
-- 等价于：
SELECT name, price FROM products WHERE price <= 100;

-- ---------------------------------------------------
-- 2.2 LIKE — 模糊匹配
-- ---------------------------------------------------
-- % 匹配任意长度（含0个）字符
-- _ 匹配恰好一个字符

-- 查商品名含"Pro"的商品
SELECT name, price FROM products WHERE name LIKE '%Pro%';

-- 查姓"刘"的客户
SELECT name FROM customers WHERE name LIKE '刘%';

-- 查"王"姓单名的客户
-- * _ 精确匹配一个字符
SELECT name FROM customers WHERE name LIKE '王_';

-- ⚠️ LIKE 以 % 开头的查询无法使用索引（第11章详解）
-- ❌ 慢：LIKE '%Pro'
-- ✅ 快：LIKE 'Pro%'

-- 转义：查含 % 符号的数据（如"100%纯棉"）
-- LIKE '%100\%%' ESCAPE '\'  或  LIKE '%100%%%' ESCAPE '%'

-- ---------------------------------------------------
-- 2.3 IN / NOT IN — 集合匹配
-- ---------------------------------------------------
-- IN 等价于多个 OR，但更简洁，优化器也可能利用索引

-- 查北京、上海、深圳的客户
SELECT name, city FROM customers WHERE city IN ('北京', '上海', '深圳');
select name, city from customers where city in ('北京', '上海', '深圳');

-- NOT IN：排除某些值
SELECT name, city FROM customers WHERE city NOT IN ('北京', '上海');

-- ⚠️ NOT IN 的 NULL 陷阱：如果 IN 列表中有 NULL，整个 NOT IN 返回空集！
-- 原因：x NOT IN (a, b, NULL) → x <> a AND x <> b AND x <> NULL
--       x <> NULL 永远返回 UNKNOWN → 整个条件为 UNKNOWN → 0 行
SELECT COUNT(*) FROM customers WHERE city NOT IN ('北京', NULL);  -- 可能返回0！

-- IN 配合子查询（进阶用法，第06章详解）
-- SELECT name FROM products WHERE category_id IN (SELECT id FROM categories WHERE name = '智能手机');

-- ---------------------------------------------------
-- 2.4 BETWEEN ... AND ... — 范围查询
-- ---------------------------------------------------
-- 包含边界值（闭区间 [a, b]）

-- 价格在 100~1000 之间的商品
SELECT name, price FROM products WHERE price BETWEEN 100 AND 1000;

-- 等价于：
SELECT name, price FROM products WHERE price >= 100 AND price <= 1000;

-- 日期范围（注册日期在 2024 年 1 月）
SELECT name, register_date
FROM customers
WHERE register_date BETWEEN '2024-01-01' AND '2024-01-31';

-- NOT BETWEEN
SELECT name, price FROM products WHERE price NOT BETWEEN 100 AND 1000;

-- ---------------------------------------------------
-- 2.5 ORDER BY — 排序
-- ---------------------------------------------------
-- ASC：升序（默认）  DESC：降序

-- 按价格降序
SELECT name, price FROM products ORDER BY price DESC LIMIT 5;

-- 多列排序：先按分类升序，同分类内按价格降序
SELECT id, name, category_id, price
FROM products
ORDER BY category_id ASC, price DESC
LIMIT 10;

select id, name, category_id, price from products order by category_id asc, price desc limit 10;

-- 按表达式排序
SELECT name, price, stock, (price * stock) AS 库存总价值
FROM products
ORDER BY 库存总价值 DESC
LIMIT 5;

select name, price, stock, (price * stock) as 库存总价值 from products order by 库存总价值 desc limit 5;

-- 按列序号排序（ORDER BY 2 表示按 SELECT 中第2列排序，不推荐，可读性差）
-- SELECT name, price FROM products ORDER BY 2 DESC;

-- NULL 的排序行为：默认 NULL 最小（ASC 时排最前，DESC 时排最后）
SELECT id, name, stock FROM products ORDER BY stock ASC LIMIT 5;

-- ---------------------------------------------------
-- 2.6 LIMIT 与 OFFSET — 分页查询
-- ---------------------------------------------------
-- LIMIT n：返回前 n 行
SELECT name, price FROM products ORDER BY price DESC LIMIT 5;

-- LIMIT n OFFSET m：跳过 m 行，返回 n 行
-- 第 1 页（每页 5 条）
SELECT id, name, price FROM products ORDER BY id LIMIT 5 OFFSET 0;
-- 第 2 页
SELECT id, name, price FROM products ORDER BY id LIMIT 5 OFFSET 5;
-- 第 3 页
SELECT id, name, price FROM products ORDER BY id LIMIT 5 OFFSET 10;

-- 简写：LIMIT m, n（m 是 offset，n 是 limit）
SELECT id, name, price FROM products ORDER BY id LIMIT 5, 5;  -- 第2页

-- ⚠️ 大偏移量分页性能差！OFFSET 100000 LIMIT 10 需要扫描 100010 行
-- 优化方案：使用索引 + WHERE id > last_id LIMIT 10（第11章详解）

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：查询价格大于 100 且库存大于 100 的商品名称和价格
-- 你的代码：

select name as 商品名称, price as 商品价格 from products where price > 100 and stock > 100;

-- 题2：查询分类ID为1或3、且价格小于200的商品（注意括号）
-- 你的代码：

select * from products where (category_id = 1 or category_id = 3) and price < 200;

-- 题3：查询姓名以"王"开头的客户（不限长度）
-- 你的代码：

select name from customers where name like '王%';

-- 题4：查询城市在北京、上海、广州的客户姓名和城市（用 IN）
-- 你的代码：

select name as 客户姓名, city as 城市 from customers where city in ('北京', '上海', '广州');


-- 题5：查询注册日期在 2024年3月 的客户姓名和注册日期
-- 你的代码：

select name as 客户姓名, register_date as 注册日期 from customers where register_date between '2024-03-01' and '2024-03-31';

-- 题6：查询价格最高的 10 件商品，按价格降序排列
-- 你的代码：


-- 题7：查询库存不为 NULL 的商品，按库存升序，显示第 6~10 名（即第2页，每页5条）
-- 你的代码：


-- 题8：查询供应商评分为 NULL 的供应商（IS NULL）
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: AND 和 OR 的优先级谁更高？
-- A: AND 高于 OR。a OR b AND c 等价于 a OR (b AND c)。
--    建议总是用括号明确优先级，增强可读性。
--
-- Q: LIKE '%keyword' 为什么慢？
-- A: 因为 % 开头会导致索引失效（B+Tree 索引依赖前缀匹配）。
--    LIKE 'keyword%' 可以利用索引，LIKE '%keyword%' 或 '%keyword' 则不行。
--
-- Q: BETWEEN 100 AND 200 包含边界值吗？
-- A: 包含，等价于 >= 100 AND <= 200。
--
-- Q: LIMIT 100000, 10 有什么问题？怎么优化？
-- A: 需要扫描前 100010 行再丢弃前 100000 行，越往后越慢。
--    优化：记录上一页最后一条的 id，用 WHERE id > last_id ORDER BY id LIMIT 10。
--
-- Q: ORDER BY 可以按 SELECT 中没有的列排序吗？
-- A: 可以，ORDER BY 可以引用表中任意列，不限于 SELECT 中的列。
--    但如果有 DISTINCT，ORDER BY 的列必须在 SELECT 中。

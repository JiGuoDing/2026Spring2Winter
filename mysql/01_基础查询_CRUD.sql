-- =====================================================
-- 文件名：01_基础查询_CRUD.sql
-- 难度：★☆☆☆☆
-- 前置知识：无（执行 setup.sql 即可）
-- 学习时间：约 45 分钟
-- 对应面试考点：SQL 基础语法、数据操作、NULL 处理
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 1.1 SELECT — 查询数据
-- ---------------------------------------------------
-- SELECT 列名 FROM 表名;
-- * 代表所有列（生产环境避免使用 *，明确列出需要的列）

-- 查所有列（仅限快速预览，正式代码不要用 *）
SELECT * FROM products LIMIT 10;
select * from customers limit 10;

-- 查指定列
SELECT id, name, price FROM products LIMIT 5;

-- 列别名（AS 可省略，但建议保留以提高可读性）
SELECT
    id   AS 商品编号,
    name AS 商品名称,
    price AS 售价
FROM products
LIMIT 5;

select id as 商品编号, name as 客户姓名, city as 所在城市 from customers limit 5;

-- ---------------------------------------------------
-- 1.2 SELECT DISTINCT — 去重查询
-- ---------------------------------------------------
-- 查所有商品分类ID（含重复）
SELECT category_id as 商品类别 FROM products LIMIT 10;

-- 去重后查有商品的分类
SELECT DISTINCT category_id as 商品类别 FROM products;

-- 多列去重：组合唯一的 (city, gender)
SELECT DISTINCT city as 所在城市, gender as 性别 FROM customers;

-- ---------------------------------------------------
-- 1.3 WHERE — 条件筛选
-- ---------------------------------------------------
-- 比较运算符：=  <>  >  <  >=  <=

-- 等值查询
SELECT name as 商品名称, price as 商品价格 FROM products WHERE price = 6999.00;

-- 范围查询
SELECT name as 商品名称, price as 商品价格 FROM products WHERE price > 5000;

-- 不等于（两种写法等价，<> 更通用）
SELECT name as 商品名称, price as 商品价格 FROM products WHERE price <> 0.01;
SELECT name as 客户姓名, city as 所在城市 FROM customers WHERE city != '北京';

-- ---------------------------------------------------
-- 1.4 NULL 与三值逻辑 ⭐ 重要！
-- ---------------------------------------------------
-- NULL 表示"未知"，不是 0、不是空字符串、不是 false
-- 任何值与 NULL 比较结果都是 NULL（不是 TRUE 也不是 FALSE）
-- SQL 使用三值逻辑：TRUE / FALSE / UNKNOWN

-- * 错误写法：= NULL 永远返回空！（因为 NULL = NULL 结果是 NULL 不是 TRUE）
SELECT * FROM products WHERE description = NULL;  -- 永远0行！

-- 正确写法：IS NULL
SELECT id, name, description FROM products WHERE description IS NULL;

-- IS NOT NULL：查有描述的商品
SELECT id as 商品编号, name as 商品名称 FROM products WHERE description IS NOT NULL;

-- MySQL 特有：<=> 安全等于（NULL <=> NULL 返回 TRUE） < = >
SELECT * FROM products WHERE description <=> NULL;

-- NULL 陷阱示例：NOT IN 遇到 NULL
-- 先看一下有哪些商品分类
SELECT DISTINCT category_id as 类别编号 FROM products;
-- 有些商品的 category_id 是 NULL
SELECT id as 商品编号, name as 商品名称, category_id as 类别编号 FROM products WHERE category_id IS NULL;
-- * ⚠️ 如果子查询中包含 NULL，NOT IN 会返回空集（第06章详解）

-- ---------------------------------------------------
-- 1.5 INSERT — 插入数据
-- ---------------------------------------------------
-- 单行插入（完整列）
INSERT INTO categories (name, parent_id, sort_order)
VALUES ('测试分类', 1, 99);
insert into categories (name, parent_id, sort_order) values ('测试分类', 1, 99);

-- 单行插入（省略有默认值的列）
INSERT INTO categories (name, parent_id)
VALUES ('测试分类2', NULL);

-- 多行插入（效率高于多次单行插入）
INSERT INTO categories (name, parent_id, sort_order) VALUES
('批量分类A', 1, 10),
('批量分类B', 1, 20),
('批量分类C', 2, 10);

-- INSERT ... SELECT（从查询结果插入，常用于数据迁移）
-- 把所有深圳客户的收货地址复制到新"深圳"分类（仅为演示语法）
-- INSERT INTO categories (name, parent_id)
-- SELECT DISTINCT CONCAT('地址-', city), NULL FROM customers WHERE city = '深圳';

-- 验证插入
SELECT id as 商品编号, name as 商品名称, parent_id as 父级ID FROM categories WHERE name LIKE '测试%' OR name LIKE '批量%';

-- ---------------------------------------------------
-- 1.6 UPDATE — 更新数据
-- ---------------------------------------------------
-- ⚠️ 不带 WHERE 的 UPDATE 会更新全表！务必小心！

-- 安全更新（只更新特定行）
UPDATE categories SET sort_order = 100 WHERE name = '测试分类';
update categories set sort_order = 100 where name = '测试分类';

-- 多列更新
UPDATE products
SET stock = stock + 10,       -- 库存+10
    updated_at = NOW()
WHERE id = 1;

-- 验证
SELECT id as 商品编号, name as 商品名称, stock as 库存, updated_at as 更新时间 FROM products WHERE id = 1;

-- 用表达式更新
UPDATE products SET price = price * 1.1 WHERE category_id = 11;  -- 智能手机涨价10%
SELECT id as 商品编号, name as 商品名称, price as 商品价格 FROM products WHERE category_id = 11;

-- 恢复原价
UPDATE products SET price = price / 1.1 WHERE category_id = 11;

-- ---------------------------------------------------
-- 1.7 DELETE — 删除数据
-- ---------------------------------------------------
-- ⚠️ 同样，不带 WHERE 会删除全表！

-- 删除刚插入的测试数据
DELETE FROM categories WHERE name LIKE '测试%' OR name LIKE '批量%';

-- DELETE vs TRUNCATE 的区别：
-- DELETE：逐行删，可回滚（事务中），触发器会触发，有 WHERE 条件，慢
-- TRUNCATE：直接清空表，不可回滚（DDL），触发器不触发，无条件，快
-- TRUNCATE TABLE audit_log;  -- 清空审计日志（仅示例，不执行）

-- 验证删除
SELECT COUNT(*) FROM categories WHERE name LIKE '测试%';  -- 应为 0

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：查询所有客户姓名和城市，列别名分别为"姓名"和"城市"
-- 你的代码：

select name as 姓名, city as 城市 from customers;

-- 题2：查询所有不重复的城市名（从 customers 表）
-- 你的代码：

select distinct city as 城市 from customers;

-- 题3：查询价格在 100 到 500 元之间的商品名称和价格
-- 你的代码：

select name as 商品名称, price as 商品价格 from products where price BETWEEN 100 and 500;

-- 题4：查询所有没有填写邮箱的客户姓名和手机号（email IS NULL）
-- 你的代码：

select name as 客户姓名, phone as 手机号 from customers where email is null;

-- 题5：向 suppliers 表插入一条新供应商：名称"测试供应商"，城市"西安"，评分4.0
-- 你的代码：

insert into suppliers (name, city, rating) VALUES ("测试供应商", "西安", 4.0);

-- 题6：将商品ID为48的库存（stock 为 NULL）更新为 0
-- 你的代码：

update products set stock = 1 where id = 48;

describe products;

-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: DELETE 和 TRUNCATE 的区别？
-- A: ① DELETE 是 DML，可回滚；TRUNCATE 是 DDL，不可回滚
--    ② DELETE 可带 WHERE，TRUNCATE 不能
--    ③ DELETE 逐行删除，慢；TRUNCATE 删除整表，快
--    ④ DELETE 会触发触发器，TRUNCATE 不会
--    ⑤ TRUNCATE 会重置 AUTO_INCREMENT，DELETE 不会
--
-- Q: NULL 和空字符串 '' 的区别？
-- A: NULL 表示未知/不存在，'' 表示已知但为空
--    NULL 比较用 IS NULL，不能用 =
--    COUNT(列名) 不统计 NULL，但 COUNT(*) 统计所有行
--
-- Q: SQL 中 = NULL 为什么查不到数据？
-- A: 因为 NULL = NULL 在 SQL 三值逻辑中返回 UNKNOWN 而非 TRUE
--    WHERE 只保留 TRUE 的行，UNKNOWN 被过滤掉
--    正确写法是 IS NULL

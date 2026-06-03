-- =====================================================
-- 文件名：12_视图.sql
-- 难度：★★☆☆☆
-- 前置知识：01~06（JOIN、子查询）
-- 学习时间：约 30 分钟
-- 对应面试考点：视图的作用、可更新视图、WITH CHECK OPTION
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 12.1 创建视图
-- ---------------------------------------------------
-- 视图 = 保存下来的 SELECT 查询，使用时像表一样查询

-- 创建视图：客户订单汇总
CREATE OR REPLACE VIEW v_customer_order_summary AS
SELECT
    c.id              AS customer_id,
    c.name            AS customer_name,
    c.city,
    COUNT(o.id)       AS order_count,
    COALESCE(SUM(o.total_amount), 0) AS total_amount,
    MAX(o.order_date) AS last_order_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name, c.city;

-- 查询视图（就像查表一样）
SELECT * FROM v_customer_order_summary
WHERE order_count > 0
ORDER BY total_amount DESC
LIMIT 10;

-- ---------------------------------------------------
-- 12.2 视图的优势
-- ---------------------------------------------------
-- 1. 简化复杂查询：把复杂的 JOIN+聚合封装成简单 SELECT
-- 2. 权限控制：隐藏敏感列（如只暴露客户的部分信息）
-- 3. 逻辑抽象：底层表结构变化，只需修改视图定义
-- 4. 可读性：给复杂的查询逻辑命名

-- 视图：只暴露客户非敏感信息
CREATE OR REPLACE VIEW v_customer_public AS
SELECT id, name, city, vip_level, register_date
FROM customers;

-- ---------------------------------------------------
-- 12.3 WITH CHECK OPTION
-- ---------------------------------------------------
-- 通过视图做 INSERT/UPDATE 时，确保操作的数据满足视图的 WHERE 条件

-- 创建视图：只看 VIP 客户
CREATE OR REPLACE VIEW v_vip_customers AS
SELECT id, name, city, vip_level
FROM customers
WHERE vip_level >= 3
WITH CHECK OPTION;  -- 确保通过该视图插入/更新的行也满足 vip_level >= 3

-- 如果尝试通过视图插入 vip_level=1 的行 → 报错！
-- INSERT INTO v_vip_customers (name, city, vip_level) VALUES ('测试', '北京', 1);  -- 违反 CHECK OPTION

-- ---------------------------------------------------
-- 12.4 可更新视图的条件
-- ---------------------------------------------------
-- 以下情况视图不可更新（不能通过视图做 INSERT/UPDATE/DELETE）：
-- ❌ 包含 GROUP BY / HAVING
-- ❌ 包含 DISTINCT
-- ❌ 包含聚合函数（COUNT/SUM/AVG 等）
-- ❌ 包含 UNION / UNION ALL
-- ❌ 包含子查询（FROM 中的子查询）
-- ❌ 多表 JOIN（某些情况可更新，但限制很多）

-- v_customer_order_summary 不可更新（有 GROUP BY + 聚合函数）
-- v_customer_public 可更新（单表 + 无聚合）

-- ---------------------------------------------------
-- 12.5 视图管理
-- ---------------------------------------------------

-- 查看视图定义
SHOW CREATE VIEW v_customer_order_summary;

-- 查看所有视图
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS
WHERE TABLE_SCHEMA = 'mysql_tutorial';

-- 删除视图
-- DROP VIEW IF EXISTS v_customer_order_summary;

-- ---------------------------------------------------
-- 12.6 视图 vs 物化视图
-- ---------------------------------------------------
-- 普通视图：不存储数据，每次查询实时执行底层 SELECT（就是"别名"）
-- 物化视图：存储数据副本，定期刷新，查询更快但数据可能过时
-- MySQL 不直接支持物化视图，但可以用 触发器 + 汇总表 模拟
-- Oracle / PostgreSQL 原生支持物化视图（大数据面试可能问）

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：创建一个视图 v_product_list，包含商品名、价格、分类名、供应商名（JOIN 3 表）
-- 你的代码：


-- 题2：基于上一题的视图，查询价格 > 1000 的商品，按价格降序
-- 你的代码：


-- 题3：创建一个 v_beijing_customers 视图（city='北京'），加上 WITH CHECK OPTION
-- 你的代码：


-- 题4：尝试通过 v_beijing_customers 插入一条 city='上海' 的客户，观察结果
-- 你的代码：


-- 题5：修改 v_customer_public 视图，增加 phone 列
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: 视图的优点和使用场景？
-- A: ① 简化复杂查询 ② 权限控制（隐藏列/行）
--    ③ 逻辑抽象（底层表变化不影响上层）
--    场景：报表查询、API 接口的数据库层抽象、多租户数据隔离
--
-- Q: 视图和表的区别？
-- A: 视图不存储数据（逻辑概念），表存储数据（物理概念）
--    表 → 物理存储，视图 → 存储的查询语句
--    对视图的查询实际上是对底层表的查询
--
-- Q: WITH CHECK OPTION 的作用？
-- A: 限制通过视图 INSERT/UPDATE 的数据必须满足视图的 WHERE 条件
--    防止通过视图插入/更新出"看不到"的数据
--
-- Q: 什么时候视图不可更新？
-- A: 包含 GROUP BY、DISTINCT、聚合函数、UNION、子查询、多表 JOIN 时

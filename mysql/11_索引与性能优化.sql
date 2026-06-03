-- =====================================================
-- 文件名：11_索引与性能优化.sql ⭐ 面试必考重点
-- 难度：★★★★☆
-- 前置知识：01~09（需要数据基础）
-- 学习时间：约 70 分钟
-- 对应面试考点：B+Tree、EXPLAIN、最左前缀、索引失效、慢查询优化
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 11.1 索引的本质 — B+Tree
-- ---------------------------------------------------
-- 索引 = 排序好的数据结构，用于加速查找
-- InnoDB 使用 B+Tree 索引：
--   叶子节点存储全部数据（聚簇索引）或主键值（二级索引）
--   叶子节点之间通过双向链表连接 → 支持范围查询
--   非叶子节点只存键值 + 子节点指针 → 树高度低，查找快
--
-- 时间复杂度：O(log n)，3-4 层树可索引千万级数据

-- ---------------------------------------------------
-- 11.2 索引类型
-- ---------------------------------------------------

-- 查看已有索引
SHOW INDEX FROM products;

-- A. 主键索引（聚簇索引 / Clustered Index）
-- InnoDB 中，表数据按主键顺序存储在 B+Tree 的叶子节点中
-- 因此主键索引 = 表数据本身
-- 建议使用自增 ID（保证插入顺序，减少页分裂）

-- B. 二级索引（非聚簇索引 / Secondary Index）
-- 叶子节点存储的是：索引列的值 + 主键值
-- 通过二级索引查找 → 拿到主键 → 回聚簇索引查完整行 = 回表

-- C. 创建索引
CREATE INDEX idx_name ON products(name);                     -- 普通索引
CREATE UNIQUE INDEX idx_unique_email ON customers(email);    -- 唯一索引（前提：数据唯一）
CREATE INDEX idx_composite ON products(category_id, price);  -- 复合索引

-- 删除测试索引（不影响后续演示）
-- DROP INDEX idx_name ON products;
-- DROP INDEX idx_composite ON products;

-- ---------------------------------------------------
-- 11.3 回表查询 与 覆盖索引 ⭐
-- ---------------------------------------------------

-- 回表（两次查找）：
-- SELECT * FROM products WHERE name = 'iPhone 16 Pro Max';
-- ① 走 idx_name 找到 name='iPhone 16 Pro Max' 的索引记录 → 拿到主键 id
-- ② 用主键 id 去聚簇索引找完整行数据 → "回表"

-- 覆盖索引（一次查找，避免回表）：
-- SELECT id, name FROM products WHERE name = 'iPhone 16 Pro Max';
-- ① 走 idx_name 找到记录 → id 和 name 都在索引中 → 不需要回表！
-- EXPLAIN 中显示：Extra: Using index

-- 实战：通过覆盖索引优化查询
EXPLAIN SELECT * FROM products WHERE category_id = 11 AND price > 5000;
-- Extra 可能显示 Using index condition（需要回表）

EXPLAIN SELECT category_id, price FROM products WHERE category_id = 11 AND price > 5000;
-- 如果 idx_category_price 覆盖了查询列，Extra: Using index（覆盖索引）

-- ---------------------------------------------------
-- 11.4 复合索引与最左前缀原则 ⭐⭐⭐ 面试必考
-- ---------------------------------------------------

-- 索引 (a, b, c) 对以下查询有效：
-- ✅ WHERE a = ?                         — 用到 a
-- ✅ WHERE a = ? AND b = ?               — 用到 a, b
-- ✅ WHERE a = ? AND b > ?               — 用到 a, b（范围后 c 失效）
-- ✅ WHERE a = ? AND b = ? AND c = ?     — 用到 a, b, c
-- ✅ WHERE a = ? AND c = ?               — 用到 a（b 缺失，c 无法用）
-- ✅ WHERE a = ? ORDER BY b              — 用到 a，且 ORDER BY 走索引

-- 对以下查询无效（或不完全有效）：
-- ❌ WHERE b = ?                         — 跳过了 a，索引全失效
-- ❌ WHERE b = ? AND c = ?               — 跳过了 a
-- ❌ WHERE a = ? AND c > ?               — 用到 a（c 范围查询但 b 缺失 → c 部分无效）
-- ❌ WHERE a > ? AND b = ?               — a 是范围，b 失效

-- 实验：验证最左前缀（解释计划分析）
EXPLAIN SELECT * FROM products WHERE category_id = 11 AND price > 5000;
-- key: idx_category_price, key_len 显示用了几列
-- 如果只有 category_id + price 都能匹配，key_len 较大

EXPLAIN SELECT * FROM products WHERE price > 5000;
-- key: NULL（或使用 idx_price），因为跳过了 category_id

-- ---------------------------------------------------
-- 11.5 EXPLAIN 执行计划解读 ⭐ 核心技能
-- ---------------------------------------------------

-- EXPLAIN 各字段含义：
-- id：     查询序号（复杂查询可能有多个）
-- select_type：SIMPLE（简单）/ PRIMARY（外层）/ SUBQUERY（子查询）/ DERIVED（派生表）
-- table：  访问的表名
-- type：   连接类型（从好到差）⭐最重要！
--          system > const > eq_ref > ref > range > index > ALL
--          system/const：唯一匹配一行（主键或唯一索引等值查询）
--          eq_ref：每行只匹配另一表的一行（JOIN 用主键/唯一键）
--          ref：索引等值匹配（可能多行）
--          range：索引范围扫描（BETWEEN, >, <, IN）
--          index：全索引扫描（比 ALL 好，依然扫描了全索引）
--          ALL：全表扫描（最差，必须优化）
-- possible_keys：可能使用的索引
-- key：实际使用的索引（NULL 表示没用到索引）
-- key_len：索引使用的字节数（越长说明复合索引利用越充分）
-- ref：和索引比较的值（const / 列名 / func）
-- rows：预估扫描行数（越小越好，但只是估算）
-- filtered：按表条件过滤的行的百分比
-- Extra：额外信息 ⭐
--         Using index：覆盖索引（好！）
--         Using where：WHERE 过滤（正常）
--         Using index condition：ICP 索引下推
--         Using temporary：需要临时表（GROUP BY 无索引 → 差！）
--         Using filesort：需要额外排序（ORDER BY 无索引 → 差！）
--         Using join buffer：JOIN 缓冲

-- 典型的"好"计划：
EXPLAIN SELECT * FROM products WHERE id = 1;
-- type: const, key: PRIMARY, rows: 1

-- 典型的"需要优化"计划：
EXPLAIN SELECT * FROM products WHERE name LIKE '%Pro%';
-- type: ALL（全表扫描），key: NULL

-- 对比：前缀匹配可以用索引
EXPLAIN SELECT * FROM products WHERE name LIKE '华为%';
-- 如果有 idx_name，可能走 range 或 ref

-- ---------------------------------------------------
-- 11.6 索引失效的常见场景 ⭐ 面试高频
-- ---------------------------------------------------

-- 场景1：对索引列使用函数
-- ❌ 索引失效
EXPLAIN SELECT * FROM orders WHERE DATE(order_date) = '2024-01-01';
-- ✅ 改写
EXPLAIN SELECT * FROM orders WHERE order_date >= '2024-01-01' AND order_date < '2024-01-02';

-- 场景2：隐式类型转换
-- ❌ phone 是 VARCHAR 类型，和整数比较会触发类型转换 → 索引失效
EXPLAIN SELECT * FROM customers WHERE phone = 13900000001;
-- ✅ 正确写法
EXPLAIN SELECT * FROM customers WHERE phone = '13900000001';

-- 场景3：LIKE 以 % 开头
-- ❌ 索引失效
EXPLAIN SELECT * FROM products WHERE name LIKE '%Pro';
-- ✅ 前缀匹配可以用索引
EXPLAIN SELECT * FROM products WHERE name LIKE '华为%';

-- 场景4：OR 连接非索引列
-- 如果 OR 两边的列，其中一个没有索引 → 全表扫描
-- ✅ 确保 OR 两边都有索引，或改用 UNION ALL

-- 场景5：NOT IN / <> / !=
-- 大多数情况下不走索引（代价估算器觉得全表扫描更快）
-- 如果查询范围小，可能仍走 range

-- 场景6：联合索引不满足最左前缀（见 11.4）

-- ---------------------------------------------------
-- 11.7 慢查询日志
-- ---------------------------------------------------

-- 开启慢查询日志（需要 SUPER 权限）
-- SET GLOBAL slow_query_log = ON;
-- SET GLOBAL long_query_time = 1;  -- 超过 1 秒的查询被记录
-- SET GLOBAL log_queries_not_using_indexes = ON;

-- 查看慢查询日志位置
-- SHOW VARIABLES LIKE 'slow_query_log_file';

-- 使用 mysqldumpslow 分析（shell 命令）
-- mysqldumpslow -s t -t 10 /var/log/mysql/slow.log  -- 按时间排序 TOP 10

-- ---------------------------------------------------
-- 11.8 索引设计建议
-- ---------------------------------------------------

-- 哪些列适合建索引：
-- 1. WHERE 条件中频繁使用的列
-- 2. JOIN 连接列
-- 3. ORDER BY / GROUP BY 的列
-- 4. 频繁查询且选择性高（不同值多）的列

-- 哪些情况不适合：
-- 1. 表很小（< 1000 行）→ 全表扫描可能更快
-- 2. 频繁更新的列 → 维护索引开销大
-- 3. 选择性低的列（如性别只有男/女）→ 索引效果差
-- 4. 大字段（TEXT/BLOB）→ 考虑前缀索引

-- 前缀索引：只索引列的前 N 个字符
-- CREATE INDEX idx_desc ON products(description(20));

-- ---------------------------------------------------
-- 11.9 分区表（Partitioning）概念
-- ---------------------------------------------------
-- 将大表按某种规则拆分成多个物理子表，但逻辑上仍是一张表
-- 分区键查询时可以"分区裁剪"，只扫描相关分区
-- RANGE 分区：按日期范围（最常用）
-- LIST 分区：按枚举值（如地区）
-- HASH 分区：按哈希值均匀分布

-- 示例（不执行，仅为概念演示）：
-- CREATE TABLE orders_partitioned (
--     id INT, order_date DATE, ...
-- ) PARTITION BY RANGE (YEAR(order_date)) (
--     PARTITION p2023 VALUES LESS THAN (2024),
--     PARTITION p2024 VALUES LESS THAN (2025),
--     PARTITION p2025 VALUES LESS THAN (2026),
--     PARTITION p_future VALUES LESS THAN MAXVALUE
-- );

-- 分区与分库分表的区别：
-- 分区：在同一个 MySQL 实例内物理拆分，对应用透明
-- 分库分表：拆分到不同 MySQL 实例/库/表，需要应用层路由
--          (如 ShardingSphere, MyCat, Vitess)

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：查看 orders 表上的索引（SHOW INDEX FROM orders）
-- 你的代码：


-- 题2：用 EXPLAIN 分析以下查询，观察 type 和 key
-- SELECT * FROM orders WHERE customer_id = 5;
-- 你的代码：


-- 题3：用 EXPLAIN 分析：SELECT * FROM products WHERE price > 100;
-- 观察是否使用 idx_price，对比没有索引时的差异
-- 你的代码：


-- 题4：创建一个覆盖索引优化以下查询：
-- SELECT customer_id, order_date FROM orders WHERE customer_id = 10 AND status = 'delivered';
-- 提示：创建 (customer_id, status, order_date) 的复合索引
-- 你的代码：


-- 题5：下面这条 SQL 为什么索引失效？如何优化？
-- EXPLAIN SELECT * FROM orders WHERE YEAR(order_date) = 2024;
-- 你的回答和优化代码：


-- 题6：写出以下 SQL 的优化方案（LIKE '%keyword' 索引失效）
-- SELECT * FROM products WHERE name LIKE '%Pro';
-- 你的回答：


-- 题7：分析以下 EXPLAIN 结果，判断是否有优化的必要
-- type=ALL, key=NULL, rows=100000
-- 你的判断：


-- 题8：如果有人想对 gender（男/女/未知）列建索引，你会怎么建议？
-- 你的回答：


-- 题9：EXPLAIN SELECT ... Extra 显示 Using filesort，说明什么问题？
-- 你的回答：


-- 题10：查询 orders 表中 customer_id=5 的最早 5 个订单
-- 用 EXPLAIN 验证是否使用了 idx_customer_date 索引
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: 什么是回表？如何避免回表？
-- A: 二级索引查完后需要回到聚簇索引取完整数据叫回表
--    避免方法：覆盖索引（SELECT 的列全部包含在索引中）
--    覆盖索引的 Extra 显示 Using index
--
-- Q: 什么是最左前缀原则？举例说明。
-- A: 复合索引 (a, b, c) 按列顺序从左到右匹配
--    必须从最左边的 a 开始且不能跳过中间列
--    WHERE a=1 AND c=3 → 只用到 a，c 无法利用索引
--    WHERE b=2 → 完全用不到索引
--
-- Q: 执行计划 type 从好到差的顺序？
-- A: system > const > eq_ref > ref > range > index > ALL
--    目标至少达到 range 级别，最好 ref 或以上
--
-- Q: 索引是不是越多越好？
-- A: 不是！索引需要维护（INSERT/UPDATE/DELETE 时需要更新索引）
--    索引占用磁盘空间
--    优化器选择索引也需要时间
--    一般单表索引控制在 5-8 个以内
--
-- Q: UNION ALL 和 UNION 哪个快？
-- A: UNION ALL 快，因为它不做去重（不需要临时表+排序）
--    如果确定结果无重复或允许重复，优先用 UNION ALL

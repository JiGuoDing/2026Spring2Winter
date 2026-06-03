-- =====================================================
-- 文件名：16_约束与外键.sql
-- 难度：★★★☆☆
-- 前置知识：setup.sql 中的建表逻辑
-- 学习时间：约 35 分钟
-- 对应面试考点：约束类型、外键级联、CHECK 约束、约束 vs 应用层
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 16.1 PRIMARY KEY — 主键约束
-- ---------------------------------------------------
-- 特点：唯一 + 非空，每表只能有一个
-- 主键自动创建聚簇索引（InnoDB）

CREATE TABLE demo_pk (
    id   INT PRIMARY KEY,                -- 列级定义
    name VARCHAR(50)
);

-- 等价于：
-- CREATE TABLE demo_pk (
--     id   INT,
--     name VARCHAR(50),
--     PRIMARY KEY (id)                   -- 表级定义（可定义复合主键）
-- );

-- 复合主键
CREATE TABLE demo_composite_pk (
    order_id   INT,
    product_id INT,
    quantity   INT,
    PRIMARY KEY (order_id, product_id)   -- 联合主键
);

DROP TABLE IF EXISTS demo_pk, demo_composite_pk;

-- ---------------------------------------------------
-- 16.2 UNIQUE — 唯一约束
-- ---------------------------------------------------
-- 特点：值不能重复，但允许多个 NULL
-- MySQL 中 UNIQUE 约束自动创建唯一索引

-- 示例：customers 表的 email 有 UNIQUE 索引
-- 尝试插入重复 email → 报错
-- INSERT INTO customers (name, email) VALUES ('测试', 'zhangwei@email.com');
-- Error: Duplicate entry 'zhangwei@email.com' for key 'idx_email'

-- ---------------------------------------------------
-- 16.3 NOT NULL — 非空约束
-- ---------------------------------------------------
-- 特点：列不能为 NULL
-- 在定义时直接加 NOT NULL 即可

-- 尝试插入 NULL → 报错
-- INSERT INTO customers (name, email) VALUES (NULL, 'test@test.com');
-- Error: Column 'name' cannot be null

-- ---------------------------------------------------
-- 16.4 FOREIGN KEY — 外键约束
-- ---------------------------------------------------
-- 保证引用完整性：子表的列值必须在父表中存在（或为 NULL）

-- 级联操作详解：
-- ON DELETE CASCADE：  父表删除，子表跟着删
-- ON DELETE SET NULL： 父表删除，子表外键置 NULL
-- ON DELETE RESTRICT： 父表有子记录时禁止删除（默认）
-- ON DELETE NO ACTION：与 RESTRICT 类似（但有细微的事务内差异）

-- ON UPDATE CASCADE：  父表主键更新，子表外键跟着更新
-- ON UPDATE SET NULL： 父表主键更新，子表外键置 NULL

-- 演示：orders 表有外键指向 customers
-- ON DELETE RESTRICT → 有订单的客户不能直接删除
-- DELETE FROM customers WHERE id = 1;  -- 报错：有订单引用

-- 演示外键约束
-- 插入一个不存在的 customer_id → 报错
-- INSERT INTO orders (customer_id, order_date) VALUES (99999, NOW());
-- Error: Cannot add or update a child row: a foreign key constraint fails

-- ---------------------------------------------------
-- 16.5 CHECK 约束（MySQL 8.0.16+）
-- ---------------------------------------------------
-- 在插入/更新时检查条件，不满足则拒绝

-- 创建带 CHECK 约束的测试表
CREATE TABLE demo_check (
    id     INT PRIMARY KEY AUTO_INCREMENT,
    name   VARCHAR(50) NOT NULL,
    age    INT CHECK (age >= 0 AND age <= 150),
    status VARCHAR(20) CHECK (status IN ('active', 'inactive', 'suspended')),
    price  DECIMAL(10,2) CHECK (price > 0)
);

-- 合法插入
INSERT INTO demo_check (name, age, status, price) VALUES ('张三', 25, 'active', 99.00);

-- 违法插入 → 报错
-- INSERT INTO demo_check (name, age, status, price) VALUES ('李四', -5, 'active', 99.00);
-- Error: Check constraint is violated

-- INSERT INTO demo_check (name, age, status, price) VALUES ('王五', 30, 'unknown', 99.00);
-- Error: Check constraint is violated

DROP TABLE IF EXISTS demo_check;

-- ---------------------------------------------------
-- 16.6 DEFAULT — 默认值
-- ---------------------------------------------------
-- 插入时如果不提供该列的值，使用默认值

-- 示例：orders.status 默认 'pending'，created_at 默认 CURRENT_TIMESTAMP
INSERT INTO orders (customer_id) VALUES (1);  -- 其他列自动取默认值
SELECT * FROM orders WHERE id = LAST_INSERT_ID();
-- 清理
DELETE FROM orders WHERE id = LAST_INSERT_ID();

-- ---------------------------------------------------
-- 16.7 AUTO_INCREMENT — 自增列
-- ---------------------------------------------------
-- 自动递增生成唯一整数值，通常用于主键

-- 查看当前自增值
SELECT AUTO_INCREMENT FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'mysql_tutorial' AND TABLE_NAME = 'products';

-- 手动设置自增起始值
-- ALTER TABLE products AUTO_INCREMENT = 100;

-- ---------------------------------------------------
-- 16.8 约束在数据库层 vs 应用层
-- ---------------------------------------------------
-- 数据库层约束（推荐）：
-- ✅ 数据完整性由 DB 保证，不会因应用 Bug 产生脏数据
-- ✅ 多应用共享时统一约束
-- ❌ 性能开销（尤其外键检查）
-- ❌ 灵活性降低（某些批量操作被约束拦住）

-- 应用层校验（很多团队的实践）：
-- ✅ 灵活性高，错误提示更友好
-- ✅ 减少数据库负担
-- ❌ 多应用可能不一致
-- ❌ 直接操作数据库（如数据迁移）可能跳过校验

-- 常见取舍：
-- 互联网公司：通常在应用层做校验，数据库层不建外键
-- 传统企业/金融：数据库层完整约束，确保数据完整性
-- 折中方案：保留 NOT NULL、UNIQUE、CHECK，外键可选

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：创建一个表 demo_student，包含：
-- id 主键自增、name 非空、email 唯一、age (0~120 CHECK)、status DEFAULT 'active'
-- 你的代码：


-- 题2：尝试插入两条 email 相同的记录，观察报错信息
-- 你的代码：


-- 题3：尝试插入 age=200 的记录，观察 CHECK 约束报错
-- 你的代码：


-- 题4：概念题：ON DELETE CASCADE 和 ON DELETE SET NULL 的区别？
-- 你的回答：


-- 题5：概念题：为什么不建议在生产环境大量使用外键约束？
-- 你的回答：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: PRIMARY KEY 和 UNIQUE 的区别？
-- A: PRIMARY KEY = UNIQUE + NOT NULL，且每表只能有一个
--    UNIQUE 允许 NULL，允许多个 UNIQUE 约束
--
-- Q: 外键的级联操作有哪些？
-- A: ON DELETE/UPDATE:
--    CASCADE：级联操作（父删子删，父改子改）
--    SET NULL：置为 NULL（需要外键列允许 NULL）
--    RESTRICT/NO ACTION：拒绝操作
--
-- Q: MySQL 的 CHECK 从哪个版本开始真正生效？
-- A: MySQL 8.0.16+，之前版本语法上允许但实际被忽略
--
-- Q: 自增主键用完了怎么办？
-- A: INT 自增约 21 亿，BIGINT 约 922 亿亿
--    如果是 INT：ALTER TABLE ... MODIFY id BIGINT AUTO_INCREMENT
--    提前规划用 BIGINT

-- =====================================================
-- 16_约束与外键 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：创建 demo_student 表
CREATE TABLE IF NOT EXISTS demo_student (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    age INT CHECK (age >= 0 AND age <= 120),
    status VARCHAR(20) DEFAULT 'active'
);

-- 题2：插入重复 email
-- INSERT INTO demo_student (name, email, age) VALUES ('A', 'test@test.com', 20);
-- INSERT INTO demo_student (name, email, age) VALUES ('B', 'test@test.com', 22);
-- Error: Duplicate entry

-- 题3：插入 age=200
-- INSERT INTO demo_student (name, email, age) VALUES ('C', 'c@test.com', 200);
-- Error: Check constraint violated

-- 题4：CASCADE vs SET NULL
-- CASCADE：父表删除/更新时，子表的引用行也自动删除/更新
-- SET NULL：父表删除/更新时，子表的外键列置为 NULL（要求外键列允许NULL）

-- 题5：为什么不建议大量使用外键
-- ① 性能开销：每次INSERT/UPDATE都要检查引用完整性
-- ② 分库分表时外键无法跨库
-- ③ 批量操作时维护外键影响效率
-- ④ 互联网大流量场景下通常在应用层保证数据一致性

DROP TABLE IF EXISTS demo_student;

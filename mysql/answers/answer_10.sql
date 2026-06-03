-- =====================================================
-- 10_事务与隔离级别 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：查看默认隔离级别
SELECT @@transaction_isolation;

-- 题2：事务 + SAVEPOINT
START TRANSACTION;
INSERT INTO suppliers (name, city, rating) VALUES ('测试A', '北京', 4.0);
SAVEPOINT sp1;
INSERT INTO suppliers (name, city, rating) VALUES ('测试B', '上海', 3.0);
ROLLBACK TO SAVEPOINT sp1;  -- 测试B撤销
COMMIT;  -- 只保留测试A
-- 清理
DELETE FROM suppliers WHERE name IN ('测试A', '测试B');

-- 题3：脏读、不可重复读、幻读
-- 脏读：读到其他事务未提交的数据
-- 不可重复读：同一事务内两次读同一行，结果不同（其他事务提交了UPDATE）
-- 幻读：同一事务内两次查同一范围，结果行数不同（其他事务提交了INSERT）

-- 题4：InnoDB REPEATABLE READ 为什么基本解决幻读
-- 通过 Next-Key Lock（记录锁 + 间隙锁）锁定索引间隙
-- 防止其他事务在间隙中插入新行
-- 仅对"当前读"（SELECT ... FOR UPDATE）生效

-- 题5：FOR UPDATE 锁定行
-- START TRANSACTION;
-- SELECT * FROM products WHERE id = 1 FOR UPDATE;
-- COMMIT;

-- 题6：MVCC 核心原理
-- 每条记录维护多个版本（通过 Undo Log）
-- 每个事务有独立的 ReadView（快照）
-- 根据 ReadView 判断当前事务应该看到哪个版本的数据
-- REPEATABLE READ: 事务开始时创建 ReadView，整个事务使用同一个
-- READ COMMITTED: 每次查询创建新的 ReadView

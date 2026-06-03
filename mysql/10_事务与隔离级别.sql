-- =====================================================
-- 文件名：10_事务与隔离级别.sql
-- 难度：★★★★☆
-- 前置知识：01_基础查询_CRUD（有基础概念即可）
-- 学习时间：约 55 分钟
-- 对应面试考点：ACID、隔离级别、MVCC、脏读/不可重复读/幻读、死锁
-- =====================================================

-- ⚠️ 本章需要开两个终端同时操作来观察并发行为
-- 终端A 执行部分语句，终端B 执行另一部分
-- 文件中对每个并发实验都有标注

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 10.1 ACID 四大特性（概念必考）
-- ---------------------------------------------------
-- A - Atomicity  原子性：事务要么全部成功，要么全部回滚（Undo Log）
-- C - Consistency 一致性：事务前后数据满足所有约束
-- I - Isolation   隔离性：并发事务之间互不干扰（锁 + MVCC）
-- D - Durability  持久性：事务提交后永久保存（Redo Log）

-- ---------------------------------------------------
-- 10.2 事务基本操作
-- ---------------------------------------------------

-- 开启事务的三种方式：
START TRANSACTION;  -- 推荐
-- BEGIN;            -- 等价
-- BEGIN WORK;       -- 等价

-- 示例：转账操作（事务保证原子性）
-- START TRANSACTION;
-- UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- UPDATE accounts SET balance = balance + 100 WHERE id = 2;
-- COMMIT;  -- 确认提交
-- 如果中间出错：
-- ROLLBACK;  -- 回滚所有操作

-- ---------------------------------------------------
-- 10.3 SAVEPOINT — 部分回滚
-- ---------------------------------------------------

START TRANSACTION;

UPDATE products SET price = price + 10 WHERE id = 1;
SAVEPOINT sp1;  -- 设置保存点

UPDATE products SET price = price + 20 WHERE id = 2;
SAVEPOINT sp2;

UPDATE products SET price = price + 30 WHERE id = 3;

-- 回滚到 sp2：id=3 的更新撤销，id=1,2 的保留
ROLLBACK TO SAVEPOINT sp2;

-- 提交（只保留 id=1,2 的更新）
COMMIT;

-- 恢复数据
UPDATE products SET price = 6999.00 WHERE id = 1;
UPDATE products SET price = 5999.00 WHERE id = 2;

-- ---------------------------------------------------
-- 10.4 四种隔离级别 ⭐ 面试必考
-- ---------------------------------------------------

-- 查看当前隔离级别
SELECT @@transaction_isolation;
-- InnoDB 默认：REPEATABLE-READ

-- 设置隔离级别（当前会话）
-- SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
-- SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
-- SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
-- SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- ---------------------------------------------------
-- 10.5 并发问题演示（需要两个终端）
-- ---------------------------------------------------

-- ===== 实验1：脏读（Read Uncommitted 下出现）=====
-- 【终端A】
-- SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
-- START TRANSACTION;
-- UPDATE products SET price = 99999 WHERE id = 1;  -- 未提交
-- -- 先不要 COMMIT

-- 【终端B】
-- SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
-- SELECT price FROM products WHERE id = 1;  -- 读到 99999（脏数据！）

-- 【终端A】
-- ROLLBACK;  -- 回滚了

-- 【终端B】
-- SELECT price FROM products WHERE id = 1;  -- 又变回 6999（读到脏数据！）

-- ===== 实验2：不可重复读（Read Committed 下出现）=====
-- 【终端A】（READ COMMITTED）
-- SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
-- START TRANSACTION;
-- SELECT price FROM products WHERE id = 1;  -- 6999

-- 【终端B】提交一个更新
-- UPDATE products SET price = 8888 WHERE id = 1;

-- 【终端A】再次读同一行
-- SELECT price FROM products WHERE id = 1;  -- 8888！和第一次读到的不一样！

-- ===== 实验3：幻读（Repeatable Read 下可能出现）=====
-- 【终端A】MVCC 快照读（普通 SELECT）不会幻读
-- 【终端A】当前读（SELECT ... FOR UPDATE）可能产生幻读
-- （InnoDB 用 Next-Key Lock 在 REPEATABLE READ 下基本解决了幻读）

-- ---------------------------------------------------
-- 10.6 隔离级别对照表
-- ---------------------------------------------------
-- 隔离级别           脏读    不可重复读    幻读
-- READ UNCOMMITTED    ✓         ✓          ✓
-- READ COMMITTED      ✗         ✓          ✓
-- REPEATABLE READ     ✗         ✗       ✓(InnoDB基本解决)
-- SERIALIZABLE        ✗         ✗          ✗

-- ---------------------------------------------------
-- 10.7 MVCC 多版本并发控制（概念）
-- ---------------------------------------------------
-- 核心思想：读不阻塞写，写不阻塞读
-- 每条记录维护多个版本，通过 Undo Log 实现
-- ReadView（快照）决定事务能看到哪个版本的数据
-- REPEATABLE READ：事务开始时创建 ReadView，整个事务用同一个
-- READ COMMITTED：  每次查询都创建新的 ReadView

-- ---------------------------------------------------
-- 10.8 锁
-- ---------------------------------------------------

-- 共享锁（S锁/读锁）— 允许其他事务读，不允许写
-- SELECT ... FOR SHARE;           -- MySQL 8.0+
-- SELECT ... LOCK IN SHARE MODE;  -- 旧版语法

-- 排他锁（X锁/写锁）— 不允许其他事务读和写（除快照读外）
-- SELECT ... FOR UPDATE;

-- 意向锁（IS/IX）：表级锁，用于协调行锁和表锁
-- 记录锁（Record Lock）：锁定单行索引记录
-- 间隙锁（Gap Lock）：锁定索引间隙（防止插入）
-- Next-Key Lock：记录锁 + 间隙锁（InnoDB 解决幻读的关键）

-- ---------------------------------------------------
-- 10.9 死锁
-- ---------------------------------------------------

-- 死锁示例（两个事务互相等待对方释放锁）：
-- 【终端A】START TRANSACTION;
-- 【终端A】UPDATE products SET price = 1 WHERE id = 1;  -- 获得 id=1 的 X 锁
-- 【终端B】START TRANSACTION;
-- 【终端B】UPDATE products SET price = 2 WHERE id = 2;  -- 获得 id=2 的 X 锁
-- 【终端A】UPDATE products SET price = 2 WHERE id = 2;  -- 等待 B 释放
-- 【终端B】UPDATE products SET price = 1 WHERE id = 1;  -- 等待 A 释放 → 死锁！
-- MySQL 会自动检测并回滚其中一个事务

-- 查看死锁信息：
-- SHOW ENGINE INNODB STATUS;

-- 避免死锁的方法：
-- 1. 按相同顺序访问资源（先锁 A 再锁 B，大家都一样）
-- 2. 保持事务短小
-- 3. 尽量使用索引（减少锁范围）

-- =====================================================
-- 第二部分：练习题（概念题为主）
-- =====================================================

-- 题1：查看当前 MySQL 的默认隔离级别
-- 你的代码：


-- 题2：开启事务，插入一条 supplier 记录，设置保存点，再插入一条，回滚到保存点，提交
-- 你的代码：


-- 题3：概念题：请简述脏读、不可重复读、幻读的区别
-- 你的回答：


-- 题4：概念题：为什么 InnoDB 在 REPEATABLE READ 下也能基本解决幻读？
-- 你的回答：


-- 题5：用 FOR UPDATE 查询 id=1 的商品并锁定该行
-- 你的代码：


-- 题6：概念题：MVCC 的核心原理是什么？
-- 你的回答：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: 请解释 ACID 各代表什么？
-- A: Atomicity 原子性：事务是不可分割的最小单元（Undo Log 实现）
--    Consistency 一致性：事务前后数据完整性不破坏
--    Isolation 隔离性：并发事务互不干扰（锁 + MVCC）
--    Durability 持久性：提交后数据永久保存（Redo Log 实现）
--
-- Q: MySQL 默认隔离级别是什么？为什么选它？
-- A: REPEATABLE READ。原因：
--    ① 避免了脏读和不可重复读
--    ② InnoDB 用 Next-Key Lock 基本解决了幻读
--    ③ 不会像 SERIALIZABLE 那样严重降低并发性能
--    ④ 满足大多数业务场景的一致性需求
--
-- Q: 什么是幻读？InnoDB 怎么解决？
-- A: 幻读：同一事务内，两次查询同一范围，第二次多出了新插入的行
--    InnoDB 用 Next-Key Lock（记录锁+间隙锁）锁定索引间隙
--    防止其他事务在间隙中插入新行 → 避免了幻读
--    但只对"当前读"（FOR UPDATE）生效，快照读（普通 SELECT）通过 MVCC 实现
--
-- Q: 共享锁和排他锁的区别？
-- A: S 锁：允许其他事务加 S 锁（可并发读），阻止 X 锁
--    X 锁：阻止其他事务加任何锁（排他）
--    SELECT 默认不加锁（快照读）
--    SELECT ... FOR SHARE 加 S 锁
--    SELECT ... FOR UPDATE 加 X 锁
--    UPDATE/DELETE/INSERT 自动加 X 锁

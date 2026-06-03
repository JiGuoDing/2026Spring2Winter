-- =====================================================
-- 文件名：17_数据库设计范式.sql
-- 难度：★★★★☆
-- 前置知识：01~16 综合
-- 学习时间：约 45 分钟
-- 对应面试考点：三大范式、反范式化、ER 模型、数据库设计实战
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 17.1 第一范式（1NF）：原子性
-- ---------------------------------------------------
-- 规则：每个列不可再分，每列都是原子值

-- ❌ 违反 1NF 的例子：
-- customers 表中有个列 phone_numbers，存 "13900001111,13900002222"
-- 这违反了原子性（一个字段存了多个电话号码）

-- ✅ 符合 1NF：
-- 方案1：把多个电话号码拆成 phone1, phone2 列（不推荐，不灵活）
-- 方案2：新建 customer_phones 表（推荐！）
--   CREATE TABLE customer_phones (
--       customer_id INT,
--       phone VARCHAR(20),
--       type VARCHAR(10),   -- 手机/座机/工作电话
--       PRIMARY KEY (customer_id, phone)
--   );

-- ---------------------------------------------------
-- 17.2 第二范式（2NF）：消除部分依赖
-- ---------------------------------------------------
-- 规则：非主属性必须完全依赖于候选键（不能只依赖部分主键）
-- 仅当存在复合主键时，2NF 才有意义

-- ❌ 违反 2NF 的例子（假设)：
-- 订单明细表 (order_id, product_id, product_name, quantity, unit_price)
-- product_name 只依赖于 product_id（部分主键），不依赖于整个 (order_id, product_id)

-- ✅ 符合 2NF：
-- order_items 只存 order_id, product_id, unit_price, quantity
-- product_name 存在 products 表中，通过 product_id 关联

-- ---------------------------------------------------
-- 17.3 第三范式（3NF）：消除传递依赖
-- ---------------------------------------------------
-- 规则：非主属性不能依赖于其他非主属性
--     （非主属性必须直接依赖于候选键）

-- ❌ 违反 3NF 的例子：
-- orders 表中加 customer_city 列
-- customer_city 依赖于 customer_id（非主属性）
-- 而 customer_id 又依赖于 order_id（主键）
-- 这就形成了传递依赖：order_id → customer_id → customer_city

-- ✅ 符合 3NF：
-- orders 只存 customer_id
-- customer_city 在 customers 表中，需要时通过 JOIN 查询

-- ---------------------------------------------------
-- 17.4 BCNF（巴斯-科德范式）
-- ---------------------------------------------------
-- 规则：每一个决定因素都包含候选键
-- 3NF 的加强版，解决了 3NF 无法解决的部分特殊情况
-- 大多数场景下 3NF 就够了

-- ---------------------------------------------------
-- 17.5 反范式化：什么时候故意违反范式？
-- ---------------------------------------------------
-- 范式化 = 减少冗余 = 更多表 = 更多 JOIN = 查询变慢
-- 反范式化 = 适当冗余 = 减少 JOIN = 查询变快

-- 反范式化案例1：订单表冗余客户姓名
-- 订单列表页通常需要显示 customer_name
-- 范式的做法：SELECT o.*, c.name FROM orders o JOIN customers c
-- 反范式化：orders 表直接加 customer_name 列
-- 代价：客户改名时需要更新所有历史订单

-- 反范式化案例2：汇总表/统计表
-- 报表需要"每日销售额"统计
-- 范式的做法：每次实时聚合 orders + order_items
-- 反范式化：建 daily_sales_summary 表，定时写入
-- CREATE TABLE daily_sales_summary (
--     stat_date   DATE PRIMARY KEY,
--     order_count INT,
--     total_amount DECIMAL(14,2),
--     avg_amount   DECIMAL(10,2)
-- );

-- 反范式化原则：
-- 1. 优先满足 3NF，设计出"正确"的数据模型
-- 2. 识别性能瓶颈（慢查询、高并发报表）
-- 3. 有目的地做反范式化，并注释清楚冗余的原因
-- 4. 确保数据一致性（用触发器/定时任务/应用代码维护冗余数据）

-- ---------------------------------------------------
-- 17.6 ER 模型设计实战
-- ---------------------------------------------------
-- 场景：设计一个"在线教育平台"的数据库

-- 需求分析：
-- 1. 平台有多个课程，每个课程属于一个分类
-- 2. 讲师可以创建课程，一个讲师可以讲多门课
-- 3. 学生可以购买课程，一个学生可以买多门课
-- 4. 每门课有多个章节，每个章节有多个课时
-- 5. 学生学习每个课时后有完成记录

-- 实体识别：学生、讲师、课程、分类、章节、课时、订单
-- 关系识别：
--   分类 1:N 课程
--   讲师 1:N 课程
--   学生 N:M 课程（通过订单）
--   课程 1:N 章节
--   章节 1:N 课时
--   学生 N:M 课时（学习记录）

-- 表结构设计（DDL 概览，不实际创建）：
-- CREATE TABLE edu_categories (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     name VARCHAR(50) NOT NULL,
--     parent_id INT DEFAULT NULL  -- 自引用，支持多级分类
-- );
--
-- CREATE TABLE edu_teachers (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     name VARCHAR(50) NOT NULL,
--     bio TEXT
-- );
--
-- CREATE TABLE edu_students (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     name VARCHAR(50) NOT NULL,
--     email VARCHAR(80) UNIQUE
-- );
--
-- CREATE TABLE edu_courses (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     title VARCHAR(200) NOT NULL,
--     category_id INT,
--     teacher_id INT,
--     price DECIMAL(10,2),
--     created_at DATETIME DEFAULT NOW()
-- );
--
-- CREATE TABLE edu_chapters (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     course_id INT NOT NULL,
--     title VARCHAR(200) NOT NULL,
--     sort_order INT DEFAULT 0
-- );
--
-- CREATE TABLE edu_lessons (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     chapter_id INT NOT NULL,
--     title VARCHAR(200) NOT NULL,
--     video_url VARCHAR(500),
--     duration INT COMMENT '秒',
--     sort_order INT DEFAULT 0
-- );
--
-- CREATE TABLE edu_orders (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     student_id INT NOT NULL,
--     course_id INT NOT NULL,
--     amount DECIMAL(10,2),
--     created_at DATETIME DEFAULT NOW(),
--     UNIQUE KEY (student_id, course_id)  -- 防止重复购买
-- );
--
-- CREATE TABLE edu_learning_records (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     student_id INT NOT NULL,
--     lesson_id INT NOT NULL,
--     watched_seconds INT DEFAULT 0,
--     completed BOOLEAN DEFAULT FALSE,
--     created_at DATETIME DEFAULT NOW(),
--     UNIQUE KEY (student_id, lesson_id)
-- );

-- =====================================================
-- 第二部分：练习题（设计题，写出 DDL 即可）
-- =====================================================

-- 题1：下面这个表违反了什么范式？请修正。
-- orders_full (order_id, customer_id, customer_name, customer_city, product_id, product_name, quantity)
-- 你的分析：


-- 题2：设计"图书馆借阅系统"的数据库：
-- 有书籍、读者、借阅记录。书籍有 ISBN、书名、作者。读者有姓名、手机号。
-- 一个读者可借多本书，一本书一次只能被一个读者借出。
-- 请写出 CREATE TABLE 语句
-- 你的代码：


-- 题3：什么时候应该反范式化？举一个实际例子。
-- 你的回答：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: 三大范式各解决了什么问题？
-- A: 1NF → 原子性：每列不可再分，解决数据冗余的基础问题
--    2NF → 消除部分依赖：非主属性必须完全依赖主键
--    3NF → 消除传递依赖：非主属性不能依赖其他非主属性
--    简单记法：1NF列不可分，2NF完全依赖，3NF直接依赖
--
-- Q: 为什么需要反范式化？
-- A: 范式化的代价是表多 → JOIN 多 → 查询慢
--    在以下场景可以考虑反范式化：
--    ① 高频查询需要多表 JOIN → 冗余部分字段
--    ② 报表/统计需要大量实时聚合 → 预先汇总
--    ③ 历史数据快照（如订单中保存当时的商品价格和名称）
--
-- Q: 数据库设计的一般流程？
-- A: ① 需求分析（有哪些业务实体？）
--    ② 概念设计（ER 图：实体 + 属性 + 关系）
--    ③ 逻辑设计（ER 图 → 表结构 + 范式化）
--    ④ 物理设计（选择存储引擎、建索引、分区策略）
--    ⑤ 实施 + 迭代优化

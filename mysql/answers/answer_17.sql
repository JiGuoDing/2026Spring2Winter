-- =====================================================
-- 17_数据库设计范式 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：orders_full 违反什么范式
-- 违反 2NF：product_name 只依赖 product_id（部分主键），不依赖完整主键 (order_id, product_id)
-- 违反 3NF：customer_name, customer_city 依赖 customer_id（非主属性），
--           而 customer_id 又依赖 order_id（主键）→ 传递依赖
-- 修正：拆分为 orders(customer_id)、customers、products、order_items 四表

-- 题2：图书馆借阅系统
-- CREATE TABLE books (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     isbn VARCHAR(20) UNIQUE NOT NULL,
--     title VARCHAR(200) NOT NULL,
--     author VARCHAR(100)
-- );
-- CREATE TABLE readers (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     name VARCHAR(50) NOT NULL,
--     phone VARCHAR(20)
-- );
-- CREATE TABLE borrow_records (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     reader_id INT NOT NULL,
--     book_id INT NOT NULL,
--     borrow_date DATE NOT NULL,
--     return_date DATE,
--     FOREIGN KEY (reader_id) REFERENCES readers(id),
--     FOREIGN KEY (book_id) REFERENCES books(id),
--     UNIQUE (book_id, return_date)  -- 未归还的书book_id不能重复
-- );

-- 题3：什么时候反范式化
-- 例：电商订单列表页需要显示"订单ID + 客户名 + 商品数 + 总金额"
-- 范式查询：orders JOIN customers JOIN order_items（3表关联，数据量大时慢）
-- 反范式化：orders 表冗余 customer_name、item_count、total_amount
-- 代价：客户改名需更新历史订单，商品变更需重算
-- 适合场景：读多写少、历史数据很少变更

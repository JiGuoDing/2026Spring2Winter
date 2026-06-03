-- =====================================================
-- 文件名：14_自定义函数.sql
-- 难度：★★★☆☆
-- 前置知识：13_存储过程
-- 学习时间：约 30 分钟
-- 对应面试考点：函数 vs 存储过程、确定性函数、UDF
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 14.1 创建标量函数
-- ---------------------------------------------------

-- 简单函数：计算含税价格
DELIMITER //

CREATE FUNCTION fn_tax_price(price DECIMAL(10,2), tax_rate DECIMAL(4,2))
RETURNS DECIMAL(10,2)
DETERMINISTIC   -- 确定性函数（相同输入永远返回相同输出）
READS SQL DATA  -- 读取 SQL 数据（可不加，但明确声明更好）
BEGIN
    RETURN price * (1 + tax_rate);
END //

DELIMITER ;

-- 使用函数（用 SELECT 调用，就像内置函数一样）
SELECT fn_tax_price(100, 0.13) AS 含税价格;  -- 113.00

-- 在查询中使用
SELECT name, price, fn_tax_price(price, 0.13) AS 含税价
FROM products
LIMIT 5;

-- ---------------------------------------------------
-- 14.2 DETERMINISTIC vs NOT DETERMINISTIC
-- ---------------------------------------------------

-- DETERMINISTIC：确定性函数（相同输入 → 永远相同输出）
--   ROUND(3.14, 1) → 永远是 3.1
-- NOT DETERMINISTIC：非确定性函数（相同输入可能不同输出）
--   RAND(), NOW(), UUID()

-- 声明为 DETERMINISTIC 的函数可能被优化器缓存结果
-- 如果实际是非确定性的但声明为 DETERMINISTIC → 结果不正确！

-- ---------------------------------------------------
-- 14.3 实用函数示例
-- ---------------------------------------------------

-- 函数：格式化金额为中文读法
DELIMITER //

CREATE FUNCTION fn_format_money(amount DECIMAL(12,2))
RETURNS VARCHAR(50)
DETERMINISTIC
BEGIN
    IF amount >= 10000 THEN
        RETURN CONCAT(ROUND(amount / 10000, 2), '万元');
    ELSEIF amount >= 1000 THEN
        RETURN CONCAT(ROUND(amount / 1000, 2), '千元');
    ELSE
        RETURN CONCAT(amount, '元');
    END IF;
END //

DELIMITER ;

SELECT
    name,
    price,
    fn_format_money(price) AS 价格展示
FROM products
ORDER BY price DESC
LIMIT 5;

-- 函数：计算客户等级
DELIMITER //

CREATE FUNCTION fn_customer_tier(
    total_spent DECIMAL(12,2),
    order_cnt   INT
)
RETURNS VARCHAR(20)
DETERMINISTIC
BEGIN
    DECLARE tier VARCHAR(20);

    IF total_spent >= 50000 AND order_cnt >= 10 THEN
        SET tier = '钻石会员';
    ELSEIF total_spent >= 20000 AND order_cnt >= 5 THEN
        SET tier = '金牌会员';
    ELSEIF total_spent >= 5000  AND order_cnt >= 3 THEN
        SET tier = '银牌会员';
    ELSEIF total_spent > 0 THEN
        SET tier = '普通会员';
    ELSE
        SET tier = '新用户';
    END IF;

    RETURN tier;
END //

DELIMITER ;

-- 使用
SELECT
    c.name,
    COALESCE(SUM(o.total_amount), 0) AS 总消费,
    COUNT(o.id) AS 订单数,
    fn_customer_tier(COALESCE(SUM(o.total_amount), 0), COUNT(o.id)) AS 会员等级
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY 总消费 DESC
LIMIT 10;

-- 函数：隐藏手机号中间4位（常用于显示脱敏）
DELIMITER //

CREATE FUNCTION fn_mask_phone(phone VARCHAR(20))
RETURNS VARCHAR(20)
DETERMINISTIC
BEGIN
    IF phone IS NULL OR CHAR_LENGTH(phone) < 7 THEN
        RETURN phone;
    END IF;
    RETURN CONCAT(
        LEFT(phone, 3),
        '****',
        RIGHT(phone, 4)
    );
END //

DELIMITER ;

SELECT name, phone, fn_mask_phone(phone) AS 脱敏手机号
FROM customers
WHERE phone IS NOT NULL
LIMIT 5;

-- ---------------------------------------------------
-- 14.4 函数中使用 SELECT 的限制
-- ---------------------------------------------------

-- 函数中可以有 SELECT ... INTO，但不能有返回结果集的 SELECT
-- 也不能在函数中修改数据（INSERT/UPDATE/DELETE）→ 会报错

-- ❌ 错误示例（函数中修改数据）：
-- CREATE FUNCTION fn_bad() RETURNS INT
-- BEGIN
--     UPDATE products SET price = 0;  -- 不允许！
--     RETURN 1;
-- END;

-- ---------------------------------------------------
-- 14.5 函数 vs 存储过程 全面对比
-- ---------------------------------------------------
--              函数                    存储过程
-- 返回值       必须有 RETURNS           通过 OUT/INOUT 参数
-- 调用方式     SELECT func()           CALL proc()
-- 事务         不能 COMMIT/ROLLBACK    可以进行事务控制
-- 修改数据     不能 INSERT/UPDATE/DELETE  可以
-- 返回结果集   不能                     可以（通过 SELECT）
-- 使用场景     计算/转换/格式化         复杂业务逻辑/批量操作
-- SQL 中调用   ✅ 可以（WHERE/SELECT）  ❌ 不可以

-- ---------------------------------------------------
-- 14.6 查看与删除函数
-- ---------------------------------------------------

SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES
WHERE ROUTINE_SCHEMA = 'mysql_tutorial' AND ROUTINE_TYPE = 'FUNCTION';

-- 删除函数
-- DROP FUNCTION IF EXISTS fn_tax_price;

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：创建函数 fn_discount_price(price, discount_pct)，返回折后价
-- discount_pct 是折扣百分比（如 20 表示打8折）
-- 你的代码：


-- 题2：创建函数 fn_product_level(price)，返回商品的文字等级
-- >=5000 → 奢侈，>=1000 → 高端，>=100 → 中端，<100 → 平价
-- 你的代码：


-- 题3：创建函数 fn_age(birth_date DATE)，计算年龄
-- 提示：用 TIMESTAMPDIFF
-- 你的代码：


-- 题4：用第2题的函数查询所有商品的等级分布（按等级分组统计数量）
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: 函数和存储过程的核心区别？
-- A: ① 返回值：函数必须有（RETURNS），存储过程可选（OUT参数）
--    ② 调用：SELECT 调用函数，CALL 调用存储过程
--    ③ 事务：函数内不能控制事务
--    ④ 数据修改：函数不能修改数据
--    ⑤ 使用位置：函数可在 SQL 任何位置使用，存储过程不行
--
-- Q: 什么场景用函数而不是存储过程？
-- A: 需要嵌入在 SQL 语句中使用时（SELECT/WHERE/ORDER BY）
--    纯计算/转换/格式化逻辑（无副作用）
--    需要返回标量值参与运算
--
-- Q: DETERMINISTIC 声明的作用？
-- A: 告知 MySQL 优化器：相同输入永远返回相同输出
--    优化器可能缓存函数结果、用于生成虚拟列的索引等
--    声明错误会导致数据不一致

-- =====================================================
-- 文件名：13_存储过程.sql
-- 难度：★★★☆☆
-- 前置知识：01_基础查询_CRUD, 04_内置函数大全
-- 学习时间：约 55 分钟
-- 对应面试考点：存储过程语法、游标、参数模式、异常处理
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 13.1 基本语法
-- ---------------------------------------------------
-- DELIMITER 用于改变语句分隔符（因为存储过程体内有 ;，需要区分）
-- DELIMITER 的使用是 MySQL 客户端的特性，不是 SQL 语法本身

-- 最简单的存储过程
DELIMITER //

CREATE PROCEDURE sp_hello()
BEGIN
    SELECT 'Hello MySQL!' AS greeting;
END //

DELIMITER ;

-- 调用
CALL sp_hello();

-- ---------------------------------------------------
-- 13.2 参数模式：IN / OUT / INOUT
-- ---------------------------------------------------

-- IN 参数（默认）：传入值
DELIMITER //

CREATE PROCEDURE sp_get_products_by_price(
    IN min_price DECIMAL(10,2)
)
BEGIN
    SELECT name, price
    FROM products
    WHERE price >= min_price
    ORDER BY price;
END //

DELIMITER ;

CALL sp_get_products_by_price(5000);

-- OUT 参数：传出值
DELIMITER //

CREATE PROCEDURE sp_count_orders(
    IN  cust_id INT,
    OUT cnt     INT,
    OUT total   DECIMAL(12,2)
)
BEGIN
    SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
    INTO cnt, total
    FROM orders
    WHERE customer_id = cust_id;
END //

DELIMITER ;

-- 调用 OUT 参数（需要用变量接收）
CALL sp_count_orders(1, @order_cnt, @total_spent);
SELECT @order_cnt AS 订单数, @total_spent AS 总消费;

-- INOUT 参数：既传入又传出
DELIMITER //

CREATE PROCEDURE sp_double(INOUT num INT)
BEGIN
    SET num = num * 2;
END //

DELIMITER ;

SET @x = 5;
CALL sp_double(@x);
SELECT @x;  -- 10

-- ---------------------------------------------------
-- 13.3 变量声明与赋值
-- ---------------------------------------------------

DELIMITER //

CREATE PROCEDURE sp_variable_demo()
BEGIN
    -- DECLARE 声明局部变量（必须在 BEGIN 之后的第一批语句）
    DECLARE product_count INT DEFAULT 0;
    DECLARE avg_price DECIMAL(10,2);

    -- SELECT ... INTO 赋值
    SELECT COUNT(*), AVG(price)
    INTO product_count, avg_price
    FROM products;

    -- SET 赋值
    SET product_count = product_count + 100;

    SELECT product_count AS 调整后商品数, avg_price AS 均价;
END //

DELIMITER ;

CALL sp_variable_demo();

-- ---------------------------------------------------
-- 13.4 流程控制
-- ---------------------------------------------------

-- IF ... THEN ... ELSEIF ... ELSE ... END IF
DELIMITER //

CREATE PROCEDURE sp_grade_price(IN price DECIMAL(10,2))
BEGIN
    IF price >= 5000 THEN
        SELECT '奢侈品' AS 等级;
    ELSEIF price >= 1000 THEN
        SELECT '高档品' AS 等级;
    ELSEIF price >= 100 THEN
        SELECT '中档品' AS 等级;
    ELSE
        SELECT '平价品' AS 等级;
    END IF;
END //

DELIMITER ;

CALL sp_grade_price(6999);
CALL sp_grade_price(299);

-- CASE WHEN
DELIMITER //

CREATE PROCEDURE sp_weekday(IN day_num INT)
BEGIN
    CASE day_num
        WHEN 1 THEN SELECT '星期一' AS 结果;
        WHEN 2 THEN SELECT '星期二' AS 结果;
        WHEN 3 THEN SELECT '星期三' AS 结果;
        WHEN 4 THEN SELECT '星期四' AS 结果;
        WHEN 5 THEN SELECT '星期五' AS 结果;
        WHEN 6 THEN SELECT '星期六' AS 结果;
        WHEN 7 THEN SELECT '星期日' AS 结果;
        ELSE SELECT '无效' AS 结果;
    END CASE;
END //

DELIMITER ;

CALL sp_weekday(3);

-- 循环：WHILE
DELIMITER //

CREATE PROCEDURE sp_while_demo(IN n INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE result TEXT DEFAULT '';

    WHILE i <= n DO
        SET result = CONCAT(result, i, ' ');
        SET i = i + 1;
    END WHILE;

    SELECT result AS 序列;
END //

DELIMITER ;

CALL sp_while_demo(5);

-- 循环：REPEAT ... UNTIL（至少执行一次）
DELIMITER //

CREATE PROCEDURE sp_repeat_demo(IN n INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE result TEXT DEFAULT '';

    REPEAT
        SET result = CONCAT(result, i, ' ');
        SET i = i + 1;
    UNTIL i > n
    END REPEAT;

    SELECT result AS 序列;
END //

DELIMITER ;

CALL sp_repeat_demo(5);

-- 循环：LOOP ... LEAVE（无限循环 + 条件跳出）
DELIMITER //

CREATE PROCEDURE sp_loop_demo(IN n INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE result TEXT DEFAULT '';

    my_loop: LOOP
        IF i > n THEN
            LEAVE my_loop;  -- 跳出循环
        END IF;
        SET result = CONCAT(result, i, ' ');
        SET i = i + 1;
    END LOOP my_loop;

    SELECT result AS 序列;
END //

DELIMITER ;

CALL sp_loop_demo(5);

-- ---------------------------------------------------
-- 13.5 游标（CURSOR）— 逐行处理结果集
-- ---------------------------------------------------

DELIMITER //

CREATE PROCEDURE sp_cursor_demo()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_name VARCHAR(100);
    DECLARE v_price DECIMAL(10,2);

    -- 声明游标
    DECLARE product_cursor CURSOR FOR
        SELECT name, price FROM products WHERE price > 5000;

    -- 游标结束时触发
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN product_cursor;

    read_loop: LOOP
        FETCH product_cursor INTO v_name, v_price;
        IF done THEN
            LEAVE read_loop;
        END IF;
        -- 逐行处理
        SELECT CONCAT(v_name, ' | ¥', v_price) AS 商品信息;
    END LOOP;

    CLOSE product_cursor;
END //

DELIMITER ;

CALL sp_cursor_demo();

-- ---------------------------------------------------
-- 13.6 异常处理
-- ---------------------------------------------------

DELIMITER //

CREATE PROCEDURE sp_error_demo()
BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT '⚠️ 发生 SQL 异常，已捕获' AS 错误信息;
    END;

    -- 以下语句会触发异常（表不存在）
    SELECT * FROM non_existent_table;
    SELECT '异常之后继续执行' AS 后续;
END //

DELIMITER ;

-- CALL sp_error_demo();  -- 取消注释以测试

-- ---------------------------------------------------
-- 13.7 实用案例：分页查询存储过程
-- ---------------------------------------------------

DELIMITER //

CREATE PROCEDURE sp_page_products(
    IN page_num   INT,   -- 页码（从1开始）
    IN page_size  INT    -- 每页条数
)
BEGIN
    DECLARE offset_val INT;
    SET offset_val = (page_num - 1) * page_size;

    SELECT SQL_CALC_FOUND_ROWS id, name, price, stock
    FROM products
    ORDER BY id
    LIMIT offset_val, page_size;

    -- 返回总行数（配合 SQL_CALC_FOUND_ROWS）
    SELECT FOUND_ROWS() AS total_rows;
END //

DELIMITER ;

CALL sp_page_products(1, 5);
CALL sp_page_products(2, 5);

-- ---------------------------------------------------
-- 13.8 查看与删除存储过程
-- ---------------------------------------------------

-- 查看所有存储过程
SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES
WHERE ROUTINE_SCHEMA = 'mysql_tutorial' AND ROUTINE_TYPE = 'PROCEDURE';

-- 查看存储过程定义
-- SHOW CREATE PROCEDURE sp_get_products_by_price;

-- 删除存储过程
-- DROP PROCEDURE IF EXISTS sp_hello;

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：创建存储过程 sp_get_customers_by_city(IN city_name VARCHAR(30))，根据城市查客户
-- 你的代码：


-- 题2：创建存储过程 sp_product_stats(IN cat_id INT)，返回该分类的商品数和均价（OUT 参数）
-- 你的代码：


-- 题3：创建存储过程 sp_customer_level(IN cust_id INT)，根据客户的VIP等级输出文字描述
-- 提示：用 IF ... THEN ... ELSEIF
-- 你的代码：


-- 题4：创建一个带游标的存储过程 sp_stock_alert(IN threshold INT)，遍历输出库存低于阈值的商品
-- 你的代码：


-- 题5：创建一个批量更新的存储过程 sp_bulk_price_increase(IN cat_id INT, IN percent DECIMAL(5,2))
-- 将该分类的商品价格上调指定百分比，用事务包裹，有错回滚
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: 存储过程的优缺点？
-- A: 优点：① 减少网络开销（多条SQL打包成一次调用）
--        ② 预编译，执行效率高 ③ 集中业务逻辑，便于维护
--    缺点：① 难以调试 ② 版本控制不友好
--        ③ 与数据库耦合 ④ 可移植性差（不同数据库语法不同）
--
-- Q: 存储过程和函数的区别？
-- A: 见第14章对比表。关键区别：
--    ① 函数必须有返回值，存储过程通过 OUT 参数
--    ② 函数用 SELECT 调用，存储过程用 CALL
--    ③ 函数不能开启/提交/回滚事务
--
-- Q: 游标的使用场景和注意事项？
-- A: 场景：需要逐行处理数据（存储过程中循环处理查询结果）
--    注意：① 游标占用资源，用完后关闭 ② 声明顺序：变量 → 游标 → Handler
--    ③ 大数据量慎用游标（逐行处理远慢于批量操作）
--
-- Q: 什么场景不适合用存储过程？
-- A: ① 简单查询（增加复杂性） ② 高并发 OLTP（存储过程占用数据库CPU）
--    ③ 微服务架构（应该每个服务管理自己的逻辑）
--    ④ 需要快速迭代的场景（修改部署不方便）

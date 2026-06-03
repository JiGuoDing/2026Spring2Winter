-- =====================================================
-- 13_存储过程 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：按城市查客户
DELIMITER //
CREATE PROCEDURE sp_get_customers_by_city(IN city_name VARCHAR(30))
BEGIN
    SELECT id, name, phone, vip_level FROM customers WHERE city = city_name;
END //
DELIMITER ;
CALL sp_get_customers_by_city('北京');

-- 题2：商品分类统计（OUT参数）
DELIMITER //
CREATE PROCEDURE sp_product_stats(IN cat_id INT, OUT cnt INT, OUT avg_p DECIMAL(10,2))
BEGIN
    SELECT COUNT(*), AVG(price) INTO cnt, avg_p
    FROM products WHERE category_id = cat_id;
END //
DELIMITER ;
CALL sp_product_stats(11, @c, @a);
SELECT @c AS 商品数, @a AS 均价;

-- 题3：VIP等级描述
DELIMITER //
CREATE PROCEDURE sp_customer_level(IN cust_id INT)
BEGIN
    DECLARE v_level INT;
    SELECT vip_level INTO v_level FROM customers WHERE id = cust_id;
    IF v_level >= 4 THEN SELECT '高价值客户' AS 等级;
    ELSEIF v_level >= 2 THEN SELECT '中等客户' AS 等级;
    ELSE SELECT '普通客户' AS 等级;
    END IF;
END //
DELIMITER ;
CALL sp_customer_level(1);

-- 题4：库存预警游标
DELIMITER //
CREATE PROCEDURE sp_stock_alert(IN threshold INT)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_name VARCHAR(100);
    DECLARE v_stock INT;
    DECLARE cur CURSOR FOR SELECT name, IFNULL(stock, 0) FROM products WHERE IFNULL(stock, 0) < threshold;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_name, v_stock;
        IF done THEN LEAVE read_loop; END IF;
        SELECT CONCAT('⚠️ ', v_name, ' 库存仅剩 ', v_stock) AS 预警;
    END LOOP;
    CLOSE cur;
END //
DELIMITER ;
-- CALL sp_stock_alert(50);

-- 题5：批量涨价（事务包裹）
DELIMITER //
CREATE PROCEDURE sp_bulk_price_increase(IN cat_id INT, IN percent DECIMAL(5,2))
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT '⚠️ 涨价失败，已回滚' AS result;
    END;
    START TRANSACTION;
    UPDATE products SET price = price * (1 + percent / 100) WHERE category_id = cat_id;
    COMMIT;
    SELECT CONCAT('✅ 分类 ', cat_id, ' 商品已涨价 ', percent, '%') AS result;
END //
DELIMITER ;
-- CALL sp_bulk_price_increase(11, 10);

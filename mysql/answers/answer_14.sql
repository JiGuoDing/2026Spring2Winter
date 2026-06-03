-- =====================================================
-- 14_自定义函数 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：折后价函数
DELIMITER //
CREATE FUNCTION fn_discount_price(price DECIMAL(10,2), discount_pct DECIMAL(5,2))
RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
    RETURN price * (1 - discount_pct / 100);
END //
DELIMITER ;
SELECT fn_discount_price(100, 20) AS 折后价;  -- 80.00

-- 题2：商品等级函数
DELIMITER //
CREATE FUNCTION fn_product_level(price DECIMAL(10,2))
RETURNS VARCHAR(10)
DETERMINISTIC
BEGIN
    IF price >= 5000 THEN RETURN '奢侈';
    ELSEIF price >= 1000 THEN RETURN '高端';
    ELSEIF price >= 100 THEN RETURN '中端';
    ELSE RETURN '平价';
    END IF;
END //
DELIMITER ;

-- 题3：年龄函数
DELIMITER //
CREATE FUNCTION fn_age(birth_date DATE)
RETURNS INT
DETERMINISTIC
BEGIN
    RETURN TIMESTAMPDIFF(YEAR, birth_date, CURDATE());
END //
DELIMITER ;
SELECT fn_age('1990-06-15') AS 年龄;

-- 题4：商品等级分布
SELECT fn_product_level(price) AS 等级, COUNT(*) AS 数量
FROM products GROUP BY 等级 ORDER BY 数量 DESC;

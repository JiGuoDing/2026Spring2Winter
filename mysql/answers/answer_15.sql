-- =====================================================
-- 15_触发器与事件 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：BEFORE INSERT 验证总金额
DELIMITER //
CREATE TRIGGER trg_orders_before_insert
BEFORE INSERT ON orders
FOR EACH ROW
BEGIN
    IF NEW.total_amount < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '订单总金额不能为负数';
    END IF;
END //
DELIMITER ;

-- 题2：AFTER DELETE 审计日志
DELIMITER //
CREATE TRIGGER trg_products_after_delete
AFTER DELETE ON products
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, old_data)
    VALUES ('products', 'DELETE', OLD.id,
            JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'price', OLD.price, 'stock', OLD.stock));
END //
DELIMITER ;

-- 题3：查看所有触发器
SHOW TRIGGERS;

-- 题4：BEFORE vs AFTER
-- BEFORE 触发器：适合数据验证（在写入前检查并阻止）
-- AFTER 触发器：适合审计日志（数据已经写入，记录变更历史）
--              适合同步其他表（源数据已确定无误，再触发级联操作）

-- =====================================================
-- 文件名：15_触发器与事件.sql
-- 难度：★★★☆☆
-- 前置知识：01_基础查询_CRUD, 13_存储过程
-- 学习时间：约 35 分钟
-- 对应面试考点：触发器的使用场景、NEW/OLD、审计日志、定时任务
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- ---------------------------------------------------
-- 15.1 触发器基本语法
-- ---------------------------------------------------
-- 触发器 = 在对表执行 INSERT/UPDATE/DELETE 时自动触发的程序
-- 时机：BEFORE（操作前） / AFTER（操作后）

-- 基本结构：
-- CREATE TRIGGER trigger_name
-- {BEFORE | AFTER} {INSERT | UPDATE | DELETE}
-- ON table_name FOR EACH ROW
-- BEGIN
--     -- 触发器逻辑
-- END;

-- ---------------------------------------------------
-- 15.2 NEW 和 OLD 伪行引用
-- ---------------------------------------------------
-- INSERT：只能引用 NEW（新插入的行数据）
-- DELETE：只能引用 OLD（被删除的行数据）
-- UPDATE：同时可使用 NEW（更新后的值）和 OLD（更新前的值）

-- ---------------------------------------------------
-- 15.3 经典案例1：自动更新 updated_at 时间戳
-- ---------------------------------------------------

DELIMITER //

CREATE TRIGGER trg_products_before_update
BEFORE UPDATE ON products
FOR EACH ROW
BEGIN
    SET NEW.updated_at = NOW();
END //

DELIMITER ;

-- 验证：更新商品价格，观察 updated_at 是否自动更新
SELECT id, name, price, updated_at FROM products WHERE id = 1;
UPDATE products SET price = 7000 WHERE id = 1;
SELECT id, name, price, updated_at FROM products WHERE id = 1;
-- 恢复
UPDATE products SET price = 6999.00 WHERE id = 1;

-- ---------------------------------------------------
-- 15.4 经典案例2：审计日志（INSERT + UPDATE + DELETE）
-- ---------------------------------------------------

-- 插入审计日志（INSERT）
DELIMITER //

CREATE TRIGGER trg_products_after_insert
AFTER INSERT ON products
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, new_data)
    VALUES ('products', 'INSERT', NEW.id,
            JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'price', NEW.price));
END //

DELIMITER ;

-- 更新审计日志（UPDATE）
DELIMITER //

CREATE TRIGGER trg_products_after_update
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, old_data, new_data)
    VALUES ('products', 'UPDATE', NEW.id,
            JSON_OBJECT('name', OLD.name, 'price', OLD.price, 'stock', OLD.stock),
            JSON_OBJECT('name', NEW.name, 'price', NEW.price, 'stock', NEW.stock));
END //

DELIMITER ;

-- 测试：插入 + 更新
INSERT INTO products (name, category_id, price, stock) VALUES ('测试触发器商品', 11, 99.00, 50);
UPDATE products SET price = 89.00 WHERE name = '测试触发器商品';

-- 查看审计日志
SELECT id, table_name, operation, record_id,
       JSON_PRETTY(old_data) AS 旧数据,
       JSON_PRETTY(new_data) AS 新数据,
       changed_at
FROM audit_log
ORDER BY id DESC
LIMIT 5;

-- 清理测试数据
DELETE FROM products WHERE name = '测试触发器商品';

-- ---------------------------------------------------
-- 15.5 BEFORE 触发器的妙用：数据验证
-- ---------------------------------------------------

-- 插入前检查：价格必须 > 0
DELIMITER //

CREATE TRIGGER trg_products_before_insert
BEFORE INSERT ON products
FOR EACH ROW
BEGIN
    IF NEW.price <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '商品价格必须大于0！';
    END IF;
END //

DELIMITER ;

-- 测试：尝试插入价格为负的商品 → 报错
-- INSERT INTO products (name, price) VALUES ('测试负价格', -10.00);

-- ---------------------------------------------------
-- 15.6 查看/删除触发器
-- ---------------------------------------------------

-- 查看所有触发器
SHOW TRIGGERS;

SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE
FROM INFORMATION_SCHEMA.TRIGGERS
WHERE TRIGGER_SCHEMA = 'mysql_tutorial';

-- 删除触发器
-- DROP TRIGGER IF EXISTS trg_products_before_update;

-- ---------------------------------------------------
-- 15.7 事件调度器（EVENT）— 定时任务
-- ---------------------------------------------------

-- 检查事件调度器状态（需要 SUPER 权限）
SHOW VARIABLES LIKE 'event_scheduler';
-- OFF：调度器未开启
-- SET GLOBAL event_scheduler = ON;  -- 开启（需SUPER权限）

-- 创建定时事件：每天凌晨清理 30 天前的审计日志
DELIMITER //

CREATE EVENT IF NOT EXISTS evt_clean_audit_log
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP + INTERVAL 1 HOUR
DO
BEGIN
    DELETE FROM audit_log
    WHERE changed_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
END //

DELIMITER ;

-- 查看事件
SHOW EVENTS;

-- 删除事件
-- DROP EVENT IF EXISTS evt_clean_audit_log;

-- ---------------------------------------------------
-- 15.8 触发器的注意事项
-- ---------------------------------------------------
-- 1. 性能影响：每次 INSERT/UPDATE/DELETE 都执行触发器逻辑
--    大量写入场景下开销显著
-- 2. 级联触发：A表触发器操作B表 → B表触发器又操作C表 ...
--    排查问题时非常困难
-- 3. 调试困难：触发器在数据库内部静默执行，难以追踪
-- 4. 架构建议：不要在触发器中放复杂业务逻辑
--    推荐只用触发器做：审计日志、自动更新时戳、简单的数据验证
--    复杂业务逻辑放在应用层

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：创建一个 BEFORE INSERT 触发器 trg_orders_check，确保订单总金额 >= 0
-- 你的代码：


-- 题2：创建 audit_log 的 AFTER DELETE 触发器 trg_products_after_delete
-- 记录被删除的商品信息到 audit_log
-- 你的代码：


-- 题3：查看当前 mysql_tutorial 库中所有的触发器
-- 你的代码：


-- 题4：概念题：BEFORE 触发器和 AFTER 触发器各适合什么场景？
-- 你的回答：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: 触发器的使用场景？
-- A: ① 审计日志（自动记录数据变更历史）
--    ② 自动更新衍生字段（如 updated_at、订单总额）
--    ③ 数据验证（BEFORE 触发器中检查并阻止非法数据）
--    ④ 同步相关表（如插入订单时自动减库存）
--
-- Q: 为什么很多团队不建议使用触发器？
-- A: ① 难以调试和追踪（静默执行）
--    ② 性能开销（尤其大表批量操作时）
--    ③ 级联触发带来不可预见的副作用
--    ④ 数据库耦合 → 逻辑分散在应用层和数据库层
--    ⑤ 大多数场景可以用应用层代码替代
--
-- Q: NEW 和 OLD 的访问规则？
-- A: INSERT 只能用 NEW；DELETE 只能用 OLD
--    UPDATE 两者都能用（NEW=更新后的值，OLD=更新前的值）

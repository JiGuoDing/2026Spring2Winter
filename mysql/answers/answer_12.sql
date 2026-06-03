-- =====================================================
-- 12_视图 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：商品+分类+供应商视图
CREATE OR REPLACE VIEW v_product_list AS
SELECT p.name AS 商品, c.name AS 分类, s.name AS 供应商, p.price
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN suppliers s ON p.supplier_id = s.id;

-- 题2：查询视图 price > 1000
SELECT * FROM v_product_list WHERE price > 1000 ORDER BY price DESC;

-- 题3：北京客户视图 WITH CHECK OPTION
CREATE OR REPLACE VIEW v_beijing_customers AS
SELECT id, name, city, vip_level
FROM customers WHERE city = '北京'
WITH CHECK OPTION;

-- 题4：违反 CHECK OPTION（预期报错）
-- INSERT INTO v_beijing_customers (name, city, vip_level) VALUES ('测试', '上海', 1);
-- Error: CHECK OPTION failed

-- 题5：修改视图增加 phone
CREATE OR REPLACE VIEW v_customer_public AS
SELECT id, name, city, phone, vip_level, register_date
FROM customers;

-- =====================================================
-- 01_基础查询_CRUD — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：查询所有客户姓名和城市
SELECT name AS 姓名, city AS 城市 FROM customers;

-- 题2：查询所有不重复的城市名
SELECT DISTINCT city FROM customers;

-- 题3：查询价格在 100 到 500 元之间的商品名称和价格
SELECT name, price FROM products WHERE price BETWEEN 100 AND 500;
-- 等价写法：SELECT name, price FROM products WHERE price >= 100 AND price <= 500;

-- 题4：查询所有没有填写邮箱的客户姓名和手机号
SELECT name, phone FROM customers WHERE email IS NULL;

-- 题5：插入新供应商
INSERT INTO suppliers (name, city, rating) VALUES ('测试供应商', '西安', 4.0);
-- 验证
SELECT * FROM suppliers WHERE name = '测试供应商';
-- 清理（可选）
DELETE FROM suppliers WHERE name = '测试供应商';

-- 题6：将商品ID为48的stock更新为0
UPDATE products SET stock = 0 WHERE id = 48 AND stock IS NULL;
-- 验证
SELECT id, name, stock FROM products WHERE id = 48;

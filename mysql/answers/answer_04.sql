-- =====================================================
-- 04_内置函数大全 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：客户姓名和联系方式（COALESCE）
SELECT name,
       COALESCE(email, phone, '无联系方式') AS 联系方式
FROM customers
LIMIT 10;

-- 题2：商品名+价格格式化
SELECT name, CONCAT('¥', ROUND(price, 2)) AS 价格
FROM products
LIMIT 10;

-- 题3：注册天数 TOP5（过滤2026年到期的？这里演示思维：注册天数最多的）
SELECT name, register_date,
       DATEDIFF(CURDATE(), register_date) AS 注册天数
FROM customers
-- 题中说"今年到期"，在当前数据中，查找注册最久的：
ORDER BY register_date ASC
LIMIT 5;
-- 注：如果你设置了特定的"到期日"场景，调整为：
-- WHERE YEAR(some_date) = 2026 过滤即可

-- 题4：VIP 等级文字
SELECT name, vip_level,
       CASE vip_level
           WHEN 0 THEN '普通'
           WHEN 1 THEN '银卡'
           WHEN 2 THEN '金卡'
           WHEN 3 THEN '铂金'
           WHEN 4 THEN '钻石'
           WHEN 5 THEN '至尊'
           ELSE '未知'
       END AS 等级
FROM customers
LIMIT 10;

-- 题5：2024年每月的订单总金额
SELECT DATE_FORMAT(order_date, '%Y-%m') AS 月份,
       SUM(total_amount) AS 总金额
FROM orders
WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01'
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY 月份;

-- 题6：商品前3字符简称
SELECT name, LEFT(name, 3) AS 简称 FROM products LIMIT 10;
-- 或 SELECT name, SUBSTRING(name, 1, 3) AS 简称 ...

-- 题7：商品名包含"版"
SELECT name FROM products WHERE INSTR(name, '版') > 0;
-- 或 SELECT name FROM products WHERE name LIKE '%版%';

-- 题8：供应商名称和电话（IFNULL）
SELECT name, IFNULL(phone, '暂无') AS 电话 FROM suppliers;

-- 题9：每个城市客户数占比
SELECT city,
       COUNT(*) AS 客户数,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM customers), 2) AS 占比
FROM customers
GROUP BY city
ORDER BY 客户数 DESC;

-- 题10：商品分档统计
SELECT
    CASE
        WHEN price > 1000 THEN '高档'
        WHEN price >= 100 THEN '中档'
        ELSE '低档'
    END AS 价格档,
    COUNT(*) AS 数量
FROM products
GROUP BY 价格档
ORDER BY 数量 DESC;

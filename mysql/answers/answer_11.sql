-- =====================================================
-- 11_索引与性能优化 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：查看 orders 表索引
SHOW INDEX FROM orders;

-- 题2：EXPLAIN 分析 customer_id 查询
EXPLAIN SELECT * FROM orders WHERE customer_id = 5;
-- 预期：type=ref, key=idx_customer，使用 customer_id 索引

-- 题3：EXPLAIN price > 100
EXPLAIN SELECT * FROM products WHERE price > 100;
-- 预期：type=range, key=idx_price（如果有 idx_price 索引）

-- 题4：覆盖索引优化
-- CREATE INDEX idx_cust_status_date ON orders(customer_id, status, order_date);
-- EXPLAIN SELECT customer_id, order_date FROM orders WHERE customer_id = 10 AND status = 'delivered';

-- 题5：YEAR() 函数索引失效
-- EXPLAIN SELECT * FROM orders WHERE YEAR(order_date) = 2024;  -- type=ALL
-- 优化：SELECT * FROM orders WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01';

-- 题6：LIKE '%keyword' 索引失效
-- 无法通过索引优化（因为 % 开头）
-- 替代方案：全文索引（FULLTEXT）、搜索引擎（Elasticsearch）

-- 题7：type=ALL 的判断
-- type=ALL 说明全表扫描，通常需要优化
-- 检查：是否缺少索引、索引是否失效、数据量是否很小

-- 题8：gender 列索引建议
-- 不建议单独建索引：选择性太低（只有3个值），优化器可能放弃使用
-- 如果和其他列一起建复合索引可以考虑（如 gender + register_date）

-- 题9：Using filesort 的含义
-- 表示 MySQL 需要额外排序（ORDER BY 没有利用索引顺序）
-- 优化：在 ORDER BY 列上建索引，或利用复合索引覆盖排序

-- 题10：customer_id=5 最早订单
EXPLAIN SELECT * FROM orders WHERE customer_id = 5 ORDER BY order_date LIMIT 5;
-- 预期使用 idx_customer_date (customer_id, order_date) 复合索引
SELECT * FROM orders WHERE customer_id = 5 ORDER BY order_date LIMIT 5;

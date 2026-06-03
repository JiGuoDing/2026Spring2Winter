-- =====================================================
-- 08_窗口函数 — 参考答案
-- =====================================================
USE mysql_tutorial;

-- 题1：ROW_NUMBER 按价格降序
SELECT ROW_NUMBER() OVER (ORDER BY price DESC) AS 排名, name, price FROM products;

-- 题2：每个分类价格TOP3
SELECT * FROM (
    SELECT category_id, name, price,
           ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY price DESC) AS rn
    FROM products WHERE category_id IS NOT NULL
) t WHERE rn <= 3 ORDER BY category_id, rn;

-- 题3：环比增长率
SELECT customer_id, order_date, total_amount,
       LAG(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date) AS prev,
       ROUND((total_amount - LAG(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date))
             / NULLIF(LAG(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date), 0) * 100, 2) AS 环比增长
FROM orders ORDER BY customer_id, order_date LIMIT 20;

-- 题4：累计销售额
SELECT DATE(order_date) AS dt, SUM(total_amount) AS 日销售额,
       SUM(SUM(total_amount)) OVER (ORDER BY DATE(order_date)) AS 累计
FROM orders WHERE status = 'delivered'
GROUP BY DATE(order_date) ORDER BY dt;

-- 题5：近5笔移动平均
SELECT order_date, total_amount,
       ROUND(AVG(total_amount) OVER (ORDER BY order_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW), 2) AS ma5
FROM orders WHERE status = 'delivered' ORDER BY order_date LIMIT 15;

-- 题6：NTILE 分桶
SELECT bucket, COUNT(*) AS cnt FROM (
    SELECT NTILE(5) OVER (ORDER BY price) AS bucket FROM products
) t GROUP BY bucket ORDER BY bucket;

-- 题7：每个客户首单和末单
SELECT DISTINCT customer_id,
       FIRST_VALUE(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS 首单,
       FIRST_VALUE(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date) AS 首单金额,
       FIRST_VALUE(order_date) OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS 末单,
       FIRST_VALUE(total_amount) OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS 末单金额
FROM orders ORDER BY customer_id LIMIT 10;

-- 题8：每个客户最高金额订单
SELECT * FROM (
    SELECT customer_id, id, total_amount,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total_amount DESC) AS rn
    FROM orders
) t WHERE rn = 1;

-- 题9：每分类内RANK前5
SELECT * FROM (
    SELECT category_id, name, price,
           RANK() OVER (PARTITION BY category_id ORDER BY price DESC) AS rk
    FROM products WHERE category_id IS NOT NULL
) t WHERE rk <= 5 ORDER BY category_id, rk;

-- 题10：日销售额7日移动平均
WITH daily AS (
    SELECT DATE(order_date) AS dt, SUM(total_amount) AS dailytotal
    FROM orders GROUP BY DATE(order_date)
)
SELECT dt, dailytotal,
       ROUND(AVG(dailytotal) OVER (ORDER BY dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS ma7
FROM daily ORDER BY dt;

-- 题11：相邻订单间隔 > 30天
SELECT * FROM (
    SELECT customer_id, order_date,
           DATEDIFF(order_date, LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)) AS gap
    FROM orders
) t WHERE gap > 30;

-- 题12：百分位排名
SELECT c.name, SUM(o.total_amount) AS total,
       ROUND(CUME_DIST() OVER (ORDER BY SUM(o.total_amount)) * 100, 2) AS 百分位
FROM customers c JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name ORDER BY total DESC LIMIT 10;

-- =====================================================
-- 文件名：04_内置函数大全.sql
-- 难度：★★☆☆☆
-- 前置知识：01_基础查询_CRUD, 02_高级过滤与排序, 03_聚合函数与分组
-- 学习时间：约 50 分钟
-- 对应面试考点：字符串处理、日期计算、CASE WHEN 条件判断
-- =====================================================

USE mysql_tutorial;

-- =====================================================
-- 第一部分：知识点讲解
-- =====================================================

-- #################################################
-- 4.1 字符串函数
-- #################################################

-- CONCAT：拼接字符串
SELECT CONCAT('MySQL', ' ', '教程') AS result;
SELECT CONCAT(name, ' - ¥', price) AS 商品信息 FROM products LIMIT 5;

-- CONCAT_WS：带分隔符拼接（第一个参数是分隔符）
SELECT CONCAT_WS(' | ', name, price, stock) AS 商品汇总 FROM products LIMIT 5;
-- ⚠️ CONCAT_WS 自动跳过 NULL，CONCAT 遇到 NULL 整个结果变 NULL

-- SUBSTRING / SUBSTR：截取子串 (位置从1开始)
SELECT SUBSTRING('Hello MySQL', 1, 5)  AS result;  -- Hello
SELECT SUBSTRING('Hello MySQL', 7)     AS result;  -- MySQL
SELECT SUBSTRING(name, 1, 5) AS 简称 FROM products WHERE price > 5000;

-- LEFT / RIGHT：取左边/右边 N 个字符
SELECT LEFT('Hello',  2) AS result;  -- He
SELECT RIGHT('Hello', 3) AS result;  -- llo

-- LENGTH (字节长度) vs CHAR_LENGTH (字符长度)
SELECT CHAR_LENGTH('Hello') AS 字符数;       -- 5
SELECT CHAR_LENGTH('你好')  AS 字符数;       -- 2
SELECT LENGTH('Hello')      AS 字节数;       -- 5 (英文1字节/字符)
SELECT LENGTH('你好')       AS 字节数;       -- 6 (utf8mb4下中文3字节/字符)

-- REPLACE：替换
SELECT REPLACE('Hello World', 'World', 'MySQL') AS result;
SELECT REPLACE(name, 'Pro', '专业版') AS 改名 FROM products WHERE name LIKE '%Pro%';

-- TRIM / LTRIM / RTRIM：去空格
SELECT TRIM('  hello  ')  AS result;  -- 'hello'
SELECT LTRIM('  hello  ') AS result;  -- 'hello  '
SELECT RTRIM('  hello  ') AS result;  -- '  hello'

-- UPPER / LOWER：大小写转换
SELECT UPPER('mysql'), LOWER('MYSQL');

-- LPAD / RPAD：左右填充到指定长度
SELECT LPAD('5', 3, '0') AS 格式化;  -- '005'
SELECT RPAD('Hello', 10, '-') AS result;  -- 'Hello-----'

-- INSTR / LOCATE：查找子串位置（返回位置，找不到返回0）
SELECT INSTR('Hello MySQL', 'MySQL') AS 位置;     -- 7
SELECT LOCATE('SQL', 'MySQL Tutorial') AS 位置;   -- 3

-- #################################################
-- 4.2 日期时间函数
-- #################################################

-- 获取当前时间
SELECT NOW()        AS 当前日期时间;
SELECT CURDATE()    AS 当前日期;
SELECT CURTIME()    AS 当前时间;

-- DATE_FORMAT：格式化日期（面试常考）
SELECT DATE_FORMAT(NOW(), '%Y-%m-%d')       AS 标准日期;
SELECT DATE_FORMAT(NOW(), '%Y年%m月%d日')    AS 中文日期;
SELECT DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s') AS 完整时间;
-- 常用格式符：%Y=4位年 %m=月 %d=日 %H=时(24) %i=分 %s=秒 %W=星期名

-- STR_TO_DATE：字符串转日期
SELECT STR_TO_DATE('2024-06-01', '%Y-%m-%d') AS 日期;

-- DATEDIFF：日期差（天数）
SELECT DATEDIFF('2024-12-31', '2024-01-01') AS 相差天数;  -- 365

-- TIMESTAMPDIFF：更灵活的时间差
SELECT TIMESTAMPDIFF(YEAR,   '2000-01-01', NOW())  AS 年差;
SELECT TIMESTAMPDIFF(MONTH,  '2024-01-01', NOW())  AS 月差;
SELECT TIMESTAMPDIFF(DAY,    '2024-01-01', NOW())  AS 日差;

-- DATE_ADD / DATE_SUB：日期加减
SELECT DATE_ADD('2024-12-01', INTERVAL 7 DAY)   AS 一周后;
SELECT DATE_SUB('2024-12-01', INTERVAL 1 MONTH) AS 一个月前;
SELECT DATE_ADD(NOW(), INTERVAL 1 YEAR)           AS 一年后;

-- 提取日期分量
SELECT
    YEAR('2024-06-15')  AS 年,
    MONTH('2024-06-15') AS 月,
    DAY('2024-06-15')   AS 日,
    DAYOFWEEK('2024-06-15') AS 星期几;  -- 1=周日

-- LAST_DAY：当月最后一天
SELECT LAST_DAY('2024-02-15') AS 二月末;  -- 2024-02-29 (闰年)

-- 实际案例：查询注册超过 365 天的老客户
SELECT name, register_date,
       DATEDIFF(CURDATE(), register_date) AS 注册天数
FROM customers
WHERE DATEDIFF(CURDATE(), register_date) > 365
LIMIT 5;

-- 实际案例：按月统计下单量
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS 月份,
    COUNT(*) AS 订单数
FROM orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY 月份;

-- #################################################
-- 4.3 数学函数
-- #################################################

SELECT ROUND(3.14159, 2)    AS 四舍五入;  -- 3.14
SELECT CEIL(3.14)           AS 向上取整;  -- 4
SELECT FLOOR(3.14)          AS 向下取整;  -- 3
SELECT ABS(-100)            AS 绝对值;    -- 100
SELECT MOD(17, 5)           AS 取余;      -- 2（等价于 17 % 5）
SELECT RAND()               AS 随机数;    -- 0~1 随机浮点数

-- 实际案例：生成 1~100 随机整数
SELECT FLOOR(1 + RAND() * 100) AS 随机整数;

-- #################################################
-- 4.4 条件函数 ⭐ 面试高频
-- #################################################

-- IF(expr, true_val, false_val)：三目运算符
SELECT
    name,
    price,
    IF(price > 1000, '高端', IF(price > 100, '中端', '低端')) AS 价格档位
FROM products
LIMIT 10;

-- IFNULL(expr, default)：如果 expr 为 NULL 则返回 default
SELECT
    id, name,
    IFNULL(stock, 0) AS 实际库存
FROM products
WHERE stock IS NULL OR id = 48;

-- COALESCE(val1, val2, ...)：返回第一个非 NULL 的值（比 IFNULL 更通用）
SELECT
    name,
    COALESCE(email, '未填写邮箱') AS 联系方式,
    COALESCE(phone, '未填写手机') AS 手机号
FROM customers
WHERE email IS NULL OR phone IS NULL
LIMIT 5;

-- NULLIF(a, b)：如果 a = b 返回 NULL，否则返回 a
SELECT NULLIF(100, 100) AS result;  -- NULL
SELECT NULLIF(100, 200) AS result;  -- 100
-- 用途：避免除零错误
-- SELECT amount / NULLIF(count, 0) FROM ...

-- CASE WHEN（SQL 版 switch／if-elif-else）
-- 两种写法：

-- 写法1：CASE 列 WHEN 值（简单 CASE）
SELECT
    name,
    status,
    CASE status
        WHEN 'delivered' THEN '✅ 已签收'
        WHEN 'shipped'   THEN '🚚 运输中'
        WHEN 'paid'      THEN '💰 已付款'
        WHEN 'pending'   THEN '⏳ 待处理'
        WHEN 'cancelled' THEN '❌ 已取消'
        ELSE '未知'
    END AS 状态描述
FROM orders
LIMIT 10;

-- 写法2：CASE WHEN 条件（搜索 CASE，更灵活）
SELECT
    name,
    price,
    CASE
        WHEN price >= 5000 THEN '奢侈品'
        WHEN price >= 1000 THEN '高档品'
        WHEN price >= 100  THEN '中档品'
        WHEN price >= 10   THEN '平价品'
        ELSE '廉价品'
    END AS 等级
FROM products
ORDER BY price DESC
LIMIT 10;

-- CASE WHEN + 聚合 → 行转列（面试高频！）
-- 按月统计各状态的订单数
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS 月份,
    COUNT(CASE WHEN status = 'delivered' THEN 1 END) AS 已签收,
    COUNT(CASE WHEN status = 'shipped'   THEN 1 END) AS 运输中,
    COUNT(CASE WHEN status = 'paid'      THEN 1 END) AS 已付款,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS 已取消
FROM orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY 月份;

-- #################################################
-- 4.5 类型转换
-- #################################################

SELECT CAST('123' AS SIGNED)       AS 转整数;
SELECT CAST('2024-01-01' AS DATE)  AS 转日期;
SELECT CAST(123 AS CHAR)           AS 转字符串;
-- CONVERT 功能类似
SELECT CONVERT('2024-01-01', DATE) AS 转日期;

-- =====================================================
-- 第二部分：练习题
-- =====================================================

-- 题1：查询客户姓名和联系方式，如果 email 为 NULL 则显示 phone，都 NULL 显示"无联系方式"（用 COALESCE）
-- 你的代码：


-- 题2：查询商品名称和价格，价格前加"¥"符号，保留两位小数（CONCAT + ROUND）
-- 你的代码：


-- 题3：查询今年到期（2026年）的客户注册天数（距现在），按天数降序 TOP 5
-- 你的代码：


-- 题4：用 CASE WHEN 将 VIP 等级转成文字：0=普通, 1=银卡, 2=金卡, 3=铂金, 4=钻石, 5=至尊
-- 你的代码：


-- 题5：查询 2024 年每个月的订单总金额（用 DATE_FORMAT 取月份）
-- 你的代码：


-- 题6：查询商品名称，截取前 3 个字符作为"简称"（LEFT 或 SUBSTRING）
-- 你的代码：


-- 题7：查询商品名称中包含"版"字的商品（用 INSTR 或 LOCATE 判断）
-- 你的代码：


-- 题8：查询供应商名称和电话，如果电话是 NULL 显示"暂无"（用 IFNULL）
-- 你的代码：


-- 题9：统计每个城市客户数，并显示每个城市客户数在全国的占比（百分比）
-- 提示：用 COUNT(*) / (SELECT COUNT(*) FROM customers)
-- 你的代码：


-- 题10：将商品按价格分为 3 档（高>1000，中100~1000，低<100），统计每档商品数量
-- 你的代码：


-- =====================================================
-- 第三部分：面试技巧
-- =====================================================
-- 常见面试问题：
--
-- Q: IFNULL 和 COALESCE 的区别？
-- A: IFNULL(expr, default) 只有两个参数，如果 expr 为 NULL 返回 default
--    COALESCE(val1, val2, ...) 接受多个参数，返回第一个非 NULL 的值
--    COALESCE 更通用，且是 SQL 标准，跨数据库兼容性好
--
-- Q: CASE WHEN 的两种写法？
-- A: ① CASE 列 WHEN 值 THEN ... END（等值比较）
--    ② CASE WHEN 条件 THEN ... END（条件比较，更灵活）
--    配合 GROUP BY 可以实现行转列
--
-- Q: CHAR_LENGTH 和 LENGTH 的区别？
-- A: CHAR_LENGTH 返回字符数，LENGTH 返回字节数
--    在 utf8mb4 下，一个中文字符 = 3 字节，一个 emoji = 4 字节
--    如需按字符截取中文，用 SUBSTRING 配合 CHAR_LENGTH

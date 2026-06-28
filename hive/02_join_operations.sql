-- ============================================================
-- Hive SQL 面试题：JOIN 操作
-- ============================================================

-- 建表：用户表
DROP TABLE IF EXISTS t_user;
CREATE TABLE t_user (
    user_id   STRING COMMENT '用户ID',
    user_name STRING COMMENT '用户名',
    city      STRING COMMENT '城市'
) COMMENT '用户表';

INSERT INTO t_user VALUES
    ('U001', '张三', '北京'),
    ('U002', '李四', '上海'),
    ('U003', '王五', '广州'),
    ('U004', '赵六', '深圳'),
    ('U005', '孙七', '杭州'),
    ('U006', '周八', '成都');

-- 建表：订单表
DROP TABLE IF EXISTS t_order;
CREATE TABLE t_order (
    order_id   STRING        COMMENT '订单ID',
    user_id    STRING        COMMENT '用户ID',
    product    STRING        COMMENT '商品',
    amount     DECIMAL(10,2) COMMENT '金额',
    order_date STRING        COMMENT '下单日期'
) COMMENT '订单表';

INSERT INTO t_order VALUES
    ('O001', 'U001', '手机',   5999.00, '2024-01-15'),
    ('O002', 'U001', '耳机',    299.00, '2024-02-20'),
    ('O003', 'U002', '电脑',   8999.00, '2024-01-20'),
    ('O004', 'U003', '鼠标',     89.00, '2024-03-10'),
    ('O005', 'U003', '键盘',    399.00, '2024-03-12'),
    ('O006', 'U007', '显示器', 1299.00, '2024-04-01'),
    ('O007', 'U001', '平板',   3499.00, '2024-05-10');

-- 建表：退款表
DROP TABLE IF EXISTS t_refund;
CREATE TABLE t_refund (
    refund_id   STRING        COMMENT '退款ID',
    order_id    STRING        COMMENT '订单ID',
    refund_amt  DECIMAL(10,2) COMMENT '退款金额',
    refund_date STRING        COMMENT '退款日期'
) COMMENT '退款表';

INSERT INTO t_refund VALUES
    ('R001', 'O001', 5999.00, '2024-01-18'),
    ('R002', 'O005',  399.00, '2024-03-15');

-- ============================================================
-- 题目 1：查询所有用户及其订单（LEFT JOIN）
-- 要求：列出所有用户，如果用户有订单则显示订单信息，
--       没有订单的用户也显示（订单列为NULL）
-- 期望列：用户ID、用户名、订单ID、商品、金额
-- ============================================================
SELECT
    u.user_id,
    u.user_name,
    o.order_id,
    o.product,
    o.amount
FROM t_user AS u
LEFT JOIN t_order AS o
    ON u.user_id = o.user_id;

-- [评价] ✅ 正确。
-- 1. 以 t_user 为左表（驱动表），LEFT JOIN 保证所有用户都出现在结果中。
-- 2. 没有订单的用户（U004、U005、U006）对应的订单列会显示为 NULL，符合题目要求。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 2：查询有订单的用户信息（INNER JOIN 或 EXISTS）
-- 要求：只查询有过订单的用户信息
-- 期望列：用户ID、用户名、城市
-- ============================================================
SELECT
    u.user_id,
    u.user_name,
    u.city
FROM t_user AS u
LEFT SEMI JOIN t_order AS o
    ON u.user_id = o.user_id;

-- [评价] ✅ 正确。
-- 1. LEFT SEMI JOIN 是 Hive 特有的语法，等价于 INNER JOIN 但只返回左表字段，效率更高。
-- 2. 它不会产生重复行（即使用户有多笔订单，也只返回一次），效果等同于 EXISTS 子查询。
-- 3. 输出列与期望列完全匹配。

-- 方法二：INNER JOIN + DISTINCT
SELECT DISTINCT
    u.user_id,
    u.user_name,
    u.city
FROM t_user AS u
INNER JOIN t_order AS o
    ON u.user_id = o.user_id;

-- 方法三：WHERE EXISTS 子查询
SELECT
    u.user_id,
    u.user_name,
    u.city
FROM t_user AS u
WHERE EXISTS (
    SELECT 1
    FROM t_order AS o
    WHERE o.user_id = u.user_id
);

-- ============================================================
-- 题目 3：查询没有订单的用户（LEFT JOIN + IS NULL）
-- 要求：找出没有下过任何订单的用户
-- 期望列：用户ID、用户名
-- ============================================================
SELECT DISTINCT
    u.user_id,
    u.user_name
FROM t_user AS u
LEFT JOIN t_order AS o
    ON u.user_id = o.user_id
WHERE o.order_id IS NULL;

-- [评价] ✅ 正确（DISTINCT 冗余但无害）。
-- 1. LEFT JOIN + WHERE o.order_id IS NULL 是经典的"查无匹配"写法，正确找出无订单用户。
-- 2. 由于 t_user 中每个 user_id 唯一，且无匹配时 LEFT JOIN 只会产生一行，这里的 DISTINCT
--    实际上是多余的，但不会影响结果正确性，可省略。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 4：查询每个用户的订单总金额
-- 要求：计算每个用户的订单总金额，没有订单的用户显示0
-- 期望列：用户ID、用户名、订单总金额
-- ============================================================
SELECT
    u.user_id,
    u.user_name,
    COALESCE(SUM(o.amount), 0) AS total_order_amount
FROM t_user AS u
LEFT JOIN t_order AS o
    ON u.user_id = o.user_id
GROUP BY u.user_id, u.user_name;

-- [评价] ✅ 正确。
-- 1. LEFT JOIN 保留所有用户，GROUP BY 按用户聚合。
-- 2. SUM(o.amount) 对无订单用户返回 NULL，COALESCE(..., 0) 将其转为 0，符合"没有订单显示0"的要求。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 5：查询包含退款订单的完整订单信息
-- 要求：关联订单表和退款表，查询所有订单及其退款情况，
--       没有退款的订单退款列显示NULL
-- 期望列：订单ID、用户ID、商品、金额、退款ID、退款金额
-- ============================================================
SELECT
    o.order_id,
    o.user_id,
    o.product,
    o.amount,
    r.refund_id,
    r.refund_amt
FROM t_order AS o
LEFT JOIN t_refund AS r
    ON o.order_id = r.order_id;

-- [评价] ✅ 正确。
-- 1. 以 t_order 为左表，LEFT JOIN 保证所有订单都出现。
-- 2. 没有退款的订单（O002、O003、O004、O006、O007）退款列显示为 NULL，正确。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 6：找出下单但已全额退款的用户
-- 要求：找出所有订单都已退款的用户
-- 期望列：用户ID、用户名
-- ============================================================
SELECT
    u.user_id,
    u.user_name
FROM t_user AS u
-- 如果使用 LEFT JOIN，则没下单的用户会错误地被统计进来
INNER JOIN t_order AS o
    ON u.user_id = o.user_id
LEFT JOIN t_refund AS r
    ON o.order_id = r.order_id
GROUP BY u.user_id, u.user_name
-- 必须用 HAVING，因为是所有订单都已退款
HAVING COUNT(o.order_id) = COUNT(r.refund_id);

-- [评价] ❌ 错误 — 逻辑不满足题目要求。
-- 1. 题目要求：找出"所有订单都已退款的用户"（即该用户的每一笔订单都在退款表中）。
-- 2. 当前写法：WHERE r.refund_id IS NOT NULL 只筛选出"存在至少一笔退款"的用户。
-- 3. 以样本数据为例：U001 有 3 笔订单（O001/O002/O007），仅 O001 退款，U001 不应
--    被选出，但当前写法会错误地将 U001 返回。
-- 4. 正确思路：需要比较每个用户的"订单总数"与"退款订单数"是否相等。
--    参考写法：
--    SELECT u.user_id, u.user_name
--    FROM t_user u
--    INNER JOIN t_order o ON u.user_id = o.user_id
--    LEFT JOIN t_refund r ON o.order_id = r.order_id
--    GROUP BY u.user_id, u.user_name
--    HAVING COUNT(o.order_id) = COUNT(r.refund_id);
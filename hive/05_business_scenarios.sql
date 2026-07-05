-- ============================================================
-- Hive SQL 面试题：综合业务场景
-- ============================================================

-- 建表：用户行为日志表
DROP TABLE IF EXISTS user_behavior;
CREATE TABLE user_behavior (
    user_id    STRING COMMENT '用户ID',
    action     STRING COMMENT '行为类型：view(浏览)/cart(加购)/order(下单)/pay(支付)',
    product_id STRING COMMENT '商品ID',
    action_time STRING COMMENT '行为时间'
) COMMENT '用户行为日志表';

INSERT INTO user_behavior VALUES
('U001', 'view',  'P001', '2024-06-01 10:00:00'),
('U001', 'view',  'P002', '2024-06-01 10:05:00'),
('U001', 'cart',  'P001', '2024-06-01 10:10:00'),
('U001', 'order', 'P001', '2024-06-01 10:15:00'),
('U001', 'pay',   'P001', '2024-06-01 10:20:00'),
('U002', 'view',  'P001', '2024-06-01 11:00:00'),
('U002', 'view',  'P003', '2024-06-01 11:05:00'),
('U002', 'cart',  'P003', '2024-06-01 11:10:00'),
('U003', 'view',  'P002', '2024-06-01 14:00:00'),
('U003', 'order', 'P002', '2024-06-01 14:10:00'),
('U003', 'pay',   'P002', '2024-06-01 14:15:00'),
('U004', 'view',  'P001', '2024-06-01 15:00:00'),
('U004', 'view',  'P002', '2024-06-01 15:05:00'),
('U004', 'cart',  'P001', '2024-06-01 15:10:00'),
('U004', 'cart',  'P002', '2024-06-01 15:12:00'),
('U004', 'order', 'P001', '2024-06-01 15:20:00'),
('U005', 'view',  'P003', '2024-06-01 16:00:00'),
('U005', 'cart',  'P003', '2024-06-01 16:05:00'),
('U005', 'order', 'P003', '2024-06-01 16:10:00'),
('U005', 'pay',   'P003', '2024-06-01 16:15:00');

-- ============================================================
-- 题目 1：转化漏斗分析
-- 要求：统计各行为阶段的用户数，形成转化漏斗
--       view → cart → order → pay
-- 期望列：行为类型、用户数
-- 提示：每个用户+商品组合在同一行为阶段只计一次
-- ============================================================
-- 解题思路：
--   1) 题目要求统计的是「用户数」（COUNT(DISTINCT user_id)），不是 用户+商品 组合数
--   2) 提示「每个用户+商品组合在同一行为阶段只计一次」是为了先把同一用户对同一商品的
--      重复行为去掉，避免同一用户因多次操作同一商品而被重复计入
--   3) 再对去重后的记录统计不同的 user_id 数量，即得到该阶段的用户数
WITH distinct_actions AS (
    -- 每个 用户+商品 组合在同一行为阶段只计一次
    SELECT DISTINCT
        user_id,
        product_id,
        action
    FROM user_behavior
),
stage_users AS (
    -- 统计每个行为阶段的去重用户数
    SELECT
        action                 AS action_type,
        COUNT(DISTINCT user_id) AS user_cnt
    FROM distinct_actions
    GROUP BY action
)
SELECT
    action_type,
    user_cnt
FROM stage_users
ORDER BY
    CASE action_type
        WHEN 'view'  THEN 1
        WHEN 'cart'  THEN 2
        WHEN 'order' THEN 3
        WHEN 'pay'   THEN 4
    END ASC;

-- 期望结果：
-- | action_type | user_cnt |
-- |-------------|----------|
-- | view        | 5 |  -- U001,U002,U003,U004,U005 都浏览过
-- | cart        | 4 |  -- U001,U002,U004,U005 加购过（U003 未加购）
-- | order       | 4 |  -- U001,U003,U004,U005 下单过（U002 未下单）
-- | pay         | 3 |  -- U001,U003,U005 支付过（U002,U004 未支付）

-- 题目 2：商品转化率
-- 要求：计算每个商品的浏览-下单转化率（下单用户数 / 浏览用户数）
-- 期望列：商品ID、浏览用户数、下单用户数、转化率
-- ============================================================
-- 解题思路：
--   1) 先用 DISTINCT 去重，使每个 用户+商品 组合在同一行为阶段只计一次
--   2) 按商品分组，分别统计 view 和 order 阶段的去重用户数
--   3) 转化率 = 下单用户数 / 浏览用户数（用 ROUND 保留 2 位小数）
WITH dedup_action AS (
    -- 每个 用户+商品+行为 只保留一条
    SELECT DISTINCT
        user_id,
        product_id,
        action
    FROM user_behavior
),
product_stats AS (
    SELECT
        product_id,
        SUM(CASE WHEN action = 'view'  THEN 1 ELSE 0 END) AS view_user_cnt,
        SUM(CASE WHEN action = 'order' THEN 1 ELSE 0 END) AS order_user_cnt
    FROM dedup_action
    GROUP BY product_id
)
SELECT
    product_id,
    view_user_cnt,
    order_user_cnt,
    ROUND(order_user_cnt / view_user_cnt, 2) AS conversion_rate
FROM product_stats
ORDER BY product_id;

-- 期望结果（基于 INSERT 数据）：
--   P001: view  {U001,U002,U004}  order {U001,U004}          → 2/3 ≈ 0.67
--   P002: view  {U001,U003,U004}  order {U003}               → 1/3 ≈ 0.33
--   P003: view  {U002,U005}       order {U005}               → 1/2 = 0.50
-- | product_id | view_user_cnt | order_user_cnt | conversion_rate |
-- |------------|---------------|----------------|-----------------|
-- | P001       | 3 | 2 | 0.67 |
-- | P002       | 3 | 1 | 0.33 |
-- | P003       | 2 | 1 | 0.50 |

-- 题目 3：用户行为路径
-- 要求：按用户分组，按时间排序，串联每个用户的行为路径
--       例如：U001 → view→view→cart→order→pay
-- 期望列：用户ID、行为路径
-- 提示：使用 COLLECT_LIST 或 CONCAT_WS 聚合
-- ============================================================

-- 题目 4：找出浏览了但未下单的商品
-- 要求：找出每个用户浏览过但没有下单的商品
-- 期望列：用户ID、商品ID
-- ============================================================

-- 题目 5：加购但未支付的用户
-- 要求：找出加购了商品但最终没有支付的用户
-- 期望列：用户ID、商品ID
-- ============================================================

-- 题目 6：每个用户首次行为到最后一次行为的时间跨度
-- 要求：计算每个用户从第一次行为到最后一次行为的时间差（单位：分钟）
-- 期望列：用户ID、首次行为时间、末次行为时间、时间跨度(分钟)
-- ============================================================
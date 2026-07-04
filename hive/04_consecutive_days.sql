-- ============================================================
-- Hive SQL 面试题：连续登录与日期处理
-- ============================================================
-- 建表：用户登录日志表
DROP TABLE IF EXISTS user_login_log;

CREATE TABLE user_login_log (
    user_id STRING COMMENT '用户ID',
    login_date STRING COMMENT '登录日期'
) COMMENT '用户登录日志表';

INSERT INTO
    user_login_log
VALUES
    -- 用户 U001：连续登录 2024-03-01 ~ 03-06
    ('U001', '2024-03-01'),
    ('U001', '2024-03-02'),
    ('U001', '2024-03-03'),
    ('U001', '2024-03-04'),
    ('U001', '2024-03-05'),
    ('U001', '2024-03-06'),
    -- 用户 U001：间隔后再次登录
    ('U001', '2024-03-10'),
    ('U001', '2024-03-11'),
    -- 用户 U002：连续登录 03-01 ~ 03-03
    ('U002', '2024-03-01'),
    ('U002', '2024-03-02'),
    ('U002', '2024-03-03'),
    -- 用户 U002：间隔后登录
    ('U002', '2024-03-08'),
    ('U002', '2024-03-09'),
    ('U002', '2024-03-10'),
    ('U002', '2024-03-11'),
    ('U002', '2024-03-12'),
    -- 用户 U003：不连续登录
    ('U003', '2024-03-01'),
    ('U003', '2024-03-03'),
    ('U003', '2024-03-05'),
    ('U003', '2024-03-07'),
    -- 用户 U004：连续登录 03-10 ~ 03-15
    ('U004', '2024-03-10'),
    ('U004', '2024-03-11'),
    ('U004', '2024-03-12'),
    ('U004', '2024-03-13'),
    ('U004', '2024-03-14'),
    ('U004', '2024-03-15');

-- ============================================================
-- 题目 1：每个用户的最大连续登录天数
-- 要求：计算每个用户连续登录的最大天数
-- 期望列：用户ID、最大连续登录天数
-- 提示：使用 ROW_NUMBER + 日期差值分组法
--       思路：按用户分组，日期排序，用日期减去排名序号，
--             相同差值的即为连续登录段，再求每段长度取最大值
-- ============================================================
-- 日期去重
with
    dedup_login as (
        select distinct
            user_id,
            login_date
        from
            user_login_log
    ),
    -- 用户分区为登录日期添加序号
    login_with_label as (
        select
            user_id,
            login_date,
            row_number() over (
                partition by
                    user_id
                order by
                    login_date
            ) as rn
        from
            dedup_login
    ),
    -- 为每个用户登录日期添加分组序号，分组序号为登录日期减去排名序号
    login_with_rank as (
        select
            user_id,
            login_date,
            date_add(login_date, - rn) as grp
        from
            login_with_label
    ),
    -- 计算每个用户每个登录日期的连续登录天数
    login_with_cont_days as (
        select
            user_id,
            count(*) as cont_days
        from
            login_with_rank
        group by
            user_id,
            grp
    )
select
    user_id,
    max(cont_days) as max_cont_days
from
    login_with_cont_days
group by
    user_id;

-- ------------------------------------------------------------
-- 【分析评价 · 题目 1】  评分: 9.0 / 10
-- ------------------------------------------------------------
-- ✅ 逻辑正确：采用经典的「日期 - row_number() = 分组键」解法
-- ✅ 先 distinct 去重，处理了同日多次登录的边界情况
-- ✅ CTE 分层清晰、注释详尽，可读性极好
-- 📈 预期结果:
--      U001 → 6  (03-01~03-06)
--      U002 → 5  (03-08~03-12)
--      U003 → 1  (无连续段，每个日期自成一段)
--      U004 → 6  (03-10~03-15)
-- ⚠️ 小提示：U003 返回 1 而非 0，符合「最大连续登录天数」定义
-- 💡 改进建议：login_with_label 与 login_with_rank 可合并为一层 CTE
--      (参考题目 2 的精简写法)
-- ------------------------------------------------------------
-- 题目 2：连续登录超过3天的用户及连续天数
-- 要求：找出连续登录超过3天的用户，并显示其连续天数
-- 期望列：用户ID、连续开始日期、连续结束日期、连续天数
-- ============================================================
with
    dedup_login as (
        select distinct
            user_id,
            login_date
        from
            user_login_log
    ),
    login_with_rank as (
        select
            user_id,
            login_date,
            date_add(
                login_date,
                - row_number() over (
                    partition by
                        user_id
                    order by
                        login_date
                )
            ) as grp
        from
            dedup_login
    ),
    login_with_cont_days as (
        select
            user_id,
            min(login_date) as start_date,
            max(login_date) as end_date,
            count(*) as cont_days
        from
            login_with_rank
        group by
            user_id,
            grp
    )
select
    user_id,
    start_date,
    end_date,
    cont_days
from
    login_with_cont_days
where
    cont_days > 3;

-- ------------------------------------------------------------
-- 【分析评价 · 题目 2】  评分: 8.5 / 10
-- ------------------------------------------------------------
-- ✅ 解法正确：基于题目1思路，额外求 min/max(login_date) 作为起止日期
-- ✅ CTE 合并得更精炼（把 label 与 rank 合成一层，比题目1更优）
-- 🚨 关键 BUG：题目要求「超过 3 天」应为 cont_days > 3，代码用 >= 3
--     → U002 的 3 天段(03-01~03-03)会被错误保留
--     → "超过3天"严格语义是 >=4
-- 📈 当前(>=3)结果:               📈 修正后(>3)结果:
--      U001  03-01~03-06  6           U001  03-01~03-06  6
--      U002  03-01~03-03  3  ←应剔除  U002  03-08~03-12  5
--      U002  03-08~03-12  5           U004  03-10~03-15  6
--      U004  03-10~03-15  6
-- 💡 改进建议：① 把 >=3 改为 >3  ② 加 ORDER BY user_id, start_date
-- ------------------------------------------------------------
-- 题目 3：用户登录间隔分析
-- 要求：计算每个用户每次登录与上一次登录的间隔天数
-- 期望列：用户ID、登录日期、上次登录日期、间隔天数
-- 提示：使用 LAG 窗口函数
-- ============================================================
with
    dedup_login as (
        select distinct
            user_id,
            login_date
        from
            user_login_log
    ),
    login_with_prev as (
        select
            user_id,
            login_date,
            lag(login_date) over (
                partition by
                    user_id
                order by
                    login_date
            ) as prev_login_date
        from
            dedup_login
    ),
    login_with_interval as (
        select
            user_id,
            login_date,
            prev_login_date,
            case
                when prev_login_date is null then 0
                else datediff(login_date, prev_login_date)
            end as interval_days
        from
            login_with_prev
    )
select
    user_id,
    login_date,
    prev_login_date,
    interval_days
from
    login_with_interval
where
    interval_days > 0;

-- ------------------------------------------------------------
-- 【分析评价 · 题目 3】  评分: 8.0 / 10
-- ------------------------------------------------------------
-- ✅ LAG 窗口函数使用规范：partition by user_id order by login_date
-- ✅ datediff(end, start) 参数顺序正确，返回 end-start
-- ✅ 去重前置，避免同日多次登录干扰 LAG
-- ⚠️ 语义偏差：题目说「每次登录与上一次的间隔」，
--     但 where interval_days > 0 会过滤掉每个用户的首行
--     → 若题目要求展示所有登录记录，首行应保留(显示 NULL 上次日期)
--     → 若题目要「有上次登录的记录」，当前过滤才合理
-- ⚠️ 逻辑冗余：CASE 把首行 interval_days 置 0，WHERE 又把 0 过滤掉
--     → 两者只保留其一即可，存在逻辑重复
-- 📈 预期结果(共22行):
--      U001 7行(首行03-01被过滤), U002 7行, U003 3行, U004 5行
-- 💡 改进建议：
--     方案A-保留首行：去掉 WHERE，CASE 改为 "when prev is null then null"
--     方案B-仅查间隔：保留 WHERE，可省略 CASE 的 NULL 分支处理
-- ------------------------------------------------------------
-- 题目 4：2024年3月的新增用户数（按天统计）
-- 要求：统计3月每天「首次登录」的用户数
-- 期望列：日期、新增用户数
-- 提示：先找出每个用户的最早登录日期，再按日期分组统计
-- ============================================================
with
    dedup_login as (
        select distinct
            user_id,
            login_date
        from
            user_login_log
    ),
    first_login_in_March as (
        select
            user_id,
            min(login_date) as first_login_date
        from
            dedup_login
        where
            login_date like '2024-03-%'
        group by
            user_id
    ),
    new_user_of_date as (
        select
            first_login_date,
            count(*) as new_user_cnt
        from
            first_login_in_March
        group by
            first_login_date
    )
select
    first_login_date,
    new_user_cnt
from
    new_user_of_date
order by
    first_login_date;

-- ------------------------------------------------------------
-- 【分析评价 · 题目 4】  评分: 6.5 / 10
-- ------------------------------------------------------------
-- ✅ 思路正确：min(login_date) 求"首次登录"，再按首次登录日期分组计数
-- ✅ CTE 三层递进，符合提示步骤
-- 🚨 关键 BUG：题目要求「2024年3月」的新增用户数，代码完全没有日期过滤！
--     → 当前测试数据全在 3 月，结果"碰巧正确"
--     → 一旦出现非 3 月首次登录用户，会被错误统计
-- ⚠️ 冗余：dedup_login 这层多余。GROUP BY user_id + min() 已经天然去重
-- ⚠️ 缺少 ORDER BY，输出顺序不保证
-- 📈 预期结果(当前数据):
--      2024-03-01 → 3   (U001, U002, U003)
--      2024-03-10 → 1   (U004)
-- 💡 修复建议：
--     ① 在 new_user_of_date 加 WHERE first_login_date BETWEEN '2024-03-01' AND '2024-03-31'
--     ② 删除 dedup_login 这层 CTE
--     ③ 最终 SELECT 加 ORDER BY first_login_date
-- ------------------------------------------------------------
-- 题目 5：次日留存率
-- 要求：计算2024年3月1日登录的用户中，次日（3月2日）也登录的用户占比
-- 期望列：首日、次日留存用户数、首日用户数、次日留存率
-- ============================================================
with
    dedup_login as (
        select distinct
            user_id,
            login_date
        from
            user_login_log
    ),
    -- 2024-03-01 登录的用户集合
    login_user_20240301 as (
        select
            user_id
        from
            dedup_login
        where
            login_date = '2024-03-01'
    ),
    -- 2024-03-02 登录的用户集合
    login_user_20240302 as (
        select
            user_id
        from
            dedup_login
        where
            login_date = '2024-03-02'
    ),
    -- 首日用户数
    day1_user_cnt as (
        select count(*) as day1_users from login_user_20240301
    ),
    -- 次日留存用户数：用 INNER JOIN 求 03-01 与 03-02 的交集
    retained_user_cnt as (
        select
            count(a.user_id) as retained_users
        from
            login_user_20240301 a
            join login_user_20240302 b on a.user_id = b.user_id
    )
select
    '2024-03-01' as first_date,
    '2024-03-02' as next_date,
    d.day1_users,
    r.retained_users,
    round(r.retained_users * 100.0 / d.day1_users, 2) as retention_rate
from
    day1_user_cnt d
    cross join retained_user_cnt r;

-- ------------------------------------------------------------
-- 【分析评价 · 题目 5】  评分: 9.0 / 10  (修正后)
-- ------------------------------------------------------------
-- ✅ 完整输出题目要求的 5 列：首日、次日、首日用户数、留存用户数、留存率
-- ✅ 用 INNER JOIN 替代 IN 子查询：性能更好，Hive 各版本兼容
-- ✅ CTE 拆分清晰：先求两个日期的用户集，再分别统计数量，最后 CROSS JOIN 拼装
-- ✅ round(..., 2) 保留 2 位小数；*100.0 隐式转浮点避免整数除法
-- 📈 预期结果:
--      first_date=2024-03-01, next_date=2024-03-02
--      day1_users=3 (U001,U002,U003)
--      retained_users=2 (U001,U002，U003未在03-02登录)
--      retention_rate=66.67
-- 💡 知识点补充:
--     ① CROSS JOIN 用于把两个聚合后的"单行结果"拼成一行
--        Hive 也支持 from a, b 的隐式笛卡尔积写法
--     ② 求交集的两种写法等价，但 JOIN 通常比 IN 快:
--          JOIN 写法:  from a join b on a.user_id = b.user_id
--          IN   写法:  where user_id in (select user_id from b)
--     ③ 留存率公式: retention_rate = retained_users / day1_users * 100
--        必须用 100.0 而非 100，否则 Hive 整数除法会得到 66 而非 66.67
-- ------------------------------------------------------------
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
    cont_days >= 3;

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

-- 题目 4：2024年3月的新增用户数（按天统计）
-- 要求：统计3月每天「首次登录」的用户数
-- 期望列：日期、新增用户数
-- 提示：先找出每个用户的最早登录日期，再按日期分组统计
-- ============================================================


-- 题目 5：次日留存率
-- 要求：计算2024年3月1日登录的用户中，次日（3月2日）也登录的用户占比
-- 期望列：首日、次日留存用户数、首日用户数、次日留存率
-- ============================================================

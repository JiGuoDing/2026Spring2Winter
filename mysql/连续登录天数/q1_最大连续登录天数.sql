-- Q1: 计算每个用户的最大连续登录天数。

-- 尝试
select user_id as 用户编号, count(*) as 最大连续登录天数 from user_login_log (login_date - row_number()) over (partition by user_id)

-- 需求1：最大连续登录天数（经典断点分组法）
-- 核心思想：利用 ROW_NUMBER() 给登录日期排序，用 登录日期 - 排序号，如果日期是连续的，相减得到的差值就是相等的。差值相同的分为同一组，就是连续登录的分组。
-- 注意：一个用户可能在1月连续登录3天，2月连续登录5天，我们要取最大的5天。

-- 构造基础数据并去重 (保证一天只算一次)
-- 在实际业务中，一天会有多条记录，先按用户和日期去重
with dedup_login as (
    select distinct user_id, login_date
    from user_login_log
),

first_login as (
-- 计算每个用户的首次登录日期（注册日）
    select user_id, min(login_date) as first_date
    from dedup_login
    group by user_id
),

ranked_login as (
-- 为每个用户的登录记录打上序号（从注册日起按日期排序）
    select
        d.user_id,
        d.login_date,
        -- f.first_date,
        row_number() over (partition by d.user_id order by d.login_date) as rn
        from dedup_login d
        -- join first_login f on d.user_id = f.user_id
-- * 这个 ) 后面不能再加,了，因为在 SQL 的 WITH 语句（CTE）语法中，
-- * 逗号是用来分隔多个临时表的。当你写了逗号，数据库引擎会认为你还要继续定义下一个 xxx AS (...)
)

select user_id as 用户编号, max(cont_days) as 最长连续登录天数
from (
    select user_id, date_sub(login_date, interval rn day) as grp, count(*) as cont_days
    from ranked_login
    group by user_id, grp
) t1
group by user_id;
-- select user_id as 用户编号, max(cont_days) as 最长连续登录天数
-- from (
--     -- date_sub(login_date, interval rn day)即login_date - rn，例如 2026-01-01 - 1 = 2025-12-31
--     -- count(*)即可算出每个用户的每一段连续登录天数
--     select user_id, date_sub(login_date, interval rn day) as grp, count(*) as cont_days
--     from ranked_login
--     group by user_id, grp
-- ) t1
-- group by user_id;





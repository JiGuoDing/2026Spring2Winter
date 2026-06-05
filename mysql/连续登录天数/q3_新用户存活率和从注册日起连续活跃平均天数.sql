with dedup_login as (
    select distinct user_id, login_date
    from user_login_log
),

first_login as (
    select user_id, min(login_date) as first_date
    from dedup_login
    group by user_id
),

ranked_login as (
    select user_id, login_date, row_number() over (partition by user_id order by login_date) as rn
    from dedup_login
)

select 
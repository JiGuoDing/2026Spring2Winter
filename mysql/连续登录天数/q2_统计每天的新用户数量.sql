with dedup_login as (
    select distinct user_id, login_date
    from user_login_log
),

first_login as (
    select user_id, min(login_date) as first_date
    from dedup_login
    group by user_id
)

select first_date as register_date, count(*) as new_user_cnt
from first_login
group by first_date
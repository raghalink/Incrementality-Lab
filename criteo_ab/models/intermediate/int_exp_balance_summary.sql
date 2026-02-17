with fact as (

    select
        variant,
        f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11
    from {{ ref('int_exp_user_fact') }}

),

unpivoted as (

    select
        variant,
        feature_name,
        feature_value
    from fact
    unpivot(
        feature_value for feature_name in (
            f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11
        )
    )

),

stats_by_variant as (

    select
        feature_name,
        variant,
        count(*) as n_users,
        avg(feature_value) as mean_value,
        stddev_samp(feature_value) as std_value,
        avg(iff(feature_value is null, 1, 0)) as missing_rate
    from unpivoted
    group by 1, 2

),

control_means as (

    select
        feature_name,
        mean_value as control_mean
    from stats_by_variant
    where variant = 'Control'

)

select
    s.feature_name,
    s.variant,
    s.n_users,
    s.mean_value,
    s.std_value,
    s.missing_rate,
    (s.mean_value - c.control_mean) as difference_vs_control
from stats_by_variant s
left join control_means c
  on s.feature_name = c.feature_name
order by feature_name, variant
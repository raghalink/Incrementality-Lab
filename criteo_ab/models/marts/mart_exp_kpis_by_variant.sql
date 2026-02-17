with base as (

    select
        analysis_type,
        variant,
        user_id,
        conversion,
        visit
    from {{ ref('int_exp_analysis_views') }}

),

aggregated as (

    select
        analysis_type,
        variant,

        count(distinct user_id) as users,
        sum(conversion) as conversions,
        sum(visit) as visits

    from base
    group by 1, 2

)

select
    analysis_type,
    variant,
    'conversion_rate' as metric_name,
    users,
    conversions as metric_numerator,
    users as metric_denominator,
    conversions / nullif(users, 0) as metric_value
from aggregated

union all

select
    analysis_type,
    variant,
    'visit_rate' as metric_name,
    users,
    visits as metric_numerator,
    users as metric_denominator,
    visits / nullif(users, 0) as metric_value
from aggregated
with base as (

    select
        user_id,
        variant,
        conversion_flag,
        visit_flag,
        exposure_flag,
        f0
    from {{ ref('int_exp_user_fact') }}
    where f0 is not null

),

segmented as (

    select
        *,
        ntile(3) over (order by f0) as f0_tertile
    from base

),

labeled as (

    select
        case
            when f0_tertile = 1 then 'f0_low'
            when f0_tertile = 2 then 'f0_mid'
            when f0_tertile = 3 then 'f0_high'
        end as segment_name,

        variant,
        conversion_flag,
        visit_flag,
        exposure_flag
    from segmented

),

aggregated as (

    select
        'criteo_uplift'::varchar as experiment_id,
        'ITT'::varchar as analysis_type,
        segment_name,

        sum(case when variant = 'Control' then 1 else 0 end) as n_control,
        sum(case when variant = 'Treatment' then 1 else 0 end) as n_treatment,

        sum(case when variant = 'Control' then conversion_flag else 0 end) as conv_control,
        sum(case when variant = 'Treatment' then conversion_flag else 0 end) as conv_treatment,

        sum(case when variant = 'Control' then visit_flag else 0 end) as visit_control,
        sum(case when variant = 'Treatment' then visit_flag else 0 end) as visit_treatment,

        avg(case when variant = 'Treatment' then exposure_flag end)::float
            as exposure_rate_treatment

    from labeled
    group by segment_name

)

select *
from aggregated


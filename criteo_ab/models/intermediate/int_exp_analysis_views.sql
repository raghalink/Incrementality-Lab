with base as (
    select 
    b.user_id,
    p.variant,
    b.exposure_flag,
    b.visit_flag,
    b.conversion_flag
    from {{ ref('stg_criteo_uplift') }} b
    join {{ ref('int_exp_population') }} p
    on b.user_id = p.user_id
    where p.is_in_analysis = true
),

itt as 
(
    select 
    user_id,
    'ITT' as analysis_type,
    variant,
    exposure_flag as exposure,
    visit_flag as visit,
    conversion_flag as conversion
    from base
),

exposure_view as (
    select 
    user_id,
    'Exposure View' as analysis_type,
    case when exposure_flag = 1 then 'Exposed' 
         else 'Not Exposed' 
    end as variant,
    exposure_flag as exposure,
    visit_flag as visit,
    conversion_flag as conversion
    from base
)

select * from itt
union all
select * from exposure_view
with base as (

    select *
    from {{ ref('stg_criteo_uplift') }}

),

pop as (

    select
        user_id,
        variant,
        is_in_analysis,
        exclude_reason
    from {{ ref('int_exp_population') }}

)

select
    b.user_id,
    p.variant,
    b.treatment_flag,
    b.exposure_flag,
    b.visit_flag,
    b.conversion_flag,

    b.f0, b.f1, b.f2, b.f3, b.f4, b.f5,
    b.f6, b.f7, b.f8, b.f9, b.f10, b.f11,

    p.is_in_analysis,
    p.exclude_reason

from base b
join pop p
  on b.user_id = p.user_id
where p.is_in_analysis = true
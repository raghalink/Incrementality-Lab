with params as (

    select
        'criteo_uplift'::varchar as experiment_id,
        'ITT'::varchar as analysis_type,
        'ALL'::varchar as segment_name,
        0.0010::float as practical_threshold_abs,
        -0.0020::float as guardrail_visit_floor_abs

),

validity as (

    select
        max(case when check_name = 'SRM' then status end) as srm_status,
        max(case when check_name = 'BALANCE' then status end) as balance_status
    from {{ ref('mart_exp_validity_checks') }}

),

counts as (

    select
        sum(case when variant = 'Control' then 1 else 0 end) as n_control,
        sum(case when variant = 'Treatment' then 1 else 0 end) as n_treatment,

        sum(case when variant = 'Control' then conversion_flag else 0 end) as conv_control,
        sum(case when variant = 'Treatment' then conversion_flag else 0 end) as conv_treatment,

        sum(case when variant = 'Control' then visit_flag else 0 end) as visit_control,
        sum(case when variant = 'Treatment' then visit_flag else 0 end) as visit_treatment,

        avg(case when variant = 'Treatment' then exposure_flag end)::float as exposure_rate_treatment

    from {{ ref('int_exp_user_fact') }}

)

select
    p.experiment_id,
    p.analysis_type,
    p.segment_name,

    c.n_control,
    c.n_treatment,
    c.conv_control,
    c.conv_treatment,
    c.visit_control,
    c.visit_treatment,
    c.exposure_rate_treatment,

    v.srm_status,
    v.balance_status,

    p.practical_threshold_abs,
    p.guardrail_visit_floor_abs

from params p
cross join counts c
cross join validity v
with params as (

    select
        'criteo_uplift'::varchar as experiment_id,
        0.005::float as srm_abs_share_tolerance,
        0.10::float as balance_std_diff_pass,
        0.25::float as balance_std_diff_fail

),

/* ---------------- SRM ---------------- */

srm_counts as (

    select
        sum(case when variant = 'Control' then 1 else 0 end)  as n_control,
        sum(case when variant = 'Treatment' then 1 else 0 end) as n_treatment,
        count(*) as n_total
    from {{ ref('int_exp_population') }}
    where is_in_analysis = true

),

srm_eval as (

    select
        p.experiment_id,
        'ITT'::varchar as analysis_type,
        'SRM'::varchar as check_name,

        c.n_control,
        c.n_treatment,
        c.n_total,

        (c.n_treatment / nullif(c.n_total, 0))::float as treatment_share,
        abs((c.n_treatment / nullif(c.n_total, 0))::float - 0.5::float) as abs_dev_from_50_50,

        p.srm_abs_share_tolerance as threshold
    from srm_counts c
    cross join params p

),

srm as (

    select
        experiment_id,
        analysis_type,
        check_name,
        case when abs_dev_from_50_50 <= threshold then 'pass' else 'fail' end as status,
        abs_dev_from_50_50 as signal_value,
        threshold,
        object_construct(
            'n_total', n_total,
            'n_control', n_control,
            'n_treatment', n_treatment,
            'treatment_share', treatment_share
        ) as details
    from srm_eval

),

/* ---------------- Balance ---------------- */

balance_wide as (

    select
        feature_name,
        max(case when variant = 'Control' then std_value end) as control_std,
        max(case when variant = 'Treatment' then difference_vs_control end) as diff_vs_control
    from {{ ref('int_exp_balance_summary') }}
    group by 1

),

balance_scored as (

    select
        feature_name,
        (diff_vs_control / nullif(control_std, 0))::float as std_diff
    from balance_wide

),

balance_agg as (

    select
        p.experiment_id,
        'ITT'::varchar as analysis_type,
        'BALANCE'::varchar as check_name,

        max(abs(std_diff)) as max_abs_std_diff,
        max_by(feature_name, abs(std_diff)) as worst_feature,

        p.balance_std_diff_pass as pass_threshold,
        p.balance_std_diff_fail as fail_threshold
    from balance_scored
    cross join params p
    group by 
        p.experiment_id,
        p.balance_std_diff_pass,
        p.balance_std_diff_fail

),

balance as (

    select
        experiment_id,
        analysis_type,
        check_name,
        case
            when max_abs_std_diff <= pass_threshold then 'pass'
            when max_abs_std_diff >= fail_threshold then 'fail'
            else 'warn'
        end as status,
        max_abs_std_diff as signal_value,
        pass_threshold as threshold,
        object_construct(
            'worst_feature', worst_feature,
            'max_abs_std_diff', max_abs_std_diff,
            'pass_threshold', pass_threshold,
            'fail_threshold', fail_threshold
        ) as details
    from balance_agg

)

select
    experiment_id,
    analysis_type,
    check_name,
    status,
    signal_value,
    threshold,
    details
from srm

union all

select
    experiment_id,
    analysis_type,
    check_name,
    status,
    signal_value,
    threshold,
    details
from balance

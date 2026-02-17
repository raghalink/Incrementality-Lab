select
    feature_name,

    max(case when variant = 'Control' then difference_vs_control end)   as control_diff,
    max(case when variant = 'Treatment' then difference_vs_control end) as treatment_diff,

    max(case when variant = 'Control' then missing_rate end)   as control_missing_rate,
    max(case when variant = 'Treatment' then missing_rate end) as treatment_missing_rate

from analytics.int_exp_balance_summary
group by feature_name
order by abs(treatment_diff) desc;
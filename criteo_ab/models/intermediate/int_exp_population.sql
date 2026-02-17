with base as (
    select * 
    from {{ ref('stg_criteo_uplift') }}
)

select 
    user_id,
    case when treatment_flag = 1 then 'Treatment' 
    else 'Control' 
    end as variant,
    true as is_in_analysis,
    null as exclude_reason

from base

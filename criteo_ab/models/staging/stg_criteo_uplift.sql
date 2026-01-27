with source as (
    SELECt * 
    from {{ source('raw', 'criteo_base') }}
)

select
    user_id::number        as user_id,
    treatment::number      as treatment_flag,
    exposure::number       as exposure_flag,
    visit::number         as visit_flag,
    conversion::number     as conversion_flag,
    f0::float               as f0,
    f1::float               as f1,
    f2::float               as f2,
    f3::float               as f3,
    f4::float               as f4,
    f5::float               as f5,
    f6::float               as f6,
    f7::float               as f7,
    f8::float               as f8,
    f9::float               as f9,
    f10::float              as f10,
    f11::float              as f11

from source
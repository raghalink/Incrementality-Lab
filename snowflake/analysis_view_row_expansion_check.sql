select
    (select count(*) from analytics.int_exp_analysis_views)      as analysis_view_rows,
    (select count(*) from analytics.int_exp_population)          as population_rows,
    (select count(*) from analytics.int_exp_analysis_views)
      / nullif((select count(*) from analytics.int_exp_population), 0)
      as ratio
;
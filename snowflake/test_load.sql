select 
count(*)  as row_count,
min(user_id) as min_user_id,
max(user_id) as max_user_id
from AB_DB.RAW.CRITEO_UPLIFT

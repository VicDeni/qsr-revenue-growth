select
    upper(state)                          as state,
    {{ try_cast('year', t_int()) }}       as year,
    {{ try_cast('population', t_int()) }} as population
from {{ source('raw', 'state_population') }}

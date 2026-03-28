-- Staging: Clean and standardize raw GitHub events
-- This is an ephemeral model 
-- Used in downstream marts

{{ config(
    materialized='ephemeral',
    tags=['staging', 'daily'],
)}}

with source_data as (
    select
        cast(id as int64) as event_id,
        type as event_type,
        actor_login,
        actor_id,
        repo_name,
        repo_id,
        created_at,
        current_timestamp() as _dbt_loaded_at
    from {{ source('raw', 'raw_events') }} -- pulls data from GCP bucket
    -- Only include events from the last 90 days by default
    where created_at >= timestamp(date_sub(current_date(), interval {{ var('lookback_days') }} day))
),


-- Remove exact duplicates
deduplicated as (
    select distinct
        event_id,
        event_type,
        actor_login,
        actor_id,
        repo_name,
        repo_id,
        created_at,
        _dbt_loaded_at
    from source_data
),

-- Add validation flags
validations as (
    select
        *,      
        case when event_id is null then false else true end as is_valid_event_id,
        case when event_type is null then false else true end as is_valid_type,
        case when repo_name is null then false else true end as is_valid_repo
    from deduplicated
)

select * from validations

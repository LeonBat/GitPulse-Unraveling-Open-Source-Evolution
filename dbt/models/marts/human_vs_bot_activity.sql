-- Human vs Bot Activity Analysis
-- Separates GitHub activity into human vs bot contributions
-- Bots are identified by "bot" in the actor_login field

{{ config(
    materialized='table',
    partition_by={
        'field': 'activity_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['contributor_type', 'activity_date'],
    tags=['marts', 'daily', 'dashboard'],
    schema='analytics',
)}}

with activity_classification as (
    select
        date(created_at) as activity_date,
        actor_login,
        actor_id,
        -- Classify as bot or human
        case
            when lower(actor_login) like '%bot%'
              or lower(actor_login) like '%[bot]%'
              or lower(actor_login) like 'dependabot%'
              or lower(actor_login) like 'renovate%'
              or lower(actor_login) like 'github-actions%'
            then 'bot'
            else 'human'
        end as contributor_type,
        event_type,
        repo_name,
        repo_id,
        1 as activity_count
    from {{ ref('stg_github_events') }}
    where is_valid_event_id and is_valid_repo and actor_login is not null
),

daily_activity_summary as (
    select
        activity_date,
        contributor_type,
        count(*) as total_events,
        count(distinct actor_login) as unique_contributors,
        count(distinct actor_id) as unique_contributor_ids,
        count(distinct repo_name) as repos_affected,
        -- Event type breakdown
        count(case when event_type = 'PushEvent' then 1 end) as push_events,
        count(case when event_type = 'PullRequestEvent' then 1 end) as pull_events,
        count(case when event_type = 'IssuesEvent' then 1 end) as issue_events,
        count(case when event_type = 'CreateEvent' then 1 end) as create_events,
        count(case when event_type = 'ForkEvent' then 1 end) as fork_events,
        current_timestamp() as computed_at
    from activity_classification
    group by 1, 2
)

select
    activity_date,
    contributor_type,
    total_events,
    unique_contributors,
    unique_contributor_ids,
    repos_affected,
    push_events,
    pull_events,
    issue_events,
    create_events,
    fork_events,
    computed_at
from daily_activity_summary
order by activity_date desc, contributor_type

-- Bot Detection Logic:
-- Looks for common bot indicators in username:
-- - "bot" anywhere in name (e.g., "renovate-bot", "dependabot", "huggingbot")
-- - "[bot]" suffix (GitHub's standard bot marker)
-- - Known bot patterns: dependabot, renovate, github-actions
--
-- This captures:
-- Dependency update bots (Dependabot, Renovate)
-- CI/CD bots (GitHub Actions)
-- Custom bots (anything with "bot" in name)
--
-- TODO: For more accuracy, integrate with GitHub API to check:
-- - User.is_bot flag (more reliable than name-based detection)
-- - Organization bot accounts
-- - Verified bot accounts

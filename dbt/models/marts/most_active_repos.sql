-- Most Active Repositories Metric
-- Calculates activity score based on weighted contributions
-- Shows repositories with highest development activity over time

{{ config(
    materialized='table',
    partition_by={
        'field': 'metric_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['weighted_activity_score'],
    tags=['marts', 'daily', 'dashboard'],
    schema='analytics',
)}}

-- counting different event types for each valid repository 
with event_counts as (
    select
        date(created_at) as event_date,
        repo_name,
        repo_id,
        count(case when event_type = 'ForkEvent' then 1 end) as fork_count,
        count(case when event_type = 'IssuesEvent' then 1 end) as issue_count,
        count(case when event_type = 'PushEvent' then 1 end) as push_count,
        count(case when event_type = 'PullRequestEvent' then 1 end) as pull_count,
        count(*) as total_activities
    from {{ ref('stg_github_events') }}
    where is_valid_event_id and is_valid_repo
    group by 1, 2, 3
),

-- Summarize daily acitvity counts for each repository
daily_aggregations as (
    select
        event_date as metric_date,
        repo_name,
        repo_id,
        sum(fork_count) as daily_forks,
        sum(issue_count) as daily_issues,
        sum(push_count) as daily_pushes,
        sum(pull_count) as daily_pulls,
        sum(total_activities) as daily_total_activities
    from event_counts
    group by 1, 2, 3
),

-- Rolling 7-day aggregations for activity scoring
rolling_window as (
    select
        metric_date,
        repo_name,
        repo_id,
        sum(daily_forks) over (
            partition by repo_name 
            order by metric_date 
            rows between 6 preceding and current row
        ) as forks_7d,
        sum(daily_issues) over (
            partition by repo_name 
            order by metric_date 
            rows between 6 preceding and current row
        ) as issues_7d,
        sum(daily_pushes) over (
            partition by repo_name 
            order by metric_date 
            rows between 6 preceding and current row
        ) as pushes_7d,
        sum(daily_pulls) over (
            partition by repo_name 
            order by metric_date 
            rows between 6 preceding and current row
        ) as pulls_7d,
        sum(daily_total_activities) over (
            partition by repo_name 
            order by metric_date 
            rows between 6 preceding and current row
        ) as total_activities_7d
    from daily_aggregations
),

-- Calculate activity score
-- Note: stars data would ideally come from a separate GitHub API call
-- For now, we use activity count as proxy; in production, integrate star counts
activity_scores as (
    select
        metric_date,
        repo_name,
        repo_id,
        forks_7d,
        issues_7d,
        pushes_7d,
        pulls_7d,
        total_activities_7d,
        cast(
            (forks_7d + issues_7d + pushes_7d + pulls_7d) as float64
        ) / (case 
              when total_activities_7d = 0 then 1 
              else nullif(total_activities_7d, 0) 
            end) as activity_score_normalized,
        -- Alternative: activity ratio (for scenarios without star data)
        (forks_7d * 5 + issues_7d * 3 + pushes_7d * 1 + pulls_7d * 4) as weighted_activity_score
    from rolling_window
    where total_activities_7d > 10  -- Filter out repos with minimal activity
),

-- Rank repositories
ranked_repos as (
    select
        *,
        row_number() over (
            partition by metric_date 
            order by weighted_activity_score desc
        ) as activity_rank,
        current_timestamp() as computed_at
    from activity_scores
)

select
    metric_date,
    repo_name,
    repo_id,
    forks_7d,
    issues_7d,
    pushes_7d,
    pulls_7d,
    total_activities_7d,
    activity_score_normalized,
    weighted_activity_score,
    activity_rank,
    computed_at
from ranked_repos
where activity_rank <= 10
-- TODO: Enhance with actual star counts from GitHub API
-- Recommended integration:
-- 1. Create a separate GCS-staged CSV with repo star counts (refreshed monthly)
-- 2. LEFT JOIN this model with GitHub-API-fetched stars
-- 3. Recalculate: underrated_score = (forks + issues + pulls) / stars
--    This would give true "underrated" metric (high activity, low recognition)

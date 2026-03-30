-- GitHub Archive Data Warehouse Schema (Simplified)
-- Only raw and two dashboard tables

-- ============================================================================
-- RAW TABLE (Landing Zone)
-- ============================================================================

-- Raw events: Direct from ingestion pipeline
CREATE TABLE IF NOT EXISTS `project.dataset.name` (
  id STRING,
  type STRING,
  actor_login STRING,
  actor_id INT64,
  repo_name STRING,
  repo_id INT64,
  created_at TIMESTAMP,
  _loaded_at STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY repo_name, actor_login;

-- ============================================================================
-- STAGING TABLE (Cleaned Data)
-- ============================================================================

-- Cleaned raw events (created by dbt stg_github_events)
CREATE TABLE IF NOT EXISTS `project_id.dataset.stg_github_events` (
event_id INT64,
event_type STRING,
actor_login STRING,
actor_id INT64,
repo_name STRING,
repo_id INT64,
created_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY repo_name, actor_login;


-- ============================================================================
-- DASHBOARD TABLES (Marts)
-- ============================================================================

-- TILE 1: Most Active Repos (top 10 by weighted activity score)

CREATE TABLE IF NOT EXISTS `project_id.dataset.most_active_repos` (
metric_date DATE,
repo_name STRING,
repo_id INT64,
forks_7d INT64,
issues_7d INT64,
pulls_7d INT64,
pushes_7d INT64,
total_activities_7d INT64,
weighted_activity_score FLOAT64,
activity_rank INT64
);


-- TILE 2: Human vs Bot Activity (daily breakdown)

CREATE TABLE IF NOT EXISTS `project_id.dataset.human_vs_bot_activity` (
activity_date DATE,
contributor_type STRING,
event_count INT64,
unique_contributors INT64
);



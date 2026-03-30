"""
GitPulse Streamlit Dashboard
Displays GitHub Archive insights with:
- Most Underrated Repositories (pie chart)
- Human vs Bot Activity (time series)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
from datetime import datetime, timedelta
import os

# ============================================================================
# Configuration
# ============================================================================

st.set_page_config(
    page_title="GitPulse Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# BigQuery setup
@st.cache_resource
def init_bigquery():
    """Initialize BigQuery client"""
    project_id = os.getenv("GCP_PROJECT_ID")
    return bigquery.Client(project=project_id)

bq_client = init_bigquery()
project_id = os.getenv("GCP_PROJECT_ID", "project_id_placeholder")
dataset_id = os.getenv("BQ_DATASET_NAME", "github_archive")

# ============================================================================
# Data Loading Functions
# ============================================================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_underrated_repos(days_back=1):
    """Load top 10 underrated repositories"""
    metric_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    query = f"""
    SELECT
        repo_name,
        underrated_rank,
        weighted_activity_score,
        forks_7d,
        issues_7d,
        pulls_7d,
        pushes_7d,
        total_activities_7d,
        metric_date
    FROM `{project_id}.{dataset_id}_analytics.underrated_repos`
    WHERE metric_date = '{metric_date}'
    ORDER BY underrated_rank ASC
    LIMIT 10
    """
    
    return bq_client.query(query).to_dataframe()

@st.cache_data(ttl=3600)
def load_human_vs_bot(days_back=30):
    """Load human vs bot activity for time series"""
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    query = f"""
    SELECT
        activity_date,
        contributor_type,
        total_events,
        unique_contributors,
        repos_affected,
        push_events,
        pull_events,
        issue_events
    FROM `{project_id}.{dataset_id}_analytics.human_vs_bot_activity`
    WHERE activity_date >= '{start_date}'
    ORDER BY activity_date DESC
    """
    
    return bq_client.query(query).to_dataframe()

# ============================================================================
# Dashboard Layout
# ============================================================================

st.title("📊 GitPulse GitHub Analytics Dashboard")
st.markdown("Real-time insights from the GitHub Archive dataset")

# Sidebar filters
st.sidebar.header("⚙️ Filters")
days_back_underrated = st.sidebar.slider(
    "Days back (Underrated Repos)",
    min_value=1,
    max_value=30, #Thirty days as maximum to maintain relevance
    value=1,
    help="How many days back to look for underrated repos"
)

days_back_activity = st.sidebar.slider(
    "Days back (Activity Trend)",
    min_value=7,
    max_value=90,
    value=30,
    help="How many days back to show in activity trend"
)

# Load data
try:
    df_underrated = load_underrated_repos(days_back_underrated)
    df_activity = load_human_vs_bot(days_back_activity)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# ============================================================================
# Tile 1: Most Underrated Repositories (Pie Chart)
# ============================================================================

st.header("🎯 Tile 1: Most Active Repositories")
st.markdown("""
**Activity Score Calculation:**
- Score = Weighted activity: (Forks×5 + Issues×3 + Pulls×4 + Pushes×1) over past 7 days
- Higher score = More development activity across all contribution types
- Larger pie slice = Repository with the most weighted contribution activity

**Note:** This currently measures repositories by *absolute activity level*. 
To calculate true "underrated" repos (high activity, low recognition), we plan to integrate the GitHub API 
to adjust activity scores relative to star counts.
""")

col1, col2 = st.columns([2, 1])

with col1:
    if len(df_underrated) > 0:
        # Prepare data for pie chart
        pie_data = df_underrated.copy()
        pie_data['label'] = pie_data['repo_name'].str.replace(
            'owner/', '', regex=False
        ).str.slice(0, 20)  # Shorten names for clarity
        
        # Create pie chart
        fig_pie = px.pie(
            pie_data,
            values='weighted_activity_score',
            names='label',
            title=f"Top 10 Underrated Repos (by Activity Score)",
            hover_data={
                'repo_name': True,
                'weighted_activity_score': ':.0f',
                'forks_7d': True,
                'issues_7d': True,
                'pulls_7d': True,
                'weighted_activity_score': False  # Don't repeat in hover
            }
        )
        
        fig_pie.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                         "Activity Score: %{customdata[1]:.0f}<br>" +
                         "Forks: %{customdata[2]}<br>" +
                         "Issues: %{customdata[3]}<br>" +
                         "Pulls: %{customdata[4]}<br>" +
                         "<extra></extra>"
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("No underrated repos data available for selected date range")

with col2:
    st.subheader("📊 Breakdown")
    if len(df_underrated) > 0:
        for idx, row in df_underrated.head(5).iterrows():
            st.metric(
                label=row['repo_name'][:30],
                value=f"{row['weighted_activity_score']:.0f}",
                delta=f"Rank #{row['underrated_rank']}",
                help="Weighted Activity Scores"
            )

# Detailed table
with st.expander("📋 Detailed Metrics", expanded=False):
    if len(df_underrated) > 0:
        display_cols = [
            'repo_name', 'underrated_rank', 'weighted_activity_score',
            'forks_7d', 'issues_7d', 'pulls_7d', 'pushes_7d'
        ]
        st.dataframe(
            df_underrated[display_cols],
            use_container_width=True,
            hide_index=True
        )

# ============================================================================
# Tile 2: Human vs Bot Activity (Time Series)
# ============================================================================

st.header("🤖 Tile 2: Contributor Automation")
st.markdown("""
**Activity Breakdown:**
- **Human**: Real developers and contributors
- **Bot**: Automated users (Dependabot, GitHub Actions, Renovate, etc.)
- Shows total events per day by contributor type
""")

if len(df_activity) > 0:
    # Pivot data for easier charting
    activity_pivot = df_activity.pivot_table(
        index='activity_date',
        columns='contributor_type',
        values='total_events',
        aggfunc='sum'
    ).fillna(0)
    
    # Create time series line chart
    fig_timeseries = go.Figure()
    
    # Human activity line
    if 'human' in activity_pivot.columns:
        fig_timeseries.add_trace(go.Scatter(
            x=activity_pivot.index,
            y=activity_pivot['human'],
            mode='lines+markers',
            name='Human Activity',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=6),
            hovertemplate='<b>Human Activity</b><br>Date: %{x}<br>Events: %{y:,.0f}<extra></extra>'
        ))
    
    # Bot activity line
    if 'bot' in activity_pivot.columns:
        fig_timeseries.add_trace(go.Scatter(
            x=activity_pivot.index,
            y=activity_pivot['bot'],
            mode='lines+markers',
            name='Bot Activity',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=6),
            hovertemplate='<b>Bot Activity</b><br>Date: %{x}<br>Events: %{y:,.0f}<extra></extra>'
        ))
    
    fig_timeseries.update_layout(
        title=f'Human vs Bot Activity (Last {days_back_activity} Days)',
        xaxis_title='Date',
        yaxis_title='Total Events',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        legend=dict(x=0.01, y=0.99)
    )
    
    st.plotly_chart(fig_timeseries, use_container_width=True)
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    human_data = df_activity[df_activity['contributor_type'] == 'human']
    bot_data = df_activity[df_activity['contributor_type'] == 'bot']
    
    with col1:
        human_total = human_data['total_events'].sum() if len(human_data) > 0 else 0
        st.metric("Total Human Events", f"{human_total:,.0f}")
    
    with col2:
        bot_total = bot_data['total_events'].sum() if len(bot_data) > 0 else 0
        st.metric("Total Bot Events", f"{bot_total:,.0f}")
    
    with col3:
        total = human_total + bot_total
        human_pct = (human_total / total * 100) if total > 0 else 0
        st.metric("Human %", f"{human_pct:.1f}%")
    
    with col4:
        bot_pct = (bot_total / total * 100) if total > 0 else 0
        st.metric("Bot %", f"{bot_pct:.1f}%")
    
    # Activity breakdown table
    with st.expander("📋 Daily Activity Detail", expanded=False):
        detail_data = df_activity.pivot_table(
            index='activity_date',
            columns='contributor_type',
            values=['total_events', 'unique_contributors'],
            aggfunc='sum'
        ).fillna(0)
        st.dataframe(detail_data, use_container_width=True)

else:
    st.warning("No human vs bot activity data available")

# ============================================================================
# Footer
# ============================================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.caption(f"📊 Data Source: GitHub Archive")

with col2:
    st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

with col3:
    st.caption(f"🎯 Project: GitPulse")

# ============================================================================
# Sidebar - Data Quality Info
# ============================================================================

st.sidebar.divider()
st.sidebar.header("ℹ️ Data Quality")

try:
    # Query to get latest data dates
    latest_query = f"""
    SELECT
        MAX(metric_date) as latest_underrated_date,
        (SELECT MAX(activity_date) FROM `{project_id}.{dataset_id}_analytics.human_vs_bot_activity`) as latest_activity_date
    FROM `{project_id}.{dataset_id}_analytics.underrated_repos`
    """
    latest_dates = bq_client.query(latest_query).to_dataframe()
    
    if len(latest_dates) > 0:
        row = latest_dates.iloc[0]
        st.sidebar.info(
            f"**Latest Data**\n\n"
            f"Underrated Repos: {row['latest_underrated_date']}\n\n"
            f"Activity: {row['latest_activity_date']}"
        )
except Exception as e:
    st.sidebar.warning(f"Could not fetch data dates: {e}")

st.sidebar.divider()
st.sidebar.caption(
    "💡 **Tip**: Refresh the page to reload data from BigQuery"
)

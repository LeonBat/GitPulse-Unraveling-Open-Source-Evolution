# GitPulse: Quick Start Guide

Get GitPulse running in under 10 minutes!

---

## What is GitPulse?

GitPulse analyzes GitHub activity to show:
1. **Most Active Repositories** - Which open-source projects are growing fastest
2. **Human vs Bot Activity** - How much of GitHub is automated

---

## 5-Minute Setup

### Step 1: Prerequisites


**Check Python Version**
```bash
python3 --version  # Should be 3.12 or higher
```

**Clone Repository**
```bash
git clone https://github.com/LeonBat/GitPulse-Unraveling-Open-Source-Evolution
cd GitPulse-Unraveling-Open-Source-Evolution
```

### Step 2: Get Google Cloud Credentials

1. Create a [Google Cloud Account](https://cloud.google.com)
2. Create a new project
3. Enable **BigQuery API** and **Cloud Storage API**
4. Go to **IAM & Admin > Service Accounts**
5. Create a service account and download JSON key
6. Save as `~/.config/gcp_credentials.json`

In case you need help you can use the extensive [google docs](https://docs.cloud.google.com/docs?hl=de) or [YouTube](https://www.youtube.com/@googlecloudtech)



### Step 3: Create `.env` File

Create `~/.env`:

```bash
GCP_PROJECT_ID=your-google-cloud-project-id
GCS_BUCKET_NAME=your-project-id-github-pulse
BQ_DATASET_NAME=github_archive
GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcp_credentials.json
```

### Step 4: Install Dependencies

**Option A: Fast (Recommended)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
source .venv/bin/activate
```

**Option B: Traditional pip**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Step 5: Configure dbt

Edit `dbt/profiles.yml` and update:
```yaml
project: YOUR_GCP_PROJECT_ID
keyfile: ~/.config/gcp_credentials.json
```

---

## Run the Pipeline

### Basic Run (Last 7 Days)

```bash
./run_pipeline.sh
```

This will:
1. Download 7 days of GitHub data
2. Transform it
3. Load results into your database

Takes ~5-10 minutes ☕

### View Results in Dashboard

```bash
./run_pipeline.sh -d
```

Opens interactive dashboard at `http://localhost:8501`

### Custom Date Range

```bash
./run_pipeline.sh -s 20240101 -e 20240131
```

---

## What Just Happened?

### Stage 1: Data Ingestion
Downloaded ~50 million GitHub events from the GitHub Archive (public BigQuery dataset)

### Stage 2: Transformation
Cleaned data and calculated:
- **Activity Score** = Forks×5 + Issues×3 + Pulls×4 + Pushes×1
- **Human vs Bot** = Event classification by contributor type

### Stage 3: Dashboard
Visual analysis of:
- Top 10 most active repositories (pie chart)
- Human vs bot trends (line chart)

---

## Next Steps

### Explore the Dashboard

- **Pie Chart**: Click slices to see repository details
- **Time Series**: Hover for exact values
- **Metrics**: View breakdown statistics
- **Detailed Data**: Expand tables for raw numbers

### Customize Analysis

Change the date range in the sidebar to analyze different periods

### View Pipeline Logs

```bash
tail -f logs/gitpulse_*.log
```

---

## Troubleshooting

### "Permission denied" on run_pipeline.sh
```bash
chmod +x run_pipeline.sh
```

### "Module not found" error
```bash
source .venv/bin/activate
pip install -e .
```

### "Authentication failed"
```bash
# Test your credentials
gcloud auth application-default login
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcp_credentials.json
```

### "Port 8501 already in use"
```bash
# Kill existing process
lsof -i :8501 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

---

## Common Questions

**Q: How much does this cost?**
A: ~$5-10/month on Google Cloud (BigQuery queries)

**Q: Can I use a different cloud provider?**
A: Yes! Terraform supports GCP, AWS, Azure. Modify `terraform/main.tf`

**Q: How often should I run the pipeline?**
A: Daily recommended, but run anytime you want fresh data

**Q: Can I modify the analysis?**
A: Yes! Edit SQL files in `dbt/models/` to customize calculations

---

## Architecture in 30 Seconds

```
GitHub Archive Data
        ↓
  Data Ingestion (Python)
        ↓
   Transformations (dbt)
        ↓
  BigQuery Tables
        ↓
  Streamlit Dashboard
```

---

## Project Structure

```
.
├── ingestion/          ← Download data from GitHub Archive
├── dbt/                ← Transform data with SQL
├── dashboard/          ← Interactive Streamlit web app
├── bigquery/           ← Schema definitions
├── terraform/          ← Cloud infrastructure
├── keys/               ← GCP credentials (DO NOT COMMIT)
├── logs/               ← Pipeline execution logs
├── run_pipeline.sh     ← Main orchestration script
├── pyproject.toml      ← Python dependencies
├── docs.md             ← Detailed documentation
└── quickstart.md       ← This file!
```

---

## Learn More

- **Full Documentation**: See `docs.md`
- **GitHub Archive**: https://www.gharchive.org/
- **dbt Tutorials**: https://docs.getdbt.com/docs/introduction
- **Streamlit Guides**: https://docs.streamlit.io/

---

## Need Help?

1. Check `logs/gitpulse_*.log` for error messages
2. Review full documentation in `docs.md`
3. Open a GitHub issue with error details

---

**Ready to explore open-source trends? Run `./run_pipeline.sh` now!** 🚀

# GitHub Archive Ingestion Module

Tnis README File shows how to set up the ingestion functionality I used in the final project.
Basically the module ingests GitHub Archive data from the BigQuery public dataset into the GCS bucket and BigQuery dataset.


## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export GCS_BUCKET_NAME="your-bucket-name"
export BQ_DATASET_NAME="github_archive"  # Optional, defaults to this
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 3. Run Locally (for testing)
```bash
python ingest.py
```

The test run This will ingest the last 7 days of GitHub Archive data. To customize you can simply
change the environment variables START_DATE and END_DATE which are set in the script:
```bash
export START_DATE="20240101"
export END_DATE="20240131"
export DAYS_BACK="30"
python ingest.py
```

## How It Works

### Data Flow
```
GitHub Archive Public BigQuery Dataset (githubarchive.day.events_*)
                              ↓
                    [Query & Filter]
                              ↓
                     [to_gcs=True?]
                       ↙        ↘
                    GCS        BigQuery
                 (Parquet)     (raw_events)
```

### Key Features
- **Cost-controlled**: Queries only public events, configurable date ranges
- **Partitioned storage**: Data organized by date in GCS (e.g., `raw/github_events/date=2024-01-31/`)
- **Efficient format**: Stores as Parquet with Snappy compression
- **Dual destination**: Data goes to both GCS (for audit trail) and BigQuery (for querying)
- **Error handling**: Comprehensive logging and error messages
- **Production-ready**: Configurable, idempotent, memory-efficient

## Script Parameters

### Query Customization
The `GitHubArchiveIngester.query_github_archive()` method filters by:
- **Date range**: Customizable start/end dates (YYYYMMDD format)
- **Public events only**: `WHERE public = TRUE`

Modify the query in `ingest.py` to add more filters:
```python
# Example: Only include specific event types
AND type IN ('PushEvent', 'PullRequestEvent', 'CreateEvent')
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | Required | Your GCP project ID |
| `GCS_BUCKET_NAME` | Required | Your GCS bucket name |
| `BQ_DATASET_NAME` | `github_archive` | BigQuery dataset name |
| `START_DATE` | 7 days ago | Start date (YYYYMMDD) |
| `END_DATE` | Today | End date (YYYYMMDD) |
| `DAYS_BACK` | `7` | Days to ingest (overrides START_DATE) |
| `GOOGLE_APPLICATION_CREDENTIALS` | ADC | Path to service account key |

## Kestra Integration

### Deploy to Kestra
1. Copy `kestra-workflow.yaml` to your Kestra instance
2. Set secrets in Kestra:
   - `GCP_PROJECT_ID`
   - `GCS_BUCKET_NAME`
   - Ensure service account has appropriate IAM roles

3. The workflow runs daily at 2 AM UTC, ingesting yesterday's data

### Manual Trigger
```bash
kestra namespace flows execute gitpulse github_archive_ingestion \
  -f '{"startDate": "20240101", "endDate": "20240131"}'
```

## GCS Storage Structure

After running, your bucket will have:
```
gs://your-bucket/
├── raw/github_events/
│   ├── date=2024-01-30/
│   │   └── events_20240130.parquet
│   ├── date=2024-01-31/
│   │   └── events_20240131.parquet
│   └── ...
```

This format follows Hive partitioning and is automatically recognized by BigQuery for external tables.

## BigQuery Access

Query your ingested data directly:
```sql
SELECT * FROM `your-project.github_archive.raw_events`
WHERE DATE(created_at) >= '2024-01-30'
LIMIT 10;
```

## Cost Estimation

### BigQuery Costs
- Public dataset query: ~$5-7 per TB scanned
- Typical GitHub Archive day: 50-100 GB → ~$0.30-0.50 per day
- Monthly (30 days): ~$10-15

### GCS Costs
- Storage: ~$0.02/GB/month (STANDARD)
- After 90 days: ~$0.004/GB/month (NEARLINE, via Terraform lifecycle rule)
- 1 month of data (1.5-3 TB): ~$2-5/month

### Total Estimated Monthly Cost
- **POC (1 month)**: ~$15-25
- **Full year**: ~$180-300

## Troubleshooting

### "Invalid project ID" error
Ensure `GCP_PROJECT_ID` environment variable is set correctly

### "Permission denied" error
Check service account has these IAM roles:
- `roles/bigquery.user`
- `roles/storage.objectCreator`

### Query running slow
- Reduce date range
- Add more filters to query (e.g., event type)
- Consider using monthly dataset instead: `githubarchive.month.events_*`

### Out of memory error
- Reduce `DAYS_BACK` to 1-2 days at a time
- The script processes all data in a single DataFrame; for very large ranges, implement chunking

## Next Steps

1. **Local testing**: Run with `DAYS_BACK=1` to test
2. **Deploy to Kestra**: Set up daily orchestration
3. **Build dbt models**: Transform raw events into marts for your dashboard
4. **Create BigQuery external table**: Reference GCS Parquet files directly

"""
GitHub Archive Data Ingestion Script
Queries GitHub Archive public BigQuery dataset and loads into GCS bucket.
"""

# Libaries
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from google.cloud import bigquery, storage
from dotenv import load_dotenv


# ── Configuration ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# load environment variables from .env_ingestion file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env_ingestion"))


class GitHubArchiveIngester:
    """
    This class ingests the data from Github Archive / public BigQuery dataset and 
    transfers the data to GCS.
    
    Args:
        project_id: GCP project ID
        bucket_name: GCS bucket name for storing data
        dataset_id: BigQuery dataset ID in your project (destination)
        credentials_path: Path to service account JSON (optional, uses ADC if not provided)
    """
    
    def __init__(
        self,
        project_id: str,
        bucket_name: str,
        dataset_id: str = "github_archive",
        credentials_path: Optional[str] = None,
    ):
        ### Attributes
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.dataset_id = dataset_id
        
        # sets the credential path as environment variable if provided
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path 
        
        # Initialize BigQuery and Storage clients
        self.bq_client = bigquery.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        
        logger.info(f"Initialized ingester for project: {project_id}")
    
    def query_github_archive(
        self,
        date: str,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Query GitHub Archive public dataset for a single day.
        
        Args:
            date: Date (YYYYMMDD format, e.g., '20240101')
            limit: Optional limit on rows (useful for testing)
            
        Returns:
            DataFrame with GitHub events for that day
        """
        logger.info(f"Querying GitHub Archive for date: {date}")
        
        # Query from GitHub Archive PUBLIC dataset for single day
        query = f"""
        SELECT
            id,
            type,
            actor.login as actor_login,
            actor.id as actor_id,
            repo.name as repo_name,
            repo.id as repo_id,
            created_at
        FROM
            `githubarchive.day.{date}`
        WHERE
            type IN ('PushEvent', 'PullRequestEvent', 'IssuesEvent', 'CreateEvent', 'ForkEvent')
        """
        
        if limit:
            query += f"\nLIMIT {limit}"
        
        logger.info(f"Executing query for date: {date}")
        logger.debug(f"\nQuery:\n{query}")
        
        try:
            logger.info("Submitting query to BigQuery...")
            job = self.bq_client.query(query)
            logger.info(f"Query job ID: {job.job_id}")
            logger.info("Waiting for query to complete...")
            result = job.result()  # Wait for query to finish
            total_rows = result.total_rows
            logger.info(f"Query completed. Total rows in result: {total_rows:,}")
            logger.info(f"Converting {total_rows:,} rows to dataframe...")
            df = result.to_dataframe()
            logger.info(f"Retrieved {len(df):,} rows from GitHub Archive for {date}")
            if df.empty:
                logger.warning(f"Query returned empty result set for {date}")
            else:
                logger.debug(f"Data sample:\n{df.head()}")
            return df
        except Exception as e:
            logger.error(f"BigQuery query failed for {date}: {e}")
            raise
    
    def upload_to_gcs(
        self,
        df: pd.DataFrame,
        date: str,
        folder: str = "raw/github_events", 
    ) -> str:
        """
        Uploads DataFrame to GCS as Parquet file.
        
        Args:
            df: DataFrame to upload
            date: Date (YYYYMMDD) for partitioning
            folder: GCS folder path (without bucket name)
            
        Returns:
            GCS blob name (path)
        """
        bucket = self.storage_client.bucket(self.bucket_name)
        
        # Partition by date: raw/github_events/date=2024-01-01/events.parquet
        blob_name = f"{folder}/date={date[:4]}-{date[4:6]}-{date[6:8]}/events_{date}.parquet"
        blob = bucket.blob(blob_name)
        
        try:
            # Convert to Parquet and upload to GCS
            logger.info(f"Starting parquet conversion for {len(df):,} rows...")
            parquet_bytes = df.to_parquet(index=False, compression="snappy")
            file_size_mb = len(parquet_bytes) / (1024 * 1024)
            logger.info(f"Parquet conversion complete ({file_size_mb:.2f} MB). Uploading to GCS...")
            blob.upload_from_string(parquet_bytes, content_type="application/parquet")
            logger.info(f"GCS upload complete.")
            
            logger.info(
                f"Uploaded {len(df):,} rows to gs://{self.bucket_name}/{blob_name} "
                f"({file_size_mb:.2f} MB)"
            )
            return blob_name
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            raise
    
    def load_to_bigquery(
        self,
        df: pd.DataFrame,
        table_id: str = "raw_events",
        write_disposition: str = "WRITE_APPEND",
    ) -> None:
        """
        Load DataFrame directly into BigQuery table.
        
        Args:
            df: DataFrame to load
            table_id: Destination table name in your dataset
            write_disposition: How to handle existing data (WRITE_APPEND, WRITE_TRUNCATE)
        """
        full_table_id = f"{self.project_id}.{self.dataset_id}.{table_id}"
        
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            autodetect=True,
        )
        
        try:
            logger.info(f"Starting BigQuery load for {len(df):,} rows to {full_table_id}...")
            job = self.bq_client.load_table_from_dataframe(
                df, full_table_id, job_config=job_config
            )
            logger.info(f"Load job submitted with ID: {job.job_id}. Waiting for completion...")
            job.result()
            logger.info(f"Loaded {len(df):,} rows to {full_table_id}")
        except Exception as e:
            logger.error(f"BigQuery load failed: {e}")
            raise
    
    def run_ingestion(
        self,
        start_date: str,
        end_date: str,
        to_gcs: bool = True,
        to_bigquery: bool = True,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Execute full ingestion pipeline for date range, processing one day at a time.
        
        Args:
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            to_gcs: Upload to GCS
            to_bigquery: Load to BigQuery
            limit: Optional row limit per day for testing
            
        Returns:
            Dictionary with aggregated ingestion stats
        """
        # Build date range
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        date_range = pd.date_range(start=start, end=end, freq="D")
        table_dates = [d.strftime("%Y%m%d") for d in date_range]
        
        stats = {
            "start_date": start_date,
            "end_date": end_date,
            "rows_ingested": 0,
            "days_processed": 0,
            "days_failed": 0,
            "gcs_locations": [],
            "status": "success",
        }
        
        logger.info(f"Processing {len(table_dates)} days from {start_date} to {end_date}")
        
        try:
            for date in table_dates:
                try:
                    logger.info(f"\n{'='*70}")
                    logger.info(f"Processing day: {date}")
                    logger.info(f"{'='*70}")
                    
                    # Step 1: Query GitHub Archive for this day
                    df = self.query_github_archive(date, limit=limit)
                    
                    if df.empty:
                        logger.warning(f"No data for {date}")
                        continue
                    
                    day_rows = len(df)
                    stats["rows_ingested"] += day_rows
                    
                    # Step 2: Upload to GCS (partitioned by date)
                    if to_gcs:
                        blob_name = self.upload_to_gcs(df, date)
                        stats["gcs_locations"].append(f"gs://{self.bucket_name}/{blob_name}")
                    
                    # Step 3: Load to BigQuery
                    if to_bigquery:
                        self.load_to_bigquery(df, write_disposition="WRITE_APPEND")
                    
                    stats["days_processed"] += 1
                    logger.info(f"Completed {date}: {day_rows:,} rows")
                    
                except Exception as e:
                    logger.error(f"Failed to process {date}: {e}")
                    stats["days_failed"] += 1
                    continue
            
            logger.info(f"\n{'='*70}")
            logger.info(f"Ingestion pipeline completed: {stats}")
            logger.info(f"{'='*70}")
            return stats
            
        except Exception as e:
            logger.error(f"Ingestion pipeline failed: {e}")
            stats["status"] = "failed"
            stats["error"] = str(e)
            raise


# ── Main execution ──────────────────────────────────────────────────

def main():
    """
    Main ingestion entry point.
    Configure these from environment variables or pass as arguments.
    """
    # Configuration
    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")
    bucket_name = os.getenv("GCS_BUCKET_NAME", "your-bucket-name")
    dataset_id = os.getenv("BQ_DATASET_NAME", "github_archive")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    #Date range (defaults to last 1 day)
    end_date = os.getenv("END_DATE", datetime.now().strftime("%Y%m%d"))
    days_back = int(os.getenv("DAYS_BACK", "1")) # Default to 1 day back for testing, adjust as needed
    start_date = os.getenv(
       "START_DATE",
       (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    )
    limit = os.getenv("LIMIT")
    if limit:
        limit = int(limit)
    
    
    logger.info("=" * 70)
    logger.info("GitHub Archive Ingestion Pipeline")
    logger.info("=" * 70)
    logger.info(f"Project ID: {project_id}")
    logger.info(f"Bucket: {bucket_name}")
    logger.info(f"Dataset: {dataset_id}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info("=" * 70)
    
    # Initialize ingester
    ingester = GitHubArchiveIngester(
        project_id=project_id,
        bucket_name=bucket_name,
        dataset_id=dataset_id,
        credentials_path=credentials_path,
    )
    
    # Run ingestion
    stats = ingester.run_ingestion(
        start_date=start_date,
        end_date=end_date,
        to_gcs=True,
        to_bigquery=True,
        limit=limit,
    )
    
    logger.info("=" * 70)
    logger.info(f"Ingestion Result: {stats['status']}")
    logger.info(f"Days processed: {stats['days_processed']}/{len([d.strftime('%Y%m%d') for d in pd.date_range(start=datetime.strptime(start_date, '%Y%m%d'), end=datetime.strptime(end_date, '%Y%m%d'), freq='D')])}")
    logger.info(f"Days failed: {stats['days_failed']}")
    logger.info(f"Total rows ingested: {stats['rows_ingested']:,}")
    if stats["gcs_locations"]:
        logger.info(f"GCS locations: {len(stats['gcs_locations'])} files uploaded")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

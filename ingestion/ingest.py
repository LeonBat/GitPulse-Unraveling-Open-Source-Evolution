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

# load environment variables from .env file
load_dotenv()


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
        start_date: str,
        end_date: str,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Query GitHub Archive public dataset for date range.
        
        Args:
            start_date: Start date (YYYYMMDD format, e.g., '20240101')
            end_date: End date (YYYYMMDD format, e.g., '20240131')
            limit: Optional limit on rows (useful for testing)
            
        Returns:
            DataFrame with GitHub events
        """
        # Build dynamic table list for date range
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        date_range = pd.date_range(start=start, end=end, freq="D")
        
        table_dates = [d.strftime("%Y%m%d") for d in date_range]
        # Query from GitHub Archive PUBLIC dataset
        # Table naming: githubarchive.day.YYYYMMDD (not .events_)
        table_list = ", ".join(
            [f"`githubarchive.day.{date}`" for date in table_dates]
        )
        
        # Sends a query to BigQuery to retrieve the data for the specified date range

        # Select relevant columns for underrated repos & bot analysis
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
            {table_list}
        WHERE
            -- Filter to main event types needed for analysis
            type IN ('PushEvent', 'PullRequestEvent', 'IssuesEvent', 'CreateEvent', 'ForkEvent')
        """
        
        if limit:
            query += f"\n        LIMIT {limit}"
        
        logger.info(f"Executing query for date range: {start_date} to {end_date}")
        
        try:
            df = self.bq_client.query(query).to_dataframe()
            logger.info(f"Retrieved {len(df):,} rows from GitHub Archive")
            return df
        except Exception as e:
            logger.error(f"BigQuery query failed: {e}")
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
            parquet_bytes = df.to_parquet(index=False, compression="snappy")
            blob.upload_from_string(parquet_bytes, content_type="application/parquet")
            
            file_size_mb = len(parquet_bytes) / (1024 * 1024)
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
            job = self.bq_client.load_table_from_dataframe(
                df, full_table_id, job_config=job_config
            )
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
        Execute full ingestion pipeline.
        
        Args:
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            to_gcs: Upload to GCS
            to_bigquery: Load to BigQuery
            limit: Optional row limit for testing
            
        Returns:
            Dictionary with ingestion stats
        """
        stats = {
            "start_date": start_date,
            "end_date": end_date,
            "rows_ingested": 0,
            "gcs_location": None,
            "status": "success",
        }
        
        try:
            # Step 1: Query GitHub Archive
            df = self.query_github_archive(start_date, end_date, limit=limit)
            stats["rows_ingested"] = len(df)
            
            if df.empty:
                logger.warning("No data returned from query")
                stats["status"] = "completed_no_data"
                return stats
            
            # Step 2: Upload to GCS (partitioned by date)
            if to_gcs:
                blob_name = self.upload_to_gcs(df, start_date)
                stats["gcs_location"] = f"gs://{self.bucket_name}/{blob_name}"
            
            # Step 3: Load to BigQuery
            if to_bigquery:
                self.load_to_bigquery(df, write_disposition="WRITE_APPEND")
            
            logger.info(f"Ingestion completed: {stats}")
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
    
    # Date range (defaults to last 1 day)
    end_date = os.getenv("END_DATE", datetime.now().strftime("%Y%m%d"))
    days_back = int(os.getenv("DAYS_BACK", "1")) # Default to 1 day back for testing, adjust as needed
    start_date = os.getenv(
        "START_DATE",
        (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    )
    
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
    )
    
    logger.info("=" * 70)
    logger.info(f"Ingestion Result: {stats['status']}")
    logger.info(f"Rows processed: {stats['rows_ingested']:,}")
    if stats["gcs_location"]:
        logger.info(f"GCS location: {stats['gcs_location']}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

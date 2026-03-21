terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = var.credential_file
}

# ── GCS Data Lake bucket ─────────────────────────────────────────
resource "google_storage_bucket" "data_lake" {
  name                        = var.bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false # safety: protects raw archive files on tf destroy 

  lifecycle_rule {
    condition { age = 90 } # move raw files to Nearline after 90 days
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  versioning {
    enabled = false # raw archive files, no versioning needed
  }
}

# ── BigQuery dataset ─────────────────────────────────────────────
resource "google_bigquery_dataset" "main" {
  dataset_id    = var.bq_dataset_name
  friendly_name = "GitHub Archive"
  description   = "Raw events and dbt-transformed marts"
  location      = var.region

  delete_contents_on_destroy = false # protects marts on tf destroy
}


# Add later
# ── BigQuery external table over GCS (raw events) ────────────────
# resource "google_bigquery_table" "raw_events" {
#   dataset_id          = google_bigquery_dataset.main.dataset_id
#   table_id            = "raw_events"
#   deletion_protection = false

#   external_data_configuration {
#     source_uris   = ["gs://${var.bucket_name}/raw/*"]
#     source_format = "NEWLINE_DELIMITED_JSON"
#     autodetect    = true

#     hive_partitioning_options {
#       mode                     = "AUTO"
#       source_uri_prefix        = "gs://${var.bucket_name}/raw/"
#       require_partition_filter = false
#     }
#  }
#}


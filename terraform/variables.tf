variable "project_id" {
  description = "The ID of the project in which the bucket is created"
  type        = string
}

variable "bucket_name" {
  description = "Name of GCP bucket"
  type        = string
}


variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west6"
}


variable "bq_dataset_name" {
  description = "Name of BigQuery dataset"
  type        = string
  default     = "github_archive"
}

variable "credential_file" {
  description = "Credentials of service account" #
  default     = "./keys/my_credentials.json"
}


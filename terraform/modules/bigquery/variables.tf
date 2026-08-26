variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID for billing export"
  type        = string
  default     = "billing_export"
}

variable "location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "asia-southeast1"
}

variable "environment" {
  description = "Environment label (dev, demo, production)"
  type        = string
  default     = "dev"
}

variable "table_expiration_days" {
  description = "Default table expiration in days (0 = no expiration)"
  type        = number
  default     = 365
}

variable "reader_service_account_email" {
  description = "Service account email to grant reader access"
  type        = string
}

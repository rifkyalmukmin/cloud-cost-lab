variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "cloud-cost-lab"
}

variable "location" {
  description = "GCS bucket location"
  type        = string
  default     = "asia-southeast1"
}

variable "environment" {
  description = "Environment label"
  type        = string
  default     = "dev"
}

variable "retention_days" {
  description = "Object retention in days before auto-delete"
  type        = number
  default     = 90
}

variable "reader_service_account_email" {
  description = "Service account email to grant reader access"
  type        = string
}

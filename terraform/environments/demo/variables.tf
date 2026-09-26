variable "gcp_project_id" {
  description = "GCP project that hosts this environment. No default: the target must be explicit."
  type        = string
}

variable "gcp_region" {
  description = "Region for regional resources (data residency explicit)."
  type        = string
  default     = "asia-southeast2"
}

variable "environment" {
  description = "Environment name used in labels and resource ids."
  type        = string
  default     = "demo"
}

variable "billing_dataset_id" {
  description = "BigQuery dataset id for the billing export destination."
  type        = string
  default     = "cloud_cost_lab_billing_demo"
}

variable "report_bucket_name" {
  description = "GCS bucket name for cost reports (globally unique)."
  type        = string
  default     = "cloud-cost-lab-reports-demo"
}

variable "data_retention_days" {
  description = "Retention for billing tables and report objects (cost guard)."
  type        = number
  default     = 365
}

variable "compute_enabled" {
  description = "The platform runs locally; a VM is NOT needed. Flip deliberately."
  type        = bool
  default     = false
}

variable "compute_zone" {
  description = "Zone for the optional compute instance."
  type        = string
  default     = "asia-southeast2-a"
}

variable "labels" {
  description = "Extra labels for every resource."
  type        = map(string)
  default     = {}
}

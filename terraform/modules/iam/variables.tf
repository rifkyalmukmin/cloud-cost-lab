variable "project_id" {
  description = "GCP project the service account lives in."
  type        = string
}

variable "service_account_id" {
  description = "Service account id (part of the email)."
  type        = string
  default     = "cost-data-reader"
}

variable "display_name" {
  description = "Human-readable service account name."
  type        = string
  default     = "Cloud Cost Lab — cost data reader"
}

variable "description" {
  description = "What this identity is allowed to do."
  type        = string
  default     = "Read-only identity for the Cloud Cost Lab platform (billing export + monitoring reads)."
}

variable "project_roles" {
  description = "Project-level IAM roles granted to the service account. Keep this minimal."
  type        = list(string)
  default     = ["roles/bigquery.jobUser"]
}

variable "project_id" {
  description = "GCP project that hosts the dataset."
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset id (billing export destination)."
  type        = string
}

variable "location" {
  description = "Dataset location. Keep data residency explicit."
  type        = string
  default     = "US"
}

variable "description" {
  description = "Human-readable dataset description."
  type        = string
  default     = "Cloud Cost Lab billing export destination"
}

variable "default_table_expiration_days" {
  description = "Tables auto-expire after this many days (retention, CLAUDE.md §9/§11). 0 disables."
  type        = number
  default     = 365
}

variable "reader_members" {
  description = "IAM members granted READER on the dataset only (least privilege)."
  type        = list(string)
  default     = []
}

variable "delete_contents_on_destroy" {
  description = "Refuse dataset destroy while tables exist unless explicitly enabled."
  type        = bool
  default     = false
}

variable "labels" {
  description = "Resource labels (managed_by is added automatically)."
  type        = map(string)
  default     = {}
}

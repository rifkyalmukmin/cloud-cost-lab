variable "project_id" {
  description = "GCP project that hosts the bucket."
  type        = string
}

variable "name" {
  description = "Bucket name (globally unique; include a random suffix at the caller)."
  type        = string
}

variable "location" {
  description = "Bucket location (region keeps data residency explicit)."
  type        = string
  default     = "asia-southeast2"
}

variable "versioning_enabled" {
  description = "Keep object versions so reports can be recovered."
  type        = bool
  default     = true
}

variable "object_retention_days" {
  description = "Non-current/auto-delete age for objects (cost guard). 0 disables the lifecycle rule."
  type        = number
  default     = 365
}

variable "viewers" {
  description = "IAM members granted objectViewer on THIS bucket only."
  type        = list(string)
  default     = []
}

variable "force_destroy" {
  description = "Refuse bucket destroy while objects exist unless explicitly enabled."
  type        = bool
  default     = false
}

variable "labels" {
  description = "Resource labels (managed_by is added automatically)."
  type        = map(string)
  default     = {}
}

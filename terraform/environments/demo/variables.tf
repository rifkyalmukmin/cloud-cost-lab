variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-southeast1"
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "cloud-cost-lab"
}

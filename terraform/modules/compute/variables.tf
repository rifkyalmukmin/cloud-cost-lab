variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "cloud-cost-lab"
}

variable "zone" {
  description = "GCP zone for the instance"
  type        = string
  default     = "asia-southeast1-a"
}

variable "machine_type" {
  description = "Instance machine type (smallest practical for cost efficiency)"
  type        = string
  default     = "e2-micro"
}

variable "disk_size_gb" {
  description = "Boot disk size in GB"
  type        = number
  default     = 10
}

variable "environment" {
  description = "Environment label"
  type        = string
  default     = "dev"
}

variable "network" {
  description = "VPC network"
  type        = string
  default     = "default"
}

variable "subnetwork" {
  description = "VPC subnetwork"
  type        = string
  default     = "default"
}

variable "enable_external_ip" {
  description = "Whether to assign an external IP (false for production)"
  type        = bool
  default     = false
}

variable "service_account_email" {
  description = "Service account email for the instance"
  type        = string
}

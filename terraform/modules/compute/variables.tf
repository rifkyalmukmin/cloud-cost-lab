variable "project_id" {
  description = "GCP project hosting the instance."
  type        = string
}

variable "name" {
  description = "Instance name."
  type        = string
}

variable "zone" {
  description = "Zone for the instance (keep data residency explicit)."
  type        = string
}

variable "machine_type" {
  description = "Smallest practical machine type first (CLAUDE.md §7)."
  type        = string
  default     = "e2-micro"
}

variable "boot_image" {
  description = "Boot disk image family."
  type        = string
  default     = "debian-cloud/debian-12"
}

variable "boot_disk_size_gb" {
  description = "Boot disk size in GB."
  type        = number
  default     = 10
}

variable "enable_public_ip" {
  description = "External IP is OFF by default: private-by-default (§7 security)."
  type        = bool
  default     = false
}

variable "subnetwork" {
  description = "Subnetwork self-link. Null uses the default network."
  type        = string
  default     = null
}

variable "service_account_email" {
  description = "Service account attached to the instance. Null = no service account."
  type        = string
  default     = null
}

variable "labels" {
  description = "Resource labels (managed_by is added automatically)."
  type        = map(string)
  default     = {}
}

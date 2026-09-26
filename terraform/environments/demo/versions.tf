terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Production-hardening: uncomment to keep state in GCS (create the bucket
  # manually once; it is outside Terraform so its own state stays local).
  # backend "gcs" {
  #   bucket = "cloud-cost-lab-tfstate"
  #   prefix = "demo"
  # }
}

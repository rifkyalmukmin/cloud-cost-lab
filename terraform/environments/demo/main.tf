terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "iam" {
  source     = "../../modules/iam"
  project_id = var.project_id
  prefix     = "${var.prefix}-demo"
}

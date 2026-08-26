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
  prefix     = var.prefix
}

module "bigquery" {
  source                       = "../../modules/bigquery"
  project_id                   = var.project_id
  dataset_id                   = var.billing_dataset_id
  location                     = var.region
  environment                  = "dev"
  table_expiration_days        = 365
  reader_service_account_email = module.iam.cost_reader_email
}

module "storage" {
  source                       = "../../modules/storage"
  project_id                   = var.project_id
  prefix                       = var.prefix
  location                     = var.region
  environment                  = "dev"
  retention_days               = 90
  reader_service_account_email = module.iam.cost_reader_email
}

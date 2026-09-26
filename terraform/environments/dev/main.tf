provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

locals {
  labels = merge(var.labels, {
    environment = var.environment
    application = "cloud-cost-lab"
  })
}

# Read-only identity for the platform (billing export + monitoring reads).
module "iam" {
  source = "../../modules/iam"

  project_id         = var.gcp_project_id
  service_account_id = "cost-data-reader-${var.environment}"
}

# Billing export destination. Table expiration enforces retention (§9/§11);
# readers are granted on the dataset only.
module "bigquery" {
  source = "../../modules/bigquery"

  project_id                    = var.gcp_project_id
  dataset_id                    = var.billing_dataset_id
  location                      = "US" # billing export supports US/EU multi-region
  default_table_expiration_days = var.data_retention_days
  reader_members                = [module.iam.service_account_email]

  labels = local.labels
}

# Cost report archive. Private, PAP enforced, lifecycle-limited.
module "storage" {
  source = "../../modules/storage"

  project_id            = var.gcp_project_id
  name                  = var.report_bucket_name
  location              = var.gcp_region
  object_retention_days = var.data_retention_days
  viewers               = [module.iam.service_account_email]

  labels = local.labels
}

# The platform runs on the developer machine — a VM is deliberately NOT
# provisioned unless compute_enabled is flipped to true by a human decision.
module "compute" {
  source = "../../modules/compute"
  count  = var.compute_enabled ? 1 : 0

  project_id            = var.gcp_project_id
  name                  = "cloud-cost-lab-${var.environment}"
  zone                  = var.compute_zone
  service_account_email = module.iam.service_account_email

  labels = local.labels
}

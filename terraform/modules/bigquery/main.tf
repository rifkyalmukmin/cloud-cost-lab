locals {
  labels = merge(var.labels, { managed_by = "terraform" })
}

resource "google_bigquery_dataset" "billing_export" {
  project                     = var.project_id
  dataset_id                  = var.dataset_id
  friendly_name               = var.dataset_id
  description                 = var.description
  location                    = var.location
  default_table_expiration_ms = var.default_table_expiration_days > 0 ? var.default_table_expiration_days * 86400000 : null

  # Least privilege: readers are granted on THIS dataset only, never at
  # project level from this module.
  dynamic "access" {
    for_each = var.reader_members
    content {
      role          = "READER"
      user_by_email = access.value
    }
  }

  # Safety: destroying the dataset requires explicitly enabling this flag,
  # so an accidental apply/destroy cannot silently drop billing history.
  delete_contents_on_destroy = var.delete_contents_on_destroy

  labels = local.labels
}

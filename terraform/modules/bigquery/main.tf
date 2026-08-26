resource "google_bigquery_dataset" "billing_export" {
  dataset_id    = var.dataset_id
  friendly_name = "Cloud Cost Lab Billing Export"
  description   = "Dataset for GCP Billing Export data"
  project       = var.project_id
  location      = var.location

  default_table_expiration_ms = var.table_expiration_days * 24 * 60 * 60 * 1000

  labels = {
    managed_by  = "terraform"
    application = "cloud-cost-lab"
    environment = var.environment
  }
}

resource "google_bigquery_dataset_iam_member" "reader" {
  dataset_id = google_bigquery_dataset.billing_export.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${var.reader_service_account_email}"
}

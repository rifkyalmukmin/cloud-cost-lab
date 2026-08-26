resource "google_service_account" "cost_reader" {
  account_id   = "${var.prefix}-cost-reader"
  display_name = "Cloud Cost Lab - Cost Data Reader"
  description  = "Read-only access to billing export data in BigQuery"
  project      = var.project_id
}

resource "google_service_account" "monitoring_reader" {
  account_id   = "${var.prefix}-mon-reader"
  display_name = "Cloud Cost Lab - Monitoring Reader"
  description  = "Read-only access to Cloud Monitoring metrics"
  project      = var.project_id
}

resource "google_project_iam_member" "cost_reader_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.cost_reader.email}"
}

resource "google_project_iam_member" "cost_reader_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.cost_reader.email}"
}

resource "google_project_iam_member" "monitoring_reader_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.monitoring_reader.email}"
}

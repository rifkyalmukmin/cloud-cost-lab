output "dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.billing_export.dataset_id
}

output "dataset_self_link" {
  description = "Self-link of the BigQuery dataset"
  value       = google_bigquery_dataset.billing_export.self_link
}

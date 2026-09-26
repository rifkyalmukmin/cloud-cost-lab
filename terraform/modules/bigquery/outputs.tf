output "dataset_id" {
  description = "The dataset id."
  value       = google_bigquery_dataset.billing_export.dataset_id
}

output "self_link" {
  description = "The dataset self link."
  value       = google_bigquery_dataset.billing_export.self_link
}

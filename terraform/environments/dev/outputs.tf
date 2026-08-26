output "cost_reader_email" {
  description = "Cost reader service account email"
  value       = module.iam.cost_reader_email
}

output "monitoring_reader_email" {
  description = "Monitoring reader service account email"
  value       = module.iam.monitoring_reader_email
}

output "bigquery_dataset_id" {
  description = "BigQuery billing dataset ID"
  value       = module.bigquery.dataset_id
}

output "reports_bucket" {
  description = "Reports storage bucket name"
  value       = module.storage.bucket_name
}

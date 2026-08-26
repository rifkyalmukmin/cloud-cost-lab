output "cost_reader_email" {
  description = "Email of the cost data reader service account"
  value       = google_service_account.cost_reader.email
}

output "cost_reader_id" {
  description = "ID of the cost data reader service account"
  value       = google_service_account.cost_reader.id
}

output "monitoring_reader_email" {
  description = "Email of the monitoring reader service account"
  value       = google_service_account.monitoring_reader.email
}

output "monitoring_reader_id" {
  description = "ID of the monitoring reader service account"
  value       = google_service_account.monitoring_reader.id
}

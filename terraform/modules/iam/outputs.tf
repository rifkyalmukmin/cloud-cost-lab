output "service_account_email" {
  description = "Email of the read-only service account."
  value       = google_service_account.reader.email
}

output "service_account_id" {
  description = "Numeric id of the service account."
  value       = google_service_account.reader.unique_id
}

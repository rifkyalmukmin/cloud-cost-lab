output "bucket_name" {
  description = "Name of the reports bucket"
  value       = google_storage_bucket.reports.name
}

output "bucket_url" {
  description = "URL of the reports bucket"
  value       = google_storage_bucket.reports.url
}

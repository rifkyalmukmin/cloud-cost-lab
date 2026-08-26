output "cost_reader_email" {
  description = "Cost reader service account email"
  value       = module.iam.cost_reader_email
}

output "monitoring_reader_email" {
  description = "Monitoring reader service account email"
  value       = module.iam.monitoring_reader_email
}

output "service_account_email" {
  description = "Read-only platform identity (attach via WIF or ADC impersonation)."
  value       = module.iam.service_account_email
}

output "billing_dataset_id" {
  description = "Configure as GCP_BILLING_DATASET in the platform .env."
  value       = module.bigquery.dataset_id
}

output "report_bucket_name" {
  description = "Bucket that receives generated cost reports."
  value       = module.storage.bucket_name
}

output "compute_instance" {
  description = "Present only when compute_enabled=true."
  value       = var.compute_enabled ? module.compute[0].instance_name : null
}

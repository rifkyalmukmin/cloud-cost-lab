output "instance_name" {
  description = "The instance name."
  value       = google_compute_instance.this.name
}

output "self_link" {
  description = "The instance self link."
  value       = google_compute_instance.this.self_link
}

output "internal_ip" {
  description = "Internal IP (no public IP is created by default)."
  value       = google_compute_instance.this.network_interface[0].network_ip
}

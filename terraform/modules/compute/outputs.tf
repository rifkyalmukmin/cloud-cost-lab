output "instance_name" {
  description = "Name of the compute instance"
  value       = google_compute_instance.api.name
}

output "instance_id" {
  description = "ID of the compute instance"
  value       = google_compute_instance.api.instance_id
}

output "internal_ip" {
  description = "Internal IP of the instance"
  value       = google_compute_instance.api.network_interface[0].network_ip
}

locals {
  labels = merge(var.labels, { managed_by = "terraform" })
}

resource "google_compute_instance" "this" {
  project      = var.project_id
  name         = var.name
  zone         = var.zone
  machine_type = var.machine_type

  boot_disk {
    initialize_params {
      image = var.boot_image
      size  = var.boot_disk_size_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    network    = "default"
    subnetwork = var.subnetwork

    # Private by default: no access_config block means NO external IP.
    dynamic "access_config" {
      for_each = var.enable_public_ip ? [1] : []
      content {
        nat_ip = null
      }
    }
  }

  dynamic "service_account" {
    for_each = var.service_account_email != null ? [1] : []
    content {
      email = var.service_account_email
      # Read-only scope; broader access comes from IAM, not scopes.
      scopes = ["https://www.googleapis.com/auth/cloud-platform.read-only"]
    }
  }

  # Hardening: legacy metadata server off; shielded bits where free.
  metadata = {
    disable-legacy-endpoints = "true"
    enable-oslogin           = "TRUE"
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  labels = local.labels
}

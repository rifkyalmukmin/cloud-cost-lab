resource "google_compute_instance" "api" {
  name         = "${var.prefix}-api-${var.environment}"
  machine_type = var.machine_type
  zone         = var.zone
  project      = var.project_id

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
      size  = var.disk_size_gb
      type  = "pd-standard"
    }
  }

  network_interface {
    network    = var.network
    subnetwork = var.subnetwork

    dynamic "access_config" {
      for_each = var.enable_external_ip ? [1] : []
      content {}
    }
  }

  service_account {
    email  = var.service_account_email
    scopes = ["cloud-platform"]
  }

  scheduling {
    automatic_restart   = var.environment == "production"
    on_host_maintenance = "MIGRATE"
    preemptible         = var.environment != "production"
  }

  labels = {
    managed_by  = "terraform"
    application = "cloud-cost-lab"
    environment = var.environment
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  tags = ["cloud-cost-lab-api", var.environment]
}

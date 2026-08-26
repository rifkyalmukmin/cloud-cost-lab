resource "google_storage_bucket" "reports" {
  name     = "${var.project_id}-${var.prefix}-reports"
  project  = var.project_id
  location = var.location

  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  lifecycle_rule {
    condition {
      age = var.retention_days
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = false
  }

  labels = {
    managed_by  = "terraform"
    application = "cloud-cost-lab"
    environment = var.environment
  }
}

resource "google_storage_bucket_iam_member" "reader" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.reader_service_account_email}"
}

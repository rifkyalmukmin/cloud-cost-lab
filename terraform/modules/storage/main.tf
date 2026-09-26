locals {
  labels = merge(var.labels, { managed_by = "terraform" })
}

resource "google_storage_bucket" "reports" {
  project  = var.project_id
  name     = var.name
  location = var.location

  # Security defaults: no legacy ACLs, public access impossible.
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = var.versioning_enabled
  }

  # Cost guard: objects older than the retention window are deleted.
  dynamic "lifecycle_rule" {
    for_each = var.object_retention_days > 0 ? [1] : []
    content {
      condition {
        age = var.object_retention_days
      }
      action {
        type = "Delete"
      }
    }
  }

  dynamic "logging" {
    for_each = []
    content {}
  }

  # Safety: destroying requires objects to be gone (or explicit opt-in).
  force_destroy = var.force_destroy

  labels = local.labels
}

resource "google_storage_bucket_iam_member" "viewers" {
  for_each = toset(var.viewers)
  bucket   = google_storage_bucket.reports.name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${each.value}"
}

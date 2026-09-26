resource "google_service_account" "reader" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = var.display_name
  description  = var.description
}

# Project-level roles stay minimal; data-level grants (dataset/bucket readers)
# live in the respective modules. NEVER create a service account key here —
# authentication is ADC locally and Workload Identity Federation in
# deployment (CLAUDE.md §36).
resource "google_project_iam_member" "roles" {
  for_each = toset(var.project_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.reader.email}"
}

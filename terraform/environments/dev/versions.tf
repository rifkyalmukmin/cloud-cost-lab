terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Remote state in GCS. GCS supports native state locking (a lock object is
  # created with an "object must not exist" precondition), so no extra lock
  # table or service is needed.
  #
  # Partial configuration: the bucket name is NOT hardcoded. Supply it at init
  # time from a git-ignored file (see backend.hcl.example and
  # terraform/README.md for bootstrap, IAM and migration steps):
  #   terraform init -backend-config=backend.hcl
  # CI and offline validation use `terraform init -backend=false`.
  backend "gcs" {}
}

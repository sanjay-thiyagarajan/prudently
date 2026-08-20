# Terraform owns the service shell (identity, IAM, env plumbing); the container image is
# updated out-of-band via `gcloud run deploy --source` (infra/scripts/deploy.sh) for fast
# hackathon iteration — Terraform intentionally ignores image drift after initial create.
resource "google_cloud_run_v2_service" "api" {
  name     = "prudently-api"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = var.coordinator_agent_sa_email

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "MEMORY_BANK_LOCATION"
        value = var.memory_bank_location
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# Public invoker — this is a demo dashboard/API for judging, not a production system with
# real patient data behind it. Revisit if that framing ever changes.
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

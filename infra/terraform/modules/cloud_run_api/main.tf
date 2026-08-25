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
      # Every other backend toggle (EMAIL_BACKEND, ARMOR_BACKEND, OBSERVABILITY_BACKEND) is
      # left unset here and falls back to config.py's own default — this one is the
      # exception, set explicitly, because its default is "local" (off) on purpose (see
      # services/platform/vendor_inbox.py's docstring: a brand-new mailbox integration that
      # hadn't earned "on by default" yet). Setting it here, not by changing the default in
      # code, keeps local dev/tests off by default while this specific deployment opts in.
      env {
        name  = "VENDOR_INBOX_BACKEND"
        value = "imap"
      }

      resources {
        limits = {
          cpu = "2"
          # 512Mi was not enough and failed in the worst way: the container OOM'd during
          # startup ("Memory limit of 512 MiB exceeded with 513 MiB used"), so Cloud Run
          # reported only "the container failed to start and listen on PORT" — a message that
          # points at the port, not at memory. Two things need the headroom: importing ADK at
          # all, and the autonomous fleet watch (services/autonomy.py), which loads a
          # specialist agent's full object graph in-process to run a real turn.
          memory = "2Gi"
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

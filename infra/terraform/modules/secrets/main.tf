# The secret itself was created manually (gcloud secrets create), not by Terraform, so its
# value is never in state or in this repo. This module only grants read access to it.
data "google_secret_manager_secret" "gemini_api_key" {
  project   = var.project_id
  secret_id = var.gemini_api_key_secret_id
}

resource "google_secret_manager_secret_iam_member" "agent_access" {
  for_each  = var.accessor_sa_emails
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

# Gmail app password (SMTP send for approval-gated agent email), created manually the same way
# as the Gemini key -- see apps/api/AGENTS.md's Gmail setup section for the app-password
# generation + `gcloud secrets create` steps.
data "google_secret_manager_secret" "gmail_app_password" {
  project   = var.project_id
  secret_id = var.gmail_app_password_secret_id
}

resource "google_secret_manager_secret_iam_member" "agent_access_gmail" {
  for_each  = var.accessor_sa_emails
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.gmail_app_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

# A2A shared secret (docs/threat-model.md finding 1) — needs exactly two readers, not the full
# accessor_sa_emails set: supply-agent-sa (Supply Chain's own dedicated identity — see
# modules/iam's docstring for how every Reasoning Engine now runs as its own per-agent SA
# rather than the shared Reasoning Engine service agent this used to grant) and
# coordinator-agent-sa (prudently-api's Cloud Run runtime identity, the receiver, and also the
# sender for the live in-process A2A path — see modules/cloud_run_api). No other agent sends or
# checks this secret.
data "google_secret_manager_secret" "a2a_shared_secret" {
  project   = var.project_id
  secret_id = var.a2a_shared_secret_secret_id
}

resource "google_secret_manager_secret_iam_member" "supply_sa_access_a2a" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.a2a_shared_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.supply_sa_email}"
}

resource "google_secret_manager_secret_iam_member" "coordinator_sa_access_a2a" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.a2a_shared_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.coordinator_sa_email}"
}

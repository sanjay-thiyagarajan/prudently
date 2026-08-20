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

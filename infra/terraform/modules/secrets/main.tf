# The secret itself was created manually (gcloud secrets create), not by Terraform, so its
# value is never in state or in this repo. This module only grants read access to it.
data "google_secret_manager_secret" "gemini_api_key" {
  project   = var.project_id
  secret_id = var.gemini_api_key_secret_id
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_secret_manager_secret_iam_member" "agent_access" {
  for_each  = var.accessor_sa_emails
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

# Deployed agents on Vertex AI Agent Engine run under Google's own Reasoning Engine service
# agent (confirmed via `client.agent_engines.get(...).effective_identity` during Day 3
# testing), NOT the custom per-agent SAs from modules/iam — Agent Engine has no
# --service_account deploy flag as of ADK 2.7.1/google-cloud-aiplatform. Revisit this when
# building Agent Identity properly (Day 5); for now this is the runtime identity that
# actually needs secret access for bootstrap_gemini_credentials() (config.py) to work.
resource "google_secret_manager_secret_iam_member" "reasoning_engine_service_agent_access" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

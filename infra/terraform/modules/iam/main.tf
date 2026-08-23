# Agent Identity fallback (docs/day1-probe-results.md row #4): per-agent service accounts
# with least-privilege IAM, standing in for a distinct "Agent Identity" product that wasn't
# found in this project. No key files are ever generated — Cloud Run / Reasoning Engine
# authenticate as these SAs via Application Default Credentials.

locals {
  agent_names = ["coordinator", "shift", "inventory", "supply", "hr", "medrep", "chaos"]
}

resource "google_service_account" "agent" {
  for_each     = toset(local.agent_names)
  project      = var.project_id
  account_id   = "${each.value}-agent-sa"
  display_name = "Prudently ${title(each.value)} Agent"
}

resource "google_service_account" "platform_admin" {
  project      = var.project_id
  account_id   = "platform-admin-sa"
  display_name = "Prudently Platform Admin (Agent Registry writes)"
}

# Every agent SA can invoke Vertex AI (Gemini, Agent Runtime, Memory Bank).
resource "google_project_iam_member" "agent_aiplatform_user" {
  for_each = google_service_account.agent
  project  = var.project_id
  role     = "roles/aiplatform.user"
  member   = "serviceAccount:${each.value.email}"
}

# Memory Bank scoping: agents can read/write only their own (agent_name, user) scope in
# principle — Memory Bank's own IAM conditions are applied at the resource level once the
# service is provisioned via the SDK (Terraform's google_project_iam_member below grants the
# baseline role; fine-grained scope conditions are enforced in application code via the
# scope field on every Memory Bank call, per apps/api/services/memory.py).
resource "google_project_iam_member" "agent_memory_editor" {
  for_each = google_service_account.agent
  project  = var.project_id
  role     = "roles/aiplatform.memoryEditor"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "platform_admin_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.platform_admin.email}"
}

# Agents read/write Firestore live state (services/state.py) directly, not just through
# platform-admin — grant every agent SA the same access.
resource "google_project_iam_member" "agent_datastore_user" {
  for_each = google_service_account.agent
  project  = var.project_id
  role     = "roles/datastore.user"
  member   = "serviceAccount:${each.value.email}"
}

# Deployed agents on Vertex AI Agent Engine run under Google's own Reasoning Engine service
# agent, not the custom per-agent SAs above (see modules/secrets/main.tf for the same
# finding re: Agent Identity). It needs Firestore access too.
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_iam_member" "reasoning_engine_service_agent_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

# Medical Representative's ingestion path calls Model Armor's sanitize APIs at runtime —
# granted to the same shared Reasoning Engine service agent as above, since that's what every
# deployed agent actually runs as (not the per-agent SAs). Applied manually via `gcloud
# projects add-iam-policy-binding` first to unblock deploys before `terraform apply` catches
# up — see AGENTS.md.
resource "google_project_iam_member" "reasoning_engine_service_agent_modelarmor_user" {
  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

# Medical Representative's A2A endpoint is mounted inside the prudently-api Cloud Run service
# (apps/api/app.py), which runs as coordinator-agent-sa (modules/cloud_run_api's
# coordinator_agent_sa_email) — a separate identity from the Reasoning Engine service agent
# above, and one that also calls Model Armor whenever Supply Chain reaches Medical
# Representative over A2A. Without this grant, VertexArmorService's fail-closed handling
# silently blocks every A2A call with matched_filters=["armor_unavailable"] instead of the
# real filter result.
resource "google_project_iam_member" "coordinator_sa_modelarmor_user" {
  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = "serviceAccount:${google_service_account.agent["coordinator"].email}"
}

# Both runtime identities that create OTel spans need roles/cloudtrace.agent to export them
# via CloudTraceSpanExporter — a missing grant here fails silently (a dropped span, not a
# raised exception), same failure shape as the modelarmor.user gap above.
resource "google_project_iam_member" "reasoning_engine_service_agent_cloudtrace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "coordinator_sa_cloudtrace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.agent["coordinator"].email}"
}

# Agent detail page's trace/log viewer: coordinator-agent-sa (prudently-api's Cloud Run
# runtime identity) reads Cloud Trace and Cloud Logging on the manager's behalf via
# routes/traces.py — a different capability from cloudtrace.agent above, which only grants
# writing spans. Without these, both endpoints 500 with a PermissionDenied swallowed into a
# generic error by the CORS middleware, which never gets a chance to attach headers to the
# exception response — looks like a CORS failure in the browser console, not an IAM gap,
# unless the real Cloud Run logs are checked directly.
resource "google_project_iam_member" "coordinator_sa_cloudtrace_user" {
  project = var.project_id
  role    = "roles/cloudtrace.user"
  member  = "serviceAccount:${google_service_account.agent["coordinator"].email}"
}

resource "google_project_iam_member" "coordinator_sa_logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.agent["coordinator"].email}"
}

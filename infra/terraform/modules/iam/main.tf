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
# finding/caveat re: Agent Identity, Day 5). It needs Firestore access too.
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_iam_member" "reasoning_engine_service_agent_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

# Medical Representative's ingestion path calls Model Armor's sanitize APIs at runtime (Day
# 4) — granted to the same shared Reasoning Engine service agent as above, since that's what
# every deployed agent actually runs as (not the per-agent SAs), confirmed Day 3. Applied
# manually via `gcloud projects add-iam-policy-binding` first to unblock Day 4 deploys before
# `terraform apply` catches up — see AGENTS.md.
resource "google_project_iam_member" "reasoning_engine_service_agent_modelarmor_user" {
  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

# Medical Representative's A2A endpoint is mounted inside the prudently-api Cloud Run service
# (apps/api/app.py), which runs as coordinator-agent-sa (modules/cloud_run_api's
# coordinator_agent_sa_email) — a separate identity from the Reasoning Engine service agent
# above, and one that also calls Model Armor whenever Supply Chain reaches Medical
# Representative over A2A. Found live Day 5: without this, VertexArmorService's fail-closed
# handling silently blocked every A2A call with matched_filters=["armor_unavailable"] instead
# of the real filter result.
resource "google_project_iam_member" "coordinator_sa_modelarmor_user" {
  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = "serviceAccount:${google_service_account.agent["coordinator"].email}"
}

# Observability (Day 5): both runtime identities that create OTel spans need
# roles/cloudtrace.agent to export them via CloudTraceSpanExporter — granted to both
# proactively, before writing any span code, having learned from the modelarmor.user gap
# above that a missing grant here fails silently (a dropped span, not a raised exception).
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

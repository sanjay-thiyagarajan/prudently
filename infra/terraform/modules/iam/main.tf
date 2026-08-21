# Agent Identity fallback (docs/day1-probe-results.md row #4): per-agent service accounts
# with least-privilege IAM, standing in for a distinct "Agent Identity" product that wasn't
# found in this project. No key files are ever generated — Cloud Run / Reasoning Engine
# authenticate as these SAs via Application Default Credentials.

locals {
  agent_names = ["coordinator", "shift", "supply", "chaos"]
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

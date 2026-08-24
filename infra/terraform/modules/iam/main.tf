# Agent Identity (docs/threat-model.md finding 9): per-agent service accounts with
# least-privilege IAM. Originally these existed but were never actually bound to a deployed
# Reasoning Engine — `adk deploy agent_engine`'s CLI has no `--service_account` flag, which is
# what the project's own earlier notes ("Agent Engine has no per-agent service account support")
# were based on. That's true of the CLI; it is not true of the underlying API: `vertexai._genai
# .types.common.AgentEngineConfig` (what the CLI itself calls) has a real `service_account`
# field, and `adk deploy`'s own `.agent_engine_config.json` mechanism merges arbitrary config
# keys in before that call — see each agent folder's `.agent_engine_config.json`. No key files
# are ever generated either way — Cloud Run / Reasoning Engine authenticate as these SAs via
# Application Default Credentials.

locals {
  # "surgical-scheduling" (hyphen), not "surgical_scheduling" (underscore) — GCP service
  # account ids must match [a-z]([-a-z0-9]*[a-z0-9]), no underscores allowed.
  agent_names = ["coordinator", "shift", "inventory", "supply", "hr", "medrep", "chaos", "surgical-scheduling"]
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

# Every deployed Reasoning Engine now runs under its own dedicated per-agent SA above, not
# Google's shared Reasoning Engine service agent — see this file's top docstring for how
# (.agent_engine_config.json's service_account field). Confirmed live, Aug 24: each engine's
# own effective_identity now reads back as its own SA, not
# service-<project#>@gcp-sa-aiplatform-re.iam.gserviceaccount.com, and every agent still works
# under it (stream_query smoke tests, a live KMS decrypt through surgical_scheduling_agent, a
# live Model Armor screen through medical_representative_agent). The shared service agent's own
# Firestore/Model-Armor/Cloud-Trace grants that used to live here are gone as of the same
# change — they were only ever needed because no engine had its own identity yet.
#
# Medical Representative's A2A endpoint is also mounted inside the prudently-api Cloud Run service
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

# medrep-agent-sa needs the same grant for a second, genuinely different reason: since every
# Reasoning Engine now runs as its own dedicated SA (each agent's .agent_engine_config.json —
# see this file's own docstring), the *standalone* deployed medical_representative_agent engine
# (used for stream_query verification, separate from the in-process copy the A2A mount above
# runs under coordinator-agent-sa) authenticates as medrep-agent-sa, not the shared identity —
# caught live: its own pre_llm_screen call failed closed with "Model Armor call failed" the
# first time this engine was redeployed onto its new SA, before this grant existed.
resource "google_project_iam_member" "medrep_sa_modelarmor_user" {
  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = "serviceAccount:${google_service_account.agent["medrep"].email}"
}

# Every runtime identity that creates OTel spans needs roles/cloudtrace.agent to export them
# via CloudTraceSpanExporter — a missing grant here fails silently (a dropped span, not a
# raised exception). A for_each across every per-agent SA, not just coordinator: each deployed
# engine's own spans depend on its own SA carrying this grant now that each runs as itself
# rather than the shared Reasoning Engine service agent.
resource "google_project_iam_member" "agent_cloudtrace_agent" {
  for_each = google_service_account.agent
  project  = var.project_id
  role     = "roles/cloudtrace.agent"
  member   = "serviceAccount:${each.value.email}"
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

# coordinator-agent-sa is prudently-api's Cloud Run runtime identity, the only identity that
# ever calls services/auth.py's require_firebase_auth/require_role. verify_id_token(...,
# check_revoked=True) (docs/threat-model.md finding 5) does real local JWT verification plus
# one extra call to Identity Toolkit's getAccountInfo to check the token against the user's
# validSince timestamp — that second call needs its own IAM grant, which this SA never had.
# Caught live, not in review: every authenticated route 401'd for a genuinely signed-in
# manager, because _verify()'s blanket `except Exception` swallowed the real
# PERMISSION_DENIED and re-raised a generic "Invalid or expired session." roles/firebaseauth
# .viewer is the minimal predefined role covering firebaseauth.users.get — read-only, no write
# access, since this SA only ever verifies, never manages, users.
resource "google_project_iam_member" "coordinator_sa_firebaseauth_viewer" {
  project = var.project_id
  role    = "roles/firebaseauth.viewer"
  member  = "serviceAccount:${google_service_account.agent["coordinator"].email}"
}

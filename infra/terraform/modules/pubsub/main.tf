# Simulation clock ticks — drives the compressed flu-surge timeline (SIM_SEED/SIM_SPEEDUP).
resource "google_pubsub_topic" "sim_ticks" {
  project = var.project_id
  name    = "sim-ticks"
}

resource "google_pubsub_subscription" "sim_ticks_api" {
  project = var.project_id
  name    = "sim-ticks-api-sub"
  topic   = google_pubsub_topic.sim_ticks.name
}

# Gateway-intercepted audit event bus (Agent Gateway fallback, see day1-probe-results.md #5).
# Hub-and-spoke only — not used for peer-to-peer agent messaging.
resource "google_pubsub_topic" "gateway_audit" {
  project = var.project_id
  name    = "gateway-audit"
}

resource "google_pubsub_subscription" "gateway_audit_api" {
  project = var.project_id
  name    = "gateway-audit-api-sub"
  topic   = google_pubsub_topic.gateway_audit.name
}

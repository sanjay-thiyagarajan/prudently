output "sim_ticks_topic" {
  value = google_pubsub_topic.sim_ticks.name
}

output "gateway_audit_topic" {
  value = google_pubsub_topic.gateway_audit.name
}

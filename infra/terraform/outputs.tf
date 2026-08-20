output "agent_service_accounts" {
  value = module.iam.agent_service_accounts
}

output "platform_admin_email" {
  value = module.iam.platform_admin_email
}

output "firestore_database" {
  value = module.firestore.database_name
}

output "sim_ticks_topic" {
  value = module.pubsub.sim_ticks_topic
}

output "gateway_audit_topic" {
  value = module.pubsub.gateway_audit_topic
}

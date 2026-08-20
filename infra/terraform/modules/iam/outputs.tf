output "agent_service_accounts" {
  description = "Map of agent name -> service account email"
  value       = { for k, v in google_service_account.agent : k => v.email }
}

output "platform_admin_email" {
  value = google_service_account.platform_admin.email
}

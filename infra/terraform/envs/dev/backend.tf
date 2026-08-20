# Deliberate hackathon-scope choice: local tfstate, not a production pattern.
# (No `backend` block = Terraform defaults to local state in this directory.)
# See AGENTS.md > Terraform section.

terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "prudently" {
  source                = "../../"
  project_id            = var.project_id
  region                = var.region
  memory_bank_location  = var.memory_bank_location
}

output "agent_service_accounts" {
  value = module.prudently.agent_service_accounts
}

output "platform_admin_email" {
  value = module.prudently.platform_admin_email
}

output "firestore_database" {
  value = module.prudently.firestore_database
}

output "sim_ticks_topic" {
  value = module.prudently.sim_ticks_topic
}

output "gateway_audit_topic" {
  value = module.prudently.gateway_audit_topic
}

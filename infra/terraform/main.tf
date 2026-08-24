module "iam" {
  source     = "./modules/iam"
  project_id = var.project_id
}

module "firestore" {
  source     = "./modules/firestore"
  project_id = var.project_id
  region     = var.region
}

module "pubsub" {
  source     = "./modules/pubsub"
  project_id = var.project_id
}

module "secrets" {
  source               = "./modules/secrets"
  project_id           = var.project_id
  accessor_sa_emails   = toset(values(module.iam.agent_service_accounts))
  coordinator_sa_email = module.iam.agent_service_accounts["coordinator"]
  supply_sa_email      = module.iam.agent_service_accounts["supply"]
}

module "cloud_run_api" {
  source                      = "./modules/cloud_run_api"
  project_id                  = var.project_id
  region                      = var.region
  memory_bank_location        = var.memory_bank_location
  coordinator_agent_sa_email  = module.iam.agent_service_accounts["coordinator"]
}

module "cloud_run_web" {
  source     = "./modules/cloud_run_web"
  project_id = var.project_id
  region     = var.region
  api_url    = module.cloud_run_api.url
}

module "kms" {
  source     = "./modules/kms"
  project_id = var.project_id
  location   = var.region
  # Deliberately narrower than modules.secrets' accessor_sa_emails (every per-agent SA, mostly
  # unused local-dev identities): only the two identities that ever legitimately decrypt patient
  # PII. surgical_scheduling_agent now runs as its own dedicated surgical-scheduling-agent-sa
  # (bound via agents/surgical_scheduling/.agent_engine_config.json's service_account field —
  # see modules/iam's own docstring for how that's actually wired, since `adk deploy`'s CLI has
  # no --service_account flag but the underlying AgentEngineConfig API does), not the shared
  # Reasoning Engine service agent every other agent still uses. coordinator-agent-sa keeps
  # access too — it's prudently-api's own Cloud Run runtime identity, and Coordinator's
  # "frozen copies" architecture means it executes surgical_scheduling's tools in-process.
  accessor_sa_emails = toset([
    module.iam.agent_service_accounts["surgical-scheduling"],
    module.iam.agent_service_accounts["coordinator"],
  ])
}

data "google_project" "current" {
  project_id = var.project_id
}

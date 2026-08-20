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
  source              = "./modules/secrets"
  project_id          = var.project_id
  accessor_sa_emails  = toset(values(module.iam.agent_service_accounts))
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

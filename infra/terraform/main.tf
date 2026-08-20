# Day 1 scope: Firestore, Pub/Sub, per-agent IAM only. Cloud Run + Secret Manager land Day 2
# (infra/terraform/modules/cloud_run_api, cloud_run_web, secrets — not yet wired here).

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

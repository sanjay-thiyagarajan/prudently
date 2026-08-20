terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

# NOTE: no `provider "google" {}` block here deliberately — this directory is a reusable
# composition module, invoked by infra/terraform/envs/dev (the actual Terraform root, which
# holds the provider config, backend config, and tfvars).

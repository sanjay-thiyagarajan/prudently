variable "project_id" {
  type = string
}

variable "gemini_api_key_secret_id" {
  type    = string
  default = "prudently-gemini-api-key"
}

variable "gmail_app_password_secret_id" {
  type    = string
  default = "prudently-gmail-app-password"
}

# docs/threat-model.md finding 1 — the shared secret both the A2A sender (Supply Chain) and
# receiver (prudently-api's SharedSecretASGIMiddleware) fetch, closing the "anyone on the
# internet can call the A2A mount" gap. Created manually via gcloud, same as the two secrets
# above — its value is never in state or in this repo.
variable "a2a_shared_secret_secret_id" {
  type    = string
  default = "prudently-a2a-shared-secret"
}

variable "accessor_sa_emails" {
  description = "Set of service account emails that may read the Gemini API key and Gmail app password secrets"
  type        = set(string)
}

variable "coordinator_sa_email" {
  description = "coordinator-agent-sa — prudently-api's actual Cloud Run runtime identity, the receiver side of the A2A shared secret"
  type        = string
}

variable "supply_sa_email" {
  description = "supply-agent-sa — the standalone deployed supply_chain_resiliency_agent Reasoning Engine's own identity, the sender side of the A2A shared secret when that engine is invoked directly (e.g. via stream_query) rather than through the in-process copy prudently-api runs as coordinator-agent-sa"
  type        = string
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "memory_bank_location" {
  type = string
}

variable "coordinator_agent_sa_email" {
  description = "Runtime service account for the API service (coordinator-agent-sa)"
  type        = string
}

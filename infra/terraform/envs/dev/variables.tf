variable "project_id" {
  type    = string
  default = "prudently-hackathon"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "memory_bank_location" {
  type = string
  # Not "us". Memory Bank scoped to a specific agent_engine_id must use that engine's own
  # region; the multi-region form 404s with "The ReasoningEngine does not exist", which looks
  # like a missing engine and sent this project debugging in the wrong place once already.
  default = "us-central1"
}

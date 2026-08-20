variable "project_id" {
  description = "GCP project ID (locked: prudently-hackathon, created Day 1)"
  type        = string
}

variable "region" {
  description = "Region lock for Cloud Run / Pub/Sub / Firestore / Reasoning Engine (see docs/day1-probe-results.md — do not change post-lock)"
  type        = string
  default     = "us-central1"
}

variable "memory_bank_location" {
  description = "Memory Bank residency (multi-region) lock"
  type        = string
  default     = "us"
}

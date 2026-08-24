variable "project_id" {
  type = string
}

variable "location" {
  type    = string
  default = "us-central1"
}

variable "key_ring_id" {
  type    = string
  default = "prudently-patient-data"
}

variable "key_id" {
  type    = string
  default = "patient-pii"
}

variable "accessor_sa_emails" {
  description = "Service accounts that may call encrypt/decrypt against the patient-pii key — deliberately a narrower set than modules/secrets' accessor_sa_emails, since not every agent should be able to decrypt patient PII (see docs/threat-model.md finding 9 and services/platform/access_control.py)"
  type        = set(string)
}

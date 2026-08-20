variable "project_id" {
  type = string
}

variable "gemini_api_key_secret_id" {
  type    = string
  default = "prudently-gemini-api-key"
}

variable "accessor_sa_emails" {
  description = "Set of service account emails that may read the Gemini API key secret"
  type        = set(string)
}

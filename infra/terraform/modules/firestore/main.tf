# Live operational state — distinct from Memory Bank's long-term narrative memory.
# Location is IMMUTABLE after creation (see docs/day1-probe-results.md region lock).
resource "google_firestore_database" "prudently" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

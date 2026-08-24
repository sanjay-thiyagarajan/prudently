# Field-level encryption for patient PII (Part D) — the concrete GCP-product-backed answer to
# docs/threat-model.md finding 9's "one compromised agent can read every Firestore collection"
# blast-radius concern. Firestore's own encryption-at-rest already protects every collection
# uniformly; this key ring exists specifically so patient name/DOB/contact fields stay opaque
# ciphertext even to a caller that can read the patients collection directly but was never
# granted decrypt access to this key — a narrower, deliberately different accessor set than
# modules/secrets' accessor_sa_emails.

resource "google_kms_key_ring" "patient_data" {
  project  = var.project_id
  name     = var.key_ring_id
  location = var.location

  # Key rings can't be deleted in GCP at all (only their keys can be rotated/destroyed) — this
  # lifecycle block just stops Terraform from trying and failing on a plan involving one, the
  # same defensive pattern modules/firestore likely already needs for its own undeletable
  # resource.
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "patient_pii" {
  name     = var.key_id
  key_ring = google_kms_key_ring.patient_data.id
  purpose  = "ENCRYPT_DECRYPT"

  # Automatic rotation — a real production expectation for a key protecting PII, cheap to set
  # up now rather than retrofit later. 90 days is a common compliance-adjacent baseline.
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key_iam_member" "accessor" {
  for_each      = var.accessor_sa_emails
  crypto_key_id = google_kms_crypto_key.patient_pii.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${each.value}"
}

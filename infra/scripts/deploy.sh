#!/usr/bin/env bash
# Deploys both Cloud Run services from source. Terraform owns the service shell (identity,
# IAM, env vars, scaling); this script owns the container image going forward — Terraform's
# `lifecycle { ignore_changes = [image] }` means these two never fight over it.
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-prudently-hackathon}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

echo "== Deploying prudently-api from apps/api =="
gcloud run deploy prudently-api \
  --project="$PROJECT" \
  --region="$REGION" \
  --source=apps/api \
  --quiet

echo
echo "== Deploying prudently-web from apps/web =="
gcloud run deploy prudently-web \
  --project="$PROJECT" \
  --region="$REGION" \
  --source=apps/web \
  --quiet

echo
echo "Done. URLs:"
gcloud run services describe prudently-api --project="$PROJECT" --region="$REGION" --format="value(status.url)"
gcloud run services describe prudently-web --project="$PROJECT" --region="$REGION" --format="value(status.url)"

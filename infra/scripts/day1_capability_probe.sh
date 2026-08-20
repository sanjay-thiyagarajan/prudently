#!/usr/bin/env bash
# Day-1 verification spike: confirm which of the 7 Fortified Enterprise Fleet
# capabilities are backed by distinct managed GCP products in this project vs.
# need the local-emulated fallback. Findings get written to docs/day1-probe-results.md.
set -euo pipefail

echo "== Active account/project =="
gcloud auth list --filter=status:ACTIVE --format="value(account)"
gcloud config get-value project

echo
echo "== Candidate services (available to enable) =="
gcloud services list --available \
  --filter="name~aiplatform OR name~agent OR name~modelarmor OR name~apigee OR name~discoveryengine" \
  --format="table(name, title)"

echo
echo "== aiplatform.googleapis.com discovery resources =="
curl -s "https://aiplatform.googleapis.com/\$discovery/rest?version=v1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(sorted(d.get('resources', {}).keys())))"

echo
echo "== Enabling core services needed regardless of probe outcome =="
gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudtrace.googleapis.com \
  logging.googleapis.com

echo
echo "Probe complete. Cross-reference output above against docs/day1-probe-results.md"
echo "and fill in the status/backend column for Registry, Identity, Gateway, Model Armor,"
echo "and Observability. Also do a manual console pass: Vertex AI > Agent Builder / Agent"
echo "Engine, since console-only surfaces won't show in the discovery doc."

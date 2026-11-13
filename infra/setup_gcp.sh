#!/usr/bin/env bash
# One-time Google Cloud setup for the scheduled BigQuery pipeline.
# Run it in Cloud Shell (gcloud and bq are preinstalled) or anywhere you are logged in with gcloud.
#
#   PROJECT_ID=my-project GITHUB_REPO=VicDeni/qsr-revenue-growth bash infra/setup_gcp.sh
#
# Optional: LANDING_BUCKET=my-bucket  -> also creates a Cloud Storage landing zone and uploads data/landing
#           BQ_LOCATION=US            -> BigQuery location (default US)
#
# Creates: BigQuery datasets, a least-privilege service account, and Workload Identity Federation so
# GitHub Actions can authenticate with short-lived tokens (no JSON keys stored anywhere).
# Cost: this project's data is ~20 MB, well inside BigQuery's free tier (10 GB storage, 1 TB queries/month).
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${GITHUB_REPO:?Set GITHUB_REPO, e.g. VicDeni/qsr-revenue-growth}"
BQ_LOCATION="${BQ_LOCATION:-US}"
SA_NAME="qsr-pipeline"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
POOL="github-pool"
PROVIDER="github-provider"

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

echo "==> Enabling APIs"
gcloud services enable bigquery.googleapis.com storage.googleapis.com iam.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com sheets.googleapis.com

echo "==> BigQuery datasets"
for ds in qsr_raw qsr_staging qsr_marts qsr_reporting; do
  bq --location="$BQ_LOCATION" show --dataset "${PROJECT_ID}:${ds}" >/dev/null 2>&1 \
    || bq --location="$BQ_LOCATION" mk --dataset --description "QSR revenue growth pipeline" "${PROJECT_ID}:${ds}"
done

echo "==> Service account ${SA_EMAIL}"
gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1 \
  || gcloud iam service-accounts create "$SA_NAME" --display-name "QSR pipeline (GitHub Actions)"
for role in roles/bigquery.jobUser roles/bigquery.dataEditor; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA_EMAIL}" \
    --role "$role" --condition None >/dev/null
done

if [[ -n "${LANDING_BUCKET:-}" ]]; then
  echo "==> Landing bucket gs://${LANDING_BUCKET}"
  gcloud storage buckets describe "gs://${LANDING_BUCKET}" >/dev/null 2>&1 \
    || gcloud storage buckets create "gs://${LANDING_BUCKET}" --location "$BQ_LOCATION" --uniform-bucket-level-access
  gcloud storage buckets add-iam-policy-binding "gs://${LANDING_BUCKET}" \
    --member "serviceAccount:${SA_EMAIL}" --role roles/storage.objectViewer >/dev/null
  gcloud storage cp -r data/landing/* "gs://${LANDING_BUCKET}/landing/"
fi

echo "==> Workload Identity Federation for ${GITHUB_REPO}"
gcloud iam workload-identity-pools describe "$POOL" --location global >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools create "$POOL" --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers describe "$PROVIDER" --location global \
  --workload-identity-pool "$POOL" >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --location global \
       --workload-identity-pool "$POOL" --display-name "GitHub OIDC" \
       --issuer-uri "https://token.actions.githubusercontent.com" \
       --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
       --attribute-condition "assertion.repository == '${GITHUB_REPO}'"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${GITHUB_REPO}" \
  >/dev/null

PROVIDER_NAME="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}"
cat <<EOF

Done. Add these as GitHub repository *variables* (Settings > Secrets and variables > Actions > Variables).
None of them are secrets, and no key file was created.

  GCP_PROJECT                     ${PROJECT_ID}
  GCP_SERVICE_ACCOUNT             ${SA_EMAIL}
  GCP_WORKLOAD_IDENTITY_PROVIDER  ${PROVIDER_NAME}
  BQ_LOCATION                     ${BQ_LOCATION}
$( [[ -n "${LANDING_BUCKET:-}" ]] && echo "  LANDING_URI                     gs://${LANDING_BUCKET}/landing" )

Or with the GitHub CLI:
  gh variable set GCP_PROJECT --body "${PROJECT_ID}" --repo ${GITHUB_REPO}
  gh variable set GCP_SERVICE_ACCOUNT --body "${SA_EMAIL}" --repo ${GITHUB_REPO}
  gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "${PROVIDER_NAME}" --repo ${GITHUB_REPO}

Optional, for an auto-refreshing Tableau Public dashboard: create a Google Sheet, share it with
${SA_EMAIL} as Editor, and set SHEETS_SPREADSHEET_ID to the ID in its URL.
EOF

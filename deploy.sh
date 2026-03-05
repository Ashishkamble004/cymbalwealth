#!/usr/bin/env bash
# =============================================================================
# Wealth Management Platform — Master GCP Deployment Script
# Idempotent: safe to run multiple times without duplicating resources
# =============================================================================
set -euo pipefail

# ---- Configuration ----
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="asia-south1"
REPO_NAME="wealth-platform"
SQL_INSTANCE="wealth-db"
DB_NAME="wealthdb"
DB_USER="wealthuser"
REDIS_INSTANCE="wealth-cache"
VPC_CONNECTOR="wealth-vpc-connector"
SA_NAME="wealth-backend"
KYC_BUCKET="kyc-documents-${PROJECT_ID}"
VOICE_BUCKET="voice-transcripts-${PROJECT_ID}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ==========================================================================
# STEP 1 — Prerequisites check
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 1 — Prerequisites Check"
echo "========================================="

command -v gcloud >/dev/null 2>&1 || err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
command -v docker >/dev/null 2>&1 || err "docker CLI not found. Install: https://docs.docker.com/get-docker/"
command -v psql   >/dev/null 2>&1 || warn "psql not found — DB seed step will be skipped"

gcloud auth print-identity-token >/dev/null 2>&1 || err "Not authenticated. Run: gcloud auth login"
[ -n "${PROJECT_ID}" ] || err "No project set. Run: gcloud config set project YOUR_PROJECT_ID"
log "Authenticated — project: ${PROJECT_ID}"

# ==========================================================================
# STEP 2 — Enable GCP APIs
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 2 — Enable GCP APIs"
echo "========================================="

APIS=(
  run.googleapis.com
  sqladmin.googleapis.com
  redis.googleapis.com
  storage.googleapis.com
  artifactregistry.googleapis.com
  aiplatform.googleapis.com
  secretmanager.googleapis.com
  vpcaccess.googleapis.com
  cloudbuild.googleapis.com
)
for api in "${APIS[@]}"; do
  gcloud services enable "$api" --quiet && log "Enabled $api"
done

# ==========================================================================
# STEP 3 — Create Infrastructure
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 3 — Create Infrastructure"
echo "========================================="

# ---- Artifact Registry ----
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Wealth Platform Docker images"
  log "Created Artifact Registry repo: $REPO_NAME"
else
  log "Artifact Registry repo already exists"
fi

# ---- Cloud SQL ----
if ! gcloud sql instances describe "$SQL_INSTANCE" >/dev/null 2>&1; then
  echo ""
  read -rsp "Enter password for database user '${DB_USER}': " DB_PASSWORD
  echo ""
  gcloud sql instances create "$SQL_INSTANCE" \
    --database-version=POSTGRES_15 \
    --tier=db-g1-small \
    --region="$REGION" \
    --root-password="${DB_PASSWORD}" \
    --storage-auto-increase \
    --availability-type=zonal \
    --quiet
  gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE" --quiet
  gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="${DB_PASSWORD}" --quiet
  log "Created Cloud SQL instance: $SQL_INSTANCE"
else
  log "Cloud SQL instance already exists"
fi

# ---- Cloud Storage ----
for bucket in "$KYC_BUCKET" "$VOICE_BUCKET"; do
  if ! gsutil ls "gs://$bucket" >/dev/null 2>&1; then
    gsutil mb -l "$REGION" "gs://$bucket"
    log "Created bucket: $bucket"
  else
    log "Bucket already exists: $bucket"
  fi
done

# ---- Memorystore Redis ----
if ! gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" >/dev/null 2>&1; then
  gcloud redis instances create "$REDIS_INSTANCE" \
    --size=1 \
    --region="$REGION" \
    --redis-version=redis_7_0 \
    --quiet
  log "Created Redis instance: $REDIS_INSTANCE"
else
  log "Redis instance already exists"
fi

# ---- VPC Connector ----
if ! gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" --region="$REGION" >/dev/null 2>&1; then
  gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR" \
    --region="$REGION" \
    --range="10.8.0.0/28" \
    --quiet
  log "Created VPC connector: $VPC_CONNECTOR"
else
  log "VPC connector already exists"
fi

# ==========================================================================
# STEP 4 — Create Secrets in Secret Manager
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 4 — Secrets"
echo "========================================="

create_secret() {
  local name=$1 value=$2
  if ! gcloud secrets describe "$name" >/dev/null 2>&1; then
    echo -n "$value" | gcloud secrets create "$name" --data-file=- --quiet
    log "Created secret: $name"
  else
    log "Secret already exists: $name"
  fi
}

REDIS_HOST=$(gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --format='value(host)' 2>/dev/null || echo "")
SQL_CONNECTION=$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)' 2>/dev/null || echo "")

if [ -z "${DB_PASSWORD:-}" ]; then
  read -rsp "Enter DB_PASSWORD for Secret Manager: " DB_PASSWORD
  echo ""
fi
read -rp "Enter GEMINI_API_KEY: " GEMINI_API_KEY

create_secret "DB_PASSWORD" "$DB_PASSWORD"
create_secret "DB_CONNECTION_STRING" "postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}"
create_secret "REDIS_HOST" "$REDIS_HOST"
create_secret "GEMINI_API_KEY" "$GEMINI_API_KEY"

# ==========================================================================
# STEP 5 — Service Accounts & IAM
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 5 — Service Accounts & IAM"
echo "========================================="

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Wealth Platform Backend SA"
  log "Created service account: $SA_EMAIL"
else
  log "Service account already exists: $SA_EMAIL"
fi

ROLES=(
  roles/cloudsql.client
  roles/storage.objectAdmin
  roles/redis.editor
  roles/secretmanager.secretAccessor
  roles/aiplatform.user
)
for role in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$role" \
    --condition=None \
    --quiet >/dev/null 2>&1
  log "Bound $role → $SA_EMAIL"
done

# ==========================================================================
# STEP 6 — Build & Push Docker Images
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 6 — Build & Push Docker Images"
echo "========================================="

IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

docker build -t "${IMAGE_BASE}/backend:latest" ./backend
docker push "${IMAGE_BASE}/backend:latest"
log "Pushed backend image"

docker build -t "${IMAGE_BASE}/frontend:latest" ./frontend
docker push "${IMAGE_BASE}/frontend:latest"
log "Pushed frontend image"

# ==========================================================================
# STEP 7 — DB Migrations & Seed
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 7 — DB Migrations & Seed"
echo "========================================="

if command -v psql >/dev/null 2>&1 && [ -n "${SQL_CONNECTION}" ]; then
  warn "Starting Cloud SQL Auth Proxy for migration..."
  # Download proxy if not present
  if [ ! -f ./cloud-sql-proxy ]; then
    curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.2/cloud-sql-proxy.linux.amd64
    chmod +x cloud-sql-proxy
  fi
  ./cloud-sql-proxy "${SQL_CONNECTION}" --port 15432 &
  PROXY_PID=$!
  sleep 5

  # Run seed
  cd backend
  DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:15432/${DB_NAME}" python -c "
from db.database import engine, Base
from models.client import Client, Holding, Goal, Transaction
Base.metadata.create_all(bind=engine)
from db.seed import seed_data
seed_data()
"
  cd ..
  kill $PROXY_PID 2>/dev/null || true
  log "Database seeded"
else
  warn "Skipping DB seed — psql or Cloud SQL connection unavailable"
fi

# ==========================================================================
# STEP 8 — Deploy to Cloud Run
# ==========================================================================
echo ""
echo "========================================="
echo "  STEP 8 — Deploy to Cloud Run"
echo "========================================="

# ---- Backend ----
gcloud run deploy wealth-backend \
  --image="${IMAGE_BASE}/backend:latest" \
  --region="$REGION" \
  --platform=managed \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=2 \
  --memory=2Gi \
  --vpc-connector="$VPC_CONNECTOR" \
  --service-account="$SA_EMAIL" \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest,DB_PASSWORD=DB_PASSWORD:latest,REDIS_HOST=REDIS_HOST:latest" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GCS_KYC_BUCKET=${KYC_BUCKET},GCS_VOICE_BUCKET=${VOICE_BUCKET},DB_URL=postgresql://${DB_USER}:\${DB_PASSWORD}@localhost:5432/${DB_NAME},BANK_NAME=Prestige Private Bank" \
  --add-cloudsql-instances="${SQL_CONNECTION}" \
  --no-allow-unauthenticated \
  --quiet
log "Deployed backend to Cloud Run"

BACKEND_URL=$(gcloud run services describe wealth-backend --region="$REGION" --format='value(status.url)')

# ---- Frontend ----
gcloud run deploy wealth-frontend \
  --image="${IMAGE_BASE}/frontend:latest" \
  --region="$REGION" \
  --platform=managed \
  --min-instances=1 \
  --max-instances=5 \
  --cpu=1 \
  --memory=512Mi \
  --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --allow-unauthenticated \
  --quiet
log "Deployed frontend to Cloud Run"

FRONTEND_URL=$(gcloud run services describe wealth-frontend --region="$REGION" --format='value(status.url)')

# ==========================================================================
# STEP 9 — Summary
# ==========================================================================
echo ""
echo "========================================="
echo "  DEPLOYMENT COMPLETE"
echo "========================================="
echo ""
echo "  Frontend URL:    ${FRONTEND_URL}"
echo "  Backend URL:     ${BACKEND_URL}"
echo "  Cloud SQL:       ${SQL_CONNECTION}"
echo "  Service Account: ${SA_EMAIL}"
echo ""
echo "  Estimated Monthly Cost (idle / light usage):"
echo "  ┌──────────────────────────┬───────────┐"
echo "  │ Cloud Run (2 services)   │ ~\$30-60   │"
echo "  │ Cloud SQL (db-g1-small)  │ ~\$25      │"
echo "  │ Memorystore Redis (1GB)  │ ~\$35      │"
echo "  │ Cloud Storage            │ ~\$1       │"
echo "  │ Gemini API calls         │ usage     │"
echo "  │ VPC Connector            │ ~\$7       │"
echo "  ├──────────────────────────┼───────────┤"
echo "  │ TOTAL (approx.)          │ ~\$100-130 │"
echo "  └──────────────────────────┴───────────┘"
echo ""

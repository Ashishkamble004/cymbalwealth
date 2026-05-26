#!/usr/bin/env bash
# Sets up AWS OIDC federation for GCP→AWS cross-cloud agent calls.
#
# KEY INSIGHT: For Google OIDC tokens, AWS maps accounts.google.com:aud
# to the `azp` claim (not `aud`). For service account tokens, `azp` is
# the SA's unique numeric ID. The OIDC provider's client ID list must
# include this numeric ID, NOT the token's actual `aud` field.
#
# Prerequisites:
#   - AWS CLI with MFA session active
#   - GCP service account's unique numeric ID (from `sub`/`azp` in the token)
#
# Run once. Idempotent — safe to re-run.

set -euo pipefail

AWS_ACCOUNT_ID="453809273083"
# This is the GCP SA's unique numeric ID (sub/azp claim in the OIDC token).
# Get it from: gcloud iam service-accounts describe <SA_EMAIL> --format='value(uniqueId)'
GCP_SA_UNIQUE_ID="102733793156029134803"
ROLE_NAME="cymbal-wealth-gcp-agentcore"
PROVIDER_URL="accounts.google.com"
PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${PROVIDER_URL}"

echo "=== Step 1: Check/Create OIDC Identity Provider ==="
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" >/dev/null 2>&1; then
    echo "OIDC provider exists. Current client IDs:"
    aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" \
        --query 'ClientIDList' --output text

    echo "Adding client ID: ${GCP_SA_UNIQUE_ID} (SA numeric ID = azp claim)"
    aws iam add-client-id-to-open-id-connect-provider \
        --open-id-connect-provider-arn "$PROVIDER_ARN" \
        --client-id "$GCP_SA_UNIQUE_ID" 2>/dev/null || echo "(already registered)"
else
    echo "Creating OIDC provider for ${PROVIDER_URL}..."
    THUMBPRINT=$(echo | openssl s_client -servername accounts.google.com \
        -connect accounts.google.com:443 -showcerts 2>/dev/null \
        | awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/{print}' \
        | openssl x509 -fingerprint -sha1 -noout 2>/dev/null \
        | sed 's/://g' | awk -F= '{print tolower($2)}')
    aws iam create-open-id-connect-provider \
        --url "https://${PROVIDER_URL}" \
        --client-id-list "$GCP_SA_UNIQUE_ID" \
        --thumbprint-list "$THUMBPRINT"
    echo "Created."
fi

echo ""
echo "=== Step 2: Check/Create IAM Role ==="
# accounts.google.com:aud maps to azp in Google tokens (SA numeric ID)
# accounts.google.com:sub maps to sub (also SA numeric ID)
TRUST_POLICY=$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${PROVIDER_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${PROVIDER_URL}:aud": "${GCP_SA_UNIQUE_ID}"
        }
      }
    }
  ]
}
POLICY
)

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
    echo "Role exists. Updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document "$TRUST_POLICY"
else
    echo "Creating role ${ROLE_NAME}..."
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "GCP OIDC federation for CymbalWealth cross-cloud agent calls"
fi

echo ""
echo "=== Step 3: Attach AgentCore invoke policy ==="
POLICY_DOC=$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeAgentCore",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime"
      ],
      "Resource": [
        "arn:aws:bedrock-agentcore:us-east-1:${AWS_ACCOUNT_ID}:runtime/*"
      ]
    }
  ]
}
POLICY
)

POLICY_NAME="cymbal-wealth-agentcore-invoke"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn "$POLICY_ARN" >/dev/null 2>&1; then
    echo "Policy exists."
else
    echo "Creating policy ${POLICY_NAME}..."
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document "$POLICY_DOC" \
        --description "Allow invoking CymbalWealth AgentCore runtimes"
fi

aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "$POLICY_ARN" 2>/dev/null || true

echo ""
echo "=== Done ==="
echo ""
echo "OIDC Provider: ${PROVIDER_ARN}"
echo "Role ARN:      arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo "Client ID:     ${GCP_SA_UNIQUE_ID} (SA azp — NOT the token audience)"
echo ""
echo "No env vars needed on Cloud Run — the code uses any audience string"
echo "and AWS validates against azp (SA numeric ID) automatically."

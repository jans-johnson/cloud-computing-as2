#!/bin/bash
# Package and deploy the serverless backend with AWS SAM.
#
# Prereqs:
#   - sam CLI installed (preinstalled on AWS Academy CloudShell)
#   - LabRole ARN, e.g. arn:aws:iam::<account>:role/LabRole
#
# Usage:
#   LAB_ROLE_ARN=arn:aws:iam::123:role/LabRole \
#   ./backend-lambda/deploy.sh <stack-name>
set -euo pipefail

STACK="${1:-music-app-serverless}"
REGION="${AWS_REGION:-us-east-1}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ -z "${LAB_ROLE_ARN:-}" ]]; then
  ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
  LAB_ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/LabRole"
  echo "LAB_ROLE_ARN not set — using ${LAB_ROLE_ARN}"
fi

SESSION_SECRET="${SESSION_SECRET:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')}"

cd "$HERE"

sam build --template-file template.yaml --use-container

sam deploy \
  --stack-name "$STACK" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset \
  --resolve-s3 \
  --parameter-overrides \
    "LabRoleArn=$LAB_ROLE_ARN" \
    "SessionSecret=$SESSION_SECRET" \
    "S3Bucket=${S3_BUCKET:-as2-music-artist-images}" \
    "FrontendOrigin=${FRONTEND_ORIGIN:-*}"

echo
echo "API endpoint:"
aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text

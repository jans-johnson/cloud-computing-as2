#!/bin/bash
# Build the Flask image and push it to ECR. Creating the cluster, task
# definition, ALB, target group, and service is done from the AWS
# console / CloudFormation in the AWS Academy environment because
# LabRole already has the necessary permissions and console flows are
# fastest there. This script handles the build/push half so the demo
# script is reproducible.
#
# Usage: ./backend-ecs/deploy.sh <ecr-repo-name>
set -euo pipefail

REPO="${1:-music-app}"
REGION="${AWS_REGION:-us-east-1}"
HERE="$(cd "$(dirname "$0")"/.. && pwd)"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
URI="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${REPO}"

aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" \
  >/dev/null 2>&1 || aws ecr create-repository --repository-name "$REPO" --region "$REGION"

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

# Build from repo root so config/ + core/ are in context
docker build --platform linux/amd64 -f "$HERE/backend-ecs/Dockerfile" -t "${REPO}:latest" "$HERE"
docker tag "${REPO}:latest" "${URI}:latest"
docker push "${URI}:latest"

echo
echo "Image pushed: ${URI}:latest"
echo "Next: register a Fargate task definition (executionRoleArn=LabRole,"
echo "taskRoleArn=LabRole, port 8080), and create a service behind an"
echo "Application Load Balancer listening on port 80."

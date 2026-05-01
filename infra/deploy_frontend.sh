#!/bin/bash
# Deploy the static frontend to S3 with website hosting.
#
# Why static + S3 (and not EC2 / a Node server):
#  - No build step or server runtime; the bundle is pure HTML/CSS/JS
#  - S3 charges per GB stored + per request; orders of magnitude cheaper
#    than running a t3.micro 24/7 for static delivery
#  - 11 9s durability and effectively unlimited horizontal scale handled
#    by AWS, no autoscaling group to operate
#  - Optionally front with CloudFront for HTTPS + edge caching
#
# Usage: ./infra/deploy_frontend.sh <bucket-name>
set -euo pipefail

BUCKET="${1:-${FRONTEND_BUCKET:-}}"
if [[ -z "$BUCKET" ]]; then
  echo "Usage: $0 <bucket-name>" >&2
  exit 2
fi

REGION="${AWS_REGION:-us-east-1}"
HERE="$(cd "$(dirname "$0")"/.. && pwd)"

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$BUCKET"
  else
    aws s3api create-bucket --bucket "$BUCKET" \
      --create-bucket-configuration "LocationConstraint=$REGION"
  fi
fi

aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

aws s3 website "s3://$BUCKET/" --index-document index.html --error-document index.html

cat > /tmp/policy.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGet",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET}/*"
  }]
}
JSON
aws s3api put-bucket-policy --bucket "$BUCKET" --policy file:///tmp/policy.json

aws s3 sync "$HERE/frontend/" "s3://$BUCKET/" --delete \
  --cache-control "public,max-age=300"

echo
echo "Frontend live at: http://${BUCKET}.s3-website-${REGION}.amazonaws.com/"
echo "Remember: open the site, then in DevTools console run:"
echo "  localStorage.setItem('api_base', 'https://your-backend.example.com')"

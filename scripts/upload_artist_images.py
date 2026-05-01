"""Task 4 of the brief: download every img_url and upload to S3.

Bucket is created private (default) and stays private — the app uses
pre-signed URLs. The bucket name comes from config.S3_BUCKET, which
must be globally unique; override via S3_BUCKET env var per region.
"""
import _bootstrap  # noqa: F401

import json
import os

import boto3
import requests
from botocore.exceptions import ClientError

from config import AWS_REGION, S3_BUCKET
from core.storage import image_key_for_artist

DATASET = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "2026a2_songs.json",
)


def ensure_bucket(s3) -> None:
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
        print(f"Bucket {S3_BUCKET!r} already exists")
        return
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code not in {"404", "NoSuchBucket"}:
            # 403 means the bucket exists but we can't head it; assume mine
            if code == "403":
                print(f"Bucket {S3_BUCKET!r} reachable but head_bucket forbidden — continuing")
                return
            raise

    if AWS_REGION == "us-east-1":
        s3.create_bucket(Bucket=S3_BUCKET)
    else:
        s3.create_bucket(
            Bucket=S3_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )
    s3.put_public_access_block(
        Bucket=S3_BUCKET,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    print(f"Created private bucket {S3_BUCKET!r}")


def upload_artist_images() -> None:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    ensure_bucket(s3)

    with open(DATASET) as f:
        songs = json.load(f)["songs"]

    seen: dict[str, str] = {}
    for s in songs:
        # Dedupe by artist — same artist always points to the same URL
        seen.setdefault(s["artist"], s.get("img_url") or s.get("image_url", ""))

    print(f"Uploading {len(seen)} unique artist images to s3://{S3_BUCKET}/")
    for artist, url in seen.items():
        if not url:
            print(f"  ! {artist}: no image_url, skipping")
            continue
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
        except requests.RequestException as exc:
            print(f"  ! {artist}: download failed ({exc})")
            continue

        key = image_key_for_artist(artist)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=r.content,
            ContentType=r.headers.get("Content-Type", "image/jpeg"),
        )
        print(f"  + {artist} -> s3://{S3_BUCKET}/{key}")


if __name__ == "__main__":
    upload_artist_images()

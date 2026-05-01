"""S3 helpers for artist images.

Bucket stays private; the frontend only ever sees short-lived pre-signed
GET URLs. This is the security best-practice the brief asks for.
"""
import re
import boto3
from functools import lru_cache
from botocore.config import Config

from config import AWS_REGION, S3_BUCKET, S3_PRESIGN_TTL


@lru_cache(maxsize=1)
def get_s3():
    # signature_version=s3v4 is required for pre-signed URLs in most regions
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        config=Config(signature_version="s3v4"),
    )


def image_key_for_artist(artist: str) -> str:
    """Deterministic S3 key from artist name.

    Mirrors the original GitHub filenames in the dataset (PascalCase, no
    spaces) so the same artist always maps to the same object.
    """
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", artist)
    return f"artists/{cleaned}.jpg"


def presigned_image_url(artist: str, ttl: int = S3_PRESIGN_TTL) -> str:
    return get_s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": image_key_for_artist(artist)},
        ExpiresIn=ttl,
    )

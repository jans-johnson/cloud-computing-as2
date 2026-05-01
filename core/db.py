"""DynamoDB resource accessors.

Lazily build a single boto3 resource per process so handlers in EC2/ECS
keep one connection pool, and Lambda containers reuse it across warm
invocations.
"""
import boto3
from functools import lru_cache

from config import AWS_REGION, LOGIN_TABLE, MUSIC_TABLE


@lru_cache(maxsize=1)
def get_dynamodb():
    return boto3.resource("dynamodb", region_name=AWS_REGION)


def get_login_table():
    return get_dynamodb().Table(LOGIN_TABLE)


def get_music_table():
    return get_dynamodb().Table(MUSIC_TABLE)

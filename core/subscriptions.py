"""Subscription management — backed by a dedicated `subscriptions` table.

Schema (created by scripts/create_subscriptions_table.py):
    PK = email
    SK = song_id = "<artist>#<title>#<album>"
    GSI song-index : PK=song_id, SK=email     (reverse lookup)

Each item denormalises the song fields (artist, title, album) so listing a
user's subscriptions is one Query — no BatchGet against the music table.
"""
from __future__ import annotations

import time

from boto3.dynamodb.conditions import Key

from .db import get_subscriptions_table
from .storage import presigned_image_url

SEP = "#"


def _song_id(artist: str, title: str, album: str) -> str:
    return f"{artist}{SEP}{title}{SEP}{album}"


def add_subscription(email: str, artist: str, title: str, album: str) -> None:
    get_subscriptions_table().put_item(
        Item={
            "email": email,
            "song_id": _song_id(artist, title, album),
            "artist": artist,
            "title": title,
            "album": album,
            "subscribed_at": int(time.time()),
        }
    )


def remove_subscription(email: str, artist: str, title: str, album: str) -> None:
    get_subscriptions_table().delete_item(
        Key={"email": email, "song_id": _song_id(artist, title, album)}
    )


def list_subscriptions(email: str) -> list[dict]:
    """Return the user's subscriptions, each with a fresh artist image URL."""
    resp = get_subscriptions_table().query(
        KeyConditionExpression=Key("email").eq(email)
    )
    out = []
    for item in resp.get("Items", []):
        out.append(
            {
                "artist": item["artist"],
                "title": item["title"],
                "album": item["album"],
                "image_url": presigned_image_url(item["artist"]),
            }
        )
    return out

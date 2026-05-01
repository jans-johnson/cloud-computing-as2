"""Subscription management — stored as a String Set on the login user.

Each membership token encodes the music table's composite key:
    artist|title|album

This keeps writes to one UpdateItem (atomic ADD/DELETE) and reads to one
GetItem on the user, then a BatchGet against the music table.
"""
from __future__ import annotations

from boto3.dynamodb.conditions import Key

from .db import get_login_table, get_music_table
from .storage import presigned_image_url

MEMBER_SEP = "|"


def _token(artist: str, title: str, album: str) -> str:
    return f"{artist}{MEMBER_SEP}{title}{MEMBER_SEP}{album}"


def _parse(token: str) -> tuple[str, str, str]:
    artist, title, album = token.split(MEMBER_SEP, 2)
    return artist, title, album


def add_subscription(email: str, artist: str, title: str, album: str) -> None:
    get_login_table().update_item(
        Key={"email": email},
        UpdateExpression="ADD subscriptions :s",
        ExpressionAttributeValues={":s": {_token(artist, title, album)}},
    )


def remove_subscription(email: str, artist: str, title: str, album: str) -> None:
    get_login_table().update_item(
        Key={"email": email},
        UpdateExpression="DELETE subscriptions :s",
        ExpressionAttributeValues={":s": {_token(artist, title, album)}},
    )


def list_subscriptions(email: str) -> list[dict]:
    """Return hydrated music items for the user, each with a fresh image URL."""
    user = get_login_table().get_item(Key={"email": email}).get("Item")
    if not user:
        return []
    tokens = user.get("subscriptions") or set()
    if not tokens:
        return []

    music = get_music_table()
    out = []
    for tok in tokens:
        artist, title, album = _parse(tok)
        resp = music.get_item(
            Key={"artist": artist, "title_album": f"{title}#{album}"}
        )
        item = resp.get("Item")
        if not item:
            continue
        item = dict(item)
        item["image_url"] = presigned_image_url(artist)
        out.append(item)
    return out

"""Music table operations.

Key schema (designed against 137-row dataset where (title, artist) is
NOT unique — Taylor Swift "Delicate" appears twice on different albums):

  PK = artist                          (71 distinct values, balanced)
  SK = title_album = f"{title}#{album}" (137 distinct → lossless import)

  LSI artist-year-index : SK = year     -> "Jimmy Buffett in 1974"
  GSI title-artist-index: PK=title, SK=artist -> title-only search

Queries that filter only on year or only on album fall back to Scan.
"""
from __future__ import annotations

import json
from pathlib import Path

from boto3.dynamodb.conditions import Key, Attr

from config import MUSIC_TITLE_GSI, MUSIC_YEAR_LSI
from .db import get_music_table

SEP = "#"


# --- Case-insensitive query support -------------------------------------
#
# DynamoDB key comparisons are byte-exact, so a marker typing
# "taylor swift" would miss the canonically-cased "Taylor Swift" row.
# We keep the strict key schema (Query on PK/GSI/LSI stays intact) and
# instead canonicalise user input at the application layer: the dataset
# domain is small and has no case/space collisions, so each lowercased
# value maps to exactly one stored value. Built once at import; on any
# failure we degrade to identity (queries still run, just case-sensitive).
_DATASET = Path(__file__).resolve().parents[1] / "data" / "2026a2_songs.json"


def _build_canonical_maps() -> dict[str, dict[str, str]]:
    maps = {"artist": {}, "title": {}, "album": {}}
    try:
        raw = json.loads(_DATASET.read_text(encoding="utf-8"))
        songs = raw["songs"] if isinstance(raw, dict) and "songs" in raw else raw
        for s in songs:
            for field in maps:
                val = str(s.get(field, "")).strip()
                if val:
                    maps[field].setdefault(val.lower(), val)
    except Exception:
        # Missing/unreadable dataset — fall back to case-sensitive behaviour
        # rather than breaking the endpoint.
        pass
    return maps


_CANONICAL = _build_canonical_maps()


def _canonical(field: str, value: str | None) -> str | None:
    """Resolve trimmed/cased user input to the stored canonical value.

    Unresolved input (genuinely absent, or a partial like "taylor") is
    returned trimmed as-is so the query still runs and correctly yields
    "No result is retrieved" — partial matching is intentionally not
    supported, per the brief.
    """
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    return _CANONICAL.get(field, {}).get(trimmed.lower(), trimmed)


def music_composite_sort_key(title: str, album: str) -> str:
    return f"{title}{SEP}{album}"


def put_song(song: dict) -> dict:
    """Insert one song. Caller passes raw fields from the JSON dataset."""
    item = {
        "artist": song["artist"],
        "title_album": music_composite_sort_key(song["title"], song["album"]),
        "title": song["title"],
        "album": song["album"],
        "year": str(song["year"]),
        "image_url": song.get("image_url") or song.get("img_url", ""),
    }
    get_music_table().put_item(Item=item)
    return item


def get_song(artist: str, title: str, album: str) -> dict | None:
    resp = get_music_table().get_item(
        Key={"artist": artist, "title_album": music_composite_sort_key(title, album)}
    )
    return resp.get("Item")


def delete_song(artist: str, title: str, album: str) -> None:
    get_music_table().delete_item(
        Key={"artist": artist, "title_album": music_composite_sort_key(title, album)}
    )


def query_music(
    *,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    year: str | None = None,
) -> list[dict]:
    """Pick the cheapest access path for the given filter combination.

    Decision tree:
      artist + (title|album|year) -> Query base table or LSI
      title only / title + artist -> Query GSI
      otherwise (year only, album only, no fields) -> Scan with FilterExpression
    """
    table = get_music_table()

    # Case-insensitive: resolve user input to the canonical stored value
    # before building the (byte-exact) key conditions. Applied centrally
    # here so all three backends inherit it.
    artist = _canonical("artist", artist)
    title = _canonical("title", title)
    album = _canonical("album", album)
    year = str(year).strip() if year is not None and str(year).strip() else None

    if artist:
        if year and not (title or album):
            resp = table.query(
                IndexName=MUSIC_YEAR_LSI,
                KeyConditionExpression=Key("artist").eq(artist) & Key("year").eq(year),
            )
            return resp.get("Items", [])

        kce = Key("artist").eq(artist)
        if title and album:
            kce = kce & Key("title_album").eq(music_composite_sort_key(title, album))
        elif title:
            kce = kce & Key("title_album").begins_with(f"{title}{SEP}")

        filters = []
        if year:
            filters.append(Attr("year").eq(year))
        if album and not title:
            filters.append(Attr("album").eq(album))

        kwargs = {"KeyConditionExpression": kce}
        if filters:
            expr = filters[0]
            for f in filters[1:]:
                expr = expr & f
            kwargs["FilterExpression"] = expr
        resp = table.query(**kwargs)
        return resp.get("Items", [])

    if title:
        kwargs = {
            "IndexName": MUSIC_TITLE_GSI,
            "KeyConditionExpression": Key("title").eq(title),
        }
        filters = []
        if album:
            filters.append(Attr("album").eq(album))
        if year:
            filters.append(Attr("year").eq(year))
        if filters:
            expr = filters[0]
            for f in filters[1:]:
                expr = expr & f
            kwargs["FilterExpression"] = expr
        resp = table.query(**kwargs)
        return resp.get("Items", [])

    return scan_music(album=album, year=year)


def scan_music(*, album: str | None = None, year: str | None = None) -> list[dict]:
    """Used when no PK is known — last resort. Required by the brief."""
    filters = []
    if album:
        filters.append(Attr("album").eq(album))
    if year:
        filters.append(Attr("year").eq(str(year)))

    kwargs = {}
    if filters:
        expr = filters[0]
        for f in filters[1:]:
            expr = expr & f
        kwargs["FilterExpression"] = expr

    items, last = [], None
    while True:
        if last:
            kwargs["ExclusiveStartKey"] = last
        resp = get_music_table().scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            return items

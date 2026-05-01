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

from boto3.dynamodb.conditions import Key, Attr

from config import MUSIC_TITLE_GSI, MUSIC_YEAR_LSI
from .db import get_music_table

SEP = "#"


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
    year = str(year) if year is not None else None

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

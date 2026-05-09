"""Confirm the music table is a lossless image of 2026a2_songs.json.

Compares the set of (artist, title, album) triples in the table against
the set in the JSON dataset. Reports counts, missing rows, and unexpected
extras. Exits non-zero if anything is off — handy for CI or a demo check.
"""
import _bootstrap  # noqa: F401

import json
import os
import sys
from collections import Counter

from config import MUSIC_TABLE
from core.db import get_dynamodb

DATASET = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "2026a2_songs.json",
)


def scan_all_items(table) -> list[dict]:
    items, last = [], None
    while True:
        kwargs = {"ExclusiveStartKey": last} if last else {}
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            return items


def main() -> int:
    with open(DATASET) as f:
        songs = json.load(f)["songs"]
    json_keys = Counter((s["artist"], s["title"], s["album"]) for s in songs)
    print(f"JSON:  {len(songs)} rows, {len(json_keys)} unique (artist,title,album)")

    table = get_dynamodb().Table(MUSIC_TABLE)
    items = scan_all_items(table)
    table_keys = Counter((i["artist"], i["title"], i["album"]) for i in items)
    print(f"Table: {len(items)} items, {len(table_keys)} unique (artist,title,album)")

    missing = set(json_keys) - set(table_keys)
    extra = set(table_keys) - set(json_keys)

    if missing:
        print(f"\nFAIL — {len(missing)} rows from JSON missing in table:")
        for k in sorted(missing)[:10]:
            print(f"  {k}")
    if extra:
        print(f"\nFAIL — {len(extra)} unexpected items in table:")
        for k in sorted(extra)[:10]:
            print(f"  {k}")

    if not missing and not extra and len(items) == len(songs):
        print("\nPASS — table is a lossless image of the JSON dataset.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

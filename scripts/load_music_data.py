"""Task 3 of the brief: load 2026a2_songs.json into the music table.

Pre-flight check verifies (artist, title, album) is unique across the
raw dataset before any writes — guarantees lossless import. Writes go
through batch_writer for throughput.
"""
import _bootstrap  # noqa: F401

import json
import os
from collections import Counter

from config import MUSIC_TABLE
from core.db import get_dynamodb
from core.music import music_composite_sort_key

DATASET = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "2026a2_songs.json",
)


def load_dataset() -> list[dict]:
    with open(DATASET) as f:
        return json.load(f)["songs"]


def assert_lossless(songs: list[dict]) -> None:
    keys = [(s["artist"], s["title"], s["album"]) for s in songs]
    dupes = [k for k, c in Counter(keys).items() if c > 1]
    if dupes:
        raise SystemExit(
            "Refusing to import: composite key (artist,title,album) is not "
            f"unique. {len(dupes)} duplicate(s): {dupes[:3]}..."
        )
    print(f"Pre-flight OK: {len(songs)} songs, all (artist,title,album) unique")


def to_item(song: dict) -> dict:
    # Spec calls the attribute image_url; dataset field is img_url.
    return {
        "artist": song["artist"],
        "title_album": music_composite_sort_key(song["title"], song["album"]),
        "title": song["title"],
        "album": song["album"],
        "year": str(song["year"]),
        "image_url": song.get("img_url") or song.get("image_url", ""),
    }


def import_songs():
    songs = load_dataset()
    assert_lossless(songs)
    table = get_dynamodb().Table(MUSIC_TABLE)
    n = 0
    with table.batch_writer() as bw:
        for s in songs:
            bw.put_item(Item=to_item(s))
            n += 1
    print(f"Imported {n} songs into {MUSIC_TABLE}")


if __name__ == "__main__":
    import_songs()

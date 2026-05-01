"""Task 2 of the brief: create the music table with GSI + LSI.

Schema rationale (see core/music.py):
  PK = artist
  SK = title_album = "<title>#<album>"  (composite ensures lossless import
                                          across the 4 (title,artist) dupes
                                          in the dataset)
  LSI artist-year-index : SK = year   — "all songs by X in 1974"
  GSI title-artist-index: PK=title, SK=artist — title-only search
"""
import _bootstrap  # noqa: F401

from botocore.exceptions import ClientError

from config import MUSIC_TABLE, MUSIC_TITLE_GSI, MUSIC_YEAR_LSI
from core.db import get_dynamodb


def create_table():
    client = get_dynamodb().meta.client
    try:
        client.describe_table(TableName=MUSIC_TABLE)
        print(f"Table {MUSIC_TABLE!r} already exists — skipping create")
        return
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    client.create_table(
        TableName=MUSIC_TABLE,
        AttributeDefinitions=[
            {"AttributeName": "artist", "AttributeType": "S"},
            {"AttributeName": "title_album", "AttributeType": "S"},
            {"AttributeName": "title", "AttributeType": "S"},
            {"AttributeName": "year", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "artist", "KeyType": "HASH"},
            {"AttributeName": "title_album", "KeyType": "RANGE"},
        ],
        LocalSecondaryIndexes=[
            {
                "IndexName": MUSIC_YEAR_LSI,
                "KeySchema": [
                    {"AttributeName": "artist", "KeyType": "HASH"},
                    {"AttributeName": "year", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": MUSIC_TITLE_GSI,
                "KeySchema": [
                    {"AttributeName": "title", "KeyType": "HASH"},
                    {"AttributeName": "artist", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print(f"Creating {MUSIC_TABLE} (with LSI + GSI) ...", end="", flush=True)
    client.get_waiter("table_exists").wait(TableName=MUSIC_TABLE)
    print(" done")


if __name__ == "__main__":
    create_table()

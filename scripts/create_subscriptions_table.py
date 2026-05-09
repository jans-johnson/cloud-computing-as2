"""Create the subscriptions table.

Schema rationale (see ASSIGNMENT_GUIDE.md §A.4):
  PK = email                                — partition by user; one user's
                                               subscriptions live in one
                                               partition, so listing them is
                                               a single Query.
  SK = song_id = "<artist>#<title>#<album>" — matches the music base table's
                                               composite uniqueness exactly.

  GSI song-index : PK=song_id, SK=email     — reverse lookup ("who is
                                               subscribed to song X?") in
                                               one Query, no Scan.

We denormalise the song fields (artist, title, album) into each subscription
item so listing a user's subs is one round-trip — no BatchGet against music
on the hot path. The write-time duplication is the standard NoSQL trade-off.
"""
import _bootstrap  # noqa: F401

from botocore.exceptions import ClientError

from config import SUBSCRIPTIONS_SONG_GSI, SUBSCRIPTIONS_TABLE
from core.db import get_dynamodb


def create_table():
    client = get_dynamodb().meta.client
    try:
        client.describe_table(TableName=SUBSCRIPTIONS_TABLE)
        print(f"Table {SUBSCRIPTIONS_TABLE!r} already exists — skipping create")
        return
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    client.create_table(
        TableName=SUBSCRIPTIONS_TABLE,
        AttributeDefinitions=[
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "song_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "email", "KeyType": "HASH"},
            {"AttributeName": "song_id", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": SUBSCRIPTIONS_SONG_GSI,
                "KeySchema": [
                    {"AttributeName": "song_id", "KeyType": "HASH"},
                    {"AttributeName": "email", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print(f"Creating {SUBSCRIPTIONS_TABLE} (with GSI) ...", end="", flush=True)
    client.get_waiter("table_exists").wait(TableName=SUBSCRIPTIONS_TABLE)
    print(" done")


if __name__ == "__main__":
    create_table()

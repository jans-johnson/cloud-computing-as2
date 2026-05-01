"""Task 1 of the brief: create the login table and seed 10 users.

Replace STUDENT_ID and FIRST/LAST when running for your own marker. The
seed pattern follows the spec: s3######N@student.rmit.edu.au and
FirstnameLastnameN with password 0123450 + N.
"""
import _bootstrap  # noqa: F401

import time

from botocore.exceptions import ClientError

from config import AWS_REGION, LOGIN_TABLE
from core.db import get_dynamodb

STUDENT_ID = "3911111"
FIRST_NAME = "Jaans"
LAST_NAME = "Johnson"


def seed_users() -> list[dict]:
    users = []
    for n in range(10):
        # Spec example: password "012345" for N=0, "123456" for N=1, ...
        password = "".join(str((i + n) % 10) for i in range(6))
        users.append(
            {
                "email": f"s{STUDENT_ID[:-1]}{n}@student.rmit.edu.au",
                "user_name": f"{FIRST_NAME}{LAST_NAME}{n}",
                "password": password,
            }
        )
    return users


def create_table():
    client = get_dynamodb().meta.client
    try:
        client.describe_table(TableName=LOGIN_TABLE)
        print(f"Table {LOGIN_TABLE!r} already exists — skipping create")
        return
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    client.create_table(
        TableName=LOGIN_TABLE,
        AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )
    print(f"Creating {LOGIN_TABLE} ...", end="", flush=True)
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=LOGIN_TABLE)
    print(" done")


def populate():
    table = get_dynamodb().Table(LOGIN_TABLE)
    with table.batch_writer() as bw:
        for u in seed_users():
            bw.put_item(Item=u)
    print(f"Inserted {len(seed_users())} seed users into {LOGIN_TABLE}")


if __name__ == "__main__":
    print(f"Region: {AWS_REGION}")
    create_table()
    # Small pause; new table can be visible to describe before fully ready
    time.sleep(2)
    populate()

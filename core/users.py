"""Login table CRUD.

Schema: PK=email (string). Plaintext passwords as the brief allows for
this assignment only — production would salt+hash with bcrypt/argon2.
Subscriptions live as a String Set on the same item to avoid a third
table while keeping reads to one GetItem.
"""
from botocore.exceptions import ClientError

from .db import get_login_table


class UserExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def create_user(email: str, user_name: str, password: str) -> dict:
    item = {"email": email, "user_name": user_name, "password": password}
    try:
        get_login_table().put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(email)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise UserExistsError(email) from exc
        raise
    return item


def get_user(email: str) -> dict | None:
    resp = get_login_table().get_item(Key={"email": email})
    return resp.get("Item")


def authenticate(email: str, password: str) -> dict:
    user = get_user(email)
    if not user or user.get("password") != password:
        raise InvalidCredentialsError()
    return {"email": user["email"], "user_name": user["user_name"]}

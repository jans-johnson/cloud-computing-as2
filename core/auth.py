"""Stateless session tokens for the Lambda backend.

Flask's built-in session cookie covers EC2/ECS. Lambda is stateless, so
we issue a signed token (itsdangerous) carrying the user's email + name.
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config import SESSION_SECRET, SESSION_TTL_SECONDS


class TokenError(Exception):
    pass


def _serializer():
    return URLSafeTimedSerializer(SESSION_SECRET, salt="music-app-session")


def issue_token(email: str, user_name: str) -> str:
    return _serializer().dumps({"email": email, "user_name": user_name})


def verify_token(token: str) -> dict:
    try:
        return _serializer().loads(token, max_age=SESSION_TTL_SECONDS)
    except SignatureExpired as exc:
        raise TokenError("session expired") from exc
    except BadSignature as exc:
        raise TokenError("invalid session") from exc

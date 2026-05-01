"""Stateless session tokens — stdlib only (HMAC-SHA256 over JSON payload).

Avoids any third-party deps so the Lambda package can ship as raw source
without a build step. Flask's signed-cookie session still uses itsdangerous
internally; that's fine because Flask bundles it transitively.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from config import SESSION_SECRET, SESSION_TTL_SECONDS


class TokenError(Exception):
    pass


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(payload: bytes) -> str:
    sig = hmac.new(SESSION_SECRET.encode("utf-8"), payload, hashlib.sha256).digest()
    return _b64e(sig)


def issue_token(email: str, user_name: str) -> str:
    body = json.dumps(
        {"email": email, "user_name": user_name, "iat": int(time.time())},
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{_b64e(body)}.{_sign(body)}"


def verify_token(token: str) -> dict:
    try:
        body_b64, sig = token.split(".", 1)
    except ValueError as exc:
        raise TokenError("malformed token") from exc

    try:
        body = _b64d(body_b64)
    except Exception as exc:
        raise TokenError("malformed token") from exc

    if not hmac.compare_digest(_sign(body), sig):
        raise TokenError("bad signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TokenError("malformed payload") from exc

    if int(time.time()) - int(payload.get("iat", 0)) > SESSION_TTL_SECONDS:
        raise TokenError("session expired")

    return {"email": payload["email"], "user_name": payload["user_name"]}

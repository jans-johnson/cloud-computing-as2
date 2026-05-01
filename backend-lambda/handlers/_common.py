"""Shared helpers for the Lambda handlers.

All handlers are invoked by API Gateway (REST proxy integration) and
return the standard {statusCode, headers, body} dict. Auth uses the
signed token from core.auth so the function can stay stateless across
invocations.
"""
import json
import os

from core.auth import TokenError, verify_token

CORS_HEADERS = {
    "Access-Control-Allow-Origin": os.environ.get("FRONTEND_ORIGIN", "*"),
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Content-Type": "application/json",
}


def respond(status: int, body: dict | list | None = None) -> dict:
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(body) if body is not None else "",
    }


def parse_body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}


def http_method(event: dict) -> str:
    # REST API exposes httpMethod; HTTP API uses requestContext.http.method.
    return (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or "GET"
    ).upper()


def authed_user(event: dict) -> dict | None:
    headers = event.get("headers") or {}
    # API Gateway lower-cases header names in HTTP API but not REST.
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if not auth.startswith("Bearer "):
        return None
    try:
        return verify_token(auth.split(" ", 1)[1])
    except TokenError:
        return None

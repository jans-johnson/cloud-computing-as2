"""Subscriptions Lambda — proper REST verbs on /subscriptions:

  GET    list current user's subscriptions
  POST   add { artist, title, album }
  DELETE remove { artist, title, album }
"""
from core.subscriptions import (
    add_subscription,
    list_subscriptions,
    remove_subscription,
)

from ._common import authed_user, http_method, parse_body, respond


def handler(event, _context):
    method = http_method(event)
    if method == "OPTIONS":
        return respond(204)

    user = authed_user(event)
    if not user:
        return respond(401, {"error": "not authenticated"})

    if method == "GET":
        return respond(200, {"items": list_subscriptions(user["email"])})

    body = parse_body(event)
    artist = body.get("artist")
    title = body.get("title")
    album = body.get("album")
    if not (artist and title and album):
        return respond(400, {"error": "artist, title, album required"})

    if method == "POST":
        add_subscription(user["email"], artist, title, album)
        return respond(201, {"ok": True})
    if method == "DELETE":
        remove_subscription(user["email"], artist, title, album)
        return respond(200, {"ok": True})

    return respond(405, {"error": "method not allowed"})

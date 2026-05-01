"""Music Lambda — bound to GET /music.

Filter combinations exercise both Query (preferred) and Scan (fallback)
on the music table.
"""
from core.music import query_music
from core.storage import presigned_image_url

from ._common import authed_user, http_method, query_params, respond


def handler(event, _context):
    method = http_method(event)
    if method == "OPTIONS":
        return respond(204)
    if method != "GET":
        return respond(405, {"error": "method not allowed"})

    if not authed_user(event):
        return respond(401, {"error": "not authenticated"})

    qp = query_params(event)
    title = (qp.get("title") or "").strip() or None
    artist = (qp.get("artist") or "").strip() or None
    album = (qp.get("album") or "").strip() or None
    year = (qp.get("year") or "").strip() or None
    if not any([title, artist, album, year]):
        return respond(400, {"error": "provide at least one of title/artist/album/year"})

    items = query_music(title=title, artist=artist, album=album, year=year)
    for it in items:
        it["image_url"] = presigned_image_url(it["artist"])
    return respond(200, {"items": items})

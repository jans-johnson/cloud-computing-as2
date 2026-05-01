"""Flask backend used for both EC2 and ECS deployments.

The same module is consumed by the ECS Dockerfile (mounted at the repo
root), so the application code is identical across the two compute
choices — they differ only in how they are run and scaled.

Session strategy: Flask's signed-cookie session. The `Authorization`
header is also accepted so the same endpoints can be hit from a
static frontend that prefers a token over cookies.
"""
from __future__ import annotations

import os
import sys

# Allow running from the repo root or from inside backend-ec2/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from functools import wraps

from flask import Flask, jsonify, request, session

from config import SESSION_SECRET
from core.auth import issue_token, verify_token, TokenError
from core.music import query_music
from core.storage import presigned_image_url
from core.subscriptions import (
    add_subscription,
    list_subscriptions,
    remove_subscription,
)
from core.users import (
    InvalidCredentialsError,
    UserExistsError,
    authenticate,
    create_user,
    get_user,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = SESSION_SECRET
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

    # The static frontend is served from a different origin (S3/CloudFront),
    # so we allow that origin and the bearer-token flow. Cookies are not
    # used cross-origin; the frontend authenticates via the issued JWT.
    allowed_origin = os.environ.get("FRONTEND_ORIGIN", "*")

    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = allowed_origin
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return resp

    @app.route("/api/<path:_>", methods=["OPTIONS"])
    def cors_preflight(_):
        return ("", 204)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.post("/api/login")
    def login():
        body = request.get_json(silent=True) or {}
        email = (body.get("email") or "").strip()
        password = body.get("password") or ""
        try:
            user = authenticate(email, password)
        except InvalidCredentialsError:
            return jsonify(error="email or password is invalid"), 401
        session["email"] = user["email"]
        session["user_name"] = user["user_name"]
        return jsonify(user_name=user["user_name"], token=issue_token(**user))

    @app.post("/api/register")
    def register():
        body = request.get_json(silent=True) or {}
        email = (body.get("email") or "").strip()
        user_name = (body.get("user_name") or body.get("username") or "").strip()
        password = body.get("password") or ""
        if not (email and user_name and password):
            return jsonify(error="email, user_name, and password are required"), 400
        try:
            create_user(email, user_name, password)
        except UserExistsError:
            return jsonify(error="The email already exists"), 409
        return jsonify(ok=True), 201

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    def current_user() -> dict | None:
        if session.get("email"):
            return {"email": session["email"], "user_name": session.get("user_name")}
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                return verify_token(auth.split(" ", 1)[1])
            except TokenError:
                return None
        return None

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify(error="not authenticated"), 401
            request.user = user  # type: ignore[attr-defined]
            return fn(*args, **kwargs)

        return wrapper

    @app.get("/api/me")
    def me():
        user = current_user()
        if not user:
            return jsonify(error="not authenticated"), 401
        return jsonify(user)

    @app.get("/api/music")
    @login_required
    def search_music():
        title = request.args.get("title") or None
        artist = request.args.get("artist") or None
        album = request.args.get("album") or None
        year = request.args.get("year") or None
        if not any([title, artist, album, year]):
            return jsonify(error="provide at least one of title/artist/album/year"), 400

        items = query_music(title=title, artist=artist, album=album, year=year)
        for it in items:
            it["image_url"] = presigned_image_url(it["artist"])
        return jsonify(items=items)

    @app.get("/api/subscriptions")
    @login_required
    def get_subs():
        return jsonify(items=list_subscriptions(request.user["email"]))

    @app.post("/api/subscriptions")
    @login_required
    def add_sub():
        body = request.get_json(silent=True) or {}
        artist, title, album = body.get("artist"), body.get("title"), body.get("album")
        if not (artist and title and album):
            return jsonify(error="artist, title, album required"), 400
        if not get_user(request.user["email"]):
            return jsonify(error="user no longer exists"), 401
        add_subscription(request.user["email"], artist, title, album)
        return jsonify(ok=True), 201

    @app.delete("/api/subscriptions")
    @login_required
    def remove_sub():
        body = request.get_json(silent=True) or {}
        artist, title, album = body.get("artist"), body.get("title"), body.get("album")
        if not (artist and title and album):
            return jsonify(error="artist, title, album required"), 400
        remove_subscription(request.user["email"], artist, title, album)
        return jsonify(ok=True)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

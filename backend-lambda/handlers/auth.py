"""Auth Lambda — bound at API Gateway as:

  POST /login
  POST /register
  POST /logout
  GET  /me

The handler dispatches on (resource, httpMethod) so a single function
serves all four routes; API Gateway still enforces the method, so the
API remains genuinely RESTful (GET vs POST are not interchangeable).
"""
from core.users import (
    InvalidCredentialsError,
    UserExistsError,
    authenticate,
    create_user,
)
from core.auth import issue_token

from ._common import authed_user, http_method, parse_body, respond


def _login(event):
    body = parse_body(event)
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    try:
        user = authenticate(email, password)
    except InvalidCredentialsError:
        return respond(401, {"error": "email or password is invalid"})
    return respond(200, {"user_name": user["user_name"], "token": issue_token(**user)})


def _register(event):
    body = parse_body(event)
    email = (body.get("email") or "").strip()
    user_name = (body.get("user_name") or body.get("username") or "").strip()
    password = body.get("password") or ""
    if not (email and user_name and password):
        return respond(400, {"error": "email, user_name, and password are required"})
    try:
        create_user(email, user_name, password)
    except UserExistsError:
        return respond(409, {"error": "The email already exists"})
    return respond(201, {"ok": True})


def _logout(_event):
    # Stateless tokens — client just drops it. No revocation list.
    return respond(200, {"ok": True})


def _me(event):
    user = authed_user(event)
    if not user:
        return respond(401, {"error": "not authenticated"})
    return respond(200, user)


def handler(event, _context):
    method = http_method(event)
    resource = (event.get("resource") or event.get("rawPath") or "").rstrip("/")

    if method == "OPTIONS":
        return respond(204)

    routes = {
        ("POST", "/api/login"): _login,
        ("POST", "/api/register"): _register,
        ("POST", "/api/logout"): _logout,
        ("GET", "/api/me"): _me,
    }
    fn = routes.get((method, resource))
    if not fn:
        return respond(404, {"error": f"no route for {method} {resource}"})
    return fn(event)

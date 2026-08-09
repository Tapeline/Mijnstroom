from datetime import datetime, timedelta, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from litestar import Request
from litestar.connection import ASGIConnection
from litestar.middleware import AbstractMiddleware
from litestar.response.base import ASGIResponse
from litestar.response.redirect import ASGIRedirectResponse
from litestar.types import ASGIApp, Receive, Scope, Send
from litestar.response import Response

from mijnstroom.config import Config

SESSION_COOKIE_NAME = "mijnstroom_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


def create_session_token(secret: str) -> str:
    """Create a signed session token."""
    serializer = URLSafeTimedSerializer(secret)
    return serializer.dumps({"auth": True})


def validate_session_token(token: str, secret: str, max_age: int = SESSION_MAX_AGE_SECONDS) -> bool:
    """Validate a session token. Returns True if valid, False otherwise."""
    serializer = URLSafeTimedSerializer(secret)
    try:
        serializer.loads(token, max_age=max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False


_EXCLUDED_PATHS = (
    "/login",
    "/api/auth/login",
    "/api/auth/logout",
    "/vendored/",
    "/js/",
)


class AuthMiddleware(AbstractMiddleware):
    """Middleware that enforces session-based authentication."""

    scopes = {"http"}

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)
        path = request.url.path

        # Allow excluded paths through without auth
        if any(path.startswith(excluded) for excluded in _EXCLUDED_PATHS):
            await self.app(scope, receive, send)
            return

        # Get config from app state
        config: Config = request.app.state.container.config

        # Check for valid session cookie
        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        if session_token and validate_session_token(session_token, config.security.secret):
            await self.app(scope, receive, send)
            return

        # Also accept Authorization: Bearer <token> header (for mobile apps)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if validate_session_token(token, config.security.secret):
                await self.app(scope, receive, send)
                return

        # No valid session - reject API requests with 401, redirect others to login
        if path.startswith("/api/"):
            # response = Response(
            #     content={"error": "Authentication required"},
            #     status_code=401,
            # )
            # await response(scope, receive, send)
            await ASGIResponse(
                body=b'{"error": "Authentication required"}',
                status_code=401,
                headers={"Content-Type": "application/json"},
            )(scope, receive, send)
        elif not path.startswith("/login"):
            await ASGIRedirectResponse(
                "/login.html"
            )(scope, receive, send)
            # response = Response(
            #     content=None,
            #     status_code=302,
            #     headers={"Location": "/login"},
            # ).to_asgi_response()
            # await response(scope, receive, send)

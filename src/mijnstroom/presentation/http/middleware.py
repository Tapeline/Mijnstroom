from dishka import AsyncContainer
from litestar.types import ASGIApp, Receive, Scope, Send

from mijnstroom.bootstrap.config import Config, OIDCConfig
from mijnstroom.infrastructure.auth.session import SESSION_COOKIE_NAME, SessionCodec

_PUBLIC_PREFIXES: tuple[str, ...] = ("/auth/", "/static/", "/healthz")


def _is_public(path: str) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def _parse_cookies(scope: Scope) -> dict[str, str]:
    headers = scope.get("headers") or []
    cookie_header = b""
    for name, value in headers:
        if name == b"cookie":
            cookie_header = value
            break
    if not cookie_header:
        return {}
    pairs: dict[str, str] = {}
    for chunk in cookie_header.decode("latin-1").split(";"):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            pairs[k.strip()] = v.strip()
    return pairs


def auth_middleware(app: ASGIApp) -> ASGIApp:
    """Plain ASGI middleware wrapping the entire app.

    Runs *before* Litestar's routing/exception middleware so unauth
    requests for unknown paths are still redirected to login.

    When ``auth_enabled`` is False in config, all requests are allowed
    through without authentication (guest mode).
    """

    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # type: ignore[comparison-overlap]
            await app(scope, receive, send)
            return
        path = scope.get("path", "/")
        if _is_public(path):
            await app(scope, receive, send)
            return

        container: AsyncContainer = scope["app"].state.dishka_container
        async with container() as request_container:
            config = await request_container.get(Config)

        # If auth is disabled, allow all requests through.
        if not config.auth_enabled:
            await app(scope, receive, send)
            return

        async with container() as request_container:
            codec = await request_container.get(SessionCodec)
            oidc_config = await request_container.get(OIDCConfig)

        cookies = _parse_cookies(scope)
        raw = cookies.get(SESSION_COOKIE_NAME)
        authenticated = False
        if raw:
            data = codec.decode(raw)
            if data.sub and (not oidc_config.allowed_sub or data.sub == oidc_config.allowed_sub):
                authenticated = True

        if authenticated:
            await app(scope, receive, send)
            return

        await send(
            {
                "type": "http.response.start",
                "status": 303,
                "headers": [
                    (b"location", b"/auth/login"),
                    (b"content-length", b"0"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    return middleware

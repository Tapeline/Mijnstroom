from dataclasses import dataclass

from litestar import Request, Response, Router, post
from litestar.di import Provide

from mijnstroom.config import Config
from mijnstroom.http.security import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
)


@dataclass
class LoginRequest:
    password: str


@post("/login")
async def login(request: Request, data: LoginRequest) -> Response:
    """Authenticate with instance password. Accepts JSON body: {"password": "..."}"""
    config: Config = request.app.state.container.config
    if data.password != config.security.password:
        return Response(
            content={"error": "Invalid password"},
            status_code=401,
        )

    token = create_session_token(config.security.secret)
    response = Response(
        content={"ok": True, "token": token},
        headers={"Set-Cookie": f"{SESSION_COOKIE_NAME}={token}; MaxAge={SESSION_MAX_AGE_SECONDS}; Path=/; Secure"},
        status_code=200,
    )
    return response


@post("/logout")
async def logout() -> Response:
    """Clear session cookie."""
    response = Response(content={"ok": True}, status_code=200)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


auth_router = Router(
    path="/api/auth",
    route_handlers=[login, logout],
)

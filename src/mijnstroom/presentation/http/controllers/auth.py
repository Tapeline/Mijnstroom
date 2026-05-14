from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, Response, get
from litestar.response import Redirect

from mijnstroom.bootstrap.config import OIDCConfig
from mijnstroom.common.errors import Forbidden, Unauthenticated
from mijnstroom.infrastructure.auth.oidc_client import OIDCClient
from mijnstroom.infrastructure.auth.session import (
    SESSION_COOKIE_NAME,
    SessionCodec,
    SessionData,
)


def _set_session(response: Response[object], codec: SessionCodec, data: SessionData) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=codec.encode(data),
        httponly=True,
        samesite="lax",
        path="/",
    )


def _clear_session(response: Response[object]) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


class AuthController(Controller):
    path = "/auth"

    @get("/login")
    @inject
    async def login(
        self,
        request: Request,  # type: ignore[type-arg]
        oidc: FromDishka[OIDCClient],
        codec: FromDishka[SessionCodec],
    ) -> Response[object]:
        # If already logged in, send the user home.
        existing = request.cookies.get(SESSION_COOKIE_NAME)
        if existing:
            data = codec.decode(existing)
            if data.sub:
                return Redirect(path="/")

        url, pending = await oidc.begin()
        response = Redirect(path=url)
        _set_session(
            response,
            codec,
            SessionData(
                sub=None,
                pending_state=pending.state,
                pending_nonce=pending.nonce,
                pending_pkce_verifier=pending.pkce_verifier,
            ),
        )
        return response

    @get("/callback")
    @inject
    async def callback(
        self,
        request: Request,  # type: ignore[type-arg]
        oidc: FromDishka[OIDCClient],
        codec: FromDishka[SessionCodec],
        config: FromDishka[OIDCConfig],
    ) -> Response[object]:
        params = request.query_params
        code = params.get("code")
        state = params.get("state")
        if not code or not state:
            raise Unauthenticated("Missing code or state")

        raw = request.cookies.get(SESSION_COOKIE_NAME)
        if not raw:
            raise Unauthenticated("Missing session cookie")
        data = codec.decode(raw)
        if (
            not data.pending_state
            or not data.pending_nonce
            or not data.pending_pkce_verifier
        ):
            raise Unauthenticated("No pending auth request")
        if state != data.pending_state:
            raise Unauthenticated("State mismatch")

        from mijnstroom.infrastructure.auth.oidc_client import AuthRequest

        pending = AuthRequest(
            state=data.pending_state,
            nonce=data.pending_nonce,
            pkce_verifier=data.pending_pkce_verifier,
        )
        id_token = await oidc.exchange(code, pending)
        if not oidc.is_allowed(id_token.sub):
            raise Forbidden(f"Subject {id_token.sub} is not allowed")

        response = Redirect(path="/")
        _set_session(response, codec, SessionData(sub=id_token.sub))
        return response

    @get("/logout")
    async def logout(self) -> Response[object]:
        response = Redirect(path="/auth/login")
        _clear_session(response)
        return response

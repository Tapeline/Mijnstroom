from litestar import Request

from mijnstroom.application.interfaces.idp import UserId, UserIdProvider
from mijnstroom.bootstrap.config import OIDCConfig
from mijnstroom.common.errors import Unauthenticated
from mijnstroom.infrastructure.auth.session import SESSION_COOKIE_NAME, SessionCodec


class SessionIdProvider(UserIdProvider):
    """Reads the current user's subject from the signed session cookie."""

    __slots__ = ("_codec", "_oidc", "_request")

    def __init__(self, request: Request, codec: SessionCodec, oidc: OIDCConfig) -> None:  # type: ignore[type-arg]
        self._request = request
        self._codec = codec
        self._oidc = oidc

    async def current_user(self) -> UserId | None:
        raw = self._request.cookies.get(SESSION_COOKIE_NAME)
        if not raw:
            return None
        data = self._codec.decode(raw)
        if not data.sub:
            return None
        if self._oidc.allowed_sub and data.sub != self._oidc.allowed_sub:
            return None
        return UserId(data.sub)

    async def require_user(self) -> UserId:
        user = await self.current_user()
        if user is None:
            raise Unauthenticated("Authentication required")
        return user


class SystemUserIdProvider(UserIdProvider):
    """Identity provider used in worker scope: always returns the configured user."""

    __slots__ = ("_user",)

    def __init__(self, oidc: OIDCConfig) -> None:
        self._user = UserId(oidc.allowed_sub or "system")

    async def current_user(self) -> UserId | None:
        return self._user

    async def require_user(self) -> UserId:
        return self._user

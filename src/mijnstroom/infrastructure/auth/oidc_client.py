import logging
import secrets
from dataclasses import dataclass

import httpx
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from mijnstroom.bootstrap.config import OIDCConfig
from mijnstroom.common.errors import AppError, Unauthenticated

logger = logging.getLogger(__name__)


class OIDCConfigurationError(AppError):
    """The OIDC configuration could not be loaded from the issuer."""


@dataclass(slots=True)
class OIDCEndpoints:
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    issuer: str


@dataclass(slots=True)
class AuthRequest:
    """A pending authorization request awaiting callback."""

    state: str
    nonce: str
    pkce_verifier: str


@dataclass(slots=True)
class IdToken:
    sub: str
    raw: str
    claims: dict[str, object]


def _b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _pkce_pair() -> tuple[str, str]:
    import hashlib

    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


class OIDCClient:
    """Authelia OIDC code-flow client."""

    def __init__(self, config: OIDCConfig) -> None:
        self._config = config
        self._endpoints: OIDCEndpoints | None = None
        self._jwks: KeySet | None = None

    @property
    def config(self) -> OIDCConfig:
        return self._config

    async def _discover(self) -> OIDCEndpoints:
        if self._endpoints is not None:
            return self._endpoints
        url = self._config.issuer.rstrip("/") + "/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
        if response.status_code != 200:
            raise OIDCConfigurationError(
                f"Failed to fetch OIDC discovery from {url}: HTTP {response.status_code}"
            )
        data = response.json()
        self._endpoints = OIDCEndpoints(
            authorization_endpoint=data["authorization_endpoint"],
            token_endpoint=data["token_endpoint"],
            jwks_uri=data["jwks_uri"],
            issuer=data.get("issuer", self._config.issuer),
        )
        return self._endpoints

    async def _jwks_keys(self) -> KeySet:
        if self._jwks is not None:
            return self._jwks
        endpoints = await self._discover()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoints.jwks_uri)
        if response.status_code != 200:
            raise OIDCConfigurationError(
                f"Failed to fetch JWKS from {endpoints.jwks_uri}: HTTP {response.status_code}"
            )
        self._jwks = KeySet.import_key_set(response.json())
        return self._jwks

    async def begin(self) -> tuple[str, AuthRequest]:
        """Build an authorization URL plus the matching pending request."""
        endpoints = await self._discover()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier, challenge = _pkce_pair()
        params = {
            "response_type": "code",
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = endpoints.authorization_endpoint + "?" + str(httpx.QueryParams(params))
        return url, AuthRequest(state=state, nonce=nonce, pkce_verifier=verifier)

    async def exchange(self, code: str, request: AuthRequest) -> IdToken:
        """Exchange ``code`` for tokens and return the verified id token."""
        endpoints = await self._discover()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._config.redirect_uri,
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "code_verifier": request.pkce_verifier,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(endpoints.token_endpoint, data=data)
        if response.status_code != 200:
            logger.warning("Token exchange failed: %s %s", response.status_code, response.text)
            raise Unauthenticated("Token exchange failed")
        payload = response.json()
        id_token = payload.get("id_token")
        if not id_token:
            raise Unauthenticated("No id_token returned from issuer")
        keys = await self._jwks_keys()
        try:
            decoded = jwt.decode(id_token, keys)
        except JoseError as exc:  # pragma: no cover - defensive
            raise Unauthenticated(f"id_token validation failed: {exc}") from exc
        claims = dict(decoded.claims)
        sub = str(claims.get("sub", ""))
        if not sub:
            raise Unauthenticated("id_token missing sub claim")
        if claims.get("nonce") != request.nonce:
            raise Unauthenticated("id_token nonce mismatch")
        return IdToken(sub=sub, raw=id_token, claims=claims)

    def is_allowed(self, sub: str) -> bool:
        return bool(self._config.allowed_sub) and sub == self._config.allowed_sub

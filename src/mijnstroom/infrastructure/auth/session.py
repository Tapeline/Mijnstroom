import json
from dataclasses import dataclass

from itsdangerous import BadSignature, URLSafeSerializer

from mijnstroom.bootstrap.config import SessionConfig

SESSION_COOKIE_NAME = "mijnstroom_session"


@dataclass(slots=True)
class SessionData:
    sub: str | None = None
    pending_state: str | None = None
    pending_nonce: str | None = None
    pending_pkce_verifier: str | None = None


class SessionCodec:
    """Encodes/decodes a :class:`SessionData` to and from a signed cookie."""

    def __init__(self, config: SessionConfig) -> None:
        self._serializer = URLSafeSerializer(config.secret, salt="mijnstroom-session")

    def encode(self, data: SessionData) -> str:
        payload = {
            "sub": data.sub,
            "pending_state": data.pending_state,
            "pending_nonce": data.pending_nonce,
            "pending_pkce_verifier": data.pending_pkce_verifier,
        }
        return self._serializer.dumps(json.dumps(payload))

    def decode(self, raw: str) -> SessionData:
        try:
            payload = json.loads(self._serializer.loads(raw))
        except (BadSignature, ValueError, TypeError):
            return SessionData()
        if not isinstance(payload, dict):
            return SessionData()
        return SessionData(
            sub=payload.get("sub"),
            pending_state=payload.get("pending_state"),
            pending_nonce=payload.get("pending_nonce"),
            pending_pkce_verifier=payload.get("pending_pkce_verifier"),
        )

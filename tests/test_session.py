from mijnstroom.bootstrap.config import SessionConfig
from mijnstroom.infrastructure.auth.session import SessionCodec, SessionData


def test_session_roundtrip() -> None:
    codec = SessionCodec(SessionConfig(secret="topsecret"))
    original = SessionData(sub="user-1", pending_state="s", pending_nonce="n", pending_pkce_verifier="v")
    encoded = codec.encode(original)
    decoded = codec.decode(encoded)
    assert decoded == original


def test_session_invalid_signature_returns_blank() -> None:
    codec_a = SessionCodec(SessionConfig(secret="a"))
    codec_b = SessionCodec(SessionConfig(secret="b"))
    encoded = codec_a.encode(SessionData(sub="user-1"))
    decoded = codec_b.decode(encoded)
    assert decoded == SessionData()


def test_session_garbage_returns_blank() -> None:
    codec = SessionCodec(SessionConfig(secret="a"))
    assert codec.decode("not-a-valid-cookie") == SessionData()

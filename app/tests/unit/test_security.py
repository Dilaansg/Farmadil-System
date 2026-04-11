"""
app/tests/unit/test_security.py
────────────────────────────────
Tests unitarios para las funciones de seguridad (no requieren BD).
"""
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_different_from_plain(self):
        hashed = hash_password("MyPassword1")
        assert hashed != "MyPassword1"

    def test_verify_correct_password(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("MyPassword1", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("WrongPassword1", hashed) is False

    def test_same_password_generates_different_hashes(self):
        """bcrypt usa salt aleatorio — dos hashes del mismo password deben diferir."""
        h1 = hash_password("MyPassword1")
        h2 = hash_password("MyPassword1")
        assert h1 != h2


class TestJWTTokens:
    def test_access_token_decode(self):
        data = {"sub": "user-123"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_type(self):
        data = {"sub": "user-123"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_invalid_token_returns_none(self):
        payload = decode_token("not.a.valid.token")
        assert payload is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": "user-123"})
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

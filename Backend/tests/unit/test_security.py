"""Unit tests for core security primitives (password hashing & JWT handling)."""

from datetime import timedelta

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    """Verify password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_access_token_creation_and_decoding():
    """Verify access token creation and decoding."""
    token = create_access_token(subject=42, role="citizen")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "citizen"
    assert payload["type"] == "access"


def test_refresh_token_creation_and_decoding():
    """Verify refresh token creation and decoding."""
    token = create_refresh_token(subject=100, role="admin")
    payload = decode_token(token)
    assert payload["sub"] == "100"
    assert payload["role"] == "admin"
    assert payload["type"] == "refresh"


def test_expired_token_raises_authentication_error():
    """Verify expired token raises AuthenticationError."""
    token = create_access_token(subject=1, role="citizen", expires_delta=timedelta(seconds=-10))
    with pytest.raises(AuthenticationError) as exc_info:
        decode_token(token)
    assert "expired" in exc_info.value.message.lower()


def test_invalid_token_raises_authentication_error():
    """Verify malformed token raises AuthenticationError."""
    with pytest.raises(AuthenticationError):
        decode_token("invalid.token.structure")

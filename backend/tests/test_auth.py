"""Unit tests for auth service functions (no DB required)."""
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    plain = "my_secure_password"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong_password", hashed)


def test_jwt_roundtrip():
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    token = create_access_token(user_id)
    decoded_id = decode_access_token(token)
    assert decoded_id == user_id


def test_jwt_invalid_token():
    assert decode_access_token("not.a.valid.token") is None

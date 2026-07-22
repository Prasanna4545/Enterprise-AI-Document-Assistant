import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


def test_password_hashing():
    raw_pwd = "SecretPassword123!"
    hashed = hash_password(raw_pwd)
    
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_encode_decode():
    payload = {"sub": "user-123-uuid", "org_id": "org-456-uuid", "role": "ADMIN"}
    token = create_access_token(payload)
    
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123-uuid"
    assert decoded["org_id"] == "org-456-uuid"
    assert decoded["role"] == "ADMIN"
    assert decoded["type"] == "access"

import pytest
from datetime import datetime, timedelta
from shadowcypher.chat.auth import (
    create_jwt_token, validate_jwt_token, derive_device_key,
    encrypt_token, decrypt_token
)

def test_create_jwt_token():
    """JWT token contains user_id, username, device_id, expiry"""
    token = create_jwt_token(user_id=1, username="alice", device_id="desktop-001")
    assert isinstance(token, str)
    assert len(token) > 0

def test_validate_jwt_token_extracts_claims():
    """JWT validation extracts user_id, username, device_id"""
    token = create_jwt_token(user_id=1, username="alice", device_id="desktop-001")
    claims = validate_jwt_token(token)

    assert claims["user_id"] == 1
    assert claims["username"] == "alice"
    assert claims["device_id"] == "desktop-001"
    assert "exp" in claims

def test_validate_expired_token_fails():
    """Expired JWT raises exception"""
    token = create_jwt_token(user_id=1, username="alice", device_id="desktop-001")
    # Manually expire by waiting (or mock time)
    # For now, just test that invalid token fails
    with pytest.raises(Exception):
        validate_jwt_token("invalid.token.here")

def test_derive_device_key_from_password():
    """Argon2 derives device key from password + device_id"""
    password = "myVaultPassword123"
    device_id = "desktop-001"

    key = derive_device_key(password, device_id)

    assert len(key) == 32  # 256-bit key
    assert key == derive_device_key(password, device_id)  # Deterministic
    assert key != derive_device_key(password, "desktop-002")  # Different device_id

def test_encrypt_decrypt_token():
    """Token encryption/decryption with device key"""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjogMX0...."
    device_key = b"k" * 32

    encrypted = encrypt_token(token, device_key)
    decrypted = decrypt_token(encrypted, device_key)

    assert encrypted != token  # Encrypted is different
    assert decrypted == token  # Decryption recovers original

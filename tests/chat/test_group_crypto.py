import pytest
from shadowcypher.chat.group_crypto import (
    derive_group_session_key,
    encrypt_group_message,
    decrypt_group_message
)

def test_derive_group_session_key():
    """Test group session key derivation."""
    group_key = b"x" * 32
    group_id = "group-123"
    key_version = 1

    session_key = derive_group_session_key(group_key, group_id, key_version)
    assert len(session_key) == 32
    assert isinstance(session_key, bytes)

def test_derive_different_key_per_version():
    """Different key versions produce different session keys."""
    group_key = b"y" * 32
    group_id = "group-456"

    key_v1 = derive_group_session_key(group_key, group_id, 1)
    key_v2 = derive_group_session_key(group_key, group_id, 2)

    assert key_v1 != key_v2

def test_encrypt_decrypt_group_message():
    """Test group message encryption/decryption roundtrip."""
    plaintext = "Secret group message"
    group_key = b"z" * 32
    group_id = "group-789"
    key_version = 1

    ciphertext, nonce = encrypt_group_message(plaintext, group_key, group_id, key_version)
    decrypted = decrypt_group_message(ciphertext, nonce, group_key, group_id, key_version)

    assert decrypted == plaintext

def test_wrong_key_version_fails():
    """Using wrong key version fails to decrypt."""
    plaintext = "Protected message"
    group_key = b"a" * 32
    group_id = "group-999"

    ciphertext, nonce = encrypt_group_message(plaintext, group_key, group_id, 1)

    # Try to decrypt with wrong key version (simulates removed member with old key)
    with pytest.raises(Exception):  # AES-GCM authentication failure
        decrypt_group_message(ciphertext, nonce, group_key, group_id, 2)

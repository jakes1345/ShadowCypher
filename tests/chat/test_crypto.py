import pytest
from shadowcypher.chat.crypto import (
    generate_keypair, derive_shared_secret, derive_session_key,
    encrypt_message, decrypt_message, fingerprint, rotate_key
)

def test_generate_keypair_returns_32_byte_keys():
    """X25519 keypair generation returns 32-byte private and public keys"""
    private_key, public_key = generate_keypair()
    assert len(private_key) == 32
    assert len(public_key) == 32
    assert private_key != public_key

def test_derive_shared_secret_from_ecdh():
    """X25519 ECDH produces shared secret from two keypairs"""
    alice_private, alice_public = generate_keypair()
    bob_private, bob_public = generate_keypair()

    alice_shared = derive_shared_secret(alice_private, bob_public)
    bob_shared = derive_shared_secret(bob_private, alice_public)

    assert alice_shared == bob_shared
    assert len(alice_shared) == 32

def test_derive_session_key_from_shared_secret():
    """HKDF-SHA256 derives session key from shared secret and conversation_id"""
    shared_secret = b"x" * 32
    conversation_id = "alice-bob-12345"

    key = derive_session_key(shared_secret, conversation_id)
    assert len(key) == 32
    assert key == derive_session_key(shared_secret, conversation_id)  # Deterministic

def test_encrypt_message_with_aes_256_gcm():
    """AES-256-GCM encryption produces ciphertext and nonce"""
    plaintext = "Hello, Bob! This is a secret message."
    session_key = b"k" * 32

    ciphertext, nonce = encrypt_message(plaintext, session_key)

    assert len(nonce) == 12  # GCM uses 96-bit nonce
    assert len(ciphertext) >= len(plaintext)  # Ciphertext includes auth tag
    assert isinstance(ciphertext, bytes)
    assert isinstance(nonce, bytes)

def test_decrypt_message_recovers_plaintext():
    """AES-256-GCM decryption recovers plaintext from ciphertext+nonce"""
    plaintext = "Hello, Bob! This is a secret message."
    session_key = b"k" * 32

    ciphertext, nonce = encrypt_message(plaintext, session_key)
    decrypted = decrypt_message(ciphertext, nonce, session_key)

    assert decrypted == plaintext

def test_decrypt_with_wrong_key_fails():
    """Decryption with wrong key raises exception (auth failure)"""
    plaintext = "Secret message"
    session_key = b"k" * 32
    wrong_key = b"w" * 32

    ciphertext, nonce = encrypt_message(plaintext, session_key)

    with pytest.raises(Exception):  # InvalidTag
        decrypt_message(ciphertext, nonce, wrong_key)

def test_fingerprint_from_pubkey():
    """Fingerprint is first 8 chars of SHA256(pubkey)"""
    _, public_key = generate_keypair()
    fp = fingerprint(public_key)

    assert len(fp) == 8
    assert fp.isalnum() or fp.isalpha() or all(c in "0123456789abcdef" for c in fp)

def test_rotate_key_produces_new_key():
    """Key rotation derives new key from old key + rotation_id"""
    old_key = b"k" * 32
    rotation_id = 1

    new_key = rotate_key(old_key, rotation_id)

    assert len(new_key) == 32
    assert new_key != old_key
    assert new_key == rotate_key(old_key, rotation_id)  # Deterministic
    assert new_key != rotate_key(old_key, 2)  # Different rotation_id → different key

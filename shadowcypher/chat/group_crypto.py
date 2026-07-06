# shadowcypher/chat/group_crypto.py

from shadowcypher.chat.crypto import derive_session_key, encrypt_message, decrypt_message
import os

def derive_group_session_key(group_key: bytes, group_id: str, key_version: int) -> bytes:
    """Derive per-message session key from group's shared group_key.

    Args:
        group_key: 32-byte shared group key (created by admin, distributed to all members)
        group_id: group UUID
        key_version: current group_key_version (changes on member add/remove)

    Returns:
        256-bit session key for this group message
    """
    # Use group_id + key_version as salt to derive distinct keys per group state
    salt_str = f"{group_id}:{key_version}"
    return derive_session_key(group_key, salt_str)

def encrypt_group_message(plaintext: str, group_key: bytes, group_id: str, key_version: int) -> tuple:
    """Encrypt plaintext message using group's shared key.

    Returns:
        (ciphertext: bytes, nonce: bytes)
    """
    session_key = derive_group_session_key(group_key, group_id, key_version)
    ciphertext, nonce = encrypt_message(plaintext, session_key)
    return ciphertext, nonce

def decrypt_group_message(ciphertext: bytes, nonce: bytes, group_key: bytes, group_id: str, key_version: int) -> str:
    """Decrypt group message using group's shared key and key version."""
    session_key = derive_group_session_key(group_key, group_id, key_version)
    return decrypt_message(ciphertext, nonce, session_key)

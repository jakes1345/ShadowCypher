"""End-to-end encryption with AES-256-GCM and PBKDF2."""
import os
import base64
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from pydantic import BaseModel

# Encryption constants
KEY_LENGTH = 32  # 256 bits
NONCE_LENGTH = 12  # 96 bits (standard for GCM)
SALT_LENGTH = 16  # 128 bits
KDF_ITERATIONS = 100_000  # PBKDF2 iterations

class EncryptedMessage(BaseModel):
    """Encrypted message with nonce and tag."""
    ciphertext: str  # base64 encoded
    nonce: str  # base64 encoded
    tag: str  # base64 encoded (16 bytes for AES-GCM)

class EncryptionKey(BaseModel):
    """User's encryption key with salt."""
    key_id: str
    salt: str  # base64 encoded
    created_at: str

def derive_key_from_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """
    Derive a 256-bit encryption key from password using PBKDF2-HMAC-SHA256.
    Returns (key, salt).
    """
    if salt is None:
        salt = os.urandom(SALT_LENGTH)

    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    key = kdf.derive(password.encode())
    return key, salt

def encrypt_message(plaintext: str, key: bytes) -> EncryptedMessage:
    """
    Encrypt a message with AES-256-GCM.
    Returns EncryptedMessage with base64-encoded ciphertext, nonce, and tag.
    """
    nonce = os.urandom(NONCE_LENGTH)
    cipher = AESGCM(key)
    ciphertext_with_tag = cipher.encrypt(nonce, plaintext.encode(), None)

    # GCM returns ciphertext + tag, split them
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]

    return EncryptedMessage(
        ciphertext=base64.b64encode(ciphertext).decode(),
        nonce=base64.b64encode(nonce).decode(),
        tag=base64.b64encode(tag).decode(),
    )

def decrypt_message(encrypted: EncryptedMessage, key: bytes) -> str:
    """
    Decrypt a message encrypted with AES-256-GCM.
    Returns plaintext string.
    """
    ciphertext = base64.b64decode(encrypted.ciphertext)
    nonce = base64.b64decode(encrypted.nonce)
    tag = base64.b64decode(encrypted.tag)

    cipher = AESGCM(key)
    ciphertext_with_tag = ciphertext + tag
    plaintext = cipher.decrypt(nonce, ciphertext_with_tag, None)
    return plaintext.decode()

def rotate_group_key(old_key: bytes, old_salt: bytes) -> Tuple[bytes, bytes]:
    """
    Generate a new encryption key for a group (on member removal).
    Returns (new_key, new_salt).
    """
    new_salt = os.urandom(SALT_LENGTH)
    new_key = os.urandom(KEY_LENGTH)
    return new_key, new_salt

# In-memory key store (replace with database)
USER_KEYS_DB = {}  # user_id -> {key: bytes, salt: bytes}
GROUP_KEYS_DB = {}  # group_id -> {current: {key, salt}, history: [{key, salt, version}]}

def store_user_key(user_id: str, password: str):
    """Derive and store user's encryption key from password."""
    key, salt = derive_key_from_password(password)
    USER_KEYS_DB[user_id] = {"key": key, "salt": base64.b64encode(salt).decode()}

def get_user_key(user_id: str, password: str) -> bytes:
    """Retrieve and verify user's encryption key."""
    if user_id not in USER_KEYS_DB:
        return None
    stored_salt = base64.b64decode(USER_KEYS_DB[user_id]["salt"])
    key, _ = derive_key_from_password(password, stored_salt)
    return key

def create_group_key(group_id: str) -> bytes:
    """Create initial encryption key for a group."""
    key = os.urandom(KEY_LENGTH)
    salt = os.urandom(SALT_LENGTH)
    GROUP_KEYS_DB[group_id] = {
        "current": {"key": key, "salt": base64.b64encode(salt).decode()},
        "history": [
            {
                "version": 1,
                "key": base64.b64encode(key).decode(),
                "salt": base64.b64encode(salt).decode(),
            }
        ]
    }
    return key

def get_group_key(group_id: str) -> bytes:
    """Get current encryption key for a group."""
    if group_id not in GROUP_KEYS_DB:
        return create_group_key(group_id)
    return base64.b64decode(GROUP_KEYS_DB[group_id]["current"]["key"])

def rotate_and_store_group_key(group_id: str):
    """Rotate group encryption key on member removal."""
    if group_id not in GROUP_KEYS_DB:
        return

    new_key = os.urandom(KEY_LENGTH)
    new_salt = os.urandom(SALT_LENGTH)
    version = len(GROUP_KEYS_DB[group_id]["history"]) + 1

    GROUP_KEYS_DB[group_id]["current"] = {
        "key": new_key,
        "salt": base64.b64encode(new_salt).decode()
    }
    GROUP_KEYS_DB[group_id]["history"].append({
        "version": version,
        "key": base64.b64encode(new_key).decode(),
        "salt": base64.b64encode(new_salt).decode(),
    })

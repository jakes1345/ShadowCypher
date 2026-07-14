"""End-to-end encryption with AES-256-GCM and PBKDF2.

Key persistence: uses SQLite (via the main chat DB session) to store
encrypted key material. Falls back to in-memory cache for the current
process if DB is unavailable.
"""
import os
import base64
import json
import sqlite3
import threading
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf import pbkdf2
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

    kdf = pbkdf2.PBKDF2(
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


# ──────────────────────────────────────────────────────────────────────────────
# Persistent Key Store — SQLite-backed with in-process memory cache
# ──────────────────────────────────────────────────────────────────────────────

def _default_key_db_path() -> str:
    xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(xdg_data, "shadowcypher", "keys.db")

_KEY_DB_PATH = os.environ.get("SC_KEY_DB") or _default_key_db_path()
_db_lock = threading.Lock()

def _open_key_db() -> sqlite3.Connection:
    """Open (and initialise) the key-store database."""
    os.makedirs(os.path.dirname(_KEY_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_KEY_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_keys (
            user_id  TEXT PRIMARY KEY,
            salt_b64 TEXT NOT NULL,
            -- key itself is NOT stored \u2014 derived on demand from password+salt
            updated_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS group_keys (
            group_id    TEXT NOT NULL,
            version     INTEGER NOT NULL,
            key_b64     TEXT NOT NULL,
            salt_b64    TEXT NOT NULL,
            created_at  INTEGER DEFAULT (strftime('%s','now')),
            PRIMARY KEY (group_id, version)
        )
    """)
    conn.commit()
    return conn

# In-memory cache (process-lifetime) for speed; SQLite is authoritative
_user_salt_cache: dict[str, str] = {}   # user_id -> salt_b64
_group_key_cache: dict[str, dict] = {}  # group_id -> {current, history}


def store_user_key(user_id: str, password: str) -> None:
    """Derive and persist user's salt (the key itself is re-derived on demand)."""
    _, salt = derive_key_from_password(password)
    salt_b64 = base64.b64encode(salt).decode()
    _user_salt_cache[user_id] = salt_b64
    with _db_lock:
        conn = _open_key_db()
        conn.execute(
            "INSERT OR REPLACE INTO user_keys (user_id, salt_b64) VALUES (?, ?)",
            (user_id, salt_b64),
        )
        conn.commit()
        conn.close()


def get_user_key(user_id: str, password: str) -> Optional[bytes]:
    """Re-derive user's key from stored salt + given password."""
    salt_b64 = _user_salt_cache.get(user_id)
    if not salt_b64:
        with _db_lock:
            conn = _open_key_db()
            row = conn.execute(
                "SELECT salt_b64 FROM user_keys WHERE user_id = ?", (user_id,)
            ).fetchone()
            conn.close()
        if not row:
            return None
        salt_b64 = row[0]
        _user_salt_cache[user_id] = salt_b64
    key, _ = derive_key_from_password(password, base64.b64decode(salt_b64))
    return key


def create_group_key(group_id: str) -> bytes:
    """Create and persist initial encryption key for a group."""
    key = os.urandom(KEY_LENGTH)
    salt = os.urandom(SALT_LENGTH)
    key_b64 = base64.b64encode(key).decode()
    salt_b64 = base64.b64encode(salt).decode()

    _group_key_cache[group_id] = {
        "current": {"key": key_b64, "salt": salt_b64, "version": 1},
        "history": [{"version": 1, "key": key_b64, "salt": salt_b64}],
    }
    with _db_lock:
        conn = _open_key_db()
        conn.execute(
            "INSERT OR IGNORE INTO group_keys (group_id, version, key_b64, salt_b64) VALUES (?, ?, ?, ?)",
            (group_id, 1, key_b64, salt_b64),
        )
        conn.commit()
        conn.close()
    return key


def _load_group_keys(group_id: str) -> Optional[dict]:
    """Load all key versions for a group from SQLite."""
    with _db_lock:
        conn = _open_key_db()
        rows = conn.execute(
            "SELECT version, key_b64, salt_b64 FROM group_keys WHERE group_id = ? ORDER BY version",
            (group_id,),
        ).fetchall()
        conn.close()
    if not rows:
        return None
    history = [{"version": r[0], "key": r[1], "salt": r[2]} for r in rows]
    current = history[-1]
    return {
        "current": current,
        "history": history,
    }


def get_group_key(group_id: str) -> bytes:
    """Get current encryption key for a group; creates it if absent."""
    if group_id not in _group_key_cache:
        data = _load_group_keys(group_id)
        if data:
            _group_key_cache[group_id] = data
        else:
            return create_group_key(group_id)
    return base64.b64decode(_group_key_cache[group_id]["current"]["key"])


def rotate_and_store_group_key(group_id: str) -> None:
    """Rotate group encryption key on member removal and persist to DB."""
    if group_id not in _group_key_cache:
        _load_group_keys(group_id)  # warm cache
    if group_id not in _group_key_cache:
        create_group_key(group_id)
        return

    new_key = os.urandom(KEY_LENGTH)
    new_salt = os.urandom(SALT_LENGTH)
    new_key_b64 = base64.b64encode(new_key).decode()
    new_salt_b64 = base64.b64encode(new_salt).decode()
    version = len(_group_key_cache[group_id]["history"]) + 1

    _group_key_cache[group_id]["current"] = {"key": new_key_b64, "salt": new_salt_b64, "version": version}
    _group_key_cache[group_id]["history"].append({"version": version, "key": new_key_b64, "salt": new_salt_b64})

    with _db_lock:
        conn = _open_key_db()
        conn.execute(
            "INSERT OR REPLACE INTO group_keys (group_id, version, key_b64, salt_b64) VALUES (?, ?, ?, ?)",
            (group_id, version, new_key_b64, new_salt_b64),
        )
        conn.commit()
        conn.close()

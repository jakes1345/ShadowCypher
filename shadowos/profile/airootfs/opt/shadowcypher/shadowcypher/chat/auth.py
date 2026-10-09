import os
import secrets
import warnings
from datetime import datetime, timedelta
from typing import Dict

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


def _load_or_create_chat_secret() -> str:
    """Load JWT secret from env, then from file, else generate and persist."""
    val = os.getenv("JWT_SECRET_KEY") or os.getenv("SC_JWT_SECRET")
    if val:
        return val
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    secret_path = os.path.join(xdg, "shadowcypher", "chat_jwt.secret")
    if os.path.exists(secret_path):
        try:
            with open(secret_path) as f:
                stored = f.read().strip()
            if stored:
                return stored
        except Exception:
            pass
    new_secret = secrets.token_hex(32)
    try:
        os.makedirs(os.path.dirname(secret_path), exist_ok=True)
        with open(secret_path, "w") as f:
            f.write(new_secret)
        os.chmod(secret_path, 0o600)
    except Exception:
        warnings.warn(
            "JWT_SECRET_KEY not set and could not persist secret — tokens won't survive restart.",
            RuntimeWarning,
            stacklevel=2,
        )
    return new_secret

SECRET_KEY = _load_or_create_chat_secret()
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24  # Match auth_backend.py

def create_jwt_token(user_id: int, username: str, device_id: str) -> str:
    """Create JWT token with user claims"""
    payload = {
        "user_id": user_id,
        "username": username,
        "device_id": device_id,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def validate_jwt_token(token: str) -> Dict:
    """Validate JWT token and extract claims"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as e:
        raise ValueError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise ValueError("Invalid token") from e

def derive_device_key(password: str, device_id: str) -> bytes:
    """Argon2id derives device key from password + device_id"""
    import hashlib
    salt = hashlib.sha256(device_id.encode()).digest()[:16]  # 16-byte salt
    kdf = Argon2id(
        salt=salt,
        length=32,  # 256-bit key
        iterations=2,  # time_cost equivalent
        lanes=1,  # parallelism equivalent
        memory_cost=65536,  # 64 MiB
    )
    return kdf.derive((password).encode())

def encrypt_token(token: str, device_key: bytes) -> bytes:
    """Encrypt token with device key using AES-256-GCM"""
    nonce = os.urandom(12)
    cipher = AESGCM(device_key)
    ciphertext = cipher.encrypt(nonce, token.encode(), None)
    return nonce + ciphertext  # Prepend nonce to ciphertext

def decrypt_token(encrypted_token: bytes, device_key: bytes) -> str:
    """Decrypt token with device key"""
    nonce = encrypted_token[:12]
    ciphertext = encrypted_token[12:]
    cipher = AESGCM(device_key)
    plaintext = cipher.decrypt(nonce, ciphertext, None)
    return plaintext.decode()

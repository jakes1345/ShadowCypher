import jwt
import os
from datetime import datetime, timedelta
from typing import Dict
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_MINUTES = 30

def create_jwt_token(user_id: int, username: str, device_id: str) -> str:
    """Create JWT token with user claims"""
    payload = {
        "user_id": user_id,
        "username": username,
        "device_id": device_id,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def validate_jwt_token(token: str) -> Dict:
    """Validate JWT token and extract claims"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

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

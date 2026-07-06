import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import hashlib
import json

def generate_keypair() -> tuple[bytes, bytes]:
    """Generate X25519 keypair"""
    private_key = x25519.X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return private_bytes, public_bytes

def derive_shared_secret(private_key: bytes, peer_public_key: bytes) -> bytes:
    """X25519 ECDH to derive shared secret"""
    private = x25519.X25519PrivateKey.from_private_bytes(private_key)
    public = x25519.X25519PublicKey.from_public_bytes(peer_public_key)
    return private.exchange(public)

def derive_session_key(shared_secret: bytes, conversation_id: str) -> bytes:
    """HKDF-SHA256 to derive 256-bit session key"""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=conversation_id.encode(),
        info=b"shadowcypher-chat-v1",
    )
    return hkdf.derive(shared_secret)

def encrypt_message(plaintext: str, session_key: bytes) -> tuple[bytes, bytes]:
    """AES-256-GCM encryption with random nonce"""
    nonce = os.urandom(12)  # 96-bit nonce
    cipher = AESGCM(session_key)
    ciphertext = cipher.encrypt(nonce, plaintext.encode(), None)
    return ciphertext, nonce

def decrypt_message(ciphertext: bytes, nonce: bytes, session_key: bytes) -> str:
    """AES-256-GCM decryption"""
    cipher = AESGCM(session_key)
    plaintext = cipher.decrypt(nonce, ciphertext, None)
    return plaintext.decode()

def fingerprint(public_key: bytes) -> str:
    """SHA256(pubkey) → first 8 hex chars"""
    digest = hashlib.sha256(public_key).hexdigest()
    return digest[:8]

def rotate_key(old_key: bytes, rotation_id: int) -> bytes:
    """Derive new key from old key + rotation_id (for key rotation)"""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=str(rotation_id).encode(),
        info=b"shadowcypher-key-rotation",
    )
    return hkdf.derive(old_key)

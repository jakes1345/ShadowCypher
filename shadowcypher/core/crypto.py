"""ShadowCypher Cryptographic Lockdown Module.
Enforces AES-256-GCM authenticated encryption over all offensive payload generation logic.
"""

import os
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

_SENTINEL_PLAINTEXT = b"sc-drm-v2"


def _gcm_encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Return nonce || ciphertext+auth_tag. Nonce is 12 random bytes."""
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct


def _gcm_decrypt(key: bytes, blob: bytes) -> bytes:
    """Decrypt nonce || ciphertext+tag blob. Raises ValueError on auth failure."""
    if len(blob) < 28:  # 12 nonce + 16 minimum tag
        raise ValueError("blob too short to be valid GCM ciphertext")
    nonce, ct = blob[:12], blob[12:]
    try:
        return AESGCM(key).decrypt(nonce, ct, None)
    except Exception as exc:
        raise ValueError("authentication failed") from exc


class CryptoManager:
    """Manages the decryption of tactical modules. Requires user license key."""

    def __init__(self):
        self.key_file = os.path.join(config.project_root, ".session-secret")
        self.is_unlocked = False
        self._key: bytes = None
        self._load_key()

    @property
    def _sentinel_path(self):
        return self.key_file + ".sentinel"

    def generate_license_key(self) -> str:
        """Generate a new 256-bit AES license key (Admin Only). Returns hex key string."""
        key = os.urandom(32)
        sentinel_blob = _gcm_encrypt(key, _SENTINEL_PLAINTEXT)
        with open(self.key_file, "wb") as f:
            f.write(key)
        os.chmod(self.key_file, 0o600)
        with open(self._sentinel_path, "wb") as f:
            f.write(sentinel_blob)
        os.chmod(self._sentinel_path, 0o600)
        self._key = key
        self.is_unlocked = True
        return key.hex()

    def _load_key(self):
        if not os.path.exists(self.key_file):
            return
        try:
            with open(self.key_file, "rb") as f:
                key = f.read()
            if len(key) != 32:
                raise ValueError(f"expected 32-byte key, got {len(key)}")
            if os.path.exists(self._sentinel_path):
                with open(self._sentinel_path, "rb") as f:
                    blob = f.read()
                _gcm_decrypt(key, blob)  # raises if key is wrong
            self._key = key
            self.is_unlocked = True
            logger.info("crypto", "System Unlocked via stored License Key.")
        except Exception as e:
            logger.info(
                "crypto", f"Stored key invalid (regenerate via System Control): {e}"
            )
            self.is_unlocked = False

    def unlock_system(self, user_key: str) -> bool:
        lockout_path = os.path.join(config.project_root, ".drm-lockout")
        if os.path.exists(lockout_path):
            try:
                with open(lockout_path, "r") as f:
                    ts = float(f.read().strip())
                if time.time() - ts < 3600:
                    logger.error(
                        "crypto", "LOCKED OUT. Wait 1 hour or delete .drm-lockout."
                    )
                    return False
                else:
                    os.unlink(lockout_path)
            except (ValueError, OSError):
                os.unlink(lockout_path)

        try:
            # Accept key as 64-char hex string (preferred) or raw bytes encoding
            try:
                key = bytes.fromhex(user_key)
            except ValueError:
                key = user_key.encode()
            if len(key) != 32:
                raise ValueError(f"key must be 32 bytes; got {len(key)}")

            if os.path.exists(self._sentinel_path):
                with open(self._sentinel_path, "rb") as f:
                    blob = f.read()
                _gcm_decrypt(key, blob)  # raises ValueError if key is wrong

            self._key = key
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            self.is_unlocked = True
            self._failed_attempts = 0
            logger.info("crypto", "SYSTEM DECRYPTED. Arsenal online.")
            return True

        except Exception:
            self._failed_attempts = getattr(self, "_failed_attempts", 0) + 1
            logger.error("crypto", f"INVALID KEY. Warning {self._failed_attempts}/5.")
            time.sleep(min(3.0 * self._failed_attempts, 15.0))

            if self._failed_attempts >= 5:
                with open(lockout_path, "w") as f:
                    f.write(str(time.time()))
                logger.error("crypto", "MAX ATTEMPTS. Locked for 1 hour.")

            return False

    def require_unlock(self, func):
        """Decorator to prevent functions from running if locked."""

        def wrapper(*args, **kwargs):
            if not self.is_unlocked:
                logger.error(
                    "crypto", "ACCESS DENIED. License key required for this subsystem."
                )
                return "[DRM_LOCK] ACCESS DENIED: Enter your valid ShadowCypher License Key in the System Control Dashboard."
            return func(*args, **kwargs)

        return wrapper


crypt_mgr = CryptoManager()

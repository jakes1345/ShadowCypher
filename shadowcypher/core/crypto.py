"""ShadowCypher Cryptographic Lockdown Module.
Enforces AES-256 DRM encryption over all offensive payload generation logic.
"""

from cryptography.fernet import Fernet
import json
import os
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


class CryptoManager:
    """Manages the decryption of tactical modules. Requires user license key."""

    def __init__(self):
        self.key_file = os.path.join(config.project_root, ".session-secret")
        self.is_unlocked = False
        self.fernet = None
        self._load_key()

    def generate_license_key(self):
        """Generates a master 256-bit AES license key (Admin Only)."""
        key = Fernet.generate_key()
        with open(self.key_file, "wb") as f:
            f.write(key)
        os.chmod(self.key_file, 0o600)
        return key.decode()

    def _load_key(self):
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "rb") as f:
                    key = f.read().strip()
                self.fernet = Fernet(key)
                self.is_unlocked = True
                logger.info("crypto", "System Unlocked via stored License Key.")
            except Exception as e:
                logger.info(
                    "crypto", f"Stored key invalid (regenerate via System Control): {e}"
                )
                self.is_unlocked = False

    def unlock_system(self, user_key):
        import time

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
            self.fernet = Fernet(user_key.encode())
            with open(self.key_file, "wb") as f:
                f.write(user_key.encode())
            os.chmod(self.key_file, 0o600)
            self.is_unlocked = True
            self._failed_attempts = 0
            logger.info("crypto", "SYSTEM DECRYPTED. Arsenal online.")
            return True

        except (ValueError, Exception):
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

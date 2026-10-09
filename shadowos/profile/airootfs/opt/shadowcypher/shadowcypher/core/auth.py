"""
ShadowCypher Auth — admin key registry and user authentication.
Stores PBKDF2-salted user hashes and a single SHA-256-hashed admin key.
"""

import hashlib
import hmac
import json
import os

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

_EMPTY_REGISTRY = {"users": {}, "keys": {}}


class AuthManager:
    def __init__(self):
        self.auth_file = os.path.join(
            str(config.project_root), "configs", "security", "auth.json"
        )
        os.makedirs(os.path.dirname(self.auth_file), exist_ok=True)
        self.registry = self._load_registry()

    def _load_registry(self):
        if not os.path.exists(self.auth_file):
            return dict(_EMPTY_REGISTRY)
        try:
            with open(self.auth_file, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("auth", f"registry unreadable, starting empty: {e}")
            return dict(_EMPTY_REGISTRY)
        # Normalize: guarantee the top-level shape downstream code relies on.
        data.setdefault("users", {})
        data.setdefault("keys", {})
        return data

    def _save_registry(self):
        tmp = self.auth_file + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.registry, f, indent=4)
        os.replace(tmp, self.auth_file)
        os.chmod(self.auth_file, 0o600)

    def generate_admin_key(self):
        """Register the admin key from env/config. No hardcoded fallback."""
        key = os.environ.get("SHADOWCYPHER_ADMIN_KEY") or config.get(
            "security", "admin_key", default=None
        )
        if not key:
            raise RuntimeError(
                "ADMIN_KEY_UNSET: refusing to register a hardcoded admin key. "
                "Set SHADOWCYPHER_ADMIN_KEY env var or [security].admin_key in config."
            )
        self.registry["keys"]["master"] = hashlib.sha256(key.encode()).hexdigest()
        self._save_registry()
        return key

    def register_user(self, username, password):
        """Register a user with a PBKDF2-HMAC-SHA256 hash (200k iterations)."""
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 200_000
        ).hex()
        self.registry["users"][username] = {
            "hash": pwd_hash,
            "salt": salt.hex(),
            "role": "USER",
            "access_level": 1,
        }
        self._save_registry()
        logger.info("auth", f"USER_REGISTERED: {username}")
        return True

    def verify_user(self, username, password):
        """Constant-time password verification."""
        user = self.registry["users"].get(username)
        if not user:
            return False
        salt = bytes.fromhex(user["salt"])
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 200_000
        ).hex()
        return hmac.compare_digest(candidate, user["hash"])

    def verify_key(self, key):
        """Constant-time admin-key verification."""
        hashed = hashlib.sha256(key.encode()).hexdigest()
        master = self.registry["keys"].get("master", "")
        if master and hmac.compare_digest(hashed, master):
            return "ADMIN"
        return "NONE"


auth_manager = AuthManager()

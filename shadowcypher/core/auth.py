"""
ShadowCypher Auth — Admin Key & User Registration Matrix.
Handles centralized authentication for all sovereign signal planes.
"""

import hashlib
import os
import json
import ctypes
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

# ── RUST GHOST-CORE LINK ──────────────────────────────────────────
try:
    lib_path = os.path.join(str(config.project_root), "shadowcypher", "native", "libs", "librust_core.so")
    ghost_lib = ctypes.CDLL(lib_path)
    ghost_lib.encrypt_signal.restype = ctypes.c_char_p
    ghost_lib.decrypt_signal.restype = ctypes.c_char_p
    logger.info("auth", "GHOST_CORE_LINKED: Rust encryption matrix active.")
except Exception as e:
    logger.warning("auth", f"GHOST_CORE_FALLBACK: Using standard Python crypto. ({e})")
    ghost_lib = None

class AuthManager:
    def __init__(self):
        self.auth_file = os.path.join(str(config.project_root), "configs", "security", "auth.json")
        os.makedirs(os.path.dirname(self.auth_file), exist_ok=True)
        self.registry = self._load_registry()

    def _load_registry(self):
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {"users": {}, "keys": {}}

    def _save_registry(self):
        with open(self.auth_file, "w") as f:
            json.dump(self.registry, f, indent=4)

    def generate_admin_key(self):
        """Generate the primary master authority key."""
        # Prefer env override; then config; then refuse to use a hardcoded fallback.
        key = os.environ.get("SHADOWCYPHER_ADMIN_KEY") or config.get("security", "admin_key", default=None)
        if not key:
            raise RuntimeError(
                "ADMIN_KEY_UNSET: refusing to register a hardcoded admin key. "
                "Set SHADOWCYPHER_ADMIN_KEY env var or [security].admin_key in config."
            )
        hashed = hashlib.sha256(key.encode()).hexdigest()
        self.registry["keys"]["master"] = hashed
        self._save_registry()
        return key

    def register_user(self, username, password):
        """Securely archive a user node with salted hashing."""
        salt = os.urandom(16).hex()
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        
        self.registry["users"][username] = {
            "hash": pwd_hash,
            "salt": salt,
            "role": "USER",
            "access_level": 1
        }
        self._save_registry()
        logger.info("auth", f"USER_REGISTERED: {username}")
        return True

    def verify_key(self, key):
        """Verify master authority or secondary keys."""
        hashed = hashlib.sha256(key.encode()).hexdigest()
        if hashed == self.registry["keys"].get("master"):
            return "ADMIN"
        return "NONE"

auth_manager = AuthManager()

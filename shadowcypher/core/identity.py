"""Admin identity verification — cryptographic proof that THIS machine is the admin node."""

import os
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


_ADMIN_PUBKEY_PATH = (
    Path(config.project_root) / "shadowcypher" / "core" / "admin_public.pem"
)
_ADMIN_PRIVKEY_PATH = Path(config.project_root) / "admin_private.pem"

_ADMIN_HANDLE = "\U0001f512 SHADOW_ADMIN"
_ADMIN_ROLE = "admin"
_USER_ROLE = "operator"


def _load_public_key():
    if not _ADMIN_PUBKEY_PATH.exists():
        return None
    try:
        with open(_ADMIN_PUBKEY_PATH, "rb") as f:
            return serialization.load_pem_public_key(f.read())
    except Exception:
        return None


def _load_private_key():
    if not _ADMIN_PRIVKEY_PATH.exists():
        return None
    try:
        with open(_ADMIN_PRIVKEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    except Exception:
        return None


def get_pubkey_fingerprint() -> str:
    pub = _load_public_key()
    if not pub:
        return ""
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(pub_bytes).hexdigest()


def verify_admin(irc_nick: Optional[str] = None) -> bool:
    """Enterprise Identity Verification.
    
    Two modes:
    - Local (irc_nick=None): Checks machine handle + crypto key proof.
      Used by the UI to gate admin features.
    - IRC (irc_nick provided): Checks the IRC nick against the admin_list.
      Only authorized nicks (e.g. 'jack', 'ShadowSentinel') get admin.
    """
    from shadowcypher.core.config import config
    
    admin_list = config.get("identity", "admin_list", default=[])
    
    # ── IRC Authorization Mode ──
    if irc_nick is not None:
        if irc_nick in admin_list:
            return True
        # Also grant admin if IRC nick matches the machine handle
        current_handle = config.get("identity", "handle", default="")
        if current_handle and irc_nick == current_handle:
            return True
        return False
    
    # ── Local Machine Authorization Mode ──
    # 1. Primary: Admin List Delegation
    try:
        current_handle = config.get("identity", "handle", default="")
        if current_handle and current_handle in admin_list:
            logger.info("identity", f"Escalating privileges for authorized ADMIN: {current_handle}")
            return True
    except Exception:
        pass

    # 2. Secondary: Cryptographic Key Proofs
    pub = _load_public_key()
    priv = _load_private_key()
    if not pub or not priv:
        return False

    try:
        shipped_fp = pub.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        derived_pub = priv.public_key()
        derived_fp = derived_pub.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        if shipped_fp != derived_fp:
            logger.warn("identity", "TAMPER DETECTED: key mismatch")
            return False

        challenge = os.urandom(32)
        signature = priv.sign(
            challenge,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        pub.verify(
            signature,
            challenge,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        logger.info("identity", "Admin identity VERIFIED via crypto-key")
        return True

    except Exception as e:
        logger.warn("identity", f"Crypto-verification failed: {e}")
        return False


class Identity:
    """Singleton that caches admin status at startup."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._is_admin = verify_admin()
            cls._instance._role = _ADMIN_ROLE if cls._instance._is_admin else _USER_ROLE
        return cls._instance

    @property
    def is_admin(self) -> bool:
        return self._is_admin

    @property
    def role(self) -> str:
        return self._role

    @property
    def handle(self) -> str:
        # Load custom handle from config (overrides for both admin and op)
        custom = config.get("identity", "handle", default="")
        if custom:
            return custom
        
        if self._is_admin:
            return _ADMIN_HANDLE
        return "SC_OPERATOR"

    def set_handle(self, new_handle: str):
        """Set and persist a custom handle (Admin or Operator)."""
        config.set("identity", "handle", new_handle)
        logger.info("identity", f"Handle updated: {new_handle}")

    @property
    def pubkey_fingerprint(self) -> str:
        return get_pubkey_fingerprint()


identity = Identity()

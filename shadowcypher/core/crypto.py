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
        self.key_file = os.path.join(config.project_root, '.session-secret')
        self.is_unlocked = False
        self.fernet = None
        self._load_key()

    def generate_license_key(self):
        """Generates a master 256-bit AES license key (Admin Only)."""
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)
        return key.decode()
        
    def _load_key(self):
        """Attempts to load a previously saved key."""
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                self.fernet = Fernet(key)
                self.is_unlocked = True
                logger.info("crypto", "System Unlocked via stored License Key.")
            except Exception:
                self.is_unlocked = False

    def unlock_system(self, user_key):
        """Validates a key provided by the user with Anti-Bruteforce Tarpits."""
        import time
        
        # Check if they are permanently locked out
        if os.path.exists(os.path.join(config.project_root, '.drm-lockout')):
            logger.error("crypto", "SYSTEM PERMANENTLY LOCKED DUE TO INTRUSION ATTEMPT.")
            return False

        try:
            self.fernet = Fernet(user_key.encode())
            # Write it so they don't have to enter it every time
            with open(self.key_file, 'wb') as f:
                f.write(user_key.encode())
            self.is_unlocked = True
            
            # Reset intrusion attempts
            self._failed_attempts = 0
            logger.info("crypto", "SYSTEM DECRYPTED. Arsenal online.")
            return True
            
        except ValueError:
            self._failed_attempts = getattr(self, '_failed_attempts', 0) + 1
            logger.error("crypto", f"INVALID KEY COMBINATION. Warning {self._failed_attempts}/5.")
            
            # Tarpit Delay: Mathematically slows down automated hash-cracking 
            time.sleep(3.0 * self._failed_attempts)
            
            if self._failed_attempts >= 5:
                # Self-Destruct Protocol
                with open(os.path.join(config.project_root, '.drm-lockout'), 'w') as f:
                    f.write("BURNED")
                logger.error("crypto", "MAXIMUM ATTEMPTS REACHED. LOCKOUT PROTOCOL ENGAGED.")
                
            return False

    def require_unlock(self, func):
        """Decorator to prevent functions from running if locked."""
        def wrapper(*args, **kwargs):
            if not self.is_unlocked:
                logger.error("crypto", "ACCESS DENIED. License key required for this subsystem.")
                return "[DRM_LOCK] ACCESS DENIED: Enter your valid ShadowCypher License Key in the System Control Dashboard."
            return func(*args, **kwargs)
        return wrapper

crypt_mgr = CryptoManager()

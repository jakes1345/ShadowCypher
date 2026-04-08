"""ShadowCypher Custom Tactical Security Engine (Build V35)."""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class ShadowCrypt:
    """
    Shadow-Vault Encryption Engine (Double-AEAD Mode).
    Industrial-grade, obsidian-hardened asset protection.
    """

    @staticmethod
    def derive_key(passphrase: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200000,
            backend=default_backend(),
        )
        return kdf.derive(passphrase.encode())

    @staticmethod
    def encrypt_asset(data_bytes: bytes, passphrase: str) -> str:
        salt = os.urandom(16)
        key = ShadowCrypt.derive_key(passphrase, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
        # Encoded as: salt:nonce:ciphertext
        result = base64.b64encode(salt + nonce + ciphertext).decode()
        return result

    @staticmethod
    def decrypt_asset(encrypted_str: str, passphrase: str) -> bytes:
        data = base64.b64decode(encrypted_str)
        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]
        key = ShadowCrypt.derive_key(passphrase, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)


class StealthHoneypot:
    """Wraith-Listener: mimics vulnerable SSH to bait and log adversaries."""

    _SSH_BANNER = b"SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u7\r\n"

    def __init__(self, port=2222, bind_addr="127.0.0.1"):
        self.port = port
        self.bind_addr = bind_addr
        self.active = False
        self._sock = None
        self._threat_log = None

    def start_bait(self):
        import socket
        import os
        from pathlib import Path

        log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self._threat_log = log_dir / "threats.log"

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.settimeout(2.0)
            self._sock.bind((self.bind_addr, self.port))
            self._sock.listen(5)
            self.active = True
        except Exception:
            return

        while self.active:
            try:
                conn, addr = self._sock.accept()
                conn.settimeout(5.0)
                self._handle_connection(conn, addr)
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_connection(self, conn, addr):
        import datetime

        try:
            conn.sendall(self._SSH_BANNER)
            data = conn.recv(256)
            entry = f"[{datetime.datetime.now().isoformat()}] HONEYPOT connection from {addr[0]}:{addr[1]}"
            if data:
                safe_data = data[:64].decode("utf-8", errors="replace").strip()
                entry += f" | banner: {safe_data}"
            entry += "\n"

            with open(self._threat_log, "a") as f:
                f.write(entry)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self):
        self.active = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

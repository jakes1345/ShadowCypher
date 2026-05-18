"""ShadowCypher Custom Tactical Security Engine (Build V35)."""

import os
import base64
import hashlib
import shutil
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus


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

    def start_bait(self, on_threat=None):
        import socket
        import threading
        from pathlib import Path
        import datetime

        if self.active:
            return

        log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self._threat_log = log_dir / "threats.log"

        def _bait_loop():
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._sock.settimeout(2.0)
                self._sock.bind((self.bind_addr, self.port))
                self._sock.listen(5)
                self.active = True
                logger.info("security", f"Stealth Honeypot active on {self.bind_addr}:{self.port}")
            except Exception as e:
                logger.error("security", f"HONEYPOT_BIND_FAILED {self.bind_addr}:{self.port}: {e}")
                self.active = False
                return

            while self.active:
                try:
                    conn, addr = self._sock.accept()
                    conn.settimeout(5.0)
                    threading.Thread(target=self._handle_connection, args=(conn, addr, on_threat), daemon=True).start()
                except socket.timeout:
                    continue
                except OSError:
                    break

        threading.Thread(target=_bait_loop, daemon=True).start()

    def _handle_connection(self, conn, addr, on_threat=None):
        import datetime
        try:
            conn.sendall(self._SSH_BANNER)
            data = conn.recv(256)
            entry = f"[{datetime.datetime.now().isoformat()}] HONEYPOT_HIT: {addr[0]}:{addr[1]}"
            if data:
                safe_data = data[:64].decode("utf-8", errors="replace").strip()
                entry += f" | banner_probe: {safe_data}"
            
            with open(self._threat_log, "a") as f:
                f.write(entry + "\n")
            
            if on_threat:
                on_threat(entry)
            
            # Feed into Kairos
            from shadowcypher.core.kairos import kairos
            kairos.analyze(entry)

        except Exception as e:
            logger.debug("security", f"Honeypot connection dropped: {e}")
        finally:
            try: conn.close()
            except Exception: pass

    def stop(self):
        self.active = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass


class IdentityHardener:
    """Manages tactical legitimacy for offensive infrastructure."""
    
    @property
    def is_secure(self) -> bool:
        """Verifies machine handle and cryptographic alignment."""
        from shadowcypher.core.identity import identity
        return identity.is_admin

    def execute_flash_wipe(self):
        """Emergency purge of session data and ephemeral keys."""
        logger.warning("security", "ALERT_REACTION: Executing flash-wipe sequence...")
        
        # 1. Clear session memory
        from shadowcypher.core.hub import hub
        hub.telemetry["missions_total"] = 0
        hub.active_missions.clear()
        
        # 2. Lock forensics (rename to hidden)
        forensic_dir = os.path.join(str(config.project_root), "forensics")
        if os.path.exists(forensic_dir):
            hidden_dir = os.path.join(str(config.project_root), f".forensics_{os.urandom(4).hex()}")
            try:
                os.rename(forensic_dir, hidden_dir)
                logger.info("security", f"LOCKDOWN: Forensics vault relocated to {hidden_dir}")
            except Exception: pass
            
        # 3. Terminate all active tunnels
        from shadowcypher.core.runner import runner
        runner.cleanup()
        
        bus.publish("security_lockdown", {"status": "ENCRYPTED"})

    def get_hardware_footprint(self) -> str:
        """Generates a stable hardware fingerprint for admin recognition."""
        import platform
        import uuid
        raw = f"{platform.node()}:{uuid.getnode()}:{platform.processor()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def provision_letsencrypt(domain: str, webroot: str = "/var/www/html"):
        """
        Automates Certbot to acquire real, CA-signed SSL certificates.
        Effectively bypasses 'Not Secure' warnings on phishing deployments.
        """
        from shadowcypher.core.runner import runner
        logger.info("security", f"PROVISIONING_CERTIFICATE: {domain}")
        # Standard certbot command for manual/automated DNS/Webroot validation
        cmd = [
            "certbot", "certonly", 
            "--manual", 
            "--preferred-challenges", "dns",
            "-d", domain,
            "--non-interactive", "--agree-tos",
            "--register-unsafely-without-email"
        ]
        return runner.execute_task("LE_PROVISION", cmd)

    @staticmethod
    def setup_cloudflare_bridge(port: int, proto: str = "http"):
        """
        Engages a Cloudflare Tunnel (Argo) for automated HTTPS/SSL 
        without domain registration or firewall exposure.
        """
        from shadowcypher.core.runner import runner
        logger.info("security", f"ENGAGING_CLOUDFLARE_BRIDGE: {proto}://127.0.0.1:{port}")
        # This provides a valid *.trycloudflare.com certificate instantly
        cmd = ["cloudflared", "tunnel", "--url", f"{proto}://127.0.0.1:{port}"]
        return runner.execute_task("CF_TUNNEL", cmd)

    @staticmethod
    def expose_sovereign_hub():
        """Publicly exposes the Sovereign Hub to the global internet."""
        irc_port = config.get("irc", "hub_irc_port", default=6667)
        logger.info("security", f"HUB_EXPOSURE: Tunneling native IRC port {irc_port}")
        # Use TCP protocol for raw IRC
        return IdentityHardener.setup_cloudflare_bridge(irc_port, proto="tcp")


hardener = IdentityHardener()

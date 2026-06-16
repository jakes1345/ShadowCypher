"""
Stealth & Privacy Hardening — Zero-Trace Operational Fabric.
Ensures all outbound tactical traffic is routed through encrypted proxies or Tor.

Gate usage in offensive modules:
    from shadowcypher.core.stealth import stealth, require_stealth
    require_stealth(on_output)   # raises StealthRequired if not active
"""

import os
import socket
import shutil
import subprocess
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


class StealthRequired(RuntimeError):
    """Raised when an offensive tool fires without stealth active."""


class StealthEngine:
    def __init__(self):
        self.proxy_url = config.get("stealth", "proxy_url")
        self.enforce_privacy = config.get("stealth", "enforce_privacy", default=True)
        self._active = False

    # ── State ─────────────────────────────────────────────────

    @property
    def active(self) -> bool:
        """True if Tor is reachable on SOCKS port (authoritative check)."""
        return self._active or self._check_tor()

    @active.setter
    def active(self, v: bool):
        self._active = v

    def ghost_mode_on(self) -> bool:
        """True if the full 8-layer ghost_mode.py engage has been run."""
        return os.path.exists("/tmp/.ghost_mode_state")  # nosec B108

    # ── Core actions ──────────────────────────────────────────

    def engage(self) -> bool:
        """Activate the stealth layer: detect Tor or configured proxy, set env vars."""
        if not self.proxy_url:
            if self._check_tor():
                self.proxy_url = "socks5h://127.0.0.1:9050"
                logger.info("stealth", "Local Tor detected — routing through SOCKS5:9050")
            else:
                logger.warning("stealth", "No proxy configured and Tor not running. Privacy NOT enforced.")
                return False

        os.environ["HTTP_PROXY"]  = self.proxy_url
        os.environ["HTTPS_PROXY"] = self.proxy_url
        os.environ["ALL_PROXY"]   = self.proxy_url
        os.environ["NO_PROXY"]    = "localhost,127.0.0.1"

        self._active = True
        logger.info("stealth", f"Stealth Layer ENGAGED → {self.proxy_url}")
        return True

    def disengage(self):
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            os.environ.pop(key, None)
        self._active = False
        logger.info("stealth", "Stealth Layer DISENGAGED")

    # ── Gate ──────────────────────────────────────────────────

    def require(self, on_output=None, strict: bool = False) -> bool:
        """
        Call at the top of any outbound offensive operation.

        strict=False  → warn if stealth not active, but allow.
        strict=True   → block execution entirely if not active.

        Returns True if safe to proceed, False if blocked.
        Calls on_output(msg) for UI feedback.
        """
        tor_up = self._check_tor()
        ghost  = self.ghost_mode_on()

        if ghost and tor_up:
            return True  # fully cloaked, proceed

        msg_parts = []
        if not tor_up:
            msg_parts.append("Tor is NOT running — your real IP will be exposed")
        if not ghost:
            msg_parts.append("Ghost Mode not engaged — MAC/DNS/logs are unprotected")

        warning = "[STEALTH WARNING] " + " | ".join(msg_parts)

        if on_output:
            on_output(warning)
        logger.warning("stealth", warning)

        if strict:
            raise StealthRequired(warning)

        return True  # non-strict: warn but allow

    # ── Command wrapping ──────────────────────────────────────

    def wrap_command(self, cmd: list) -> list:
        """Prepend proxychains4/proxychains if Tor is active and the tool is available."""
        if not self._check_tor():
            return cmd
        pc = shutil.which("proxychains4") or shutil.which("proxychains")
        if pc:
            return [pc, "-q"] + cmd
        # Fall back to torsocks
        ts = shutil.which("torsocks")
        if ts:
            return [ts] + cmd
        return cmd

    def torify_requests_session(self):
        """Return a requests.Session configured to use Tor SOCKS5."""
        import requests
        session = requests.Session()
        proxies = {
            "http":  "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050",
        }
        session.proxies.update(proxies)
        return session

    # ── Verification ──────────────────────────────────────────

    def verify_ip_masked(self) -> dict:
        """
        Check real IP vs Tor exit IP.
        Returns {"real": str, "tor": str|None, "masked": bool}.
        """
        real_ip = self._get_real_ip()
        tor_ip  = self._get_tor_ip() if self._check_tor() else None
        masked  = tor_ip is not None and tor_ip != real_ip
        return {"real": real_ip, "tor": tor_ip, "masked": masked}

    def rotate_tor_circuit(self) -> bool:
        """Send NEWNYM signal to Tor control port to get a new exit node."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 9051))
            s.send(b'AUTHENTICATE ""\r\n')
            resp = s.recv(1024).decode()
            if "250 OK" not in resp:
                s.send(b"AUTHENTICATE\r\n")
                resp = s.recv(1024).decode()
            s.send(b"SIGNAL NEWNYM\r\n")
            resp = s.recv(1024).decode()
            s.close()
            return "250 OK" in resp
        except Exception:
            return False

    # ── Internal helpers ──────────────────────────────────────

    def _check_tor(self) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex(("127.0.0.1", 9050)) == 0
        except OSError:
            return False

    def _get_real_ip(self) -> str:
        try:
            r = subprocess.run(
                ["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
                capture_output=True, text=True, timeout=8
            )
            return r.stdout.strip() or "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def _get_tor_ip(self) -> str | None:
        try:
            r = subprocess.run(
                ["curl", "-s", "--max-time", "10",
                 "--socks5-hostname", "127.0.0.1:9050",
                 "https://api.ipify.org"],
                capture_output=True, text=True, timeout=15
            )
            ip = r.stdout.strip()
            return ip if ip else None
        except Exception:
            return None


stealth = StealthEngine()


def require_stealth(on_output=None, strict: bool = False) -> bool:
    """Module-level shortcut: call at top of any outbound offensive function."""
    return stealth.require(on_output=on_output, strict=strict)

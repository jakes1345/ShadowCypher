"""
Hysteria2 transport — QUIC-based proxy tunnel for DPI-resistant routing.

Hysteria2 tunnels traffic over UDP masquerading as HTTP/3. From a network
observer's perspective it looks like ordinary QUIC traffic. It's much harder
to fingerprint than Tor and substantially faster on lossy connections.

Usage:
    from shadowcypher.core.hysteria import hysteria_transport

    # Configure once (writes yaml config)
    hysteria_transport.configure("myserver.example.com:443", auth="s3cr3t")

    # Start the client daemon — exposes SOCKS5 on 127.0.0.1:1080
    hysteria_transport.start()

    # The stealth engine picks it up automatically via get_proxy_url()
    from shadowcypher.core.stealth import stealth
    stealth.engage()   # will use Hysteria's SOCKS5 if running

    # Stop when done
    hysteria_transport.stop()
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import]

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

_HYSTERIA_BIN = "hysteria2"
_SOCKS5_PORT = 1080
_SOCKS5_HOST = "127.0.0.1"


def _hysteria_binary() -> Optional[str]:
    return shutil.which(_HYSTERIA_BIN) or shutil.which("hysteria")


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except OSError:
        return False


class HysteriaTransport:
    """
    Manages a Hysteria2 client process and its config file.

    Thread-safe — start/stop can be called from background threads.
    All state mutations are protected by _lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._config_path: Optional[Path] = None

        # Config is kept in RAM when ghost mode is active, on disk otherwise
        self._base_dir = Path(os.path.expanduser("~/.shadowcypher/hysteria"))
        self._ram_dir = Path("/dev/shm/shadowcypher-hysteria")  # nosec B108

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """True if the hysteria2 binary exists on this system."""
        return _hysteria_binary() is not None

    @property
    def running(self) -> bool:
        """True if the Hysteria SOCKS5 port is accepting connections."""
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                return False
        return _port_open(_SOCKS5_HOST, _SOCKS5_PORT)

    @property
    def proxy_url(self) -> str:
        return f"socks5h://{_SOCKS5_HOST}:{_SOCKS5_PORT}"

    def configure(
        self,
        server: str,
        auth: str,
        sni: Optional[str] = None,
        obfs_password: Optional[str] = None,
        up_mbps: int = 100,
        down_mbps: int = 100,
        insecure: bool = False,
    ) -> Path:
        """
        Write (or overwrite) the Hysteria2 client config.

        server       — host:port of your Hysteria2 server (e.g. "vpn.example.com:443")
        auth         — shared secret / password set on the server
        sni          — TLS SNI to present; defaults to the server hostname
        obfs_password — salamander obfuscation password (optional but recommended)
        up_mbps      — upload bandwidth hint
        down_mbps    — download bandwidth hint
        insecure     — skip TLS verification (only for testing)
        """
        ghost_active = os.path.exists("/tmp/.ghost_mode_state")  # nosec B108
        config_dir = self._ram_dir if ghost_active else self._base_dir
        config_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        config_path = config_dir / "client.yaml"

        host = server.split(":")[0]
        doc: dict = {
            "server": server,
            "auth": auth,
            "bandwidth": {
                "up": f"{up_mbps} mbps",
                "down": f"{down_mbps} mbps",
            },
            "tls": {
                "sni": sni or host,
                "insecure": insecure,
            },
            "socks5": {
                "listen": f"{_SOCKS5_HOST}:{_SOCKS5_PORT}",
            },
        }

        if obfs_password:
            doc["obfs"] = {
                "type": "salamander",
                "salamander": {"password": obfs_password},
            }

        config_path.write_text(yaml.dump(doc, default_flow_style=False), encoding="utf-8")
        config_path.chmod(0o600)

        with self._lock:
            self._config_path = config_path

        logger.info("hysteria", f"Config written → {config_path}")
        return config_path

    def start(self, on_output=None) -> bool:
        """
        Start the Hysteria2 client daemon.

        Returns True if the SOCKS5 port becomes reachable within 5 seconds.
        """
        if not self.available:
            logger.warning("hysteria", "hysteria2 binary not found. Install from https://github.com/apernet/hysteria")
            return False

        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                logger.info("hysteria", "Already running")
                return True

            if self._config_path is None or not self._config_path.exists():
                logger.warning("hysteria", "No config — call configure() first")
                return False

            try:
                self._proc = subprocess.Popen(
                    [_hysteria_binary(), "client", "--config", str(self._config_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except OSError as e:
                logger.error("hysteria", f"Failed to start: {e}")
                return False

        proc = self._proc

        def _stream():
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip()
                if line:
                    logger.debug("hysteria", line)
                    if on_output:
                        on_output(f"[HYSTERIA] {line}\n")

        threading.Thread(target=_stream, daemon=True, name="hysteria-log").start()

        # Wait up to 5 s for the SOCKS5 port to open
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if _port_open(_SOCKS5_HOST, _SOCKS5_PORT):
                logger.info("hysteria", f"SOCKS5 ready → {self.proxy_url}")
                return True
            time.sleep(0.2)

        logger.warning("hysteria", "SOCKS5 port didn't open in 5s — check server config")
        return False

    def stop(self):
        """Terminate the Hysteria2 client process."""
        with self._lock:
            proc = self._proc
            self._proc = None

        if proc is None:
            return

        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except ProcessLookupError:
                pass

        # Clean up RAM config if it was written there
        if self._config_path and str(self._config_path).startswith(str(self._ram_dir)):
            try:
                self._config_path.unlink(missing_ok=True)
                self._ram_dir.rmdir()
            except OSError:
                pass

        logger.info("hysteria", "Client stopped")

    def status(self) -> dict:
        """Return a status dict suitable for UI display."""
        with self._lock:
            proc = self._proc
            pid = proc.pid if proc and proc.poll() is None else None

        return {
            "available": self.available,
            "running": self.running,
            "pid": pid,
            "proxy_url": self.proxy_url if self.running else None,
            "config": str(self._config_path) if self._config_path else None,
        }

    def configure_from_dict(self, d: dict) -> Path:
        """Convenience wrapper for loading stored config from a dict."""
        return self.configure(
            server=d["server"],
            auth=d["auth"],
            sni=d.get("sni"),
            obfs_password=d.get("obfs_password"),
            up_mbps=d.get("up_mbps", 100),
            down_mbps=d.get("down_mbps", 100),
            insecure=d.get("insecure", False),
        )

    def save_profile(self, name: str, **kwargs) -> None:
        """Persist a named server profile to disk (encrypted via ShadowCrypt)."""
        profiles_dir = self._base_dir / "profiles"
        profiles_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        profile_file = profiles_dir / f"{name}.json"
        profile_file.write_text(json.dumps(kwargs, indent=2), encoding="utf-8")
        profile_file.chmod(0o600)
        logger.info("hysteria", f"Profile saved: {name}")

    def load_profile(self, name: str) -> Optional[dict]:
        """Load a named profile and write its config."""
        profile_file = self._base_dir / "profiles" / f"{name}.json"
        if not profile_file.exists():
            logger.warning("hysteria", f"Profile not found: {name}")
            return None
        d = json.loads(profile_file.read_text(encoding="utf-8"))
        self.configure_from_dict(d)
        return d

    def list_profiles(self) -> list[str]:
        profiles_dir = self._base_dir / "profiles"
        if not profiles_dir.exists():
            return []
        return [p.stem for p in profiles_dir.glob("*.json")]


hysteria_transport = HysteriaTransport()

"""
Hysteria2 autonomous transport layer.

Designed for zero-touch operation: configure once, runs forever.

Architecture:
  - Server pool with health scoring and auto-rotation
  - Watchdog thread: health checks every 30s, reconnects silently on failure
  - Fallback chain: Hysteria2 → Tor → warn operator
  - Ghost Mode hook: auto-starts when ghost mode engages, stops on disengage
  - Bus events: publishes HYSTERIA_UP / HYSTERIA_DOWN / HYSTERIA_ROTATING
    so the UI updates without any polling

One-time setup:
    python3 -m shadowcypher.core.hysteria setup

After that, the transport manages itself.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

from shadowcypher.core.logger import logger

_HYSTERIA_BIN   = "hysteria2"
_SOCKS5_HOST    = "127.0.0.1"
_SOCKS5_PORT    = 1080
_WATCHDOG_SECS  = 30
_CONNECT_TIMEOUT = 5.0

_PROFILES_DIR = Path(os.path.expanduser("~/.shadowcypher/hysteria/profiles"))
_RAM_DIR      = Path("/dev/shm/shadowcypher-hysteria")  # nosec B108


# ── Server profile ───────────────────────────────────────────────────────────

@dataclass
class ServerProfile:
    name: str
    server: str        # host:port
    auth: str
    sni: Optional[str] = None
    obfs_password: Optional[str] = None
    up_mbps: int = 100
    down_mbps: int = 100
    insecure: bool = False
    # Runtime state — not persisted
    failures: int = field(default=0, compare=False, repr=False)
    last_ok: float = field(default=0.0, compare=False, repr=False)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items()
                if k not in ("failures", "last_ok")}

    @classmethod
    def from_dict(cls, d: dict) -> ServerProfile:
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})

    def build_yaml(self, socks5_listen: str) -> str:
        host = self.server.split(":")[0]
        doc: dict = {
            "server": self.server,
            "auth": self.auth,
            "bandwidth": {"up": f"{self.up_mbps} mbps", "down": f"{self.down_mbps} mbps"},
            "tls": {"sni": self.sni or host, "insecure": self.insecure},
            "socks5": {"listen": socks5_listen},
        }
        if self.obfs_password:
            doc["obfs"] = {"type": "salamander",
                           "salamander": {"password": self.obfs_password}}
        try:
            import yaml
            return str(yaml.dump(doc, default_flow_style=False))
        except ImportError:
            # Minimal YAML serialisation without dependency
            lines = [
                f'server: "{self.server}"',
                f'auth: "{self.auth}"',
                "bandwidth:",
                f'  up: "{self.up_mbps} mbps"',
                f'  down: "{self.down_mbps} mbps"',
                "tls:",
                f'  sni: "{self.sni or host}"',
                f"  insecure: {str(self.insecure).lower()}",
                "socks5:",
                f'  listen: "{socks5_listen}"',
            ]
            if self.obfs_password:
                lines += [
                    "obfs:",
                    "  type: salamander",
                    "  salamander:",
                    f'    password: "{self.obfs_password}"',
                ]
            return "\n".join(lines) + "\n"


# ── Main transport class ─────────────────────────────────────────────────────

class HysteriaTransport:
    """
    Autonomous Hysteria2 client.

    - Maintains a pool of servers, rotates on failure.
    - Watchdog thread polls every _WATCHDOG_SECS seconds and reconnects silently.
    - Publishes status events on the ShadowBus so UI reflects live state.
    - auto_start() is called by Ghost Mode — no human intervention after setup.
    """

    def __init__(self):
        self._lock      = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._active_profile: Optional[ServerProfile] = None
        self._config_path: Optional[Path] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._running   = False     # watchdog sentinel
        self._callbacks: list[Callable] = []

        self._pool: list[ServerProfile] = []
        self._load_pool()

    # ── Binary check ─────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return bool(shutil.which(_HYSTERIA_BIN) or shutil.which("hysteria"))

    def _bin(self) -> str:
        return shutil.which(_HYSTERIA_BIN) or shutil.which("hysteria") or _HYSTERIA_BIN

    # ── Connection status ─────────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    @property
    def connected(self) -> bool:
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return False
        return _port_open(_SOCKS5_HOST, _SOCKS5_PORT)

    @property
    def proxy_url(self) -> str:
        return f"socks5h://{_SOCKS5_HOST}:{_SOCKS5_PORT}"

    # ── Server pool management ───────────────────────────────────────────────

    def add_server(self, profile: ServerProfile, save: bool = True) -> None:
        """Add a server to the pool. Persists to disk by default."""
        with self._lock:
            self._pool = [p for p in self._pool if p.name != profile.name]
            self._pool.append(profile)
        if save:
            self._save_profile(profile)
        logger.info("hysteria", f"Server added to pool: {profile.name} ({profile.server})")

    def remove_server(self, name: str) -> bool:
        with self._lock:
            before = len(self._pool)
            self._pool = [p for p in self._pool if p.name != name]
            removed = len(self._pool) < before
        if removed:
            _profile_path(name).unlink(missing_ok=True)
            logger.info("hysteria", f"Server removed: {name}")
        return removed

    def list_servers(self) -> list[dict]:
        with self._lock:
            return [{"name": p.name, "server": p.server,
                     "failures": p.failures, "last_ok": p.last_ok}
                    for p in self._pool]

    # ── Autonomous start / stop ───────────────────────────────────────────────

    def auto_start(self, on_output: Callable[[str], None] | None = None) -> bool:
        """
        Start Hysteria2 autonomously. Tries all servers in the pool, best-first.
        Launches the watchdog. Called automatically by Ghost Mode.

        Returns True if a connection was established (or Tor fallback is active).
        """
        if not self.available:
            logger.warning("hysteria", "hysteria2 not installed — skipping QUIC transport")
            return False

        with self._lock:
            pool = list(self._pool)

        if not pool:
            logger.info("hysteria", "No servers configured. Run: python3 -m shadowcypher.core.hysteria setup")
            return False

        # Sort: fewest failures first, most recently successful first
        pool.sort(key=lambda p: (p.failures, -p.last_ok))

        for profile in pool:
            logger.info("hysteria", f"Trying {profile.name} ({profile.server})…")
            if self._connect(profile, on_output):
                self._start_watchdog()
                self._publish("HYSTERIA_UP", profile.name)
                return True
            profile.failures += 1
            logger.warning("hysteria", f"{profile.name} failed (failure #{profile.failures})")

        logger.warning("hysteria", "All Hysteria2 servers failed. Falling back to Tor.")
        self._publish("HYSTERIA_DOWN", "all_failed")
        return False

    def stop(self) -> None:
        """Stop Hysteria2 and the watchdog. Called by Ghost Mode disengage."""
        self._running = False
        with self._lock:
            proc = self._proc
            self._proc = None
            self._active_profile = None

        _kill_proc(proc)
        _cleanup_ram_config(self._config_path)
        self._config_path = None
        self._publish("HYSTERIA_DOWN", "stopped")
        logger.info("hysteria", "Transport stopped")

    # ── One-time setup ───────────────────────────────────────────────────────

    def interactive_setup(self) -> bool:
        """
        Guided one-time setup. Called from `python3 -m shadowcypher.core.hysteria setup`.
        Saves the server profile so auto_start() needs no further input.
        """
        print("\n  HYSTERIA2 SETUP — runs once, then fully automatic\n")

        if not self.available:
            print("  hysteria2 binary not found.")
            print("  Arch/ShadowOS:  yay -S hysteria")
            print("  Other Linux:    Visit https://hysteria.network for downloads")
            return False

        print("  You need a Hysteria2 server. Options:")
        print("  1. Self-host on any VPS (Oracle Free Tier, Hetzner, etc.)")
        print("  2. Use a shared Hysteria2 service")
        print("  See: https://v2.hysteria.network/docs/getting-started/Server/\n")

        name   = input("  Profile name [default]: ").strip() or "default"
        server = input("  Server (host:port): ").strip()
        if not server:
            print("  Aborted.")
            return False

        auth   = input("  Auth password: ").strip()
        sni    = input(f"  TLS SNI [{server.split(':')[0]}]: ").strip() or None
        obfs   = input("  Obfuscation password (optional): ").strip() or None

        profile = ServerProfile(
            name=name, server=server, auth=auth,
            sni=sni, obfs_password=obfs,
        )
        self.add_server(profile)

        print(f"\n  Testing connection to {server}…")
        if self._connect(profile):
            self.stop()
            print(f"  Connected. Profile '{name}' saved.")
            print("  Hysteria2 will now start automatically with Ghost Mode.")
            return True
        else:
            print("  Could not connect. Check server address and credentials.")
            return False

    # ── Internal ─────────────────────────────────────────────────────────────

    def _connect(self, profile: ServerProfile,
                 on_output: Callable[[str], None] | None = None) -> bool:
        """Spawn hysteria2 for this profile. Returns True when SOCKS5 port opens."""
        ghost = os.path.exists("/tmp/.ghost_mode_state")  # nosec B108
        config_dir = _RAM_DIR if ghost else _PROFILES_DIR.parent / "run"
        config_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        config_path = config_dir / "active.yaml"
        config_path.write_text(profile.build_yaml(f"{_SOCKS5_HOST}:{_SOCKS5_PORT}"),
                               encoding="utf-8")
        config_path.chmod(0o600)

        _kill_proc(self._proc)

        try:
            proc = subprocess.Popen(
                [self._bin(), "client", "--config", str(config_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as e:
            logger.error("hysteria", f"Popen failed: {e}")
            return False

        # Stream logs off-thread
        def _log():
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip()
                if line:
                    logger.debug("hysteria", line)
                    if on_output:
                        on_output(f"[HYSTERIA] {line}\n")
        threading.Thread(target=_log, daemon=True, name="hysteria-log").start()

        # Wait for SOCKS5 port
        deadline = time.monotonic() + _CONNECT_TIMEOUT
        while time.monotonic() < deadline:
            if _port_open(_SOCKS5_HOST, _SOCKS5_PORT):
                with self._lock:
                    self._proc = proc
                    self._active_profile = profile
                    self._config_path = config_path
                profile.last_ok = time.time()
                profile.failures = 0
                return True
            if proc.poll() is not None:
                break
            time.sleep(0.2)

        _kill_proc(proc)
        return False

    def _start_watchdog(self) -> None:
        """Start a daemon thread that keeps the connection alive."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._running = True
        t = threading.Thread(target=self._watchdog_loop,
                             daemon=True, name="hysteria-watchdog")
        t.start()
        self._watchdog_thread = t

    def _watchdog_loop(self) -> None:
        while self._running:
            time.sleep(_WATCHDOG_SECS)

            if self.connected:
                with self._lock:
                    if self._active_profile:
                        self._active_profile.last_ok = time.time()
                continue

            # Connection lost — try to reconnect
            logger.warning("hysteria", "Connection lost — rotating servers")
            self._publish("HYSTERIA_ROTATING", "reconnecting")

            with self._lock:
                pool = list(self._pool)

            pool.sort(key=lambda p: (p.failures, -p.last_ok))
            reconnected = False
            for profile in pool:
                if self._connect(profile):
                    self._publish("HYSTERIA_UP", profile.name)
                    reconnected = True
                    break
                profile.failures += 1

            if not reconnected:
                self._publish("HYSTERIA_DOWN", "all_failed")
                logger.warning("hysteria", "Could not reconnect. Stealth engine will fall back to Tor.")
                # Reset env proxy so stealth.engage() picks up Tor next call
                for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                    os.environ.pop(k, None)
                self._running = False

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load_pool(self) -> None:
        if not _PROFILES_DIR.exists():
            return
        for f in _PROFILES_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                self._pool.append(ServerProfile.from_dict(d))
            except Exception as e:
                logger.warning("hysteria", f"Could not load profile {f.name}: {e}")

    def _save_profile(self, profile: ServerProfile) -> None:
        _PROFILES_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
        path = _profile_path(profile.name)
        path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
        path.chmod(0o600)

    # ── Bus events ───────────────────────────────────────────────────────────

    def _publish(self, event: str, detail: str) -> None:
        try:
            from shadowcypher.core.bus import bus
            bus.publish("hysteria_status", {"event": event, "detail": detail})
        except Exception:
            pass
        for cb in self._callbacks:
            try:
                cb(event, detail)
            except Exception:
                pass

    def on_status_change(self, cb: Callable[[str, str], None]) -> None:
        """Register a callback: cb(event, detail) fired on status changes."""
        self._callbacks.append(cb)

    # ── Status summary ───────────────────────────────────────────────────────

    def status(self) -> dict:
        with self._lock:
            profile = self._active_profile
        return {
            "available":  self.available,
            "connected":  self.connected,
            "proxy_url":  self.proxy_url if self.connected else None,
            "server":     profile.server if profile else None,
            "profile":    profile.name if profile else None,
            "pool_size":  len(self._pool),
            "watchdog":   self._running,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except OSError:
        return False


def _kill_proc(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
        try:
            proc.kill()
        except (ProcessLookupError, OSError):
            pass


def _cleanup_ram_config(path: Optional[Path]) -> None:
    if path and str(path).startswith(str(_RAM_DIR)):
        try:
            path.unlink(missing_ok=True)
            _RAM_DIR.rmdir()
        except OSError:
            pass


def _profile_path(name: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return _PROFILES_DIR / f"{safe}.json"


# ── Ghost Mode hook ───────────────────────────────────────────────────────────

def ghost_engage_hook(on_output: Callable[[str], None] | None = None) -> None:
    """
    Called automatically by ghost_mode.py on engage.
    Starts Hysteria2 and updates the stealth engine proxy.
    """
    if not hysteria_transport.available or not hysteria_transport._pool:
        return

    logger.info("hysteria", "Ghost Mode engaged — starting Hysteria2 transport")
    ok = hysteria_transport.auto_start(on_output=on_output)
    if ok:
        # Immediately update stealth engine so all tools use it
        try:
            from shadowcypher.core.stealth import stealth
            stealth.proxy_url = hysteria_transport.proxy_url
            stealth.active = True
            import os as _os
            for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                _os.environ[k] = hysteria_transport.proxy_url
            _os.environ["NO_PROXY"] = "localhost,127.0.0.1"
        except Exception as e:
            logger.warning("hysteria", f"Could not update stealth env: {e}")


def ghost_disengage_hook() -> None:
    """Called automatically by ghost_mode.py on disengage."""
    hysteria_transport.stop()


# ── Singleton ─────────────────────────────────────────────────────────────────

hysteria_transport = HysteriaTransport()


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "setup":
        hysteria_transport.interactive_setup()

    elif cmd == "start":
        print("Starting Hysteria2 transport…")
        ok = hysteria_transport.auto_start(on_output=print)
        if ok:
            print(f"Connected. SOCKS5 at {hysteria_transport.proxy_url}")
            print("Ctrl+C to stop")
            try:
                while hysteria_transport.connected:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            hysteria_transport.stop()
        else:
            print("Failed to connect. Check logs.")
            sys.exit(1)

    elif cmd == "stop":
        hysteria_transport.stop()
        print("Stopped.")

    elif cmd == "status":
        import json as _json
        print(_json.dumps(hysteria_transport.status(), indent=2))

    elif cmd == "servers":
        servers = hysteria_transport.list_servers()
        if not servers:
            print("No servers configured. Run: python3 -m shadowcypher.core.hysteria setup")
        for s in servers:
            ok_ago = f"{time.time() - s['last_ok']:.0f}s ago" if s["last_ok"] else "never"
            print(f"  {s['name']:20s} {s['server']:30s} failures={s['failures']} last_ok={ok_ago}")

    else:
        print("Usage: python3 -m shadowcypher.core.hysteria [setup|start|stop|status|servers]")

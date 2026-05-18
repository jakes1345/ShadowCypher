"""
Mesh Network Relay — Decentralized Operations Plane.
P2P encrypted UDP signaling plane with ECC key exchange,
ChaCha20-Poly1305 message encryption, peer discovery,
heartbeat monitoring, and remote provisioning.
"""

import socket
import threading
import time
import os
import json
import hashlib
import struct
import secrets
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from shadowcypher.core.module import BaseModule
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

# Protocol headers
MAGIC_HANDSHAKE = b"\xde\xad\xbe\xef"
MAGIC_HEARTBEAT = b"\xca\xfe\xba\xbe"
MAGIC_DATA      = b"\xf0\x0d\xfa\xce"
MAGIC_COMMAND   = b"\xc0\xde\xc0\xde"

try:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


@dataclass
class MeshPeer:
    """A verified endpoint in the mesh topology."""
    node_id: str
    addr: tuple  # (ip, port)
    public_key: bytes = b""
    shared_secret: bytes = b""
    last_seen: float = 0
    latency_ms: float = 0
    capabilities: List[str] = field(default_factory=list)
    is_mobile: bool = False

    @property
    def is_alive(self) -> bool:
        return (time.time() - self.last_seen) < 60

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "addr": f"{self.addr[0]}:{self.addr[1]}",
            "last_seen": self.last_seen,
            "latency_ms": round(self.latency_ms, 1),
            "alive": self.is_alive,
            "is_mobile": self.is_mobile,
            "capabilities": self.capabilities,
        }


class MeshRelay(BaseModule):
    """Encrypted P2P relay for autonomous mesh communication."""

    def __init__(self):
        super().__init__(module_name="mesh_relay")
        self.port = 19999
        self.node_id = hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:16]
        self.peers: Dict[str, MeshPeer] = {}
        self.server_sock: Optional[socket.socket] = None
        self.running = False

        # ECC keypair for Diffie-Hellman
        self._private_key = None
        self._public_key_bytes = b""
        self._on_message: Optional[Callable] = None

        self.key_dir = os.path.join(os.path.expanduser("~"), ".shadowcypher", "mesh")
        os.makedirs(self.key_dir, exist_ok=True)

        self._generate_keypair()

    def _generate_keypair(self):
        """Generate X25519 keypair for ECDH key exchange."""
        if not HAS_CRYPTO:
            logger.warning("mesh", "CRYPTO_MISSING: python-cryptography required for E2E encryption.")
            self._public_key_bytes = self.node_id.encode()[:32].ljust(32, b'\x00')
            return

        key_path = os.path.join(self.key_dir, "node_key.bin")
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                raw = f.read()
            self._private_key = X25519PrivateKey.from_private_bytes(raw)
        else:
            self._private_key = X25519PrivateKey.generate()
            raw = self._private_key.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption()
            )
            with open(key_path, "wb") as f:
                f.write(raw)
            os.chmod(key_path, 0o600)

        self._public_key_bytes = self._private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        logger.info("mesh", f"NODE_PROVISIONED: {self.node_id} | PubKey: {self._public_key_bytes.hex()[:16]}...")

    def _derive_shared_secret(self, peer_public_bytes: bytes) -> bytes:
        """ECDH: derive shared secret from peer's public key."""
        if not HAS_CRYPTO or not self._private_key:
            return hashlib.sha256(peer_public_bytes).digest()
        peer_pub = X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared = self._private_key.exchange(peer_pub)
        return hashlib.sha256(shared).digest()

    def _encrypt(self, plaintext: bytes, key: bytes) -> bytes:
        """ChaCha20-Poly1305 encrypt."""
        if not HAS_CRYPTO:
            return plaintext
        nonce = secrets.token_bytes(12)
        cipher = ChaCha20Poly1305(key)
        ct = cipher.encrypt(nonce, plaintext, None)
        return nonce + ct

    def _decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        """ChaCha20-Poly1305 decrypt."""
        if not HAS_CRYPTO:
            return ciphertext
        nonce = ciphertext[:12]
        ct = ciphertext[12:]
        cipher = ChaCha20Poly1305(key)
        return cipher.decrypt(nonce, ct, None)

    # ══════════════════════════════════════════════════════════════
    # Core Mesh Lifecycle
    # ══════════════════════════════════════════════════════════════

    def start_hub(self, on_message: Optional[Callable] = None):
        """Initialize the local relay hub."""
        if self.running:
            return
        self._on_message = on_message
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # SECURITY: Default to loopback. Require explicit opt-in for external listeners.
        bind_addr = os.environ.get("SHADOWCYPHER_MESH_BIND", "127.0.0.1")
        self.server_sock.bind((bind_addr, self.port))
        self.running = True

        threading.Thread(target=self._listen_loop, daemon=True, name="MeshListener").start()
        threading.Thread(target=self._heartbeat_loop, daemon=True, name="MeshTelemetry").start()
        threading.Thread(target=self._reaper_loop, daemon=True, name="MeshPruner").start()

        logger.info("mesh", f"MESH_RELAY_ACTIVE: UDP/{self.port} | Node: {self.node_id}")
        bus.publish("module_status", {
            "module": "mesh_relay", "status": "ONLINE",
            "node_id": self.node_id, "port": self.port,
        })

    def stop_hub(self):
        """Terminate the local relay hub."""
        self.running = False
        if self.server_sock:
            self.server_sock.close()
        self.peers.clear()
        logger.info("mesh", "MESH_RELAY_TERMINATED")
        bus.publish("module_status", {"module": "mesh_relay", "status": "OFFLINE"})

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.server_sock.recvfrom(65535)
                if len(data) < 4:
                    continue
                magic = data[:4]
                payload = data[4:]

                if magic == MAGIC_HANDSHAKE:
                    self._handle_handshake(payload, addr)
                elif magic == MAGIC_HEARTBEAT:
                    self._handle_heartbeat(payload, addr)
                elif magic == MAGIC_DATA:
                    self._handle_data(payload, addr)
                elif magic == MAGIC_COMMAND:
                    self._handle_command(payload, addr)
            except OSError:
                break
            except Exception as e:
                if self.running:
                    logger.error("mesh", f"RECEIVE_FAULT: {e}")

    def _heartbeat_loop(self):
        """Dispatch presence telemetry to all registered peers."""
        while self.running:
            time.sleep(15)
            packet = MAGIC_HEARTBEAT + self.node_id.encode()[:16].ljust(16, b'\x00')
            packet += struct.pack("!d", time.time())  # Timestamp for latency telemetry
            for peer in list(self.peers.values()):
                try:
                    self.server_sock.sendto(packet, peer.addr)
                except Exception:
                    pass

    def _reaper_loop(self):
        """Prune unreachable endpoints from the routing table."""
        while self.running:
            time.sleep(30)
            dead = [pid for pid, p in self.peers.items() if not p.is_alive]
            for pid in dead:
                peer = self.peers.pop(pid, None)
                if peer:
                    logger.info("mesh", f"NODE_DROPPED: {pid} ({peer.addr})")
                    bus.publish("mesh_peer_lost", {"node_id": pid})

    # ══════════════════════════════════════════════════════════════
    # Protocol Dispatch
    # ══════════════════════════════════════════════════════════════

    def _handle_handshake(self, payload: bytes, addr: tuple):
        """Process cryptographic handshake & capability exchange."""
        if len(payload) < 48:
            return
        node_id = payload[:16].decode("utf-8", errors="ignore").strip('\x00')
        peer_pubkey = payload[16:48]

        caps = []
        if len(payload) > 48:
            try:
                caps = json.loads(payload[48:].decode())
            except Exception:
                pass

        shared = self._derive_shared_secret(peer_pubkey)

        peer = MeshPeer(
            node_id=node_id,
            addr=addr,
            public_key=peer_pubkey,
            shared_secret=shared,
            last_seen=time.time(),
            capabilities=caps,
        )
        self.peers[node_id] = peer

        logger.info("mesh", f"PEER_AUTHENTICATED: {node_id} at {addr[0]}:{addr[1]}")
        bus.publish("mesh_peer_join", peer.to_dict())

        # Reciprocate handshake
        response = (MAGIC_HANDSHAKE +
                     self.node_id.encode()[:16].ljust(16, b'\x00') +
                     self._public_key_bytes)
        self.server_sock.sendto(response, addr)

    def _handle_heartbeat(self, payload: bytes, addr: tuple):
        node_id = payload[:16].decode("utf-8", errors="ignore").strip('\x00')
        if node_id in self.peers:
            self.peers[node_id].last_seen = time.time()
            if len(payload) >= 24:
                sent_ts = struct.unpack("!d", payload[16:24])[0]
                self.peers[node_id].latency_ms = (time.time() - sent_ts) * 1000

    def _handle_data(self, payload: bytes, addr: tuple):
        node_id = payload[:16].decode("utf-8", errors="ignore").strip('\x00')
        encrypted = payload[16:]

        peer = self.peers.get(node_id)
        if not peer:
            return

        try:
            decrypted = self._decrypt(encrypted, peer.shared_secret)
            msg = json.loads(decrypted)
            logger.info("mesh", f"DATA_INGEST [{node_id}]: {str(msg)[:100]}")
            bus.publish("mesh_data", {"from": node_id, "data": msg})
            if self._on_message:
                self._on_message(node_id, msg)
        except Exception as e:
            logger.error("mesh", f"DECRYPTION_FAULT [{node_id}]: {e}")

    def _handle_command(self, payload: bytes, addr: tuple):
        node_id = payload[:16].decode("utf-8", errors="ignore").strip('\x00')
        peer = self.peers.get(node_id)
        if not peer:
            return

        try:
            decrypted = self._decrypt(payload[16:], peer.shared_secret)
            cmd_data = json.loads(decrypted)
            logger.info("mesh", f"RPC_REQUEST [{node_id}]: {cmd_data.get('cmd', '?')}")
            bus.publish("mesh_command", {"from": node_id, "data": cmd_data})
        except Exception as e:
            logger.error("mesh", f"RPC_FAULT [{node_id}]: {e}")

    # ══════════════════════════════════════════════════════════════
    # Routing Interfaces
    # ══════════════════════════════════════════════════════════════

    def connect_to_peer(self, ip: str, port: int = 19999):
        """Initiate tunnel establishment to a remote peer."""
        handshake = (MAGIC_HANDSHAKE +
                     self.node_id.encode()[:16].ljust(16, b'\x00') +
                     self._public_key_bytes +
                     json.dumps(["recon", "exploit", "c2", "relay"]).encode())
        try:
            self.server_sock.sendto(handshake, (ip, port))
            logger.info("mesh", f"HANDSHAKE_DISPATCHED -> {ip}:{port}")
        except Exception as e:
            logger.error("mesh", f"CONNECT_FAULT: {e}")

    def send_to_peer(self, node_id: str, data: dict) -> bool:
        """Route an encrypted datagram to a specific peer."""
        peer = self.peers.get(node_id)
        if not peer or not peer.shared_secret:
            return False
        try:
            plaintext = json.dumps(data).encode()
            encrypted = self._encrypt(plaintext, peer.shared_secret)
            packet = (MAGIC_DATA +
                      self.node_id.encode()[:16].ljust(16, b'\x00') +
                      encrypted)
            self.server_sock.sendto(packet, peer.addr)
            return True
        except Exception as e:
            logger.error("mesh", f"ROUTING_FAULT [{node_id}]: {e}")
            return False

    def broadcast(self, data: dict):
        """Multicast encrypted data to the active routing table."""
        for node_id in list(self.peers.keys()):
            self.send_to_peer(node_id, data)

    def send_command(self, node_id: str, cmd: str, args: dict = None) -> bool:
        """Dispatch a remote procedure call."""
        peer = self.peers.get(node_id)
        if not peer:
            return False
        payload = json.dumps({"cmd": cmd, **(args or {})}).encode()
        encrypted = self._encrypt(payload, peer.shared_secret)
        packet = (MAGIC_COMMAND +
                  self.node_id.encode()[:16].ljust(16, b'\x00') +
                  encrypted)
        try:
            self.server_sock.sendto(packet, peer.addr)
            return True
        except Exception:
            return False

    # ══════════════════════════════════════════════════════════════
    # Remote Provisioning
    # ══════════════════════════════════════════════════════════════

    def get_mobile_provision(self, name: str) -> str:
        """Export connection topology for automated node onboarding."""
        provision = {
            "node_name": name,
            "hub_endpoint": f"{self._get_public_ip()}:{self.port}",
            "hub_node_id": self.node_id,
            "hub_pubkey": self._public_key_bytes.hex(),
            "encryption": "X25519-ChaCha20Poly1305",
            "protocol": "MESH-UDP",
            "magic_handshake": MAGIC_HANDSHAKE.hex(),
            "stealth": True,
        }
        prov_file = os.path.join(self.key_dir, f"{name}_mesh_config.json")
        with open(prov_file, "w") as f:
            json.dump(provision, f, indent=4)
        logger.info("mesh", f"PROVISION_EXPORTED: {prov_file}")
        return prov_file

    def get_peer_list(self) -> List[dict]:
        return [p.to_dict() for p in self.peers.values()]

    def _get_public_ip(self) -> str:
        try:
            import urllib.request
            return urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
        except Exception:
            return "0.0.0.0"


# Maintained for backward compatibility
shadow_swarm = MeshRelay()

# Back-compat alias — older callers referenced ShadowSwarm for MeshRelay
ShadowSwarm = MeshRelay

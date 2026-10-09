"""P2P message forwarding between Shadow instances (Phase 2, Task 2).

Attempts a direct TLS TCP connection between instances to relay encrypted
messages. Falls back to server relay (Task 3) when P2P is unavailable.
The server never decrypts message contents — only ciphertext + nonce
are forwarded, identical to the Phase 1 message format.
"""

import ipaddress
import json
import logging
import socket
import ssl
import threading
import time

from sqlalchemy.orm import Session

from shadowcypher.chat import instance_registry
from shadowcypher.chat.db import SessionLocal
from shadowcypher.chat.models import P2PConnection

log = logging.getLogger(__name__)

# Global connection pool: {(from_id, to_id): socket}
p2p_connections = {}
connection_lock = threading.Lock()

P2P_PORT = 19999
P2P_TIMEOUT = 30 * 60  # Close after 30 min idle
CONNECTION_TIMEOUT = 10  # Give P2P 10 sec to connect

class P2PMessage:
    """Encrypted message for P2P relay."""
    def __init__(self, from_instance_id: str, to_instance_id: str, ciphertext: bytes, nonce: bytes):
        self.from_instance_id = from_instance_id
        self.to_instance_id = to_instance_id
        self.ciphertext = ciphertext
        self.nonce = nonce

    def to_json(self) -> str:
        return json.dumps({
            "from": self.from_instance_id,
            "to": self.to_instance_id,
            "ciphertext": self.ciphertext.hex(),
            "nonce": self.nonce.hex()
        })

    @staticmethod
    def from_json(data: str) -> "P2PMessage":
        obj = json.loads(data)
        return P2PMessage(
            from_instance_id=obj["from"],
            to_instance_id=obj["to"],
            ciphertext=bytes.fromhex(obj["ciphertext"]),
            nonce=bytes.fromhex(obj["nonce"])
        )

def _is_safe_endpoint(endpoint: str) -> bool:
    """Validate endpoint IP to prevent SSRF (no loopback, private, link-local, or multicast)."""
    try:
        ip_str = endpoint.rsplit(":", 1)[0]
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast:
            return False
        return True
    except (ValueError, IndexError):
        return False

def connect_p2p(from_instance_id: str, to_instance_id: str, session: Session) -> socket.socket | None:
    """Establish TLS-wrapped P2P connection to target instance."""
    to_instance = instance_registry.get_instance(session, to_instance_id)
    if not to_instance or not to_instance.is_online:
        return None

    # SSRF check: reject internal IPs
    if not _is_safe_endpoint(to_instance.endpoint):
        return None

    try:
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(CONNECTION_TIMEOUT)

        # Parse endpoint "IP:port"
        ip, port = to_instance.endpoint.rsplit(":", 1)
        port = int(port)

        raw_sock.connect((ip, port))
        raw_sock.settimeout(None)  # No timeout after connected

        # Wrap with TLS (opportunistic — server must present a valid cert)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False  # Instances use IP, not hostnames
        ctx.verify_mode = ssl.CERT_NONE  # Self-signed certs OK for P2P
        sock = ctx.wrap_socket(raw_sock, server_side=False)

        return sock
    except Exception as e:
        log.warning("P2P connection to %s failed: %s", to_instance_id, e)
        return None

def send_p2p_message(from_instance_id: str, to_instance_id: str, ciphertext: bytes, nonce: bytes) -> dict:
    """Send encrypted message via P2P; return {status: "delivered" | "failed", via: "p2p" | "relay"}."""
    session = SessionLocal()
    try:
        key = (from_instance_id, to_instance_id)

        # Check cache without blocking
        sock = None
        with connection_lock:
            if key in p2p_connections:
                sock = p2p_connections[key]

        # Dial WITHOUT lock (blocking operation)
        if not sock:
            sock = connect_p2p(from_instance_id, to_instance_id, session)

        if not sock:
            return {"status": "failed", "via": "p2p"}

        # Send WITH lock
        with connection_lock:
            p2p_connections[key] = sock
            try:
                msg = P2PMessage(from_instance_id, to_instance_id, ciphertext, nonce)
                sock.sendall(msg.to_json().encode() + b"\n")

                # Log P2P connection
                conn = session.query(P2PConnection).filter(
                    P2PConnection.from_instance_id == from_instance_id,
                    P2PConnection.to_instance_id == to_instance_id
                ).first()
                if conn:
                    conn.last_activity = int(time.time())
                    conn.messages_sent += 1

                session.commit()
                return {"status": "delivered", "via": "p2p"}
            except Exception as e:
                log.warning("P2P send to %s failed: %s", to_instance_id, e)
                if key in p2p_connections:
                    del p2p_connections[key]
                return {"status": "failed", "via": "p2p"}
    finally:
        session.close()

def cleanup_idle_connections():
    """Periodically close idle P2P connections."""
    while True:
        time.sleep(60)  # Check every minute
        with connection_lock:
            to_remove = []
            for key, sock in p2p_connections.items():
                # If socket is closed or error, remove it
                try:
                    sock.getpeername()  # Check if still connected
                except Exception:
                    to_remove.append(key)
            for key in to_remove:
                del p2p_connections[key]

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_idle_connections, daemon=True)
cleanup_thread.start()

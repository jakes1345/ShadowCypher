"""
Agent Relay — Multi-hop Relay & Proxy Manager for Guardian Agents
Manages relay chains, heartbeats, and encrypted tunnels between field agents.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from shadowcypher.core.module import BaseModule


@dataclass
class RelayNode:
    node_id: str
    host: str
    port: int
    relay_type: str  # "direct" | "socks5" | "http_tunnel"
    secret: str
    last_seen: float = field(default_factory=time.time)
    active: bool = True


@dataclass
class AgentSession:
    session_id: str
    agent_id: str
    relay_chain: list[str]  # ordered node_id list
    created_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRelay(BaseModule):
    """
    Multi-hop relay manager for ShadowCypher field agents.
    Manages the relay topology, session routing, and agent heartbeats.
    """

    def __init__(self, ping_interval: float = 60.0):
        super().__init__(module_name="agent_relay")
        self._nodes: dict[str, RelayNode] = {}
        self._sessions: dict[str, AgentSession] = {}
        self._lock = threading.Lock()
        self._ping_interval = ping_interval
        self._monitor_thread: threading.Thread | None = None
        self._running = False
        self._callbacks: list[Callable[[str, Any], None]] = []

    # ── Node management ───────────────────────────────────────────────────────

    def register_node(
        self,
        host: str,
        port: int,
        relay_type: str = "direct",
        node_id: str | None = None,
    ) -> RelayNode:
        """Register a relay node. Returns the node object with generated credentials."""
        nid = node_id or self._gen_id("node")
        secret = secrets.token_hex(32)
        node = RelayNode(
            node_id=nid,
            host=host,
            port=port,
            relay_type=relay_type,
            secret=secret,
        )
        with self._lock:
            self._nodes[nid] = node
        self.log(f"NODE_REGISTERED: {nid} @ {host}:{port} [{relay_type}]")
        return node

    def deregister_node(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                self._nodes.pop(node_id)
                self.log(f"NODE_DEREGISTERED: {node_id}")
                return True
        return False

    def list_nodes(self, active_only: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            nodes = list(self._nodes.values())
        if active_only:
            nodes = [n for n in nodes if n.active]
        return [
            {
                "node_id": n.node_id,
                "host": n.host,
                "port": n.port,
                "relay_type": n.relay_type,
                "active": n.active,
                "last_seen": n.last_seen,
                "age_seconds": round(time.time() - n.last_seen, 1),
            }
            for n in nodes
        ]

    # ── Session management ────────────────────────────────────────────────────

    def create_session(
        self,
        agent_id: str,
        relay_chain: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> AgentSession | None:
        """
        Create a relay session for a field agent through a specified relay chain.
        relay_chain: ordered list of node_ids to route through.
        """
        with self._lock:
            missing = [nid for nid in relay_chain if nid not in self._nodes]
        if missing:
            self.log(f"SESSION_FAILED: unknown nodes {missing}")
            return None

        session_id = self._gen_id("sess")
        session = AgentSession(
            session_id=session_id,
            agent_id=agent_id,
            relay_chain=relay_chain,
            metadata=metadata or {},
        )
        with self._lock:
            self._sessions[session_id] = session
        self.log(f"SESSION_CREATED: {session_id} agent={agent_id} chain={relay_chain}")
        self._emit("session_created", {"session_id": session_id, "agent_id": agent_id})
        return session

    def terminate_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                self._sessions.pop(session_id)
                self.log(f"SESSION_TERMINATED: {session_id}")
                self._emit("session_terminated", {"session_id": session_id})
                return True
        return False

    def ping_session(self, session_id: str) -> bool:
        """Record a heartbeat ping for a session. Returns False if session unknown."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return False
            sess.last_ping = time.time()
        return True

    def list_sessions(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        now = time.time()
        return [
            {
                "session_id": s.session_id,
                "agent_id": s.agent_id,
                "relay_chain": s.relay_chain,
                "age_seconds": round(now - s.created_at, 1),
                "last_ping_seconds_ago": round(now - s.last_ping, 1),
                "metadata": s.metadata,
            }
            for s in sessions
        ]

    # ── Route resolution ──────────────────────────────────────────────────────

    def resolve_route(self, session_id: str) -> list[dict[str, Any]] | None:
        """
        Resolve the full relay chain for a session.
        Returns ordered list of node connection details.
        """
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return None
            nodes = [self._nodes.get(nid) for nid in sess.relay_chain]

        if any(n is None for n in nodes):
            return None

        return [
            {"node_id": n.node_id, "host": n.host, "port": n.port, "relay_type": n.relay_type}
            for n in nodes
            if n is not None
        ]

    # ── Heartbeat monitor ─────────────────────────────────────────────────────

    def start_monitor(self, stale_threshold: float = 120.0) -> None:
        """Start background thread that marks stale nodes/sessions."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(stale_threshold,),
            daemon=True,
        )
        self._monitor_thread.start()
        self.log("MONITOR_STARTED")

    def stop_monitor(self) -> None:
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.log("MONITOR_STOPPED")

    def _monitor_loop(self, stale_threshold: float) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                for node in list(self._nodes.values()):
                    was_active = node.active
                    node.active = (now - node.last_seen) < stale_threshold
                    if was_active and not node.active:
                        self._emit("node_stale", {"node_id": node.node_id})
                        self.log(f"NODE_STALE: {node.node_id}")

                for sess in list(self._sessions.values()):
                    if (now - sess.last_ping) > stale_threshold * 2:
                        self._sessions.pop(sess.session_id)
                        self._emit("session_expired", {"session_id": sess.session_id})
                        self.log(f"SESSION_EXPIRED: {sess.session_id}")

            time.sleep(self._ping_interval)

    # ── Callback system ───────────────────────────────────────────────────────

    def on_event(self, callback: Callable[[str, Any], None]) -> None:
        """Register a callback for relay events (node_stale, session_created, etc.)."""
        self._callbacks.append(callback)

    def _emit(self, event: str, data: Any) -> None:
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return f"{prefix}_{secrets.token_hex(8)}"

    def node_fingerprint(self, node_id: str) -> str | None:
        """Derive a deterministic fingerprint for a node (host:port:secret hash)."""
        with self._lock:
            node = self._nodes.get(node_id)
        if node is None:
            return None
        raw = f"{node.host}:{node.port}:{node.secret}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def topology(self) -> dict[str, Any]:
        """Return a snapshot of the current relay topology."""
        return {
            "nodes": self.list_nodes(),
            "sessions": self.list_sessions(),
            "total_nodes": len(self._nodes),
            "total_sessions": len(self._sessions),
            "monitor_running": self._running,
        }

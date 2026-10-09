"""
ShadowCypher Nexus Relay — Sovereign UDP/TCP/WebRTC Orchestrator.
Provides dynamic CoTURN credentials, NAT traversal, and CORS-enabled protocol bridges.
Ported from TAZHER forensic architecture.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Dict, Optional

from aiohttp import web

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


class NexusRelay:
    """
    The Nexus Relay provides:
    1. Dynamic TURN/STUN credentials (shared secret auth).
    2. CORS-enabled REST API for protocol handshakes.
    3. UDP/TCP Relay orchestration for P2P bypass.
    4. Sovereign Node Discovery & Registration.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9988):
        self.host = os.environ.get("SHADOWCYPHER_NEXUS_HOST", host)
        self.port = int(os.environ.get("SHADOWCYPHER_NEXUS_PORT", port))
        secret = os.environ.get("SHADOWCYPHER_HUB_SECRET") or config.get("nexus", "hub_secret", default=None)
        if not secret or secret == "REPLACE_WITH_SECURE_HUB_SECRET":
            logger.warning("nexus", "HUB_SECRET unset — running in no-auth mode. Set SHADOWCYPHER_HUB_SECRET for production.")
            secret = ""
        self.secret = secret
        self._auth_enabled = bool(secret)
        self.nodes_file = os.path.join(str(config.project_root), "nodes.json")
        self.nodes: Dict[str, dict] = self._load_nodes()
        self.app = web.Application()
        self._setup_routes()

    def _load_nodes(self) -> Dict[str, dict]:
        """Deep-dive persistence: Recovery of the signal plane."""
        if os.path.exists(self.nodes_file):
            try:
                with open(self.nodes_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_nodes(self):
        """Persistent snapshot of the swarm."""
        try:
            with open(self.nodes_file, "w") as f:
                json.dump(self.nodes, f)
        except Exception:
            pass

    def _setup_routes(self):
        self.app.router.add_get("/api/nexus/ice", self.handle_ice_request)
        self.app.router.add_get("/api/nexus/status", self.handle_status)
        self.app.router.add_get("/api/nexus/tunnel", self.handle_tunnel)
        self.app.router.add_get("/api/nexus/nodes", self.handle_list_nodes)
        self.app.router.add_get("/api/nexus/swarm", self.handle_swarm_sync)
        self.app.router.add_post("/api/nexus/register", self.handle_register_node)
        self.app.router.add_options("/{tail:.*}", self.handle_options)
        self.app.middlewares.append(self.cors_middleware)

    @staticmethod
    def _allowed_origin(request) -> str:
        """Match request Origin against SHADOWCYPHER_ALLOWED_ORIGINS whitelist.

        Env var is comma-separated (e.g. "https://shadowcypher.site,https://app.shadowcypher.site").
        Returns the echoed Origin if allowed, else empty string (browser will block).
        Default whitelist is https://shadowcypher.site only — no `*` wildcard.
        """
        raw = os.environ.get("SHADOWCYPHER_ALLOWED_ORIGINS", "https://shadowcypher.site")
        allowed = {o.strip() for o in raw.split(",") if o.strip()}
        origin = request.headers.get("Origin", "")
        return origin if origin in allowed else ""

    @web.middleware
    async def cors_middleware(self, request, handler):
        if request.method == "OPTIONS":
            return await self.handle_options(request)
        response = await handler(request)
        allowed = self._allowed_origin(request)
        if allowed:
            response.headers["Access-Control-Allow-Origin"] = allowed
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Vary"] = "Origin"
        return response

    async def handle_options(self, request):
        allowed = self._allowed_origin(request)
        if not allowed:
            return web.Response(status=403)
        return web.Response(status=204, headers={
            "Access-Control-Allow-Origin": allowed,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
            "Vary": "Origin",
        })

    async def handle_status(self, request):
        return web.json_response({
            "status": "OPERATIONAL",
            "node": "NEXUS-ALPHA",
            "load": 0.0,
            "uptime": int(time.time()),
            "protocols": ["UDP", "TCP", "TURN", "STUN"]
        })

    async def handle_ice_request(self, request):
        user_nick = request.query.get("nick", "anonymous")
        timestamp = int(time.time()) + 36000
        username = f"{timestamp}:{user_nick}"
        password = hmac.HMAC(self.secret.encode(), username.encode(), hashlib.sha256).digest()
        password_b64 = base64.b64encode(password).decode()

        return web.json_response({
            "username": username,
            "password": password_b64,
            "ttl": 36000,
            "iceServers": [
                {"urls": "stun:stun.l.google.com:19302"},
                {"urls": "turn:turn.shadowcypher.site:3478", "username": username, "credential": password_b64}
            ]
        })

    async def handle_register_node(self, request):
        try:
            data = await request.json()
            node_id = data.get("id")
            if not node_id:
                return web.json_response({"error": "Missing node ID"}, status=400)

            self.nodes[node_id] = {
                "addr": request.remote,
                "info": data.get("info", {}),
                "last_seen": int(time.time())
            }
            self._save_nodes()
            return web.json_response({"status": "REGISTERED", "id": node_id})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_list_nodes(self, request):
        return web.json_response(self.nodes)

    async def handle_tunnel(self, request):
        target = request.query.get("target")
        if not target or target not in self.nodes:
            return web.json_response({"error": "Target node not found"}, status=404)
        return web.json_response({"endpoint": self.nodes[target]["addr"]})

    async def handle_swarm_sync(self, request):
        return web.json_response({"swarm_count": len(self.nodes), "peers": list(self.nodes.keys())})

    def start(self):
        logger.info("nexus", f"STARTING_NEXUS_RELAY on {self.host}:{self.port}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runner = web.AppRunner(self.app)
        loop.run_until_complete(runner.setup())

        # Try up to 5 consecutive ports if the primary is already in use
        bound_port = None
        for attempt in range(5):
            candidate = self.port + attempt
            site = web.TCPSite(runner, self.host, candidate)
            try:
                loop.run_until_complete(site.start())
                bound_port = candidate
                break
            except OSError as e:
                import errno
                if e.errno == errno.EADDRINUSE:
                    logger.warning(
                        "nexus",
                        f"NEXUS_PORT_BUSY: {candidate} in use — trying {candidate + 1}",
                    )
                    loop.run_until_complete(site.stop())
                else:
                    raise

        if bound_port is None:
            logger.error("nexus", f"NEXUS_STARTUP_FAILED: all ports {self.port}–{self.port + 4} busy")
            loop.run_until_complete(runner.cleanup())
            return

        if bound_port != self.port:
            logger.warning("nexus", f"NEXUS_RELAY: fell back to port {bound_port}")
        else:
            logger.info("nexus", f"NEXUS_RELAY: listening on {self.host}:{bound_port}")

        loop.run_forever()

# Lazy singleton — building NexusRelay() now would fail-fast on missing hub secret,
# which would break `import shadowcypher.core.nexus` in CI/test contexts.
_nexus_instance: Optional[NexusRelay] = None

def get_nexus() -> NexusRelay:
    global _nexus_instance
    if _nexus_instance is None:
        _nexus_instance = NexusRelay()
    return _nexus_instance

class _NexusProxy:
    """Backwards-compatible proxy: legacy callers do `from .nexus import nexus; nexus.start()`."""
    def __getattr__(self, name):
        return getattr(get_nexus(), name)

nexus = _NexusProxy()

if __name__ == "__main__":
    get_nexus().start()

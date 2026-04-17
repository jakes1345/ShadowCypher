"""
ShadowCypher Nexus Relay — Sovereign UDP/TCP/WebRTC Orchestrator.
Provides dynamic CoTURN credentials, NAT traversal, and CORS-enabled protocol bridges.
Ported from TAZHER forensic architecture.
"""

import os
import json
import asyncio
import hmac
import hashlib
import time
import base64
from typing import Dict, Any, Optional, List
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

    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.secret = config.get("irc", "hub_secret", default="shadow_master_secret")
        self.nodes: Dict[str, dict] = {} # node_id -> metadata
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/api/nexus/ice", self.handle_ice_request)
        self.app.router.add_get("/api/nexus/status", self.handle_status)
        self.app.router.add_get("/api/nexus/tunnel", self.handle_tunnel)
        self.app.router.add_get("/api/nexus/nodes", self.handle_list_nodes)
        self.app.router.add_get("/api/nexus/swarm", self.handle_swarm_sync) # P2P SWARM SYNC
        self.app.router.add_post("/api/nexus/register", self.handle_register_node)
        self.app.router.add_options("/{tail:.*}", self.handle_options)
        self.app.middlewares.append(self.cors_middleware)

    @web.middleware
    async def cors_middleware(self, request, handler):
        """Universal CORS bridge for cross-origin tactical UIs."""
        if request.method == "OPTIONS":
            return await self.handle_options(request)
        
        response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    async def handle_options(self, request):
        return web.Response(status=204, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
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
        """
        Generates time-limited TURN/STUN credentials for WebRTC/P2P bypass.
        Format: username=timestamp:nick, password=hmac(secret, username)
        """
        user_nick = request.query.get("nick", "anonymous")
        timestamp = int(time.time()) + 36000  # 10 hour validity
        username = f"{timestamp}:{user_nick}"
        
        # CoTURN style shared secret auth
        password = base64.b64encode(
            hmac.new(self.secret.encode(), username.encode(), hashlib.sha256).digest()
        ).decode()

        relay_host = config.get("irc", "sovereign_server", default="127.0.0.1")
        
        ice_servers = [
            {"urls": f"stun:{relay_host}:3478"},
            {
                "urls": f"turn:{relay_host}:3478?transport=udp",
                "username": username,
                "credential": password
            },
            {
                "urls": f"turn:{relay_host}:3478?transport=tcp",
                "username": username,
                "credential": password
            }
        ]

        logger.info("nexus", f"ICE_CREDENTIALS_GENERATED: {user_nick} (exp: {timestamp})")
        return web.json_response({"iceServers": ice_servers})

    async def handle_tunnel(self, request):
        """
        WebSocket-over-CORS Tunnel. 
        Enables raw TCP/UDP proxying from browsers or restricted networks 
        through the Nexus Relay protocol.
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        target_reader = None
        target_writer = None

        try:
            # First frame must be config
            msg = await ws.receive()
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                host = data.get("host")
                port = data.get("port")
                proto = data.get("proto", "tcp")
                
                logger.info("nexus", f"TUNNEL_INITIATED: {proto}://{host}:{port}")
                
                if proto == "tcp":
                    target_reader, target_writer = await asyncio.open_connection(host, port)
                    
                    async def ws_to_tcp():
                        try:
                            async for m in ws:
                                if m.type == web.WSMsgType.BINARY:
                                    target_writer.write(m.data)
                                    await target_writer.drain()
                                elif m.type == web.WSMsgType.CLOSE:
                                    break
                        except Exception:
                            pass
                        finally:
                            if target_writer:
                                target_writer.close()

                    async def tcp_to_ws():
                        try:
                            while not ws.closed:
                                chunk = await target_reader.read(8192)
                                if not chunk:
                                    break
                                await ws.send_bytes(chunk)
                        except Exception:
                            pass
                        finally:
                            await ws.close()

                    await asyncio.gather(ws_to_tcp(), tcp_to_ws())
        except Exception as e:
            logger.error("nexus", f"TUNNEL_FATAL_ERROR: {e}")
        finally:
            if not ws.closed:
                await ws.close()
            return ws

    async def handle_list_nodes(self, request):
        """Returns a list of active Sovereign hubs registered with this Nexus."""
        # Filter stale nodes (> 5 mins)
        now = time.time()
        active_nodes = {k: v for k, v in self.nodes.items() if now - v["last_seen"] < 300}
        return web.json_response(active_nodes)

    async def handle_register_node(self, request):
        """Allows a Sovereign hub to announce its existence to the network."""
        try:
            data = await request.json()
            node_id = data.get("node_id")
            if not node_id:
                return web.Response(status=400, text="MISSING_NODE_ID")
            
            self.nodes[node_id] = {
                "host": data.get("host", request.remote),
                "port": data.get("port", 8888),
                "name": data.get("name", "ShadowNode"),
                "load": data.get("load", 0.0),
                "users": data.get("users", 0),
                "last_seen": time.time()
            }
            logger.info("nexus", f"NODE_REGISTERED: {node_id} at {self.nodes[node_id]['host']}:{self.nodes[node_id]['port']}")
            return web.json_response({"status": "REGISTERED"})
        except Exception as e:
            return web.Response(status=500, text=str(e))

    async def handle_swarm_sync(self, request):
        """Returns a list of active P2P Swarm Nodes for the ShadowScript Engine."""
        now = time.time()
        peers = [f"{v['host']}:{v['port']}" for v in self.nodes.values() if now - v["last_seen"] < 600]
        return web.json_response({"peers": peers, "version": "1.0-SWARM"})

    async def start(self):
        """Launch the Nexus Relay service with NetBoozt socket optimizations."""
        import socket
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        # Optimize parent listener socket
        site = web.TCPSite(runner, self.host, self.port, backlog=128)
        await site.start()
        
        logger.info("nexus", f"NEXUS_RELAY: Swarm-Optimized bridge active on {self.host}:{self.port}")

# Global instance for orchestration
nexus = NexusRelay()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(nexus.start())
    loop.run_forever()

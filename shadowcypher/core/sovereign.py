"""
ShadowCypher Sovereign Server — Xat-Grade JSON Coordination Hub.
Features: Hybrid JSON protocol, Power-aware RBAC, AI-Stream bridging.
"""

import asyncio
import json
import websockets
import time
import uuid
import hmac
import hashlib
from typing import Dict, Set, Any, Optional
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class SovereignServer:
    def __init__(self, host="127.0.0.1", port=8888):
        self.host = host
        self.port = port
        self.clients: Dict[str, Any] = {}
        self.user_data: Dict[str, Any] = {} # nick -> metadata
        self.channels = ["#general", "#intel", "#missions", "#chaos"]
        self.rooms: Dict[str, Set[str]] = {chan: set() for chan in self.channels}
        self._ip_locks: Dict[str, float] = {} 
        self._xp_db: Dict[str, int] = {} # Nick -> XP (Simple in-memory for now)

    async def start(self) -> None:
        """Launches the Sovereign Web-Room engine on the Obsidian Citadel bus."""
        # 1. Primary Terminal Hub
        server = websockets.serve(self._handle_connection, self.host, self.port)
        
        # 2. Encrypted Ghost Port for Emergency Persistence
        ghost_port = config.get("irc", "hub_ghost_port", default=44444)
        ghost_server = websockets.serve(self._handle_connection, self.host, ghost_port)
        
        # 3. Bus Bridge: Broadcast internal messages to external clients
        def on_sovereign_broadcast(packet):
            if packet.get("source") == "external":
                return
            # Use current event loop to broadcast
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._broadcast(packet))
            except: pass

        bus.subscribe("sovereign_in", on_sovereign_broadcast)

        logger.info("server", f"SOVEREIGN_SERVER: Active on {self.port} & Ghost_{ghost_port}")
        
        async with server, ghost_server:
            await asyncio.Future()  # Run forever

    async def _handle_connection(self, ws, path):
        remote_ip = ws.remote_address[0]
        challenge = uuid.uuid4().hex
        nick = "Unknown"
        
        try:
            await ws.send(json.dumps({"type": "auth_req", "challenge": challenge}))
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            
            if data.get("type") != "auth_proof":
                raise ConnectionError("INVALID_HANDSHAKE_TYPE")
                
            proof = data.get("proof", "")
            secret = config.get("irc", "hub_secret", default="shadow_secret")
            expected = hmac.new(secret.encode(), challenge.encode(), hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(proof, expected):
                await ws.send(json.dumps({"type": "error", "text": "ACCESS_DENIED: PROOF_MISMATCH"}))
                await ws.close()
                return

            nick = data.get("nick", "Guest_" + uuid.uuid4().hex[:4])
            chan = data.get("channel", "#general")
            self.clients[nick] = ws
            self.rooms[chan].add(nick)
            
            self.user_data[nick] = {
                "nick": nick,
                "power": "mod" if nick in config.get("identity", "admin_list", default=[]) else "default",
                "xp": self._xp_db.get(nick, 0),
                "level": (self._xp_db.get(nick, 0) // 100) + 1,
                "channel": chan,
                "status": "online",
                "ip": remote_ip
            }
            
            await self._broadcast({
                "type": "sys",
                "text": f"[*] {nick} joined (AUTHENTICATED).",
                "nick": nick,
                "channel": chan
            })
            await self._sync_users()
            
            async for message in ws:
                now = time.time()
                if now - self._ip_locks.get(remote_ip, 0) < 0.5:
                    continue 
                self._ip_locks[remote_ip] = now
                
                data = json.loads(message)
                if data.get("type") == "chat":
                    bus.publish("sovereign_in", {
                        "type": "chat",
                        "nick": nick,
                        "text": data.get("text"),
                        "channel": chan,
                        "power": self.user_data[nick]["power"],
                        "level": self.user_data[nick]["level"],
                        "source": "external"
                    })
                
                await self._process_command(nick, data)
                
        except Exception as e:
            if not isinstance(e, websockets.exceptions.ConnectionClosed):
                logger.error("server", f"HUB_CONN_ERROR: {e}")
            await ws.close()
        finally:
            await self._cleanup(nick)

    async def _process_command(self, nick: str, data: dict):
        msg_type = data.get("type")
        chan = self.user_data[nick]["channel"]
        
        if msg_type == "chat":
            self._xp_db[nick] = self._xp_db.get(nick, 0) + 5
            self.user_data[nick]["xp"] = self._xp_db[nick]
            self.user_data[nick]["level"] = (self._xp_db[nick] // 100) + 1
            
            await self._broadcast({
                "type": "chat",
                "nick": nick,
                "channel": chan,
                "text": data.get("text"),
                "power": self.user_data[nick]["power"],
                "level": self.user_data[nick]["level"],
                "time": time.time()
            })
            
        elif msg_type == "switch_channel":
            new_chan = data.get("channel")
            if new_chan in self.channels:
                self.rooms[chan].remove(nick)
                self.rooms[new_chan].add(nick)
                self.user_data[nick]["channel"] = new_chan
                await self._sync_users()

    async def _broadcast(self, packet):
        target_chan = packet.get("channel")
        msg = json.dumps(packet)
        if target_chan and target_chan in self.rooms:
            recipients = [self.clients[n] for n in self.rooms[target_chan] if n in self.clients]
            if recipients:
                # Optimized multi-send
                await asyncio.gather(*[ws.send(msg) for ws in recipients], return_exceptions=True)
        else:
            if self.clients:
                await asyncio.gather(*[ws.send(msg) for ws in self.clients.values()], return_exceptions=True)

    async def _sync_users(self):
        await self._broadcast({
            "type": "user_sync",
            "users": list(self.user_data.values())
        })

    async def _cleanup(self, nick):
        if nick in self.clients: del self.clients[nick]
        if nick in self.user_data: del self.user_data[nick]
        await self._broadcast({"type": "sys", "text": f"[-] {nick} left.", "nick": nick})
        await self._sync_users()

if __name__ == "__main__":
    srv = SovereignServer()
    asyncio.run(srv.start())

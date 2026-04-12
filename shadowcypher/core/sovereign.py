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
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

class SovereignServer:
    def __init__(self, host="127.0.0.1", port=8888):
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.user_data: Dict[str, dict] = {} # nick -> metadata
        # Discord-style channels
        self.channels = ["#general", "#intel", "#missions", "#chaos"]
        self.rooms: Dict[str, Set[str]] = {chan: set() for chan in self.channels}
        self._ip_locks: Dict[str, float] = {} # IP -> last_msg_time (Rate limit)
        
    async def start(self):
        # 1. Primary Terminal Hub
        main_task = asyncio.create_task(
            websockets.serve(self._handle_connection, self.host, self.port)
        )
        # 2. Encrypted Ghost Port for Emergency Persistence
        ghost_port = config.get("irc", "hub_ghost_port", default=44444)
        ghost_task = asyncio.create_task(
            websockets.serve(self._handle_connection, self.host, ghost_port)
        )
        
        # 3. Bus Bridge: Broadcast internal messages to external clients
        def on_sovereign_broadcast(packet):
            # Only broadcast if it's not from a local loop
            if packet.get("source") == "external":
                return
            asyncio.run_coroutine_threadsafe(self._broadcast(packet), asyncio.get_event_loop())

        bus.subscribe("sovereign_in", on_sovereign_broadcast)

        logger.info("server", f"CITADEL_HUB_HARDENED: Active on {self.port} & Ghost_{ghost_port}")
        await asyncio.gather(main_task, ghost_task)

    async def _handle_connection(self, ws, path):
        # SECURITY_HANDSHAKE: Required for Sovereign Clearance
        remote_ip = ws.remote_address[0]
        challenge = uuid.uuid4().hex
        nick = "Unknown"
        
        try:
            # 1. Send Challenge
            await ws.send(json.dumps({"type": "auth_req", "challenge": challenge}))
            
            # 2. Wait for Proof (Strict 3s Timeout)
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            
            if data.get("type") != "auth_proof":
                raise ConnectionError("INVALID_HANDSHAKE_TYPE")
                
            proof = data.get("proof", "")
            secret = config.get("irc", "hub_secret")
            expected = hmac.new(secret.encode(), challenge.encode(), hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(proof, expected):
                logger.error("server", f"AUTH_FAILED: IP {remote_ip} provided invalid proof.")
                await ws.send(json.dumps({"type": "error", "text": "ACCESS_DENIED: PROOF_MISMATCH"}))
                await ws.close()
                return

            # Success -> Proceed to session init
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
                "avatar": None,
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
                # RATE_LIMITING: Max 1 message per 0.5s per IP
                now = time.time()
                last = self._ip_locks.get(remote_ip, 0)
                if now - last < 0.5:
                    continue 
                self._ip_locks[remote_ip] = now
                
                data = json.loads(message)
                
                # Publish to ShadowBus so internal UI and Bots see it
                if data.get("type") == "chat":
                    bus.publish("sovereign_in", {
                        "type": "chat",
                        "nick": nick,
                        "text": data.get("text"),
                        "channel": chan,
                        "power": self.user_data[nick]["power"],
                        "level": self.user_data[nick]["level"],
                        "source": "external" # Prevent echo
                    })
                
                await self._process_command(nick, data)
                
        except asyncio.TimeoutError:
            logger.warn("server", f"AUTH_TIMEOUT: Peer {remote_ip} failed to respond in time.")
            await ws.close()
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
            # XP Gain for participation
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
                "avatar": self.user_data[nick]["avatar"],
                "time": time.time()
            })
            
        elif msg_type == "switch_channel":
            new_chan = data.get("channel")
            if new_chan in self.channels:
                self.rooms[chan].remove(nick)
                self.rooms[new_chan].add(nick)
                self.user_data[nick]["channel"] = new_chan
                await self._sync_users()

        elif msg_type == "embed":
            # Discord-style rich embed (Missions, Intel, Chaos)
            await self._broadcast({
                "type": "embed",
                "nick": nick,
                "channel": chan,
                "title": data.get("title"),
                "color": data.get("color", "#00d4ff"),
                "fields": data.get("fields", {}),
                "footer": data.get("footer", "ShadowCypher Apex")
            })

    async def _broadcast(self, packet):
        # Channel-aware broadcoast
        target_chan = packet.get("channel")
        msg = json.dumps(packet)
        if target_chan and target_chan in self.rooms:
            recipients = [self.clients[n] for n in self.rooms[target_chan] if n in self.clients]
            if recipients:
                await asyncio.wait([ws.send(msg) for ws in recipients])
        else:
            # Global broadcast
            if self.clients:
                await asyncio.wait([ws.send(msg) for ws in self.clients.values()])

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
    hub = SovereignServer()
    asyncio.run(hub.start())

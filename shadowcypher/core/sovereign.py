"""
ShadowCypher Sovereign Client — High-Fidelity Signal Plane Interface.
WebSocket-based JSON protocol for the native Swarm Relay and Ergo bridge.
"""

import asyncio
import json
import websockets
import threading
import time
from typing import Dict, List, Callable, Any, Optional
from shadowcypher.core.logger import logger

class SovereignClient:
    """
    Asynchronous WebSocket client for the Sovereign communication fabric.
    Supports event-based callbacks and real-time tactical signal ingest.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8888, nick: str = "Operator"):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}/ws"
        self.nick = nick
        self._callbacks: Dict[str, List[Callable]] = {}
        self._user_modes: Dict[str, str] = {}
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def on(self, event: str, cb: Callable):
        """Registers a tactical callback for a specific signal type."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(cb)

    def _trigger(self, event: str, data: Any):
        """Internal dispatcher for inbound signals."""
        if event in self._callbacks:
            for cb in self._callbacks[event]:
                try:
                    cb(data)
                except Exception as e:
                    logger.error("sovereign", f"Callback error in {event}: {e}")

    async def connect(self):
        """Main connection loop with automated handshake and recovery."""
        self._running = True
        self._loop = asyncio.get_running_loop()
        
        while self._running:
            try:
                logger.info("sovereign", f"Connecting to signal plane at {self.uri}...")
                async with websockets.connect(self.uri, ping_interval=20, ping_timeout=10) as ws:
                    self._websocket = ws
                    
                    # Sovereign Handshake
                    await self.send({
                        "type": "auth",
                        "nick": self.nick,
                        "timestamp": time.time()
                    })
                    
                    self._trigger("sys", {"text": "SOVEREIGN_LINK_ESTABLISHED: Synchronized with signal plane."})
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            typ = data.get("type", "chat")
                            
                            # Update local state if it's a protocol message
                            if typ == "userlist":
                                users = data.get("users", [])
                                self._user_modes = {u['nick']: u.get('prefix', '') for u in users if isinstance(u, dict)}
                            elif typ == "join":
                                nick = data.get("nick")
                                if nick: self._user_modes[nick] = data.get("prefix", "")
                            elif typ == "part" or typ == "quit":
                                nick = data.get("nick")
                                if nick in self._user_modes: del self._user_modes[nick]
                            
                            elif typ == "unmask_report":
                                # Forensic ingest: Unmasked node metadata
                                nick = data.get("nick")
                                report = data.get("report", {})
                                from shadowcypher.core.forensics import registry
                                registry.register_threat({
                                    "id": f"SOV-{nick}",
                                    "handle": nick,
                                    "hostmask": data.get("hostmask", "UNK"),
                                    "local_ips": report.get("local_ips", []),
                                    "hw_mac": report.get("hw_mac", "UNK"),
                                    "risk_level": "HIGH",
                                    "status": "UNMASKED"
                                })
                            
                            self._trigger(typ, data)
                        except json.JSONDecodeError:
                            logger.warning("sovereign", f"Received malformed signal: {message}")
            except Exception as e:
                self._websocket = None
                if self._running:
                    logger.warning("sovereign", f"Signal plane disconnect: {e}. Retrying in 5s...")
                    self._trigger("sys", {"text": "SIGNAL_LOST: Re-synchronizing..."})
                    await asyncio.sleep(5)
            else:
                break # Clean shutdown

    async def send(self, data: dict):
        """Injects a JSON signal into the WebSocket stream."""
        if self._websocket and self._websocket.open:
            try:
                await self._websocket.send(json.dumps(data))
            except Exception as e:
                logger.error("sovereign", f"Signal injection failed: {e}")

    def send_message(self, text: str, channel: str = "#general"):
        """Public API for sending channel messages."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.send({"type": "chat", "channel": channel, "text": text, "nick": self.nick}),
                self._loop
            )

    def send_private(self, target: str, text: str):
        """Public API for private communication."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.send({"type": "pm", "target": target, "text": text, "nick": self.nick}),
                self._loop
            )

    def register_nick(self, password: str, email: str = "operator@shadowcypher.site"):
        """Registers the current nick with NickServ on the Sovereign server."""
        self.send_message(f"NS REGISTER {password} {email}", "NickServ")

    def register_channel(self, channel: str, desc: str = "ShadowCypher Tactical"):
        """Registers a channel with ChanServ."""
        self.send_message(f"CS REGISTER {channel} {desc}", "ChanServ")

    def identify(self, password: str):
        """Identifies with NickServ."""
        self.send_message(f"NS IDENTIFY {password}", "NickServ")

    def unmask_user(self, nick: str):
        """Requests a high-fidelity unmasking report for a specific nick."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.send({"type": "unmask", "target": nick}),
                self._loop
            )

    def get_user_prefix(self, nick: str) -> str:
        """Retrieves the tactical status prefix (@, +, etc.) for a specific nick."""
        return self._user_modes.get(nick, "")

    def disconnect(self, reason: str = "Signing off"):
        """Terminates the signal plane connection."""
        self._running = False
        if self._loop and self._websocket:
            asyncio.run_coroutine_threadsafe(self._websocket.close(), self._loop)
        self._trigger("disconnect", {"reason": reason})

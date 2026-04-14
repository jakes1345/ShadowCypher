"""
ShadowCypher Sovereign Server — Full IRC-Grade Encrypted Chat Hub.
All the features of Libera/freenode IRC but self-hosted, no backdoors,
E2E encrypted DMs that are NEVER logged or stored.
"""

import asyncio
import json
import time
import uuid
import hmac
import hashlib
import base64
from typing import Dict, Set, Any, Optional, List
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

import websockets


# ── Channel Modes ────────────────────────────────────────────────
# +i = invite-only, +k = key (password), +s = secret (hidden from list),
# +m = moderated (only ops/voiced can talk), +t = only ops set topic
DEFAULT_CHAN_MODES = "+t"


class Channel:
    """IRC-style channel with modes, topic, ops, bans, invites."""

    def __init__(self, name: str, topic: str = "", modes: str = DEFAULT_CHAN_MODES,
                 key: str = ""):
        self.name = name
        self.topic = topic
        self.topic_setter = ""
        self.topic_time: float = 0
        self.modes = set(modes.replace("+", ""))
        self.key = key                          # channel password (+k)
        self.users: Set[str] = set()            # nicks in channel
        self.ops: Set[str] = set()              # @operators
        self.voiced: Set[str] = set()           # +voiced users
        self.bans: Set[str] = set()             # banned nicks
        self.invites: Set[str] = set()          # invited nicks (for +i)
        self.created: float = time.time()

    def can_talk(self, nick: str) -> bool:
        """Check if user can send messages (respects +m moderated)."""
        if "m" not in self.modes:
            return True
        return nick in self.ops or nick in self.voiced

    def can_join(self, nick: str, key: str = "") -> tuple:
        """Check if user can join. Returns (allowed, reason)."""
        if nick in self.bans:
            return False, "You are banned from this channel"
        if "i" in self.modes and nick not in self.invites:
            return False, "Channel is invite-only (+i)"
        if "k" in self.modes and self.key and key != self.key:
            return False, "Bad channel key (+k)"
        return True, ""


MOTD = [
    "  ╔═══════════════════════════════════════════════════╗",
    "  ║       SOVEREIGN CHAT — ShadowCypher Network       ║",
    "  ║                                                   ║",
    "  ║  Private. Encrypted. No logs on DMs. Ever.        ║",
    "  ║                                                   ║",
    "  ║  Commands: /nick /topic /me /whois /join /part     ║",
    "  ║           /invite /kick /ban /mode /list /motd     ║",
    "  ║           /dm <nick> <message>                     ║",
    "  ║                                                   ║",
    "  ║  Channel modes: +i invite-only  +k key/password   ║",
    "  ║                 +m moderated    +t ops-set-topic   ║",
    "  ║                 +s secret                          ║",
    "  ║                                                   ║",
    "  ║  DMs are end-to-end encrypted and NEVER stored.   ║",
    "  ╚═══════════════════════════════════════════════════╝",
]


class SovereignServer:
    """
    Full IRC-grade chat server. Channel messages logged. DMs encrypted
    and NEVER logged or stored — not on disk, not in memory after delivery.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8888):
        self.host = host
        self.port = port
        self.clients: Dict[str, Any] = {}          # nick -> websocket
        self.user_data: Dict[str, dict] = {}        # nick -> metadata
        self._rate_limits: Dict[str, float] = {}    # ip -> last_msg_time
        self._ban_list: Set[str] = set()             # banned IPs
        self._xp_db: Dict[str, int] = {}             # nick -> XP
        self._user_pubkeys: Dict[str, bytes] = {}    # nick -> X25519 public key
        self._registered_nicks: Dict[str, str] = {}  # nick -> password hash (NickServ)
        self._identified: Set[str] = set()           # nicks that identified this session

        # Default channels
        self.channels: Dict[str, Channel] = {}
        for name in ["#general", "#intel", "#missions", "#chaos", "#dev"]:
            self.channels[name] = Channel(name)
        self.channels["#general"].topic = "Welcome to ShadowCypher Sovereign"
        self.channels["#general"].topic_setter = "system"
        self.channels["#general"].topic_time = time.time()

    async def start(self) -> None:
        """Launch the Sovereign server."""
        ghost_port = config.get("irc", "hub_ghost_port", default=44444)

        # Bus bridge
        def on_bus_broadcast(packet):
            if packet.get("source") == "external":
                return
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._broadcast_channel(
                        packet.get("channel", "#general"), packet
                    ))
            except Exception:
                pass

        bus.subscribe("sovereign_in", on_bus_broadcast)
        logger.info("server", f"SOVEREIGN_SERVER: Listening on {self.host}:{self.port} & ghost:{ghost_port}")

        async with websockets.serve(self._handle_connection, self.host, self.port):
            try:
                async with websockets.serve(self._handle_connection, self.host, ghost_port):
                    await asyncio.Future()
            except OSError:
                logger.warning("server", f"Ghost port {ghost_port} unavailable, primary only")
                await asyncio.Future()

    # ── Connection Handler ───────────────────────────────────────

    async def _handle_connection(self, ws, path=None):
        remote_ip = ws.remote_address[0] if ws.remote_address else "unknown"
        nick = None

        if remote_ip in self._ban_list:
            await ws.close(4003, "BANNED")
            return

        try:
            # HMAC challenge-response auth
            challenge = uuid.uuid4().hex
            await ws.send(json.dumps({"type": "auth_req", "challenge": challenge}))
            msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(msg)

            if data.get("type") != "auth_proof":
                await ws.close(4001, "INVALID_HANDSHAKE")
                return

            proof = data.get("proof", "")
            secret = config.get("irc", "hub_secret", default="shadow_secret")
            expected = hmac.new(
                secret.encode(), challenge.encode(), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(proof, expected):
                await ws.close(4002, "AUTH_FAILED")
                return

            nick = data.get("nick", f"anon_{uuid.uuid4().hex[:6]}")

            # Nick collision
            if nick in self.clients:
                nick = f"{nick}_{uuid.uuid4().hex[:4]}"

            chan = data.get("channel", "#general")
            if chan not in self.channels:
                chan = "#general"

            # E2E public key for DMs
            if data.get("pubkey"):
                self._user_pubkeys[nick] = base64.b64decode(data["pubkey"])

            # Register
            self.clients[nick] = ws
            is_admin = nick in config.get("identity", "admin_list", default=[])
            xp = self._xp_db.get(nick, 0)
            self.user_data[nick] = {
                "nick": nick,
                "power": "admin" if is_admin else "user",
                "channel": chan,
                "status": "online",
                "away": "",
                "realname": data.get("realname", nick),
                "joined": time.time(),
                "e2e": nick in self._user_pubkeys,
                "xp": xp,
                "level": (xp // 100) + 1,
                "idle_since": time.time(),
                "signon": time.time(),
            }

            # Auto-op admins
            channel = self.channels[chan]
            channel.users.add(nick)
            if is_admin:
                channel.ops.add(nick)

            # Send MOTD
            await self._send_to(nick, {"type": "motd", "lines": MOTD})

            # Send topic
            if channel.topic:
                await self._send_to(nick, {
                    "type": "topic",
                    "channel": chan,
                    "topic": channel.topic,
                    "setter": channel.topic_setter,
                    "time": channel.topic_time,
                })

            # Send user list for this channel (with op/voice prefixes)
            await self._send_names(nick, chan)

            # Announce join
            await self._broadcast_channel(chan, {
                "type": "join",
                "nick": nick,
                "channel": chan,
            })
            await self._sync_users()

            # Message loop
            async for message in ws:
                now = time.time()
                if now - self._rate_limits.get(remote_ip, 0) < 0.3:
                    continue
                self._rate_limits[remote_ip] = now

                # Update idle time
                if nick in self.user_data:
                    self.user_data[nick]["idle_since"] = now

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                await self._route_message(nick, data)

        except websockets.exceptions.ConnectionClosed:
            pass
        except asyncio.TimeoutError:
            logger.warning("server", f"Auth timeout from {remote_ip}")
        except Exception as e:
            logger.error("server", f"Connection error: {e}")
        finally:
            if nick:
                await self._cleanup(nick)

    # ── Message Router ───────────────────────────────────────────

    async def _route_message(self, nick: str, data: dict):
        msg_type = data.get("type")

        if msg_type == "chat":
            await self._handle_chat(nick, data)
        elif msg_type == "dm":
            await self._handle_dm(nick, data)
        elif msg_type == "action":
            await self._handle_action(nick, data)
        elif msg_type == "nick":
            await self._handle_nick(nick, data)
        elif msg_type == "topic":
            await self._handle_topic(nick, data)
        elif msg_type == "join":
            await self._handle_join(nick, data)
        elif msg_type == "part":
            await self._handle_part(nick, data)
        elif msg_type == "whois":
            await self._handle_whois(nick, data)
        elif msg_type == "list":
            await self._handle_list(nick)
        elif msg_type == "motd":
            await self._send_to(nick, {"type": "motd", "lines": MOTD})
        elif msg_type == "names":
            chan = data.get("channel", self.user_data.get(nick, {}).get("channel", "#general"))
            await self._send_names(nick, chan)
        elif msg_type == "mode":
            await self._handle_mode(nick, data)
        elif msg_type == "kick":
            await self._handle_kick(nick, data)
        elif msg_type == "ban":
            await self._handle_ban(nick, data)
        elif msg_type == "invite":
            await self._handle_invite(nick, data)
        elif msg_type == "away":
            await self._handle_away(nick, data)
        elif msg_type == "register":
            await self._handle_register(nick, data)
        elif msg_type == "identify":
            await self._handle_identify(nick, data)
        elif msg_type == "create_channel":
            await self._handle_create_channel(nick, data)

    # ── Chat ─────────────────────────────────────────────────────

    async def _handle_chat(self, nick: str, data: dict):
        text = data.get("text", "").strip()
        if not text:
            return

        chan_name = self.user_data.get(nick, {}).get("channel", "#general")
        channel = self.channels.get(chan_name)
        if not channel:
            return

        # Check moderated
        if not channel.can_talk(nick):
            await self._send_to(nick, {
                "type": "error", "text": f"Cannot send to {chan_name} (+m moderated, need voice or op)"
            })
            return

        # XP
        self._xp_db[nick] = self._xp_db.get(nick, 0) + 5
        if nick in self.user_data:
            self.user_data[nick]["xp"] = self._xp_db[nick]
            self.user_data[nick]["level"] = (self._xp_db[nick] // 100) + 1

        packet = {
            "type": "chat",
            "nick": nick,
            "channel": chan_name,
            "text": text,
            "power": self.user_data.get(nick, {}).get("power", "user"),
            "level": self.user_data.get(nick, {}).get("level", 1),
            "op": nick in channel.ops,
            "voice": nick in channel.voiced,
            "time": time.time(),
        }

        logger.info("chat", f"[{chan_name}] <{nick}> {text}")
        await self._broadcast_channel(chan_name, packet)
        bus.publish("sovereign_in", {**packet, "source": "external"})

    # ── DM — NEVER LOGGED ────────────────────────────────────────

    async def _handle_dm(self, nick: str, data: dict):
        """Private message — encrypted relay. NEVER logged. NEVER stored."""
        target_nick = data.get("target")
        if not target_nick or target_nick not in self.clients:
            await self._send_to(nick, {
                "type": "error", "text": f"User '{target_nick}' not online."
            })
            return

        # Check if target is away
        away_msg = self.user_data.get(target_nick, {}).get("away", "")
        if away_msg:
            await self._send_to(nick, {
                "type": "away_notify", "nick": target_nick, "message": away_msg,
            })

        dm_packet = {
            "type": "dm",
            "from": nick,
            "to": target_nick,
            "encrypted": data.get("encrypted", False),
            "payload": data.get("payload", ""),
            "nonce": data.get("nonce", ""),
            "time": time.time(),
        }

        # NO LOGGING. NO STORAGE.
        await self._send_to(target_nick, dm_packet)
        await self._send_to(nick, {"type": "dm_ack", "to": target_nick, "time": dm_packet["time"]})

    # ── /me Action ───────────────────────────────────────────────

    async def _handle_action(self, nick: str, data: dict):
        """CTCP ACTION — /me slaps someone with a trout"""
        text = data.get("text", "").strip()
        if not text:
            return
        chan = self.user_data.get(nick, {}).get("channel", "#general")
        await self._broadcast_channel(chan, {
            "type": "action",
            "nick": nick,
            "channel": chan,
            "text": text,
            "time": time.time(),
        })

    # ── /nick ────────────────────────────────────────────────────

    async def _handle_nick(self, nick: str, data: dict):
        new_nick = data.get("nick", "").strip()
        if not new_nick or len(new_nick) > 30:
            await self._send_to(nick, {"type": "error", "text": "Invalid nick"})
            return
        if new_nick in self.clients:
            await self._send_to(nick, {"type": "error", "text": f"Nick '{new_nick}' already in use"})
            return

        # Check if new nick is registered and user hasn't identified
        if new_nick in self._registered_nicks and new_nick not in self._identified:
            await self._send_to(nick, {"type": "error", "text": f"Nick '{new_nick}' is registered. Use /identify first."})
            return

        # Update all references
        ws = self.clients.pop(nick)
        self.clients[new_nick] = ws
        ud = self.user_data.pop(nick)
        ud["nick"] = new_nick
        self.user_data[new_nick] = ud

        if nick in self._user_pubkeys:
            self._user_pubkeys[new_nick] = self._user_pubkeys.pop(nick)
        if nick in self._xp_db:
            self._xp_db[new_nick] = self._xp_db.pop(nick)
        if nick in self._identified:
            self._identified.discard(nick)
            self._identified.add(new_nick)

        # Update channel membership
        for ch in self.channels.values():
            if nick in ch.users:
                ch.users.discard(nick)
                ch.users.add(new_nick)
            if nick in ch.ops:
                ch.ops.discard(nick)
                ch.ops.add(new_nick)
            if nick in ch.voiced:
                ch.voiced.discard(nick)
                ch.voiced.add(new_nick)

        # Broadcast nick change to everyone
        await self._broadcast_all({
            "type": "nick_change",
            "old": nick,
            "new": new_nick,
            "time": time.time(),
        })
        await self._sync_users()

    # ── /topic ───────────────────────────────────────────────────

    async def _handle_topic(self, nick: str, data: dict):
        chan_name = data.get("channel", self.user_data.get(nick, {}).get("channel"))
        channel = self.channels.get(chan_name)
        if not channel:
            return

        new_topic = data.get("topic")
        if new_topic is None:
            # Query topic
            await self._send_to(nick, {
                "type": "topic",
                "channel": chan_name,
                "topic": channel.topic,
                "setter": channel.topic_setter,
                "time": channel.topic_time,
            })
            return

        # Set topic — check +t (only ops can set)
        if "t" in channel.modes and nick not in channel.ops and not self._is_admin(nick):
            await self._send_to(nick, {"type": "error", "text": f"Cannot set topic on {chan_name} (+t, need op)"})
            return

        channel.topic = new_topic
        channel.topic_setter = nick
        channel.topic_time = time.time()

        await self._broadcast_channel(chan_name, {
            "type": "topic",
            "channel": chan_name,
            "topic": new_topic,
            "setter": nick,
            "time": channel.topic_time,
        })

    # ── /join ────────────────────────────────────────────────────

    async def _handle_join(self, nick: str, data: dict):
        chan_name = data.get("channel", "")
        if not chan_name.startswith("#"):
            chan_name = f"#{chan_name}"
        key = data.get("key", "")

        # Create channel if it doesn't exist
        if chan_name not in self.channels:
            self.channels[chan_name] = Channel(chan_name)
            # Creator gets ops
            self.channels[chan_name].ops.add(nick)

        channel = self.channels[chan_name]
        allowed, reason = channel.can_join(nick, key)
        if not allowed:
            await self._send_to(nick, {"type": "error", "text": reason})
            return

        # Leave old channel
        old_chan = self.user_data.get(nick, {}).get("channel")
        if old_chan and old_chan != chan_name:
            old_channel = self.channels.get(old_chan)
            if old_channel:
                old_channel.users.discard(nick)
                old_channel.ops.discard(nick)
                old_channel.voiced.discard(nick)
                await self._broadcast_channel(old_chan, {
                    "type": "part", "nick": nick, "channel": old_chan, "reason": f"Joined {chan_name}",
                })

        # Join new channel
        channel.users.add(nick)
        if self._is_admin(nick):
            channel.ops.add(nick)
        self.user_data[nick]["channel"] = chan_name

        # Remove from invites (used it)
        channel.invites.discard(nick)

        # Send topic
        if channel.topic:
            await self._send_to(nick, {
                "type": "topic", "channel": chan_name, "topic": channel.topic,
                "setter": channel.topic_setter, "time": channel.topic_time,
            })

        await self._send_names(nick, chan_name)
        await self._broadcast_channel(chan_name, {
            "type": "join", "nick": nick, "channel": chan_name,
        })
        await self._sync_users()

    # ── /part ────────────────────────────────────────────────────

    async def _handle_part(self, nick: str, data: dict):
        chan_name = data.get("channel", self.user_data.get(nick, {}).get("channel"))
        reason = data.get("reason", "Leaving")
        channel = self.channels.get(chan_name)
        if not channel:
            return

        channel.users.discard(nick)
        channel.ops.discard(nick)
        channel.voiced.discard(nick)

        await self._broadcast_channel(chan_name, {
            "type": "part", "nick": nick, "channel": chan_name, "reason": reason,
        })

        # Move to #general
        self.user_data[nick]["channel"] = "#general"
        self.channels["#general"].users.add(nick)
        await self._sync_users()

    # ── /whois ───────────────────────────────────────────────────

    async def _handle_whois(self, nick: str, data: dict):
        target = data.get("target", nick)
        ud = self.user_data.get(target)
        if not ud:
            await self._send_to(nick, {"type": "error", "text": f"No such nick: {target}"})
            return

        idle_secs = int(time.time() - ud.get("idle_since", time.time()))
        signon = ud.get("signon", time.time())

        # Find which channels they're in
        in_channels = []
        for ch_name, ch in self.channels.items():
            if target in ch.users:
                prefix = "@" if target in ch.ops else "+" if target in ch.voiced else ""
                in_channels.append(f"{prefix}{ch_name}")

        await self._send_to(nick, {
            "type": "whois",
            "nick": target,
            "realname": ud.get("realname", target),
            "channels": in_channels,
            "idle": idle_secs,
            "signon": signon,
            "power": ud.get("power", "user"),
            "level": ud.get("level", 1),
            "xp": ud.get("xp", 0),
            "e2e": ud.get("e2e", False),
            "away": ud.get("away", ""),
            "registered": target in self._registered_nicks,
            "identified": target in self._identified,
            "server": "ShadowCypher Sovereign",
        })

    # ── /list ────────────────────────────────────────────────────

    async def _handle_list(self, nick: str):
        chan_list = []
        for name, ch in self.channels.items():
            if "s" in ch.modes and nick not in ch.users:
                continue  # Secret channel, user not in it
            chan_list.append({
                "name": name,
                "users": len(ch.users),
                "topic": ch.topic,
                "modes": "+" + "".join(sorted(ch.modes)) if ch.modes else "",
            })
        await self._send_to(nick, {"type": "list", "channels": chan_list})

    # ── /mode ────────────────────────────────────────────────────

    async def _handle_mode(self, nick: str, data: dict):
        chan_name = data.get("channel", self.user_data.get(nick, {}).get("channel"))
        channel = self.channels.get(chan_name)
        if not channel:
            return

        mode_str = data.get("mode", "")
        target = data.get("target", "")

        # Query mode
        if not mode_str:
            modes = "+" + "".join(sorted(channel.modes)) if channel.modes else "+"
            await self._send_to(nick, {
                "type": "mode_info", "channel": chan_name, "modes": modes,
            })
            return

        # Only ops or admins can set modes
        if nick not in channel.ops and not self._is_admin(nick):
            await self._send_to(nick, {"type": "error", "text": "You're not a channel operator"})
            return

        adding = True
        changes = []
        for char in mode_str:
            if char == "+":
                adding = True
            elif char == "-":
                adding = False
            elif char in "ikmst":
                if adding:
                    channel.modes.add(char)
                    if char == "k":
                        channel.key = data.get("key", "")
                else:
                    channel.modes.discard(char)
                    if char == "k":
                        channel.key = ""
                changes.append(f"{'+' if adding else '-'}{char}")
            elif char == "o" and target:
                if adding:
                    channel.ops.add(target)
                else:
                    channel.ops.discard(target)
                changes.append(f"{'+' if adding else '-'}o {target}")
            elif char == "v" and target:
                if adding:
                    channel.voiced.add(target)
                else:
                    channel.voiced.discard(target)
                changes.append(f"{'+' if adding else '-'}v {target}")
            elif char == "b" and target:
                if adding:
                    channel.bans.add(target)
                else:
                    channel.bans.discard(target)
                changes.append(f"{'+' if adding else '-'}b {target}")

        if changes:
            await self._broadcast_channel(chan_name, {
                "type": "mode",
                "nick": nick,
                "channel": chan_name,
                "changes": " ".join(changes),
                "time": time.time(),
            })

    # ── /kick ────────────────────────────────────────────────────

    async def _handle_kick(self, nick: str, data: dict):
        chan_name = data.get("channel", self.user_data.get(nick, {}).get("channel"))
        channel = self.channels.get(chan_name)
        target = data.get("target")
        reason = data.get("reason", "Kicked")

        if not channel or not target:
            return
        if nick not in channel.ops and not self._is_admin(nick):
            await self._send_to(nick, {"type": "error", "text": "You're not a channel operator"})
            return
        if target not in channel.users:
            return

        channel.users.discard(target)
        channel.ops.discard(target)
        channel.voiced.discard(target)

        await self._broadcast_channel(chan_name, {
            "type": "kick", "nick": nick, "target": target,
            "channel": chan_name, "reason": reason, "time": time.time(),
        })

        # Move kicked user to #general
        if target in self.user_data:
            self.user_data[target]["channel"] = "#general"
            self.channels["#general"].users.add(target)
        await self._sync_users()

    # ── /ban ─────────────────────────────────────────────────────

    async def _handle_ban(self, nick: str, data: dict):
        chan_name = data.get("channel", self.user_data.get(nick, {}).get("channel"))
        channel = self.channels.get(chan_name)
        target = data.get("target")

        if not channel or not target:
            return
        if nick not in channel.ops and not self._is_admin(nick):
            await self._send_to(nick, {"type": "error", "text": "You're not a channel operator"})
            return

        channel.bans.add(target)

        # Also kick if in channel
        if target in channel.users:
            channel.users.discard(target)
            channel.ops.discard(target)
            channel.voiced.discard(target)

        await self._broadcast_channel(chan_name, {
            "type": "ban", "nick": nick, "target": target,
            "channel": chan_name, "time": time.time(),
        })

        # Server-wide IP ban (admin only)
        if self._is_admin(nick) and data.get("server_ban") and target in self.clients:
            ws = self.clients[target]
            if ws.remote_address:
                self._ban_list.add(ws.remote_address[0])
            await ws.close(4003, "BANNED")

    # ── /invite ──────────────────────────────────────────────────

    async def _handle_invite(self, nick: str, data: dict):
        chan_name = data.get("channel", self.user_data.get(nick, {}).get("channel"))
        channel = self.channels.get(chan_name)
        target = data.get("target")

        if not channel or not target:
            return
        if nick not in channel.ops and not self._is_admin(nick):
            await self._send_to(nick, {"type": "error", "text": "You're not a channel operator"})
            return

        channel.invites.add(target)

        # Notify target
        await self._send_to(target, {
            "type": "invite", "from": nick, "channel": chan_name,
        })
        await self._send_to(nick, {
            "type": "sys", "text": f"Invited {target} to {chan_name}",
        })

    # ── /away ────────────────────────────────────────────────────

    async def _handle_away(self, nick: str, data: dict):
        message = data.get("message", "")
        if nick in self.user_data:
            self.user_data[nick]["away"] = message
            self.user_data[nick]["status"] = "away" if message else "online"
        status = "AWAY" if message else "BACK"
        await self._send_to(nick, {
            "type": "sys", "text": f"You are now {status}" + (f": {message}" if message else ""),
        })
        await self._sync_users()

    # ── NickServ: /register ──────────────────────────────────────

    async def _handle_register(self, nick: str, data: dict):
        password = data.get("password", "")
        if not password or len(password) < 6:
            await self._send_to(nick, {"type": "error", "text": "Password must be at least 6 characters"})
            return
        if nick in self._registered_nicks:
            await self._send_to(nick, {"type": "error", "text": f"Nick '{nick}' is already registered"})
            return

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        self._registered_nicks[nick] = pw_hash
        self._identified.add(nick)
        await self._send_to(nick, {"type": "sys", "text": f"Nick '{nick}' is now registered and identified."})

    # ── NickServ: /identify ──────────────────────────────────────

    async def _handle_identify(self, nick: str, data: dict):
        password = data.get("password", "")
        stored = self._registered_nicks.get(nick)
        if not stored:
            await self._send_to(nick, {"type": "error", "text": f"Nick '{nick}' is not registered"})
            return

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if hmac.compare_digest(pw_hash, stored):
            self._identified.add(nick)
            await self._send_to(nick, {"type": "sys", "text": "You are now identified."})
        else:
            await self._send_to(nick, {"type": "error", "text": "Wrong password."})

    # ── Create channel ───────────────────────────────────────────

    async def _handle_create_channel(self, nick: str, data: dict):
        name = data.get("name", "")
        if not name.startswith("#"):
            name = f"#{name}"
        if name in self.channels:
            await self._send_to(nick, {"type": "error", "text": f"Channel {name} already exists"})
            return

        topic = data.get("topic", "")
        modes = data.get("modes", DEFAULT_CHAN_MODES)
        key = data.get("key", "")

        self.channels[name] = Channel(name, topic=topic, modes=modes, key=key)
        self.channels[name].ops.add(nick)
        self.channels[name].topic_setter = nick
        self.channels[name].topic_time = time.time()

        await self._send_to(nick, {"type": "sys", "text": f"Channel {name} created. You are operator."})

    # ── Helpers ───────────────────────────────────────────────────

    def _is_admin(self, nick: str) -> bool:
        return self.user_data.get(nick, {}).get("power") == "admin"

    async def _send_to(self, nick: str, packet: dict):
        ws = self.clients.get(nick)
        if ws:
            try:
                await ws.send(json.dumps(packet))
            except Exception:
                pass

    async def _send_names(self, nick: str, chan_name: str):
        """Send NAMES list with @op and +voice prefixes."""
        channel = self.channels.get(chan_name)
        if not channel:
            return
        names = []
        for user in sorted(channel.users):
            if user in channel.ops:
                names.append(f"@{user}")
            elif user in channel.voiced:
                names.append(f"+{user}")
            else:
                names.append(user)
        await self._send_to(nick, {
            "type": "names", "channel": chan_name, "names": names,
        })

    async def _broadcast_channel(self, channel: str, packet: dict):
        ch = self.channels.get(channel)
        if not ch:
            return
        msg = json.dumps(packet)
        tasks = []
        for n in list(ch.users):
            ws = self.clients.get(n)
            if ws:
                tasks.append(ws.send(msg))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _sync_users(self):
        safe_users = []
        for ud in self.user_data.values():
            chan_name = ud.get("channel", "#general")
            ch = self.channels.get(chan_name)
            safe_users.append({
                "nick": ud["nick"],
                "power": ud["power"],
                "channel": chan_name,
                "status": ud["status"],
                "away": ud.get("away", ""),
                "e2e": ud.get("e2e", False),
                "xp": ud.get("xp", 0),
                "level": ud.get("level", 1),
                "op": ud["nick"] in ch.ops if ch else False,
                "voice": ud["nick"] in ch.voiced if ch else False,
                "registered": ud["nick"] in self._registered_nicks,
                "identified": ud["nick"] in self._identified,
            })
        await self._broadcast_all({"type": "user_sync", "users": safe_users})

    async def _broadcast_all(self, packet: dict):
        msg = json.dumps(packet)
        if self.clients:
            await asyncio.gather(
                *[ws.send(msg) for ws in self.clients.values()],
                return_exceptions=True,
            )

    async def _cleanup(self, nick: str):
        chan = self.user_data.get(nick, {}).get("channel", "#general")
        self.clients.pop(nick, None)
        self.user_data.pop(nick, None)
        self._user_pubkeys.pop(nick, None)
        self._identified.discard(nick)

        for ch in self.channels.values():
            ch.users.discard(nick)
            ch.ops.discard(nick)
            ch.voiced.discard(nick)

        await self._broadcast_channel(chan, {
            "type": "quit", "nick": nick, "reason": "Connection closed",
        })
        await self._sync_users()


if __name__ == "__main__":
    srv = SovereignServer()
    asyncio.run(srv.start())

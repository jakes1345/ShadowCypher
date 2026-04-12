"""
ShadowCypher IRC Engine v2 — Production-Grade Raw Socket IRC Client.
Features: SSL, SASL PLAIN, auto-reconnect, rate limiting, NICK/TOPIC/KICK/MODE tracking.
No external IRC dependencies. Fully self-contained.
"""

import socket
import ssl
import threading
import time
import re
import hashlib
import base64
from typing import Callable, Optional, Dict
from shadowcypher.core.logger import logger


# Strip mIRC color/formatting codes from messages
_IRC_STRIP_RE = re.compile(
    r'\x03(\d{1,2}(,\d{1,2})?)?|\x02|\x1f|\x16|\x0f|\x1d|\x1e|\x11'
)


def strip_irc_formatting(text: str) -> str:
    """Remove mIRC color codes, bold, underline, italic, reverse, etc."""
    return _IRC_STRIP_RE.sub('', text)


class IRCClient:
    """Production-grade IRC client with SSL, SASL, reconnect, and flood protection."""

    def __init__(self, server: str = "irc.libera.chat", port: int = 6697,
                 channel: str = "#shadowcypher-support",
                 nick: str = "sc_operator", use_ssl: bool = True,
                 sasl_user: str = None, sasl_pass: str = None,
                 auto_reconnect: bool = True, max_reconnect_delay: int = 300):
        self.server = server
        self.port = port
        self.channel = channel
        self.nick = nick
        self.use_ssl = use_ssl

        # SASL Authentication
        self.sasl_user = sasl_user or ""
        self.sasl_pass = sasl_pass or ""

        # Auto-Reconnect
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_delay = max_reconnect_delay
        self._reconnect_delay = 5

        # Rate Limiter (Anti-Flood)
        self._send_lock = threading.Lock()
        self._last_send_time = 0.0
        self._send_interval = 0.5
        self._burst_count = 0
        self._burst_reset_time = 0.0
        self._max_burst = 5

        # Connection state
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._buffer = ""

        # Channel state
        self.channel_topic = ""
        self.channel_topic_setter = ""
        self._user_modes: Dict[str, str] = {}

        # WHOIS state
        self._whois_cache: dict = {}
        self._whois_building: Optional[str] = None

        # Callbacks
        self._on_message: Optional[Callable] = None
        self._on_system: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_userlist: Optional[Callable] = None
        self._on_whois: Optional[Callable] = None
        self._on_private: Optional[Callable] = None
        self._on_join: Optional[Callable] = None
        self._on_part: Optional[Callable] = None
        self._on_ctcp: Optional[Callable] = None
        self._on_topic: Optional[Callable] = None
        self._on_nick_change: Optional[Callable] = None
        self._on_kick: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None

    # ─── Callback Registration ───────────────────────────────────
    def on_message(self, cb):
        """(nick, channel, message, full_source)"""
        self._on_message = cb

    def on_system(self, cb):
        """(system_message_str)"""
        self._on_system = cb

    def on_connect(self, cb):
        """()"""
        self._on_connect = cb

    def on_userlist(self, cb):
        """(list_of_nicks)"""
        self._on_userlist = cb

    def on_whois(self, cb):
        """(whois_info_dict)"""
        self._on_whois = cb

    def on_private(self, cb):
        """(nick, message, full_source)"""
        self._on_private = cb

    def on_join(self, cb):
        """(nick)"""
        self._on_join = cb

    def on_part(self, cb):
        """(nick)"""
        self._on_part = cb

    def on_ctcp(self, cb):
        """(nick, content, full_source)"""
        self._on_ctcp = cb

    def on_topic(self, cb):
        """(topic_text, setter_nick_or_None)"""
        self._on_topic = cb

    def on_nick_change(self, cb):
        """(old_nick, new_nick)"""
        self._on_nick_change = cb

    def on_kick(self, cb):
        """(kicker_nick, kicked_nick, reason)"""
        self._on_kick = cb

    def on_disconnect(self, cb):
        """()"""
        self._on_disconnect = cb

    def on_typing(self, cb):
        """(nick, status) — status in ['active', 'paused', 'done']"""
        self._on_typing = cb

    # ─── Public API ──────────────────────────────────────────────
    def connect(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._connection_loop, daemon=True, name="IRC-Engine"
        )
        self._thread.start()

    def disconnect(self, reason="Signing off"):
        self.auto_reconnect = False
        self._running = False
        if self._sock:
            try:
                self._send_raw(f"QUIT :{reason}")
                time.sleep(0.3)
                self._sock.close()
            except Exception:
                pass
        self._connected = False
        self._emit_sys("Disconnected from IRC.")
        if self._on_disconnect:
            self._on_disconnect()

    def send_message(self, msg: str, target: str = None):
        target = target or self.channel
        self._send_throttled(f"PRIVMSG {target} :{msg}")
        # When sending a real message, always clear typing status
        self.send_typing(target, "done")

    def send_private(self, nick: str, msg: str):
        self._send_throttled(f"PRIVMSG {nick} :{msg}")
        self.send_typing(nick, "done")

    def send_typing(self, target: str, status: str = "active"):
        """Broadcast typing status (IRCv3 + CTCP Fallback)."""
        if not self._connected: return
        # 1. TAGMSG (Modern IRCv3)
        self._send_raw(f"@typing={status} TAGMSG {target}")
        # 2. CTCP Fallback (For legacy clients)
        if status in ["active", "done"]:
            code = "1" if status == "active" else "0"
            self._send_raw(f"PRIVMSG {target} :\x01TYPING {code}\x01")

    def send_action(self, msg: str, target: str = None):
        target = target or self.channel
        self._send_throttled(f"PRIVMSG {target} :\x01ACTION {msg}\x01")

    def send_whois(self, nick: str):
        self._whois_building = nick
        self._whois_cache[nick] = {"nick": nick}
        self._send_raw(f"WHOIS {nick}")

    def request_names(self):
        self._send_raw(f"NAMES {self.channel}")

    def change_nick(self, new_nick: str):
        self._send_raw(f"NICK {new_nick}")

    def set_topic(self, topic: str, channel: str = None):
        channel = channel or self.channel
        self._send_throttled(f"TOPIC {channel} :{topic}")

    def kick_user(self, nick: str, reason: str = "Removed", channel: str = None):
        channel = channel or self.channel
        self._send_raw(f"KICK {channel} {nick} :{reason}")

    def set_mode(self, mode: str, target: str = None, channel: str = None):
        channel = channel or self.channel
        cmd = f"MODE {channel} {mode} {target}" if target else f"MODE {channel} {mode}"
        self._send_raw(cmd)

    def get_user_prefix(self, nick: str) -> str:
        """Get the mode prefix for a user (@, +, %, ~, &)."""
        return self._user_modes.get(nick, "")

    @property
    def connected(self) -> bool:
        return self._connected

    # ─── Connection Loop with Auto-Reconnect ─────────────────────
    def _connection_loop(self):
        """Main connection loop with exponential backoff reconnection."""
        while self._running:
            try:
                self._emit_sys(f"Connecting to {self.server}:{self.port}...")
                raw = socket.create_connection(
                    (self.server, self.port), timeout=15
                )

                if self.use_ssl:
                    ctx = ssl.create_default_context()
                    self._sock = ctx.wrap_socket(
                        raw, server_hostname=self.server
                    )
                else:
                    self._sock = raw

                self._sock.settimeout(300)

                # SASL negotiation + v3 Caps
                req_caps = ["typing", "message-tags", "multi-prefix", "away-notify"]
                if self.sasl_user and self.sasl_pass:
                    req_caps.append("sasl")
                
                self._send_raw(f"CAP REQ :{' '.join(req_caps)}")

                self._send_raw(f"NICK {self.nick}")
                self._send_raw(f"USER {self.nick} 0 * :ShadowCypher Operator")

                # Reset backoff on successful TCP connect
                self._reconnect_delay = 5
                self._read_loop()

            except Exception as e:
                self._emit_sys(f"Connection failed: {e}")
                logger.error("irc", f"IRC connect failed: {e}")
            finally:
                self._connected = False
                if self._sock:
                    try:
                        self._sock.close()
                    except Exception:
                        pass
                    self._sock = None

            # Auto-reconnect logic
            if self._running and self.auto_reconnect:
                self._emit_sys(
                    f"Reconnecting in {self._reconnect_delay}s..."
                )
                if self._on_disconnect:
                    self._on_disconnect()
                time.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.max_reconnect_delay
                )
            else:
                break

        self._running = False

    def _read_loop(self):
        while self._running:
            try:
                data = self._sock.recv(4096)
                if not data:
                    self._emit_sys("Server closed connection.")
                    break

                self._buffer += data.decode("utf-8", errors="replace")
                while "\r\n" in self._buffer:
                    line, self._buffer = self._buffer.split("\r\n", 1)
                    self._handle_line(line)

            except socket.timeout:
                self._send_raw(f"PING :keepalive_{int(time.time())}")
            except Exception as e:
                if self._running:
                    self._emit_sys(f"Read error: {e}")
                break

    # ─── Full Protocol Handler ───────────────────────────────────
    def _handle_line(self, line: str):
        # --- IRCv3 Tag Parsing ---
        tags = {}
        if line.startswith("@"):
            tag_part, line = line[1:].split(" ", 1)
            for t in tag_part.split(";"):
                if "=" in t:
                    k, v = t.split("=", 1)
                    tags[k] = v
                else:
                    tags[t] = True

        if line.startswith("PING"):
            self._send_raw(line.replace("PING", "PONG", 1))
            return

        parts = line.split(" ", 3)
        if len(parts) < 2:
            return

        command = parts[1] if parts[0].startswith(":") else parts[0]

        # ── Welcome (001) ────────────────────────────────────────
        if command == "001":
            self._connected = True
            self._emit_sys(
                f"Connected as {self.nick}. Joining {self.channel}..."
            )
            self._send_raw(f"JOIN {self.channel}")
            if self._on_connect:
                self._on_connect()

        # ── IRCv3 CAPs ───────────────────────────────────────────
        elif command == "CAP":
            sub = parts[2]
            if sub == "ACK":
                self._emit_sys(f"Capabilities enabled: {line}")
            self._send_raw("CAP END")

        # ── SASL Handshake ───────────────────────────────────────
        elif command == "AUTHENTICATE" and "+" in line:
            if self.sasl_user and self.sasl_pass:
                auth = f"{self.sasl_user}\x00{self.sasl_user}\x00{self.sasl_pass}"
                encoded = base64.b64encode(auth.encode()).decode()
                self._send_raw(f"AUTHENTICATE {encoded}")

        elif command == "903":
            self._emit_sys("SASL authentication successful.")

        elif command in ("904", "905"):
            self._emit_sys("SASL auth failed. Continuing without auth.")

        # ── IRCv3 TAGMSG (Typing) ────────────────────────────────
        elif command == "TAGMSG":
            nick = self._extract_nick(parts[0])
            if "typing" in tags and hasattr(self, "_on_typing") and self._on_typing:
                self._on_typing(nick, tags["typing"])

        # ── NAMES (353/366) ──────────────────────────────────────
        elif command == "353" and len(parts) > 3:
            names_str = parts[3].split(":", 1)[-1]
            raw_names = names_str.split()
            clean_names = []
            for n in raw_names:
                prefix = ""
                while n and n[0] in "@+%~&":
                    prefix += n[0]
                    n = n[1:]
                if n:
                    clean_names.append(n)
                    self._user_modes[n] = prefix
            if self._on_userlist:
                self._on_userlist(clean_names)

        elif command == "366":
            pass

        # ── TOPIC (332/333/TOPIC) ────────────────────────────────
        elif command == "332":
            raw = line.split(" ", 4)
            if len(raw) >= 5:
                self.channel_topic = raw[4].lstrip(":")
                if self._on_topic:
                    self._on_topic(self.channel_topic, None)
                self._emit_sys(f"Topic: {self.channel_topic}")

        elif command == "333":
            raw = line.split(" ", 5)
            if len(raw) >= 5:
                self.channel_topic_setter = raw[4]

        elif command == "TOPIC":
            nick = self._extract_nick(parts[0])
            topic = parts[3][1:] if len(parts) > 3 else ""
            self.channel_topic = topic
            self.channel_topic_setter = nick
            if self._on_topic:
                self._on_topic(topic, nick)
            self._emit_sys(f"{nick} changed topic to: {topic}")

        # ── WHOIS (311/312/317/319/318) ──────────────────────────
        elif command == "311":
            raw = line.split(" ", 6)
            if len(raw) >= 6 and self._whois_building:
                info = self._whois_cache.get(self._whois_building, {})
                info["user"] = raw[4]
                info["host"] = raw[5]
                if len(raw) > 6:
                    info["realname"] = raw[6].lstrip(":")
                self._whois_cache[self._whois_building] = info

        elif command == "312":
            raw = line.split(" ", 5)
            if len(raw) >= 5 and self._whois_building:
                info = self._whois_cache.get(self._whois_building, {})
                info["server"] = raw[4]
                if len(raw) > 5:
                    info["server_info"] = raw[5].lstrip(":")

        elif command == "319":
            raw = line.split(":", 2)
            if len(raw) >= 3 and self._whois_building:
                info = self._whois_cache.get(self._whois_building, {})
                info["channels"] = raw[2].strip()

        elif command == "317":
            raw = line.split(" ", 6)
            if len(raw) >= 6 and self._whois_building:
                info = self._whois_cache.get(self._whois_building, {})
                try:
                    info["idle_seconds"] = int(raw[4])
                    info["signon_time"] = int(raw[5])
                except (ValueError, IndexError):
                    pass

        elif command == "318":
            if self._whois_building and self._on_whois:
                info = self._whois_cache.get(self._whois_building, {})
                self._on_whois(info)
            self._whois_building = None

        # ── AWAY (301/305/306) ───────────────────────────────────
        elif command == "301":
            raw = line.split(" ", 4)
            if len(raw) >= 5:
                self._emit_sys(
                    f"[AWAY] {raw[3]}: {raw[4].lstrip(':')}"
                )

        elif command == "305":
            self._emit_sys("You are no longer marked as away.")

        elif command == "306":
            self._emit_sys("You are now marked as away.")

        # ── Nick in use (433) ────────────────────────────────────
        elif command == "433":
            self.nick += "_"
            self._send_raw(f"NICK {self.nick}")
            self._emit_sys(f"Nick taken, trying: {self.nick}")

        # ── JOIN ─────────────────────────────────────────────────
        elif command == "JOIN":
            nick = self._extract_nick(parts[0])
            if nick == self.nick:
                self._emit_sys(f"Joined {self.channel}")
                self._send_raw(f"NAMES {self.channel}")
            else:
                self._emit_sys(f"{nick} joined the channel")
                if self._on_join:
                    self._on_join(nick)
                self._send_raw(f"NAMES {self.channel}")

        # ── PART ─────────────────────────────────────────────────
        elif command == "PART":
            nick = self._extract_nick(parts[0])
            self._user_modes.pop(nick, None)
            self._emit_sys(f"{nick} left the channel")
            if self._on_part:
                self._on_part(nick)
            self._send_raw(f"NAMES {self.channel}")

        # ── QUIT ─────────────────────────────────────────────────
        elif command == "QUIT":
            nick = self._extract_nick(parts[0])
            self._user_modes.pop(nick, None)
            self._emit_sys(f"{nick} disconnected")
            if self._on_part:
                self._on_part(nick)
            self._send_raw(f"NAMES {self.channel}")

        # ── NICK (nick change) ───────────────────────────────────
        elif command == "NICK":
            old_nick = self._extract_nick(parts[0])
            new_nick = parts[2].lstrip(":") if len(parts) > 2 else ""

            if old_nick in self._user_modes:
                self._user_modes[new_nick] = self._user_modes.pop(old_nick)

            if old_nick == self.nick:
                self.nick = new_nick
                self._emit_sys(f"You are now known as {new_nick}")
            else:
                self._emit_sys(f"{old_nick} is now known as {new_nick}")

            if self._on_nick_change:
                self._on_nick_change(old_nick, new_nick)
            self._send_raw(f"NAMES {self.channel}")

        # ── KICK ─────────────────────────────────────────────────
        elif command == "KICK":
            kicker = self._extract_nick(parts[0])
            raw_parts = line.split(" ", 4)
            kicked = raw_parts[3] if len(raw_parts) > 3 else ""
            reason = raw_parts[4].lstrip(":") if len(raw_parts) > 4 else ""

            self._user_modes.pop(kicked, None)
            self._emit_sys(f"{kicked} was kicked by {kicker} ({reason})")

            if self._on_kick:
                self._on_kick(kicker, kicked, reason)

            # Auto-rejoin if WE were kicked
            if kicked == self.nick:
                self._emit_sys("Auto-rejoining channel...")
                time.sleep(2)
                self._send_raw(f"JOIN {self.channel}")

        # ── MODE ─────────────────────────────────────────────────
        elif command == "MODE":
            raw_parts = line.split(" ")
            if len(raw_parts) >= 5:
                if "o" in raw_parts[3] or "v" in raw_parts[3]:
                    self._send_raw(f"NAMES {self.channel}")

        # ── PRIVMSG ──────────────────────────────────────────────
        elif command == "PRIVMSG":
            nick = self._extract_nick(parts[0])
            source = parts[0].lstrip(":")
            target = parts[2]
            msg = parts[3][1:] if len(parts) > 3 else ""

            # CTCP (before stripping — uses \x01)
            if msg.startswith("\x01") and msg.endswith("\x01"):
                ctcp = msg[1:-1]
                if ctcp.startswith("ACTION "):
                    self._emit_sys(f"* {nick} {ctcp[7:]}")
                elif ctcp.startswith("VERSION"):
                    self._send_raw(
                        f"NOTICE {nick} :\x01VERSION ShadowCypher IRC v2.0\x01"
                    )
                elif ctcp.startswith("TYPING "):
                    # Fallback typing signal
                    try:
                        code = ctcp.split(" ")[1]
                        status = "active" if code == "1" else "done"
                        if hasattr(self, "_on_typing") and self._on_typing:
                            self._on_typing(nick, status)
                    except Exception: pass
                elif ctcp.startswith("PING"):
                    self._send_raw(f"NOTICE {nick} :\x01{ctcp}\x01")
                return

            # Strip mIRC formatting from regular messages
            msg = strip_irc_formatting(msg)

            if target == self.nick:
                if self._on_private:
                    self._on_private(nick, msg, source)
            elif self._on_message:
                self._on_message(nick, target, msg, source)

        # ── NOTICE ───────────────────────────────────────────────
        elif command == "NOTICE":
            nick = self._extract_nick(parts[0])
            msg = parts[3][1:] if len(parts) > 3 else ""
            source = parts[0].lstrip(":")

            if msg.startswith("\x01") and msg.endswith("\x01"):
                ctcp_content = msg[1:-1]
                if self._on_ctcp:
                    self._on_ctcp(nick, ctcp_content, source)
                self._emit_sys(f"[CTCP_REPLY] {nick}: {ctcp_content}")
            else:
                msg = strip_irc_formatting(msg)
                self._emit_sys(f"[NOTICE] {msg}")

    # ─── Send with Rate Limiting ─────────────────────────────────
    def _send_throttled(self, raw: str):
        """Send with flood protection — burst limit + interval enforcement."""
        with self._send_lock:
            now = time.time()

            if now - self._burst_reset_time > 2.0:
                self._burst_count = 0
                self._burst_reset_time = now

            if self._burst_count >= self._max_burst:
                wait = 2.0 - (now - self._burst_reset_time)
                if wait > 0:
                    time.sleep(wait)
                self._burst_count = 0
                self._burst_reset_time = time.time()

            elapsed = now - self._last_send_time
            if elapsed < self._send_interval:
                time.sleep(self._send_interval - elapsed)

            self._send_raw(raw)
            self._last_send_time = time.time()
            self._burst_count += 1

    def _send_raw(self, raw: str):
        """Direct send without rate limiting (for protocol messages)."""
        if self._sock:
            try:
                self._sock.send(f"{raw}\r\n".encode("utf-8"))
            except Exception as e:
                logger.error("irc", f"Send failed: {e}")

    @staticmethod
    def _extract_nick(prefix: str) -> str:
        if "!" in prefix:
            return prefix[1:prefix.index("!")]
        return prefix.lstrip(":")

    def _emit_sys(self, msg: str):
        if self._on_system:
            self._on_system(msg)
        logger.info("irc", msg)


def generate_machine_token(pubkey_fingerprint: str) -> str:
    """Generate a verification token from this machine.
    Proves the user has a real ShadowCypher install with the correct
    public key, without revealing any private data."""
    import platform
    machine_id = f"{platform.node()}:{platform.machine()}:{pubkey_fingerprint}"
    return hashlib.sha256(machine_id.encode()).hexdigest()[:16]

"""
ShadowCypher IRC Engine — Raw socket IRC client for Support & Comms.
No external dependencies. Handles connect, auth, messaging, and keepalive.
"""

import socket
import ssl
import threading
import time
import re
import hashlib
from typing import Callable, Optional
from shadowcypher.core.logger import logger


class IRCClient:
    """Minimal IRC client using raw sockets + SSL."""

    def __init__(self, server: str = "irc.libera.chat", port: int = 6697,
                 channel: str = "#shadowcypher-support",
                 nick: str = "sc_operator", use_ssl: bool = True):
        self.server = server
        self.port = port
        self.channel = channel
        self.nick = nick
        self.use_ssl = use_ssl
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_message: Optional[Callable] = None
        self._on_system: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_userlist: Optional[Callable] = None
        self._on_whois: Optional[Callable] = None
        self._on_private: Optional[Callable] = None
        self._on_join: Optional[Callable] = None
        self._on_part: Optional[Callable] = None
        self._buffer = ""
        self._whois_cache: dict = {}
        self._whois_building: Optional[str] = None

    def on_message(self, cb: Callable[[str, str, str], None]):
        """Register callback: (nick, channel/target, message)"""
        self._on_message = cb

    def on_system(self, cb: Callable[[str], None]):
        """Register callback: (system_message)"""
        self._on_system = cb

    def on_connect(self, cb: Callable[[], None]):
        self._on_connect = cb

    def on_userlist(self, cb: Callable[[list], None]):
        self._on_userlist = cb

    def on_whois(self, cb: Callable[[dict], None]):
        """Register callback: (whois_info_dict)"""
        self._on_whois = cb

    def on_private(self, cb: Callable[[str, str], None]):
        """Register callback for private messages: (nick, message)"""
        self._on_private = cb

    def on_join(self, cb: Callable[[str], None]):
        self._on_join = cb

    def on_part(self, cb: Callable[[str], None]):
        self._on_part = cb

    def connect(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def disconnect(self, reason="Signing off"):
        self._running = False
        if self._sock:
            try:
                self._send(f"QUIT :{reason}")
                time.sleep(0.3)
                self._sock.close()
            except Exception:
                pass
        self._connected = False
        self._emit_sys("Disconnected from IRC.")

    def send_message(self, msg: str, target: str = None):
        target = target or self.channel
        self._send(f"PRIVMSG {target} :{msg}")

    def send_private(self, nick: str, msg: str):
        self._send(f"PRIVMSG {nick} :{msg}")

    def send_action(self, msg: str, target: str = None):
        target = target or self.channel
        self._send(f"PRIVMSG {target} :\x01ACTION {msg}\x01")

    def send_whois(self, nick: str):
        self._whois_building = nick
        self._whois_cache[nick] = {"nick": nick}
        self._send(f"WHOIS {nick}")

    def request_names(self):
        self._send(f"NAMES {self.channel}")

    @property
    def connected(self) -> bool:
        return self._connected

    def _run(self):
        try:
            self._emit_sys(f"Connecting to {self.server}:{self.port}...")
            raw = socket.create_connection((self.server, self.port), timeout=15)

            if self.use_ssl:
                ctx = ssl.create_default_context()
                self._sock = ctx.wrap_socket(raw, server_hostname=self.server)
            else:
                self._sock = raw

            self._sock.settimeout(300)

            self._send(f"NICK {self.nick}")
            self._send(f"USER {self.nick} 0 * :ShadowCypher Operator")

            self._read_loop()

        except Exception as e:
            self._emit_sys(f"Connection failed: {e}")
            logger.error("irc", f"IRC connect failed: {e}")
        finally:
            self._connected = False
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
                self._send(f"PING :keepalive_{int(time.time())}")
            except Exception as e:
                if self._running:
                    self._emit_sys(f"Read error: {e}")
                break

    def _handle_line(self, line: str):
        if line.startswith("PING"):
            self._send(line.replace("PING", "PONG", 1))
            return

        parts = line.split(" ", 3)

        if len(parts) >= 2:
            command = parts[1] if parts[0].startswith(":") else parts[0]

            # 001 = Welcome
            if command == "001":
                self._connected = True
                self._emit_sys(f"Connected as {self.nick}. Joining {self.channel}...")
                self._send(f"JOIN {self.channel}")
                if self._on_connect:
                    self._on_connect()

            # 353 = NAMES list
            elif command == "353" and len(parts) > 3:
                names_str = parts[3].split(":", 1)[-1]
                names = [n.lstrip("@+%~&") for n in names_str.split()]
                if self._on_userlist:
                    self._on_userlist(names)

            elif command == "366":
                pass

            # 311 = WHOIS user info
            elif command == "311":
                raw = line.split(" ", 6)
                if len(raw) >= 6 and self._whois_building:
                    info = self._whois_cache.get(self._whois_building, {})
                    info["user"] = raw[4]
                    info["host"] = raw[5]
                    if len(raw) > 6:
                        info["realname"] = raw[6].lstrip(":")
                    self._whois_cache[self._whois_building] = info

            # 312 = WHOIS server
            elif command == "312":
                raw = line.split(" ", 5)
                if len(raw) >= 5 and self._whois_building:
                    info = self._whois_cache.get(self._whois_building, {})
                    info["server"] = raw[4]
                    if len(raw) > 5:
                        info["server_info"] = raw[5].lstrip(":")

            # 319 = WHOIS channels
            elif command == "319":
                raw = line.split(":", 2)
                if len(raw) >= 3 and self._whois_building:
                    info = self._whois_cache.get(self._whois_building, {})
                    info["channels"] = raw[2].strip()

            # 317 = WHOIS idle/signon
            elif command == "317":
                raw = line.split(" ", 6)
                if len(raw) >= 6 and self._whois_building:
                    info = self._whois_cache.get(self._whois_building, {})
                    try:
                        info["idle_seconds"] = int(raw[4])
                        info["signon_time"] = int(raw[5])
                    except (ValueError, IndexError):
                        pass

            # 318 = End of WHOIS
            elif command == "318":
                if self._whois_building and self._on_whois:
                    info = self._whois_cache.get(self._whois_building, {})
                    self._on_whois(info)
                self._whois_building = None

            # 433 = Nick in use
            elif command == "433":
                self.nick += "_"
                self._send(f"NICK {self.nick}")
                self._emit_sys(f"Nick taken, trying: {self.nick}")

            elif command == "JOIN":
                nick = self._extract_nick(parts[0])
                if nick == self.nick:
                    self._emit_sys(f"Joined {self.channel}")
                    self._send(f"NAMES {self.channel}")
                else:
                    self._emit_sys(f"{nick} joined the channel")
                    if self._on_join:
                        self._on_join(nick)
                    self._send(f"NAMES {self.channel}")

            elif command == "PART":
                nick = self._extract_nick(parts[0])
                self._emit_sys(f"{nick} left the channel")
                if self._on_part:
                    self._on_part(nick)
                self._send(f"NAMES {self.channel}")

            elif command == "QUIT":
                nick = self._extract_nick(parts[0])
                self._emit_sys(f"{nick} disconnected")
                if self._on_part:
                    self._on_part(nick)
                self._send(f"NAMES {self.channel}")

            elif command == "PRIVMSG":
                nick = self._extract_nick(parts[0])
                target = parts[2]
                msg = parts[3][1:] if len(parts) > 3 else ""

                if msg.startswith("\x01ACTION") and msg.endswith("\x01"):
                    action = msg[8:-1]
                    self._emit_sys(f"* {nick} {action}")
                elif target == self.nick:
                    if self._on_private:
                        self._on_private(nick, msg)
                elif self._on_message:
                    self._on_message(nick, target, msg)

            elif command == "NOTICE":
                msg = parts[3][1:] if len(parts) > 3 else ""
                self._emit_sys(f"[NOTICE] {msg}")

    @staticmethod
    def _extract_nick(prefix: str) -> str:
        if "!" in prefix:
            return prefix[1:prefix.index("!")]
        return prefix.lstrip(":")

    def _send(self, raw: str):
        if self._sock:
            try:
                self._sock.send(f"{raw}\r\n".encode("utf-8"))
            except Exception as e:
                logger.error("irc", f"Send failed: {e}")

    def _emit_sys(self, msg: str):
        if self._on_system:
            self._on_system(msg)
        logger.info("irc", msg)


def generate_machine_token(pubkey_fingerprint: str) -> str:
    """Generate a verification token from this machine.
    This proves the user has a real ShadowCypher install with the correct
    public key, without revealing any private data."""
    import platform
    machine_id = f"{platform.node()}:{platform.machine()}:{pubkey_fingerprint}"
    return hashlib.sha256(machine_id.encode()).hexdigest()[:16]

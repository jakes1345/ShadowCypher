"""
SovereignChatPage — Production GTK3 chat UI for the native WebSocket signal plane.
Replaces all legacy IRC dependencies. Connects to sovereign_chat.py backend.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango

import asyncio
import json
import hashlib
import threading
import time
import websockets
from typing import Optional, Dict, List
from datetime import datetime

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.core.config import config

NICK_COLORS = [
    "#38bdf8", "#f472b6", "#a78bfa", "#34d399", "#fb923c",
    "#facc15", "#f87171", "#22d3ee", "#c084fc", "#4ade80",
    "#e879f9", "#2dd4bf", "#fbbf24", "#60a5fa", "#f97316",
]

def _nick_color(nick: str) -> str:
    idx = int(hashlib.md5(nick.encode()).hexdigest(), 16) % len(NICK_COLORS)
    return NICK_COLORS[idx]


class SovereignChatClient:
    """Async WebSocket client for the Sovereign Chat server."""

    def __init__(self, host="127.0.0.1", port=9090, nick="Operator"):
        self.uri = f"ws://{host}:{port}/ws"
        self.nick = nick
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._on_message = None
        self._on_status = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def on_message(self, cb):
        self._on_message = cb

    def on_status(self, cb):
        self._on_status = cb

    def _emit_status(self, text):
        if self._on_status:
            GLib.idle_add(self._on_status, text)

    def _emit_message(self, data):
        if self._on_message:
            GLib.idle_add(self._on_message, data)

    def connect_threaded(self):
        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect_loop())
        threading.Thread(target=_run, daemon=True, name="SovChatClient").start()

    async def _connect_loop(self):
        self._running = True
        while self._running:
            try:
                self._emit_status("CONNECTING")
                async with websockets.connect(self.uri, ping_interval=20, ping_timeout=10) as ws:
                    self._ws = ws
                    await ws.send(json.dumps({
                        "type": "auth",
                        "nick": self.nick,
                        "fingerprint": "",
                    }))
                    self._emit_status("ONLINE")
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                            self._emit_message(data)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                self._emit_status(f"OFFLINE ({e})")
                self._ws = None
                await asyncio.sleep(5)

    def send(self, msg_type: str, **kwargs):
        if not self._ws or not self._loop:
            return
        payload = {"type": msg_type, **kwargs}
        asyncio.run_coroutine_threadsafe(
            self._ws.send(json.dumps(payload)), self._loop
        )

    def send_chat(self, room: str, text: str):
        self.send("chat", room=room, text=text)

    def join_room(self, room: str):
        self.send("join", room=room)

    def part_room(self, room: str):
        self.send("part", room=room)

    def request_history(self, room: str, limit=50):
        self.send("history", room=room, limit=limit)

    def request_users(self, room: str):
        self.send("users", room=room)

    def disconnect(self):
        self._running = False


class SovereignChatPage(Gtk.Box):
    """Full-featured sovereign chat interface — zero IRC dependencies."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class("sovereign-chat")

        self._nick = config.identity.handle or "Operator"
        self._active_room: str = "#general"
        self._rooms: Dict[str, Dict] = {}  # room -> {buf, members}
        self._is_admin = False

        self._apply_css()
        self._build_ui()
        self._init_client()

    def _apply_css(self):
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .sov-sidebar { background-color: #0a0f1a; border-right: 1px solid #1a2540; }
            .sov-sidebar-row { padding: 8px 14px; border-radius: 6px; color: #8892b0; }
            .sov-sidebar-row:hover { background-color: #112240; color: #ccd6f6; }
            .sov-sidebar-row.active { background-color: #1d4ed8; color: #ffffff; }
            .sov-header { background-color: #0d1424; border-bottom: 1px solid #1a2540; padding: 12px 20px; }
            .sov-chat-area { background-color: #020817; }
            .sov-input { background: #0f172a; color: #e2e8f0; border: 1px solid #1e3a5f;
                         border-radius: 8px; padding: 10px 14px; font-family: 'Inter', sans-serif; }
            .sov-input:focus { border-color: #3b82f6; }
            .sov-user-panel { background-color: #0a0f1a; border-left: 1px solid #1a2540; }
            .sov-status-online { color: #34d399; font-weight: 700; }
            .sov-status-offline { color: #f87171; font-weight: 700; }
            .sov-msg-view { background-color: transparent; color: #cbd5e1;
                            font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

    def _build_ui(self):
        # Main horizontal split
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(hbox, True, True, 0)

        # ── LEFT: Room sidebar ──
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.get_style_context().add_class("sov-sidebar")
        sidebar.set_size_request(200, -1)

        hdr = Gtk.Label()
        hdr.set_markup("<span size='small' weight='800' color='#475569'>SOVEREIGN ROOMS</span>")
        hdr.set_margin_top(14); hdr.set_margin_start(14); hdr.set_margin_bottom(8)
        hdr.set_halign(Gtk.Align.START)
        sidebar.pack_start(hdr, False, False, 0)

        self.room_list = Gtk.ListBox()
        self.room_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.room_list.connect("row-activated", self._on_room_select)
        room_scroll = Gtk.ScrolledWindow()
        room_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        room_scroll.add(self.room_list)
        sidebar.pack_start(room_scroll, True, True, 0)

        # Status indicator
        self.status_lbl = Gtk.Label(label="● OFFLINE")
        self.status_lbl.get_style_context().add_class("sov-status-offline")
        self.status_lbl.set_margin_bottom(10); self.status_lbl.set_margin_start(14)
        self.status_lbl.set_halign(Gtk.Align.START)
        sidebar.pack_end(self.status_lbl, False, False, 0)

        hbox.pack_start(sidebar, False, False, 0)

        # ── CENTER: Chat area ──
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.get_style_context().add_class("sov-chat-area")

        # Header bar
        header_box = Gtk.Box(spacing=10)
        header_box.get_style_context().add_class("sov-header")
        self.room_title = Gtk.Label()
        self.room_title.set_markup("<span size='large' weight='800' color='#3b82f6'>#general</span>")
        header_box.pack_start(self.room_title, False, False, 0)
        self.room_topic = Gtk.Label(label="Sovereign Communication")
        self.room_topic.set_ellipsize(Pango.EllipsizeMode.END)
        self.room_topic.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.39, 0.43, 0.53, 1))
        header_box.pack_start(self.room_topic, True, True, 10)
        center.pack_start(header_box, False, False, 0)

        # Message stack (one buffer per room)
        self.chat_stack = Gtk.Stack()
        self.chat_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        center.pack_start(self.chat_stack, True, True, 0)

        # Input bar
        input_box = Gtk.Box(spacing=10)
        input_box.set_margin_start(16); input_box.set_margin_end(16)
        input_box.set_margin_top(8); input_box.set_margin_bottom(12)
        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("sov-input")
        self.entry.set_placeholder_text("Type a message…")
        self.entry.connect("activate", self._on_send)
        input_box.pack_start(self.entry, True, True, 0)
        center.pack_start(input_box, False, False, 0)

        hbox.pack_start(center, True, True, 0)

        # ── RIGHT: User panel ──
        self.user_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.user_panel.get_style_context().add_class("sov-user-panel")
        self.user_panel.set_size_request(170, -1)
        self.user_panel.set_margin_top(10)

        user_hdr = Gtk.Label()
        user_hdr.set_markup("<span size='small' weight='800' color='#475569'>ONLINE</span>")
        user_hdr.set_halign(Gtk.Align.START); user_hdr.set_margin_start(12)
        self.user_panel.pack_start(user_hdr, False, False, 4)

        self.user_list = Gtk.ListBox()
        user_scroll = Gtk.ScrolledWindow()
        user_scroll.add(self.user_list)
        self.user_panel.pack_start(user_scroll, True, True, 0)

        hbox.pack_start(self.user_panel, False, False, 0)

        # Initialize default room buffer
        self._ensure_room("#general")

    def _ensure_room(self, room: str):
        if room in self._rooms:
            return
        buf = Gtk.TextBuffer()
        buf.create_tag("system", foreground="#475569", style=Pango.Style.ITALIC)
        buf.create_tag("timestamp", foreground="#334155")
        buf.create_tag("self_nick", foreground="#3b82f6", weight=Pango.Weight.BOLD)
        buf.create_tag("admin_nick", foreground="#f59e0b", weight=Pango.Weight.BOLD)
        for c in NICK_COLORS:
            buf.create_tag(f"n{c.replace('#','')}", foreground=c, weight=Pango.Weight.BOLD)

        view = Gtk.TextView(buffer=buf)
        view.set_editable(False); view.set_cursor_visible(False)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.get_style_context().add_class("sov-msg-view")

        scroll = Gtk.ScrolledWindow()
        scroll.add(view)
        scroll.show_all()

        self.chat_stack.add_named(scroll, room)
        self._rooms[room] = {"buf": buf, "scroll": scroll, "members": []}

        # Add sidebar row
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label=f"  🛡  {room}")
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("sov-sidebar-row")
        row.add(lbl)
        row._room = room
        self.room_list.add(row)
        row.show_all()

    def _init_client(self):
        sov_cfg = config.irc if hasattr(config, "irc") else None
        host = "127.0.0.1"
        port = 9090

        self.client = SovereignChatClient(host=host, port=port, nick=self._nick)
        self.client.on_message(self._on_ws_message)
        self.client.on_status(self._on_ws_status)

        # Start sovereign chat server in background
        from shadowcypher.core.sovereign_chat import sovereign_chat_server
        sovereign_chat_server.start_threaded()

        # Give server a moment to bind, then connect
        GLib.timeout_add(1500, lambda: (self.client.connect_threaded(), False)[-1])

    def _on_ws_status(self, status: str):
        if "ONLINE" in status.upper():
            self.status_lbl.set_text("● ONLINE")
            self.status_lbl.get_style_context().remove_class("sov-status-offline")
            self.status_lbl.get_style_context().add_class("sov-status-online")
        else:
            self.status_lbl.set_text(f"● {status}")
            self.status_lbl.get_style_context().remove_class("sov-status-online")
            self.status_lbl.get_style_context().add_class("sov-status-offline")

    def _on_ws_message(self, data: dict):
        msg_type = data.get("type", "")

        if msg_type == "auth_ok":
            self._is_admin = data.get("is_admin", False)
            for r in data.get("rooms", []):
                self._ensure_room(r)
            self.client.request_history("#general")
            self._append_system("#general", "Connected to Sovereign Signal Plane.")

        elif msg_type == "chat":
            room = data.get("room", "#general")
            self._ensure_room(room)
            nick = data.get("nick", "?")
            text = data.get("text", "")
            is_self = (nick == self._nick)
            is_admin = data.get("is_admin", False)
            self._append_chat(room, nick, text, is_self, is_admin)

        elif msg_type == "join":
            room = data.get("room", "#general")
            nick = data.get("nick", "?")
            self._ensure_room(room)
            self._append_system(room, f"{nick} joined {room}")
            self.client.request_users(room)

        elif msg_type == "part":
            room = data.get("room", "#general")
            nick = data.get("nick", "?")
            self._append_system(room, f"{nick} left {room}")
            self.client.request_users(room)

        elif msg_type == "room_info":
            room = data.get("room", "#general")
            self._ensure_room(room)
            if room in self._rooms:
                self._rooms[room]["members"] = data.get("members", [])
            if room == self._active_room:
                self._refresh_user_list()

        elif msg_type == "users":
            room = data.get("room", "#general")
            if room in self._rooms:
                self._rooms[room]["members"] = [u["nick"] for u in data.get("users", [])]
            if room == self._active_room:
                self._refresh_user_list()

        elif msg_type == "history":
            room = data.get("room", "#general")
            self._ensure_room(room)
            for m in data.get("messages", []):
                is_self = (m.get("nick") == self._nick)
                self._append_chat(room, m["nick"], m["text"], is_self, False)

        elif msg_type == "error":
            self._append_system(self._active_room, f"ERROR: {data.get('text', '?')}")

    def _append_chat(self, room: str, nick: str, text: str, is_self: bool, is_admin: bool):
        if room not in self._rooms:
            return
            
        # APEX_HARDENING: Scrub sensitive hex patterns (long keys/hashes)
        import re
        scrubbed_text = re.sub(r'[0-9a-fA-F]{32,}', lambda m: f"{m.group(0)[:8]}...[REDACTED]", text)
        
        buf = self._rooms[room]["buf"]
        it = buf.get_end_iter()

        ts = datetime.now().strftime("[%H:%M] ")
        buf.insert_with_tags_by_name(it, ts, "timestamp")

        it = buf.get_end_iter()
        if is_self:
            tag = "self_nick"
        elif is_admin:
            tag = "admin_nick"
        else:
            color = _nick_color(nick).replace("#", "")
            tag = f"n{color}"
        buf.insert_with_tags_by_name(it, f"{nick}: ", tag)

        it = buf.get_end_iter()
        buf.insert(it, f"{scrubbed_text}\n")
        self._auto_scroll(room)

    def _append_system(self, room: str, text: str):
        if room not in self._rooms:
            return
        buf = self._rooms[room]["buf"]
        it = buf.get_end_iter()
        ts = datetime.now().strftime("[%H:%M] ")
        buf.insert_with_tags_by_name(it, f"{ts}» {text}\n", "system")
        self._auto_scroll(room)

    def _auto_scroll(self, room: str):
        if room not in self._rooms:
            return
        scroll = self._rooms[room]["scroll"]
        adj = scroll.get_vadjustment()
        GLib.idle_add(lambda: adj.set_value(adj.get_upper() - adj.get_page_size()))

    def _refresh_user_list(self):
        for child in self.user_list.get_children():
            self.user_list.remove(child)
        members = self._rooms.get(self._active_room, {}).get("members", [])
        for nick in members:
            row = Gtk.ListBoxRow()
            color = _nick_color(nick)
            lbl = Gtk.Label()
            lbl.set_markup(f"<span color='{color}'>● {nick}</span>")
            lbl.set_halign(Gtk.Align.START); lbl.set_margin_start(12)
            row.add(lbl)
            self.user_list.add(row)
        self.user_list.show_all()

    def _on_room_select(self, listbox, row):
        room = row._room
        self._active_room = room
        self.chat_stack.set_visible_child_name(room)
        self.room_title.set_markup(f"<span size='large' weight='800' color='#3b82f6'>{room}</span>")
        self.client.request_users(room)
        self.client.request_history(room)

    def _on_send(self, entry):
        text = entry.get_text().strip()
        if not text:
            return
        entry.set_text("")

        if text.startswith("/join "):
            room = text.split(" ", 1)[1].strip()
            if not room.startswith("#"):
                room = f"#{room}"
            self._ensure_room(room)
            self.client.join_room(room)
        elif text.startswith("/part"):
            self.client.part_room(self._active_room)
        else:
            self.client.send_chat(self._active_room, text)

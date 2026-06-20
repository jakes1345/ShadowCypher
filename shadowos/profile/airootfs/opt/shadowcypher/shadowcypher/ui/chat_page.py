import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango
import threading
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


def _api_get(path: str, api_key: str) -> dict:
    base = getattr(config, "api_base_url", "https://api.shadowcypher.site")
    url = f"{base}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
        return json.loads(r.read())


def _api_post(path: str, api_key: str, body: dict) -> dict:
    base = getattr(config, "api_base_url", "https://api.shadowcypher.site")
    url = f"{base}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
        return json.loads(r.read())


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local = dt.astimezone()
        return local.strftime("%H:%M")
    except Exception:
        return ""


NICK_COLORS = [
    "#60a5fa", "#34d399", "#f59e0b", "#f87171",
    "#a78bfa", "#fb923c", "#38bdf8", "#4ade80",
]

def _nick_color(nick: str) -> str:
    return NICK_COLORS[hash(nick) % len(NICK_COLORS)]


class ChatPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        self._api_key: str = ""
        self._rooms: list = []
        self._current_room: str = "global"
        self._messages: list = []
        self._online: list = []
        self._last_msg_id: str = ""
        self._polling = False
        self._poll_thread = None

        self._load_api_key()
        self._build_ui()
        self._start_polling()

    # ── API key ──────────────────────────────────────────────────────────────

    def _load_api_key(self):
        try:
            key_path = getattr(config, "api_key_path", None)
            if key_path:
                import os
                if os.path.exists(key_path):
                    with open(key_path) as f:
                        self._api_key = f.read().strip()
                    return
            self._api_key = getattr(config, "api_key", "") or ""
        except Exception:
            self._api_key = ""

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Left: room list sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.set_size_request(200, -1)
        sidebar.get_style_context().add_class("chat-sidebar")

        sidebar_header = Gtk.Label()
        sidebar_header.set_markup("<span weight='bold' color='#94a3b8' size='small'>CHANNELS</span>")
        sidebar_header.set_halign(Gtk.Align.START)
        sidebar_header.set_margin_start(12)
        sidebar_header.set_margin_top(12)
        sidebar_header.set_margin_bottom(6)
        sidebar.pack_start(sidebar_header, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)

        self._room_list = Gtk.ListBox()
        self._room_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._room_list.connect("row-selected", self._on_room_selected)
        scroller.add(self._room_list)
        sidebar.pack_start(scroller, True, True, 0)

        self.pack_start(sidebar, False, False, 0)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(sep, False, False, 0)

        # Center: message area
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.set_hexpand(True)

        # Room title bar
        self._room_title = Gtk.Label()
        self._room_title.set_markup("<span weight='bold' color='#e2e8f0'>#global</span>")
        self._room_title.set_halign(Gtk.Align.START)
        self._room_title.set_margin_start(16)
        self._room_title.set_margin_top(10)
        self._room_title.set_margin_bottom(10)
        center.pack_start(self._room_title, False, False, 0)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        center.pack_start(sep2, False, False, 0)

        # Message feed
        msg_scroller = Gtk.ScrolledWindow()
        msg_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        msg_scroller.set_vexpand(True)

        self._msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._msg_box.set_margin_start(12)
        self._msg_box.set_margin_end(12)
        self._msg_box.set_margin_top(8)
        self._msg_box.set_valign(Gtk.Align.END)
        self._msg_box.set_vexpand(True)

        self._msg_viewport = Gtk.Viewport()
        self._msg_viewport.add(self._msg_box)
        msg_scroller.add(self._msg_viewport)
        center.pack_start(msg_scroller, True, True, 0)
        self._msg_scroller = msg_scroller

        # Input bar
        input_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_bar.set_margin_start(12)
        input_bar.set_margin_end(12)
        input_bar.set_margin_top(8)
        input_bar.set_margin_bottom(12)

        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Message #global…")
        self._entry.set_hexpand(True)
        self._entry.connect("activate", self._on_send)

        send_btn = Gtk.Button(label="Send")
        send_btn.get_style_context().add_class("suggested-action")
        send_btn.connect("clicked", self._on_send)

        input_bar.pack_start(self._entry, True, True, 0)
        input_bar.pack_start(send_btn, False, False, 0)
        center.pack_start(input_bar, False, False, 0)

        self.pack_start(center, True, True, 0)

        # Separator
        sep3 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(sep3, False, False, 0)

        # Right: online users
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.set_size_request(160, -1)

        online_header = Gtk.Label()
        online_header.set_markup("<span weight='bold' color='#94a3b8' size='small'>ONLINE</span>")
        online_header.set_halign(Gtk.Align.START)
        online_header.set_margin_start(12)
        online_header.set_margin_top(12)
        online_header.set_margin_bottom(6)
        right.pack_start(online_header, False, False, 0)

        online_scroller = Gtk.ScrolledWindow()
        online_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        online_scroller.set_vexpand(True)

        self._online_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._online_box.set_margin_start(12)
        self._online_box.set_margin_top(4)
        online_scroller.add(self._online_box)
        right.pack_start(online_scroller, True, True, 0)

        self.pack_start(right, False, False, 0)

        # CSS
        css = b"""
        .chat-sidebar { background-color: #1e293b; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Seed global room immediately
        self._add_room_row("global", "#global")
        self._select_room("global")

    def _add_room_row(self, name: str, display: str):
        row = Gtk.ListBoxRow()
        row._room_name = name
        lbl = Gtk.Label(label=display, xalign=0)
        lbl.set_margin_start(12)
        lbl.set_margin_top(6)
        lbl.set_margin_bottom(6)
        row.add(lbl)
        self._room_list.add(row)
        row.show_all()

    # ── Room selection ────────────────────────────────────────────────────────

    def _on_room_selected(self, lb, row):
        if row is None:
            return
        name = getattr(row, "_room_name", None)
        if name and name != self._current_room:
            self._select_room(name)

    def _select_room(self, name: str):
        self._current_room = name
        self._messages = []
        self._last_msg_id = ""

        display = f"#{name}"
        for r in self._rooms:
            if r.get("name") == name:
                display = r.get("display_name", display)
                break

        GLib.idle_add(self._room_title.set_markup,
                      f"<span weight='bold' color='#e2e8f0'>{display}</span>")
        GLib.idle_add(self._entry.set_placeholder_text, f"Message {display}…")
        GLib.idle_add(self._clear_messages)
        self._fetch_messages()

    # ── Polling ───────────────────────────────────────────────────────────────

    def _start_polling(self):
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while self._polling:
            try:
                self._fetch_rooms()
                self._fetch_messages()
                self._fetch_online()
                self._send_presence()
            except Exception as e:
                logger.warning("chat", f"poll error: {e}")
            time.sleep(2)

    def _fetch_rooms(self):
        if not self._api_key:
            return
        try:
            data = _api_get("/v1/chat/rooms", self._api_key)
            rooms = data.get("rooms", [])
            if rooms != self._rooms:
                self._rooms = rooms
                GLib.idle_add(self._refresh_room_list)
        except Exception:
            pass

    def _fetch_messages(self):
        if not self._api_key:
            return
        try:
            data = _api_get(f"/v1/chat/messages?room={self._current_room}&limit=50", self._api_key)
            msgs = data.get("messages", [])
            if not msgs:
                return
            new_msgs = [m for m in msgs if m["id"] not in {x["id"] for x in self._messages}]
            if new_msgs:
                self._messages.extend(new_msgs)
                self._messages.sort(key=lambda m: m["created_at"])
                GLib.idle_add(self._render_new_messages, new_msgs)
        except Exception:
            pass

    def _fetch_online(self):
        if not self._api_key:
            return
        try:
            data = _api_get(f"/v1/chat/online?room={self._current_room}", self._api_key)
            online = data.get("online", [])
            if online != self._online:
                self._online = online
                GLib.idle_add(self._refresh_online)
        except Exception:
            pass

    def _send_presence(self):
        if not self._api_key:
            return
        try:
            _api_post("/v1/chat/presence", self._api_key, {"room": self._current_room})
        except Exception:
            pass

    # ── Render ────────────────────────────────────────────────────────────────

    def _refresh_room_list(self):
        existing = set()
        for row in self._room_list.get_children():
            name = getattr(row, "_room_name", None)
            if name:
                existing.add(name)

        for room in self._rooms:
            name = room.get("name", "")
            if name and name not in existing:
                display = room.get("display_name", f"#{name}")
                self._add_room_row(name, display)

    def _clear_messages(self):
        for child in self._msg_box.get_children():
            self._msg_box.remove(child)

    def _render_new_messages(self, msgs: list):
        for msg in msgs:
            self._append_message_row(msg)
        self._scroll_to_bottom()

    def _append_message_row(self, msg: dict):
        nick = msg.get("nick", "?")
        content = msg.get("content", "")
        ts = _fmt_time(msg.get("created_at", ""))
        color = _nick_color(nick)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_top(2)
        row.set_margin_bottom(2)

        # Avatar circle (colored label)
        avatar = Gtk.Label(label=nick[0].upper())
        avatar.set_size_request(32, 32)
        avatar.set_markup(
            f"<span background='{color}' color='#0f172a' weight='bold'> {nick[0].upper()} </span>"
        )

        # Content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Gtk.Label()
        header.set_markup(
            f"<span weight='bold' color='{color}'>{GLib.markup_escape_text(nick)}</span>"
            f"  <span size='small' color='#64748b'>{ts}</span>"
        )
        header.set_halign(Gtk.Align.START)

        body = Gtk.Label(label=content)
        body.set_halign(Gtk.Align.START)
        body.set_line_wrap(True)
        body.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        body.set_selectable(True)
        body.set_xalign(0)
        body.get_style_context().add_class("dim-label") if not content.strip() else None

        content_box.pack_start(header, False, False, 0)
        content_box.pack_start(body, False, False, 0)

        row.pack_start(avatar, False, False, 0)
        row.pack_start(content_box, True, True, 0)

        self._msg_box.pack_start(row, False, True, 0)
        row.show_all()

    def _scroll_to_bottom(self):
        def _do_scroll():
            adj = self._msg_scroller.get_vadjustment()
            adj.set_value(adj.get_upper())
        GLib.idle_add(_do_scroll)

    def _refresh_online(self):
        for child in self._online_box.get_children():
            self._online_box.remove(child)

        for user in self._online:
            nick = user.get("nick", "?")
            color = _nick_color(nick)
            lbl = Gtk.Label()
            lbl.set_markup(
                f"<span color='#22c55e'>● </span>"
                f"<span color='{color}'>{GLib.markup_escape_text(nick)}</span>"
            )
            lbl.set_halign(Gtk.Align.START)
            self._online_box.pack_start(lbl, False, False, 0)
            lbl.show()

        if not self._online:
            empty = Gtk.Label()
            empty.set_markup("<span color='#475569'>no one here</span>")
            empty.set_halign(Gtk.Align.START)
            self._online_box.pack_start(empty, False, False, 0)
            empty.show()

    # ── Send ─────────────────────────────────────────────────────────────────

    def _on_send(self, *_):
        content = self._entry.get_text().strip()
        if not content:
            return
        if not self._api_key:
            self._show_error("No API key configured.")
            return

        self._entry.set_text("")
        self._entry.set_sensitive(False)

        def _do_send():
            try:
                data = _api_post(
                    "/v1/chat/send", self._api_key,
                    {"room": self._current_room, "content": content}
                )
                msg = data.get("message")
                if msg:
                    GLib.idle_add(self._on_sent, msg)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
            finally:
                GLib.idle_add(self._entry.set_sensitive, True)
                GLib.idle_add(self._entry.grab_focus)

        threading.Thread(target=_do_send, daemon=True).start()

    def _on_sent(self, msg: dict):
        if msg["id"] not in {m["id"] for m in self._messages}:
            self._messages.append(msg)
            self._append_message_row(msg)
            self._scroll_to_bottom()

    def _show_error(self, text: str):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=text,
        )
        dialog.run()
        dialog.destroy()

    def do_unrealize(self):
        self._polling = False
        Gtk.Box.do_unrealize(self)

import gi

gi.require_version("Gtk", "3.0")
import json
import mimetypes
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid as _uuid_mod
from datetime import datetime

from gi.repository import Gdk, GLib, Gtk, Pango

try:
    import websocket
    _HAS_WS = True
except ImportError:
    _HAS_WS = False

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


def _api_get(path: str, api_key: str) -> dict:
    base = getattr(config, "api_base_url", "https://api.shadowcypher.site")
    url = f"{base}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
        return json.loads(r.read())


_ATTACH_RE = re.compile(r'\[attachment:([^\]:]+):([^\]]*)\]')


def _api_upload(path: str, api_key: str, file_path: str, file_name: str) -> dict:
    base = getattr(config, "api_base_url", "https://api.shadowcypher.site")
    url = f"{base}{path}"
    boundary = f"----FormBoundary{_uuid_mod.uuid4().hex}"
    with open(file_path, "rb") as f:
        file_data = f.read()
    mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310
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

        self._api_key = ""
        self._nick = "user"
        self._rooms = []
        self._current_room = "global"
        self._messages = []
        self._online = []

        # WebSocket state
        self._ws = None
        self._ws_lock = threading.Lock()
        self._ws_stop = threading.Event()  # set to terminate run loop

        self._load_api_key()
        self._build_ui()
        self._resolve_nick_async()
        self._fetch_rooms_async()
        self._fetch_dms_async()
        self._ws_start("global")

    # ── API key ───────────────────────────────────────────────────────────────

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

    def _resolve_nick_async(self):
        if not self._api_key:
            return
        def _do():
            try:
                data = _api_get("/v1/me", self._api_key)
                email = data.get("email", "")
                if "@" in email:
                    self._nick = email.split("@")[0]
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    # ── WebSocket ─────────────────────────────────────────────────────────────

    def _ws_start(self, room: str):
        if not self._api_key:
            return
        if not _HAS_WS:
            self._poll_start()
            return
        self._ws_stop.clear()
        threading.Thread(target=self._ws_run_loop, args=(room,), daemon=True).start()

    def _ws_run_loop(self, _room: str):
        base = getattr(config, "api_base_url", "https://api.shadowcypher.site")
        ws_base = base.replace("https://", "wss://").replace("http://", "ws://")

        while not self._ws_stop.is_set():
            nick = urllib.parse.quote(self._nick, safe="")
            url = (f"{ws_base}/v1/chat/ws"
                   f"?room={self._current_room}&key={self._api_key}&nick={nick}")
            try:
                ws = websocket.WebSocketApp(
                    url,
                    on_open=self._ws_on_open,
                    on_message=self._ws_on_message,
                    on_error=self._ws_on_error,
                    on_close=self._ws_on_close,
                )
                with self._ws_lock:
                    self._ws = ws
                ws.run_forever()
            except Exception as e:
                logger.warning("chat", f"ws: {e}")
            finally:
                with self._ws_lock:
                    if self._ws is ws:
                        self._ws = None

            if not self._ws_stop.is_set():
                # 3s back-off on error; immediate if we closed for a room switch
                self._ws_stop.wait(timeout=3)

    def _ws_on_open(self, ws):
        logger.info("chat", "WebSocket connected")
        threading.Thread(target=self._ws_ping_loop, args=(ws,), daemon=True).start()

    def _ws_on_close(self, ws, code, msg):
        logger.info("chat", f"WebSocket closed {code}")

    def _ws_on_error(self, ws, err):
        logger.warning("chat", f"WebSocket error: {err}")

    def _ws_on_message(self, ws, raw: str):
        try:
            frame = json.loads(raw)
        except Exception:
            return
        t = frame.get("type")
        if t == "history":
            GLib.idle_add(self._handle_history, frame.get("messages", []))
        elif t == "message":
            GLib.idle_add(self._handle_incoming, frame)
        elif t == "presence":
            GLib.idle_add(self._handle_presence, frame)

    def _ws_ping_loop(self, ws):
        while True:
            time.sleep(25)
            try:
                ws.send(json.dumps({"type": "ping"}))
            except Exception:
                break

    def _ws_send(self, payload: dict) -> bool:
        with self._ws_lock:
            ws = self._ws
        if ws is None:
            return False
        try:
            ws.send(json.dumps(payload))
            return True
        except Exception:
            return False

    def _ws_switch_room(self):
        # Close current socket; run loop reconnects immediately to _current_room
        with self._ws_lock:
            ws = self._ws
        if ws:
            try:
                ws.close()
            except Exception:
                pass

    # ── Fallback polling (when websocket-client is not installed) ─────────────

    def _poll_start(self):
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _poll_loop(self):
        while not self._ws_stop.is_set():
            try:
                self._poll_rooms()
                self._poll_messages()
                self._poll_online()
                self._poll_presence()
            except Exception as e:
                logger.warning("chat", f"poll: {e}")
            self._ws_stop.wait(timeout=2)

    def _poll_rooms(self):
        try:
            data = _api_get("/v1/chat/rooms", self._api_key)
            rooms = data.get("rooms", [])
            if rooms != self._rooms:
                self._rooms = rooms
                GLib.idle_add(self._refresh_room_list)
        except Exception:
            pass

    def _poll_messages(self):
        try:
            data = _api_get(
                f"/v1/chat/messages?room={self._current_room}&limit=50", self._api_key
            )
            msgs = data.get("messages", [])
            ids = {m.get("id") for m in self._messages}
            new = [m for m in msgs if m.get("id") not in ids]
            if new:
                self._messages.extend(new)
                self._messages.sort(key=lambda m: m.get("created_at", ""))
                GLib.idle_add(self._render_new_messages, new)
        except Exception:
            pass

    def _poll_online(self):
        try:
            data = _api_get(f"/v1/chat/online?room={self._current_room}", self._api_key)
            online = data.get("online", [])
            if online != self._online:
                self._online = online
                GLib.idle_add(self._refresh_online)
        except Exception:
            pass

    def _poll_presence(self):
        try:
            _api_post("/v1/chat/presence", self._api_key, {"room": self._current_room})
        except Exception:
            pass

    # ── Rooms fetch ───────────────────────────────────────────────────────────

    def _fetch_rooms_async(self):
        if not self._api_key:
            return
        def _do():
            try:
                data = _api_get("/v1/chat/rooms", self._api_key)
                rooms = data.get("rooms", [])
                if rooms != self._rooms:
                    self._rooms = rooms
                    GLib.idle_add(self._refresh_room_list)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    # ── WS frame handlers (GTK main thread) ──────────────────────────────────

    def _handle_history(self, msgs: list):
        self._messages = list(msgs)
        self._clear_messages()
        for msg in msgs:
            self._append_message_row(msg)
        self._scroll_to_bottom()

    def _handle_incoming(self, frame: dict):
        if frame.get("id") in {m.get("id") for m in self._messages}:
            return
        self._messages.append(frame)
        self._append_message_row(frame)
        self._scroll_to_bottom()

    def _handle_presence(self, frame: dict):
        nick = frame.get("nick", "")
        if frame.get("online"):
            if not any(u.get("nick") == nick for u in self._online):
                self._online.append({"nick": nick, "user_id": frame.get("user_id", "")})
        else:
            self._online = [u for u in self._online if u.get("nick") != nick]
        self._refresh_online()

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.set_size_request(200, -1)
        sidebar.get_style_context().add_class("chat-sidebar")

        dm_header = Gtk.Label()
        dm_header.set_markup(
            "<span weight='bold' color='#00f2ff' size='small'>DIRECT MESSAGES</span>"
        )
        dm_header.set_halign(Gtk.Align.START)
        dm_header.set_margin_start(12)
        dm_header.set_margin_top(12)
        dm_header.set_margin_bottom(4)
        sidebar.pack_start(dm_header, False, False, 0)

        dm_scroller = Gtk.ScrolledWindow()
        dm_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        dm_scroller.set_size_request(-1, 140)

        self._dm_list = Gtk.ListBox()
        self._dm_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._dm_list.connect("row-selected", self._on_room_selected)
        dm_scroller.add(self._dm_list)
        sidebar.pack_start(dm_scroller, False, False, 0)

        new_dm_btn = Gtk.Button(label="✉ New DM")
        new_dm_btn.set_margin_start(12)
        new_dm_btn.set_margin_end(12)
        new_dm_btn.set_margin_top(4)
        new_dm_btn.set_margin_bottom(8)
        new_dm_btn.connect("clicked", self._on_new_dm)
        sidebar.pack_start(new_dm_btn, False, False, 0)

        sidebar_header = Gtk.Label()
        sidebar_header.set_markup(
            "<span weight='bold' color='#94a3b8' size='small'>PUBLIC CHANNELS</span>"
        )
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
        self.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

        # Center: message area
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.set_hexpand(True)

        self._room_title = Gtk.Label()
        self._room_title.set_markup("<span weight='bold' color='#e2e8f0'>#global</span>")
        self._room_title.set_halign(Gtk.Align.START)
        self._room_title.set_margin_start(16)
        self._room_title.set_margin_top(10)
        self._room_title.set_margin_bottom(10)
        center.pack_start(self._room_title, False, False, 0)
        center.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

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

        input_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_bar.set_margin_start(12)
        input_bar.set_margin_end(12)
        input_bar.set_margin_top(8)
        input_bar.set_margin_bottom(12)

        attach_btn = Gtk.Button(label="📎")
        attach_btn.set_tooltip_text("Attach file (max 10 MB)")
        attach_btn.connect("clicked", self._on_attach)
        self._attach_btn = attach_btn

        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Message #global…")
        self._entry.set_hexpand(True)
        self._entry.connect("activate", self._on_send)

        send_btn = Gtk.Button(label="Send")
        send_btn.get_style_context().add_class("suggested-action")
        send_btn.connect("clicked", self._on_send)

        input_bar.pack_start(attach_btn, False, False, 0)
        input_bar.pack_start(self._entry, True, True, 0)
        input_bar.pack_start(send_btn, False, False, 0)
        center.pack_start(input_bar, False, False, 0)

        self.pack_start(center, True, True, 0)
        self.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

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

        css = b".chat-sidebar { background-color: #1e293b; }"
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._add_room_row("global", "#global")

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
        self._online = []

        display = f"#{name}"
        for r in self._rooms:
            if r.get("name") == name:
                display = r.get("display_name", display)
                break

        self._room_title.set_markup(f"<span weight='bold' color='#e2e8f0'>{display}</span>")
        self._entry.set_placeholder_text(f"Message {display}…")
        self._clear_messages()
        self._refresh_online()

        if _HAS_WS and self._api_key:
            # Closing the socket causes the run loop to immediately reconnect
            # to the updated _current_room.
            self._ws_switch_room()

    # ── Render helpers ────────────────────────────────────────────────────────

    def _refresh_room_list(self):
        existing = {getattr(r, "_room_name", None) for r in self._room_list.get_children()}
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

        avatar = Gtk.Label(label=nick[0].upper())
        avatar.set_size_request(32, 32)
        avatar.set_markup(
            f"<span background='{color}' color='#0f172a' weight='bold'> {nick[0].upper()} </span>"
        )

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Gtk.Label()
        header.set_markup(
            f"<span weight='bold' color='{color}'>{GLib.markup_escape_text(nick)}</span>"
            f"  <span size='small' color='#64748b'>{ts}</span>"
        )
        header.set_halign(Gtk.Align.START)

        m = _ATTACH_RE.fullmatch(content.strip()) if content else None
        if m:
            key, fname = m.group(1), m.group(2) or "file"
            base = getattr(config, "api_base_url", "https://api.shadowcypher.site")
            dl_url = (f"{base}/v1/files/{urllib.parse.quote(key, safe='')}"
                      f"?key={urllib.parse.quote(self._api_key, safe='')}")
            body = Gtk.LinkButton.new_with_label(dl_url, f"📎 {fname}")
            body.set_halign(Gtk.Align.START)
        else:
            body = Gtk.Label(label=content)
            body.set_halign(Gtk.Align.START)
            body.set_line_wrap(True)
            body.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            body.set_selectable(True)
            body.set_xalign(0)

        content_box.pack_start(header, False, False, 0)
        content_box.pack_start(body, False, False, 0)

        row.pack_start(avatar, False, False, 0)
        row.pack_start(content_box, True, True, 0)

        self._msg_box.pack_start(row, False, True, 0)
        row.show_all()

    def _scroll_to_bottom(self):
        def _do():
            adj = self._msg_scroller.get_vadjustment()
            adj.set_value(adj.get_upper())
        GLib.idle_add(_do)

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

    # ── Direct Messages ───────────────────────────────────────────────────────

    def _fetch_dms_async(self):
        if not self._api_key:
            return
        def _do():
            try:
                data = _api_get("/v1/chat/dm", self._api_key)
                dms = data.get("dms", [])
                GLib.idle_add(self._refresh_dm_list, dms)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _refresh_dm_list(self, dms: list):
        for row in self._dm_list.get_children():
            self._dm_list.remove(row)
        for dm in dms:
            self._add_dm_row(dm.get("name", ""), dm.get("display_name", "?"), dm.get("other_nick", ""))

    def _add_dm_row(self, room_name: str, display: str, other_nick: str):
        row = Gtk.ListBoxRow()
        row._room_name = room_name
        lbl = Gtk.Label(label=display, xalign=0)
        lbl.set_markup(f"<span color='#00f2ff'>{GLib.markup_escape_text(display)}</span>")
        lbl.set_margin_start(12)
        lbl.set_margin_top(5)
        lbl.set_margin_bottom(5)
        row.add(lbl)
        self._dm_list.add(row)
        row.show_all()

    def _on_new_dm(self, *_):
        dialog = Gtk.Dialog(
            title="New Direct Message",
            transient_for=self.get_toplevel(),
            modal=True,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OK, Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_margin_top(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_bottom(12)

        label = Gtk.Label(label="Enter handle (without @):")
        label.set_halign(Gtk.Align.START)
        content.pack_start(label, False, False, 0)

        entry = Gtk.Entry()
        entry.set_placeholder_text("e.g., alice")
        content.pack_start(entry, False, False, 6)
        content.show_all()

        response = dialog.run()
        handle = entry.get_text().strip().lower()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and handle:
            self._open_dm_api(handle)

    def _open_dm_api(self, handle: str):
        if not self._api_key:
            self._show_error("No API key configured.")
            return

        def _do():
            try:
                data = _api_post("/v1/chat/dm/open", self._api_key, {"handle": handle})
                if data.get("ok"):
                    room = data.get("room", "")
                    display = data.get("display", f"@{handle}")
                    GLib.idle_add(self._on_dm_opened, room, display)
                else:
                    GLib.idle_add(self._show_error, data.get("error", "Could not open DM"))
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))

        threading.Thread(target=_do, daemon=True).start()

    def _on_dm_opened(self, room_name: str, display: str):
        # Add to DM list if not already there
        existing = {getattr(r, "_room_name", None) for r in self._dm_list.get_children()}
        if room_name not in existing:
            self._add_dm_row(room_name, display, display.lstrip("@"))
        self._select_room(room_name)

    # ── File attach ───────────────────────────────────────────────────────────

    def _on_attach(self, *_):
        if not self._api_key:
            self._show_error("No API key configured.")
            return
        dialog = Gtk.FileChooserDialog(
            title="Choose a file to attach",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        response = dialog.run()
        file_path = dialog.get_filename()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not file_path:
            return

        import os
        if os.path.getsize(file_path) > 10 * 1024 * 1024:
            self._show_error("File too large (max 10 MB)")
            return

        file_name = os.path.basename(file_path)
        self._attach_btn.set_sensitive(False)
        self._attach_btn.set_label("⏳")
        threading.Thread(target=self._upload_file_async,
                         args=(file_path, file_name), daemon=True).start()

    def _upload_file_async(self, file_path: str, file_name: str):
        try:
            data = _api_upload("/v1/files/upload", self._api_key, file_path, file_name)
            if not data.get("ok"):
                GLib.idle_add(self._show_error, data.get("error", "Upload failed"))
                return
            token = f"[attachment:{data['key']}:{data['name']}]"
            sent = self._ws_send({"type": "message", "content": token})
            if not sent:
                _api_post("/v1/chat/send", self._api_key,
                          {"room": self._current_room, "content": token})
        except Exception as e:
            GLib.idle_add(self._show_error, f"Upload error: {e}")
        finally:
            GLib.idle_add(self._attach_btn.set_sensitive, True)
            GLib.idle_add(self._attach_btn.set_label, "📎")

    # ── Send ──────────────────────────────────────────────────────────────────

    def _on_send(self, *_):
        content = self._entry.get_text().strip()
        if not content:
            return
        if not self._api_key:
            self._show_error("No API key configured.")
            return

        self._entry.set_text("")

        if _HAS_WS and self._ws_send({"type": "message", "content": content}):
            return  # server echoes the message back as a frame

        # REST fallback (no WebSocket connection yet or not installed)
        self._entry.set_sensitive(False)

        def _do():
            try:
                data = _api_post(
                    "/v1/chat/send", self._api_key,
                    {"room": self._current_room, "content": content},
                )
                msg = data.get("message")
                if msg:
                    GLib.idle_add(self._handle_incoming, msg)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
            finally:
                GLib.idle_add(self._entry.set_sensitive, True)
                GLib.idle_add(self._entry.grab_focus)

        threading.Thread(target=_do, daemon=True).start()

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
        self._ws_stop.set()
        with self._ws_lock:
            ws = self._ws
        if ws:
            try:
                ws.close()
            except Exception:
                pass
        Gtk.Box.do_unrealize(self)

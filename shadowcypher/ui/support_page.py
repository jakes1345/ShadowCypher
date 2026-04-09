"""Support & Communications — Encrypted tickets + Live IRC with PM tabs."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango
import threading
import os
import json
import time
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from shadowcypher.core.logger import logger


NICK_COLORS = [
    "#38bdf8", "#f472b6", "#a78bfa", "#34d399", "#fb923c",
    "#facc15", "#f87171", "#22d3ee", "#c084fc", "#4ade80",
    "#e879f9", "#2dd4bf", "#fbbf24", "#60a5fa", "#f97316",
]


def _nick_color(nick):
    idx = int(hashlib.md5(nick.encode()).hexdigest(), 16) % len(NICK_COLORS)
    return NICK_COLORS[idx]


class SupportPage(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        from shadowcypher.core.identity import identity
        from shadowcypher.core.config import config

        self._identity = identity
        self._config = config
        self._tickets_dir = Path(config.project_root) / "tickets"
        self._tickets_dir.mkdir(exist_ok=True)

        self._irc = None
        self._pm_tabs = {}
        self._users = []

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.pack_start(self.notebook, True, True, 0)

        self.notebook.append_page(self._build_irc_tab(), Gtk.Label(label="\U0001f4e1 Live Comm-Link"))
        self.notebook.append_page(self._build_ticket_tab(), Gtk.Label(label="\U0001f512 Encrypted Tickets"))

    # ═══════════════════════════════════════════════
    # TAB 1: LIVE IRC
    # ═══════════════════════════════════════════════

    def _build_irc_tab(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)

        config_row = Gtk.Box(spacing=6)

        config_row.pack_start(Gtk.Label(label="Server:"), False, False, 0)
        self.irc_server = Gtk.Entry()
        self.irc_server.set_text(self._config.get("irc", "server", default="irc.libera.chat"))
        self.irc_server.set_width_chars(18)
        config_row.pack_start(self.irc_server, False, False, 0)

        config_row.pack_start(Gtk.Label(label=":"), False, False, 0)
        self.irc_port = Gtk.Entry()
        self.irc_port.set_text(str(self._config.get("irc", "port", default=6697)))
        self.irc_port.set_width_chars(5)
        config_row.pack_start(self.irc_port, False, False, 0)

        config_row.pack_start(Gtk.Label(label="Channel:"), False, False, 0)
        self.irc_channel = Gtk.Entry()
        self.irc_channel.set_text(self._config.get("irc", "channel", default="#shadowcypher-support"))
        self.irc_channel.set_width_chars(22)
        config_row.pack_start(self.irc_channel, True, True, 0)

        self.irc_ssl = Gtk.CheckButton(label="SSL")
        self.irc_ssl.set_active(self._config.get("irc", "use_ssl", default=True))
        config_row.pack_start(self.irc_ssl, False, False, 0)

        vbox.pack_start(config_row, False, False, 0)

        nick_row = Gtk.Box(spacing=6)

        nick_row.pack_start(Gtk.Label(label="Nick:"), False, False, 0)
        self.irc_nick = Gtk.Entry()
        self.irc_nick.set_width_chars(16)
        self.irc_nick.set_text(self._generate_nick())
        nick_row.pack_start(self.irc_nick, False, False, 0)

        from shadowcypher.core.irc import generate_machine_token
        token = generate_machine_token(self._identity.pubkey_fingerprint)
        token_lbl = Gtk.Label(label=f"Token: {token}")
        token_lbl.get_style_context().add_class("text-muted")
        token_lbl.set_selectable(True)
        nick_row.pack_start(token_lbl, False, False, 8)

        nick_row.pack_end(self._mkbtn("Disconnect", self._on_irc_disconnect, "destructive-action"), False, False, 0)
        self.irc_connect_btn = self._mkbtn("\u26a1 Connect", self._on_irc_connect, "suggested-action")
        nick_row.pack_end(self.irc_connect_btn, False, False, 0)

        vbox.pack_start(nick_row, False, False, 0)

        self.irc_status = Gtk.Label(label="DISCONNECTED")
        self.irc_status.set_halign(Gtk.Align.START)
        self.irc_status.get_style_context().add_class("text-muted")
        vbox.pack_start(self.irc_status, False, False, 0)

        chat_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.chat_notebook = Gtk.Notebook()
        self.chat_notebook.set_tab_pos(Gtk.PositionType.BOTTOM)
        self.chat_notebook.set_scrollable(True)

        channel_page = self._make_chat_page()
        self.channel_buffer = channel_page["buffer"]
        self.channel_view = channel_page["view"]
        self.channel_scroll = channel_page["scroll"]
        self.chat_notebook.append_page(channel_page["box"], Gtk.Label(label="# channel"))

        chat_hbox.pack_start(self.chat_notebook, True, True, 0)

        user_frame = Gtk.Frame()
        user_frame.set_size_request(180, -1)
        user_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        user_header = Gtk.Label()
        user_header.set_markup("<b>Online</b>")
        user_header.set_margin_top(6)
        user_header.set_margin_bottom(4)
        user_vbox.pack_start(user_header, False, False, 0)

        self.user_count_lbl = Gtk.Label(label="0 users")
        self.user_count_lbl.get_style_context().add_class("text-muted")
        user_vbox.pack_start(self.user_count_lbl, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        user_vbox.pack_start(sep, False, False, 4)

        self.user_listbox = Gtk.ListBox()
        self.user_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.user_listbox.connect("row-activated", self._on_user_double_click)
        self.user_listbox.connect("button-press-event", self._on_user_right_click)

        user_scroll = Gtk.ScrolledWindow()
        user_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        user_scroll.add(self.user_listbox)
        user_vbox.pack_start(user_scroll, True, True, 0)

        user_frame.add(user_vbox)
        chat_hbox.pack_start(user_frame, False, False, 0)

        vbox.pack_start(chat_hbox, True, True, 0)

        input_row = Gtk.Box(spacing=6)
        self.irc_entry = Gtk.Entry()
        self.irc_entry.set_placeholder_text("Type a message... (Enter to send)")
        self.irc_entry.set_hexpand(True)
        self.irc_entry.connect("activate", self._on_irc_send)
        self.irc_entry.set_sensitive(False)
        input_row.pack_start(self.irc_entry, True, True, 0)

        self.irc_send_btn = self._mkbtn("Send", self._on_irc_send, "suggested-action")
        self.irc_send_btn.set_sensitive(False)
        input_row.pack_start(self.irc_send_btn, False, False, 0)

        vbox.pack_start(input_row, False, False, 0)

        return vbox

    def _make_chat_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        buf = Gtk.TextBuffer()

        tag_table = buf.get_tag_table()
        buf.create_tag("system", foreground="#64748b", style=Pango.Style.ITALIC)
        buf.create_tag("mention", foreground="#fbbf24", weight=Pango.Weight.BOLD)
        buf.create_tag("action", foreground="#a78bfa", style=Pango.Style.ITALIC)
        buf.create_tag("timestamp", foreground="#475569")
        buf.create_tag("self_nick", foreground="#38bdf8", weight=Pango.Weight.BOLD)

        for color in NICK_COLORS:
            safe_name = f"nick_{color.replace('#', '')}"
            if not tag_table.lookup(safe_name):
                buf.create_tag(safe_name, foreground=color, weight=Pango.Weight.BOLD)

        view = Gtk.TextView(buffer=buf)
        view.set_editable(False)
        view.set_cursor_visible(False)
        view.set_monospace(True)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.get_style_context().add_class("terminal-view")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(400)
        scroll.add(view)
        box.pack_start(scroll, True, True, 0)

        return {"box": box, "buffer": buf, "view": view, "scroll": scroll}

    def _generate_nick(self):
        if self._identity.is_admin:
            return "SC_Admin"
        fp = self._identity.pubkey_fingerprint
        if fp:
            return f"sc_{fp[:8]}"
        return "sc_operator"

    def _on_irc_connect(self, btn):
        from shadowcypher.core.irc import IRCClient

        server = self.irc_server.get_text().strip()
        port_str = self.irc_port.get_text().strip()
        channel = self.irc_channel.get_text().strip()
        nick = self.irc_nick.get_text().strip()
        use_ssl = self.irc_ssl.get_active()

        if not server or not channel or not nick:
            self._chat_sys(self.channel_buffer, "Fill in server, channel, and nick.")
            return

        try:
            port = int(port_str)
        except ValueError:
            self._chat_sys(self.channel_buffer, "Invalid port number.")
            return

        if self._irc and self._irc.connected:
            self._irc.disconnect()

        self._config.set("irc", "server", server)
        self._config.set("irc", "port", port)
        self._config.set("irc", "channel", channel)
        self._config.set("irc", "use_ssl", use_ssl)

        self._irc = IRCClient(server=server, port=port, channel=channel, nick=nick, use_ssl=use_ssl)

        self._irc.on_message(self._cb_message)
        self._irc.on_system(self._cb_system)
        self._irc.on_connect(self._cb_connect)
        self._irc.on_userlist(self._cb_userlist)
        self._irc.on_whois(self._cb_whois)
        self._irc.on_private(self._cb_private)
        self._irc.on_join(lambda nick: GLib.idle_add(self._chat_sys, self.channel_buffer, f"\u2192 {nick} joined"))
        self._irc.on_part(lambda nick: GLib.idle_add(self._chat_sys, self.channel_buffer, f"\u2190 {nick} left"))

        self._chat_sys(self.channel_buffer, f"Connecting to {server}:{port} ({channel})...")
        GLib.idle_add(self.irc_status.set_text, f"CONNECTING to {server}:{port}...")

        tab_label = self.chat_notebook.get_tab_label(self.chat_notebook.get_nth_page(0))
        if isinstance(tab_label, Gtk.Label):
            tab_label.set_text(channel)

        self._irc.connect()

    def _on_irc_disconnect(self, btn):
        if self._irc:
            self._irc.disconnect()
        GLib.idle_add(self.irc_entry.set_sensitive, False)
        GLib.idle_add(self.irc_send_btn.set_sensitive, False)
        GLib.idle_add(self.irc_status.set_text, "DISCONNECTED")

    def _on_irc_send(self, widget):
        if not self._irc or not self._irc.connected:
            return
        msg = self.irc_entry.get_text().strip()
        if not msg:
            return
        self.irc_entry.set_text("")

        current_page = self.chat_notebook.get_current_page()

        if msg.startswith("/me "):
            action_text = msg[4:]
            if current_page == 0:
                self._irc.send_action(action_text)
                self._chat_action(self.channel_buffer, self._irc.nick, action_text)
            else:
                pm_nick = self._get_pm_nick_for_page(current_page)
                if pm_nick:
                    self._irc.send_action(action_text, target=pm_nick)
                    buf = self._pm_tabs[pm_nick]["buffer"]
                    self._chat_action(buf, self._irc.nick, action_text)
            return

        if msg.startswith("/msg "):
            parts = msg.split(" ", 2)
            if len(parts) >= 3:
                target_nick, pm_msg = parts[1], parts[2]
                self._irc.send_private(target_nick, pm_msg)
                self._ensure_pm_tab(target_nick)
                buf = self._pm_tabs[target_nick]["buffer"]
                self._chat_msg(buf, self._irc.nick, pm_msg, is_self=True)
                self._focus_pm_tab(target_nick)
            return

        if current_page == 0:
            self._irc.send_message(msg)
            self._chat_msg(self.channel_buffer, self._irc.nick, msg, is_self=True)
        else:
            pm_nick = self._get_pm_nick_for_page(current_page)
            if pm_nick:
                self._irc.send_private(pm_nick, msg)
                buf = self._pm_tabs[pm_nick]["buffer"]
                self._chat_msg(buf, self._irc.nick, msg, is_self=True)

    def _cb_message(self, nick, target, msg):
        GLib.idle_add(self._chat_msg, self.channel_buffer, nick, msg, False)

    def _cb_system(self, msg):
        GLib.idle_add(self._chat_sys, self.channel_buffer, msg)

    def _cb_connect(self):
        GLib.idle_add(self.irc_entry.set_sensitive, True)
        GLib.idle_add(self.irc_send_btn.set_sensitive, True)
        GLib.idle_add(self.irc_status.set_text, f"CONNECTED \u2014 {self._irc.channel}")

    def _cb_userlist(self, names):
        GLib.idle_add(self._update_userlist, names)

    def _cb_whois(self, info):
        GLib.idle_add(self._show_whois, info)

    def _cb_private(self, nick, msg):
        GLib.idle_add(self._handle_pm_incoming, nick, msg)

    def _update_userlist(self, names):
        self._users = sorted(names, key=str.lower)
        for child in self.user_listbox.get_children():
            self.user_listbox.remove(child)

        for name in self._users:
            row = Gtk.ListBoxRow()
            row.set_name(name)
            hbox = Gtk.Box(spacing=8)
            hbox.set_margin_start(8)
            hbox.set_margin_end(8)
            hbox.set_margin_top(4)
            hbox.set_margin_bottom(4)

            color = _nick_color(name)
            dot = Gtk.Label()
            dot.set_markup(f"<span foreground='{color}'>\u25cf</span>")
            hbox.pack_start(dot, False, False, 0)

            lbl = Gtk.Label(label=name, xalign=0)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            hbox.pack_start(lbl, True, True, 0)

            if name in self._pm_tabs:
                pm_indicator = Gtk.Label()
                pm_indicator.set_markup("<span foreground='#fbbf24'>\u2709</span>")
                hbox.pack_end(pm_indicator, False, False, 0)

            row.add(hbox)
            self.user_listbox.add(row)

        self.user_listbox.show_all()
        self.user_count_lbl.set_text(f"{len(self._users)} users")

    def _on_user_double_click(self, listbox, row):
        nick = row.get_name()
        if nick and self._irc and nick != self._irc.nick:
            self._ensure_pm_tab(nick)
            self._focus_pm_tab(nick)

    def _on_user_right_click(self, widget, event):
        if event.button != 3:
            return False

        row = self.user_listbox.get_row_at_y(int(event.y))
        if not row:
            return False

        nick = row.get_name()
        if not nick:
            return False

        menu = Gtk.Menu()

        item_pm = Gtk.MenuItem(label=f"\U0001f4ac Private Message {nick}")
        item_pm.connect("activate", lambda w: self._open_pm(nick))
        menu.append(item_pm)

        item_mention = Gtk.MenuItem(label=f"@ Mention {nick}")
        item_mention.connect("activate", lambda w: self._insert_mention(nick))
        menu.append(item_mention)

        menu.append(Gtk.SeparatorMenuItem())

        item_whois = Gtk.MenuItem(label=f"\U0001f50d Whois {nick}")
        item_whois.connect("activate", lambda w: self._request_whois(nick))
        menu.append(item_whois)

        item_copy = Gtk.MenuItem(label="\U0001f4cb Copy Nick")
        item_copy.connect("activate", lambda w: self._copy_nick(nick))
        menu.append(item_copy)

        if self._identity.is_admin:
            menu.append(Gtk.SeparatorMenuItem())
            item_kick = Gtk.MenuItem(label=f"\U0001f6ab Kick {nick}")
            item_kick.connect("activate", lambda w: self._kick_user(nick))
            menu.append(item_kick)

        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def _open_pm(self, nick):
        if self._irc and nick != self._irc.nick:
            self._ensure_pm_tab(nick)
            self._focus_pm_tab(nick)

    def _insert_mention(self, nick):
        current = self.irc_entry.get_text()
        prefix = " @" if current and not current.endswith(" ") else "@"
        self.irc_entry.set_text(f"{current}{prefix}{nick} ")
        self.irc_entry.set_position(len(self.irc_entry.get_text()))
        self.irc_entry.grab_focus()

    def _request_whois(self, nick):
        if self._irc and self._irc.connected:
            self._irc.send_whois(nick)
            self._chat_sys(self.channel_buffer, f"Requesting WHOIS for {nick}...")

    def _copy_nick(self, nick):
        clipboard = Gtk.Clipboard.get_default(self.get_display())
        clipboard.set_text(nick, -1)

    def _kick_user(self, nick):
        if self._irc and self._irc.connected:
            self._irc._send(f"KICK {self._irc.channel} {nick} :Removed by admin")
            self._chat_sys(self.channel_buffer, f"Kicked {nick} from channel.")

    def _show_whois(self, info):
        nick = info.get("nick", "?")
        lines = [f"\u2550\u2550 WHOIS: {nick} \u2550\u2550"]
        if "user" in info and "host" in info:
            lines.append(f"  Host: {info['user']}@{info['host']}")
        if "realname" in info:
            lines.append(f"  Name: {info['realname']}")
        if "server" in info:
            lines.append(f"  Server: {info['server']}")
        if "channels" in info:
            lines.append(f"  Channels: {info['channels']}")
        if "idle_seconds" in info:
            idle_m = info["idle_seconds"] // 60
            lines.append(f"  Idle: {idle_m}m")
        if "signon_time" in info:
            try:
                signon = datetime.fromtimestamp(info["signon_time"]).strftime("%Y-%m-%d %H:%M")
                lines.append(f"  Signon: {signon}")
            except (OSError, ValueError):
                pass
        lines.append("\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550")

        for line in lines:
            self._chat_sys(self.channel_buffer, line)

    def _ensure_pm_tab(self, nick):
        if nick in self._pm_tabs:
            return

        page = self._make_chat_page()

        tab_box = Gtk.Box(spacing=4)
        color = _nick_color(nick)
        tab_label = Gtk.Label()
        tab_label.set_markup(f"<span foreground='{color}'>\u25cf</span> {nick}")

        close_btn = Gtk.Button()
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.set_size_request(20, 20)
        close_img = Gtk.Label(label="\u2715")
        close_img.get_style_context().add_class("text-muted")
        close_btn.add(close_img)
        close_btn.connect("clicked", lambda w: self._close_pm_tab(nick))

        tab_box.pack_start(tab_label, False, False, 0)
        tab_box.pack_start(close_btn, False, False, 0)
        tab_box.show_all()

        idx = self.chat_notebook.append_page(page["box"], tab_box)
        page["box"].show_all()

        self._pm_tabs[nick] = {
            "buffer": page["buffer"],
            "view": page["view"],
            "scroll": page["scroll"],
            "box": page["box"],
            "page_index": idx,
        }

        self._chat_sys(page["buffer"], f"Private conversation with {nick}")

    def _close_pm_tab(self, nick):
        if nick not in self._pm_tabs:
            return
        page_box = self._pm_tabs[nick]["box"]
        page_num = self.chat_notebook.page_num(page_box)
        if page_num >= 0:
            self.chat_notebook.remove_page(page_num)
        del self._pm_tabs[nick]

    def _focus_pm_tab(self, nick):
        if nick not in self._pm_tabs:
            return
        page_box = self._pm_tabs[nick]["box"]
        page_num = self.chat_notebook.page_num(page_box)
        if page_num >= 0:
            self.chat_notebook.set_current_page(page_num)
        self.irc_entry.grab_focus()

    def _get_pm_nick_for_page(self, page_index):
        page_widget = self.chat_notebook.get_nth_page(page_index)
        for nick, tab_info in self._pm_tabs.items():
            if tab_info["box"] is page_widget:
                return nick
        return None

    def _handle_pm_incoming(self, nick, msg):
        self._ensure_pm_tab(nick)
        buf = self._pm_tabs[nick]["buffer"]
        self._chat_msg(buf, nick, msg, is_self=False)

        current_page = self.chat_notebook.get_current_page()
        pm_page = self.chat_notebook.page_num(self._pm_tabs[nick]["box"])
        if current_page != pm_page:
            tab_widget = self.chat_notebook.get_tab_label(self._pm_tabs[nick]["box"])
            if tab_widget:
                for child in tab_widget.get_children():
                    if isinstance(child, Gtk.Label) and nick in (child.get_text() or ""):
                        child.set_markup(f"<span foreground='#fbbf24'><b>\u25cf {nick} \u2709</b></span>")
                        break

    def _chat_sys(self, buf, msg):
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")
        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
        end = buf.get_end_iter()
        buf.insert_with_tags_by_name(end, f"\u2699 {msg}\n", "system")
        self._autoscroll(buf)

    def _chat_msg(self, buf, nick, msg, is_self=False):
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")

        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
        end = buf.get_end_iter()

        color = _nick_color(nick)
        tag_name = f"nick_{color.replace('#', '')}"
        if is_self:
            buf.insert_with_tags_by_name(end, f"{nick}: ", "self_nick")
        else:
            buf.insert_with_tags_by_name(end, f"{nick}: ", tag_name)

        end = buf.get_end_iter()
        my_nick = self._irc.nick if self._irc else ""
        if my_nick and f"@{my_nick}" in msg:
            parts = msg.split(f"@{my_nick}")
            for i, part in enumerate(parts):
                end = buf.get_end_iter()
                buf.insert(end, part)
                if i < len(parts) - 1:
                    end = buf.get_end_iter()
                    buf.insert_with_tags_by_name(end, f"@{my_nick}", "mention")
            end = buf.get_end_iter()
            buf.insert(end, "\n")
        else:
            buf.insert(end, f"{msg}\n")

        self._autoscroll(buf)

    def _chat_action(self, buf, nick, action_text):
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")
        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
        end = buf.get_end_iter()
        buf.insert_with_tags_by_name(end, f"* {nick} {action_text}\n", "action")
        self._autoscroll(buf)

    def _autoscroll(self, buf):
        for nick, tab in self._pm_tabs.items():
            if tab["buffer"] is buf:
                adj = tab["scroll"].get_vadjustment()
                adj.set_value(adj.get_upper() - adj.get_page_size())
                return
        if buf is self.channel_buffer:
            adj = self.channel_scroll.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())

    # ═══════════════════════════════════════════════
    # TAB 2: ENCRYPTED TICKETS
    # ═══════════════════════════════════════════════

    def _build_ticket_tab(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)

        conn_frame = Gtk.Frame(label="Operator Identity")
        conn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        conn_box.set_margin_start(10)
        conn_box.set_margin_end(10)
        conn_box.set_margin_top(10)
        conn_box.set_margin_bottom(10)

        if self._identity.is_admin:
            lbl_info = Gtk.Label(
                label="You are the ADMIN NODE. Incoming tickets are decrypted here."
            )
        else:
            lbl_info = Gtk.Label(
                label="Send encrypted tickets to the developer. RSA-OAEP encrypted \u2014 only the admin can decrypt."
            )
        lbl_info.set_line_wrap(True)
        conn_box.pack_start(lbl_info, False, False, 0)

        row1 = Gtk.Box(spacing=10)
        row1.pack_start(Gtk.Label(label="Handle:"), False, False, 0)
        self.entry_handle = Gtk.Entry()
        if self._identity.is_admin:
            self.entry_handle.set_text(self._identity.handle)
            self.entry_handle.set_sensitive(False)
        else:
            self.entry_handle.set_placeholder_text("Choose your operator alias...")
        row1.pack_start(self.entry_handle, True, True, 0)
        conn_box.pack_start(row1, False, False, 0)

        conn_frame.add(conn_box)
        vbox.pack_start(conn_frame, False, False, 0)

        chat_frame = Gtk.Frame(label="Encrypted Ticket System")
        chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        chat_box.set_margin_start(10)
        chat_box.set_margin_end(10)
        chat_box.set_margin_top(10)
        chat_box.set_margin_bottom(10)

        self.ticket_buffer = Gtk.TextBuffer()
        output_view = Gtk.TextView(buffer=self.ticket_buffer)
        output_view.set_editable(False)
        output_view.set_monospace(True)
        output_view.get_style_context().add_class("terminal-view")
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_min_content_height(350)
        scroll.add(output_view)
        chat_box.pack_start(scroll, True, True, 0)

        in_row = Gtk.Box(spacing=10)
        self.entry_msg = Gtk.Entry()
        self.entry_msg.set_placeholder_text("Type message... (encrypted before save)")
        self.entry_msg.set_hexpand(True)
        self.entry_msg.connect("activate", self._on_ticket_send)
        in_row.pack_start(self.entry_msg, True, True, 0)

        btn_send = self._mkbtn("Transmit", self._on_ticket_send, "suggested-action")
        in_row.pack_start(btn_send, False, False, 0)
        chat_box.pack_start(in_row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_export = Gtk.Button(label="\U0001f4cb Copy Last Ticket")
        btn_export.connect("clicked", self._on_copy_ticket)
        btn_row.pack_start(btn_export, False, False, 0)

        btn_load = Gtk.Button(label="\U0001f4c2 Load Ticket File")
        btn_load.connect("clicked", self._on_load_ticket)
        btn_row.pack_start(btn_load, False, False, 0)

        if self._identity.is_admin:
            btn_decrypt = Gtk.Button(label="\U0001f5dd Decrypt Loaded Ticket")
            btn_decrypt.get_style_context().add_class("danger-btn")
            btn_decrypt.connect("clicked", self._on_decrypt_ticket)
            btn_row.pack_start(btn_decrypt, False, False, 0)

        chat_box.pack_start(btn_row, False, False, 5)

        chat_frame.add(chat_box)
        vbox.pack_start(chat_frame, True, True, 0)

        self._last_ticket_b64 = None
        self._loaded_ticket_b64 = None

        self._ticket_sys("System initialized. All messages are end-to-end encrypted.")
        self._ticket_sys(
            f"Role: {self._identity.role.upper()} | Fingerprint: {self._identity.pubkey_fingerprint[:16]}..."
        )
        self._load_ticket_history()

        return vbox

    def _ticket_sys(self, msg):
        end = self.ticket_buffer.get_end_iter()
        self.ticket_buffer.insert(end, f"[SYSTEM] {msg}\n")

    def _ticket_msg(self, handle, msg):
        end = self.ticket_buffer.get_end_iter()
        self.ticket_buffer.insert(end, f"[{handle}] {msg}\n")

    def _on_ticket_send(self, widget):
        handle = self.entry_handle.get_text().strip()
        msg = self.entry_msg.get_text().strip()

        if not handle:
            self._ticket_sys("ERROR: Set your operator handle first.")
            return
        if not msg:
            return

        self._ticket_msg(handle, msg)
        self.entry_msg.set_text("")
        threading.Thread(
            target=self._encrypt_and_save, args=(handle, msg), daemon=True
        ).start()

    def _encrypt_and_save(self, handle, msg):
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes, serialization

        pub_key_path = os.path.join(
            str(self._config.project_root), "shadowcypher", "core", "admin_public.pem"
        )

        if not os.path.exists(pub_key_path):
            GLib.idle_add(self._ticket_sys, "CRITICAL: Admin public key not found.")
            return

        try:
            with open(pub_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read())

            ciphertext = public_key.encrypt(
                msg.encode("utf-8"),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            b64_cipher = base64.b64encode(ciphertext).decode()
            self._last_ticket_b64 = b64_cipher

            ticket = {
                "handle": handle,
                "timestamp": datetime.now().isoformat(),
                "encrypted_message": b64_cipher,
                "role": self._identity.role,
            }

            ts = int(time.time())
            ticket_path = self._tickets_dir / f"ticket_{ts}.json"
            with open(ticket_path, "w") as f:
                json.dump(ticket, f, indent=2)

            GLib.idle_add(self._ticket_sys, f"Ticket saved: {ticket_path.name}")
            GLib.idle_add(self._ticket_sys, f"Cipher: {b64_cipher[:50]}...")

        except Exception as e:
            GLib.idle_add(self._ticket_sys, f"Encryption failed: {e}")

    def _on_copy_ticket(self, btn):
        if not self._last_ticket_b64:
            self._ticket_sys("No ticket to copy. Send a message first.")
            return
        clipboard = Gtk.Clipboard.get_default(self.get_display())
        clipboard.set_text(self._last_ticket_b64, -1)
        self._ticket_sys("Encrypted ticket copied to clipboard.")

    def _on_load_ticket(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="Load Encrypted Ticket",
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        filt = Gtk.FileFilter()
        filt.set_name("Ticket files")
        filt.add_pattern("ticket_*.json")
        filt.add_pattern("*.json")
        dialog.add_filter(filt)
        dialog.set_current_folder(str(self._tickets_dir))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            try:
                with open(path, "r") as f:
                    ticket = json.load(f)
                handle = ticket.get("handle", "UNKNOWN")
                ts = ticket.get("timestamp", "?")
                self._loaded_ticket_b64 = ticket.get("encrypted_message", "")
                self._ticket_sys(f"Loaded ticket from {handle} ({ts})")
                self._ticket_sys(f"Cipher: {self._loaded_ticket_b64[:50]}...")
            except Exception as e:
                self._ticket_sys(f"Failed to load ticket: {e}")
        dialog.destroy()

    def _on_decrypt_ticket(self, btn):
        if not self._loaded_ticket_b64:
            self._ticket_sys("Load a ticket file first.")
            return

        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes, serialization

        priv_path = os.path.join(str(self._config.project_root), "admin_private.pem")
        if not os.path.exists(priv_path):
            self._ticket_sys("DENIED: Admin private key not found on this system.")
            return

        try:
            with open(priv_path, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(), password=None
                )

            ciphertext = base64.b64decode(self._loaded_ticket_b64)
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            self._ticket_sys("\u2550\u2550\u2550\u2550\u2550\u2550 DECRYPTED \u2550\u2550\u2550\u2550\u2550\u2550")
            self._ticket_msg("\U0001f513 PLAINTEXT", plaintext.decode("utf-8"))
            self._ticket_sys("\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550")
        except Exception as e:
            self._ticket_sys(f"Decryption failed: {e}")

    def _load_ticket_history(self):
        tickets = sorted(self._tickets_dir.glob("ticket_*.json"))
        if not tickets:
            return
        self._ticket_sys(f"Found {len(tickets)} ticket(s) in archive.")
        for tp in tickets[-5:]:
            try:
                with open(tp, "r") as f:
                    t = json.load(f)
                handle = t.get("handle", "?")
                ts = t.get("timestamp", "?")
                role = t.get("role", "operator")
                self._ticket_sys(f"  [{role.upper()}] {handle} @ {ts}")
            except Exception:
                pass

    @staticmethod
    def _mkbtn(label, handler, style=None):
        btn = Gtk.Button(label=label)
        if style:
            btn.get_style_context().add_class(style)
        btn.connect("clicked", handler)
        return btn

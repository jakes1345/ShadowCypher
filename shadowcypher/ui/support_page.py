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
from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import TacticalTerminal, DataPod, TacticalHeader
from shadowcypher.core.config import config
from shadowcypher.core.bus import bus


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
        self._typing_timers = {} # nick -> GLib source id
        self._last_typing_sent = 0
        
        # Sovereign Internal State
        self._sov_connected = False
        self._sov_users = []

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.pack_start(self.notebook, True, True, 0)

        # 1. IRC PROTOCOL TAB
        irc_box = self._build_irc_tab()
        self.notebook.append_page(irc_box, Gtk.Label(label="\U0001f310 IRC_PROTOCOL"))

        # 2. SOVEREIGN WAR-ROOM TAB (Xat-style Custom Hub)
        sov_box = self._build_sovereign_tab()
        self.notebook.append_page(sov_box, Gtk.Label(label="\U0001f6e1 SOVEREIGN_HUB"))

        self.notebook.append_page(self._build_ticket_tab(), Gtk.Label(label="\U0001f512 Encrypted Tickets"))
        self.notebook.append_page(self._build_forensic_tab(), Gtk.Label(label="\U0001f6e1 Forensic Registry"))

        # 3. Sovereign Integration Hub
        bus.subscribe("sovereign_in", self._handle_sov_packet)

    def _build_sovereign_tab(self):
        """Discord-style High-Engagement Coordination Hub."""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        # 1. Channel Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        sidebar.get_style_context().add_class("channel-sidebar")
        sidebar.set_size_request(160, -1)
        
        sidebar_lbl = Gtk.Label()
        sidebar_lbl.set_markup("<span weight='bold' size='small' color='#64748b'>OPERATIONAL_CHANNELS</span>")
        sidebar_lbl.set_margin_top(15)
        sidebar.pack_start(sidebar_lbl, False, False, 10)
        
        self.sov_channels_list = Gtk.ListBox()
        self.sov_channels_list.get_style_context().add_class("user-list")
        self.sov_channels_list.connect("row-activated", self._on_chan_switch)
        
        for c in ["#general", "#intel", "#missions", "#chaos"]:
            row = Gtk.ListBoxRow()
            row.set_name(c)
            row.get_style_context().add_class("channel-row")
            lbl = Gtk.Label(label=c, xalign=0)
            row.add(lbl)
            self.sov_channels_list.add(row)
        
        sidebar.pack_start(self.sov_channels_list, True, True, 0)
        hbox.pack_start(sidebar, False, False, 0)

        # 2. Main Center (Chat)
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_vbox.set_margin_start(15)
        main_vbox.set_margin_end(15)
        main_vbox.set_margin_top(15)
        
        header = Gtk.Box(spacing=10)
        self.sov_channel_lbl = Gtk.Label()
        self.sov_channel_lbl.set_markup("<span size='large' weight='800' color='#00d4ff'>#general</span>")
        header.pack_start(self.sov_channel_lbl, False, False, 0)
        
        self.sov_status = Gtk.Label(label="HUB_ENCRYPTED")
        self.sov_status.get_style_context().add_class("text-muted")
        header.pack_end(self.sov_status, False, False, 0)
        main_vbox.pack_start(header, False, False, 0)

        self.sov_terminal = TacticalTerminal(height=500)
        main_vbox.pack_start(self.sov_terminal, True, True, 0)

        # Input
        sov_entry_box = Gtk.Box(spacing=10)
        self.sov_entry = Gtk.Entry()
        self.sov_entry.set_placeholder_text("Broadcast to Sovereign Hub...")
        self.sov_entry.connect("activate", self._on_sov_send)
        sov_entry_box.pack_start(self.sov_entry, True, True, 10)
        
        main_vbox.pack_start(sov_entry_box, False, False, 10)
        hbox.pack_start(main_vbox, True, True, 0)

        # 3. User List (Dominion)
        user_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        user_vbox.set_size_request(200, -1)
        user_vbox.get_style_context().add_class("card")
        
        user_lbl = Gtk.Label()
        user_lbl.set_markup("<span weight='bold' size='small' color='#64748b'>DOMINIONS</span>")
        user_vbox.pack_start(user_lbl, False, False, 5)
        
        self.sov_user_list = Gtk.ListBox()
        user_scroll = Gtk.ScrolledWindow()
        user_scroll.add(self.sov_user_list)
        user_vbox.pack_start(user_scroll, True, True, 0)

        # Power Persistence (X-style)
        pwr_row = Gtk.Box(homogeneous=True, spacing=2)
        for pwr, cls in [("GOLD", "power-gold"), ("HACKER", "power-hacker"), ("MOD", "power-mod")]:
            btn = Gtk.Button(label=pwr)
            btn.get_style_context().add_class(cls)
            btn.connect("clicked", lambda b, p=pwr: self._on_sov_set_power(p))
            pwr_row.pack_start(btn, True, True, 0)
        user_vbox.pack_end(pwr_row, False, False, 5)

        hbox.pack_start(user_vbox, False, False, 0)
        return hbox

    def _build_forensic_tab(self):
        """High-density operational view of global threats and unmasked culprits."""
        from shadowcypher.core.forensics import registry
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(15)
        vbox.set_margin_bottom(15)
        vbox.set_margin_start(15)
        vbox.set_margin_end(15)
        
        header = Gtk.Label()
        header.set_markup("<span size='large' weight='bold' foreground='#00ff9d'>[GLOBAL_THREAT_REGISTRY]</span>")
        header.set_halign(Gtk.Align.START)
        vbox.pack_start(header, False, False, 0)
        
        # Threat Table
        self.threat_store = Gtk.ListStore(str, str, str, str, str) # ID, Handle, Hostmask, Risk, Status
        self.threat_tree = Gtk.TreeView(model=self.threat_store)
        self.threat_tree.get_style_context().add_class("terminal-view")
        
        cols = ["ID", "HANDLE", "HOSTMASK", "RISK", "STATUS"]
        for i, col_title in enumerate(cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_resizable(True)
            self.threat_tree.append_column(column)
            
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.threat_tree)
        vbox.pack_start(scroll, True, True, 0)
        
        btn_box = Gtk.Box(spacing=10)
        btn_refresh = Gtk.Button(label="\u21bb Refresh Registry")
        btn_refresh.connect("clicked", lambda w: self._refresh_forensics())
        btn_box.pack_start(btn_refresh, False, False, 0)
        
        vbox.pack_start(btn_box, False, False, 0)
        
        # Auto-refresh
        GLib.timeout_add(2000, self._refresh_forensics)
        return vbox

    def _refresh_forensics(self):
        """Sync UI with Global Forensic Memory."""
        from shadowcypher.core.forensics import registry
        self.threat_store.clear()
        for threat in registry.get_all_threats():
            self.threat_store.append([
                threat.get("id", "UNK"),
                threat.get("handle", "UNK"),
                threat.get("hostmask", "UNK"),
                threat.get("risk_level", "MED"),
                threat.get("status", "ACTIVE")
            ])
        return True

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

        # Tactical Tip
        tip = Gtk.Label()
        tip.set_markup("<span size='small' color='#10b981'>\u24d8 TIP: Mention 'Sentinel' or type <b>!help</b> to engage AI swarm.</span>")
        tip.set_halign(Gtk.Align.START)
        vbox.pack_start(tip, False, False, 0)

        # Topic bar
        self.topic_bar = Gtk.Label()
        self.topic_bar.set_markup("<span color='#64748b' size='small'>No topic set</span>")
        self.topic_bar.set_halign(Gtk.Align.START)
        self.topic_bar.set_ellipsize(Pango.EllipsizeMode.END)
        self.topic_bar.set_selectable(True)
        self.topic_bar.set_margin_start(6)
        self.topic_bar.set_margin_top(2)
        self.topic_bar.set_margin_bottom(2)
        vbox.pack_start(self.topic_bar, False, False, 0)

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
        self.irc_entry.connect("changed", self._on_irc_entry_changed)
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

        # SOVEREIGN_SAFETY_PROTOCOL: Prevent IRC socket crashes against WebSocket hub
        if server in ["127.0.0.1", "localhost"] and port == 8888:
            self._chat_sys(self.channel_buffer, "\u26a0\ufe0f [CONFLICT] Port 8888 is the internal SOVEREIGN_HUB (WebSocket).")
            self._chat_sys(self.channel_buffer, "[INFO] Standard IRC Protocol is incompatible with this port.")
            self._chat_sys(self.channel_buffer, "[ACTION] Switch to the 'SOVEREIGN_HUB' tab for internal coordination.")
            GLib.idle_add(self.irc_status.set_text, "DISCONNECTED: Port Conflict (Use Sovereign Hub)")
            return

        if self._irc:
            self._irc.disconnect()

        self._config.set("irc", "server", server)
        self._config.set("irc", "port", port)
        self._config.set("irc", "channel", channel)
        self._config.set("irc", "use_ssl", use_ssl)

        self._irc = IRCClient(server=server, port=port, channel=channel, nick=nick, use_ssl=use_ssl, auto_reconnect=True)

        self._irc.on_message(self._cb_message)
        self._irc.on_system(self._cb_system)
        self._irc.on_connect(self._cb_connect)
        self._irc.on_userlist(self._cb_userlist)
        self._irc.on_whois(self._cb_whois)
        self._irc.on_private(self._cb_private)
        self._irc.on_join(lambda nick: GLib.idle_add(self._chat_sys, self.channel_buffer, f"\u2192 {nick} joined"))
        self._irc.on_part(lambda nick: GLib.idle_add(self._chat_sys, self.channel_buffer, f"\u2190 {nick} left"))
        self._irc.on_topic(self._cb_topic)
        self._irc.on_nick_change(self._cb_nick_change)
        self._irc.on_kick(self._cb_kick)
        self._irc.on_typing(self._cb_typing)
        self._irc.on_disconnect(self._cb_disconnect)

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

    def _cb_message(self, nick, target, msg, source=None):
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

    def _cb_private(self, nick, msg, source=None):
        GLib.idle_add(self._handle_pm_incoming, nick, msg)

    def _update_userlist(self, names):
        self._users = sorted(names, key=str.lower)
        for child in self.user_listbox.get_children():
            self.user_listbox.remove(child)

        for name in self._users:
            row = Gtk.ListBoxRow()
            row.set_name(name)
            row.get_style_context().add_class("irc-user-row")
            
            hbox = Gtk.Box(spacing=6)
            hbox.set_margin_start(4)
            hbox.set_margin_end(4)
            hbox.set_margin_top(0)
            hbox.set_margin_bottom(0)

            color = _nick_color(name)

            # High-density color indicator
            id_bar = Gtk.Box()
            id_bar.set_size_request(2, -1)
            rgba = Gdk.RGBA()
            rgba.parse(color)
            id_bar.override_background_color(Gtk.StateFlags.NORMAL, rgba)
            hbox.pack_start(id_bar, False, False, 0)

            # Micro-Avatar (14px font)
            initial = name[0].upper() if name else "?"
            avatar_lbl = Gtk.Label()
            avatar_lbl.set_markup(f"<span foreground='{color}' font_desc='8' weight='bold'>{initial}</span>")
            avatar_lbl.set_size_request(14, 14)
            hbox.pack_start(avatar_lbl, False, False, 0)

            # Mode prefix + nick
            prefix = self._irc.get_user_prefix(name) if self._irc else ""
            display_name = f"{prefix}{name}" if prefix else name
            lbl = Gtk.Label(label=display_name, xalign=0)
            lbl.get_style_context().add_class("irc-user-nick")
            
            # Bot-specific branding
            if name == "ShadowSentinel":
                lbl.get_style_context().add_class("irc-sentinel-nick")
                
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            hbox.pack_start(lbl, True, True, 0)

            if name in self._pm_tabs:
                pm_indicator = Gtk.Label()
                pm_indicator.set_markup("<span foreground='#fbbf24' font_desc='8'>\u2709</span>")
                hbox.pack_end(pm_indicator, False, False, 0)

            row.add(hbox)
            self.user_listbox.add(row)

        self.user_listbox.show_all()
        self.user_count_lbl.set_text(f"{len(self._users)} users")

    def _cb_typing(self, nick, status):
        """Typing signal from IRC."""
        GLib.idle_add(self._handle_typing_change, nick, status)

    def _handle_typing_change(self, nick, status):
        """Update UI avatar with typing animation."""
        if nick in self._typing_timers:
            GLib.source_remove(self._typing_timers[nick])
            del self._typing_timers[nick]

        # Find row and avatar
        found_avatar = None
        for row in self.user_listbox.get_children():
            if row.get_name() == nick:
                hbox = row.get_child()
                # avatar_lbl is the 2nd pack item (index 1)
                found_avatar = hbox.get_children()[1]
                break
        
        if not found_avatar: return

        if status == "active":
            found_avatar.get_style_context().add_class("typing-avatar")
            # Clear after 6 seconds of silence
            self._typing_timers[nick] = GLib.timeout_add_seconds(6, self._handle_typing_change, nick, "done")
        else:
            found_avatar.get_style_context().remove_class("typing-avatar")

    def _on_irc_entry_changed(self, entry):
        """Send local typing status."""
        if not self._irc or not self._irc.connected: return
        now = time.time()
        # Rate limit typing signals to 1 per 3 seconds
        if now - self._last_typing_sent > 3:
            text = entry.get_text().strip()
            if text:
                self._irc.send_typing(self._irc.channel, "active")
                self._last_typing_sent = now

    def _on_chan_switch(self, listbox, row):
        chan = row.get_name()
        # Update UI state
        self.sov_channel_lbl.set_markup(f"<span size='large' weight='800' color='#00d4ff'>{chan}</span>")
        for r in listbox.get_children():
            r.get_style_context().remove_class("channel-active")
        row.get_style_context().add_class("channel-active")
        
        # Notify server
        self._sov_broadcast({"type": "switch_channel", "channel": chan})
        self._chat_sys(self.sov_terminal.text_view.get_buffer(), f"CHANNEL_SHIFT: Switched to {chan}")

    def _on_sov_send(self, widget):
        msg = self.sov_entry.get_text().strip()
        if not msg: return
        self._sov_broadcast({"type": "chat", "text": msg})
        self.sov_entry.set_text("")
        
    def _on_sov_set_power(self, power):
        self._sov_broadcast({"type": "set_metadata", "field": "power", "value": power.lower()})
        self._chat_sys(self.sov_terminal.text_view.get_buffer(), f"POWER_UPDATE: Attempting shift to {power}")

    def _sov_broadcast(self, packet):
        """Internal dispatch to the Sovereign Hub."""
        # For this implementation, we bridge to the SovereignServer via the Bus
        # but also simulate the network response for immediate feedback.
        from shadowcypher.core.bus import bus
        packet["nick"] = self._irc.nick if self._irc else "Operator"
        bus.publish("sovereign_out", packet)
        
    def _handle_sov_packet(self, packet):
        """Process incoming Sovereign data (Xat-style)."""
        GLib.idle_add(self._process_sov_ui, packet)

    def _process_sov_ui(self, packet):
        ptype = packet.get("type")
        nick = packet.get("nick", "Unknown")
        buf = self.sov_terminal.text_view.get_buffer()
        
        if ptype == "chat":
            power = packet.get("power", "default")
            power_cls = f"power-{power}"
            text = packet.get("text", "")
            
            end = buf.get_end_iter()
            ts = time.strftime("%H:%M:%S")
            buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
            
            # Nick with Power styling
            end = buf.get_end_iter()
            nick_tag = f"nick_{_nick_color(nick).replace('#', '')}"
            buf.insert_with_tags_by_name(end, f"{nick}", nick_tag)
            
            if power != "default":
                end = buf.get_end_iter()
                buf.insert_with_tags_by_name(end, f" [{power.upper()}]", power_cls)
            
            end = buf.get_end_iter()
            buf.insert(end, f": {text}\n")
            
        elif ptype == "user_sync":
            self._sov_users = packet.get("users", [])
            self._update_sov_userlist()

    def _update_sov_userlist(self):
        for child in self.sov_user_list.get_children():
            self.sov_user_list.remove(child)
            
        for u in self._sov_users:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("irc-user-row")
            hbox = Gtk.Box(spacing=8)
            hbox.set_margin_start(5)
            
            # Xat-style Avatar or Power Dot
            dot = Gtk.Label()
            color = "#00ff9d" # default sovereign green
            if u["power"] == "gold": color = "#fbbf24"
            elif u["power"] == "mod": color = "#8b5cf6"
            
            dot.set_markup(f"<span color='{color}' font_desc='10'>\u2b24</span>")
            hbox.pack_start(dot, False, False, 0)
            
            lbl = Gtk.Label(label=u["nick"], xalign=0)
            lbl.get_style_context().add_class(f"power-{u['power']}")
            hbox.pack_start(lbl, True, True, 0)

            # Level Badge
            lvl = u.get("level", 1)
            badge = Gtk.Label()
            badge.set_markup(f"<span class='xp-badge'>Lvl {lvl}</span>")
            hbox.pack_end(badge, False, False, 5)
            
            row.add(hbox)
            self.sov_user_list.add(row)
        self.sov_user_list.show_all()

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
            self._irc.kick_user(nick, "Removed by admin")
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

        # Xat-style minimal separator
        end = buf.get_end_iter()
        buf.insert_with_tags_by_name(end, "\u2500" * 15 + "\n", "timestamp")

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

    # ─── IRC v2 Event Callbacks ──────────────────────────────────

    def _cb_topic(self, topic, setter):
        GLib.idle_add(self._update_topic, topic, setter)

    def _update_topic(self, topic, setter):
        if topic:
            escaped = GLib.markup_escape_text(topic)
            prefix = f"{setter} set " if setter else ""
            self.topic_bar.set_markup(
                f"<span color='#94a3b8' size='small'><b>Topic:</b> {escaped}</span>"
            )
        else:
            self.topic_bar.set_markup(
                "<span color='#64748b' size='small'>No topic set</span>"
            )

    def _cb_nick_change(self, old_nick, new_nick):
        GLib.idle_add(self._handle_nick_change, old_nick, new_nick)

    def _handle_nick_change(self, old_nick, new_nick):
        self._chat_sys(self.channel_buffer, f"{old_nick} \u2192 {new_nick}")
        # Migrate PM tab if one is open for the old nick
        if old_nick in self._pm_tabs:
            tab_data = self._pm_tabs.pop(old_nick)
            self._pm_tabs[new_nick] = tab_data
            page_box = tab_data["box"]
            tab_widget = self.chat_notebook.get_tab_label(page_box)
            if tab_widget:
                for child in tab_widget.get_children():
                    if isinstance(child, Gtk.Label):
                        color = _nick_color(new_nick)
                        child.set_markup(
                            f"<span foreground='{color}'>\u25cf</span> {new_nick}"
                        )
                        break
            self._chat_sys(
                tab_data["buffer"],
                f"{old_nick} is now known as {new_nick}"
            )

    def _cb_kick(self, kicker, kicked, reason):
        GLib.idle_add(
            self._chat_sys, self.channel_buffer,
            f"\u26d4 {kicked} was kicked by {kicker} ({reason})"
        )

    def _cb_disconnect(self):
        GLib.idle_add(self._handle_disconnect)

    def _handle_disconnect(self):
        if self._irc and self._irc.auto_reconnect and self._irc._running:
            self.irc_status.set_text("DISCONNECTED \u2014 Reconnecting...")
        else:
            self.irc_status.set_text("DISCONNECTED")
        self.irc_entry.set_sensitive(False)
        self.irc_send_btn.set_sensitive(False)

    # \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
    # TAB 2: ENCRYPTED TICKETS
    # \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

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
            saved_handle = self._identity.handle
            self.entry_handle.set_text(saved_handle)
            self.entry_handle.set_placeholder_text("Choose your operator alias...")
            self.entry_handle.connect("changed", self._on_handle_changed)
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

    def _on_handle_changed(self, entry):
        """Save the handle to config as the user types (stabilized)."""
        new_handle = entry.get_text().strip()
        self._identity.set_handle(new_handle)

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

        # Admin authorization gate — only authorized identities can decrypt
        if not self._identity.is_admin:
            self._ticket_sys("\u26d4 ACCESS_DENIED: Admin clearance required for decryption.")
            self._ticket_sys(f"Current identity: {self._identity.handle} ({self._identity.role})")
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

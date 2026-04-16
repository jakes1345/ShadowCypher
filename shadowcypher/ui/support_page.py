"""Support & Communications — Encrypted tickets + Live IRC with PM tabs."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango
import threading
import os
import json
import time
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from shadowcypher.core.logger import logger
from shadowcypher.core.irc import IRCClient
from shadowcypher.core.sovereign import SovereignClient
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
        
        # Sovereign Internal State (Ergo IRC via IRCClient)
        self._sov_irc: SovereignClient | None = None
        self._sov_connected = False
        self._sov_loop_thread = None
        self._sov_users = []          # list of nicks in current channel
        self._sov_nick = "Operator"
        self._sov_channel = "#general"
        self._sov_active_pm = None     # nick if viewing a PM, None if channel

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.pack_start(self.notebook, True, True, 0)

        # 1. SOVEREIGN WAR-ROOM (Main IRC Hub)
        sov_box = self._build_sovereign_tab()
        self.notebook.append_page(sov_box, Gtk.Label(label="\U0001f6e1 SOVEREIGN_HUB"))

        self.notebook.append_page(self._build_ticket_tab(), Gtk.Label(label="\U0001f512 Encrypted Tickets"))
        self.notebook.append_page(self._build_forensic_tab(), Gtk.Label(label="\U0001f6e1 Forensic Registry"))

        # 3. Sovereign Integration — start server + auto-connect
        self._start_sovereign_server()
        # Auto-connect after a short delay (let server boot)
        GLib.timeout_add(1500, self._sov_auto_connect)

    def _build_sovereign_tab(self):
        """Full IRC-style Sovereign Hub with real WebSocket connection."""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # 1. Channel Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        sidebar.get_style_context().add_class("channel-sidebar")
        sidebar.set_size_request(160, -1)

        sidebar_lbl = Gtk.Label()
        sidebar_lbl.set_markup("<span weight='bold' size='small' color='#64748b'>CHANNELS</span>")
        sidebar_lbl.set_margin_top(15)
        sidebar.pack_start(sidebar_lbl, False, False, 10)

        self.sov_channels_list = Gtk.ListBox()
        self.sov_channels_list.get_style_context().add_class("user-list")
        self.sov_channels_list.connect("row-activated", self._on_chan_switch)

        for c in ["#general", "#intel", "#missions", "#chaos", "#dev"]:
            self._add_sidebar_row(c, is_channel=True)

        sidebar.pack_start(self.sov_channels_list, True, True, 0)

        # PM section label
        pm_lbl = Gtk.Label()
        pm_lbl.set_markup("<span weight='bold' size='small' color='#64748b'>PRIVATE</span>")
        pm_lbl.set_margin_top(10)
        sidebar.pack_start(pm_lbl, False, False, 0)

        self.sov_pm_list = Gtk.ListBox()
        self.sov_pm_list.get_style_context().add_class("user-list")
        self.sov_pm_list.connect("row-activated", self._on_pm_tab_switch)
        sidebar.pack_start(self.sov_pm_list, False, False, 0)

        # Connect / Disconnect buttons
        conn_row = Gtk.Box(spacing=4)
        conn_row.set_margin_start(4)
        conn_row.set_margin_end(4)
        conn_row.set_margin_bottom(4)
        self.sov_connect_btn = Gtk.Button(label="Connect")
        self.sov_connect_btn.get_style_context().add_class("suggested-action")
        self.sov_connect_btn.connect("clicked", lambda b: self._sov_connect())
        conn_row.pack_start(self.sov_connect_btn, True, True, 0)
        self.sov_disconnect_btn = Gtk.Button(label="DC")
        self.sov_disconnect_btn.get_style_context().add_class("destructive-action")
        self.sov_disconnect_btn.connect("clicked", lambda b: self._sov_disconnect())
        conn_row.pack_start(self.sov_disconnect_btn, False, False, 0)

        self.sov_crawl_btn = Gtk.Button(label="\U0001f50e Crawl")
        self.sov_crawl_btn.connect("clicked", self._on_crawl_network)
        conn_row.pack_start(self.sov_crawl_btn, False, False, 0)
        
        sidebar.pack_end(conn_row, False, False, 0)

        hbox.pack_start(sidebar, False, False, 0)

        # 2. Main Chat Area
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_vbox.set_margin_start(10)
        main_vbox.set_margin_end(10)
        main_vbox.set_margin_top(10)

        header = Gtk.Box(spacing=10)
        self.sov_channel_lbl = Gtk.Label()
        self.sov_channel_lbl.set_markup("<span size='large' weight='800' color='#00d4ff'>#general</span>")
        header.pack_start(self.sov_channel_lbl, False, False, 0)

        self.sov_topic_lbl = Gtk.Label()
        self.sov_topic_lbl.set_markup("<span color='#64748b' size='small'>Welcome to ShadowCypher Sovereign</span>")
        self.sov_topic_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        header.pack_start(self.sov_topic_lbl, True, True, 8)

        self.sov_status = Gtk.Label(label="DISCONNECTED")
        self.sov_status.get_style_context().add_class("text-muted")
        header.pack_end(self.sov_status, False, False, 0)
        main_vbox.pack_start(header, False, False, 0)

        # Chat display
        self.sov_chat_buf = Gtk.TextBuffer()
        tag_table = self.sov_chat_buf.get_tag_table()
        self.sov_chat_buf.create_tag("system", foreground="#64748b", style=Pango.Style.ITALIC)
        self.sov_chat_buf.create_tag("error", foreground="#f87171", weight=Pango.Weight.BOLD)
        self.sov_chat_buf.create_tag("action", foreground="#a78bfa", style=Pango.Style.ITALIC)
        self.sov_chat_buf.create_tag("timestamp", foreground="#475569")
        self.sov_chat_buf.create_tag("self_nick", foreground="#38bdf8", weight=Pango.Weight.BOLD)
        self.sov_chat_buf.create_tag("motd", foreground="#22d3ee")
        for color in NICK_COLORS:
            safe_name = f"nick_{color.replace('#', '')}"
            if not tag_table.lookup(safe_name):
                self.sov_chat_buf.create_tag(safe_name, foreground=color, weight=Pango.Weight.BOLD)

        self.sov_chat_view = Gtk.TextView(buffer=self.sov_chat_buf)
        self.sov_chat_view.set_editable(False)
        self.sov_chat_view.set_cursor_visible(False)
        self.sov_chat_view.set_monospace(True)
        self.sov_chat_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.sov_chat_view.get_style_context().add_class("terminal-view")

        self.sov_chat_scroll = Gtk.ScrolledWindow()
        self.sov_chat_scroll.set_propagate_natural_width(False)
        self.sov_chat_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.sov_chat_scroll.set_min_content_height(400)
        self.sov_chat_scroll.add(self.sov_chat_view)

        # Paned: channel chat on left, PM panel slides in on right (xat-style)
        self.sov_chat_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.sov_chat_paned.pack1(self.sov_chat_scroll, resize=True, shrink=False)

        # PM panel (hidden by default, slides in with blue glow)
        self.sov_pm_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.sov_pm_panel.set_no_show_all(True)

        # PM header with nick + close button
        pm_header = Gtk.Box(spacing=6)
        pm_header.set_margin_start(8)
        pm_header.set_margin_end(8)
        pm_header.set_margin_top(6)
        self.sov_pm_header_lbl = Gtk.Label()
        self.sov_pm_header_lbl.set_markup("<span color='#60a5fa' weight='bold'>\u2709 Private Chat</span>")
        pm_header.pack_start(self.sov_pm_header_lbl, True, True, 0)
        pm_close = Gtk.Button(label="\u2716")
        pm_close.set_relief(Gtk.ReliefStyle.NONE)
        pm_close.connect("clicked", lambda w: self._close_active_pm())
        pm_header.pack_end(pm_close, False, False, 0)
        self.sov_pm_panel.pack_start(pm_header, False, False, 0)

        # PM chat view
        self.sov_pm_buf = Gtk.TextBuffer()
        self.sov_pm_buf.create_tag("system", foreground="#64748b", style=Pango.Style.ITALIC)
        self.sov_pm_buf.create_tag("timestamp", foreground="#475569")
        self.sov_pm_buf.create_tag("self_nick", foreground="#38bdf8", weight=Pango.Weight.BOLD)
        for color in NICK_COLORS:
            safe = f"nick_{color.replace('#', '')}"
            tag_table = self.sov_pm_buf.get_tag_table()
            if not tag_table.lookup(safe):
                self.sov_pm_buf.create_tag(safe, foreground=color, weight=Pango.Weight.BOLD)

        self.sov_pm_view = Gtk.TextView(buffer=self.sov_pm_buf)
        self.sov_pm_view.set_editable(False)
        self.sov_pm_view.set_cursor_visible(False)
        self.sov_pm_view.set_monospace(True)
        self.sov_pm_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.sov_pm_view.get_style_context().add_class("terminal-view")

        pm_scroll = Gtk.ScrolledWindow()
        pm_scroll.set_propagate_natural_width(False)
        pm_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        pm_scroll.add(self.sov_pm_view)
        self.sov_pm_scroll = pm_scroll
        self.sov_pm_panel.pack_start(pm_scroll, True, True, 0)

        # PM input
        pm_input_box = Gtk.Box(spacing=4)
        pm_input_box.set_margin_start(4)
        pm_input_box.set_margin_end(4)
        pm_input_box.set_margin_bottom(4)
        self.sov_pm_entry = Gtk.Entry()
        self.sov_pm_entry.set_placeholder_text("Private message...")
        self.sov_pm_entry.connect("activate", self._on_sov_pm_send)
        pm_input_box.pack_start(self.sov_pm_entry, True, True, 0)
        pm_send = Gtk.Button(label="Send")
        pm_send.get_style_context().add_class("suggested-action")
        pm_send.connect("clicked", self._on_sov_pm_send)
        pm_input_box.pack_start(pm_send, False, False, 0)
        self.sov_pm_panel.pack_start(pm_input_box, False, False, 0)

        self.sov_chat_paned.pack2(self.sov_pm_panel, resize=True, shrink=True)
        main_vbox.pack_start(self.sov_chat_paned, True, True, 0)

        # Apply blue glow CSS to PM panel
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .pm-glow {
                border-left: 2px solid #3b82f6;
                box-shadow: -4px 0 15px rgba(59, 130, 246, 0.3);
                background: rgba(30, 58, 138, 0.08);
                padding: 4px;
            }
            .pm-unread {
                background: rgba(59, 130, 246, 0.15);
                border-left: 3px solid #60a5fa;
            }
            .pm-unread label {
                color: #60a5fa;
                font-weight: bold;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.sov_pm_panel.get_style_context().add_class("pm-glow")

        # Input
        sov_entry_box = Gtk.Box(spacing=8)
        self.sov_nick_lbl = Gtk.Label()
        self.sov_nick_lbl.set_markup("<span color='#38bdf8' weight='bold'>Operator</span>")
        sov_entry_box.pack_start(self.sov_nick_lbl, False, False, 4)

        self.sov_entry = Gtk.Entry()
        self.sov_entry.set_placeholder_text("Type message or /command...")
        self.sov_entry.connect("activate", self._on_sov_send)
        self.sov_entry.set_sensitive(False)
        sov_entry_box.pack_start(self.sov_entry, True, True, 0)

        sov_send_btn = Gtk.Button(label="Send")
        sov_send_btn.get_style_context().add_class("suggested-action")
        sov_send_btn.connect("clicked", self._on_sov_send)
        sov_entry_box.pack_start(sov_send_btn, False, False, 0)

        main_vbox.pack_start(sov_entry_box, False, False, 8)

        # PM buffers (nick -> TextBuffer) — swap into main chat view
        self._sov_pm_tabs = {}  # nick -> {buf}
        self._sov_channel_buf = self.sov_chat_buf  # save reference to channel buffer

        hbox.pack_start(main_vbox, True, True, 0)

        # 3. User List
        user_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        user_vbox.set_size_request(180, -1)
        user_vbox.get_style_context().add_class("card")

        user_lbl = Gtk.Label()
        user_lbl.set_markup("<span weight='bold' size='small' color='#64748b'>ONLINE</span>")
        user_vbox.pack_start(user_lbl, False, False, 5)

        self.sov_user_count = Gtk.Label(label="0 users")
        self.sov_user_count.get_style_context().add_class("text-muted")
        user_vbox.pack_start(self.sov_user_count, False, False, 0)

        self.sov_user_list = Gtk.ListBox()
        self.sov_user_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sov_user_list.connect("button-press-event", self._on_sov_user_click)
        user_scroll = Gtk.ScrolledWindow()
        user_scroll.set_propagate_natural_width(False)
        user_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        user_scroll.add(self.sov_user_list)
        user_vbox.pack_start(user_scroll, True, True, 0)

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
        scroll.set_propagate_natural_width(False)
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
        user_scroll.set_propagate_natural_width(False)
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

    # ═══════════════════════════════════════════════
    # SOVEREIGN HUB — WebSocket Client & Handlers
    # ═══════════════════════════════════════════════

    def _start_sovereign_server(self):
        """Start the Ergo IRC server via sovereign.sh if not already running."""
        irc_dir = Path(config.project_root) / "irc"
        pidfile = irc_dir / "ergo.pid"
        ergo_bin = irc_dir / "ergo"

        if not ergo_bin.exists():
            logger.warning("sovereign", "Ergo binary not found at %s", ergo_bin)
            return

        # Check if already running
        if pidfile.exists():
            try:
                pid = int(pidfile.read_text().strip())
                os.kill(pid, 0)  # signal 0 = check if alive
                logger.info("sovereign", f"Ergo already running (PID {pid})")
                return
            except (OSError, ValueError):
                pass  # stale pid, start fresh

        script = irc_dir / "sovereign.sh"
        if script.exists():
            def _launch():
                try:
                    subprocess.run(
                        ["bash", str(script), "start"],
                        cwd=str(irc_dir), timeout=15,
                        capture_output=True, text=True,
                    )
                except Exception as e:
                    logger.error("sovereign", f"Failed to start Ergo: {e}")

            threading.Thread(target=_launch, daemon=True).start()
            logger.info("sovereign", "Launching Ergo IRC server...")

    def _sov_auto_connect(self):
        """Auto-connect to Ergo IRC after server has had time to start."""
        if not self._sov_connected:
            self._sov_connect()
        return False  # Don't repeat

    def _sov_connect(self):
        """Connect to the Ergo IRC server via IRCClient."""
        if self._sov_connected or self._sov_irc:
            return

        from shadowcypher.core.identity import identity
        import re as _re
        raw_handle = identity.handle or "Operator"
        # Sanitize for IRC: strip non-alphanumeric, no spaces, max 32 chars
        clean = _re.sub(r'[^A-Za-z0-9_\-\[\]\\`^{}]', '', raw_handle)
        self._sov_nick = clean[:32] if clean else "Operator"

        self._sov_irc = SovereignClient(
            host="127.0.0.1",
            port=8888,
            nick=self._sov_nick
        )

        # Wire up all callbacks (JSON protocol)
        self._sov_irc.on("chat", lambda d: GLib.idle_add(self._sov_on_irc_message, d.get("nick"), d.get("channel"), d.get("text")))
        self._sov_irc.on("sys", lambda d: GLib.idle_add(self._sov_sys, d.get("text")))
        self._sov_irc.on("join", lambda d: GLib.idle_add(self._sov_on_irc_join, d.get("nick")))
        self._sov_irc.on("unmask_report", lambda d: GLib.idle_add(self._on_unmask_result, d))
        self._sov_irc.on("unmask_report_all", lambda d: GLib.idle_add(self._on_unmask_result_all, d))
        self._sov_irc.on("disconnect", lambda d: GLib.idle_add(self._sov_on_disconnect))
        
        # Start connection in background loop
        def run_loop():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._sov_irc.connect())
        
        self._sov_loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._sov_loop_thread.start()
        self._sov_on_connect() # Optimistic state

        self._sov_irc.connect()

    def _sov_disconnect(self):
        """Disconnect from Ergo IRC server."""
        if self._sov_irc:
            self._sov_irc.disconnect("Signing off")
            self._sov_irc = None
        self._sov_on_disconnect()

    def _sov_on_connect(self):
        """Called on GTK thread when IRC connection established."""
        self._sov_connected = True
        if self._sov_irc:
            self._sov_nick = self._sov_irc.nick
        self.sov_status.set_text("CONNECTED")
        self.sov_status.get_style_context().remove_class("text-muted")
        self.sov_entry.set_sensitive(True)
        self.sov_nick_lbl.set_markup(
            f"<span color='#38bdf8' weight='bold'>{GLib.markup_escape_text(self._sov_nick)}</span>"
        )
        self._sov_sys(f"Connected to Sovereign as {self._sov_nick}")

    def _sov_on_disconnect(self):
        """Called on GTK thread when disconnected."""
        self._sov_connected = False
        self.sov_status.set_text("DISCONNECTED")
        self.sov_status.get_style_context().add_class("text-muted")
        self.sov_entry.set_sensitive(False)

    # ── Sovereign IRC Callbacks (fired from IRCClient thread → GTK via GLib.idle_add) ──

    def _sov_on_irc_message(self, nick, channel, msg):
        """Channel message from Ergo."""
        buf = self.sov_chat_buf
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")
        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")

        end = buf.get_end_iter()
        prefix = self._sov_irc.get_user_prefix(nick) if self._sov_irc else ""
        is_self = (nick == self._sov_nick)
        if is_self:
            buf.insert_with_tags_by_name(end, f"{prefix}{nick}", "self_nick")
        else:
            color = _nick_color(nick)
            tag = f"nick_{color.replace('#', '')}"
            buf.insert_with_tags_by_name(end, f"{prefix}{nick}", tag)

        end = buf.get_end_iter()
        buf.insert(end, f": {msg}\n")
        self._sov_autoscroll()

    def _sov_on_irc_private(self, nick, msg):
        """Private message from Ergo — open PM panel and display."""
        was_active = (self._sov_active_pm == nick)
        self._open_sov_pm(nick)
        self._sov_pm_append(nick, msg, target_nick=nick)
        if not was_active:
            # Add unread glow to sidebar row
            for row in self.sov_pm_list.get_children():
                if row.get_name() == nick:
                    row.get_style_context().add_class("pm-unread")
                    break
            self._sov_sys(f"\u2709 PM from {nick}")

    def _sov_on_irc_userlist(self, names):
        """NAMES reply — update the user sidebar."""
        self._sov_users = names
        self._update_sov_userlist()

    def _sov_on_irc_whois(self, info):
        """WHOIS result from Ergo."""
        nick = info.get("nick", "?")
        lines = [f"\u2550\u2550 WHOIS: {nick} \u2550\u2550"]
        if info.get("user"):
            lines.append(f"  User: {info['user']}@{info.get('host', '?')}")
        if info.get("realname"):
            lines.append(f"  Real name: {info['realname']}")
        if info.get("channels"):
            lines.append(f"  Channels: {info['channels']}")
        if info.get("server"):
            lines.append(f"  Server: {info['server']} ({info.get('server_info', '')})")
        if info.get("idle_seconds") is not None:
            lines.append(f"  Idle: {info['idle_seconds']}s")
        lines.append("\u2550" * 40)
        for line in lines:
            self._sov_sys(line)

    def _sov_on_irc_join(self, nick):
        """Someone joined the channel."""
        pass  # on_system already prints it; userlist refresh is triggered by IRCClient

    def _sov_on_irc_part(self, nick):
        """Someone left the channel."""
        pass  # on_system handles it

    def _sov_on_irc_topic(self, topic, setter):
        """Topic changed."""
        escaped = GLib.markup_escape_text(topic) if topic else "No topic set"
        self.sov_topic_lbl.set_markup(f"<span color='#94a3b8' size='small'>{escaped}</span>")

    def _sov_on_irc_nick_change(self, old_nick, new_nick):
        """Someone changed nick."""
        if old_nick == self._sov_nick:
            self._sov_nick = new_nick
            self.sov_nick_lbl.set_markup(
                f"<span color='#38bdf8' weight='bold'>{GLib.markup_escape_text(new_nick)}</span>"
            )

    def _sov_on_irc_kick(self, kicker, kicked, reason):
        """Someone was kicked."""
        pass  # on_system handles display; IRCClient auto-rejoins if we were kicked

    # ── Sovereign Chat Output Helpers ───────────────────────────

    def _sov_sys(self, msg):
        """System message in Sovereign chat."""
        buf = self.sov_chat_buf
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")
        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
        end = buf.get_end_iter()
        buf.insert_with_tags_by_name(end, f"\u2699 {msg}\n", "system")
        self._sov_autoscroll()

    def _sov_error(self, msg):
        """Error message in Sovereign chat."""
        buf = self.sov_chat_buf
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")
        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
        end = buf.get_end_iter()
        buf.insert_with_tags_by_name(end, f"\u2716 {msg}\n", "error")
        self._sov_autoscroll()

    def _sov_motd(self, line):
        """MOTD line in Sovereign chat."""
        buf = self.sov_chat_buf
        end = buf.get_end_iter()
        buf.insert_with_tags_by_name(end, f"{line}\n", "motd")
        self._sov_autoscroll()

    def _sov_action(self, nick, text):
        """Action (/me) in Sovereign chat."""
        buf = self.sov_chat_buf
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")
        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
        end = buf.get_end_iter()
        buf.insert_with_tags_by_name(end, f"* {nick} {text}\n", "action")
        self._sov_autoscroll()

    def _sov_autoscroll(self):
        adj = self.sov_chat_scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    # ── Sovereign Input & Command Parser ────────────────────────

    # ── Right-Click Context Menu & PM System ──────────────────────

    def _add_sidebar_row(self, name, is_channel=True):
        """Add a channel or PM row to the sidebar."""
        row = Gtk.ListBoxRow()
        row.set_name(name)
        row.get_style_context().add_class("channel-row")
        lbl = Gtk.Label(xalign=0)
        lbl.set_margin_start(8)
        if is_channel:
            lbl.set_text(name)
        else:
            color = _nick_color(name)
            lbl.set_markup(f"<span color='{color}'>\u2709 {GLib.markup_escape_text(name)}</span>")
        row.add(lbl)
        if is_channel:
            self.sov_channels_list.add(row)
        else:
            self.sov_pm_list.add(row)
        return row

    def _sov_current_target(self):
        """Return current target — channel name or PM nick."""
        return getattr(self, '_sov_active_pm', None) or self._sov_channel

    def _on_pm_tab_switch(self, listbox, row):
        """Click a PM nick in sidebar — open/focus the PM panel."""
        nick = row.get_name()
        self._open_sov_pm(nick)

    def _on_sov_user_click(self, widget, event):
        """Handle clicks on user list — right-click for context menu, double-click for PM."""
        if event.button == 3:  # Right click
            row = self.sov_user_list.get_row_at_y(int(event.y))
            if not row:
                return False
            nick = row.get_name()
            if not nick or nick == self._sov_nick:
                return False
            self._show_sov_user_menu(nick, event)
            return True
        elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:  # Double click
            row = self.sov_user_list.get_row_at_y(int(event.y))
            if row:
                nick = row.get_name()
                if nick and nick != self._sov_nick:
                    self._open_sov_pm(nick)
            return True
        return False

    def _show_sov_user_menu(self, nick, event):
        """Right-click context menu for a user."""
        menu = Gtk.Menu()

        # Private Message
        item_pm = Gtk.MenuItem(label=f"Private Message {nick}")
        item_pm.connect("activate", lambda w: self._open_sov_pm(nick))
        menu.append(item_pm)

        # Whois
        item_whois = Gtk.MenuItem(label=f"Whois {nick}")
        item_whois.connect("activate", lambda w: self._sov_irc.send_whois(nick) if self._sov_irc else None)
        menu.append(item_whois)

        menu.append(Gtk.SeparatorMenuItem())

        # Mention in chat
        item_mention = Gtk.MenuItem(label=f"Mention @{nick}")
        item_mention.connect("activate", lambda w: self._sov_insert_text(f"{nick}: "))
        menu.append(item_mention)

        # Slap (fun)
        item_slap = Gtk.MenuItem(label=f"Slap {nick}")
        item_slap.connect("activate", lambda w: self._sov_do_action(f"slaps {nick} around a bit with a large trout"))
        menu.append(item_slap)

        menu.append(Gtk.SeparatorMenuItem())

        # Op/Voice/Kick (admin actions)
        item_op = Gtk.MenuItem(label=f"Give Op (+o)")
        item_op.connect("activate", lambda w: self._sov_irc.set_mode("+o", nick) if self._sov_irc else None)
        menu.append(item_op)

        item_voice = Gtk.MenuItem(label=f"Give Voice (+v)")
        item_voice.connect("activate", lambda w: self._sov_irc.set_mode("+v", nick) if self._sov_irc else None)
        menu.append(item_voice)

        item_kick = Gtk.MenuItem(label=f"Kick {nick}")
        item_kick.connect("activate", lambda w: self._sov_kick_prompt(nick))
        menu.append(item_kick)

        item_ban = Gtk.MenuItem(label=f"Ban {nick}")
        item_ban.connect("activate", lambda w: self._sov_irc.set_mode(f"+b {nick}!*@*") if self._sov_irc else None)
        menu.append(item_ban)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _sov_insert_text(self, text):
        """Insert text into the chat entry."""
        self.sov_entry.set_text(text)
        self.sov_entry.set_position(-1)
        self.sov_entry.grab_focus()

    def _sov_do_action(self, text):
        """Send a /me action."""
        if self._sov_irc and self._sov_connected:
            self._sov_irc.send_action(text)
            self._sov_action(self._sov_nick, text)

    def _sov_kick_prompt(self, nick):
        """Kick with optional reason dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Kick {nick}?",
        )
        dialog.format_secondary_text("Enter reason (optional):")
        entry = Gtk.Entry()
        entry.set_text("Removed")
        dialog.get_content_area().pack_end(entry, False, False, 0)
        dialog.show_all()
        resp = dialog.run()
        reason = entry.get_text() or "Removed"
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and self._sov_irc:
            self._sov_irc.kick_user(nick, reason)

    def _open_sov_pm(self, nick):
        """Open PM panel next to main chat (xat-style slide-in)."""
        if nick not in self._sov_pm_tabs:
            self._sov_pm_tabs[nick] = True
            self._add_sidebar_row(nick, is_channel=False)
            self.sov_pm_list.show_all()

        self._sov_active_pm = nick
        for row in self.sov_pm_list.get_children():
            if row.get_name() == nick:
                row.get_style_context().remove_class("pm-unread")
                break
        self.sov_pm_header_lbl.set_markup(
            f"<span color='#60a5fa' weight='bold'>\u2709 {GLib.markup_escape_text(nick)}</span>"
        )

        # Per-nick persistent buffers — no more history wipe on switch
        if not hasattr(self, '_sov_pm_nick_bufs'):
            self._sov_pm_nick_bufs = {}
        if nick not in self._sov_pm_nick_bufs:
            buf = Gtk.TextBuffer()
            # Clone tags from master buffer
            for tag_name, fg, weight in [
                ("system", "#64748b", None),
                ("timestamp", "#475569", None),
                ("self_nick", "#38bdf8", Pango.Weight.BOLD),
            ]:
                props = {"foreground": fg}
                if weight: props["weight"] = weight
                if tag_name == "system": props["style"] = Pango.Style.ITALIC
                buf.create_tag(tag_name, **props)
            for safe, color in [(f"nick_{c.replace('#','')}", c) for c in
                                ["#f87171","#fb923c","#fbbf24","#a3e635",
                                 "#4ade80","#34d399","#22d3ee","#60a5fa",
                                 "#818cf8","#a78bfa","#c084fc","#e879f9",
                                 "#f472b6","#fb7185"]]:
                buf.create_tag(safe, foreground=color, weight=Pango.Weight.BOLD)
            end = buf.get_end_iter()
            buf.insert_with_tags_by_name(end, f"Private chat with {nick}\n", "system")
            self._sov_pm_nick_bufs[nick] = buf

        # Swap buffer into the view — preserves history per nick
        self.sov_pm_view.set_buffer(self._sov_pm_nick_bufs[nick])

        self.sov_pm_panel.show_all()
        self.sov_pm_entry.grab_focus()

        # Set paned position to give PM ~40% of space
        GLib.idle_add(lambda: self.sov_chat_paned.set_position(
            int(self.sov_chat_paned.get_allocated_width() * 0.6)
        ))

    def _close_active_pm(self):
        """Close the PM panel (slide it away)."""
        self.sov_pm_panel.hide()
        self._sov_active_pm = None

    def _on_sov_pm_send(self, widget):
        """Send from the PM input box."""
        msg = self.sov_pm_entry.get_text().strip()
        if not msg or not self._sov_irc or not self._sov_active_pm:
            return
        self.sov_pm_entry.set_text("")
        nick = self._sov_active_pm
        self._sov_irc.send_private(nick, msg)
        self._sov_pm_append(self._sov_nick, msg)

    def _sov_pm_append(self, sender, msg, target_nick=None):
        """Append a message to the PM panel for `target_nick` (defaults to active)."""
        target_nick = target_nick or self._sov_active_pm
        if not target_nick:
            return
        bufs = getattr(self, '_sov_pm_nick_bufs', {})
        buf = bufs.get(target_nick, self.sov_pm_buf)
        end = buf.get_end_iter()
        ts = time.strftime("%H:%M:%S")
        buf.insert_with_tags_by_name(end, f"[{ts}] ", "timestamp")
        end = buf.get_end_iter()
        if sender == self._sov_nick:
            buf.insert_with_tags_by_name(end, sender, "self_nick")
        else:
            color = _nick_color(sender)
            tag = f"nick_{color.replace('#', '')}"
            buf.insert_with_tags_by_name(end, sender, tag)
        end = buf.get_end_iter()
        buf.insert(end, f": {msg}\n")
        # Auto-scroll PM
        adj = self.sov_pm_scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def _close_sov_pm(self, nick):
        """Remove a PM from sidebar."""
        if nick in self._sov_pm_tabs:
            for row in self.sov_pm_list.get_children():
                if row.get_name() == nick:
                    self.sov_pm_list.remove(row)
                    break
            del self._sov_pm_tabs[nick]
        if self._sov_active_pm == nick:
            self._close_active_pm()

    def _on_sov_send(self, widget):
        """Handle user input — route to channel or PM depending on active view."""
        msg = self.sov_entry.get_text().strip()
        if not msg:
            return
        self.sov_entry.set_text("")

        if not self._sov_irc or not self._sov_connected:
            self._sov_sys("Not connected to Sovereign")
            return

        if msg.startswith("/"):
            self._sov_parse_command(msg)
        elif self._sov_active_pm:
            # Main entry also works for PM if panel is open
            nick = self._sov_active_pm
            self._sov_irc.send_private(nick, msg)
            self._sov_pm_append(self._sov_nick, msg)
        else:
            # Channel message
            self._sov_irc.send_message(msg)
            self._sov_on_irc_message(self._sov_nick, self._sov_channel, msg)

    def _sov_parse_command(self, msg):
        """Parse IRC-style commands and dispatch via IRCClient."""
        irc = self._sov_irc
        if not irc:
            return

        parts = msg.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/nick":
            if args:
                irc.change_nick(args.strip())
            else:
                self._sov_sys(f"Current nick: {self._sov_nick}")

        elif cmd == "/topic":
            if args:
                irc.set_topic(args)
            else:
                topic = irc.channel_topic or "No topic set"
                self._sov_sys(f"Topic: {topic}")

        elif cmd == "/join":
            chan = args.strip()
            if chan:
                if not chan.startswith("#"):
                    chan = f"#{chan}"
                # Part current channel, join new one
                irc._send_raw(f"PART {self._sov_channel} :Switching channels")
                self._sov_channel = chan
                irc.channel = chan
                irc._send_raw(f"JOIN {chan}")
                self.sov_channel_lbl.set_markup(
                    f"<span size='large' weight='800' color='#00d4ff'>{GLib.markup_escape_text(chan)}</span>"
                )

        elif cmd == "/part":
            reason = args or "Leaving"
            irc._send_raw(f"PART {self._sov_channel} :{reason}")

        elif cmd in ("/msg", "/dm", "/pm", "/query"):
            dm_parts = args.split(None, 1)
            if len(dm_parts) >= 1 and dm_parts[0]:
                target = dm_parts[0]
                dm_msg = dm_parts[1] if len(dm_parts) == 2 else ""
                self._open_sov_pm(target)
                if dm_msg:
                    irc.send_private(target, dm_msg)
                    self._sov_pm_append(self._sov_nick, dm_msg, target_nick=target)
            else:
                self._sov_sys("Usage: /msg <nick> [message]")

        elif cmd == "/me":
            if args:
                irc.send_action(args)
                self._sov_action(self._sov_nick, args)

        elif cmd == "/whois":
            target = args.strip() or self._sov_nick
            irc.send_whois(target)

        elif cmd == "/list":
            irc._send_raw("LIST")

        elif cmd == "/names":
            irc.request_names()

        elif cmd == "/mode":
            mode_parts = args.split(None, 1)
            if mode_parts:
                target = mode_parts[1] if len(mode_parts) > 1 else None
                irc.set_mode(mode_parts[0], target=target)
            else:
                irc._send_raw(f"MODE {self._sov_channel}")

        elif cmd == "/kick":
            kick_parts = args.split(None, 1)
            if kick_parts:
                reason = kick_parts[1] if len(kick_parts) > 1 else "Removed"
                irc.kick_user(kick_parts[0], reason)
            else:
                self._sov_sys("Usage: /kick <nick> [reason]")

        elif cmd == "/ban":
            if args:
                target = args.split()[0]
                irc.set_mode(f"+b {target}!*@*")
            else:
                self._sov_sys("Usage: /ban <nick>")

        elif cmd == "/invite":
            if args:
                irc._send_raw(f"INVITE {args.strip()} {self._sov_channel}")
            else:
                self._sov_sys("Usage: /invite <nick>")

        elif cmd == "/away":
            if args:
                irc._send_raw(f"AWAY :{args}")
            else:
                irc._send_raw("AWAY")

        elif cmd == "/register":
            if args:
                irc._send_raw(f"PRIVMSG NickServ :REGISTER {args}")
                self._sov_sys("Registration request sent to NickServ")
            else:
                self._sov_sys("Usage: /register <password> <email>")

        elif cmd == "/identify":
            if args:
                irc._send_raw(f"PRIVMSG NickServ :IDENTIFY {args}")
            else:
                self._sov_sys("Usage: /identify <password>")

        elif cmd == "/oper":
            if args:
                oper_parts = args.split(None, 1)
                if len(oper_parts) >= 2:
                    irc._send_raw(f"OPER {oper_parts[0]} {oper_parts[1]}")
                else:
                    self._sov_sys("Usage: /oper <name> <password>")
            else:
                self._sov_sys("Usage: /oper <name> <password>")

        elif cmd == "/unmask":
            # GOD_MODE: Command-level unmasking request
            target = args.strip()
            loop = asyncio.get_event_loop()
            if target:
                loop.create_task(self._sov_irc.send({"type": "unmask", "target": target}))
            else:
                loop.create_task(self._sov_irc.send({"type": "unmask"}))

        elif cmd == "/raw":
            if args:
                irc._send_raw(args)
                self._sov_sys(f">> {args}")
            else:
                self._sov_sys("Usage: /raw <IRC command>")

        elif cmd == "/help":
            help_lines = [
                "Sovereign IRC Commands:",
                "  /nick <name>           — Change your nick",
                "  /topic [text]          — View or set channel topic",
                "  /join <#channel>       — Join a channel",
                "  /part [reason]         — Leave current channel",
                "  /msg <nick> <text>     — Send private message",
                "  /me <action>           — Action (/me does something)",
                "  /whois [nick]          — User info lookup",
                "  /list                  — List all channels",
                "  /names                 — List users in channel",
                "  /mode <flags> [target] — Set channel/user modes",
                "  /kick <nick> [reason]  — Kick user from channel",
                "  /ban <nick>            — Ban user from channel",
                "  /invite <nick>         — Invite user to channel",
                "  /away [message]        — Set/clear away status",
                "  /register <pass> <email> — Register nick (NickServ)",
                "  /identify <password>   — Identify to NickServ",
                "  /oper <name> <pass>    — Authenticate as IRC operator",
                "  /raw <command>         — Send raw IRC command",
            ]
            for line in help_lines:
                self._sov_sys(line)
        else:
            self._sov_sys(f"Unknown command: {cmd}. Type /help for commands.")

    def _on_chan_switch(self, listbox, row):
        """Switch channels via IRC JOIN/PART."""
        chan = row.get_name()
        # Deselect PM sidebar
        self.sov_pm_list.unselect_all()

        self.sov_channel_lbl.set_markup(
            f"<span size='large' weight='800' color='#00d4ff'>{GLib.markup_escape_text(chan)}</span>"
        )
        for r in listbox.get_children():
            r.get_style_context().remove_class("channel-active")
        row.get_style_context().add_class("channel-active")

        if self._sov_irc and self._sov_connected and chan != self._sov_channel:
            self._sov_irc._send_raw(f"PART {self._sov_channel} :Switching")
            self._sov_channel = chan
            self._sov_irc.channel = chan
            self._sov_irc._send_raw(f"JOIN {chan}")

    def _update_sov_userlist(self):
        """Refresh the user list from IRCClient NAMES data."""
        for child in self.sov_user_list.get_children():
            self.sov_user_list.remove(child)

        user_modes = self._sov_irc._user_modes if self._sov_irc else {}

        for nick in self._sov_users:
            row = Gtk.ListBoxRow()
            row.set_name(nick)
            row.get_style_context().add_class("irc-user-row")
            hbox = Gtk.Box(spacing=6)
            hbox.set_margin_start(4)
            hbox.set_margin_end(4)

            prefix = user_modes.get(nick, "")

            # Status dot color based on mode prefix
            dot = Gtk.Label()
            if "@" in prefix or "~" in prefix or "&" in prefix:
                color = "#fbbf24"   # op/owner/admin = gold
            elif "+" in prefix or "%" in prefix:
                color = "#22d3ee"   # voice/halfop = cyan
            else:
                color = "#00ff9d"   # normal = green
            dot.set_markup(f"<span color='{color}'>\u2b24</span>")
            hbox.pack_start(dot, False, False, 0)

            # Nick with prefix
            nick_color = _nick_color(nick)
            lbl = Gtk.Label(xalign=0)
            lbl.set_markup(
                f"<span color='{nick_color}'>{GLib.markup_escape_text(prefix + nick)}</span>"
            )
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            hbox.pack_start(lbl, True, True, 0)

            row.add(hbox)
            self.sov_user_list.add(row)

        self.sov_user_list.show_all()
        self.sov_user_count.set_text(f"{len(self._sov_users)} users")

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
        output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        output_view.get_style_context().add_class("terminal-view")
        scroll = Gtk.ScrolledWindow()
        scroll.set_propagate_natural_width(False)
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
    def _on_crawl_network(self, btn):
        self._sov_sys("NEXUS_SYNC: Attempting global node discovery...")
        threading.Thread(target=self._crawl_task, daemon=True).start()

    def _crawl_task(self):
        import requests
        try:
            nexus_url = config.get("stealth", "nexus_relay_url", default="http://127.0.0.1:9999")
            resp = requests.get(f"{nexus_url}/api/nexus/nodes", timeout=5)
            if resp.status_code == 200:
                nodes = resp.json()
                if not nodes:
                    GLib.idle_add(self._sov_sys, "NEXUS_INFO: No other public nodes discovered.")
                    return
                GLib.idle_add(self._show_nodes_dialog, nodes)
            else:
                GLib.idle_add(self._sov_sys, f"NEXUS_ERROR: Directory unreachable (Status {resp.status_code})")
        except Exception as e:
            GLib.idle_add(self._sov_sys, f"NEXUS_FAULT: {e}")

    def _show_nodes_dialog(self, nodes):
        dialog = Gtk.Dialog(title="GLOBAL_SHADOW_NODES", parent=self.get_toplevel(), modal=True)
        dialog.set_default_size(400, 300)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(10); box.set_margin_end(10); box.set_margin_top(10)

        list_box = Gtk.ListBox()
        for nid, n in nodes.items():
            row = Gtk.Box(spacing=10)
            row.pack_start(Gtk.Label(label=f"{n['name']} ({n['host']}:{n['port']})"), True, True, 0)
            btn = Gtk.Button(label="Connect")
            btn.connect("clicked", lambda b, host=n['host'], port=n['port']: self._connect_to_remote(dialog, host, port))
            row.pack_end(btn, False, False, 0)
            list_box.add(row)

        scroll = Gtk.ScrolledWindow()
        scroll.set_propagate_natural_width(False)
        scroll.add(list_box)
        box.pack_start(scroll, True, True, 0)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def _connect_to_remote(self, dialog, host, port):
        dialog.response(Gtk.ResponseType.OK)
        # Update config temporarily (or permanently if desired)
        self._config.set("irc", "sovereign_server", host)
        self._config.set("irc", "sovereign_port", port)
        self._sov_disconnect()
        self._sov_connect()

    def _sov_sys(self, msg):
        end = self.sov_chat_buf.get_end_iter()
        self.sov_chat_buf.insert_with_tags_by_name(end, f"[*] {msg}\n", "system")
        if self._sov_active_pm == None:
            self._scroll_to_bottom(self.sov_chat_scroll)
    def _on_unmask_result(self, d):
        target = d.get("target")
        data = d.get("data", {})
        msg = f"[GOD_MODE] UNMASK_REPORT for {target}:\n"
        msg += f"  IP: {data.get('ip')}\n"
        msg += f"  OS: {data.get('os')} ({data.get('distro')})\n"
        msg += f"  Platform: {data.get('platform')}\n"
        msg += f"  UA: {data.get('agent')}\n"
        self._sov_sys(msg)

    def _on_unmask_result_all(self, d):
        nodes = d.get("nodes", {})
        msg = f"[GOD_MODE] FULL_SPECTRUM_UNMASK ({len(nodes)} nodes):\n"
        for nick, data in nodes.items():
            msg += f"  {nick} -> {data.get('ip')} | {data.get('os')} | {data.get('distro')}\n"
        self._sov_sys(msg)

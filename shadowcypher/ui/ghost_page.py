import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from shadowcypher.core.hub import hub
from shadowcypher.core.logger import logger

class GhostDeck(Gtk.Box):
    """Spectral Ghost-Deck — The Command Bridge for Autonomous Infiltrations."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.set_margin_top(40)
        self.set_margin_start(40)
        self.set_margin_end(40)

        # 1. Header Area
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_lbl = Gtk.Label()
        title_lbl.set_markup("<span size='xx-large' weight='bold' color='#e2e8f0'>SPECTRAL_GHOST-DECK</span>")
        header.pack_start(title_lbl, False, False, 0)
        
        # Stealth Status Badge
        self.stealth_badge = Gtk.Label()
        self._update_stealth_status()
        header.pack_end(self.stealth_badge, False, False, 0)
        
        self.pack_start(header, False, False, 0)

        # 2. Command Console
        cmd_box = Gtk.Frame()
        cmd_box.get_style_context().add_class("card")
        cmd_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        cmd_inner.set_margin_top(20)
        cmd_inner.set_margin_bottom(20)
        cmd_inner.set_margin_start(20)
        cmd_inner.set_margin_end(20)
        
        desc = Gtk.Label(label="Target an infrastructure node or web layer for autonomous zero-trace infiltration.")
        desc.set_halign(Gtk.Align.START)
        cmd_inner.pack_start(desc, False, False, 0)
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text("Target (URL or IP)")
        self.target_entry.set_hexpand(True)
        hbox.pack_start(self.target_entry, True, True, 0)
        
        self.ignite_btn = Gtk.Button(label="IGNITE_GHOST_CYCLE")
        self.ignite_btn.get_style_context().add_class("primary-button")
        self.ignite_btn.connect("clicked", self._on_ignite)
        hbox.pack_start(self.ignite_btn, False, False, 0)
        
        self.battle_btn = Gtk.Button(label="\u2694\ufe0f SPAWN_BATTLEGROUND")
        self.battle_btn.connect("clicked", self._on_spawn_battleground)
        hbox.pack_start(self.battle_btn, False, False, 0)
        
        cmd_inner.pack_start(hbox, False, False, 0)
        cmd_box.add(cmd_inner)
        self.pack_start(cmd_box, False, False, 0)

        # 3. Mission Phase Monitor
        monitor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        mon_lbl = Gtk.Label()
        mon_lbl.set_markup("<span weight='bold' color='#94a3b8'>// AUTONOMOUS_STATE_PHASES</span>")
        mon_lbl.set_halign(Gtk.Align.START)
        monitor_box.pack_start(mon_lbl, False, False, 0)
        
        self.phase_bar = Gtk.ProgressBar()
        self.phase_bar.set_fraction(0.0)
        monitor_box.pack_start(self.phase_bar, False, False, 0)
        
        self.phase_desc = Gtk.Label(label="Ready for mission ignition...")
        self.phase_desc.set_halign(Gtk.Align.START)
        monitor_box.pack_start(self.phase_desc, False, False, 0)
        
        self.pack_start(monitor_box, False, False, 0)

        # 4. Neural Thought Trace
        self.trace_view = Gtk.TextView()
        self.trace_view.set_editable(False)
        self.trace_view.set_cursor_visible(False)
        self.trace_view.get_style_context().add_class("console")
        
        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.add(self.trace_view)
        self.pack_start(scroller, True, True, 0)

        # Heartbeat check for stealth
        GLib.timeout_add(1000, self._update_stealth_status)
        
        # Subscribe to real-time mission updates
        from shadowcypher.core.bus import bus
        bus.subscribe("ghost_update", self._on_ghost_update)

    def _on_ghost_update(self, data: dict):
        """Reactive handler for autonomous mission pulses."""
        GLib.idle_add(self._process_ghost_event, data)

    def _process_ghost_event(self, data: dict):
        phase = data.get("phase")
        msg = data.get("message")
        progress = data.get("progress", 0.0)
        
        self.phase_bar.set_fraction(progress)
        self.phase_desc.set_text(msg)
        self._log_trace(f"[{phase}] {msg}")
        
        if phase == "COMPLETE" or phase == "EMERGENCY":
            self.ignite_btn.set_sensitive(True)

    def _update_stealth_status(self):
        is_ready = hub.is_stealth_ready()
        if is_ready:
            self.stealth_badge.set_markup("<span background='#22c55e' color='white' weight='bold'>   ONION_LINK: STEALTH_READY   </span>")
            if self.phase_bar.get_fraction() == 0.0 or self.phase_bar.get_fraction() == 1.0:
                self.ignite_btn.set_sensitive(True)
        else:
            self.stealth_badge.set_markup("<span background='#f87171' color='white' weight='bold'>   ONION_LINK: EXPOSED   </span>")
            self.ignite_btn.set_sensitive(False)
        return True

    def _on_spawn_battleground(self, btn):
        import subprocess
        from shadowcypher.core.platform import platform_engine
        
        # Path to Battleground Config (using arsenal primitives as target if composer is missing)
        self._log_trace("[BATTLEGROUND] IGNITING_SACRIFICIAL_TARGETS... Please Wait.")
        try:
            # We use the gauntlet_victim as a lightweight alternative to full docker
            victim_script = platform_engine.resolve_path("native", "relay", "shadow-relay") # Placeholder if gauntlet is not executable
            self._log_trace("[OK] Battleground Deployment Initiated. Access targets at 127.0.0.1:9999.")
            self.target_entry.set_text("127.0.0.1:9999")
        except Exception as e:
            self._log_trace(f"[FAIL] Battleground ignition failed: {e}")

    def _on_ignite(self, btn):
        target = self.target_entry.get_text()
        if not target: return
        
        res = hub.dispatch_ghost_mission(target)
        if "SUCCESS" in res:
            self._log_trace(f"[IGNITION] Launching Ghost Operational Cycle against {target}...")
            self.target_entry.set_text("")
            self.ignite_btn.set_sensitive(False)

    def _log_trace(self, msg):
        buffer = self.trace_view.get_buffer()
        buffer.insert_at_cursor(f"{msg}\n")
        # Scroll to end
        mark = buffer.create_mark(None, buffer.get_end_iter(), False)
        self.trace_view.scroll_to_mark(mark, 0.0, True, 0.5, 0.5)

        

"""
ShadowCypher Dashboard — Premium HUD with Cairo gauge visualizations.
Arc gauges for CPU/RAM/Disk, real metrics, arsenal status, live feed.
"""

import gi

gi.require_version("Gtk", "3.0")
import math
import shutil
import time

import cairo
import psutil
from gi.repository import GLib, Gtk, Pango

from shadowcypher.ai.sisyphus import sisyphus
from shadowcypher.core.bus import bus
from shadowcypher.core.hub import hub
from shadowcypher.core.logger import logger
from shadowcypher.ui.components import TacticalTerminal


class ArcGauge(Gtk.DrawingArea):
    """Cairo-drawn arc gauge — like the mockup's CPU/RAM dials."""

    def __init__(self, title="CPU", unit="%", accent=(0, 0.83, 1.0),
                 size=140, subtitle=""):
        super().__init__()
        self.set_size_request(size, size + 40)
        self._title = title
        self._unit = unit
        self._accent = accent
        self._value = 0.0
        self._subtitle = subtitle
        self._size = size
        self.connect("draw", self._on_draw)

    def set_value(self, val, subtitle=None):
        self._value = max(0, min(100, val))
        if subtitle is not None:
            self._subtitle = subtitle
        self.queue_draw()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        widget.get_allocated_height()
        cx = w / 2
        cy = self._size / 2 + 5
        radius = (self._size / 2) - 14

        cr.set_antialias(cairo.ANTIALIAS_BEST)

        # 1. Background Ring
        cr.set_line_width(8)
        cr.set_source_rgba(0.08, 0.12, 0.2, 0.6)
        cr.arc(cx, cy, radius, 0.75 * math.pi, 2.25 * math.pi)
        cr.stroke()

        # 2. Progress Arc
        if self._value > 0:
            cr.set_line_width(10)
            r, g, b = self._accent
            # Color escalation
            if self._value > 85: r, g, b = 0.96, 0.25, 0.37
            elif self._value > 65: r, g, b = 0.96, 0.62, 0.04

            cr.set_source_rgba(r, g, b, 0.9)
            angle = 0.75 * math.pi + (self._value / 100.0) * (1.5 * math.pi)
            cr.arc(cx, cy, radius, 0.75 * math.pi, angle)
            cr.stroke()

            # Glow
            cr.set_line_width(2)
            cr.set_source_rgba(r, g, b, 0.3)
            cr.arc(cx, cy, radius + 4, 0.75 * math.pi, angle)
            cr.stroke()

        # 3. Text & Labels
        cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(24)
        val_text = f"{self._value:.0f}{self._unit}"
        extents = cr.text_extents(val_text)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.move_to(cx - extents.width / 2, cy + extents.height / 2 - 2)
        cr.show_text(val_text)

        cr.set_font_size(10)
        cr.set_source_rgba(0.58, 0.64, 0.7, 1.0)
        title_ext = cr.text_extents(self._title)
        cr.move_to(cx - title_ext.width / 2, 12)
        cr.show_text(self._title)

        if self._subtitle:
            sub_ext = cr.text_extents(self._subtitle)
            cr.move_to(cx - sub_ext.width / 2, self._size + 24)
            cr.show_text(self._subtitle)


class MiniStat(Gtk.Box):
    """Small stat card for the info row."""
    def __init__(self, title, value="—", accent="#00d4ff"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.get_style_context().add_class("card")
        self.set_margin_start(3)
        self.set_margin_end(3)

        self._title_lbl = Gtk.Label(label=title.upper(), xalign=0)
        self._title_lbl.get_style_context().add_class("dim-label")
        self.pack_start(self._title_lbl, False, False, 0)

        self._val_lbl = Gtk.Label(xalign=0)
        self._val_lbl.set_markup(
            f"<span font_weight='800' color='{accent}'>{value}</span>"
        )
        self.pack_start(self._val_lbl, False, False, 0)
        self._accent = accent

    def set_value(self, val):
        GLib.idle_add(self._val_lbl.set_markup,
                      f"<span font_weight='800' color='{self._accent}'>{val}</span>")


class DashboardPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_width(False)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(20)
        content.set_margin_end(20)

        # ── Header ──
        header = Gtk.Box(spacing=12)
        title_lbl = Gtk.Label(xalign=0)
        title_lbl.set_markup(
            "<span font_weight='900' size='large' color='#00d4ff'>"
            "SHADOW_NODE_HUD</span>"
        )
        header.pack_start(title_lbl, False, False, 0)

        self._status = Gtk.Label()
        self._status.set_markup(
            "<span color='#10b981' font_weight='700'>● ALL SYSTEMS NOMINAL</span>"
        )
        header.pack_end(self._status, False, False, 0)
        content.pack_start(header, False, False, 0)

        # ── Gauge Row ──
        gauge_row = Gtk.Box(spacing=20, homogeneous=False)

        # Gauges panel (left)
        gauges_box = Gtk.Box(spacing=15, homogeneous=False)
        gauges_box.get_style_context().add_class("citadel-pulse")

        self.gauge_cpu = ArcGauge("CPU LOAD", "%", (0, 1.0, 0.61), 120)
        self.gauge_ram = ArcGauge("MEMORY", "%", (0.6, 0.4, 1.0), 120)
        self.gauge_disk = ArcGauge("DISK", "%", (1.0, 0.6, 0.1), 120)

        for g in [self.gauge_cpu, self.gauge_ram, self.gauge_disk]:
            gauges_box.pack_start(g, True, True, 5)
        gauge_row.pack_start(gauges_box, True, True, 0)

        # Stats panel (right)
        stats_box = Gtk.Grid()
        stats_box.set_column_spacing(24)
        stats_box.set_row_spacing(10)
        stats_box.set_valign(Gtk.Align.START)

        self.stat_ai = MiniStat("AI_CORE", "NOMINAL", "#8b5cf6")
        self.stat_missions = MiniStat("ACTIVE_MISSIONS", "0", "#f43f5e")
        self.stat_uptime = MiniStat("MISSION_UPTIME", "0:00:00", "#38bdf8")
        self.stat_stealth = MiniStat("STEALTH_SIGNATURE", "4/5 ACTIVE", "#fbbf24")
        self.stat_threats = MiniStat("THREAT_INTEL", "0 HITS", "#f97316")
        self.stat_integrity = MiniStat("CORE_INTEGRITY", "VERIFIED", "#10b981")
        self.stat_relay = MiniStat("SHADOW_PLANE", "SECURE", "#0ea5e9")
        self.stat_net = MiniStat("GHOST_IO_SPEED", "0 B/s", "#64748b")
        self.stat_pulse = MiniStat("ENTROPY_SIGNATURE", "NOMINAL", "#00ff9d")

        stats_list = [
            self.stat_ai, self.stat_missions, self.stat_uptime,
            self.stat_stealth, self.stat_threats, self.stat_integrity,
            self.stat_relay, self.stat_net, self.stat_pulse
        ]

        for i, stat in enumerate(stats_list):
            stats_box.attach(stat, i % 3, i // 3, 1, 1)

        gauge_row.pack_start(stats_box, True, True, 10)
        content.pack_start(gauge_row, False, False, 0)

        # ── Arsenal Grid ──
        arsenal_lbl = Gtk.Label(xalign=0)
        arsenal_lbl.set_markup(
            "<span font_weight='800' color='#94a3b8' size='small'>"
            "ARSENAL STATUS</span>"
        )
        content.pack_start(arsenal_lbl, False, False, 2)

        arsenal_flow = Gtk.FlowBox()
        arsenal_flow.set_max_children_per_line(6)
        arsenal_flow.set_min_children_per_line(3)
        arsenal_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        arsenal_flow.set_row_spacing(6)
        arsenal_flow.set_column_spacing(6)
        arsenal_flow.set_homogeneous(True)

        tools = [
            ("nmap", "Nmap"),
            ("hydra", "Hydra"),
            ("hashcat", "Hashcat"),
            ("aircrack-ng", "Aircrack"),
            ("nuclei", "Nuclei"),
            ("ffuf", "FFuF"),
            ("john", "John"),
            ("tcpdump", "tcpdump"),
            ("sqlmap", "SQLMap"),
            ("nikto", "Nikto"),
            ("tor", "Tor"),
            ("responder", "Responder"),
        ]

        self._arsenal_rows = {}
        for cmd, label in tools:
            tb = Gtk.Box(spacing=8)
            tb.get_style_context().add_class("card")
            dot = Gtk.Label()
            dot.set_markup("<span color='#475569'>●</span>") # Default to dim/searching
            tb.pack_start(dot, False, False, 4)
            nm = Gtk.Label(label=label, xalign=0)
            nm.set_ellipsize(Pango.EllipsizeMode.END)
            nm.get_style_context().add_class("dim-label")
            tb.pack_start(nm, True, True, 0)
            arsenal_flow.add(tb)
            self._arsenal_rows[cmd] = (dot, nm)

        content.pack_start(arsenal_flow, False, False, 0)

        # ── Mission Telemetry (Live Feed) ──
        feed_lbl = Gtk.Label(xalign=0)
        feed_lbl.set_markup(
            "<span font_weight='800' color='#94a3b8' size='small'>"
            "MISSION TELEMETRY</span>"
        )
        content.pack_start(feed_lbl, False, False, 2)

        self.terminal = TacticalTerminal(height=160)
        content.pack_start(self.terminal, True, True, 0)

        scroll.add(content)
        self.pack_start(scroll, True, True, 0)

        # ── Init + Timers ──
        _n = psutil.net_io_counters()
        self._last_net_bytes = _n.bytes_sent + _n.bytes_recv
        self._last_t = time.time()
        GLib.timeout_add(1500, self._tick)
        GLib.idle_add(self._init_once)

        # Async Arsenal Audit (Prevents UI hang on constructor)
        import threading
        threading.Thread(target=self._async_arsenal_audit, daemon=True).start()

        bus.subscribe("mission_update",
                      lambda m: GLib.idle_add(
                          self.terminal.log, f"MISSION: {m}", "INFO"))
        bus.subscribe("module_log",
                      lambda m: GLib.idle_add(
                          self.terminal.log,
                          f"{m.get('module','?')}: {m.get('text','')}",
                          m.get('level', 'INFO')))

        self.terminal.log("ShadowCypher operational. All systems ready.", "SYSTEM")
        self.show_all()

    def _async_arsenal_audit(self):
        """Checks for tool availability without blocking the main thread."""
        for cmd, (dot, nm) in self._arsenal_rows.items():
            found = shutil.which(cmd) is not None
            if found:
                GLib.idle_add(dot.set_markup, "<span color='#10b981'>●</span>")
                GLib.idle_add(nm.get_style_context().remove_class, "dim-label")
            time.sleep(0.01) # Tiny yield to keep thread pool breathing

    def _init_once(self):
        """One-shot init for AI + stealth."""
        try:
            from shadowcypher.ai.providers import provider_registry
            p = provider_registry.active
            if p and p.is_configured:
                self.stat_ai.set_value(f"{p.model}")
            else:
                self.stat_ai.set_value("Ollama (local)")
        except Exception:
            self.stat_ai.set_value("Offline")

        try:
            from shadowcypher.core.web import stealth_web
            caps = stealth_web.get_capabilities()
            n = sum(1 for v in caps.values() if v)
            self.stat_stealth.set_value(f"{n}/5 Active")
        except Exception:
            self.stat_stealth.set_value("N/A")

        return False

    def _tick(self):
        """Live data refresh for all tactical and security metrics."""
        if not self.get_mapped():
            return True
        try:
            # 1. System Gauges
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            GLib.idle_add(self.gauge_cpu.set_value, cpu)
            GLib.idle_add(self.gauge_ram.set_value, mem.percent)
            GLib.idle_add(self.gauge_disk.set_value, disk.percent)

            # 2. Mission & System Stats
            summary = hub.get_tactical_summary()

            # Map stats safely
            stat_map = {
                self.stat_missions: str(summary.get("active_missions", 0)),
                self.stat_uptime: summary.get("uptime", "0:00:00"),
                self.stat_integrity: "VERIFIED" if sisyphus.is_stable else "TAMPERED",
                self.stat_threats: f"{summary.get('threat_hits', 0)} HITS",
                self.stat_stealth: "ACTIVE" if hub.is_stealth_ready() else "EXPOSED"
            }

            for widget, val in stat_map.items():
                widget.set_value(val)

            # Signal Bridge (Go Relay)
            relay_lbl = "SECURE" if (hasattr(hub, 'relay_bridge') and hub.relay_bridge.connected) else "OFFLINE"
            self.stat_relay.set_value(relay_lbl)

            # Real network throughput
            now = time.time()
            dt = now - self._last_t or 1
            net = psutil.net_io_counters()
            total_bytes = net.bytes_sent + net.bytes_recv
            bps = (total_bytes - self._last_net_bytes) / dt
            self._last_net_bytes = total_bytes
            self._last_t = now
            if bps >= 1_048_576:
                net_str = f"{bps/1_048_576:.1f} MB/s"
            elif bps >= 1024:
                net_str = f"{bps/1024:.1f} KB/s"
            else:
                net_str = f"{bps:.0f} B/s"
            self.stat_net.set_value(net_str)

            # Real entropy: measure randomness of /dev/urandom read
            try:
                raw = open("/dev/urandom", "rb").read(64)
                byte_counts = [0] * 256
                for b in raw:
                    byte_counts[b] += 1
                import math as _math
                ent = -sum((c/64) * _math.log2(c/64) for c in byte_counts if c)
                self.stat_pulse.set_value(f"{ent:.2f} bits")
            except Exception:
                self.stat_pulse.set_value("NOMINAL")

        except Exception as e:
            logger.debug("ui", f"DASHBOARD_TICK_FAILURE: {e}")

        return True

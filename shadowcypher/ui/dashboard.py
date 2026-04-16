"""
ShadowCypher Dashboard — Premium HUD with Cairo gauge visualizations.
Arc gauges for CPU/RAM/Disk, real metrics, arsenal status, live feed.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango, Gdk
import cairo
import math
import psutil
import time
import shutil

from shadowcypher.core.hub import hub
from shadowcypher.core.bus import bus
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
        h = widget.get_allocated_height()
        cx = w / 2
        cy = self._size / 2 + 5
        radius = (self._size / 2) - 14

        # Background
        cr.set_source_rgba(0.02, 0.04, 0.06, 0)
        cr.paint()

        # Track arc (270 degrees, gap at bottom)
        start_angle = 0.75 * math.pi  # 135 degrees
        end_angle = 2.25 * math.pi    # 405 degrees
        arc_range = end_angle - start_angle

        # Background track
        cr.set_line_width(8)
        cr.set_source_rgba(0.15, 0.2, 0.25, 0.5)
        cr.arc(cx, cy, radius, start_angle, end_angle)
        cr.stroke()

        # Value arc
        if self._value > 0:
            val_angle = start_angle + (self._value / 100.0) * arc_range
            r, g, b = self._accent

            # Color shift based on value (green -> yellow -> red)
            if self._value > 85:
                r, g, b = 0.96, 0.25, 0.37  # Rose
            elif self._value > 65:
                r, g, b = 0.96, 0.62, 0.04  # Amber

            # Gradient glow effect
            cr.set_line_width(8)
            cr.set_source_rgba(r, g, b, 0.9)
            cr.arc(cx, cy, radius, start_angle, val_angle)
            cr.stroke()

            # Outer glow
            cr.set_line_width(12)
            cr.set_source_rgba(r, g, b, 0.12)
            cr.arc(cx, cy, radius, start_angle, val_angle)
            cr.stroke()

        # Tick marks
        cr.set_line_width(1)
        for i in range(0, 101, 10):
            angle = start_angle + (i / 100.0) * arc_range
            inner = radius - 12
            outer = radius - 6
            cr.set_source_rgba(0.4, 0.5, 0.6, 0.4)
            cr.move_to(cx + inner * math.cos(angle), cy + inner * math.sin(angle))
            cr.line_to(cx + outer * math.cos(angle), cy + outer * math.sin(angle))
            cr.stroke()

        # Center value text
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(28)
        val_text = f"{self._value:.0f}{self._unit}"
        extents = cr.text_extents(val_text)
        cr.set_source_rgba(0.94, 0.97, 0.97, 1.0)
        cr.move_to(cx - extents.width / 2, cy + extents.height / 2 - 2)
        cr.show_text(val_text)

        # Title above gauge
        cr.set_font_size(10)
        cr.set_source_rgba(0.58, 0.64, 0.7, 1.0)
        title_ext = cr.text_extents(self._title)
        cr.move_to(cx - title_ext.width / 2, 14)
        cr.show_text(self._title)

        # Subtitle below gauge
        if self._subtitle:
            cr.set_font_size(10)
            cr.set_source_rgba(0.45, 0.52, 0.58, 0.8)
            sub_ext = cr.text_extents(self._subtitle)
            cr.move_to(cx - sub_ext.width / 2, self._size + 20)
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
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # ── Header ──
        header = Gtk.Box(spacing=12)
        title_lbl = Gtk.Label(xalign=0)
        title_lbl.set_markup(
            "<span font_weight='900' size='large' color='#00d4ff'>"
            "OPERATIONAL OVERVIEW</span>"
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
        gauges_box = Gtk.Box(spacing=15, homogeneous=True)
        gauges_box.get_style_context().add_class("citadel-pulse") # Use pulse styling for consistency

        self.gauge_cpu = ArcGauge("CPU LOAD", "%", (0, 1.0, 0.61), 180)
        self.gauge_ram = ArcGauge("MEMORY", "%", (0.6, 0.4, 1.0), 180)
        self.gauge_disk = ArcGauge("DISK", "%", (1.0, 0.6, 0.1), 180)

        gauges_box.pack_start(self.gauge_cpu, True, True, 10)
        gauges_box.pack_start(self.gauge_ram, True, True, 10)
        gauges_box.pack_start(self.gauge_disk, True, True, 10)
        gauge_row.pack_start(gauges_box, True, True, 0)

        # Stats panel (right)
        stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        stats_box.set_size_request(240, -1)

        self.stat_ai = MiniStat("AI_CORE", "NOMINAL", "#8b5cf6")
        self.stat_missions = MiniStat("ACTIVE_MISSIONS", "0", "#f43f5e")
        self.stat_pulse = MiniStat("SPECTRAL_PULSE", "NOMINAL", "#00ff9d")
        self.stat_uptime = MiniStat("MISSION_UPTIME", "0:00:00", "#38bdf8")
        self.stat_net = MiniStat("NET_IO_PRESSURE", "0 B/s", "#64748b")
        self.stat_stealth = MiniStat("STEALTH_SIGNATURE", "4/5 ACTIVE", "#fbbf24")

        for stat in [self.stat_ai, self.stat_missions, self.stat_pulse, self.stat_uptime, self.stat_net, self.stat_stealth]:
            stats_box.pack_start(stat, False, False, 0)
        
        gauge_row.pack_start(stats_box, False, False, 0)
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

        for cmd, label in tools:
            found = shutil.which(cmd) is not None
            tb = Gtk.Box(spacing=8)
            tb.get_style_context().add_class("card")
            dot = Gtk.Label()
            dot.set_markup(
                f"<span color='{'#10b981' if found else '#475569'}'>●</span>"
            )
            tb.pack_start(dot, False, False, 4)
            nm = Gtk.Label(label=label, xalign=0)
            nm.set_ellipsize(Pango.EllipsizeMode.END)
            if not found:
                nm.get_style_context().add_class("dim-label")
            tb.pack_start(nm, True, True, 0)
            arsenal_flow.add(tb)

        content.pack_start(arsenal_flow, False, False, 0)

        # ── Mission Telemetry (Live Feed) ──
        feed_lbl = Gtk.Label(xalign=0)
        feed_lbl.set_markup(
            "<span font_weight='800' color='#94a3b8' size='small'>"
            "MISSION TELEMETRY</span>"
        )
        content.pack_start(feed_lbl, False, False, 2)

        self.terminal = TacticalTerminal(height=200)
        content.pack_start(self.terminal, True, True, 0)

        scroll.add(content)
        self.pack_start(scroll, True, True, 0)

        # ── Init + Timers ──
        self._last_net = 0
        self._last_t = time.time()
        GLib.timeout_add(1500, self._tick)
        GLib.idle_add(self._init_once)

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
        """Live data refresh."""
        try:
            # Gauges
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            GLib.idle_add(self.gauge_cpu.set_value, cpu,
                          f"{psutil.cpu_count()} cores · {psutil.cpu_freq().current:.0f}MHz"
                          if psutil.cpu_freq() else f"{psutil.cpu_count()} cores")
            GLib.idle_add(self.gauge_ram.set_value, mem.percent,
                          f"{mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB")
            GLib.idle_add(self.gauge_disk.set_value, disk.percent,
                          f"{disk.free / (1024**3):.0f} GB free")

            # Network rate
            now = time.time()
            net = psutil.net_io_counters()
            dt = now - self._last_t
            if dt > 0 and self._last_net > 0:
                rate = (net.bytes_sent - self._last_net) / dt
                if rate > 1048576:
                    self.stat_net.set_value(f"{rate/1048576:.1f} MB/s")
                elif rate > 1024:
                    self.stat_net.set_value(f"{rate/1024:.1f} KB/s")
                else:
                    self.stat_net.set_value(f"{rate:.0f} B/s")
            self._last_net = net.bytes_sent
            self._last_t = now

            # Hub
            s = hub.get_tactical_summary()
            self.stat_missions.set_value(str(s["active_missions"]))
            self.stat_uptime.set_value(s["uptime"])

            # Pulse
            from shadowcypher.core.pulse import pulse
            score = pulse.last_anomaly_score
            pulse_lbl = "NOMINAL" if score < 2.5 else f"ANOMALY ({score:.1f})"
            self.stat_pulse.set_value(pulse_lbl)

        except Exception:
            pass
        return True

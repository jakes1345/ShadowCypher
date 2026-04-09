"""
ShadowCypher APEX_DASHBOARD — The ultimate mission-control visualization.
Powered by high-fidelity Cairo rendering and real-time telemetry from the ShadowHub.
"""

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GLib, Gdk, Pango, PangoCairo
import cairo
import math
import psutil
import time
import random

from shadowcypher.core.hub import hub
from shadowcypher.core.bus import bus
from shadowcypher.ui.components import TacticalTerminal

class TacticalHUD(Gtk.DrawingArea):
    """Premium High-Fidelity Mission Command HUD."""
    
    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 580)
        self.angle = 0.0
        self.pings = [{"x": random.random(), "y": random.random(), "life": random.random()} for _ in range(15)]
        self.metrics = {"cpu": "0%", "ram": "0%", "net": "0 KB/s", "uptime": "0s", "missions": "0"}
        
        self.connect("draw", self._on_draw)
        GLib.timeout_add(33, self._tick_vis)
        GLib.timeout_add(1000, self._update_metrics)

    def _update_metrics(self):
        summary = hub.get_tactical_summary()
        self.metrics["cpu"] = f"{psutil.cpu_percent():.0f}%"
        self.metrics["ram"] = f"{psutil.virtual_memory().percent:.0f}%"
        self.metrics["uptime"] = summary["uptime"]
        self.metrics["missions"] = str(summary["active_missions"])
        return True

    def _tick_vis(self):
        self.angle += 0.04
        for p in self.pings:
            p["life"] -= 0.01
            if p["life"] <= 0:
                p["x"], p["y"], p["life"] = random.random(), random.random(), 1.0
        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cx, cy = w / 2, h / 2
        
        # 1. Depth (Glass)
        cr.set_source_rgba(0.01, 0.02, 0.04, 1.0)
        cr.paint()
        
        # 2. Cyber Radar
        radius = min(w, h) * 0.35
        cr.set_line_width(0.5)
        for r_f in [0.2, 0.4, 0.6, 0.8, 1.0]:
            cr.set_source_rgba(0, 0.8, 1.0, 0.05)
            cr.arc(cx, cy, radius * r_f, 0, 2 * math.pi)
            cr.stroke()
            
        # Sweep
        for i in range(20):
            ta = self.angle - (i * 0.05)
            cr.set_source_rgba(0, 0.9, 1.0, 0.2 * (1 - i/20))
            cr.set_line_width(3)
            cr.move_to(cx, cy)
            cr.line_to(cx + radius * math.cos(ta), cy + radius * math.sin(ta))
            cr.stroke()
            
        # 3. OSINT Pings
        for p in self.pings:
            alpha = p["life"] * 0.5
            cr.set_source_rgba(0, 1.0, 1.0, alpha)
            cr.arc(p["x"] * w, p["y"] * h, (1-p["life"]) * 30, 0, 2 * math.pi)
            cr.stroke()

        # 4. Status Pods
        self._draw_pod(cr, 50, 50, "PROCESSOR", self.metrics["cpu"], "CYBER_LOAD")
        self._draw_pod(cr, 50, 180, "MEMORY", self.metrics["ram"], "RAM_NEURAL")
        self._draw_pod(cr, w - 350, 50, "UPTIME", self.metrics["uptime"], "PERSISTENCE")
        self._draw_pod(cr, w - 350, 180, "MISSIONS", self.metrics["missions"], "ACTIVE_SWARM")

    def _draw_pod(self, cr, x, y, title, val, sub):
        cr.set_source_rgba(0.05, 0.1, 0.15, 0.8)
        # Rounded box
        cr.rectangle(x, y, 300, 110)
        cr.fill_preserve()
        cr.set_source_rgba(0, 1.0, 1.0, 0.2)
        cr.stroke()
        
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(11)
        cr.move_to(x+15, y+25)
        cr.show_text(title)
        
        cr.set_font_size(32)
        cr.move_to(x+15, y+70)
        cr.show_text(str(val))
        
        cr.set_source_rgba(0, 0.8, 1.0, 0.5)
        cr.set_font_size(9)
        cr.move_to(x+15, y+95)
        cr.show_text(sub)

class DashboardPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.hud = TacticalHUD()
        self.pack_start(self.hud, True, True, 0)

        # Tactical Feed
        f_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        f_box.set_margin_all(20)
        lbl = Gtk.Label(xalign=0)
        lbl.set_markup("<span color='#38bdf8' font_weight='bold'>\U0001f575\ufe0f MISSION_FEED_SYNC</span>")
        f_box.pack_start(lbl, False, False, 0)
        
        self.terminal = TacticalTerminal(height=250)
        f_box.pack_start(self.terminal, True, True, 0)
        self.pack_start(f_box, False, False, 0)
        
        # Subscribe to missions via Bus
        bus.subscribe("mission_update", lambda m: GLib.idle_add(self.terminal.log, f"MSN_UPDATE: {m}", "INFO"))
        self.show_all()

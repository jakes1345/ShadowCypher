import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango, PangoCairo
import cairo, math, psutil

class TacticalHUD(Gtk.DrawingArea):
    def __init__(self):
        super().__init__(); self.set_size_request(-1, 750); self.angle = 0.0
        self.metrics = {"cqu": "0%", "ram": "0%", "net": "0 TX/S", "stat": "IDLE"}
        self.connect("draw", self._on_draw)
        GLib.timeout_add(16, self._tick_vis); GLib.timeout_add(1000, self._tick_tel)
    def _tick_tel(self):
        self.metrics["cpu"] = f"{psutil.cpu_percent()}%"
        self.metrics["ram"] = f"{100-psutil.virtual_memory().percent:.1f}% FREE"
        self.metrics["net"] = f"{psutil.net_io_counters().packets_sent % 1000} TX/S"
        return True
    def _tick_vis(self): self.angle += 0.05; self.queue_draw(); return True
    def _on_draw(self, w, cr):
        width, height = w.get_allocated_width(), w.get_allocated_height()
        cx, cy = width/2, height/2; radius = 240
        cr.set_source_rgba(0.004, 0.006, 0.01, 1.0); cr.paint()
        # Radar Pulse Hub
        cr.set_source_rgba(0, 0.9, 1.0, 0.15); cr.set_line_width(1.5)
        for r in [0.2, 0.5, 0.8, 1.0]: cr.arc(cx, cy, radius*r, 0, 2*math.pi); cr.stroke()
        # Glass Pods (Build V21.2)
        self._draw_pod(cr, 80, 100, 320, 180, "SIGNAL_INTEL", self.metrics["net"], cx, cy)
        self._draw_pod(cr, width-400, 100, 320, 180, "CPU_ENGINE", self.metrics["cpu"], cx, cy)
        self._draw_pod(cr, 80, height-280, 320, 180, "MEMORY_HUB", self.metrics["ram"], cx, cy)
        self._draw_pod(cr, width-400, height-280, 320, 180, "TACTICAL", "ACTIVE", cx, cy)
    def _draw_pod(self, cr, x, y, pw, ph, title, val, cx, cy):
        cr.set_source_rgba(0, 0.9, 1.0, 0.4); cr.set_line_width(1.5); cr.move_to(cx, cy); cr.line_to(x+pw/2, y+ph/2); cr.stroke()
        r = 20; cr.set_source_rgba(0.06, 0.09, 0.12, 0.98)
        cr.arc(x+r, y+r, r, math.pi, 1.5*math.pi); cr.arc(x+pw-r, y+r, r, 1.5*math.pi, 2*math.pi)
        cr.arc(x+pw-r, y+ph-r, r, 0, 0.5*math.pi); cr.arc(x+r, y+ph-r, r, 0.5*math.pi, math.pi); cr.fill_preserve()
        cr.set_source_rgba(0, 0.9, 1.0, 0.5); cr.set_line_width(2.5); cr.stroke()
        cr.set_source_rgba(0, 0.9, 1.0, 0.9); cr.set_font_size(14); cr.move_to(x+30, y+35); cr.show_text(title)
        cr.set_source_rgba(1, 1, 1, 1); cr.set_font_size(44); cr.move_to(x+30, y+90); cr.show_text(str(val))

class DashboardPage(Gtk.Box):
    def __init__(self, animation_type=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add(TacticalHUD()); self.show_all()

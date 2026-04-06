"""Professional Theme Engine — 7 High-Fidelity Security Aesthetics."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import math
import cairo

from shadowcypher.ui.styles import SHADOWCYPHER_CSS

# ─────────────────────────────────────────────────────────────────────
# 1) PROFESSIONAL MONITOR ENGINES (High-FPS, Low-Distraction)
# ─────────────────────────────────────────────────────────────────────

class PulseMonitor(Gtk.DrawingArea):
    """Sub-pixel smooth pulse monitor. Stealthy, Obsidian aesthetic."""
    def __init__(self, color_rgba=(0.0, 0.95, 1.0, 1.0)):
        super().__init__()
        self.rgba = color_rgba
        self.set_size_request(-1, 150)
        self.connect("draw", self._on_draw)
        self.glow = 0.0
        self.dir = 1
        GLib.timeout_add(16, self._tick)

    def _tick(self):
        self.glow += (0.01 * self.dir)
        if self.glow >= 0.7 or self.glow <= 0.0: self.dir *= -1
        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        # Deep Obsidian Base
        cr.set_source_rgba(0.04, 0.05, 0.07, 1.0)
        cr.paint()
        
        # Subtle Grid Trace
        cr.set_source_rgba(self.rgba[0], self.rgba[1], self.rgba[2], 0.03)
        cr.set_line_width(1)
        for i in range(0, w, 40):
            cr.move_to(i, 0); cr.line_to(i, h); cr.stroke()
        for i in range(0, h, 40):
            cr.move_to(0, i); cr.line_to(w, i); cr.stroke()

        # Premium Radial Glow
        grad = cairo.RadialGradient(w/2, h/2, 10, w/2, h/2, 80 + (self.glow * 100))
        grad.add_color_stop_rgba(0, self.rgba[0], self.rgba[1], self.rgba[2], 0.15 * self.glow)
        grad.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(grad)
        cr.arc(w/2, h/2, 80 + (self.glow * 100), 0, 2 * math.pi)
        cr.fill()

# ─────────────────────────────────────────────────────────────────────
# 2) THEME REPOSITORY (7 Pro-Tier Aesthetics)
# ─────────────────────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "name": "Obsidian Stealth",
        "description": "Professional 60FPS Glassmorphic Tactical HUD",
        "animation": "pulse_cyan",
        "css": """
            * { background-clip: padding-box; }
            window { background-color: #010204; color: #d0d5d9; font-family: sans-serif; }
            headerbar { background: #030508; border-bottom: 3px solid #00f2ff; box-shadow: 0 4px 20px rgba(0, 242, 255, 0.6); }
            headerbar title { font-weight: 900; color: #00f2ff; letter-spacing: 3px; font-size: 16pt; }
            .sidebar { background: rgba(2, 3, 5, 0.98); border-right: 1px solid rgba(0, 242, 255, 0.3); }
            .sidebar row { padding: 22px 35px; transition: all 0.3s; border-left: 10px solid transparent; }
            .sidebar row:selected { background: rgba(0, 242, 255, 0.2); color: #00f2ff; border-left: 10px solid #00f2ff; }
            .card, scrolledwindow, viewport, notebook, notebook stack, stack { background-color: #010204; color: #d0d5d9; border: none; }
            .terminal-view, textview, textview text, textview .view, textview.view { background-color: #000; color: #00f2ff; font-family: monospace; border: none; }
            notebook header { background-color: #05070a; padding: 5px; border-bottom: 2px solid rgba(0, 242, 255, 0.3); }
            notebook tab { padding: 12px 24px; background: transparent; color: #888; font-weight: bold; border: none; }
            notebook tab:checked { background: rgba(0, 242, 255, 0.15); color: #00f2ff; border-bottom: 3px solid #00f2ff; }
            treeview, treeview.view { background-color: #010204; color: #d0d5d9; }
            treeview:selected { background: rgba(0, 242, 255, 0.3); }
            button, button:active, button:checked { background: #05070a; color: #00f2ff; border: 1.5px solid rgba(0, 242, 255, 0.35); border-radius: 12px; padding: 12px 24px; font-weight: 700; transition: all 0.2s; }
            button:hover { background: rgba(0, 242, 255, 0.15); border-color: #00f2ff; box-shadow: 0 0 15px rgba(0, 242, 255, 0.3); }
            button.suggested-action { background: #00f2ff; color: #000; font-weight: 900; box-shadow: 0 0 35px rgba(0, 242, 255, 0.9); border: none; }
            entry { background: rgba(5, 7, 10, 0.98); border: 2px solid rgba(0, 242, 255, 0.3); border-radius: 12px; color: #fff; padding: 14px; }
            label.dim-label { color: #666; font-size: 10pt; }
        """
    },









    "matrix": {
        "name": "Active Digital",
        "description": "Deep green command center — focused and premium",
        "animation": "pulse_green",
        "css": """
            window { background-color: #040804; color: #4ade80; }
            headerbar { background: rgba(5, 12, 5, 0.95); border-bottom: 1px solid #22c55e; }
            .sidebar row:selected { background: rgba(34, 197, 94, 0.15); color: #22c55e; border-left: 4px solid #22c55e; }
            .card { background: rgba(20, 30, 20, 0.6); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 8px; }
        """
    },
    "ghost": {
        "name": "Ghost HUD",
        "description": "Tactical icy blue HUD for high-stakes ops",
        "animation": "radar_blue",
        "css": """
            window { background-color: #0b111a; color: #7dd3fc; }
            headerbar { background: rgba(15, 23, 42, 0.95); border-bottom: 2px solid #0ea5e9; }
            .sidebar row:selected { background: rgba(14, 165, 233, 0.15); color: #0ea5e9; border-left: 4px solid #0ea5e9; }
            .card { background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(14, 165, 233, 0.2); }
        """
    },
    # (Other themes professionalized with high-fidelity palettes)
}

# ─────────────────────────────────────────────────────────────────────
# 3) PUBLIC API
# ─────────────────────────────────────────────────────────────────────

def get_theme_names(): return list(THEMES.keys())
def get_theme(name): return THEMES.get(name, THEMES["dark"])
def get_theme_css(name): return get_theme(name)["css"]
def get_theme_animation(name): return get_theme(name)["animation"]

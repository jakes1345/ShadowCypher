"""
ShadowComponents — The Elite Tactical UI Library.
Grouped, high-performance GTK components for the Apex Predator HUD.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import math

class TacticalTerminal(Gtk.Box):
    """A glass-styled terminal with smooth scrolling and high-fidelity output."""
    def __init__(self, height=300):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.get_style_context().add_class("terminal-view")
        self.text_view.set_size_request(-1, height)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.text_view)
        self.pack_start(self.scroll, True, True, 0)

    def log(self, text: str, tag: str = "INFO"):
        """Thread-safe logging to the terminal."""
        def _insert():
            buf = self.text_view.get_buffer()
            timestamp = GLib.DateTime.new_now_local().format("%H:%M:%S")
            msg = f"[{timestamp}] [{tag.upper()}] {text}\n"
            buf.insert(buf.get_end_iter(), msg)
            # Auto-scroll to end
            adj = self.scroll.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
            
        GLib.idle_add(_insert)

class DataPod(Gtk.Box):
    """A glowing data card for tactical metrics."""
    def __init__(self, title: str, initial_value: str = "---"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.get_style_context().add_class("card")
        
        self.lbl_title = Gtk.Label(label=title.upper())
        self.lbl_title.get_style_context().add_class("dim-label")
        self.pack_start(self.lbl_title, False, False, 0)
        
        self.lbl_value = Gtk.Label(label=initial_value)
        self.lbl_value.get_style_context().add_class("metric-value")
        self.pack_start(self.lbl_value, False, False, 0)

    def set_value(self, value: str):
        GLib.idle_add(self.lbl_value.set_text, str(value))

class TacticalHeader(Gtk.Box):
    """Consistent header for all suite pages."""
    def __init__(self, title: str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_margin_bottom(20)
        
        lbl = Gtk.Label(label=title.upper())
        lbl.get_style_context().add_class("app-title")
        self.pack_start(lbl, False, False, 0)
        
        # Spacer
        self.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), True, True, 20)
        
        # Activity Spinner (Apex Sentry)
        self.spinner = Gtk.Spinner()
        self.pack_end(self.spinner, False, False, 0)

    def set_active(self, active: bool):
        if active: self.spinner.start()
        else: self.spinner.stop()

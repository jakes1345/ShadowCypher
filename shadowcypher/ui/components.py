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
        self._create_tags()

    def _create_tags(self):
        buf = self.text_view.get_buffer()
        tag_table = buf.get_tag_table()
        tags = [
            ("timestamp", {"foreground": "#64748b", "weight": 400}),
            ("system", {"foreground": "#fbbf24", "weight": 700}),
            ("user", {"foreground": "#00d4ff", "weight": 900}),
            ("ai", {"foreground": "#a78bfa", "weight": 700}),
            ("quantum", {"foreground": "#00ff9d", "weight": 800}),
            ("error", {"foreground": "#f87171", "weight": 700}),
            ("success", {"foreground": "#34d399", "weight": 700}),
        ]
        for name, props in tags:
            tag = Gtk.TextTag.new(name); tag_table.add(tag)
            for k, v in props.items(): tag.set_property(k, v)

    def clear(self):
        """Thread-safe clear of the terminal buffer."""
        def _clear():
            self.text_view.get_buffer().set_text("")
        GLib.idle_add(_clear)

    def log(self, text: str, tag: str = "INFO"):
        """Thread-safe logging with stylistic tags."""
        def _insert():
            buf = self.text_view.get_buffer()
            ts = GLib.DateTime.new_now_local().format("%H:%M:%S")
            it = buf.get_end_iter()
            buf.insert_with_tags_by_name(it, f"[{ts}] ", "timestamp")
            
            it = buf.get_end_iter()
            color_tag = tag.lower() if tag.lower() in ["system", "quantum", "error", "success", "ai"] else "timestamp"
            buf.insert_with_tags_by_name(it, f"[{tag.upper()}] ", color_tag)
            
            it = buf.get_end_iter()
            buf.insert(it, f"{text}\n")
            
            adj = self.scroll.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
        GLib.idle_add(_insert)

class DataPod(Gtk.Box):
    """A glowing data card for tactical metrics."""
    def __init__(self, title: str, initial_value: str = "---", accent: str = "cyan"):
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
    
    def update_value(self, value: str):
        self.set_value(value)

class TacticalHeader(Gtk.Box):
    """Consistent header for all suite pages."""
    def __init__(self, title: str, subtitle: str = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_margin_bottom(20)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        lbl = Gtk.Label(label=title.upper())
        lbl.get_style_context().add_class("app-title")
        main_box.pack_start(lbl, False, False, 0)
        
        # Spacer
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), True, True, 20)
        
        # Activity Spinner (Apex Sentry)
        self.spinner = Gtk.Spinner()
        main_box.pack_end(self.spinner, False, False, 0)
        
        self.pack_start(main_box, False, False, 0)

        if subtitle:
            sub = Gtk.Label(label=subtitle.upper())
            sub.set_halign(Gtk.Align.START)
            sub.get_style_context().add_class("text-muted")
            sub.set_markup(f"<span size='small' color='#64748b'>{subtitle.upper()}</span>")
            self.pack_start(sub, False, False, 0)

    def set_active(self, active: bool):
        if active: self.spinner.start()
        else: self.spinner.stop()

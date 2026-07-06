"""Chat window widget for GTK desktop app."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class ChatWindow(Gtk.VBox):
    """Chat window widget - Phase 1 placeholder."""

    def __init__(self):
        super().__init__()
        self.set_spacing(10)
        self.set_margin_top(10)
        self.set_margin_start(10)
        self.set_margin_end(10)

        # Placeholder
        placeholder = Gtk.Label(label="Chat feature - Phase 1 (Desktop GTK)")
        self.pack_start(placeholder, False, False, 10)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class SupportPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        center.set_valign(Gtk.Align.CENTER)
        center.set_halign(Gtk.Align.CENTER)
        lbl = Gtk.Label()
        lbl.set_markup(
            "<span size='x-large' weight='800' color='#3b82f6'>SUPPORT</span>\n"
            "<span color='#64748b'>Visit shadowcypher.site for documentation and support.</span>"
        )
        lbl.set_justify(Gtk.Justification.CENTER)
        center.pack_start(lbl, False, False, 0)
        self.pack_start(center, True, True, 0)

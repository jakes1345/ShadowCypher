"""Vault unlock dialog for GTK desktop app."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class VaultUnlockDialog(Gtk.Dialog):
    """Dialog to unlock vault with master password."""

    def __init__(self, parent):
        super().__init__(title="Unlock Vault", parent=parent, modal=True)
        self.set_default_size(300, 200)

        content = self.get_content_area()

        # Lock icon label
        icon_label = Gtk.Label(label="🔒")
        icon_label.set_markup("<big>🔒</big>")
        content.pack_start(icon_label, False, False, 10)

        # Title
        title = Gtk.Label(label="Enter Master Password")
        title.set_markup("<b>Enter Master Password</b>")
        content.pack_start(title, False, False, 10)

        # Password input
        self.password_input = Gtk.Entry()
        self.password_input.set_visibility(False)
        self.password_input.set_placeholder_text("Password")
        content.pack_start(self.password_input, False, False, 10)

        # Buttons
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        "Unlock", Gtk.ResponseType.OK)

        content.show_all()

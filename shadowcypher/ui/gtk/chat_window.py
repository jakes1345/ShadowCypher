"""GTK chat window widget — wraps the full ChatPage implementation."""
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from shadowcypher.ui.chat_page import ChatPage


class ChatWindow(Gtk.VBox):
    """Chat window widget — thin wrapper around ChatPage for embedding in the main window.

    Previously this was a placeholder; now it delegates entirely to ChatPage
    which has the full encrypted-group chat, room list, message polling, and
    instance discovery implemented.
    """

    def __init__(self):
        super().__init__()
        self.set_spacing(0)

        # ChatPage is a full GTK widget; pack it to fill this container
        self._chat = ChatPage()
        self.pack_start(self._chat, True, True, 0)
        self.show_all()

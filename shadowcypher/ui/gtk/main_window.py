"""Main window for GTK desktop app with notebook tabs."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from shadowcypher.ui.gtk.chat_window import ChatWindow


class MainWindow(Gtk.Window):
    """Main application window with notebook tabs."""

    def __init__(self):
        super().__init__(Gtk.WindowType.TOPLEVEL)
        self.set_title("ShadowCypher Desktop")
        self.set_default_size(800, 600)
        self.connect("destroy", Gtk.main_quit)

        # Create notebook
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.LEFT)

        # Add Chat tab
        chat_window = ChatWindow()
        notebook.append_page(chat_window, Gtk.Label(label="Chat"))

        # Add notebook to window
        self.add(notebook)
        self.show_all()

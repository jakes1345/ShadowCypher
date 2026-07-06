"""Chat window widget for GTK desktop app."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class ChatWindow(Gtk.VBox):
    """Chat window widget - Phase 1 + Phase 2 instances tab."""

    def __init__(self):
        super().__init__()
        self.set_spacing(10)
        self.set_margin_top(10)
        self.set_margin_start(10)
        self.set_margin_end(10)

        # Create notebook for tabs
        notebook = Gtk.Notebook()
        self.pack_start(notebook, True, True, 0)

        # Chat tab (Phase 1)
        chat_box = Gtk.VBox(spacing=8)
        placeholder = Gtk.Label(label="Chat feature - Phase 1 (Desktop GTK)")
        chat_box.pack_start(placeholder, False, False, 10)
        notebook.append_page(chat_box, Gtk.Label("💬 Chat"))

        # Instances tab (Phase 2)
        instances_box = Gtk.VBox(spacing=8)
        instances_label = Gtk.Label("Connected Shadow Instances")
        instances_label.set_line_wrap(True)
        instances_box.pack_start(instances_label, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        self.instance_store = Gtk.ListStore(str, str, bool)  # id, endpoint, online
        tree = Gtk.TreeView(model=self.instance_store)

        col_id = Gtk.TreeViewColumn("Instance ID", Gtk.CellRendererText(), text=0)
        col_ep = Gtk.TreeViewColumn("Endpoint", Gtk.CellRendererText(), text=1)
        col_on = Gtk.TreeViewColumn("Online", Gtk.CellRendererToggle(), active=2)

        tree.append_column(col_id)
        tree.append_column(col_ep)
        tree.append_column(col_on)

        scroll.add(tree)
        instances_box.pack_start(scroll, True, True, 0)

        notebook.append_page(instances_box, Gtk.Label("🔗 Instances"))

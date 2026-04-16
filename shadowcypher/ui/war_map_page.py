import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import json
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class WarMapPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.set_margin_top(40)
        self.set_margin_start(40)
        self.set_margin_end(40)
        self.nodes = {}
        self._setup_ui()
        bus.subscribe("sovereign_node_update", self._on_node_update_async)

    def _setup_ui(self):
        # Header
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_lbl = Gtk.Label()
        title_lbl.set_markup("<span size='xx-large' weight='bold' color='#f87171'>GLOBAL SPECTRE WAR-MAP</span>")
        header_hbox.pack_start(title_lbl, False, False, 0)
        
        self.status_lbl = Gtk.Label(label="SWEEPING SPECTRUM... [IDLE]")
        self.status_lbl.get_style_context().add_class("dim-text")
        header_hbox.pack_end(self.status_lbl, False, False, 0)
        self.add(header_hbox)

        self.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Main Layout
        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.add(main_hbox)

        # 1. Map Visualization Area (Placeholder for SVG/Canvas)
        self.map_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.map_area.set_size_request(900, 600)
        self.map_area.get_style_context().add_class("terminal-box")
        
        map_placeholder = Gtk.Label()
        map_placeholder.set_markup("<span size='large' color='#334155'>SYNCHRONIZING GLOBAL TOPOLOGY...</span>")
        self.map_area.pack_start(map_placeholder, True, True, 0)
        main_hbox.pack_start(self.map_area, True, True, 0)

        # 2. Node List Area
        node_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        node_panel.set_size_request(400, -1)
        
        node_header = Gtk.Label()
        node_header.set_markup("<span weight='bold' color='#94a3b8'>// ENGAGED_NODES</span>")
        node_header.set_halign(Gtk.Align.START)
        node_panel.pack_start(node_header, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.node_list = Gtk.ListBox()
        self.node_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.node_list.get_style_context().add_class("node-list")
        scroller.add(self.node_list)
        node_panel.pack_start(scroller, True, True, 0)
        
        main_hbox.pack_end(node_panel, False, False, 0)

    def _on_node_update_async(self, data):
        # GTK UI updates must happen on main thread
        GLib.idle_add(self._on_node_update, data)

    def _on_node_update(self, data):
        node_id = data.get("fingerprint") or data.get("ip")
        if not node_id: return
        
        self.nodes[node_id] = data
        self._refresh_list()
        self.status_lbl.set_text(f"SWEEPING SPECTRUM... [{len(self.nodes)} NODES ACTIVE]")

    def _refresh_list(self):
        # Clear list
        for child in self.node_list.get_children():
            self.node_list.remove(child)
        
        for nid, data in self.nodes.items():
            row = Gtk.ListBoxRow()
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_margin_top(10)
            vbox.set_margin_bottom(10)
            vbox.set_margin_start(10)
            
            status_color = "#4ade80" if data.get("online") else "#f87171"
            title = Gtk.Label()
            title.set_markup(f"<span weight='bold' color='{status_color}'>\u25cf</span> <span weight='bold'>{data.get('nick', 'UNKNOWN')}</span> <span size='small' color='#475569'>#{nid[:8]}</span>")
            title.set_halign(Gtk.Align.START)
            vbox.pack_start(title, False, False, 0)
            
            info = Gtk.Label()
            info.set_markup(f"<span size='small' color='#94a3b8'>IP: {data.get('ip')} | OS: {data.get('os')}</span>")
            info.set_halign(Gtk.Align.START)
            vbox.pack_start(info, False, False, 0)
            
            mac = Gtk.Label()
            mac.set_markup(f"<span size='x-small' color='#ef4444' style='italic'>MAC: {data.get('mac', 'UNMASK_FAILED')}</span>")
            mac.set_halign(Gtk.Align.START)
            vbox.pack_start(mac, False, False, 0)
            
            row.add(vbox)
            self.node_list.add(row)
        
        self.node_list.show_all()

# For dynamic loading in app.py
DashboardPage = WarMapPage

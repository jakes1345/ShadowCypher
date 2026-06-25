"""Intelligence page — OSINT and network recon tabs."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from shadowcypher.core.hub import hub
from shadowcypher.modules.osint import OSINT
from shadowcypher.modules.network import Network
from shadowcypher.modules.recon import Recon

class SpectralIntelligencePage(BasePage):
    """Intelligence hub \u2014 OSINT and network recon."""

    def __init__(self, start_tab=0):
        super().__init__("\u2728 Intel")
        self._build_ui(start_tab)

    def _build_ui(self, start_tab):
        self.pod_nodes = DataPod("Nodes", "0", "cyan")
        self.pod_intel = DataPod("Intel score", "0", "violet")
        self.metric_strip.pack_start(self.pod_nodes, True, True, 0)
        self.metric_strip.pack_start(self.pod_intel, True, True, 0)

        # 2. Operational Tabs
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(self._build_osint_tab(), Gtk.Label(label="Strategic OSINT"))
        self.notebook.append_page(self._build_network_tab(), Gtk.Label(label="Network Recon"))
        self.notebook.set_current_page(start_tab)
        
        self.workspace.pack_start(self.notebook, True, True, 0)

    def _build_osint_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_property("margin", 15)
        
        row1 = Gtk.Box(spacing=10)
        self.osint_target = Gtk.Entry()
        self.osint_target.set_placeholder_text("Target Domain, IP, or Email...")
        row1.pack_start(self.osint_target, True, True, 0)
        
        btn_go = Gtk.Button(label="Run")
        btn_go.get_style_context().add_class("suggested-action")
        btn_go.connect("clicked", self._on_osint_pulse)
        row1.pack_start(btn_go, False, False, 0)
        box.pack_start(row1, False, False, 0)

        # Action Flow
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        
        actions = [
            ("SSL Audit", self._on_osint_ssl),
            ("HTTP Headers", self._on_osint_headers),
            ("Tech Stack", self._on_osint_tech),
            ("Whois/ASN", self._on_osint_whois),
            ("Social FP", self._on_osint_social),
            ("Wayback", self._on_osint_wayback)
        ]
        for label, handler in actions:
            btn = self.make_action_btn(label, handler)
            flow.add(btn)
        
        box.pack_start(flow, False, False, 0)
        return box

    def _build_network_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_property("margin", 15)

        row1 = Gtk.Box(spacing=10)
        self.net_target = Gtk.Entry()
        self.net_target.set_placeholder_text("Target Subnet or IP...")
        row1.pack_start(self.net_target, True, True, 0)
        
        self.net_iface = Gtk.Entry()
        self.net_iface.set_placeholder_text("iface (auto)")
        self.net_iface.set_width_chars(10)
        row1.pack_start(self.net_iface, False, False, 0)
        
        box.pack_start(row1, False, False, 0)

        btn_row = Gtk.FlowBox()
        btn_row.set_max_children_per_line(4)
        btn_row.set_selection_mode(Gtk.SelectionMode.NONE)
        
        net_actions = [
            ("ARP Scan", self._on_net_arp),
            ("TCP Sweep", self._on_net_tcp),
            ("SYN Stealth", self._on_net_syn),
            ("OS Detect", self._on_net_os),
            ("Service Map", self._on_net_service),
            ("Packet Capture", self._on_net_pcap)
        ]
        for label, handler in net_actions:
            btn = self.make_action_btn(label, handler)
            btn_row.add(btn)
        
        box.pack_start(btn_row, False, False, 0)
        return box

    # --- Handlers ---
    def _on_osint_pulse(self, btn):
        target = self.osint_target.get_text().strip()
        if not target:
            return
        self.log(f"Intel gather: {target}", "INTEL")
        hub.dispatch_mission(f"Spectral Intelligence audit on {target}", agent_role="commander")

    def _on_osint_ssl(self, btn):
        target = self.osint_target.get_text().strip()
        if not target:
            return
        self.run_job(OSINT.ssl_cert_info(target, 443, self.on_output, self.on_complete))

    def _on_osint_headers(self, btn):
        target = self.osint_target.get_text().strip()
        if not target:
            return
        url = target if target.startswith("http") else f"https://{target}"
        self.run_job(OSINT.http_headers(url, self.on_output, self.on_complete))

    def _on_osint_tech(self, btn):
        target = self.osint_target.get_text().strip()
        if not target:
            return
        url = target if target.startswith("http") else f"https://{target}"
        self.run_job(OSINT.tech_detect(url, self.on_output, self.on_complete))

    def _on_osint_whois(self, btn):
        target = self.osint_target.get_text().strip()
        if not target:
            return
        import threading
        from gi.repository import GLib
        threading.Thread(
            target=lambda: GLib.idle_add(self.log, OSINT.subnet_info(target), "INTEL"),
            daemon=True
        ).start()

    def _on_osint_social(self, btn):
        target = self.osint_target.get_text().strip()
        if not target:
            return
        from shadowcypher.modules.osint_deep import DeepOSINT
        DeepOSINT().social_footprint(target, on_output=self.on_output)

    def _on_osint_wayback(self, btn):
        target = self.osint_target.get_text().strip()
        if not target:
            return
        from shadowcypher.modules.osint_deep import DeepOSINT
        DeepOSINT().wayback_recon(target, on_output=self.on_output)

    def _on_net_arp(self, btn):
        target = self.net_target.get_text().strip() or None
        iface = self.net_iface.get_text().strip() or None
        self.run_job(Network.arp_scan(iface, target, self.on_output, self.on_complete))

    def _on_net_tcp(self, btn):
        target = self.net_target.get_text().strip()
        if not target:
            return
        self.run_job(Network.port_scan_tcp_connect(target, "1-1024", self.on_output, self.on_complete))

    def _on_net_syn(self, btn):
        target = self.net_target.get_text().strip()
        if not target:
            return
        self.run_job(Network.port_scan_syn(target, "1-1024", self.on_output, self.on_complete))

    def _on_net_os(self, btn):
        target = self.net_target.get_text().strip()
        if not target:
            return
        self.run_job(Network.network_os_detection(target, self.on_output, self.on_complete))

    def _on_net_service(self, btn):
        target = self.net_target.get_text().strip()
        if not target:
            return
        self.run_job(Network.service_fingerprint(target, None, self.on_output, self.on_complete))

    def _on_net_pcap(self, btn):
        iface = self.net_iface.get_text().strip() or None
        self.run_job(Network.packet_capture(iface, 100, "", self.on_output, self.on_complete))

"""Network operations page — packet capture, ARP scan, port scanning UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.network import Network
from shadowcypher.ui.base_page import BasePage


class NetworkPage(BasePage):
    """Network operations UI."""

    def __init__(self):
        super().__init__("\U0001f310 Network Operations")

        # ── Target/Interface row ──
        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text("IP or subnet (e.g. 192.168.1.0/24)")
        self.target_entry.set_hexpand(True)
        row1.pack_start(self.target_entry, True, True, 0)

        row1.pack_start(Gtk.Label(label="Interface:"), False, False, 0)
        self.iface_entry = Gtk.Entry()
        self.iface_entry.set_placeholder_text("auto-detect")
        self.iface_entry.set_width_chars(12)
        row1.pack_start(self.iface_entry, False, False, 0)

        row1.pack_start(Gtk.Label(label="Ports:"), False, False, 0)
        self.ports_entry = Gtk.Entry()
        self.ports_entry.set_placeholder_text("1-1024")
        self.ports_entry.set_width_chars(12)
        row1.pack_start(self.ports_entry, False, False, 0)
        self.pack_start(row1, False, False, 0)

        # ── Packet capture options ──
        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="Capture filter:"), False, False, 0)
        self.filter_entry = Gtk.Entry()
        self.filter_entry.set_placeholder_text("BPF filter (e.g. tcp port 80)")
        self.filter_entry.set_hexpand(True)
        row2.pack_start(self.filter_entry, True, True, 0)

        row2.pack_start(Gtk.Label(label="Count:"), False, False, 0)
        self.count_spin = Gtk.SpinButton.new_with_range(10, 10000, 10)
        self.count_spin.set_value(100)
        row2.pack_start(self.count_spin, False, False, 0)
        self.pack_start(row2, False, False, 0)

        # ── Buttons ──
        btn_box = Gtk.Box(spacing=8)
        for label, handler in [
            ("ARP Scan", self._on_arp_scan),
            ("TCP Scan", self._on_tcp_scan),
            ("SYN Scan", self._on_syn_scan),
            ("OS Detect", self._on_os_detect),
            ("Svc Fingerprint", self._on_service),
            ("Capture", self._on_capture),
            ("Monitor", self._on_monitor),
            ("DNS Leak", self._on_dns_leak),
        ]:
            btn_box.pack_start(self.make_action_btn(label, handler), False, False, 0)

        btn_box.pack_end(self.build_stop_button(), False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self.build_terminal()

        # Load initial info
        info = Network.get_interfaces()
        self.clear_output(f"Network Interfaces:\n{info}\n")

    def _get_iface(self):
        iface = self.iface_entry.get_text().strip()
        return iface if iface else None

    def _require_target(self):
        target = self.target_entry.get_text().strip()
        if not target:
            self.clear_output("Enter a target IP/hostname.")
            return None
        return target

    def _on_arp_scan(self, btn):
        subnet = self.target_entry.get_text().strip() or None
        self.clear_output(f"ARP scanning {subnet or 'auto-detected subnet'}...\n\n")
        self.run_job(Network.arp_scan(self._get_iface(), subnet, self.on_output, self.on_complete))

    def _on_tcp_scan(self, btn):
        target = self._require_target()
        if not target:
            return
        ports = self.ports_entry.get_text().strip() or "1-1024"
        self.clear_output(f"TCP connect scan: {target} ports {ports}...\n\n")
        self.run_job(Network.port_scan_tcp_connect(target, ports, self.on_output, self.on_complete))

    def _on_syn_scan(self, btn):
        target = self._require_target()
        if not target:
            return
        ports = self.ports_entry.get_text().strip() or "1-65535"
        self.clear_output(f"SYN stealth scan: {target} ports {ports}...\n\n")
        self.run_job(Network.port_scan_syn(target, ports, self.on_output, self.on_complete))

    def _on_service(self, btn):
        target = self._require_target()
        if not target:
            return
        ports = self.ports_entry.get_text().strip() or None
        self.clear_output(f"Service fingerprinting: {target}...\n\n")
        self.run_job(Network.service_fingerprint(target, ports, self.on_output, self.on_complete))

    def _on_capture(self, btn):
        iface = self._get_iface()
        count = int(self.count_spin.get_value())
        filt = self.filter_entry.get_text().strip()
        self.clear_output(f"Capturing {count} packets on {iface or 'default'}...\n\n")
        self.run_job(Network.packet_capture(iface, count, filt, self.on_output, self.on_complete))

    def _on_monitor(self, btn):
        iface = self._get_iface()
        self.clear_output(f"Monitoring traffic on {iface or 'default'}...\n\n")
        self.run_job(Network.network_monitor(iface, self.on_output, self.on_complete))

    def _on_dns_leak(self, btn):
        self.clear_output("Running DNS leak test...\n\n")
        self.run_job(Network.dns_leak_test(self.on_output, self.on_complete))

    def _on_os_detect(self, btn):
        target = self._require_target()
        if not target:
            return
        self.clear_output(f"OS Fingerprinting: {target}...\n\n")
        self.run_job(Network.network_os_detection(target, self.on_output, self.on_complete))

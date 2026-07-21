"""Network operations page — packet capture, ARP scan, port scanning UI."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.core.stealth import require_stealth
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
        self.workspace.pack_start(row1, False, False, 0)

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
        self.workspace.pack_start(row2, False, False, 0)

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
        self.workspace.pack_start(btn_box, False, False, 0)

        self.build_terminal()

        # ── Script tools (pure-Python, no nmap dependency) ──
        script_nb = Gtk.Notebook()
        script_nb.append_page(self._build_port_reaper_tab(), Gtk.Label(label="Port Reaper"))
        script_nb.append_page(self._build_packet_siphon_tab(), Gtk.Label(label="Packet Siphon"))
        script_nb.append_page(self._build_arp_phantom_tab(), Gtk.Label(label="ARP Phantom"))
        script_nb.append_page(self._build_apex_stress_tab(), Gtk.Label(label="Apex Stress"))
        self.workspace.pack_start(script_nb, True, True, 0)

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

    # ── Script tool tabs ─────────────────────────────────────────────────────

    def _build_port_reaper_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self._pr_target = Gtk.Entry()
        self._pr_target.set_placeholder_text("IP / hostname")
        self._pr_target.set_hexpand(True)
        row.pack_start(self._pr_target, True, True, 0)
        row.pack_start(Gtk.Label(label="Ports:"), False, False, 0)
        self._pr_ports = Gtk.Entry()
        self._pr_ports.set_placeholder_text("1-1024")
        self._pr_ports.set_width_chars(12)
        row.pack_start(self._pr_ports, False, False, 0)
        row.pack_start(Gtk.Label(label="Threads:"), False, False, 0)
        self._pr_threads = Gtk.SpinButton.new_with_range(50, 5000, 50)
        self._pr_threads.set_value(500)
        row.pack_start(self._pr_threads, False, False, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        scan_btn = self.make_action_btn("Scan", self._on_port_reaper)
        banner_btn = self.make_action_btn("Scan + Banners", self._on_port_reaper_banners)
        btn_row.pack_start(scan_btn, False, False, 0)
        btn_row.pack_start(banner_btn, False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_packet_siphon_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="Interface:"), False, False, 0)
        self._ps_iface = Gtk.Entry()
        self._ps_iface.set_placeholder_text("eth0 / auto")
        self._ps_iface.set_width_chars(10)
        row.pack_start(self._ps_iface, False, False, 0)
        row.pack_start(Gtk.Label(label="Count:"), False, False, 0)
        self._ps_count = Gtk.SpinButton.new_with_range(10, 10000, 10)
        self._ps_count.set_value(100)
        row.pack_start(self._ps_count, False, False, 0)
        row.pack_start(Gtk.Label(label="Filter:"), False, False, 0)
        self._ps_filter = Gtk.Entry()
        self._ps_filter.set_placeholder_text("tcp / udp port 53")
        self._ps_filter.set_hexpand(True)
        row.pack_start(self._ps_filter, True, True, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        btn_row.pack_start(self.make_action_btn("Capture (root)", self._on_packet_siphon), False, False, 0)
        btn_row.pack_start(self.make_action_btn("Capture + Hex", self._on_packet_siphon_hex), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_arp_phantom_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self._ap_target = Gtk.Entry()
        self._ap_target.set_placeholder_text("Victim IP")
        self._ap_target.set_hexpand(True)
        row.pack_start(self._ap_target, True, True, 0)
        row.pack_start(Gtk.Label(label="Gateway:"), False, False, 0)
        self._ap_gw = Gtk.Entry()
        self._ap_gw.set_placeholder_text("Router IP")
        self._ap_gw.set_width_chars(16)
        row.pack_start(self._ap_gw, False, False, 0)
        row.pack_start(Gtk.Label(label="Iface:"), False, False, 0)
        self._ap_iface = Gtk.Entry()
        self._ap_iface.set_placeholder_text("eth0")
        self._ap_iface.set_width_chars(8)
        row.pack_start(self._ap_iface, False, False, 0)
        box.pack_start(row, False, False, 0)

        self._ap_forward = Gtk.CheckButton(label="Enable IP forwarding (MITM)")
        box.pack_start(self._ap_forward, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        btn_row.pack_start(self.make_action_btn("Launch ARP Spoof (root)", self._on_arp_phantom), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_apex_stress_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self._ax_target = Gtk.Entry()
        self._ax_target.set_placeholder_text("host or IP")
        self._ax_target.set_hexpand(True)
        row.pack_start(self._ax_target, True, True, 0)
        row.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self._ax_port = Gtk.SpinButton.new_with_range(1, 65535, 1)
        self._ax_port.set_value(80)
        row.pack_start(self._ax_port, False, False, 0)
        row.pack_start(Gtk.Label(label="Iterations:"), False, False, 0)
        self._ax_iters = Gtk.SpinButton.new_with_range(5, 500, 5)
        self._ax_iters.set_value(20)
        row.pack_start(self._ax_iters, False, False, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        btn_row.pack_start(self.make_action_btn("Run Benchmark", self._on_apex_stress), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    # ── Script handlers ──────────────────────────────────────────────────────

    def _on_port_reaper(self, btn):
        t = self._pr_target.get_text().strip()
        if not t:
            self.log("Enter a target.", "WARN")
            return
        require_stealth(on_output=self.on_output)
        args = [t, "-p", self._pr_ports.get_text().strip() or "1-1024",
                "-t", str(int(self._pr_threads.get_value()))]
        self.run_script("port_reaper.py", args)

    def _on_port_reaper_banners(self, btn):
        t = self._pr_target.get_text().strip()
        if not t:
            self.log("Enter a target.", "WARN")
            return
        require_stealth(on_output=self.on_output)
        args = [t, "-p", self._pr_ports.get_text().strip() or "1-1024",
                "-t", str(int(self._pr_threads.get_value())), "--banners"]
        self.run_script("port_reaper.py", args)

    def _on_packet_siphon(self, btn):
        require_stealth(on_output=self.on_output)
        args = []
        iface = self._ps_iface.get_text().strip()
        if iface:
            args += ["-i", iface]
        args += ["-c", str(int(self._ps_count.get_value()))]
        filt = self._ps_filter.get_text().strip()
        if filt:
            args += ["-f", filt]
        self.run_script("packet_siphon.py", args, sudo=True)

    def _on_packet_siphon_hex(self, btn):
        require_stealth(on_output=self.on_output)
        args = []
        iface = self._ps_iface.get_text().strip()
        if iface:
            args += ["-i", iface]
        args += ["-c", str(int(self._ps_count.get_value())), "--hex"]
        filt = self._ps_filter.get_text().strip()
        if filt:
            args += ["-f", filt]
        self.run_script("packet_siphon.py", args, sudo=True)

    def _on_arp_phantom(self, btn):
        t = self._ap_target.get_text().strip()
        g = self._ap_gw.get_text().strip()
        if not t or not g:
            self.log("Target and gateway required.", "WARN")
            return
        require_stealth(on_output=self.on_output)
        args = ["-t", t, "-g", g]
        iface = self._ap_iface.get_text().strip()
        if iface:
            args += ["-i", iface]
        if self._ap_forward.get_active():
            args.append("--forward")
        self.run_script("arp_phantom.py", args, sudo=True)

    def _on_apex_stress(self, btn):
        t = self._ax_target.get_text().strip()
        if not t:
            self.log("Enter a target.", "WARN")
            return
        require_stealth(on_output=self.on_output)
        args = [t, "-p", str(int(self._ax_port.get_value())), "-c", str(int(self._ax_iters.get_value()))]
        self.run_script("load_tester.py", args)

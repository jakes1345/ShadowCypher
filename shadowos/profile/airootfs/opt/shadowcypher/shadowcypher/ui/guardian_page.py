"""Guardian page — personal device security scanner UI."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.core.logger import logger
from shadowcypher.ui.base_page import BasePage


class GuardianPage(BasePage):
    """Guardian: local network + host security scanner."""

    def __init__(self):
        super().__init__("\U0001f6e1 Guardian — Device Security")

        from shadowcypher.ui.components import DataPod
        self.pod_devices = DataPod("devices", "—", "cyan")
        self.pod_risk = DataPod("risk", "—", "amber")
        self.pod_status = DataPod("status", "idle", "violet")
        self.metric_strip.pack_start(self.pod_devices, True, True, 0)
        self.metric_strip.pack_start(self.pod_risk, True, True, 0)
        self.metric_strip.pack_start(self.pod_status, True, True, 0)

        notebook = Gtk.Notebook()
        notebook.append_page(self._build_scan_tab(), Gtk.Label(label="Network Scan"))
        notebook.append_page(self._build_devices_tab(), Gtk.Label(label="Devices"))
        notebook.append_page(self._build_audit_tab(), Gtk.Label(label="Host Audit"))
        notebook.append_page(self._build_router_tab(), Gtk.Label(label="Router Audit"))
        notebook.append_page(self._build_monitor_tab(), Gtk.Label(label="Monitor"))
        notebook.append_page(self._build_harden_tab(), Gtk.Label(label="Harden"))
        notebook.append_page(self._build_host_audit_tab(), Gtk.Label(label="Host Audit"))
        notebook.append_page(self._build_fail2ban_tab(), Gtk.Label(label="Fail2Ban"))
        notebook.append_page(self._build_tls_tab(), Gtk.Label(label="TLS Audit"))
        notebook.append_page(self._build_yara_tab(), Gtk.Label(label="YARA Scan"))
        self.workspace.pack_start(notebook, False, False, 0)
        self._scan_devices: list = []

    # ── Tabs ─────────────────────────────────────────────────────────────────

    def _build_devices_tab(self):
        """Device inventory panel — shows results of the last local scan with click-to-detail."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        hdr = Gtk.Box(spacing=8)
        hdr_lbl = Gtk.Label()
        hdr_lbl.set_markup("<span color='#94a3b8' size='small'>Device inventory from the last network scan. Click a device to see port history, risk score, and details.</span>")
        hdr_lbl.set_line_wrap(True)
        hdr_lbl.set_xalign(0)
        hdr.pack_start(hdr_lbl, True, True, 0)
        refresh_btn = self.make_action_btn("Refresh", self._on_devices_refresh)
        hdr.pack_end(refresh_btn, False, False, 0)
        box.pack_start(hdr, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)

        self._device_listbox = Gtk.ListBox()
        self._device_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._device_listbox.connect("row-activated", self._on_device_row_activated)
        self._device_listbox.get_style_context().add_class("shadowbox")
        scroll.add(self._device_listbox)
        box.pack_start(scroll, True, True, 0)

        self._device_detail_revealer = Gtk.Revealer()
        self._device_detail_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._device_detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._device_detail_box.set_margin_top(8)
        self._device_detail_revealer.add(self._device_detail_box)
        box.pack_start(self._device_detail_revealer, False, False, 0)

        self._populate_device_list(self._scan_devices)
        return box

    def _populate_device_list(self, devices):
        for child in self._device_listbox.get_children():
            self._device_listbox.remove(child)

        if not devices:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label()
            lbl.set_markup("<span color='#555555' size='small'>No devices yet — run a network scan first.</span>")
            lbl.set_margin_start(8)
            lbl.set_margin_top(6)
            lbl.set_margin_bottom(6)
            lbl.set_xalign(0)
            row.add(lbl)
            self._device_listbox.add(row)
            self._device_listbox.show_all()
            return

        RISKY_PORTS = {21, 23, 445, 1900, 3389, 7547}
        for d in devices:
            row = Gtk.ListBoxRow()
            row._device_data = d
            hbox = Gtk.Box(spacing=12)
            hbox.set_margin_start(8)
            hbox.set_margin_end(8)
            hbox.set_margin_top(5)
            hbox.set_margin_bottom(5)

            ports = d.get("open_ports") or []
            risky = [p for p in ports if p in RISKY_PORTS]
            risk_color = "#ef4444" if risky else ("#f97316" if len(ports) > 4 else "#48c78e")
            risk_char = "●"

            indicator = Gtk.Label(label=risk_char)
            indicator.set_markup(f"<span color='{risk_color}'>{risk_char}</span>")
            hbox.pack_start(indicator, False, False, 0)

            name_lbl = Gtk.Label()
            name = d.get("hostname") or d.get("ip") or d.get("mac", "unknown")
            name_lbl.set_markup(f"<b>{name}</b>")
            name_lbl.set_xalign(0)
            hbox.pack_start(name_lbl, False, False, 0)

            ip_lbl = Gtk.Label()
            ip_lbl.set_markup(f"<span color='#94a3b8' size='small'>{d.get('ip', '')}</span>")
            hbox.pack_start(ip_lbl, True, True, 0)

            port_lbl = Gtk.Label()
            port_str = ", ".join(str(p) for p in ports[:6]) if ports else "—"
            if len(ports) > 6:
                port_str += f" +{len(ports) - 6}"
            port_lbl.set_markup(f"<span color='#64748b' size='small'>{port_str}</span>")
            hbox.pack_end(port_lbl, False, False, 0)

            row.add(hbox)
            self._device_listbox.add(row)

        self._device_listbox.show_all()

    def _on_device_row_activated(self, listbox, row):
        d = getattr(row, "_device_data", None)
        if not d:
            self._device_detail_revealer.set_reveal_child(False)
            return

        for child in self._device_detail_box.get_children():
            self._device_detail_box.remove(child)

        RISKY_PORTS = {21, 23, 445, 1900, 3389, 7547}
        ports = d.get("open_ports") or []
        risky = [p for p in ports if p in RISKY_PORTS]

        risk = min(len(risky) * 8 + (len(ports) > 4) * 5, 60)
        risk_label = "HIGH" if risk >= 40 else "MEDIUM" if risk >= 15 else "LOW"
        risk_color = "#ef4444" if risk >= 40 else "#f97316" if risk >= 15 else "#48c78e"

        detail_lbl = Gtk.Label()
        detail_lbl.set_markup(
            f"<b>{d.get('hostname') or d.get('ip') or d.get('mac', '?')}</b>  "
            f"<span color='#64748b'>{d.get('mac', '—')}</span>  "
            f"<span color='#94a3b8'>{d.get('vendor', '—')}</span>\n"
            f"<span size='small'>IP: {d.get('ip', '—')}  ·  OS: {d.get('os_fingerprint') or '—'}  ·  "
            f"Type: {d.get('device_type') or '—'}  ·  "
            f"<span color='{risk_color}'>RISK: {risk_label}</span></span>\n"
            f"<span size='small' color='#94a3b8'>Ports: {', '.join(str(p) for p in ports) or 'none detected'}</span>"
            + (f"\n<span size='small' color='#ef4444'>⚠ Risky ports: {', '.join(str(p) for p in risky)}</span>" if risky else "")
        )
        detail_lbl.set_use_markup(True)
        detail_lbl.set_line_wrap(True)
        detail_lbl.set_xalign(0)
        detail_lbl.set_margin_start(8)
        detail_lbl.set_margin_top(4)
        detail_lbl.set_margin_bottom(4)
        self._device_detail_box.pack_start(detail_lbl, False, False, 0)
        self._device_detail_box.show_all()
        self._device_detail_revealer.set_reveal_child(True)

    def _on_devices_refresh(self, btn):
        self.pod_status.update("SCANNING")
        self.run_script("guardian.py", ["scan"])

    def _build_scan_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Discovers every device on your LAN, fingerprints OS, checks for dangerous open ports and weak configs.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Subnet:"), False, False, 0)
        self._scan_subnet = Gtk.Entry()
        self._scan_subnet.set_placeholder_text("auto-detect (e.g. 192.168.1.0/24)")
        self._scan_subnet.set_hexpand(True)
        row.pack_start(self._scan_subnet, True, True, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Scan Network", self._on_scan), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_audit_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Deep security audit of this machine: open ports, running services, SUID binaries, sudoers, cron jobs, world-writable paths.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Audit This Machine", self._on_audit), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_router_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Audits your home router: default creds check, exposed admin panel, UPnP exposure, WAN-facing services, firmware fingerprint.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Audit Router", self._on_router), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_monitor_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Continuous threat monitoring: new device detection, ARP poisoning, port changes, unexpected traffic. Runs until stopped.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Interval (s):"), False, False, 0)
        self._mon_interval = Gtk.SpinButton.new_with_range(10, 300, 10)
        self._mon_interval.set_value(30)
        row.pack_start(self._mon_interval, False, False, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Start Monitor", self._on_monitor), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_harden_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Auto-harden this machine: disable unused services, tighten SSH, configure nftables rules, remove weak ciphers. Requires root.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Harden (root)", self._on_harden, style="destructive-action"), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_scan(self, btn):
        self.pod_status.update("SCANNING")
        self.run_script("guardian.py", ["scan"])
        import threading
        threading.Thread(target=self._bg_scan_and_refresh, daemon=True).start()

    def _bg_scan_and_refresh(self):
        import subprocess, shutil, xml.etree.ElementTree as ET, time
        from gi.repository import GLib
        time.sleep(1)  # let guardian.py start
        nmap = shutil.which("nmap")
        if not nmap:
            return
        try:
            out = subprocess.check_output(
                [nmap, "-sn", "-oX", "-", "192.168.1.0/24"],
                timeout=60, stderr=subprocess.DEVNULL,
            )
            root = ET.fromstring(out)
            devices = []
            for host in root.findall("host"):
                if host.find("status").get("state") != "up":
                    continue
                d: dict = {}
                for addr in host.findall("address"):
                    t = addr.get("addrtype", "")
                    if t == "ipv4":
                        d["ip"] = addr.get("addr")
                    elif t == "mac":
                        d["mac"] = addr.get("addr")
                        d["vendor"] = addr.get("vendor", "")
                hostnames = host.find("hostnames")
                if hostnames is not None:
                    hn = hostnames.find("hostname")
                    if hn is not None:
                        d["hostname"] = hn.get("name")
                ports_el = host.find("ports")
                if ports_el is not None:
                    d["open_ports"] = [
                        int(p.get("portid")) for p in ports_el.findall("port")
                        if p.find("state") is not None and p.find("state").get("state") == "open"
                    ]
                if d.get("ip") or d.get("mac"):
                    devices.append(d)
            self._scan_devices = devices
            GLib.idle_add(self._populate_device_list, devices)
            GLib.idle_add(self.pod_devices.update, str(len(devices)))
            GLib.idle_add(self.pod_status.update, "idle")
        except Exception:
            GLib.idle_add(self.pod_status.update, "idle")

    def _on_audit(self, btn):
        self.pod_status.update("AUDITING")
        self.run_script("guardian.py", ["audit"])

    def _on_router(self, btn):
        self.pod_status.update("AUDITING")
        self.run_script("guardian.py", ["router"])

    def _on_monitor(self, btn):
        self.pod_status.update("MONITORING")
        self.run_script("guardian.py", ["monitor"])

    def _on_harden(self, btn):
        dlg = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Auto-harden this machine?",
        )
        dlg.format_secondary_text("This will modify system configuration (SSH, firewall, services). Requires root.")
        resp = dlg.run()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK:
            self.pod_status.update("HARDENING")
            self.run_script("guardian.py", ["harden"], sudo=True)

    def _build_host_audit_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Deep local host audit: rootkit detection (rkhunter), hardening assessment (Lynis), system misconfiguration checks. Requires root.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("RKHunter Scan", self._on_rkhunter), False, False, 0)
        btn_row.pack_start(self.make_action_btn("Lynis Audit", self._on_lynis), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_fail2ban_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Monitor and manage fail2ban jails: view banned IPs, ban/unban hosts, inspect log patterns. Requires fail2ban installed.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("View Status", self._on_fail2ban), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_tls_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Audit TLS/SSL certificates and configurations: cipher strength, certificate expiry, protocol versions, HSTS headers.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Host:port"), False, False, 0)
        self._tls_target = Gtk.Entry()
        self._tls_target.set_placeholder_text("example.com:443")
        self._tls_target.set_hexpand(True)
        row.pack_start(self._tls_target, True, True, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Scan TLS", self._on_tls), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_yara_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='small' color='#94a3b8'>Scan files and processes against YARA malware signatures: detects trojans, rootkits, APTs. Rules auto-update from community repos.</span>")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target path:"), False, False, 0)
        self._yara_path = Gtk.Entry()
        self._yara_path.set_placeholder_text("/home or /usr/bin (leave empty to scan all)")
        self._yara_path.set_hexpand(True)
        row.pack_start(self._yara_path, True, True, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Scan with YARA", self._on_yara), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _on_rkhunter(self, btn):
        self.pod_status.update("SCANNING ROOTKITS")
        self.terminal.log("Running RKHunter scan (rootkit detection)...", "INFO")
        try:
            from shadowcypher.modules.host_audit import HostAudit
            auditor = HostAudit()
            output = auditor.rkhunter_scan(on_output=lambda msg: self.terminal.log(msg, "INFO"))
            if output:
                self.terminal.log(output, "SUCCESS")
            else:
                self.terminal.log("RKHunter not available (install: pacman -S rkhunter)", "WARN")
        except Exception as e:
            logger.error("guardian_page", f"RKHunter scan failed: {e}")
            self.terminal.log(f"Error: {e}", "ERROR")
        self.pod_status.update("idle")

    def _on_lynis(self, btn):
        self.pod_status.update("AUDITING HOST")
        self.terminal.log("Running Lynis system hardening audit...", "INFO")
        try:
            from shadowcypher.modules.host_audit import HostAudit
            auditor = HostAudit()
            output = auditor.lynis_scan(on_output=lambda msg: self.terminal.log(msg, "INFO"))
            if output:
                self.terminal.log(output, "SUCCESS")
            else:
                self.terminal.log("Lynis not available (install: pacman -S lynis)", "WARN")
        except Exception as e:
            logger.error("guardian_page", f"Lynis audit failed: {e}")
            self.terminal.log(f"Error: {e}", "ERROR")
        self.pod_status.update("idle")

    def _on_fail2ban(self, btn):
        self.pod_status.update("CHECKING JAILS")
        self.terminal.log("Loading Fail2Ban manager...", "INFO")
        try:
            from shadowcypher.modules.fail2ban_mgr import Fail2BanManager
            mgr = Fail2BanManager()
            output = mgr.status(on_output=lambda msg: self.terminal.log(msg, "INFO"))
            if output:
                self.terminal.log(output, "SUCCESS")
            else:
                self.terminal.log("Fail2Ban not available", "WARN")
        except Exception as e:
            logger.error("guardian_page", f"Fail2Ban check failed: {e}")
            self.terminal.log(f"Error: {e}", "ERROR")
        self.pod_status.update("idle")

    def _on_tls(self, btn):
        target = self._tls_target.get_text() or "localhost:443"
        self.pod_status.update("SCANNING TLS")
        self.terminal.log(f"Auditing TLS on {target}...", "INFO")
        try:
            from shadowcypher.modules.tls_audit import TlsAudit
            auditor = TlsAudit()
            output = auditor.full_audit(target, on_output=lambda msg: self.terminal.log(msg, "INFO"))
            if output:
                self.terminal.log(output, "SUCCESS")
            else:
                self.terminal.log("TLS audit completed (testssl.sh not available)", "WARN")
        except Exception as e:
            logger.error("guardian_page", f"TLS audit failed: {e}")
            self.terminal.log(f"Error: {e}", "ERROR")
        self.pod_status.update("idle")

    def _on_yara(self, btn):
        target = self._yara_path.get_text() or "/"
        self.pod_status.update("YARA SCANNING")
        self.terminal.log(f"Scanning {target} with YARA rules...", "INFO")
        try:
            from shadowcypher.modules.yara_scan import YaraScan
            scanner = YaraScan()
            import os
            if os.path.isdir(target):
                output = scanner.scan_directory(target, on_output=lambda msg: self.terminal.log(msg, "INFO"))
            else:
                output = scanner.scan_file(target, on_output=lambda msg: self.terminal.log(msg, "INFO"))
            if output:
                self.terminal.log(output, "SUCCESS")
            else:
                self.terminal.log("YARA scan completed (check if rules are installed)", "WARN")
        except Exception as e:
            logger.error("guardian_page", f"YARA scan failed: {e}")
            self.terminal.log(f"Error: {e}", "ERROR")
        self.pod_status.update("idle")

"""Guardian page — personal device security scanner UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.logger import logger


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
        notebook.append_page(self._build_audit_tab(), Gtk.Label(label="Host Audit"))
        notebook.append_page(self._build_router_tab(), Gtk.Label(label="Router Audit"))
        notebook.append_page(self._build_monitor_tab(), Gtk.Label(label="Monitor"))
        notebook.append_page(self._build_harden_tab(), Gtk.Label(label="Harden"))
        notebook.append_page(self._build_fail2ban_tab(), Gtk.Label(label="Fail2Ban"))
        notebook.append_page(self._build_tls_tab(), Gtk.Label(label="TLS Audit"))
        notebook.append_page(self._build_yara_tab(), Gtk.Label(label="YARA Scan"))
        self.workspace.pack_start(notebook, False, False, 0)

    # ── Tabs ─────────────────────────────────────────────────────────────────

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
        lbl.set_markup("<span size='small' color='#94a3b8'>Auto-harden this machine: disable unused services, tighten SSH, configure UFW, remove weak ciphers. Requires root.</span>")
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

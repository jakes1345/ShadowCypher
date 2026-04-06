"""Vulnerability scanner page — nikto, sqlmap, nmap NSE, searchsploit UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.vuln_scanner import VulnScanner
from shadowcypher.ui.base_page import BasePage


class VulnScannerPage(BasePage):
    """Vulnerability scanning UI — real tool integration."""

    def __init__(self):
        super().__init__("\U0001f6e1 Vulnerability Scanner")

        # ── TACTICAL WORKSPACE (Obsidian Pod) ──
        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        # 1. Header Area
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl = Gtk.Label(label="\U0001f50e SURFACE VULNERABILITY ANALYSIS")
        lbl.get_style_context().add_class("app-title")
        header.pack_start(lbl, False, False, 0)
        self.main_pod.pack_start(header, False, False, 0)

        notebook = Gtk.Notebook()
        notebook.append_page(self._build_nikto_tab(), Gtk.Label(label="Nikto"))
        notebook.append_page(self._build_sqlmap_tab(), Gtk.Label(label="SQLmap"))
        notebook.append_page(self._build_nse_tab(), Gtk.Label(label="Nmap NSE"))
        notebook.append_page(self._build_searchsploit_tab(), Gtk.Label(label="Exploit-DB"))
        notebook.append_page(self._build_assessment_tab(), Gtk.Label(label="Full Assessment"))
        self.main_pod.pack_start(notebook, False, False, 0)

        self.build_terminal()

        stop_box = Gtk.Box()
        stop_box.pack_start(self.build_stop_button(), False, False, 0)
        self.main_pod.pack_start(stop_box, False, False, 0)

    # ── Nikto ──

    def _build_nikto_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.nikto_target = Gtk.Entry()
        self.nikto_target.set_placeholder_text("http://target.com or IP")
        self.nikto_target.set_hexpand(True)
        row.pack_start(self.nikto_target, True, True, 0)

        row.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self.nikto_port = Gtk.Entry()
        self.nikto_port.set_text("80")
        self.nikto_port.set_width_chars(6)
        row.pack_start(self.nikto_port, False, False, 0)

        self.nikto_ssl = Gtk.CheckButton(label="SSL")
        row.pack_start(self.nikto_ssl, False, False, 0)
        box.pack_start(row, False, False, 0)

        btn = self.make_action_btn("\U0001f50d Scan with Nikto", self._on_nikto, "danger-btn")
        box.pack_start(btn, False, False, 0)
        return box

    def _on_nikto(self, btn):
        target = self.nikto_target.get_text().strip()
        if not target:
            self.clear_output("Enter a target.")
            return
        port = int(self.nikto_port.get_text().strip() or "80")
        ssl = self.nikto_ssl.get_active()
        self.clear_output(f"Nikto scan: {target}:{port} (SSL={ssl})\n\n")
        self.run_job(VulnScanner.nikto_scan(
            target, port=port, ssl=ssl,
            on_output=self.on_output, on_complete=self.on_complete
        ))

    # ── SQLmap ──

    def _build_sqlmap_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)

        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="URL:"), False, False, 0)
        self.sqlmap_url = Gtk.Entry()
        self.sqlmap_url.set_placeholder_text("http://target.com/page?id=1")
        self.sqlmap_url.set_hexpand(True)
        row1.pack_start(self.sqlmap_url, True, True, 0)
        box.pack_start(row1, False, False, 0)

        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="POST Data:"), False, False, 0)
        self.sqlmap_data = Gtk.Entry()
        self.sqlmap_data.set_placeholder_text("(optional) user=admin&pass=test")
        self.sqlmap_data.set_hexpand(True)
        row2.pack_start(self.sqlmap_data, True, True, 0)

        row2.pack_start(Gtk.Label(label="Level:"), False, False, 0)
        self.sqlmap_level = Gtk.SpinButton.new_with_range(1, 5, 1)
        self.sqlmap_level.set_value(1)
        row2.pack_start(self.sqlmap_level, False, False, 0)

        row2.pack_start(Gtk.Label(label="Risk:"), False, False, 0)
        self.sqlmap_risk = Gtk.SpinButton.new_with_range(1, 3, 1)
        self.sqlmap_risk.set_value(1)
        row2.pack_start(self.sqlmap_risk, False, False, 0)
        box.pack_start(row2, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("\U0001f489 Test Injection", self._on_sqlmap, "danger-btn"), False, False, 0)
        btn_row.pack_start(self.make_action_btn("\U0001f4be Dump DBs", self._on_sqlmap_enum), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _on_sqlmap(self, btn):
        url = self.sqlmap_url.get_text().strip()
        if not url:
            self.clear_output("Enter a URL with injection point (e.g. ?id=1).")
            return
        data = self.sqlmap_data.get_text().strip() or None
        level = int(self.sqlmap_level.get_value())
        risk = int(self.sqlmap_risk.get_value())
        self.clear_output(f"SQLmap injection test: {url}\nLevel: {level}, Risk: {risk}\n\n")
        self.run_job(VulnScanner.sqlmap_scan(
            url, data=data, level=level, risk=risk,
            on_output=self.on_output, on_complete=self.on_complete
        ))

    def _on_sqlmap_enum(self, btn):
        url = self.sqlmap_url.get_text().strip()
        if not url:
            self.clear_output("Enter a URL first.")
            return
        self.clear_output(f"SQLmap enumerating databases: {url}\n\n")
        self.run_job(VulnScanner.sqlmap_enumerate(
            url, action="dbs",
            on_output=self.on_output, on_complete=self.on_complete
        ))

    # ── Nmap NSE ──

    def _build_nse_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.nse_target = Gtk.Entry()
        self.nse_target.set_placeholder_text("IP or hostname")
        self.nse_target.set_hexpand(True)
        row.pack_start(self.nse_target, True, True, 0)

        row.pack_start(Gtk.Label(label="Ports:"), False, False, 0)
        self.nse_ports = Gtk.Entry()
        self.nse_ports.set_placeholder_text("(optional)")
        self.nse_ports.set_width_chars(12)
        row.pack_start(self.nse_ports, False, False, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(self.make_action_btn("Vuln Scripts", self._on_nse_vuln), False, False, 0)
        btn_row.pack_start(self.make_action_btn("SMB Vulns", self._on_nse_smb), False, False, 0)
        btn_row.pack_start(self.make_action_btn("SSL/TLS Audit", self._on_nse_ssl, ), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _on_nse_vuln(self, btn):
        target = self.nse_target.get_text().strip()
        if not target:
            self.clear_output("Enter a target."); return
        ports = self.nse_ports.get_text().strip() or None
        self.clear_output(f"Nmap vulnerability scripts: {target}\n\n")
        self.run_job(VulnScanner.nmap_vuln_scan(target, ports=ports, on_output=self.on_output, on_complete=self.on_complete))

    def _on_nse_smb(self, btn):
        target = self.nse_target.get_text().strip()
        if not target:
            self.clear_output("Enter a target."); return
        self.clear_output(f"SMB vulnerability check: {target}\n\n")
        self.run_job(VulnScanner.nmap_smb_vuln(target, on_output=self.on_output, on_complete=self.on_complete))

    def _on_nse_ssl(self, btn):
        target = self.nse_target.get_text().strip()
        if not target:
            self.clear_output("Enter a target."); return
        self.clear_output(f"SSL/TLS audit: {target}\n\n")
        self.run_job(VulnScanner.nmap_ssl_scan(target, on_output=self.on_output, on_complete=self.on_complete))

    # ── Searchsploit ──

    def _build_searchsploit_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Search:"), False, False, 0)
        self.sploit_query = Gtk.Entry()
        self.sploit_query.set_placeholder_text("e.g. apache 2.4, vsftpd 2.3.4, ms17-010")
        self.sploit_query.set_hexpand(True)
        row.pack_start(self.sploit_query, True, True, 0)

        btn = self.make_action_btn("\U0001f50e Search Exploit-DB", self._on_searchsploit)
        row.pack_start(btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _on_searchsploit(self, btn):
        query = self.sploit_query.get_text().strip()
        if not query:
            self.clear_output("Enter a search query."); return
        self.clear_output(f"Searching Exploit-DB: {query}\n\n")
        self.run_job(VulnScanner.searchsploit(query, on_output=self.on_output, on_complete=self.on_complete))

    # ── Full Assessment ──

    def _build_assessment_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)

        info = Gtk.Label(label="Runs a multi-phase vulnerability assessment:\nPort scan → NSE vuln scripts → SSL audit → HTTP analysis → Exploit-DB cross-reference")
        info.set_halign(Gtk.Align.START)
        info.set_line_wrap(True)
        box.pack_start(info, False, False, 0)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.assess_target = Gtk.Entry()
        self.assess_target.set_placeholder_text("IP or hostname")
        self.assess_target.set_hexpand(True)
        row.pack_start(self.assess_target, True, True, 0)

        btn = self.make_action_btn("\u26a1 Full Assessment", self._on_assess, "danger-btn")
        row.pack_start(btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _on_assess(self, btn):
        target = self.assess_target.get_text().strip()
        if not target:
            self.clear_output("Enter a target."); return
        self.clear_output(f"Starting comprehensive assessment: {target}\nThis will take several minutes...\n\n")
        self.run_job(VulnScanner.full_assessment(target, on_output=self.on_output, on_complete=self.on_complete))

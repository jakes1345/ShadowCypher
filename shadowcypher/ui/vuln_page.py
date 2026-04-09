"""Vulnerability scanner page — nikto, sqlmap, nmap NSE, searchsploit UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.vuln_scanner import VulnScanner
from shadowcypher.ui.base_page import BasePage


from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import TacticalTerminal, TacticalHeader, DataPod
from shadowcypher.core.hub import hub
from shadowcypher.modules.vuln_scanner import VulnScanner
from shadowcypher.core.logger import logger

class VulnScannerPage(BasePage):
    """Apex Vulnerability Nexus. Integrated with ShadowHub."""

    def __init__(self):
        super().__init__("\U0001f6e1 Vulnerability Scanner")
        self._build_ui()

    def _build_ui(self):
        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        # 1. Apex Header
        self.header = TacticalHeader("SURFACE VULNERABILITY ANALYSIS")
        self.main_pod.pack_start(self.header, False, False, 0)

        # 2. Strategic Tabs
        notebook = Gtk.Notebook()
        notebook.append_page(self._build_nikto_tab(), Gtk.Label(label="Nikto"))
        notebook.append_page(self._build_sqlmap_tab(), Gtk.Label(label="SQLmap"))
        notebook.append_page(self._build_nse_tab(), Gtk.Label(label="Nmap NSE"))
        self.main_pod.pack_start(notebook, False, False, 0)

        # 3. Apex Terminal
        self.terminal = TacticalTerminal(height=400)
        self.main_pod.pack_start(self.terminal, True, True, 0)

    def _build_nikto_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_all(15)
        row = Gtk.Box(spacing=10)
        self.nikto_target = Gtk.Entry(placeholder_text="Target URL/IP")
        row.pack_start(self.nikto_target, True, True, 0)
        
        btn = Gtk.Button(label="SCAN_NIKTO")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self._on_nikto)
        row.pack_end(btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _on_nikto(self, btn):
        target = self.nikto_target.get_text().strip()
        if not target: return
        self.header.set_active(True)
        self.terminal.log(f"INITIATING_NIKTO_SCAN: {target}", "VULN")
        hub.register_mission(f"Nikto vulnerability scan on {target}")
        VulnScanner.nikto_scan(target, on_output=lambda x: self.terminal.log(x.strip(), "NIKTO"), 
                             on_complete=lambda: self.header.set_active(False))

    def _build_sqlmap_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_all(15)
        self.sqlmap_url = Gtk.Entry(placeholder_text="IP/URL for SQLi Check")
        box.pack_start(self.sqlmap_url, False, False, 0)
        
        btn = Gtk.Button(label="INJECT_TEST")
        btn.get_style_context().add_class("destructive-action")
        btn.connect("clicked", self._on_sqlmap)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_sqlmap(self, btn):
        url = self.sqlmap_url.get_text().strip()
        if not url: return
        self.terminal.log(f"INITIATING_SQLMAP_PULSE: {url}", "SQLMAP")
        VulnScanner.sqlmap_scan(url, on_output=lambda x: self.terminal.log(x.strip(), "SQLMAP"))

    def _build_nse_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_all(15)
        self.nse_target = Gtk.Entry(placeholder_text="Target IP")
        box.pack_start(self.nse_target, False, False, 0)
        
        btn = Gtk.Button(label="NSE_VULN_AUDIT")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self._on_nse_vuln)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_nse_vuln(self, btn):
        target = self.nse_target.get_text().strip()
        if not target: return
        self.terminal.log(f"RUNNING_NSE_VULN_SCRIPTS: {target}", "NMAP")
        VulnScanner.nmap_vuln_scan(target, on_output=lambda x: self.terminal.log(x.strip(), "NMAP"))

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

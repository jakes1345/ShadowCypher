"""Vulnerability scanner page — nikto, sqlmap, nmap NSE, searchsploit UI."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from shadowcypher.core.hub import hub
from shadowcypher.modules.vuln_scanner import VulnScanner
from shadowcypher.ui.base_page import BasePage


class VulnScannerPage(BasePage):
    """Apex Vulnerability Nexus. Integrated with ShadowHub."""

    def __init__(self):
        super().__init__("\U0001f6e1 Vulnerability Scanner")
        self._scanner = VulnScanner()
        self._build_ui()

    def _build_ui(self):
        # Strategic Tabs
        notebook = Gtk.Notebook()
        notebook.append_page(self._build_nikto_tab(), Gtk.Label(label="Nikto"))
        notebook.append_page(self._build_sqlmap_tab(), Gtk.Label(label="SQLmap"))
        notebook.append_page(self._build_nse_tab(), Gtk.Label(label="Nmap NSE"))
        notebook.append_page(self._build_shadow_tab(), Gtk.Label(label="Shadow Audit"))
        self.workspace.pack_start(notebook, False, False, 0)

    def _build_nikto_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15); box.set_margin_bottom(15); box.set_margin_start(15); box.set_margin_end(15)
        row = Gtk.Box(spacing=10)
        self.nikto_target = Gtk.Entry()
        self.nikto_target.set_placeholder_text("Target URL/IP")
        row.pack_start(self.nikto_target, True, True, 0)

        btn = Gtk.Button(label="SCAN_NIKTO")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self._on_nikto)
        row.pack_end(btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _on_nikto(self, btn):
        target = self.nikto_target.get_text().strip()
        if not target:
            return
        self.header.set_active(True)
        self.terminal.log(f"INITIATING_NIKTO_SCAN: {target}", "VULN")
        hub.dispatch_mission(f"Nikto vulnerability scan on {target}")
        self._scanner.nikto_scan(
            target,
            on_output=lambda x: GLib.idle_add(self.terminal.log, x.strip(), "NIKTO"),
        )

    def _build_sqlmap_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15); box.set_margin_bottom(15); box.set_margin_start(15); box.set_margin_end(15)
        self.sqlmap_url = Gtk.Entry()
        self.sqlmap_url.set_placeholder_text("IP/URL for SQLi Check")
        box.pack_start(self.sqlmap_url, False, False, 0)

        btn = Gtk.Button(label="INJECT_TEST")
        btn.get_style_context().add_class("destructive-action")
        btn.connect("clicked", self._on_sqlmap)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_sqlmap(self, btn):
        url = self.sqlmap_url.get_text().strip()
        if not url:
            return
        self.terminal.log(f"INITIATING_SQLMAP_PULSE: {url}", "SQLMAP")
        self._scanner.sqlmap_scan(
            url,
            on_output=lambda x: GLib.idle_add(self.terminal.log, x.strip(), "SQLMAP"),
        )

    def _build_nse_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15); box.set_margin_bottom(15); box.set_margin_start(15); box.set_margin_end(15)
        self.nse_target = Gtk.Entry()
        self.nse_target.set_placeholder_text("Target IP")
        box.pack_start(self.nse_target, False, False, 0)

        btn = Gtk.Button(label="NSE_VULN_AUDIT")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self._on_nse_vuln)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_nse_vuln(self, btn):
        target = self.nse_target.get_text().strip()
        if not target:
            return
        self.terminal.log(f"RUNNING_NSE_VULN_SCRIPTS: {target}", "NMAP")
        # Use nuclei_scan with vuln tags as the NSE equivalent
        self._scanner.nuclei_scan(
            target,
            tags="cve,vuln",
            on_output=lambda x: GLib.idle_add(self.terminal.log, x.strip(), "NMAP"),
        )

    def _build_shadow_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15); box.set_margin_bottom(15); box.set_margin_start(15); box.set_margin_end(15)

        info = Gtk.Label(xalign=0)
        info.set_markup(
            "<span color='#94a3b8' size='small'>Full audit: Nikto web scan + Nuclei CVE templates + Nmap service/version.</span>"
        )
        info.set_line_wrap(True)
        box.pack_start(info, False, False, 0)

        self.shadow_target = Gtk.Entry()
        self.shadow_target.set_placeholder_text("Target URL or IP (e.g. 192.168.1.1 or https://example.com)")
        box.pack_start(self.shadow_target, False, False, 0)

        btn = self.make_action_btn("\u26a1 FULL AUDIT", self._on_shadow_audit, "danger-btn")
        box.pack_start(btn, False, False, 0)
        return box

    def _on_shadow_audit(self, btn):
        import shutil
        import threading
        target = self.shadow_target.get_text().strip()
        if not target:
            return
        self.terminal.log(f"FULL_AUDIT_START: {target}", "SYSTEM")

        def _run():
            out = lambda x: GLib.idle_add(self.terminal.log, x.strip(), "AUDIT") if x.strip() else None
            # 1. Nikto web scan
            if shutil.which("nikto"):
                self.terminal.log("\u2192 nikto web scan", "AUDIT")
                self._scanner.nikto_scan(target, on_output=out)
            else:
                GLib.idle_add(self.terminal.log, "nikto not found \u2014 skipping", "WARN")
            # 2. Nuclei CVE templates
            if shutil.which("nuclei"):
                GLib.idle_add(self.terminal.log, "\u2192 nuclei cve,vuln templates", "AUDIT")
                self._scanner.nuclei_scan(target, tags="cve,vuln", on_output=out)
            else:
                GLib.idle_add(self.terminal.log, "nuclei not found \u2014 skipping", "WARN")
            # 3. Nmap service/version fingerprint
            if shutil.which("nmap"):
                GLib.idle_add(self.terminal.log, "\u2192 nmap service+version fingerprint", "AUDIT")
                from shadowcypher.modules.network import Network
                Network.service_fingerprint(target, on_output=out)
            else:
                GLib.idle_add(self.terminal.log, "nmap not found \u2014 skipping", "WARN")
            GLib.idle_add(self.terminal.log, "FULL_AUDIT_COMPLETE", "SYSTEM")

        threading.Thread(target=_run, daemon=True).start()

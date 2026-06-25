"""Vulnerability scanner page — nikto, sqlmap, nmap NSE, searchsploit UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from shadowcypher.core.hub import hub
from shadowcypher.modules.vuln_scanner import VulnScanner
from shadowcypher.core.logger import logger


class VulnScannerPage(BasePage):
    """Vulnerability scanner UI."""

    def __init__(self):
        super().__init__("\U0001f6e1 Vulnerability Scanner")
        self._scanner = VulnScanner()
        self._build_ui()

    def _build_ui(self):
        # Strategic Tabs
        notebook = Gtk.Notebook()
        notebook.append_page(self._build_auto_tab(), Gtk.Label(label="Auto Scan"))
        notebook.append_page(self._build_nikto_tab(), Gtk.Label(label="Nikto"))
        notebook.append_page(self._build_sqlmap_tab(), Gtk.Label(label="SQLmap"))
        notebook.append_page(self._build_nse_tab(), Gtk.Label(label="Nmap NSE"))
        notebook.append_page(self._build_shadow_tab(), Gtk.Label(label="Shadow Audit"))
        self.workspace.pack_start(notebook, False, False, 0)

    def _build_nikto_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)
        row = Gtk.Box(spacing=10)
        self.nikto_target = Gtk.Entry()
        self.nikto_target.set_placeholder_text("Target URL/IP")
        row.pack_start(self.nikto_target, True, True, 0)

        btn = Gtk.Button(label="Nikto")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self._on_nikto)
        row.pack_end(btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    def _on_nikto(self, btn):
        target = self.nikto_target.get_text().strip()
        if not target:
            return
        self.terminal.log(f"Nikto → {target}", "VULN")
        hub.dispatch_mission(f"Nikto vulnerability scan on {target}")
        self._scanner.nikto_scan(
            target,
            on_output=lambda x: GLib.idle_add(self.terminal.log, x.strip(), "NIKTO"),
        )

    def _build_sqlmap_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)
        self.sqlmap_url = Gtk.Entry()
        self.sqlmap_url.set_placeholder_text("URL")
        box.pack_start(self.sqlmap_url, False, False, 0)

        btn = Gtk.Button(label="sqlmap")
        btn.get_style_context().add_class("destructive-action")
        btn.connect("clicked", self._on_sqlmap)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_sqlmap(self, btn):
        url = self.sqlmap_url.get_text().strip()
        if not url:
            return
        self.terminal.log(f"SQLmap → {url}", "SQLMAP")
        self._scanner.sqlmap_scan(
            url,
            on_output=lambda x: GLib.idle_add(self.terminal.log, x.strip(), "SQLMAP"),
        )

    def _build_nse_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)
        self.nse_target = Gtk.Entry()
        self.nse_target.set_placeholder_text("Target IP")
        box.pack_start(self.nse_target, False, False, 0)

        btn = Gtk.Button(label="NSE")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self._on_nse_vuln)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_nse_vuln(self, btn):
        target = self.nse_target.get_text().strip()
        if not target:
            return
        self.terminal.log(f"NSE vuln scripts → {target}", "NMAP")
        # Use nuclei_scan with vuln tags as the NSE equivalent
        self._scanner.nuclei_scan(
            target,
            tags="cve,vuln",
            on_output=lambda x: GLib.idle_add(self.terminal.log, x.strip(), "NMAP"),
        )

    def _build_shadow_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)
        self.shadow_target = Gtk.Entry()
        self.shadow_target.set_placeholder_text("target")
        box.pack_start(self.shadow_target, False, False, 0)

        btn = self.make_action_btn("\U0001f441\ufe0f Run Shadow Audit", self._on_shadow_audit, "danger-btn")
        box.pack_start(btn, False, False, 0)
        return box

    def _on_shadow_audit(self, btn):
        target = self.shadow_target.get_text().strip()
        self.terminal.log("Running shadow audit...", "AI")
        self._scanner.shadow_zero_day_scan(target, on_output=self.on_output)

    # ── Auto Scan tab ──────────────────────────────────────────────────────────

    def _build_auto_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)

        # Description
        label = Gtk.Label()
        label.set_markup(
            "<b>Adaptive Security Pipeline</b>\n"
            "<small>Runs nmap → decides next tools based on findings → CVE + threat intel → AI report</small>"
        )
        label.set_xalign(0)
        box.pack_start(label, False, False, 0)

        row = Gtk.Box(spacing=8)
        self.auto_target = Gtk.Entry()
        self.auto_target.set_placeholder_text("Target IP / hostname (e.g. 192.168.1.1)")
        row.pack_start(self.auto_target, True, True, 0)

        btn = Gtk.Button(label="Scan")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self._on_auto_scan)
        row.pack_end(btn, False, False, 0)
        box.pack_start(row, False, False, 0)

        # Phase selector (checkboxes in a flow box)
        phases_frame = Gtk.Frame(label="Phases")
        phases_box = Gtk.Box(spacing=6)
        phases_box.set_margin_top(6)
        phases_box.set_margin_bottom(6)
        phases_box.set_margin_start(6)
        phases_box.set_margin_end(6)
        self._phase_checks = {}
        for phase in ["nmap", "web", "vuln", "sqli", "subdomain", "cve", "threat_intel", "assess", "report"]:
            cb = Gtk.CheckButton(label=phase)
            cb.set_active(True)
            phases_box.pack_start(cb, False, False, 0)
            self._phase_checks[phase] = cb
        phases_frame.add(phases_box)
        box.pack_start(phases_frame, False, False, 0)

        return box

    def _on_auto_scan(self, btn):
        target = self.auto_target.get_text().strip()
        if not target:
            return

        selected_phases = [p for p, cb in self._phase_checks.items() if cb.get_active()]

        self.terminal.log(f"Starting auto scan: {target} ({len(selected_phases)} phases)", "AUTOSCAN")

        def _confirm(tool: str, tgt: str) -> bool:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Run {tool} on {tgt}?",
            )
            dialog.format_secondary_text(
                f"{tool} is a potentially destructive test. Confirm you own or are authorized to test {tgt}."
            )
            resp = dialog.run()
            dialog.destroy()
            return resp == Gtk.ResponseType.YES

        def _on_line(line: str):
            GLib.idle_add(self.terminal.log, line.rstrip(), "AUTOSCAN")

        def _on_done(result):
            GLib.idle_add(self.terminal.log,
                          f"Auto scan done: {result.summary()} ({result.duration_s}s)", "SUCCESS")

        hub.dispatch_auto_scan(
            target,
            on_output=_on_line,
            on_complete=_on_done,
            confirm_fn=_confirm,
            phases=selected_phases if selected_phases else None,
        )

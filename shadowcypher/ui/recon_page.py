"""Recon Engine — multi-mode service discovery and intelligence gathering."""

import gi

gi.require_version("Gtk", "3.0")
import threading

from gi.repository import GLib, Gtk

from shadowcypher.modules.recon import Recon
from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod


class ReconPage(BasePage):
    """Recon UI — nmap, masscan, subdomain enum, HTTP probe, AI recon."""

    def __init__(self):
        super().__init__("📡 Recon Engine")
        self._recon = Recon()
        self._active_jobs = 0

        self.pod_gateway = DataPod("Gateway", self._recon.gateway, "cyan")
        self.pod_jobs = DataPod("Jobs", "0", "amber")
        self.pod_hosts = DataPod("Hosts found", "0", "violet")
        for p in [self.pod_gateway, self.pod_jobs, self.pod_hosts]:
            self.metric_strip.pack_start(p, True, True, 0)

        self._build_ui()

    def _build_ui(self):
        # Target row
        target_row = Gtk.Box(spacing=10)
        target_row.set_margin_start(10)
        target_row.set_margin_end(10)
        target_row.set_margin_top(10)
        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text("IP, hostname, CIDR, or domain...")
        self.target_entry.set_text(self._recon.gateway)
        self.target_entry.connect("activate", self._on_quick_scan)
        target_row.pack_start(self.target_entry, True, True, 0)

        quick_btn = Gtk.Button(label="Quick Scan")
        quick_btn.get_style_context().add_class("suggested-action")
        quick_btn.connect("clicked", self._on_quick_scan)
        target_row.pack_start(quick_btn, False, False, 0)

        self.workspace.pack_start(target_row, False, False, 0)

        nb = Gtk.Notebook()
        nb.append_page(self._build_nmap_tab(), Gtk.Label(label="Nmap"))
        nb.append_page(self._build_mass_tab(), Gtk.Label(label="Masscan"))
        nb.append_page(self._build_sub_tab(), Gtk.Label(label="Subdomains"))
        nb.append_page(self._build_http_tab(), Gtk.Label(label="HTTP Probe"))
        nb.append_page(self._build_ai_tab(), Gtk.Label(label="AI Recon"))
        self.workspace.pack_start(nb, True, True, 0)

    def _target(self):
        return self.target_entry.get_text().strip()

    def _inc_jobs(self, n=1):
        self._active_jobs += n
        GLib.idle_add(self.pod_jobs.set_value, str(self._active_jobs))

    def _dec_jobs(self):
        self._active_jobs = max(0, self._active_jobs - 1)
        GLib.idle_add(self.pod_jobs.set_value, str(self._active_jobs))

    def _run(self, fn, *args, **kwargs):
        self._inc_jobs()
        def _worker():
            try:
                fn(*args, **kwargs)
            finally:
                self._dec_jobs()
        threading.Thread(target=_worker, daemon=True).start()

    # ── Nmap tab ──────────────────────────────────────────────────────────────

    def _build_nmap_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 10)

        port_row = Gtk.Box(spacing=8)
        port_row.pack_start(Gtk.Label(label="Ports:"), False, False, 0)
        self._nmap_ports = Gtk.Entry()
        self._nmap_ports.set_text("1-1024")
        self._nmap_ports.set_width_chars(16)
        port_row.pack_start(self._nmap_ports, False, False, 0)
        box.pack_start(port_row, False, False, 0)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(3)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        actions = [
            ("Quick Port Scan", lambda b: self._run(self._recon.quick_scan, self._target(), on_output=self.on_output)),
            ("Service Fingerprint", lambda b: self._run(self._recon.pulse_target, self._target(), "Service Fingerprint", on_output=self.on_output)),
            ("Deep Recon (-A)", lambda b: self._run(self._recon.deep_recon, self._target(), on_output=self.on_output)),
            ("OS Detection", lambda b: self._run(self._recon.pulse_target, self._target(), "OS Detection", on_output=self.on_output)),
            ("Vuln Scripts (-sV --script vuln)", lambda b: self._run(self._recon.pulse_target, self._target(), "Vuln Scan", on_output=self.on_output)),
            ("UDP Top Ports", lambda b: self._run(self._recon.pulse_target, self._target(), "UDP Scan", on_output=self.on_output)),
        ]
        for label, handler in actions:
            flow.add(self.make_action_btn(label, handler))
        box.pack_start(flow, False, False, 0)
        return box

    # ── Masscan tab ───────────────────────────────────────────────────────────

    def _build_mass_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 10)

        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="Ports:"), False, False, 0)
        self._mass_ports = Gtk.Entry()
        self._mass_ports.set_text("0-65535")
        self._mass_ports.set_width_chars(12)
        row1.pack_start(self._mass_ports, False, False, 0)
        row1.pack_start(Gtk.Label(label="Rate:"), False, False, 0)
        self._mass_rate = Gtk.SpinButton()
        self._mass_rate.set_adjustment(Gtk.Adjustment(value=1000, lower=100, upper=100000, step_increment=500))
        row1.pack_start(self._mass_rate, False, False, 0)
        box.pack_start(row1, False, False, 0)

        btn = self.make_action_btn("⚡ Launch Masscan", self._on_masscan)
        box.pack_start(btn, False, False, 0)

        hint = Gtk.Label(xalign=0)
        hint.set_markup("<span size='small' color='#f59e0b'>⚠ Requires root. High rates may trigger IDS.</span>")
        box.pack_start(hint, False, False, 0)
        return box

    def _on_masscan(self, btn):
        target = self._target()
        ports = self._mass_ports.get_text().strip() or "0-65535"
        rate = int(self._mass_rate.get_value())
        if not target:
            return
        self._run(self._recon.masscan, target, ports=ports, rate=rate, on_output=self.on_output)

    # ── Subdomain tab ─────────────────────────────────────────────────────────

    def _build_sub_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 10)

        lbl = Gtk.Label(xalign=0)
        lbl.set_markup("<span color='#94a3b8'>Enumerate subdomains via brute-force and passive sources.</span>")
        box.pack_start(lbl, False, False, 0)

        wl_row = Gtk.Box(spacing=8)
        wl_row.pack_start(Gtk.Label(label="Wordlist:"), False, False, 0)
        self._sub_wordlist = Gtk.Entry()
        self._sub_wordlist.set_placeholder_text("/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt")
        wl_row.pack_start(self._sub_wordlist, True, True, 0)
        box.pack_start(wl_row, False, False, 0)

        btn = self.make_action_btn("🔍 Enumerate Subdomains", self._on_subdomain)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_subdomain(self, btn):
        target = self._target()
        if not target:
            return
        self._run(self._recon.subdomain_enum, target, on_output=self.on_output)

    # ── HTTP Probe tab ────────────────────────────────────────────────────────

    def _build_http_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 10)

        lbl = Gtk.Label(xalign=0)
        lbl.set_markup("<span color='#94a3b8'>Probe HTTP services with httpx — status codes, titles, tech.</span>")
        box.pack_start(lbl, False, False, 0)

        btn = self.make_action_btn("🌐 HTTP Probe", self._on_http_probe)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_http_probe(self, btn):
        target = self._target()
        if not target:
            return
        self._run(self._recon.http_probe, target, on_output=self.on_output)

    # ── AI Recon tab ──────────────────────────────────────────────────────────

    def _build_ai_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 10)

        lbl = Gtk.Label(xalign=0)
        lbl.set_line_wrap(True)
        lbl.set_markup(
            "<span color='#94a3b8'>AI-assisted recon: runs service fingerprint, then asks the AI to "
            "identify attack paths and recommend next steps.</span>"
        )
        box.pack_start(lbl, False, False, 0)

        btn = self.make_action_btn("🧠 AI Recon", self._on_ai_recon)
        box.pack_start(btn, False, False, 0)
        return box

    def _on_ai_recon(self, btn):
        target = self._target()
        if not target:
            return
        self._run(self._recon.ai_recon, target, on_output=self.on_output)

    # ── Quick scan (entry bar) ─────────────────────────────────────────────────

    def _on_quick_scan(self, widget):
        target = self._target()
        if not target:
            return
        self.log(f"Quick scan: {target}", "RECON")
        self._run(self._recon.quick_scan, target, on_output=self.on_output)

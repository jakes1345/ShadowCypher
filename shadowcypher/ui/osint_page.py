"""OSINT page — open source intelligence gathering UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.osint import OSINT
from shadowcypher.ui.base_page import BasePage


class OSINTPage(BasePage):
    """OSINT operations UI."""

    def __init__(self):
        super().__init__("\U0001f50e OSINT / Intelligence")

        # Target input
        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text("Domain, IP, or URL")
        self.target_entry.set_hexpand(True)
        row1.pack_start(self.target_entry, True, True, 0)

        row1.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text("443")
        self.port_entry.set_text("443")
        self.port_entry.set_width_chars(6)
        row1.pack_start(self.port_entry, False, False, 0)
        self.workspace.pack_start(row1, False, False, 0)

        # Action buttons
        btn_box = Gtk.Box(spacing=8)
        for label, handler in [
            ("SSL Cert", self._on_ssl),
            ("HTTP Headers", self._on_headers),
            ("Tech Detect", self._on_tech),
            ("MX/SPF Check", self._on_mx),
            ("Subnet/ASN", self._on_subnet),
            ("Zone Transfer", self._on_zone),
        ]:
            btn_box.pack_start(self.make_action_btn(label, handler), False, False, 0)

        btn_box.pack_end(self.build_stop_button(), False, False, 0)
        self.workspace.pack_start(btn_box, False, False, 0)

        self.build_terminal()

    def _get_target(self):
        target = self.target_entry.get_text().strip()
        if not target:
            self.clear_output("Enter a target domain, IP, or URL.")
            return None
        return target

    def _on_ssl(self, btn):
        target = self._get_target()
        if not target:
            return
        port_str = self.port_entry.get_text().strip()
        port = int(port_str) if port_str.isdigit() else 443
        self.clear_output(f"Fetching SSL certificate: {target}:{port}...\n\n")
        self.run_job(OSINT.ssl_cert_info(target, port, self.on_output, self.on_complete))

    def _on_headers(self, btn):
        target = self._get_target()
        if not target:
            return
        url = target if target.startswith("http") else f"https://{target}"
        self.clear_output(f"Fetching HTTP headers: {url}...\n\n")
        self.run_job(OSINT.http_headers(url, self.on_output, self.on_complete))

    def _on_tech(self, btn):
        target = self._get_target()
        if not target:
            return
        url = target if target.startswith("http") else f"https://{target}"
        self.clear_output(f"Detecting technologies: {url}...\n\n")
        self.run_job(OSINT.tech_detect(url, self.on_output, self.on_complete))

    def _on_mx(self, btn):
        target = self._get_target()
        if not target:
            return
        self.clear_output(f"Checking MX/SPF: {target}...\n\n")
        result = OSINT.email_mx_check(target)
        self.clear_output(result)

    def _on_subnet(self, btn):
        target = self._get_target()
        if not target:
            return
        self.clear_output(f"Subnet/ASN info: {target}...\n\n")
        result = OSINT.subnet_info(target)
        self.clear_output(result)

    def _on_zone(self, btn):
        target = self._get_target()
        if not target:
            return
        self.clear_output(f"Attempting zone transfer: {target}...\n\n")
        self.run_job(OSINT.zone_transfer(target, on_output=self.on_output, on_complete=self.on_complete))

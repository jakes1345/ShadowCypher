"""Wireless page — aircrack-ng suite UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.wireless import Wireless
from shadowcypher.ui.base_page import BasePage


class WirelessPage(BasePage):
    """Wireless attacks UI."""

    def __init__(self):
        super().__init__("\U0001f4e1 Wireless Operations")

        # Interface controls
        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="Interface:"), False, False, 0)
        self.iface_entry = Gtk.Entry()
        self.iface_entry.set_placeholder_text("wlan0")
        self.iface_entry.set_width_chars(14)
        row1.pack_start(self.iface_entry, False, False, 0)

        row1.pack_start(self.make_action_btn("Enable Monitor", self._on_enable_monitor), False, False, 0)
        row1.pack_start(self.make_action_btn("Disable Monitor", self._on_disable_monitor), False, False, 0)
        row1.pack_start(self.make_action_btn("List Interfaces", self._on_list), False, False, 0)
        self.pack_start(row1, False, False, 0)

        # Target AP
        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="BSSID:"), False, False, 0)
        self.bssid_entry = Gtk.Entry()
        self.bssid_entry.set_placeholder_text("AA:BB:CC:DD:EE:FF")
        self.bssid_entry.set_width_chars(20)
        row2.pack_start(self.bssid_entry, False, False, 0)

        row2.pack_start(Gtk.Label(label="Channel:"), False, False, 0)
        self.channel_spin = Gtk.SpinButton.new_with_range(1, 14, 1)
        self.channel_spin.set_value(6)
        row2.pack_start(self.channel_spin, False, False, 0)

        row2.pack_start(Gtk.Label(label="Client:"), False, False, 0)
        self.client_entry = Gtk.Entry()
        self.client_entry.set_placeholder_text("optional client MAC")
        self.client_entry.set_width_chars(20)
        row2.pack_start(self.client_entry, False, False, 0)
        self.pack_start(row2, False, False, 0)

        # Cap file
        row3 = Gtk.Box(spacing=8)
        row3.pack_start(Gtk.Label(label="Cap file:"), False, False, 0)
        self.cap_entry = Gtk.Entry()
        self.cap_entry.set_placeholder_text("path to .cap file for cracking")
        self.cap_entry.set_hexpand(True)
        row3.pack_start(self.cap_entry, True, True, 0)
        cap_btn = Gtk.Button(label="Browse")
        cap_btn.connect("clicked", lambda b: self._browse(self.cap_entry))
        row3.pack_start(cap_btn, False, False, 0)
        self.pack_start(row3, False, False, 0)

        # Action buttons
        btn_box = Gtk.Box(spacing=8)
        btn_box.pack_start(self.make_action_btn("Scan Networks", self._on_scan), False, False, 0)
        btn_box.pack_start(self.make_action_btn("Capture Handshake", self._on_capture), False, False, 0)
        btn_box.pack_start(self.make_action_btn("Deauth", self._on_deauth, "danger-btn"), False, False, 0)
        btn_box.pack_start(self.make_action_btn("Crack WPA", self._on_crack_wpa), False, False, 0)
        btn_box.pack_end(self.build_stop_button(), False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self.build_terminal()

    def _browse(self, entry):
        dialog = Gtk.FileChooserDialog(title="Select file", action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            entry.set_text(dialog.get_filename())
        dialog.destroy()

    def _get_iface(self):
        return self.iface_entry.get_text().strip() or "wlan0"

    def _on_list(self, btn):
        self.clear_output("Listing wireless interfaces...\n\n")
        self.run_job(Wireless.list_interfaces(self.on_output, self.on_complete))

    def _on_enable_monitor(self, btn):
        iface = self._get_iface()
        self.clear_output(f"Enabling monitor mode on {iface}...\n\n")
        self.run_job(Wireless.enable_monitor(iface, self.on_output, self.on_complete))

    def _on_disable_monitor(self, btn):
        iface = self._get_iface()
        self.clear_output(f"Disabling monitor mode on {iface}...\n\n")
        self.run_job(Wireless.disable_monitor(iface, self.on_output, self.on_complete))

    def _on_scan(self, btn):
        iface = self._get_iface()
        self.clear_output(f"Scanning networks on {iface} (30s)...\n\n")
        self.run_job(Wireless.scan_networks(iface, 30, self.on_output, self.on_complete))

    def _on_capture(self, btn):
        iface = self._get_iface()
        bssid = self.bssid_entry.get_text().strip()
        if not bssid:
            self.clear_output("Enter target BSSID.")
            return
        channel = int(self.channel_spin.get_value())
        self.clear_output(f"Capturing handshake: {bssid} CH{channel}...\n\n")
        self.run_job(Wireless.capture_handshake(iface, bssid, channel, 120, self.on_output, self.on_complete))

    def _on_deauth(self, btn):
        iface = self._get_iface()
        bssid = self.bssid_entry.get_text().strip()
        if not bssid:
            self.clear_output("Enter target BSSID.")
            return
        client = self.client_entry.get_text().strip() or None
        self.clear_output(f"Sending deauth to {bssid}...\n\n")
        self.run_job(Wireless.deauth(iface, bssid, client, 10, self.on_output, self.on_complete))

    def _on_crack_wpa(self, btn):
        cap = self.cap_entry.get_text().strip()
        if not cap:
            self.clear_output("Select a .cap file to crack.")
            return
        self.clear_output(f"Cracking WPA: {cap}...\n\n")
        self.run_job(Wireless.crack_wpa(cap, on_output=self.on_output, on_complete=self.on_complete))

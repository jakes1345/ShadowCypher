"""Forensics page — file analysis, hashing, steganography UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.modules.forensics import Forensics
from shadowcypher.ui.base_page import BasePage


class ForensicsPage(BasePage):
    """Digital forensics UI."""

    def __init__(self):
        super().__init__("\U0001f52c Digital Forensics")
        self._engine = Forensics()
        self._build_controls()

    def _build_controls(self):
        # File selection
        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="File:"), False, False, 0)
        self.file_entry = Gtk.Entry()
        self.file_entry.set_placeholder_text("Path to file for analysis")
        self.file_entry.set_hexpand(True)
        row1.pack_start(self.file_entry, True, True, 0)
        browse_btn = Gtk.Button(label="Browse")
        browse_btn.connect("clicked", self._on_browse)
        row1.pack_start(browse_btn, False, False, 0)
        self.workspace.pack_start(row1, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=8)
        for label, handler in [
            ("File Info", self._on_file_info),
            ("SHA-256", self._on_hashes),
            ("Strings", self._on_strings),
            ("EXIF/Meta", self._on_exif),
            ("Binwalk", self._on_binwalk),
        ]:
            btn_box.pack_start(self.make_action_btn(label, handler), False, False, 0)
        self.workspace.pack_start(btn_box, False, False, 0)

    def _on_browse(self, btn):
        dialog = Gtk.FileChooserDialog(title="Select file", action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            self.file_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def _get_file(self):
        f = self.file_entry.get_text().strip()
        if not f:
            self.log("Select a file first.", "WARN")
            return None
        return f

    def _on_file_info(self, btn):
        f = self._get_file()
        if f:
            self.log(f"ANALYZING_FILE: {f}", "FORENSICS")
            self._engine.analyze_file(
                f,
                on_output=lambda x: GLib.idle_add(self.log, x.strip(), "INFO"),
            )

    def _on_hashes(self, btn):
        f = self._get_file()
        if f:
            self.log(f"HASHING_FILE: {f}", "FORENSICS")
            self._engine.generate_hashes(
                f,
                on_output=lambda x: GLib.idle_add(self.log, x.strip(), "INFO"),
            )

    def _on_strings(self, btn):
        f = self._get_file()
        if f:
            self.log(f"STRINGS_EXTRACTION: {f}", "FORENSICS")
            self._engine.extract_strings(
                f,
                on_output=lambda x: GLib.idle_add(self.log, x.strip(), "INFO"),
            )

    def _on_exif(self, btn):
        f = self._get_file()
        if f:
            self.log(f"EXTRACTING_METADATA: {f}", "FORENSICS")
            self._engine.extract_metadata(
                f,
                on_output=lambda x: GLib.idle_add(self.log, x.strip(), "INFO"),
            )

    def _on_binwalk(self, btn):
        f = self._get_file()
        if f:
            self.log(f"BINWALK_AUDIT: {f}", "FORENSICS")
            self._engine.binwalk_scan(
                f,
                on_output=lambda x: GLib.idle_add(self.log, x.strip(), "INFO"),
            )

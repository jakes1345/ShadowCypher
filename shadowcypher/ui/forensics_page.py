"""Forensics page — file analysis, hashing, steganography UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.forensics import Forensics
from shadowcypher.ui.base_page import BasePage


class ForensicsPage(BasePage):
    """Digital forensics UI."""

    def __init__(self):
        super().__init__("\U0001f52c Digital Forensics")

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
        self.pack_start(row1, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=8)
        for label, handler in [
            ("File Info", self._on_file_info),
            ("Hashes", self._on_hashes),
            ("Strings", self._on_strings),
            ("Hex Dump", self._on_hex),
            ("EXIF", self._on_exif),
            ("Stego Detect", self._on_stego),
            ("Binwalk", self._on_binwalk),
            ("PDF Scan", self._on_pdf),
        ]:
            btn_box.pack_start(self.make_action_btn(label, handler), False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self.build_terminal()

    def _on_browse(self, btn):
        dialog = Gtk.FileChooserDialog(title="Select file", action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            self.file_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def _get_file(self):
        f = self.file_entry.get_text().strip()
        if not f:
            self.clear_output("Select a file first.")
            return None
        return f

    def _on_file_info(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(Forensics.file_info(f))

    def _on_hashes(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(Forensics.file_hashes(f))

    def _on_strings(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(f"Extracting strings from {f}...\n\n")
            self.run_job(Forensics.strings_extract(f, on_output=self.on_output, on_complete=self.on_complete))

    def _on_hex(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(Forensics.hex_dump(f))

    def _on_exif(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(Forensics.exif_data(f))

    def _on_stego(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(f"Running steganography detection on {f}...\n\n")
            self.run_job(Forensics.stego_detect(f, self.on_output, self.on_complete))

    def _on_binwalk(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(f"Binwalk extracting: {f}...\n\n")
            self.run_job(Forensics.binwalk_extract(f, on_output=self.on_output, on_complete=self.on_complete))

    def _on_pdf(self, btn):
        f = self._get_file()
        if f:
            self.clear_output(Forensics.pdf_analysis(f))

"""Forensics page — file analysis, hashing, steganography UI."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.modules.forensics import Forensics
from shadowcypher.ui.base_page import BasePage


class ForensicsPage(BasePage):
    """Digital forensics UI."""

    def __init__(self):
        super().__init__("\U0001f52c DIGITAL_FORENSICS_VAULT")

        from shadowcypher.ui.components import DataPod
        
        # 1. Populate Metrics
        self.pod_evidence = DataPod("EVIDENCE_LOCKED", "READY", "cyan")
        self.pod_integrity = DataPod("HOST_INTEGRITY", "VERIFIED", "violet")
        self.pod_audit = DataPod("AUDIT_PULSE", "NOMINAL", "amber")
        
        self.metric_strip.pack_start(self.pod_evidence, True, True, 0)
        self.metric_strip.pack_start(self.pod_integrity, True, True, 0)
        self.metric_strip.pack_start(self.pod_audit, True, True, 0)

        self._engine = Forensics()
        self._build_controls()
        self._build_ops_section()

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

    # ── Ops section: Trace Eraser + Dead Drop ────────────────────────────────

    def _build_ops_section(self):
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.workspace.pack_start(sep, False, False, 4)

        ops_nb = Gtk.Notebook()
        ops_nb.append_page(self._build_trace_eraser_tab(), Gtk.Label(label="Trace Eraser"))
        ops_nb.append_page(self._build_dead_drop_tab(), Gtk.Label(label="Dead Drop"))
        self.workspace.pack_start(ops_nb, False, False, 0)

    def _build_trace_eraser_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        row = Gtk.Box(spacing=6)
        self._te_deep = Gtk.CheckButton(label="--deep (incl. swap/kernel logs)")
        self._te_timestamps = Gtk.CheckButton(label="--timestamps (normalize file times)")
        row.pack_start(self._te_deep, False, False, 0)
        row.pack_start(self._te_timestamps, False, False, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        btn_row.pack_start(self.make_action_btn("Erase Traces (root)", self._on_trace_eraser), False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _build_dead_drop_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self._dd_target = Gtk.Entry()
        self._dd_target.set_placeholder_text("file/dir or /dev/sdX for USB")
        self._dd_target.set_hexpand(True)
        row.pack_start(self._dd_target, True, True, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=6)
        for label, handler in [
            ("Secure Delete", self._on_dd_shred),
            ("Wipe Swap", self._on_dd_swap),
            ("USB Dead Drop", self._on_dd_usb),
            ("PANIC", self._on_dd_panic),
        ]:
            style = "destructive-action" if label == "PANIC" else "suggested-action"
            btn = self.make_action_btn(label, handler, style=style)
            btn_row.pack_start(btn, False, False, 0)
        box.pack_start(btn_row, False, False, 0)
        return box

    def _on_trace_eraser(self, btn):
        args = []
        if self._te_deep.get_active():
            args.append("--deep")
        if self._te_timestamps.get_active():
            args.append("--timestamps")
        self.run_script("trace_eraser.py", args, sudo=True)

    def _on_dd_shred(self, btn):
        t = self._dd_target.get_text().strip()
        if not t:
            self.log("Enter file/dir path.", "WARN")
            return
        self.run_script("dead_drop.py", ["shred", t], sudo=True)

    def _on_dd_swap(self, btn):
        self.run_script("dead_drop.py", ["swap"], sudo=True)

    def _on_dd_usb(self, btn):
        t = self._dd_target.get_text().strip()
        if not t:
            self.log("Enter device path (e.g. /dev/sdb).", "WARN")
            return
        self.run_script("dead_drop.py", ["usb", t], sudo=True)

    def _on_dd_panic(self, btn):
        dlg = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="PANIC — destroy all sensitive data?",
        )
        dlg.format_secondary_text("This is irreversible. All sensitive files will be overwritten and deleted.")
        resp = dlg.run()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK:
            self.run_script("dead_drop.py", ["panic"], sudo=True)

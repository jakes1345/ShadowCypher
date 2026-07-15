"""ShadowCypher Audit Page — Real-time platform verification."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from shadowcypher.core.severity import audit_engine
from shadowcypher.ui.base_page import BasePage


class ShadowCypherAuditPage(BasePage):
    """Platform verification HUD."""

    def __init__(self):
        super().__init__("\U0001f3af ShadowCypher Audit (Platform Verification)")

        info = Gtk.Label()
        info.set_markup("<span color='#94a3b8'>Run a full audit of the platform core and installed runtimes.</span>")
        self.workspace.pack_start(info, False, False, 10)

        # Audit Display
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(20)
        self.grid.set_row_spacing(10)
        self.grid.set_margin_top(20)
        self.workspace.pack_start(self.grid, False, False, 0)

        btn_box = Gtk.Box(spacing=10)
        self.audit_btn = Gtk.Button(label="Run Audit")
        self.audit_btn.connect("clicked", self._on_audit)
        btn_box.pack_start(self.audit_btn, False, False, 0)
        self.workspace.pack_start(btn_box, False, False, 20)

        self.build_terminal()
        self._row_count = 0

    def _on_audit(self, btn):
        self.audit_btn.set_sensitive(False)
        self.clear_output("Running platform audit...\n\n")

        # Clear previous grid rows
        for child in self.grid.get_children():
            self.grid.remove(child)
        self._row_count = 0

        import threading
        def run():
            results = audit_engine.run_full_audit(on_update=lambda msg: GLib.idle_add(self.on_output, msg + "\n"))
            GLib.idle_add(self._display_results, results)

        threading.Thread(target=run, daemon=True).start()

    def _display_results(self, results):
        for name, status in results.items():
            lbl_name = Gtk.Label(label=name, xalign=0)
            lbl_status = Gtk.Label(label=status, xalign=0)

            if "FAIL" in status or "WARNING" in status:
                lbl_status.get_style_context().add_class("danger-text")
            else:
                lbl_status.get_style_context().add_class("cyan-text")

            self.grid.attach(lbl_name, 0, self._row_count, 1, 1)
            self.grid.attach(lbl_status, 1, self._row_count, 1, 1)
            self._row_count += 1

        self.grid.show_all()
        self.on_output("\nAudit complete.\n")
        self.audit_btn.set_sensitive(True)

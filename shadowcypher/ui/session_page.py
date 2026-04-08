"""Session Management Page — manage professional engagements/projects."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.core.session import session
from shadowcypher.ui.base_page import BasePage


class SessionPage(BasePage):
    """Session and Project management UI."""

    def __init__(self):
        super().__init__("\U0001f4c2 Session & Projects")

        # Main layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        self.add(vbox)

        # ── PROJECT SELECTOR ──
        sel_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        lbl = Gtk.Label(label="Active Engagement")
        lbl.get_style_context().add_class("section-title")
        lbl.set_halign(Gtk.Align.START)
        sel_box.pack_start(lbl, False, False, 0)

        sel_row = Gtk.Box(spacing=8)
        self.proj_combo = Gtk.ComboBoxText()
        self._refresh_projects()
        sel_row.pack_start(self.proj_combo, True, True, 0)

        load_btn = self.make_action_btn(
            "\U0001f4c2 Load Project", self._on_load_project
        )
        sel_row.pack_start(load_btn, False, False, 0)
        sel_box.pack_start(sel_row, False, False, 0)
        vbox.pack_start(sel_box, False, False, 0)

        # ── CREATE NEW PROJECT ──
        new_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        new_box.set_name("new-project-box")
        new_box.get_style_context().add_class("terminal-view")
        new_box.set_margin_top(20)
        new_box.set_border_width(20)

        lbl = Gtk.Label(label="Create New Engagement")
        lbl.get_style_context().add_class("section-title")
        lbl.set_halign(Gtk.Align.START)
        new_box.pack_start(lbl, False, False, 0)

        # Grid for inputs
        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.attach(Gtk.Label(label="Project Name:"), 0, 0, 1, 1)
        self.new_name = Gtk.Entry()
        self.new_name.set_placeholder_text("e.g. Penetration Test: ACME Labs")
        grid.attach(self.new_name, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Targets (CSV):"), 0, 1, 1, 1)
        self.new_targets = Gtk.Entry()
        self.new_targets.set_placeholder_text("e.g. 10.10.10.1, 10.10.10.2")
        grid.attach(self.new_targets, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Scope (CSV):"), 0, 2, 1, 1)
        self.new_scope = Gtk.Entry()
        self.new_scope.set_placeholder_text("e.g. 10.10.10.0/24")
        grid.attach(self.new_scope, 1, 2, 1, 1)

        new_box.pack_start(grid, False, False, 0)

        create_btn = self.make_action_btn(
            "\u2795 Create Project", self._on_create_project, "success-btn"
        )
        new_box.pack_start(create_btn, False, False, 0)
        vbox.pack_start(new_box, False, False, 0)

        # ── STATUS / SUMMARY ──
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.status_lbl = Gtk.Label(label="No project currently active.")
        self.status_lbl.set_halign(Gtk.Align.START)
        self.status_box.pack_start(self.status_lbl, False, False, 0)
        vbox.pack_start(self.status_box, False, False, 0)

        # --- DRM LICENSE CONTROL ---
        frm_drm = Gtk.Frame(label="System License & DRM Unlock")
        drm_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        drm_box.set_margin_top(10)
        drm_box.set_margin_bottom(10)
        drm_box.set_margin_start(10)
        drm_box.set_margin_end(10)

        lbl_drm = Gtk.Label(label="AES-256 Key:")
        self.key_entry = Gtk.Entry()
        self.key_entry.set_placeholder_text("Enter License Key to decrypt Arsenal...")
        self.key_entry.set_hexpand(True)
        self.key_entry.set_visibility(False)  # Hide password

        btn_unlock = Gtk.Button(label="Unlock Subsystems")
        btn_unlock.get_style_context().add_class("suggested-action")
        btn_unlock.connect("clicked", self._on_unlock_system)

        drm_box.pack_start(lbl_drm, False, False, 0)
        drm_box.pack_start(self.key_entry, True, True, 0)
        drm_box.pack_start(btn_unlock, False, False, 0)
        frm_drm.add(drm_box)
        vbox.pack_start(frm_drm, False, False, 10)

        # ── EXPORT REPORTS ──
        rep_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        lbl = Gtk.Label(label="Export Engagement Reports")
        lbl.get_style_context().add_class("section-title")
        lbl.set_halign(Gtk.Align.START)
        rep_box.pack_start(lbl, False, False, 0)

        rep_row = Gtk.Box(spacing=8)
        rep_row.pack_start(
            self.make_action_btn(
                "\U0001f310 HTML Report", self._on_export_html, "success-btn"
            ),
            False,
            False,
            0,
        )
        rep_row.pack_start(
            self.make_action_btn("\U0001f4c4 Text Report", self._on_export_text),
            False,
            False,
            0,
        )
        rep_row.pack_start(
            self.make_action_btn("\U0001f4dc JSON Export", self._on_export_json),
            False,
            False,
            0,
        )
        rep_box.pack_start(rep_row, False, False, 0)
        vbox.pack_start(rep_box, False, False, 0)

        # ── STATUS / SUMMARY ──
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.status_lbl = Gtk.Label(label="No project currently active.")
        self.status_lbl.set_halign(Gtk.Align.START)
        self.status_box.pack_start(self.status_lbl, False, False, 0)
        vbox.pack_start(self.status_box, False, False, 0)

        self._update_status()

    def _refresh_projects(self):
        self.proj_combo.remove_all()
        projects = session.get_projects()
        for p in projects:
            self.proj_combo.append_text(p)
        if projects:
            self.proj_combo.set_active(0)

    def _update_status(self):
        from shadowcypher.core.crypto import crypt_mgr

        lock_status = (
            "<span foreground='#00ff41'><b>[UNLOCKED] Arsenal Online</b></span>"
            if crypt_mgr.is_unlocked
            else "<span foreground='#ff0000'><b>[LOCKED] System Encrypted</b></span>"
        )

        if session.current_project:
            p = session.current_project
            status = f"""<b>ACTIVE PROJECT: {p.name}</b>
<b>Created:</b> {p.created}
<b>Targets:</b> {", ".join(p.targets)}
<b>Scope:</b> {", ".join(p.scope) if p.scope else "Unlimited"}

<b>DRM Status:</b> {lock_status}
"""
            self.status_lbl.set_markup(status)
        else:
            self.status_lbl.set_markup(
                f"<i>No professional engagement currently active. Create one above to begin.</i>\n\n<b>DRM Status:</b> {lock_status}"
            )

    def _on_create_project(self, btn):
        name = self.new_name.get_text().strip()
        if not name:
            # Simple error dialog
            return

        targets = [
            t.strip() for t in self.new_targets.get_text().split(",") if t.strip()
        ]
        scope = [s.strip() for s in self.new_scope.get_text().split(",") if s.strip()]

        session.create_project(name, targets=targets, scope=scope)
        self._refresh_projects()
        self._update_status()
        self.new_name.set_text("")
        self.new_targets.set_text("")
        self.new_scope.set_text("")

    def _on_unlock_system(self, btn):
        from shadowcypher.core.crypto import crypt_mgr

        key = self.key_entry.get_text().strip()
        if crypt_mgr.unlock_system(key):
            self.key_entry.set_text("")
            self._update_status()

    def _on_load_project(self, btn):
        name = self.proj_combo.get_active_text()
        if name:
            session.load_project(name)
            self._update_status()

    def _on_export_html(self, btn):
        if session.current_project:
            path = session.current_project.report.generate_html()
            import webbrowser

            webbrowser.open(f"file://{path}")

    def _on_export_text(self, btn):
        if session.current_project:
            path = session.current_project.report.generate_text()
            import subprocess

            subprocess.Popen(
                ["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

    def _on_export_json(self, btn):
        if session.current_project:
            session.current_project.report.generate_json()

"""Standalone GTK threat briefing — not wired into ShadowCypher dashboard."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from public_awareness.engine import ThreatBriefingEngine


class ThreatAwarenessWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="Threat Briefing — Public Awareness")
        self.set_default_size(960, 640)
        self.set_position(Gtk.WindowPosition.CENTER)

        self._threats = ThreatBriefingEngine.list_threats()
        self._current = None
        self._status = None

        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            window { background-color: #0f172a; color: #e2e8f0; }
            label { color: #e2e8f0; }
            .muted-text { color: #64748b; font-size: 0.85em; }
            textview { background-color: #1e293b; color: #cbd5e1; font-family: monospace; }
            entry { background-color: #1e293b; color: #e2e8f0; }
            combobox button { background-color: #1e293b; color: #e2e8f0; }
            listbox row:selected { background-color: #334155; }
            """
        )
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Threat Briefing")
        header.set_subtitle("Know what's out there — share with family")
        self.set_titlebar(header)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_top(12)
        body.set_margin_bottom(12)
        body.set_margin_start(12)
        body.set_margin_end(12)
        root.pack_start(body, True, True, 0)

        intro = Gtk.Label()
        intro.set_markup(
            "<span color='#94a3b8'>Real campaigns people lose money to — QR scams, "
            "iCloud/Google theft, SIM swaps, fake delivery texts, AI voice clones. "
            "Learn it, share it, defend your circle.</span>"
        )
        intro.set_line_wrap(True)
        intro.set_xalign(0)
        body.pack_start(intro, False, False, 0)

        toolbar = Gtk.Box(spacing=8)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search threats (qr, icloud, bank, sim…)")
        self.search_entry.connect("search-changed", self._on_search)
        toolbar.pack_start(self.search_entry, True, True, 0)

        self.cat_combo = Gtk.ComboBoxText()
        self.cat_combo.append_text("All categories")
        for cat in ThreatBriefingEngine.categories():
            self.cat_combo.append_text(cat.replace("_", " ").title())
        self.cat_combo.set_active(0)
        self.cat_combo.connect("changed", self._on_filter)
        toolbar.pack_start(self.cat_combo, False, False, 0)

        export_btn = Gtk.Button(label="Export family playbook")
        export_btn.connect("clicked", self._on_export)
        toolbar.pack_start(export_btn, False, False, 0)

        copy_btn = Gtk.Button(label="Copy tell-a-friend script")
        copy_btn.connect("clicked", self._on_copy_script)
        toolbar.pack_start(copy_btn, False, False, 0)
        body.pack_start(toolbar, False, False, 0)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(280)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-selected", self._on_row_selected)
        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.set_size_request(260, 400)
        list_scroll.add(self.list_box)
        paned.add1(list_scroll)

        detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.title_lbl = Gtk.Label()
        self.title_lbl.set_markup(
            "<span size='large' weight='bold'>Select a threat</span>"
        )
        self.title_lbl.set_xalign(0)
        self.title_lbl.set_line_wrap(True)
        detail_box.pack_start(self.title_lbl, False, False, 0)

        self.detail_buffer = Gtk.TextBuffer()
        self.detail_view = Gtk.TextView(buffer=self.detail_buffer)
        self.detail_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.detail_view.set_editable(False)
        self.detail_view.set_cursor_visible(False)
        detail_scroll = Gtk.ScrolledWindow()
        detail_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        detail_scroll.add(self.detail_view)
        detail_box.pack_start(detail_scroll, True, True, 0)
        paned.add2(detail_box)
        body.pack_start(paned, True, True, 0)

        self._status = Gtk.Statusbar()
        self._status_ctx = self._status.get_context_id("main")
        root.pack_start(self._status, False, False, 0)
        self._set_status(
            f"Loaded {len(self._threats)} threat briefings | public_awareness (standalone)"
        )

        self._populate_list(self._threats)
        if self._threats:
            self.list_box.select_row(self.list_box.get_row_at_index(0))

    def _set_status(self, text: str) -> None:
        self._status.pop(self._status_ctx)
        self._status.push(self._status_ctx, text)

    def _populate_list(self, threats) -> None:
        for child in self.list_box.get_children():
            self.list_box.remove(child)
        sev_color = {
            "critical": "#f87171",
            "high": "#fb923c",
            "medium": "#fbbf24",
            "low": "#94a3b8",
        }
        for t in threats:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            color = sev_color.get(t.severity, "#94a3b8")
            title = Gtk.Label()
            title.set_markup(
                f"<span weight='bold' color='{color}'>[{t.severity.upper()}]</span> {t.title}"
            )
            title.set_xalign(0)
            title.set_line_wrap(True)
            sub = Gtk.Label(label=t.category.replace("_", " "))
            sub.set_xalign(0)
            sub.get_style_context().add_class("muted-text")
            box.pack_start(title, False, False, 0)
            box.pack_start(sub, False, False, 0)
            row.add(box)
            row.threat_id = t.id
            self.list_box.add(row)
        self.list_box.show_all()

    def _on_search(self, entry) -> None:
        self._apply_category_filter()

    def _on_filter(self, _combo) -> None:
        self._apply_category_filter()

    def _apply_category_filter(self) -> None:
        idx = self.cat_combo.get_active()
        threats = ThreatBriefingEngine.search(self.search_entry.get_text())
        if idx > 0:
            cat = ThreatBriefingEngine.categories()[idx - 1]
            threats = [t for t in threats if t.category == cat]
        self._populate_list(threats)

    def _on_row_selected(self, _lb, row) -> None:
        if not row or not hasattr(row, "threat_id"):
            return
        t = ThreatBriefingEngine.get(row.threat_id)
        if not t:
            return
        self._current = t
        self.title_lbl.set_markup(
            f"<span size='large' weight='bold'>{t.title}</span>"
        )
        self.detail_buffer.set_text(ThreatBriefingEngine.format_brief(t))
        self._set_status(f"Briefing: {t.id} ({t.severity})")

    def _on_copy_script(self, _btn) -> None:
        if not self._current:
            self._set_status("Select a threat first")
            return
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clip.set_text(self._current.tell_others, -1)
        self._set_status("Copied tell-a-friend script to clipboard")

    def _on_export(self, _btn) -> None:
        home = Path.home()
        out = home / "family_scam_playbook.md"
        env_out = os.environ.get("PUBLIC_AWARENESS_EXPORT")
        if env_out:
            out = Path(env_out).expanduser()

        def run() -> None:
            msg = ThreatBriefingEngine.export_markdown(
                out, on_output=lambda m: GLib.idle_add(self._set_status, m)
            )
            GLib.idle_add(self._set_status, msg)

        threading.Thread(target=run, daemon=True).start()


class ThreatAwarenessApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.shadowcypher.public-awareness")

    def do_activate(self) -> None:
        win = ThreatAwarenessWindow(self)
        win.connect("destroy", lambda *_: self.quit())
        win.show_all()
        win.present()


def main() -> int:
    app = ThreatAwarenessApp()
    return app.run(None)

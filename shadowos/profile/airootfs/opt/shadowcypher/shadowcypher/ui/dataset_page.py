"""
Dataset page — INTEL HARVEST.

Configures and launches scripts/dataset_scraper.py to collect a security
training corpus from ExploitDB, Metasploit, GitHub red-team repos and Nuclei.
"""

import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.ui.base_page import BasePage


class DatasetPage(BasePage):
    """Training-data collection UI for the security LLM fine-tune pipeline."""

    SOURCES = [
        ("exploitdb",  "ExploitDB exploits + code"),
        ("metasploit", "Metasploit Framework modules"),
        ("github",     "GitHub red-team repos"),
        ("nuclei",     "Nuclei templates (local)"),
    ]

    def __init__(self):
        super().__init__("INTEL HARVEST — Training Data Collection")

        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        form.set_margin_start(12)
        form.set_margin_end(12)
        form.set_margin_top(12)
        form.set_margin_bottom(12)

        # ── Sources (checkboxes) ────────────────────────────────────────
        src_frame = Gtk.Frame(label="Sources")
        src_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        src_box.set_margin_start(10)
        src_box.set_margin_end(10)
        src_box.set_margin_top(6)
        src_box.set_margin_bottom(6)
        self._source_checks: dict[str, Gtk.CheckButton] = {}
        for key, label in self.SOURCES:
            cb = Gtk.CheckButton(label=label)
            cb.set_active(True)
            self._source_checks[key] = cb
            src_box.pack_start(cb, False, False, 0)
        src_frame.add(src_box)
        form.pack_start(src_frame, False, False, 0)

        # ── Output path ─────────────────────────────────────────────────
        out_row = Gtk.Box(spacing=6)
        out_row.pack_start(Gtk.Label(label="Output:"), False, False, 0)
        self._output = Gtk.Entry()
        self._output.set_text("./data/security_corpus.jsonl")
        self._output.set_hexpand(True)
        out_row.pack_start(self._output, True, True, 0)
        browse_btn = Gtk.Button(label="Browse")
        browse_btn.connect("clicked", self._on_browse)
        out_row.pack_start(browse_btn, False, False, 0)
        form.pack_start(out_row, False, False, 0)

        # ── GitHub token (masked) ───────────────────────────────────────
        tok_row = Gtk.Box(spacing=6)
        tok_row.pack_start(Gtk.Label(label="GitHub Token:"), False, False, 0)
        self._token = Gtk.Entry()
        self._token.set_visibility(False)
        self._token.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self._token.set_placeholder_text("optional — falls back to $GITHUB_TOKEN")
        self._token.set_hexpand(True)
        env_tok = os.environ.get("GITHUB_TOKEN", "")
        if env_tok:
            self._token.set_text(env_tok)
        tok_row.pack_start(self._token, True, True, 0)
        form.pack_start(tok_row, False, False, 0)

        # ── Limit per source ────────────────────────────────────────────
        lim_row = Gtk.Box(spacing=6)
        lim_row.pack_start(Gtk.Label(label="Limit per source:"), False, False, 0)
        self._limit = Gtk.SpinButton.new_with_range(10, 100_000, 50)
        self._limit.set_value(1000)
        lim_row.pack_start(self._limit, False, False, 0)
        form.pack_start(lim_row, False, False, 0)

        # ── Action button ───────────────────────────────────────────────
        btn_row = Gtk.Box(spacing=6)
        scrape_btn = self.make_action_btn(
            "\U0001f4e1 SCRAPE", self._on_scrape, "danger-btn"
        )
        btn_row.pack_start(scrape_btn, False, False, 0)
        form.pack_start(btn_row, False, False, 0)

        self.workspace.pack_start(form, False, False, 0)
        self.build_terminal()

        stop_box = Gtk.Box()
        stop_box.pack_start(self.build_stop_button(), False, False, 0)
        self.workspace.pack_start(stop_box, False, False, 0)

    # ── handlers ────────────────────────────────────────────────────────

    def _on_browse(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title="Select output JSONL",
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,   Gtk.ResponseType.OK,
        )
        dialog.set_current_name("security_corpus.jsonl")
        if dialog.run() == Gtk.ResponseType.OK:
            self._output.set_text(dialog.get_filename())
        dialog.destroy()

    def _on_scrape(self, _btn):
        selected = [k for k, cb in self._source_checks.items() if cb.get_active()]
        if not selected:
            self.terminal.log("Select at least one source.", "WARN")
            return

        output = self._output.get_text().strip() or "./data/security_corpus.jsonl"
        limit = int(self._limit.get_value())
        token = self._token.get_text().strip()

        args = [
            "--sources", ",".join(selected),
            "--output",  output,
            "--limit",   str(limit),
        ]
        if token:
            args += ["--github-token", token]

        self.terminal.log(
            f"INTEL_HARVEST: sources={selected} limit={limit} → {output}",
            "TASK",
        )
        self.run_script("dataset_scraper.py", args)

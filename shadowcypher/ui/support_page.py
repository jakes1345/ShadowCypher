"""Support page — system info, diagnostics, documentation links."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import platform
import shutil
import threading

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod


class SupportPage(BasePage):
    """Support hub — diagnostics and documentation."""

    def __init__(self):
        super().__init__("📞 Support & Diagnostics")
        self._build_ui()

    def _build_ui(self):
        self.pod_py = DataPod("Python", platform.python_version(), "cyan")
        self.pod_os = DataPod("OS", platform.system(), "violet")
        self.pod_arch = DataPod("Arch", platform.machine(), "amber")
        for p in [self.pod_py, self.pod_os, self.pod_arch]:
            self.metric_strip.pack_start(p, True, True, 0)

        nb = Gtk.Notebook()
        nb.append_page(self._build_info_tab(), Gtk.Label(label="System Info"))
        nb.append_page(self._build_diag_tab(), Gtk.Label(label="Diagnostics"))
        nb.append_page(self._build_links_tab(), Gtk.Label(label="Docs & Links"))
        self.workspace.pack_start(nb, True, True, 0)

    # ── System Info ───────────────────────────────────────────────────────────

    def _build_info_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_property("margin", 15)

        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(8)

        self._info_rows = [
            ("Platform", platform.platform()),
            ("Python", platform.python_version()),
            ("Architecture", platform.machine()),
            ("Processor", platform.processor() or "—"),
            ("Hostname", platform.node()),
        ]
        try:
            from shadowcypher.core.config import config
            self._info_rows.insert(0, ("ShadowCypher", getattr(config, "version", "—")))
        except Exception:
            pass

        for i, (label, value) in enumerate(self._info_rows):
            k = Gtk.Label(label=label + ":", xalign=0)
            k.get_style_context().add_class("dim-label")
            v = Gtk.Label(label=value, xalign=0)
            v.set_selectable(True)
            grid.attach(k, 0, i, 1, 1)
            grid.attach(v, 1, i, 1, 1)

        box.pack_start(grid, False, False, 0)

        copy_btn = Gtk.Button(label="Copy to Clipboard")
        copy_btn.set_halign(Gtk.Align.START)
        copy_btn.connect("clicked", self._on_copy_info)
        box.pack_start(copy_btn, False, False, 0)

        return box

    def _on_copy_info(self, btn):
        text = "\n".join(f"{k}: {v}" for k, v in self._info_rows)
        clip = Gtk.Clipboard.get_default(btn.get_display())
        clip.set_text(text, -1)
        btn.set_label("Copied!")
        GLib.timeout_add_seconds(2, lambda: btn.set_label("Copy to Clipboard") or False)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def _build_diag_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 15)

        lbl = Gtk.Label(xalign=0)
        lbl.set_markup("<span color='#94a3b8'>Check core services, tools, and AI module availability.</span>")
        box.pack_start(lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        self._diag_btn = Gtk.Button(label="Run Diagnostics")
        self._diag_btn.get_style_context().add_class("suggested-action")
        self._diag_btn.connect("clicked", self._on_run_diag)
        btn_row.pack_start(self._diag_btn, False, False, 0)
        box.pack_start(btn_row, False, False, 0)

        self.build_terminal()
        box.pack_start(self.terminal, True, True, 0)
        return box

    def _on_run_diag(self, btn):
        btn.set_sensitive(False)
        self.clear_output("Running diagnostics...\n\n")

        def _run():
            checks = []

            # Services
            import socket
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)  # nosec B310
                checks.append(("Ollama API", "✓ online"))
            except Exception:
                checks.append(("Ollama API", "✗ offline"))

            try:
                s = socket.socket()
                s.settimeout(1)
                s.connect(("127.0.0.1", 9050))
                s.close()
                checks.append(("Tor SOCKS", "✓ port 9050 open"))
            except Exception:
                checks.append(("Tor SOCKS", "✗ not running"))

            # Security tools
            checks.append(("", ""))
            checks.append(("[Tools]", ""))
            for tool in ["nmap", "nuclei", "masscan", "gobuster", "hydra",
                         "sqlmap", "ffuf", "john", "hashcat", "responder"]:
                found = shutil.which(tool)
                checks.append((f"  {tool}", "✓" if found else "✗"))

            # Python packages
            checks.append(("", ""))
            checks.append(("[Python packages]", ""))
            for pkg in ["gi", "requests", "treequest", "shinka", "pdfminer"]:
                try:
                    __import__(pkg)
                    checks.append((f"  {pkg}", "✓"))
                except ImportError:
                    checks.append((f"  {pkg}", "✗ missing"))

            # AI modules
            checks.append(("", ""))
            checks.append(("[AI modules]", ""))
            for mod in ["shadowcypher.ai.tree_reasoner", "shadowcypher.ai.evo_memory",
                        "shadowcypher.ai.transformer2", "shadowcypher.ai.drope",
                        "shadowcypher.ai.shinka_evolver", "shadowcypher.ai.doc_lora",
                        "shadowcypher.ai.model_merger"]:
                short = mod.split(".")[-1]
                try:
                    __import__(mod)
                    checks.append((f"  {short}", "✓"))
                except Exception as e:
                    checks.append((f"  {short}", f"✗ {e}"))

            for label, status in checks:
                if not label and not status:
                    GLib.idle_add(self.on_output, "\n")
                elif not status:
                    GLib.idle_add(self.on_output, f"{label}\n")
                else:
                    GLib.idle_add(self.on_output, f"  {label:<26} {status}\n")

            GLib.idle_add(self.on_output, "\nDiagnostics complete.\n")
            GLib.idle_add(btn.set_sensitive, True)

        threading.Thread(target=_run, daemon=True).start()

    # ── Docs & Links ──────────────────────────────────────────────────────────

    def _build_links_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 15)

        links = [
            ("🌐 Website", "https://shadowcypher.site"),
            ("📖 Documentation", "https://shadowcypher.site/docs"),
            ("🐛 Report a Bug", "https://github.com/jakes1345/ShadowCypher/issues/new"),
            ("📦 GitHub", "https://github.com/jakes1345/ShadowCypher"),
        ]
        for label, url in links:
            btn = Gtk.LinkButton(uri=url, label=label)
            btn.set_halign(Gtk.Align.START)
            box.pack_start(btn, False, False, 0)

        box.pack_start(Gtk.Separator(), False, False, 8)

        note = Gtk.Label(xalign=0)
        note.set_line_wrap(True)
        note.set_markup(
            "<span color='#64748b'>Include your System Info output when reporting bugs.\n"
            "Run Diagnostics first to check for common issues.</span>"
        )
        box.pack_start(note, False, False, 0)
        return box

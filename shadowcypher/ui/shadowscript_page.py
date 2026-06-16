import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango
import os
import threading

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.ui.base_page import BasePage

_MISSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "shadowscript", "missions")
_ENGINE_PATH  = os.path.join(os.path.dirname(__file__), "..", "..", "shadowscript", "core", "engine.py")

class ShadowScriptPage(BasePage):
    """Tactical IDE for the ShadowCypher scripting language."""

    def __init__(self):
        super().__init__("SHADOWSCRIPT LAB")
        self.set_margin_start(30)
        self.set_margin_end(30)
        self.set_margin_top(20)
        self.set_margin_bottom(20)

        # 1. Header: Sovereign Identity
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold' color='#22d3ee'>SHADOWSCRIPT_LAB</span>")
        title.set_halign(Gtk.Align.START)
        header.pack_start(title, True, True, 0)
        
        status_dot = Gtk.Label(label="\u25cf NATIVE_RUNTIME_READY")
        status_dot.get_style_context().add_class("cyan-text")
        header.pack_end(status_dot, False, False, 10)
        
        self.pack_start(header, False, False, 10)

        # 2. Main Lab Layout (Editor + Terminal)
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(self.paned, True, True, 0)

        # ── THE EDITOR ──
        editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        ed_label = Gtk.Label(label="Tactical Mission Editor (.shadow)", xalign=0)
        ed_label.get_style_context().add_class("dim-text")
        editor_box.pack_start(ed_label, False, False, 0)

        self.editor_view = Gtk.TextView()
        self.editor_view.set_monospace(True)
        self.editor_view.set_left_margin(10)
        self.editor_view.set_top_margin(10)
        self.editor_view.get_style_context().add_class("shadow-editor")
        
        # Default Template
        buffer = self.editor_view.get_buffer()
        buffer.set_text("# NEW MISSION ARCHITECTURE\n\nTARGET(\"127.0.0.1\")\nSWARM()\nAI(\"Explain the current landscape\")\n!sys(\"echo Mission Ready\")\n")
        
        scroll_ed = Gtk.ScrolledWindow()
        scroll_ed.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_ed.add(self.editor_view)
        editor_box.pack_start(scroll_ed, True, True, 0)
        
        self.paned.add1(editor_box)

        # ── THE TERMINAL ──
        term_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        term_label = Gtk.Label(label="Global Execution Trace", xalign=0)
        term_label.get_style_context().add_class("dim-text")
        term_box.pack_start(term_label, False, False, 0)

        self.terminal_view = Gtk.TextView()
        self.terminal_view.set_editable(False)
        self.terminal_view.set_cursor_visible(False)
        self.terminal_view.set_monospace(True)
        self.terminal_view.set_left_margin(10)
        self.terminal_view.set_top_margin(10)
        self.terminal_view.get_style_context().add_class("shadow-terminal")
        
        scroll_term = Gtk.ScrolledWindow()
        scroll_term.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_term.add(self.terminal_view)
        term_box.pack_start(scroll_term, True, True, 0)
        
        self.paned.add2(term_box)
        self.paned.set_position(500)

        # 3. Action Bar: Swarm Ignition
        btn_box = Gtk.ActionBar()
        btn_box.get_style_context().add_class("action-bar-lab")
        
        self.run_btn = Gtk.Button(label="IGNITE_MISSION")
        self.run_btn.get_style_context().add_class("btn-ignite")
        self.run_btn.connect("clicked", self._on_ignite_clicked)
        btn_box.pack_end(self.run_btn)
        
        self.pack_end(btn_box, False, False, 0)

        self.show_all()

    def _on_ignite_clicked(self, btn):
        buffer = self.editor_view.get_buffer()
        start, end = buffer.get_bounds()
        code = buffer.get_text(start, end, True)
        
        os.makedirs(_MISSIONS_DIR, exist_ok=True)
        tmp_path = os.path.join(_MISSIONS_DIR, "live_draft.shadow")
        with open(tmp_path, "w") as f:
            f.write(code)

        self.log_to_terminal("[IGNITION] Spawning tactical runner for: live_draft.shadow\n")

        def run():
            try:
                import sys as _sys
                env = os.environ.copy()
                env["PYTHONPATH"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..")
                )
                import subprocess
                proc = subprocess.Popen(
                    [_sys.executable, _ENGINE_PATH, tmp_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
                )
                for line in proc.stdout:
                    GLib.idle_add(self.log_to_terminal, line)
                for line in proc.stderr:
                    GLib.idle_add(self.log_to_terminal, f"ERROR: {line}")
            except Exception as e:
                GLib.idle_add(self.log_to_terminal, f"CRITICAL_FAILURE: {e}")

        threading.Thread(target=run, daemon=True).start()

    def log_to_terminal(self, text):
        buffer = self.terminal_view.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        # Scroll to bottom
        adj = self.terminal_view.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

class ShadowScriptBible(Gtk.ScrolledWindow):
    """The visual guide to the ShadowCypher Programming Language."""
    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(40)
        box.set_margin_end(40)
        box.set_margin_top(40)
        
        # Load the guide.md
        guide_path = os.path.join(os.path.dirname(__file__), "..", "..", "shadowscript", "docs", "guide.md")
        content = "Guide not found."
        if os.path.exists(guide_path):
            with open(guide_path, "r") as f:
                content = f.read()

        label = Gtk.Label()
        
        # Robust Pango Markup Generation
        markup_lines = []
        for line in content.split("\n"):
            line = GLib.markup_escape_text(line)
            if line.startswith("##"):
                markup_lines.append(f"<span weight='bold' color='#22d3ee'>{line}</span>")
            elif line.startswith("#"):
                markup_lines.append(f"<span size='large' weight='heavy' color='#e2e8f0'>{line}</span>")
            elif line.startswith("```"):
                markup_lines.append(f"<span font='monospace' background='#1e293b'>{line}</span>")
            else:
                markup_lines.append(line)
        
        full_markup = f"<span size='medium' color='#94a3b8'>{''.join([ln + chr(10) for ln in markup_lines])}</span>"
        label.set_markup(full_markup)
        label.set_line_wrap(True)
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)
        
        self.add(box)
        self.show_all()

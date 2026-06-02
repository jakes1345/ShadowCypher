"""
BasePage — The Apex Foundation for all ShadowCypher tactical modules.
Directly integrated with ShadowComponents and ShadowHub.
"""

import gi
import subprocess
import threading
import sys
import os
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.ui.components import TacticalTerminal, TacticalHeader
from shadowcypher.core.hub import hub

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

class BasePage(Gtk.Box):
    """
    Apex Base Page.
    Standardizes the Tactical HUD across all tactical modules.
    """

    def __init__(self, title: str, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        self.set_margin_top(0)
        self.set_margin_bottom(0)
        self.set_margin_start(0)
        self.set_margin_end(0)
        
        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        # 1. Apex Header
        self.header = TacticalHeader(title.upper())
        self.main_pod.pack_start(self.header, False, False, 0)

        # 2. Tactical Metric Strip
        self.metric_strip = Gtk.Box(spacing=10)
        self.metric_strip.set_margin_start(20); self.metric_strip.set_margin_end(20)
        self.main_pod.pack_start(self.metric_strip, False, False, 0)

        # 3. Tactical Environment (H-Box)
        self.tactical_env = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.main_pod.pack_start(self.tactical_env, True, True, 0)

        self.workspace = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.workspace.set_margin_top(20); self.workspace.set_margin_bottom(20)
        self.workspace.set_margin_start(20); self.workspace.set_margin_end(20)
        self.tactical_env.pack_start(self.workspace, True, True, 0)

        # 3b. Intelligence Sidebar (Righty) - Fills the 'Barren' space
        self.intel_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.intel_sidebar.set_size_request(300, -1)
        self.intel_sidebar.set_margin_start(10)
        self.intel_sidebar.set_margin_end(10)
        self.intel_sidebar.set_margin_top(20)
        
        intel_header = Gtk.Label()
        intel_header.set_markup("<span size='small' weight='bold' color='#94a3b8'>// IN-MEMORY_INTELLIGENCE</span>")
        intel_header.set_halign(Gtk.Align.START)
        self.intel_sidebar.pack_start(intel_header, False, False, 0)
        
        self.mission_state_lbl = Gtk.Label(label="STATE: ANALYZING_VECTORS...")
        self.mission_state_lbl.set_halign(Gtk.Align.START)
        self.intel_sidebar.pack_start(self.mission_state_lbl, False, False, 10)
        
        self.tactical_env.pack_end(self.intel_sidebar, False, False, 0)

        # 4. Apex Terminal (Mission Oversight)
        self.terminal = TacticalTerminal(height=340)
        self.main_pod.pack_start(self.terminal, True, True, 0)
        
        self._action_buttons: list[Gtk.Button] = []

    def log(self, text, tag="INFO"):
        """Thread-safe logging."""
        GLib.idle_add(self.terminal.log, text, tag)

    def run_mission(self, query, role="adversary"):
        """Centralized Mission Dispatch."""
        self.header.set_active(True)
        self.log(f"INITIATING_MISSION: {query}", "APEX")
        hub.dispatch_mission(query, agent_role=role)

    def make_action_btn(self, label, handler, style="suggested-action"):
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class(style)
        btn.connect("clicked", handler)
        self._action_buttons.append(btn)
        return btn

    def build_terminal(self):
        if self.terminal.get_parent():
            return Gtk.Box()
        return self.terminal

    def build_stop_button(self):
        btn = Gtk.Button(label="⬛ STOP")
        btn.get_style_context().add_class("destructive-action")
        btn.connect("clicked", self._on_stop)
        return btn

    def _on_stop(self, _btn=None):
        task_id = getattr(self, "_current_task_id", None)
        if task_id:
            from shadowcypher.core.runner import runner
            runner.stop_task(task_id)
            self.log("Task terminated by user.", "ERROR")
        self.header.set_active(False)

    def run_job(self, task_id):
        """Store task ID so Stop button can kill it."""
        self._current_task_id = task_id
        self.header.set_active(True)

    def clear_output(self, text=""):
        GLib.idle_add(self.terminal.clear)
        if text:
            self.log(text)

    def on_output(self, text):
        self.log(text.rstrip())

    def on_complete(self, rc):
        self.header.set_active(False)
        tag = "success" if rc == 0 else "error"
        self.log(f"Done. Exit code: {rc}", tag)

    def run_script(self, script_name: str, args: list, sudo: bool = False):
        """Run a script from shadowcypher/scripts/ as a subprocess, streaming output to terminal."""
        script_path = os.path.abspath(os.path.join(_SCRIPTS_DIR, script_name))
        if not os.path.exists(script_path):
            self.log(f"[ERROR] Script not found: {script_name}", "ERROR")
            return
        cmd = (["sudo"] if sudo else []) + [sys.executable, script_path] + [str(a) for a in args]
        self.header.set_active(True)
        self.log(f"$ {' '.join(cmd)}", "EXEC")

        def _worker():
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    GLib.idle_add(self.terminal.log, line.rstrip(), "INFO")
                rc = proc.wait()
                GLib.idle_add(self.header.set_active, False)
                GLib.idle_add(self.terminal.log, f"[exit {rc}]", "SUCCESS" if rc == 0 else "ERROR")
            except Exception as e:
                GLib.idle_add(self.terminal.log, f"[ERROR] {e}", "ERROR")
                GLib.idle_add(self.header.set_active, False)

        threading.Thread(target=_worker, daemon=True).start()

"""
BasePage — The Apex Foundation for all ShadowCypher tactical modules.
Directly integrated with ShadowComponents and ShadowHub.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.ui.components import TacticalTerminal, TacticalHeader
from shadowcypher.core.hub import hub

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

        # 3. Workspace / Controls Area
        self.workspace = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.workspace.set_margin_top(20)
        self.workspace.set_margin_bottom(20)
        self.workspace.set_margin_start(20)
        self.workspace.set_margin_end(20)
        self.main_pod.pack_start(self.workspace, False, False, 0)

        # 4. Apex Terminal (Mission Oversight)
        self.terminal = TacticalTerminal(height=340)
        self.main_pod.pack_start(self.terminal, True, True, 0)
        
        self._action_buttons = []

    def log(self, text, tag="INFO"):
        """Thread-safe logging."""
        GLib.idle_add(self.terminal.log, text, tag)

    def run_mission(self, query, role="red_team"):
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

    # Legacy Compatibility Layer (Ensures zero 'Nope' moments for old pages)
    def build_terminal(self): 
        # Only pack if not already visible to avoid container double-packing
        if self.terminal.get_parent(): return Gtk.Box() 
        return self.terminal
        
    def build_stop_button(self):
        btn = Gtk.Button(label="TERMINATE_MISSION")
        btn.get_style_context().add_class("destructive-action")
        return btn

    def run_job(self, result):
        """Mock/Wrapper for legacy job execution."""
        self.log(f"EXECUTING_TACTICAL_JOB: {result}", "TASK")

    def clear_output(self, text=""): 
        # Use GLib to clear/set buffer
        self.log("WINDOW_CLEAR", "SYSTEM")
        
    def on_output(self, text): self.log(text)
    def on_complete(self, rc): 
        self.header.set_active(False)
        self.log(f"MISSION_FINALIZED_CODE: {rc}", "SUCCESS")

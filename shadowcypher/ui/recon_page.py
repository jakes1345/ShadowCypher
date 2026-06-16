"""
ShadowCypher Signal Recon Page — High-Fidelity Tactical Intelligence.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from shadowcypher.core.hub import hub
from shadowcypher.modules.recon import Recon

class ReconPage(BasePage):
    """Apex Reconnaissance Hub. Cross-Platform Integrated."""

    def __init__(self):
        super().__init__("\U0001f4e1 SIGNAL RECONNAISSANCE")
        self.inspector = Recon()
        self._build_ui()

    def _build_ui(self):
        # Telemetry Strip
        self.pod_gateway = DataPod("GATEWAY", self.inspector.gateway)
        self.metric_strip.pack_start(self.pod_gateway, True, True, 0)

        # Control Hub
        ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text("ENTER_TARGET_IP_OR_DOMAIN...")
        self.target_entry.set_text(self.inspector.gateway)
        ctrl.pack_start(self.target_entry, True, True, 0)

        self.btn_inspect = Gtk.Button(label="PULSE_SERVICE_MAP")
        self.btn_inspect.get_style_context().add_class("suggested-action")
        self.btn_inspect.connect("clicked", self._on_inspect_clicked)
        ctrl.pack_start(self.btn_inspect, False, False, 0)

        self.workspace.pack_start(ctrl, False, False, 0)

    def _on_inspect_clicked(self, btn):
        target = self.target_entry.get_text()
        if not target:
            return
        
        self.header.set_active(True)
        self.terminal.log(f"INITIATING_CROSS_PLATFORM_PULSE: {target}", "RECON")
        
        self.inspector.pulse_target(
            target, 
            on_output=lambda line: self.terminal.log(line.strip(), "NMAP")
        )
        # AI Shadow Mission
        hub.dispatch_mission(f"Identify service vulnerabilities and exploit paths for {target}.", agent_role="commander")

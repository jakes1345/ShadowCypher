"""APEX UI: ENTERPRISE_NETWORK V3.0"""
from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from gi.repository import Gtk

class AdPage(BasePage):
    def __init__(self):
        super().__init__("🏰 ENTERPRISE_NETWORK")
        self._build_tactical_interface()

    def _build_tactical_interface(self):
        # 1. Metric Strip
        strip = Gtk.Box(spacing=15)
        strip.pack_start(DataPod("PULSE", "ACTIVE", "cyan"), True, True, 0)
        strip.pack_start(DataPod("LOAD", "0.0%", "violet"), True, True, 0)
        strip.set_margin_bottom(20)
        self.workspace.pack_start(strip, False, False, 0)

        # 2. Control Pod
        pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        pod.get_style_context().add_class("card")
        pod.set_margin_top(15); pod.set_margin_bottom(15); pod.set_margin_start(15); pod.set_margin_end(15)
        
        self.target_entry = Gtk.Entry(placeholder_text="MISSION_TARGET_SPEC")
        pod.pack_start(self.target_entry, False, False, 0)
        
        btn = self.make_action_btn("⚡ INITIATE_OPERATION", self._on_mission)
        pod.pack_start(btn, False, False, 0)
        
        self.workspace.pack_start(pod, True, True, 0)

    def _on_mission(self, btn):
        target = self.target_entry.get_text()
        self.run_mission(f"Perform ENTERPRISE_NETWORK on target: {target}")

